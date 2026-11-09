#!/usr/bin/env python3
"""Tarefa 11: separar quantização de backend. GSM8K (questions_full.jsonl) no Fedora, CPU (llama.cpp dde879bc,
build-server com as mesmas opções do build/ original), para os arquivos do treinado: Q4_K_M, Q8_0, F16 e Q5_K_M.
Derivado de experiments/gsm8k-full-gpu-20261108/run_eval_full.py v4: mesmo SYSTEM, mesma requisição (temperature 0,
seed 42, max_tokens 320, enable_thinking False), mesmo template, -c 4096, -n 320, mesmo grading.py, timeout de 120 s
com registro e parada no primeiro travamento, servidor novo a cada bloco de 50, gravação retomável.
Sem as partes do PS4 (chat, torrents, vigia, repouso). Servidor só em 127.0.0.1:8090, sem chave. -t 4 (núcleos físicos).
Uso: python3 -u run_quant.py --braco q4km --ini 0 --fim 20 [--saida resultados_q4km.csv]"""
import argparse, csv, fcntl, hashlib, json, os, signal, subprocess, sys, time, traceback, urllib.error, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from grading import grade, extract_strict, extract_flex  # noqa: E402

ROOT = os.path.expanduser("~/LLM-PS4")
SERVER_BIN = f"{ROOT}/gguf/llama.cpp/build-server/bin/llama-server"
JINJA = f"{ROOT}/gguf/out/chat_template_treinado.jinja"
BRACOS = {  # caminho, sha256 de referência (gguf/out/MANIFEST.csv; Q5_K_M: quant-jaguar-20261104/preparation-v4/manifest.csv)
    "q4km": (f"{ROOT}/gguf/out/qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf", "d7771967dc6e5a69a8c676f8d0103763062d44b5b581aa9c707bc60a4684722b"),
    "q8":   (f"{ROOT}/gguf/out/qwen3-1.7b-gsm8k-grpo-Q8_0.gguf", "037c54e893afc4aa12280df84939aba2ae4acb213ef912a4bde133c7800eb36c"),
    "f16":  (f"{ROOT}/gguf/out/qwen3-1.7b-gsm8k-grpo-F16.gguf", "c2ea227a124d02c5873175980b27e675d76782323fee86beba27a0583f1fd06f"),
    "q5km": (f"{ROOT}/experiments/quant-jaguar-20261104/preparation-v4/models/qwen3-1.7b-gsm8k-grpo-Q5_K_M.gguf",
             "366dbe4ccc8d701f3f92e1ea3a2148c8d6527039e0c78d770422b88686a15b95"),
}
HOST, PORT, THREADS = "127.0.0.1", 8090, 4
SYSTEM = ("Solve the math problem. Reason briefly, step by step. "
          "On the last line, write only the final answer as: #### <number>")
BLOCK, TIMEOUT_Q = 50, 120
STAMP = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
FIELDS = ["modelo", "bloco", "idx", "gold", "pred_strict", "pred_flex", "correct_strict", "correct_flex",
          "finish_reason", "completion_tokens", "prompt_tokens", "prompt_n", "prompt_ms", "predicted_n",
          "predicted_ms", "predicted_per_second", "e2e_s", "inicio", "tempo_valido", "output"]
BFIELDS = ["bloco", "idx_ini", "idx_fim", "n", "subida_s", "temp_ini_c", "temp_max_c", "temp_fim_c", "ac_online",
           "load_ini", "load_fim", "inicio", "fim"]
LOGFILE = None


class Travamento(Exception):
    pass


def log(*a):
    line = " ".join([datetime.now().strftime("%Y-%m-%d %H:%M:%S")] + [str(x) for x in a])
    if LOGFILE:
        with open(LOGFILE, "a") as f: f.write(line + "\n")
    try: print(line, flush=True)
    except OSError: pass


def sh(cmd, timeout=30):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def hwmon(name):
    for h in sorted(os.listdir("/sys/class/hwmon")):
        try:
            if open(f"/sys/class/hwmon/{h}/name").read().strip() == name: return f"/sys/class/hwmon/{h}"
        except OSError: pass
    return None


CORE = hwmon("coretemp")
def temp_c():
    try: return int(open(f"{CORE}/temp1_input").read()) / 1000  # Package id 0
    except Exception: return float("nan")
loadavg = lambda: " ".join(open("/proc/loadavg").read().split()[:3])
def ac_online():
    for d in os.listdir("/sys/class/power_supply"):
        if d.startswith(("AC", "ADP")):
            try: return open(f"/sys/class/power_supply/{d}/online").read().strip()
            except OSError: pass
    return "?"


def health(timeout=3):
    try:
        with urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=timeout) as r: return r.status == 200
    except Exception: return False


def server_start(model):
    lf = open(os.path.join(HERE, f"llama-server_{STAMP}.log"), "a")
    p = subprocess.Popen([SERVER_BIN, "-m", model, "-c", "4096", "-n", "320", "-t", str(THREADS), "--jinja",
                          "--chat-template-file", JINJA, "--host", HOST, "--port", str(PORT)],
                         env=dict(os.environ, TMPDIR=os.path.join(HERE, "tmp")), stdout=lf, stderr=subprocess.STDOUT,
                         start_new_session=True)
    t0 = time.time()
    while time.time() - t0 < 300:
        if p.poll() is not None: raise RuntimeError(f"servidor saiu com código {p.returncode}")
        if health(): return p, time.time() - t0
        time.sleep(1)
    raise RuntimeError("servidor não ficou pronto em 300 s")


def server_stop(p):
    if p is None or p.poll() is not None: return True
    p.terminate()
    try: p.wait(timeout=30)
    except subprocess.TimeoutExpired:
        p.kill()
        try: p.wait(timeout=30)
        except subprocess.TimeoutExpired:
            log(f"servidor NÃO saiu nem com SIGKILL (pid {p.pid})"); return False
    return True


def registrar_travamento(motivo, srv):
    f = os.path.join(HERE, f"travamento_{STAMP}.txt")
    partes = [f"# travamento {datetime.now().astimezone().isoformat(timespec='seconds')}: {motivo}"]
    for titulo, c in (("processos em estado D", "ps -eo pid,stat,wchan:40,etime,cmd | awk 'NR==1 || $2 ~ /D/'"),
                      ("servidor", f"ps -o pid,stat,wchan:40,etime,cmd -p {srv.pid if srv else 0}"),
                      ("log do servidor (últimas 30)", f"tail -30 {HERE}/llama-server_{STAMP}.log")):
        try: out = sh(c).stdout
        except Exception as e: out = f"(falhou: {e!r})"
        partes.append(f"\n===== {titulo} =====\n$ {c}\n{out}")
    open(f, "w").write("\n".join(partes)); log(f"TRAVAMENTO registrado em {os.path.basename(f)}")


def ask(q):
    body = {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": q}],
            "temperature": 0, "seed": 42, "max_tokens": 320,
            "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(f"http://{HOST}:{PORT}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=TIMEOUT_Q) as r:
        resp = json.load(r)
    return resp, time.perf_counter() - t0


def _stop(signum, frame):
    raise SystemExit(f"sinal {signum}")


def main():
    global LOGFILE
    ap = argparse.ArgumentParser()
    ap.add_argument("--braco", required=True, choices=sorted(BRACOS))
    ap.add_argument("--ini", type=int, default=0); ap.add_argument("--fim", type=int, default=1319)
    ap.add_argument("--saida", default=None)
    a = ap.parse_args()
    model, ref = BRACOS[a.braco]
    out_csv = os.path.join(HERE, a.saida or f"resultados_{a.braco}.csv")
    blocks_csv = out_csv.replace(".csv", "_blocos.csv"); LOGFILE = out_csv.replace(".csv", ".log")
    lock = open(os.path.join(HERE, ".lock"), "w")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: sys.exit("outra instância já está rodando (um braço por vez, para não misturar tempos)")
    for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT): signal.signal(s, _stop)
    os.makedirs(os.path.join(HERE, "tmp"), exist_ok=True)

    qs = [json.loads(l) for l in open(os.path.join(HERE, "questions_full.jsonl"))]
    assert [q["idx"] for q in qs] == list(range(1319))
    feitos = {int(r["idx"]) for r in csv.DictReader(open(out_csv, newline=""))} if os.path.exists(out_csv) else set()
    todo = [q for q in qs[a.ini:a.fim] if q["idx"] not in feitos]
    log(f"braço {a.braco}: faixa {a.ini}-{a.fim-1}; já feitas {len(feitos & set(range(a.ini, a.fim)))}; a fazer {len(todo)}; saída {os.path.basename(out_csv)}")
    if not todo: log("nada a fazer"); return
    got = sha256(model)
    if got != ref: sys.exit(f"SHA256 do modelo não confere: {got}")
    log(f"modelo {os.path.basename(model)}: SHA256 OK; AC={ac_online()}; temp={temp_c():.1f} °C; load={loadavg()}")

    srv = None; travou = False
    novo, novob = not os.path.exists(out_csv), not os.path.exists(blocks_csv)
    try:
        with open(out_csv, "a", newline="") as f, open(blocks_csv, "a", newline="") as fb:
            w = csv.DictWriter(f, fieldnames=FIELDS); wb = csv.DictWriter(fb, fieldnames=BFIELDS)
            if novo: w.writeheader()
            if novob: wb.writeheader()
            for bi in range(0, len(todo), BLOCK):
                bl = todo[bi:bi + BLOCK]; bnum = bl[0]["idx"] // BLOCK + 1
                if not server_stop(srv):
                    travou = True; registrar_travamento(f"servidor anterior não saiu (bloco {bnum})", srv); raise Travamento("servidor preso")
                srv, sub = server_start(model)
                t_ini, tmax = temp_c(), temp_c(); load_ini = loadavg(); ini = datetime.now().astimezone().isoformat(timespec="seconds")
                log(f"bloco {bnum}: idx {bl[0]['idx']}-{bl[-1]['idx']} ({len(bl)}); servidor (re)iniciado, subida {sub:.1f}s; {t_ini:.1f} °C; AC={ac_online()}")
                for q in bl:
                    when = datetime.now().astimezone().isoformat(timespec="seconds"); t0 = time.time()
                    try:
                        resp, e2e = ask(q["question"])
                    except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
                        travou = True
                        registrar_travamento(f"idx {q['idx']} sem resposta em {time.time()-t0:.0f}s ({e!r})", srv)
                        raise Travamento(f"idx {q['idx']}: {e!r}") from e
                    out = resp["choices"][0]["message"].get("content") or ""
                    tm = resp.get("timings", {}); s, fl = grade(out, q["gold"]); tmax = max(tmax, temp_c())
                    w.writerow({"modelo": a.braco, "bloco": bnum, "idx": q["idx"], "gold": q["gold"],
                                "pred_strict": extract_strict(out), "pred_flex": extract_flex(out),
                                "correct_strict": s, "correct_flex": fl,
                                "finish_reason": resp["choices"][0].get("finish_reason"),
                                "completion_tokens": resp["usage"]["completion_tokens"],
                                "prompt_tokens": resp["usage"]["prompt_tokens"],
                                "prompt_n": tm.get("prompt_n"), "prompt_ms": tm.get("prompt_ms"),
                                "predicted_n": tm.get("predicted_n"), "predicted_ms": tm.get("predicted_ms"),
                                "predicted_per_second": tm.get("predicted_per_second"),
                                "e2e_s": round(e2e, 3), "inicio": when, "tempo_valido": True, "output": out})
                    f.flush(); os.fsync(f.fileno())
                    log(f"  idx={q['idx']:>4} strict={s!s:5} flex={fl!s:5} tok={tm.get('predicted_n')} e2e={e2e:.1f}s")
                wb.writerow({"bloco": bnum, "idx_ini": bl[0]["idx"], "idx_fim": bl[-1]["idx"], "n": len(bl), "subida_s": round(sub, 1),
                             "temp_ini_c": t_ini, "temp_max_c": tmax, "temp_fim_c": temp_c(), "ac_online": ac_online(),
                             "load_ini": load_ini, "load_fim": loadavg(), "inicio": ini,
                             "fim": datetime.now().astimezone().isoformat(timespec="seconds")})
                fb.flush(); os.fsync(fb.fileno())
                log(f"bloco {bnum} fim: {temp_c():.1f} °C (máx {tmax:.1f})")
    except BaseException as e:
        log(f"EXCEÇÃO: {e!r}\n" + "".join(traceback.format_exception(e)).rstrip())
        raise
    finally:
        for s in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT, signal.SIGPIPE): signal.signal(s, signal.SIG_IGN)
        try:
            server_stop(srv); log("servidor desligado")
        except Exception as e:
            log(f"ERRO ao desligar o servidor: {e!r}")
        if os.path.exists(out_csv):
            R = [r for r in csv.DictReader(open(out_csv, newline="")) if a.ini <= int(r["idx"]) < a.fim]
            if R:
                log(f"RESUMO {a.braco} faixa {a.ini}-{a.fim-1}: {len(R)} feitas; strict {sum(r['correct_strict']=='True' for r in R)}; "
                    f"flex {sum(r['correct_flex']=='True' for r in R)}; cortadas {sum(r['finish_reason']=='length' for r in R)}; "
                    f"s/resposta {sum(float(r['e2e_s']) for r in R)/len(R):.2f}; tok/s geração "
                    f"{sum(float(r['predicted_n']) for r in R)/sum(float(r['predicted_ms']) for r in R)*1000:.2f}"
                    + ("; TRAVOU" if travou else ""))
        log("FIM")


if __name__ == "__main__":
    main()
