#!/usr/bin/env python3
"""Tarefa 10: GSM8K completo (1.319 questões) na GPU do PS4, com o cliente rodando no próprio PS4.
Só biblioteca padrão. Mesmo pipeline de geração do run_eval_gpu.py (tarefa 8): mesmo SYSTEM, temperature 0, seed 42,
max_tokens 320, enable_thinking False; servidor build-vulkan com -ngl 99 -c 4096 -t 8 --jinja, mesmo template e mesma
chave; mesmo grading.py. Diferenças operacionais: servidor só em 127.0.0.1:8082 (fora do alcance da LAN/Tailscale),
blocos de 50 questões com resfriamento entre eles, gravação retomável.

Regras de benchmark do PS4 aplicadas:
  - para o chat (tmux llm em /mnt/midia/llm-ps4/chat-gpu) antes e, no finally, religa-o se estava rodando;
  - pausa os torrents ativos e retoma-os no finally (a lista sobrevive a reinícios em qbt_pausados.txt);
  - recusa começar com ffmpeg rodando; repouso de 300 s e resfriamento até repouso + 3 C (máx. 5 min) por bloco;
  - vigia (vigia_full.sh) a cada 10 s: pausa o servidor com >= 85 C e retoma < 75 C; perguntas cujo intervalo cruza
    uma pausa ficam com tempo_valido=False.

Uso (no PS4):  python3 -u run_eval_full.py --ini 0 --fim 1319 --saida resultados_full.csv
Retomável: cada resposta é gravada (flush + fsync) assim que sai; ao reiniciar, os idx já presentes na saída são pulados.
"""
import argparse, csv, fcntl, json, os, signal, subprocess, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from grading import grade, extract_strict, extract_flex  # noqa: E402

ROOT = "/mnt/midia/llm-ps4"
EXP = HERE
MODEL = f"{ROOT}/models/proprios/qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf"
JINJA = f"{ROOT}/models/proprios/chat_template_treinado.jinja"
KEYFILE = os.path.expanduser("~/.config/llm-ps4/api-key")
SERVER_BIN = f"{ROOT}/llama.cpp/build-vulkan/bin/llama-server"
HOST, PORT = "127.0.0.1", 8082
SERVER_ENV = dict(os.environ,
                  VK_DRIVER_FILES=f"{ROOT}/vulkan/mesa-ps4-extract2-20261106-152705/radeon_icd_local.json",
                  MESA_SHADER_CACHE_DIR=f"{EXP}/cache/mesa", XDG_CACHE_HOME=f"{EXP}/cache/xdg", TMPDIR=f"{EXP}/tmp")
SYSTEM = ("Solve the math problem. Reason briefly, step by step. "
          "On the last line, write only the final answer as: #### <number>")
REST_S, COOL_DELTA_MC, COOL_MAX_S, COOL_POLL_S = 300, 3000, 300, 15
BLOCK = 50
CHAT_DIR = f"{ROOT}/chat-gpu"
# Sem a variável TMUX: dentro do tmux do cliente ela apontaria para o socket errado e esconderia o tmux do chat.
CHAT_ENV = {k: v for k, v in os.environ.items() if k != "TMUX"} | {"TMUX_TMPDIR": f"{CHAT_DIR}/tmux", "SHELL": "/bin/bash"}
QBT = "http://127.0.0.1:8080/api/v2/torrents"
F_QBT, F_CHAT, F_EV, F_PID, F_STOPV = (os.path.join(EXP, n) for n in
                                       ("qbt_pausados.txt", "estado_chat.txt", "vigia_eventos.txt", "servidor.pid", "parar_vigia"))
STAMP = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
FIELDS = ["modelo", "bloco", "idx", "gold", "pred_strict", "pred_flex", "correct_strict", "correct_flex",
          "finish_reason", "completion_tokens", "prompt_tokens", "prompt_n", "prompt_ms", "predicted_n",
          "predicted_ms", "predicted_per_second", "e2e_s", "inicio", "tempo_valido", "output"]
BFIELDS = ["bloco", "idx_ini", "idx_fim", "n", "repouso_c", "alvo_c", "temp_ini_c", "temp_fim_c", "atingiu_alvo",
           "espera_s", "load_ini", "load_fim", "inicio", "fim"]


LOGFILE = None  # definido em main(); o log vai direto para arquivo, sem depender de pipe/terminal


def log(*a):
    line = " ".join([datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + [str(x) for x in a])
    if LOGFILE:
        with open(LOGFILE, "a") as f:
            f.write(line + "\n")
    try:
        print(line, flush=True)
    except OSError:  # terminal/tmux já fechado: segue só com o arquivo
        pass


def sh(cmd, env=None, check=False, timeout=60):
    p = subprocess.run(cmd, shell=isinstance(cmd, str), env=env, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"falhou ({p.returncode}): {cmd if isinstance(cmd, str) else ' '.join(cmd)}: {p.stderr.strip()[:300]}")
    return p


def hwmon(name):
    for h in sorted(os.listdir("/sys/class/hwmon")):
        p = f"/sys/class/hwmon/{h}"
        if open(f"{p}/name").read().strip() == name:
            return p
    raise RuntimeError(f"hwmon {name} não encontrado")


K10 = hwmon("k10temp")
temp_mc = lambda: int(open(f"{K10}/temp1_input").read())
loadavg = lambda: " ".join(open("/proc/loadavg").read().split()[:3])


def http(url, data=None, headers=None, timeout=10):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def health(port, timeout=3):
    try:
        return http(f"http://127.0.0.1:{port}/health", timeout=timeout)[0] == 200
    except Exception:
        return False


# ---------- torrents ----------
def qbt_hashes(pred):
    return [t["hash"] for t in json.loads(http(f"{QBT}/info")[1]) if pred(t["state"])]


def qbt_pause():
    stopped = lambda s: s.startswith(("stopped", "paused"))
    prev = open(F_QBT).read().split() if os.path.exists(F_QBT) else []
    active = qbt_hashes(lambda s: not stopped(s))
    allh = sorted(set(prev) | set(active))
    with open(F_QBT, "w") as f:
        f.write("\n".join(allh) + ("\n" if allh else ""))
        f.flush(); os.fsync(f.fileno())
    if active:
        http(f"{QBT}/stop", data=urllib.parse.urlencode({"hashes": "|".join(active)}).encode())
        time.sleep(3)
    still = qbt_hashes(lambda s: not stopped(s))
    log(f"qBittorrent: {len(active)} ativo(s) pausado(s) agora; {len(prev)} já pausado(s) por rodada anterior; ativos restantes: {len(still)}")
    if still:
        raise RuntimeError("ainda há torrents ativos")


def qbt_resume():
    if not os.path.exists(F_QBT):
        log("qBittorrent: nada a retomar"); return
    hs = open(F_QBT).read().split()
    if hs:
        http(f"{QBT}/start", data=urllib.parse.urlencode({"hashes": "|".join(hs)}).encode())
        time.sleep(3)
        parados = len(set(hs) & set(qbt_hashes(lambda s: s.startswith(("stopped", "paused")))))
        log(f"qBittorrent: {len(hs)} retomado(s); ainda parados entre eles: {parados}")
    else:
        log("qBittorrent: 0 retomado(s)")
    os.replace(F_QBT, os.path.join(EXP, f"qbt_retomados_{STAMP}.txt"))


# ---------- chat (tmux llm em chat-gpu) ----------
def chat_running():
    return sh(["tmux", "has-session", "-t", "llm"], env=CHAT_ENV).returncode == 0


def chat_stop():
    if not os.path.exists(F_CHAT):  # guarda o estado ORIGINAL; não sobrescreve num reinício
        with open(F_CHAT, "w") as f:
            f.write("rodando\n" if chat_running() else "parado\n")
    if chat_running():
        sh(["tmux", "kill-session", "-t", "llm"], env=CHAT_ENV, check=True)
        for _ in range(30):
            if not health(8081, 1): break
            time.sleep(1)
        log("chat: tmux llm parado")
    log(f"chat: estado original = {open(F_CHAT).read().strip()}")
    if health(8081, 2):
        raise RuntimeError("chat ainda responde em 127.0.0.1:8081 depois de parado: abortando")


def chat_restore():
    if not os.path.exists(F_CHAT):
        log("chat: sem estado registrado; nada a fazer"); return
    estado = open(F_CHAT).read().strip()
    if estado == "rodando" and not chat_running():
        cmd = open(f"{CHAT_DIR}/comando.txt").read().strip()
        logf = f"{CHAT_DIR}/logs/llama-server_chat_gpu_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
        sh(["tmux", "-f", "/dev/null", "new-session", "-d", "-s", "llm", f"{cmd} 2>&1 | tee -a {logf}"], env=CHAT_ENV, check=True)
        t0 = time.time()
        while time.time() - t0 < 180 and not health(8081):
            time.sleep(2)
        log(f"chat: religado na GPU (tmux llm); /health={'200' if health(8081) else 'SEM RESPOSTA'} em {time.time()-t0:.0f}s")
    else:
        log(f"chat: estado original '{estado}', rodando agora: {chat_running()}; nada a fazer")
    os.replace(F_CHAT, os.path.join(EXP, f"estado_chat_{STAMP}.txt"))


# ---------- vigia e servidor ----------
def vigia_start():
    if os.path.exists(F_STOPV): os.remove(F_STOPV)
    return subprocess.Popen(["bash", os.path.join(EXP, "vigia_full.sh"), EXP], start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def vigia_stop(p):
    open(F_STOPV, "w").close()
    try: p.wait(timeout=30)
    except subprocess.TimeoutExpired: p.kill()


def pausas():
    """Intervalos (ini, fim) de pausa registrados pelo vigia; pausa aberta vai até agora."""
    out, ab = [], None
    if os.path.exists(F_EV):
        for line in open(F_EV):
            p = line.split()
            if len(p) >= 4 and p[3] == "PAUSA": ab = int(p[2])
            elif len(p) >= 4 and p[3].startswith("RETOMADA") and ab is not None: out.append((ab, int(p[2]))); ab = None
    if ab is not None: out.append((ab, time.time()))
    return out


def server_start():
    lf = open(os.path.join(EXP, f"llama-server_{STAMP}.log"), "a")
    p = subprocess.Popen([SERVER_BIN, "-m", MODEL, "-ngl", "99", "-c", "4096", "-t", "8", "--jinja",
                          "--chat-template-file", JINJA, "--host", HOST, "--port", str(PORT), "--api-key-file", KEYFILE],
                         env=SERVER_ENV, stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
    open(F_PID, "w").write(f"{p.pid}\n")
    t0 = time.time()
    while time.time() - t0 < 300:
        if p.poll() is not None: raise RuntimeError(f"servidor saiu com código {p.returncode}")
        if health(PORT): log(f"servidor GPU pronto em {time.time()-t0:.0f}s (127.0.0.1:{PORT}, pid {p.pid})"); return p
        time.sleep(2)
    raise RuntimeError("servidor não ficou pronto em 300 s")


def server_stop(p):
    if p and p.poll() is None:
        os.kill(p.pid, signal.SIGCONT)  # se o vigia o deixou pausado
        p.terminate()
        try: p.wait(timeout=30)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
    if os.path.exists(F_PID): os.remove(F_PID)
    log("servidor da avaliação desligado")


def ask(key, q):
    body = {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}],
            "temperature": 0, "seed": 42, "max_tokens": 320,
            "chat_template_kwargs": {"enable_thinking": False}}
    t0 = time.perf_counter()
    _, raw = http(f"http://{HOST}:{PORT}/v1/chat/completions", data=json.dumps(body).encode(),
                  headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}, timeout=900)
    return json.loads(raw), time.perf_counter() - t0


def wait_cool(target_mc):
    t0 = time.time(); t = temp_mc()
    while t > target_mc and time.time() - t0 < COOL_MAX_S:
        log(f"esperando esfriar: {t/1000:.1f} °C (alvo {target_mc/1000:.1f})")
        time.sleep(COOL_POLL_S); t = temp_mc()
    return t, t <= target_mc, round(time.time() - t0)


def _stop(signum, frame):
    raise SystemExit(f"sinal {signum}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ini", type=int, default=0); ap.add_argument("--fim", type=int, default=1319)
    ap.add_argument("--saida", default="resultados_full.csv")
    a = ap.parse_args()
    global LOGFILE
    out_csv = os.path.join(EXP, a.saida); blocks_csv = out_csv.replace(".csv", "_blocos.csv")
    LOGFILE = out_csv.replace(".csv", ".log")
    lock = open(os.path.join(EXP, ".lock"), "w")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: sys.exit("outra instância já está rodando")
    for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT): signal.signal(s, _stop)
    os.makedirs(f"{EXP}/cache/mesa", exist_ok=True); os.makedirs(f"{EXP}/cache/xdg", exist_ok=True); os.makedirs(f"{EXP}/tmp", exist_ok=True)

    qs = [json.loads(l) for l in open(os.path.join(EXP, "questions_full.jsonl"))]
    assert [q["idx"] for q in qs] == list(range(len(qs))) and len(qs) == 1319
    feitos = set()
    if os.path.exists(out_csv):
        feitos = {int(r["idx"]) for r in csv.DictReader(open(out_csv, newline=""))}
    todo = [q for q in qs[a.ini:a.fim] if q["idx"] not in feitos]
    log(f"faixa {a.ini}-{a.fim-1}: {a.fim-a.ini} questões; já feitas {len(feitos & set(range(a.ini, a.fim)))}; a fazer {len(todo)}; saída {a.saida}")
    if not todo: log("nada a fazer"); return
    if sh("pgrep -a ffmpeg").returncode == 0: sys.exit("ffmpeg rodando: não começo")
    if not os.path.exists(KEYFILE): sys.exit("chave ausente")
    key = open(KEYFILE).read().strip()  # só em memória; nunca é impressa
    t_kernel = int(time.time())

    srv = vig = None
    novo = not os.path.exists(out_csv)
    novob = not os.path.exists(blocks_csv)
    try:
        chat_stop()
        qbt_pause()
        vig = vigia_start()
        log(f"repouso: {REST_S}s com o PS4 ocioso (sem servidor)")
        time.sleep(REST_S)
        t_rest = temp_mc(); target = t_rest + COOL_DELTA_MC
        log(f"repouso: {t_rest/1000:.1f} °C; alvo {target/1000:.1f} °C")
        srv = server_start()
        with open(out_csv, "a", newline="") as f, open(blocks_csv, "a", newline="") as fb:
            w = csv.DictWriter(f, fieldnames=FIELDS); wb = csv.DictWriter(fb, fieldnames=BFIELDS)
            if novo: w.writeheader()
            if novob: wb.writeheader()
            for bi in range(0, len(todo), BLOCK):
                bl = todo[bi:bi + BLOCK]; bnum = bl[0]["idx"] // BLOCK + 1
                t_ini, ok, waited = wait_cool(target)
                load_ini, ini = loadavg(), datetime.now().astimezone().isoformat(timespec="seconds")
                log(f"bloco {bnum}: idx {bl[0]['idx']}-{bl[-1]['idx']} ({len(bl)}), {t_ini/1000:.1f} °C (alvo {target/1000:.1f}, atingiu: {ok}, espera {waited}s)")
                for q in bl:
                    when = datetime.now().astimezone().isoformat(timespec="seconds"); t0 = time.time()
                    resp, e2e = ask(key, q["question"])
                    t1 = time.time()
                    out = resp["choices"][0]["message"].get("content") or ""
                    tm = resp.get("timings", {})
                    s, fl = grade(out, q["gold"])
                    valido = not any(pa - 1 <= t1 and t0 <= pb + 1 for pa, pb in pausas())
                    w.writerow({"modelo": "gpu", "bloco": bnum, "idx": q["idx"], "gold": q["gold"],
                                "pred_strict": extract_strict(out), "pred_flex": extract_flex(out),
                                "correct_strict": s, "correct_flex": fl,
                                "finish_reason": resp["choices"][0].get("finish_reason"),
                                "completion_tokens": resp["usage"]["completion_tokens"],
                                "prompt_tokens": resp["usage"]["prompt_tokens"],
                                "prompt_n": tm.get("prompt_n"), "prompt_ms": tm.get("prompt_ms"),
                                "predicted_n": tm.get("predicted_n"), "predicted_ms": tm.get("predicted_ms"),
                                "predicted_per_second": tm.get("predicted_per_second"),
                                "e2e_s": round(e2e, 3), "inicio": when, "tempo_valido": valido, "output": out})
                    f.flush(); os.fsync(f.fileno())
                    log(f"  idx={q['idx']:>4} strict={s!s:5} flex={fl!s:5} tok={tm.get('predicted_n')} e2e={e2e:.1f}s"
                        + ("" if valido else "  [TEMPO INVÁLIDO: pausa do vigia]"))
                t_fim = temp_mc()
                wb.writerow({"bloco": bnum, "idx_ini": bl[0]["idx"], "idx_fim": bl[-1]["idx"], "n": len(bl),
                             "repouso_c": t_rest / 1000, "alvo_c": target / 1000, "temp_ini_c": t_ini / 1000,
                             "temp_fim_c": t_fim / 1000, "atingiu_alvo": ok, "espera_s": waited, "load_ini": load_ini,
                             "load_fim": loadavg(), "inicio": ini, "fim": datetime.now().astimezone().isoformat(timespec="seconds")})
                fb.flush(); os.fsync(fb.fileno())
                log(f"bloco {bnum} fim: {t_fim/1000:.1f} °C")
    finally:
        for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT, signal.SIGPIPE): signal.signal(s, signal.SIG_IGN)
        for etapa in (lambda: server_stop(srv), lambda: vig and vigia_stop(vig), qbt_resume, chat_restore):
            try: etapa()
            except Exception as e: log(f"ERRO no encerramento: {e!r}")
        k = sh(f"journalctl -k --no-pager --since @{t_kernel} 2>/dev/null | grep -iE 'amdgpu|drm|gpu'").stdout.strip()
        log(f"kernel (amdgpu|drm|gpu) desde o início: {len(k.splitlines()) if k else 0} linha(s)" + (f"\n{k}" if k else ""))
        if os.path.exists(out_csv):
            R = [r for r in csv.DictReader(open(out_csv, newline="")) if a.ini <= int(r["idx"]) < a.fim]
            if R:
                nv = [r for r in R if r["tempo_valido"] == "True"]
                e2e = sum(float(r["e2e_s"]) for r in nv) / len(nv) if nv else float("nan")
                log(f"RESUMO faixa {a.ini}-{a.fim-1}: {len(R)} feitas; strict {sum(r['correct_strict']=='True' for r in R)}; "
                    f"flex {sum(r['correct_flex']=='True' for r in R)}; cortadas {sum(r['finish_reason']=='length' for r in R)}; "
                    f"tempo inválido {len(R)-len(nv)}; s/resposta (válidas) {e2e:.2f}")
        log("FIM")


if __name__ == "__main__":
    main()
