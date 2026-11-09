#!/usr/bin/env python3
"""Tarefa 8: treinado (Q4_K_M) no PS4, GPU (Vulkan, -ngl 99) x CPU, mesmo pipeline de 03/11.
Ordem: gpu 0-49, cpu 0-49, gpu 50-99, cpu 50-99. Derivado de run_eval_0311_original.py."""
import csv, json, os, subprocess, sys, time, urllib.request, urllib.error
from datetime import datetime
from grading import grade, extract_strict, extract_flex

PS4_HOST = os.environ["PS4_HOST"]  # Tarefa 8: IP lido do ambiente
PORT = 8081
ROOT = "/mnt/midia/llm-ps4"
# Tarefa 8: dois braços com o MESMO modelo treinado (sha256 d7771967…722b); só muda o binário do servidor.
MODEL = f"{ROOT}/models/proprios/qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf"
MODELS = {"gpu": MODEL, "cpu": MODEL}
SERVERS = {"gpu": f"{ROOT}/llama.cpp/build-vulkan/bin/llama-server -ngl 99",
           "cpu": f"{ROOT}/llama.cpp/build/bin/llama-server"}
EXP = f"{ROOT}/experiments/ps4-eval-gpu-20261106"
ENV = (f"VK_DRIVER_FILES={ROOT}/vulkan/mesa-ps4-extract2-20261106-152705/radeon_icd_local.json "
       f"MESA_SHADER_CACHE_DIR={EXP}/cache/mesa XDG_CACHE_HOME={EXP}/cache/xdg TMPDIR={EXP}/tmp")
TMUX = f"TMUX_TMPDIR={EXP}/tmux"  # socket do tmux fora de /tmp
JINJA = f"{ROOT}/models/proprios/chat_template_treinado.jinja"
KEYFILE = "~/.config/llm-ps4/api-key"
SYSTEM = ("Solve the math problem. Reason briefly, step by step. "
          "On the last line, write only the final answer as: #### <number>")
REST_S, COOL_DELTA_MC, COOL_MAX_S, COOL_POLL_S = 300, 3000, 300, 15
BLOCKS = [("gpu", 0, 50), ("cpu", 0, 50), ("gpu", 50, 100), ("cpu", 50, 100)]
HERE = os.path.dirname(os.path.abspath(__file__))
STAMP = datetime.now().astimezone().strftime("%Y%m%d_%H%M")
OUT_LOCAL = os.path.join(HERE, f"ps4_eval_gpu_{STAMP}.csv")
BLOCKS_LOCAL = os.path.join(HERE, f"ps4_eval_gpu_{STAMP}_blocos.csv")


def log(*a):
    print(datetime.now().strftime("%H:%M:%S"), *a, flush=True)


def ssh(cmd, timeout=60, check=True):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", "ps4", "bash", "-s"], input=cmd,
                       capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"ssh falhou ({p.returncode}): {p.stderr.strip()[:300]}")
    return p.stdout.strip()


def temp_mc():
    return int(ssh("cat /sys/class/hwmon/hwmon2/temp1_input"))


def loadavg():
    return ssh("cut -d' ' -f1-3 /proc/loadavg")


def ensure_key():
    # Tarefa 8: só leitura; usa a mesma chave de 03/11 e não grava nada em ~
    return ssh(f"[ -s {KEYFILE} ] && cat {KEYFILE}")  # fica só em memória; nunca é impresso


def start_server(model):
    ssh(f"""mountpoint -q /mnt/midia || {{ echo NAO_MONTADO >&2; exit 1; }}
{TMUX} tmux kill-session -t llm 2>/dev/null; sleep 2
{TMUX} SHELL=/bin/bash tmux -f /dev/null new-session -d -s llm "env {ENV} {SERVERS[model]} -m {MODELS[model]} -c 4096 -t 8 --jinja --chat-template-file {JINJA} --host 0.0.0.0 --port {PORT} --api-key-file {KEYFILE} 2>&1 | tee -a {EXP}/llama-server_{STAMP}_{model}.log"
""")
    t0 = time.time()
    while time.time() - t0 < 300:
        try:
            with urllib.request.urlopen(f"http://{PS4_HOST}:{PORT}/health", timeout=5) as r:
                if r.status == 200:
                    log(f"servidor pronto ({model}) em {time.time()-t0:.0f}s")
                    return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError("servidor não ficou pronto em 300 s")


def rest():
    """PS4 ocioso (sem llama-server) por REST_S; devolve a temperatura de repouso."""
    ssh(f"{TMUX} tmux kill-session -t llm 2>/dev/null; true")
    log(f"repouso: {REST_S}s com o PS4 ocioso")
    time.sleep(REST_S)
    t = temp_mc()
    log(f"repouso: {t/1000:.1f} °C")
    return t


def wait_cool(target_mc):
    t0 = time.time()
    t = temp_mc()
    while t > target_mc and time.time() - t0 < COOL_MAX_S:
        log(f"esperando esfriar: {t/1000:.1f} °C (alvo {target_mc/1000:.1f})")
        time.sleep(COOL_POLL_S)
        t = temp_mc()
    return t, t <= target_mc, round(time.time() - t0)


def ask(key, q):
    body = {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}],
            "temperature": 0, "seed": 42, "max_tokens": 320,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://{PS4_HOST}:{PORT}/v1/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {key}"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:
        resp = json.load(r)
    return resp, time.perf_counter() - t0


QBT = "http://127.0.0.1:8080/api/v2/torrents"


def qbt_pause():
    out = ssh(f"curl -s -m 10 '{QBT}/info'")
    active = [t["hash"] for t in json.loads(out) if not t["state"].startswith(("stopped", "paused"))]
    if active:
        ssh(f"curl -s -m 10 -X POST -d 'hashes={'|'.join(active)}' '{QBT}/stop'")
    log(f"qBittorrent: {len(active)} torrent(s) ativo(s) pausado(s)")
    return active


def qbt_resume(active):
    if active:
        ssh(f"curl -s -m 10 -X POST -d 'hashes={'|'.join(active)}' '{QBT}/start'")
    log(f"qBittorrent: {len(active)} torrent(s) retomado(s)")


def main():
    qs = [json.loads(l) for l in open(os.path.join(HERE, "questions.jsonl"))]
    key = ensure_key()
    fields = ["modelo", "bloco", "idx", "gold", "pred_strict", "pred_flex", "correct_strict", "correct_flex",
              "finish_reason", "completion_tokens", "prompt_tokens", "prompt_n", "prompt_ms", "predicted_n",
              "predicted_ms", "predicted_per_second", "e2e_s", "inicio", "output"]
    bfields = ["bloco", "modelo", "idx_ini", "idx_fim", "repouso_c", "alvo_c", "temp_ini_c", "temp_fim_c",
               "atingiu_alvo", "espera_s", "load_ini", "load_fim", "inicio", "fim"]
    active = qbt_pause()
    try:
        with open(OUT_LOCAL, "w", newline="") as f, open(BLOCKS_LOCAL, "w", newline="") as fb:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
            wb = csv.DictWriter(fb, fieldnames=bfields); wb.writeheader()
            t_rest = rest()
            target = t_rest + COOL_DELTA_MC
            wb.writerow({"bloco": 0, "modelo": "repouso", "repouso_c": t_rest / 1000, "alvo_c": target / 1000,
                         "temp_ini_c": t_rest / 1000, "espera_s": REST_S, "load_fim": loadavg(),
                         "fim": datetime.now().astimezone().isoformat(timespec="seconds")})
            fb.flush()
            for bi, (model, a, b) in enumerate(BLOCKS, 1):
                start_server(model)
                t_ini, ok, waited = wait_cool(target)
                load_ini = loadavg()
                ini = datetime.now().astimezone().isoformat(timespec="seconds")
                log(f"bloco {bi}: {model} {a}-{b-1}, {t_ini/1000:.1f} °C (alvo {target/1000:.1f}, atingiu: {ok}, espera {waited}s)")
                for q in qs[a:b]:
                    when = datetime.now().astimezone().isoformat(timespec="seconds")
                    resp, e2e = ask(key, q["question"])
                    out = resp["choices"][0]["message"].get("content") or ""
                    tm = resp.get("timings", {})
                    s, fl = grade(out, q["gold"])
                    w.writerow({"modelo": model, "bloco": bi, "idx": q["idx"], "gold": q["gold"],
                                "pred_strict": extract_strict(out), "pred_flex": extract_flex(out),
                                "correct_strict": s, "correct_flex": fl,
                                "finish_reason": resp["choices"][0].get("finish_reason"),
                                "completion_tokens": resp["usage"]["completion_tokens"],
                                "prompt_tokens": resp["usage"]["prompt_tokens"],
                                "prompt_n": tm.get("prompt_n"), "prompt_ms": tm.get("prompt_ms"),
                                "predicted_n": tm.get("predicted_n"), "predicted_ms": tm.get("predicted_ms"),
                                "predicted_per_second": tm.get("predicted_per_second"),
                                "e2e_s": round(e2e, 3), "inicio": when, "output": out})
                    f.flush()
                    log(f"  {model} idx={q['idx']:>2} strict={s!s:5} flex={fl!s:5} "
                        f"tok={tm.get('predicted_n')} e2e={e2e:.1f}s")
                t_fim = temp_mc()
                wb.writerow({"bloco": bi, "modelo": model, "idx_ini": a, "idx_fim": b - 1,
                             "repouso_c": t_rest / 1000, "alvo_c": target / 1000,
                             "temp_ini_c": t_ini / 1000, "temp_fim_c": t_fim / 1000, "atingiu_alvo": ok,
                             "espera_s": waited, "load_ini": load_ini, "load_fim": loadavg(), "inicio": ini,
                             "fim": datetime.now().astimezone().isoformat(timespec="seconds")})
                fb.flush()
                log(f"bloco {bi} fim: {t_fim/1000:.1f} °C")
    finally:
        try:
            qbt_resume(active)
        finally:
            ssh(f"{TMUX} tmux kill-session -t llm 2>/dev/null; touch {EXP}/fim; true", check=False)
            log("servidor desligado")
    for p in (OUT_LOCAL, BLOCKS_LOCAL):
        subprocess.run(["timeout", "120", "scp", "-q", "-o", "BatchMode=yes", p,
                        f"ps4:{EXP}/"], check=True)
    log("CSV copiados para o PS4:", OUT_LOCAL, BLOCKS_LOCAL)


if __name__ == "__main__":
    main()
