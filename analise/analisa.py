#!/usr/bin/env python3
"""Análise de erros (só leitura dos CSVs). Gera números para o relatorio.md em analise_dados.json
e imprime um resumo. Uso: ~/LLM-PS4/gguf/.venv/bin/python -I analisa.py"""
import csv, json, re, statistics, random, os
from collections import Counter
from tokenizers import Tokenizer

HERE = os.path.dirname(os.path.abspath(__file__))
TOK = Tokenizer.from_file(os.path.expanduser("~/LLM-PS4/gguf/hf/qwen3-1.7b-gsm8k-grpo/tokenizer.json"))
ntok = lambda s: len(TOK.encode(s, add_special_tokens=False).ids) if s else 0


def load(n):
    return {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, f"eval/eval_{n}.csv")))}


B, G = load("base"), load("grpo")
T = lambda r, k: r[k] == "True"
out = {}

# ---------- a/b: repetição ----------
def rep8(text, n=8):
    w = text.split()
    grams = Counter(tuple(w[i:i + n]) for i in range(len(w) - n + 1))
    reps = {g: c for g, c in grams.items() if c >= 2}
    return reps


def maxrun_lines(text):
    """maior número de vezes que uma mesma linha não-vazia aparece"""
    c = Counter(l.strip() for l in text.splitlines() if len(l.strip()) > 3)
    return max(c.values()) if c else 0


def loop_info(text):
    reps = rep8(text)
    top = max(reps.items(), key=lambda kv: kv[1]) if reps else None
    return {"n_8grams_repetidos": len(reps), "max_rep_8gram": top[1] if top else 0,
            "8gram_mais_repetido": " ".join(top[0]) if top else "", "max_linha_repetida": maxrun_lines(text)}


for name, D in (("base", B), ("grpo", G)):
    tr = [i for i, r in D.items() if T(r, "truncated")]
    out[f"trunc_{name}"] = {"n": len(tr), "idx": tr,
                            "flex_ok": sum(T(D[i], "correct_flex") for i in tr),
                            "com_loop(8gram>=3x)": sum(loop_info(D[i]["output"])["max_rep_8gram"] >= 3 for i in tr),
                            "com_rep8": sum(bool(rep8(D[i]["output"])) for i in tr)}
    has = [i for i, r in D.items() if rep8(r["output"])]
    loop3 = [i for i, r in D.items() if loop_info(r["output"])["max_rep_8gram"] >= 3]
    out[f"rep_{name}"] = {"n_com_rep8": len(has), "pct": round(100 * len(has) / len(D), 1),
                          "n_rep8_3x_ou_mais": len(loop3),
                          "rep8_entre_trunc": sum(T(D[i], "truncated") for i in has),
                          "flex_acc_com_rep": round(sum(T(D[i], "correct_flex") for i in has) / max(1, len(has)), 3),
                          "flex_acc_sem_rep": round(sum(T(D[i], "correct_flex") for i in D if i not in set(has)) / (len(D) - len(has)), 3)}
    # o que mais se repete (n-gramas de 8 repetidos dentro da mesma resposta)
    cg = Counter()
    for i in has:
        for g in rep8(D[i]["output"]):
            cg[" ".join(g)] += 1
    out[f"rep_{name}"]["top_8grams"] = cg.most_common(8)

out["trunc_grpo_detalhe"] = [{"idx": i, "gold": G[i]["gold"], "n_tokens": G[i]["n_tokens"],
                              "correct_flex": G[i]["correct_flex"], **loop_info(G[i]["output"]),
                              "output": G[i]["output"]} for i in out["trunc_grpo"]["idx"]]

# ---------- c: desperdício ----------
FINAL = re.compile(r"####\s*\$?-?[\d,]*\.?\d+\$?")


def after_final(text):
    m = list(FINAL.finditer(text))
    return text[m[-1].end():] if m else None


MATH = re.compile(r"[\d=+\-×*/÷^%$\\]")


def classify_line(line, question):
    s = line.strip()
    if not s or re.fullmatch(r"[#*\-\s]*", s):
        return None
    if s.startswith("####"):
        return None
    if MATH.search(s):
        return None
    qw = set(re.findall(r"[a-z']+", question.lower()))
    lw = re.findall(r"[a-z']+", s.lower())
    if len(lw) >= 5 and sum(w in qw for w in lw) / len(lw) >= 0.7:
        return "reenuncia"
    return "texto_sem_conta"


def norm_line(s):
    s = re.sub(r"^[\s#*\-\d.)]+", "", s.strip()).strip("*: ").lower()
    return s


for name, D in (("base", B), ("grpo", G)):
    aft = [after_final(r["output"]) for r in D.values()]
    with_final = [a for a in aft if a is not None]
    nonempty = [a for a in with_final if a.strip()]
    lines_c, tok_by_cat = Counter(), Counter()
    per_resp = []
    for r in D.values():
        t = 0
        for l in r["output"].splitlines():
            c = classify_line(l, r["question"])
            if c:
                k = ntok(l + "\n")
                tok_by_cat[c] += k
                t += k
                lines_c[norm_line(l)] += 1
        per_resp.append(t)
    nt = [int(r["n_tokens"]) for r in D.values()]
    out[f"desperdicio_{name}"] = {
        "com_####_final": len(with_final),
        "algo_depois_do_####": len(nonempty),
        "exemplos_depois": Counter(a.strip()[:60] for a in nonempty).most_common(6),
        "tokens_depois_media_global": round(sum(ntok(a) for a in nonempty) / len(D), 2),
        "tokens_sem_conta_por_resposta_media": round(statistics.mean(per_resp), 1),
        "tokens_sem_conta_mediana": statistics.median(per_resp),
        "pct_dos_tokens_gerados": round(100 * sum(per_resp) / sum(nt), 1),
        "tokens_por_categoria_por_resposta": {k: round(v / len(D), 1) for k, v in tok_by_cat.items()},
        "linhas_mais_comuns": lines_c.most_common(15),
    }
    # aberturas: primeira linha
    first = Counter(norm_line(r["output"].strip().splitlines()[0])[:70] for r in D.values() if r["output"].strip())
    out[f"desperdicio_{name}"]["primeiras_linhas"] = first.most_common(8)
    lets = [r for r in D.values() if re.match(r"\s*let'?s (solve|break)", r["output"], re.I)]
    out[f"desperdicio_{name}"]["abre_com_lets_solve_break"] = {
        "n": len(lets), "tokens_da_linha_media": round(statistics.mean(ntok(r["output"].strip().splitlines()[0]) for r in lets), 1) if lets else 0}


# ---------- d: tamanho ----------
def stats(v):
    v = sorted(v)
    p90 = v[min(len(v) - 1, int(round(0.9 * (len(v) - 1))))]
    return {"n": len(v), "media": round(statistics.mean(v), 1), "mediana": statistics.median(v), "p90": p90,
            "min": v[0], "max": v[-1]}


for name, D in (("grpo", G), ("base", B)):
    ok = [int(r["n_tokens"]) for r in D.values() if T(r, "correct_flex")]
    er = [int(r["n_tokens"]) for r in D.values() if not T(r, "correct_flex")]
    out[f"tamanho_{name}"] = {"acertos": stats(ok), "erros": stats(er), "todos": stats(ok + er)}
    bins = [0, 50, 100, 150, 200, 250, 319, 320]
    hist = []
    for lo, hi in zip(bins, bins[1:]):
        sel = [r for r in D.values() if lo < int(r["n_tokens"]) <= hi]
        hist.append({"faixa": f"{lo + 1}-{hi}", "n": len(sel),
                     "acc_flex": round(sum(T(r, "correct_flex") for r in sel) / len(sel), 3) if sel else None})
    out[f"tamanho_{name}"]["hist"] = hist

# ---------- e: amostra de erros ----------
err = sorted(i for i, r in G.items() if not T(r, "correct_flex"))
random.seed(20261103)
amostra = sorted(random.sample(err, 40))
out["amostra_erros"] = {"semente": 20261103, "n_erros": len(err), "idx": amostra}
json.dump([{"idx": i, "question": G[i]["question"], "gold": G[i]["gold"], "n_tokens": G[i]["n_tokens"],
            "truncated": G[i]["truncated"], "strict": G[i]["correct_strict"], "output": G[i]["output"],
            "base_flex": B[i]["correct_flex"]} for i in amostra],
          open(os.path.join(HERE, "amostra_erros.json"), "w"), ensure_ascii=False, indent=1)

# ---------- f: base acertava / treinado errou e vice-versa ----------
KW = {"porcentagem": r"%|percent", "fração": r"\bhalf\b|\bthird\b|quarter|\d+/\d+|fraction",
      "dinheiro": r"\$|dollar|cents?\b|price|cost|pay|earn",
      "tempo": r"\bhours?\b|minutes?|\bdays?\b|weeks?|months?|years?",
      "taxa/velocidade": r"per (hour|minute|day)|mph|miles per|speed|rate",
      "comparação (more/less/times)": r"\bmore than\b|\bless than\b|\btimes as\b|twice|fewer"}


def feats(i):
    q = G[i]["question"]
    return {"q_palavras": len(q.split()), "q_numeros": len(re.findall(r"\d+(?:\.\d+)?", q)),
            "gold_abs": abs(float(G[i]["gold"].replace(",", ""))),
            "tok_base": int(B[i]["n_tokens"]), "tok_grpo": int(G[i]["n_tokens"]),
            "trunc_base": T(B[i], "truncated"), "trunc_grpo": T(G[i], "truncated"),
            **{k: bool(re.search(p, q, re.I)) for k, p in KW.items()}}


groups = {
    "base_ok_grpo_erro": [i for i in G if T(B[i], "correct_flex") and not T(G[i], "correct_flex")],
    "base_erro_grpo_ok": [i for i in G if not T(B[i], "correct_flex") and T(G[i], "correct_flex")],
    "ambos_ok": [i for i in G if T(B[i], "correct_flex") and T(G[i], "correct_flex")],
    "ambos_erro": [i for i in G if not T(B[i], "correct_flex") and not T(G[i], "correct_flex")],
}
fsum = {}
for gname, ids in groups.items():
    F = [feats(i) for i in ids]
    d = {"n": len(ids)}
    for k in ["q_palavras", "q_numeros", "tok_base", "tok_grpo"]:
        d[k + "_media"] = round(statistics.mean(f[k] for f in F), 1)
        d[k + "_mediana"] = statistics.median(f[k] for f in F)
    d["gold_mediana"] = statistics.median(f["gold_abs"] for f in F)
    for k in ["trunc_base", "trunc_grpo", *KW]:
        d[k + "_pct"] = round(100 * sum(f[k] for f in F) / len(F), 1)
    fsum[gname] = d
out["flips"] = fsum
out["flips_idx"] = {k: v for k, v in groups.items() if k.startswith("base_")}
# nas trocas: o grpo errou porque não deu resposta (cortado / sem número) ou deu um número errado?
for gname in ["base_ok_grpo_erro", "base_erro_grpo_ok"]:
    ids = groups[gname]
    lose = "grpo" if gname == "base_ok_grpo_erro" else "base"
    D = G if lose == "grpo" else B
    out["flips"][gname]["perdedor_cortado"] = sum(T(D[i], "truncated") for i in ids)
    out["flips"][gname]["delta_tokens_grpo_menos_base_mediana"] = statistics.median(
        int(G[i]["n_tokens"]) - int(B[i]["n_tokens"]) for i in ids)
json.dump(groups, open(os.path.join(HERE, "flips_idx.json"), "w"))

json.dump(out, open(os.path.join(HERE, "analise_dados.json"), "w"), ensure_ascii=False, indent=1)
skip = {"trunc_grpo_detalhe", "flips_idx"}
print(json.dumps({k: v for k, v in out.items() if k not in skip}, ensure_ascii=False, indent=1)[:20000])
