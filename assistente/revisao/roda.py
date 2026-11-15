"""Executa a avaliação do assistente contra um llama-server (notebook ou PS4) e grava um JSONL por item (retomável).
Uso: python3 aval/roda.py --config configs/X.json --url http://127.0.0.1:8090 --divisao dev --saida aval/resultados/X_dev.jsonl
       [--paralelo 4] [--categorias a,b] [--limite N] [--chave ARQ] [--pid-servidor PID]
Mede por item: acerto pelas verificações objetivas, idioma, repetição, resposta vazia/cortada, tempo até o primeiro token,
tempo total, tokens de prompt e de resposta; e a memória residente do servidor (se --pid-servidor)."""
import argparse, json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI); sys.path.insert(0, os.path.join(AQUI, "..", "runtime"))
from verifica import avalia
from assistente import carrega_config, responde

ap = argparse.ArgumentParser(); ap.add_argument("--config", required=True); ap.add_argument("--url", required=True); ap.add_argument("--divisao", default="dev")
ap.add_argument("--saida", required=True); ap.add_argument("--paralelo", type=int, default=1); ap.add_argument("--categorias"); ap.add_argument("--limite", type=int)
ap.add_argument("--max-segundos", type=int, help="para de pegar itens novos depois desse tempo (sai com código 4 se sobrar item)"); ap.add_argument("--tempo-limite-item", type=int, default=300, help="segundos sem receber nada do servidor = travamento (sai com código 3)")
ap.add_argument("--por-categoria", type=int, help="só os primeiros K itens de cada categoria (triagem rápida)"); ap.add_argument("--chave"); ap.add_argument("--pid-servidor", type=int); ap.add_argument("--itens", default=os.path.join(AQUI, "itens")); a = ap.parse_args()
cfg = carrega_config(a.config); cfg["tempo_limite_s"] = a.tempo_limite_item; chave = open(a.chave).read().strip() if a.chave else None
div = json.load(open(os.path.join(AQUI, "divisao.json")))[a.divisao] if a.divisao != "todos" else None
itens = []
for f in sorted(os.listdir(a.itens)):
    if f.endswith(".jsonl"):
        itens += [json.loads(l) for l in open(os.path.join(a.itens, f), encoding="utf-8") if l.strip()]
itens = [x for x in itens if (div is None or x["id"] in set(div)) and (not a.categorias or x["categoria"] in a.categorias.split(","))]
if a.limite: itens = itens[:a.limite]
if a.por_categoria:
    _c = {}; itens = [x for x in itens if _c.setdefault(x["categoria"], 0) < a.por_categoria and not _c.update({x["categoria"]: _c[x["categoria"]] + 1})]
feitos = {json.loads(l)["id"] for l in open(a.saida, encoding="utf-8")} if os.path.exists(a.saida) else set()
pend = [x for x in itens if x["id"] not in feitos]; trava = threading.Lock(); t0 = time.time(); n = [0]
print(f"config {cfg['nome']} | divisão {a.divisao} | {len(itens)} itens, {len(feitos)} já feitos, {len(pend)} a fazer | {a.url}", flush=True)


def rss_mb():
    try:
        s = open(f"/proc/{a.pid_servidor}/status").read(); g = lambda k: int(s.split(k + ":")[1].split()[0]) // 1024
        return {"rss_mb": g("VmRSS"), "pico_mb": g("VmHWM")}
    except Exception: return {}


def um(it):
    reg = {"id": it["id"], "categoria": it["categoria"], "subtipo": it.get("subtipo"), "config": cfg["nome"]}
    try:
        r = responde(cfg, a.url, it["mensagens"], it.get("documentos"), it.get("fixtures"), it.get("max_tokens", 400), chave)
        av = avalia(it, r["texto"])
        reg.update(resposta=r["texto"], raciocinio_chars=len(r["raciocinio"]), fim=r["fim"], cortada=r["fim"] == "length", t_primeiro=r["t_primeiro"], t_primeiro_texto=r["t_primeiro_texto"],
                   t_total=r["t_total"], tokens_prompt=r["tokens_prompt"], tokens_resposta=r["tokens_resposta"], tokens_prompt_total=r.get("tokens_prompt_total"), tokens_resposta_total=r.get("tokens_resposta_total"), tempos=r["tempos"], rastro=r["rastro"], **av)
    except Exception as e:
        reg.update(ok=False, erro=repr(e)[:300]); reg["travamento"] = "timed out" in repr(e).lower() or "timeout" in repr(e).lower()
    reg.update(rss_mb() if a.pid_servidor else {})
    with trava:
        open(a.saida, "a", encoding="utf-8").write(json.dumps(reg, ensure_ascii=False) + "\n"); n[0] += 1
        if n[0] % 10 == 0 or n[0] == len(pend):
            dt = time.time() - t0; print(f"{time.strftime('%H:%M:%S')} {n[0]}/{len(pend)} em {dt / 60:.1f} min; restante ≈ {dt / n[0] * (len(pend) - n[0]) / 60:.0f} min", flush=True)


if a.paralelo > 1 and not a.max_segundos:
    with ThreadPoolExecutor(a.paralelo) as ex: list(ex.map(um, pend))
else:  # sequencial: permite blocos por tempo e parada no primeiro travamento (protocolo do PS4)
    for k, it in enumerate(pend):
        if a.max_segundos and time.time() - t0 > a.max_segundos:
            print(f"RESTAM {len(pend) - k} (limite de tempo do bloco)", flush=True); sys.exit(4)
        um(it)
        ult = json.loads(open(a.saida, encoding="utf-8").read().strip().split("\n")[-1])
        if ult.get("travamento"): print(f"TRAVAMENTO em {it['id']}", flush=True); sys.exit(3)
print("fim", flush=True)
