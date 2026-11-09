#!/usr/bin/env python3
"""Tarefa 11, braço Q4_K_M no Fedora (CPU, llama.cpp dde879bc): métricas e comparações pareadas.
Contra: Kaggle (eval_grpo.csv, v1 precisão cheia; pareado pelo texto da pergunta e recorrigido com o mesmo grading.py),
GPU do PS4 (gsm8k-full-gpu-20261108, mesmo questions_full.jsonl, pareado por idx) e, nas questões 0–99, a CPU do PS4
(tarefa 8). Regra de decisão (manifest.csv): igual = |Δflex| <= 1,5 ponto E McNemar exato p > 0,05.
Mesmas definições de métrica do resumo.py de 03/11. Uso: python3 analise_q4km.py  -> resultado_q4km.md"""
import csv, json, math, os, statistics as st, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from grading import grade  # noqa: E402

Z = 1.959963984540054
T = lambda r, k: r[k] == "True"
f = lambda r, k: float(r[k])


def wilson(k, n):
    p = k / n; den = 1 + Z**2 / n
    c = (p + Z**2 / (2 * n)) / den; h = Z * math.sqrt(p * (1 - p) / n + Z**2 / (4 * n**2)) / den
    return c - h, c + h


def mcnemar(b, c):
    n, m = b + c, min(b, c)
    return min(1.0, 2 * sum(math.comb(n, j) for j in range(m + 1)) / 2**n) if n else 1.0


def newcombe(a, b, c, d):
    n = a + b + c + d; p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n); l2, u2 = wilson(a + c, n)
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d)); num = a * d - b * c
    phi = 0.0 if den == 0 else (max(num - n / 2, 0) if num > 0 else num) / den
    dl = p1 - p2
    lo = dl - math.sqrt(max((p1 - l1)**2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2)**2, 0))
    hi = dl + math.sqrt(max((u1 - p1)**2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2)**2, 0))
    return dl, lo, hi


def comparar(pares, nome_a, nome_b):
    """pares: lista de (acerto_a: dict strict/flex, acerto_b: dict). Devolve linhas da tabela e o resultado flex."""
    linhas, res = [], {}
    n = len(pares)
    for k in ("strict", "flex"):
        a = sum(x[k] and y[k] for x, y in pares); b = sum(x[k] and not y[k] for x, y in pares)
        c = sum(y[k] and not x[k] for x, y in pares); d = n - a - b - c
        dl, lo, hi = newcombe(a, b, c, d); p = mcnemar(b, c)
        res[k] = (dl, lo, hi, p, b, c, a + d)
        linhas.append(f"| {k} | {a+b}/{n} ({100*(a+b)/n:.1f}%) | {a+c}/{n} ({100*(a+c)/n:.1f}%) | {b} / {c} | {p:.3g} | "
                      f"{100*dl:+.1f} ({100*lo:+.1f} a {100*hi:+.1f}) | {a+d}/{n} |")
    cab = (f"| | {nome_a} | {nome_b} | só {nome_a} acerta / só {nome_b} acerta | McNemar exato (p) | "
           f"{nome_a} − {nome_b} (pontos, IC95% Newcombe) | mesmo veredito |\n|---|---|---|---|---|---|---|")
    return cab, linhas, res


def regra(res):
    dl, lo, hi, p, b, c, same = res["flex"]
    igual = abs(100 * dl) <= 1.5 and p > 0.05
    det = f"Δflex = {100*dl:+.1f} pts, McNemar p = {p:.3g}"
    if igual: return f"**igual** ({det}: |Δ| ≤ 1,5 e p > 0,05)"
    motivos = ([f"|Δ| = {abs(100*dl):.1f} > 1,5"] if abs(100 * dl) > 1.5 else []) + (["p ≤ 0,05"] if p <= 0.05 else [])
    return f"**não igual** ({det}; falha: {' e '.join(motivos)})"


Q = {q["idx"]: q for q in map(json.loads, open(os.path.join(HERE, "questions_full.jsonl")))}
F = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "resultados_q4km.csv"), newline=""))}
assert sorted(F) == list(range(1319)), f"faltam questões: {1319 - len(F)}"
acc = lambda r: {"strict": T(r, "correct_strict"), "flex": T(r, "correct_flex")}
out = []; w = out.append
v = list(F.values()); n = len(v); ns, nf = sum(T(r, "correct_strict") for r in v), sum(T(r, "correct_flex") for r in v)
pct = lambda k: f"{k}/{n} = {100*k/n:.1f}% (IC95% {100*wilson(k, n)[0]:.1f}–{100*wilson(k, n)[1]:.1f})"
e2e = sum(f(r, "e2e_s") for r in v)
w("## Tarefa 11 — Q4_K_M no Fedora (CPU i5-10300H, llama.cpp dde879bc, -t 4), GSM8K completo (1.319)\n")
w("Mesmo pipeline de 03/11 (SYSTEM, temperature 0, seed 42, max_tokens 320, sem pensar, template, -c 4096, grading.py); "
  "mesmo arquivo Q4_K_M do PS4 (d7771967…).\n")
w("### Métricas\n\n| | Fedora Q4_K_M |\n|---|---|")
w(f"| acerto strict | {pct(ns)} |"); w(f"| acerto flex | {pct(nf)} |")
w(f"| tokens por resposta (média / mediana) | {st.mean(f(r,'predicted_n') for r in v):.1f} / {st.median(f(r,'predicted_n') for r in v):.0f} |")
w(f"| cortadas (320) | {sum(r['finish_reason']=='length' for r in v)} |")
w(f"| tempo de prompt / geração por resposta (s) | {st.mean(f(r,'prompt_ms') for r in v)/1000:.2f} / {st.mean(f(r,'predicted_ms') for r in v)/1000:.2f} |")
w(f"| geração tokens/s (total ÷ total) | {sum(f(r,'predicted_n') for r in v)/sum(f(r,'predicted_ms') for r in v)*1000:.2f} |")
w(f"| segundos por resposta / por acerto (flex) | {e2e/n:.2f} / {e2e/nf:.2f} |")

# Kaggle
K = list(csv.DictReader(open(os.path.join(HERE, "../../ps4-eval/hf/eval/eval_grpo.csv"), newline="")))
byt = {}
for r in K: byt.setdefault(r["question"], []).append(r)
pk = []
for i in range(1319):
    ks = byt.get(Q[i]["question"], []); assert len(ks) == 1 and ks[0]["gold"] == F[i]["gold"]
    s, fl = grade(ks[0]["output"], ks[0]["gold"]); pk.append((acc(F[i]), {"strict": s, "flex": fl}))
# PS4 GPU
G = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "../gsm8k-full-gpu-20261108/dados_ps4/resultados_full.csv"), newline=""))}
assert sorted(G) == list(range(1319)) and all(G[i]["gold"] == F[i]["gold"] for i in range(1319))
pg = [(acc(F[i]), acc(G[i])) for i in range(1319)]
# PS4 CPU (tarefa 8), 0–99
T8 = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "../ps4-eval-gpu-20261106/ps4_eval_gpu_20261106_1724.csv"), newline="")) if r["modelo"] == "cpu"}
pc = [(acc(F[i]), acc(T8[i])) for i in range(100)]
# controle: Kaggle e PS4 GPU nas mesmas 1.319 (o que a GPU já mostrou)
pgk = [(acc(G[i]), y) for i, (_, y) in enumerate(pk)]

decis = []
for titulo, pares, na, nb, extra in (
        ("Fedora Q4_K_M × Kaggle (v1, precisão cheia) — 1.319, pareado pelo texto", pk, "Fedora", "Kaggle",
         f"Saídas idênticas: {sum(F[i]['output'].strip() == byt[Q[i]['question']][0]['output'].strip() for i in range(1319))}/1319."),
        ("Fedora Q4_K_M × PS4 GPU Q4_K_M (gsm8k-full-gpu-20261108) — 1.319, mesmo arquivo de modelo", pg, "Fedora", "PS4-GPU",
         f"Saídas idênticas: {sum(F[i]['output'] == G[i]['output'] for i in range(1319))}/1319."),
        ("Fedora Q4_K_M × PS4 CPU Q4_K_M (tarefa 8) — questões 0–99", pc, "Fedora", "PS4-CPU",
         f"Saídas idênticas: {sum(F[i]['output'] == T8[i]['output'] for i in range(100))}/100. n = 100: pouca potência para detectar diferenças pequenas.")):
    cab, linhas, res = comparar(pares, na, nb)
    w(f"\n### {titulo}\n"); w(cab); [w(l) for l in linhas]; w(f"\n{extra} Regra de decisão (flex): {regra(res)}.")
    decis.append((titulo.split(" — ")[0], regra(res)))
cab, linhas, res = comparar(pgk, "PS4-GPU", "Kaggle")
w("\n### Referência: PS4 GPU × Kaggle (já reportado na análise de gsm8k-full-gpu-20261108)\n"); w(cab); [w(l) for l in linhas]
w(f"\nRegra de decisão (flex): {regra(res)}.")
decis.append(("PS4 GPU × Kaggle (referência)", regra(res)))

w("\n### Regra de decisão — resumo\n\nRegra registrada no manifest.csv antes da rodada: **igual = |Δflex| ≤ 1,5 ponto E McNemar exato p > 0,05**.\n")
w("| comparação | resultado |\n|---|---|"); [w(f"| {a} | {b} |") for a, b in decis]

# condições da rodada
bl = list(csv.DictReader(open(os.path.join(HERE, "resultados_q4km_blocos.csv"), newline="")))
pk_l = [l.split("packagekitd:")[-1].strip() for l in open(os.path.join(HERE, "packagekitd_cpu.log")) if "packagekitd:" in l]
com = [x for x in pk_l if x]
w("\n### Condições da rodada\n")
w(f"- Blocos: {len(bl)}; AC ligado em {sum(b['ac_online']=='1' for b in bl)}/{len(bl)} (o bloco das questões 0–19 do teste rodou na bateria); "
  f"subida do servidor {min(float(b['subida_s']) for b in bl):.0f}–{max(float(b['subida_s']) for b in bl):.0f} s; "
  f"temperatura máxima da CPU (coretemp) {max(float(b['temp_max_c']) for b in bl):.0f} °C.")
w(f"- packagekitd: {len(pk_l)} amostras de 60 s; rodando em {len(com)}" + (f" (CPU% máx {max(map(float, com)):.1f})" if com else "") + ".")
w(f"- Tempo somado das respostas: {e2e/3600:.2f} h.")
print("\n".join(out))
open(os.path.join(HERE, "resultado_q4km.md"), "x").write("\n".join(out) + "\n")
