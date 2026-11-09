#!/usr/bin/env python3
"""Resumo da medição no PS4. Uso: python3 resumo.py ps4_eval_<stamp>.csv"""
import csv, sys, statistics as st, os

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1]
R = list(csv.DictReader(open(path)))
by = {m: {int(r["idx"]): r for r in R if r["modelo"] == m} for m in ("base", "treinado")}
assert all(len(v) == 100 for v in by.values()), {k: len(v) for k, v in by.items()}
T = lambda r, k: r[k] == "True"
f = lambda r, k: float(r[k])

out = []
w = out.append
w("| | base | treinado |\n|---|---|---|")
rows = {}
for m, D in by.items():
    v = list(D.values())
    nf, ns = sum(T(r, "correct_flex") for r in v), sum(T(r, "correct_strict") for r in v)
    e2e = sum(f(r, "e2e_s") for r in v)
    rows[m] = {
        "acerto strict": f"{ns}%", "acerto flex": f"{nf}%",
        "tokens por resposta (média / mediana)": f"{st.mean(f(r,'predicted_n') for r in v):.1f} / {st.median(f(r,'predicted_n') for r in v):.0f}",
        "cortadas (320)": str(sum(r["finish_reason"] == "length" for r in v)),
        "tokens de prompt processados (média)": f"{st.mean(f(r,'prompt_n') for r in v):.1f}",
        "tempo de prompt por resposta (s)": f"{st.mean(f(r,'prompt_ms') for r in v)/1000:.2f}",
        "tempo de geração por resposta (s)": f"{st.mean(f(r,'predicted_ms') for r in v)/1000:.2f}",
        "geração tokens/s (total tokens ÷ total tempo)": f"{sum(f(r,'predicted_n') for r in v)/sum(f(r,'predicted_ms') for r in v)*1000:.2f}",
        "segundos por resposta (ponta a ponta)": f"{e2e/len(v):.2f}",
        "segundos por resposta correta (flex)": f"{e2e/nf:.2f}",
    }
for k in rows["base"]:
    w(f"| {k} | {rows['base'][k]} | {rows['treinado'][k]} |")

B, G = by["base"], by["treinado"]
bo = sorted(i for i in B if T(B[i], "correct_flex") and not T(G[i], "correct_flex"))
go = sorted(i for i in B if not T(B[i], "correct_flex") and T(G[i], "correct_flex"))
w(f"\n**Trocas (flex):** base acerta e treinado erra em {len(bo)} ({', '.join(map(str, bo))}); "
  f"treinado acerta e base erra em {len(go)} ({', '.join(map(str, go))}). "
  f"Ambos acertam {sum(T(B[i],'correct_flex') and T(G[i],'correct_flex') for i in B)}, ambos erram {sum(not T(B[i],'correct_flex') and not T(G[i],'correct_flex') for i in B)}.")

# Kaggle
K = {}
for m, fn in (("base", "eval_base.csv"), ("treinado", "eval_grpo.csv")):
    K[m] = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "hf/eval", fn))) if int(r["idx"]) < 100}
w("\n**PS4 (Q4_K_M, llama.cpp) × Kaggle (mesmas 100 questões):**\n")
w("| | flex PS4 | flex Kaggle | strict PS4 | strict Kaggle | mesma correção (flex) nas 100 | saída idêntica | tokens PS4 / Kaggle (média) |\n|---|---|---|---|---|---|---|---|")
for m in ("base", "treinado"):
    P, Q = by[m], K[m]
    same = sum(T(P[i], "correct_flex") == T(Q[i], "correct_flex") for i in P)
    ident = sum(P[i]["output"].strip() == Q[i]["output"].strip() for i in P)
    w(f"| {m} | {sum(T(r,'correct_flex') for r in P.values())} | {sum(T(r,'correct_flex') for r in Q.values())} | "
      f"{sum(T(r,'correct_strict') for r in P.values())} | {sum(T(r,'correct_strict') for r in Q.values())} | {same}/100 | {ident}/100 | "
      f"{st.mean(f(r,'predicted_n') for r in P.values()):.1f} / {st.mean(f(r,'n_tokens') for r in Q.values()):.1f} |")
notes = []
for m in ("base", "treinado"):
    P, Q = by[m], K[m]
    pk = sorted(i for i in P if T(P[i], "correct_flex") and not T(Q[i], "correct_flex"))
    kp = sorted(i for i in P if not T(P[i], "correct_flex") and T(Q[i], "correct_flex"))
    notes.append(f"- {m}: só o PS4 acerta {pk}; só o Kaggle acerta {kp}")
w("")
out.extend(notes)

bl = list(csv.DictReader(open(path.replace(".csv", "_blocos.csv"))))
w("\n**Temperatura (k10temp) por bloco:**\n")
w("| bloco | modelo | início (°C) | fim (°C) | alvo (°C) | atingiu | espera (s) |\n|---|---|---|---|---|---|---|")
for b in bl:
    w(f"| {b['bloco']} | {b['modelo']} | {b['temp_ini_c']} | {b['temp_fim_c'] or '—'} | {b['alvo_c']} | {b['atingiu_alvo'] or '—'} | {b['espera_s']} |")
# velocidade por bloco
w("\n**Geração tokens/s por bloco:** " + ", ".join(
    f"bloco {b}: {sum(f(r,'predicted_n') for r in R if r['bloco']==str(b))/sum(f(r,'predicted_ms') for r in R if r['bloco']==str(b))*1000:.2f}"
    for b in (1, 2, 3, 4)))
print("\n".join(out))
open(path.replace(".csv", "_resumo.md"), "w").write("\n".join(out) + "\n")
