"""E1 — diagnóstico de configuração: a decodificação gulosa (desaconselhada no cartão oficial do Qwen3) explica os ECOS do
literal '#### <number>' e os LAÇOS/cortes em raciocínio longo? Mesmas questões, mesmo modelo, só muda a amostragem.
Dados de investigação (nada de teste final): 300 questões do GSM8K-TREINO (gsm_sel) e 120 itens de BBH do VAL antigo.
Uso: python3 aval/e1_config.py <url> <condição> <saida.jsonl> [--paralelo 4] [--so gsm|bbh]"""
import json, os, re, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI); sys.path.insert(0, os.path.join(AQUI, "..", "runtime")); sys.path.insert(0, os.path.join(AQUI, "..", "..", "weight-edit", "ps4", "wedit-tv15-20261112"))
from cliente import conversa
from grading import grade
from verifica import repeticao
COND = {"guloso": {"temperature": 0, "seed": 42},
        "oficial": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0, "seed": 42},                      # sem raciocínio, cartão do Qwen3
        "oficial_s2": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0, "seed": 7},                   # outra semente: variação da própria amostragem
        "oficial_pp": {"temperature": 0.7, "top_p": 0.8, "top_k": 20, "min_p": 0, "presence_penalty": 1.5, "seed": 42}}
url, cond, saida = sys.argv[1:4]; par = int(sys.argv[sys.argv.index("--paralelo") + 1]) if "--paralelo" in sys.argv else 4; so = sys.argv[sys.argv.index("--so") + 1] if "--so" in sys.argv else None
W = os.path.join(AQUI, "..", "..", "weight-edit", "dados", "splits")
gsm = [json.loads(l) for l in open(os.path.join(W, "gsm_sel.jsonl"))][:300]
bbh = [x for x in (json.loads(l) for l in open(os.path.join(W, "val.jsonl"))) if x["task"].startswith("bbh_")]
itens = ([] if so == "bbh" else gsm) + ([] if so == "gsm" else bbh)
feitos = {json.loads(l)["id"] for l in open(saida)} if os.path.exists(saida) else set(); pend = [x for x in itens if x["id"] not in feitos]; tr = threading.Lock(); n = [0]; t0 = time.time()
print(f"E1 {cond}: {len(itens)} itens, {len(pend)} a fazer", flush=True)
def um(x):
    ms = ([{"role": "system", "content": x["system"]}] if x.get("system") else []) + [{"role": "user", "content": x["prompt"]}]
    try:
        r = conversa(url, ms, amostragem=COND[cond], max_tokens=x.get("max_new", 320), raciocinio=False); t = r["texto"]
        reg = {"id": x["id"], "task": x["task"], "texto": t, "tokens": r["tokens_resposta"], "cortada": r["fim"] == "length", "repeticao": repeticao(t), "eco": bool(re.search(r"####\s*<number>", t))}
        if x["task"] == "gsm8k": st, fl = grade(t, x["gold"]); reg.update(estrito=bool(st), ok=bool(fl))
        else:
            m = re.findall(r"Answer:\s*\**\(?([A-H])\b", t); g = x["gold"] if isinstance(x["gold"], str) else "ABCDEFGH"[x["gold"]]; reg.update(tem_resposta=bool(m), ok=bool(m) and m[-1] == g)
    except Exception as e: reg = {"id": x["id"], "task": x["task"], "erro": repr(e)[:200], "ok": False}
    with tr:
        open(saida, "a").write(json.dumps(reg, ensure_ascii=False) + "\n"); n[0] += 1
        if n[0] % 40 == 0: print(f"{time.strftime('%T')} {n[0]}/{len(pend)} restante ≈ {(time.time() - t0) / n[0] * (len(pend) - n[0]) / 60:.0f} min", flush=True)
with ThreadPoolExecutor(par) as ex: list(ex.map(um, pend))
print("fim", flush=True)
