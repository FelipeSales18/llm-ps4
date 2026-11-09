#!/usr/bin/env python3
"""Análise da rodada GSM8K completa (1.319 questões) do Qwen3-1.7B GRPO Q4_K_M na GPU do PS4 (llama.cpp Vulkan).
Mesmas definições de métrica do resumo.py de 03/11. Lê dados_ps4/ (cópia dos arquivos do PS4), o eval_grpo.csv do
Kaggle (v1, precisão cheia) e o CSV da tarefa 8. Escreve resultado_full.md.
Uso: python3 analise_full.py"""
import csv, json, math, os, re, statistics as st, sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from grading import grade  # noqa: E402  (mesmo grading.py da rodada)

D = os.path.join(HERE, "dados_ps4")
KAG = os.path.join(HERE, "../../ps4-eval/hf/eval/eval_grpo.csv")
T8 = os.path.join(HERE, "../ps4-eval-gpu-20261106/ps4_eval_gpu_20261106_1724.csv")
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


def newcombe_paired(a, b, c, d):
    """IC 95% da diferença p1 - p2 para proporções pareadas (Newcombe 1998, método 10).
    a = ambos certos, b = só 1 certo, c = só 2 certo, d = ambos errados."""
    n = a + b + c + d; p1, p2 = (a + b) / n, (a + c) / n
    l1, u1 = wilson(a + b, n); l2, u2 = wilson(a + c, n)
    den = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    num = a * d - b * c
    phi = 0.0 if den == 0 else (max(num - n / 2, 0) if num > 0 else num) / den
    dlt = p1 - p2
    lo = dlt - math.sqrt(max((p1 - l1)**2 - 2 * phi * (p1 - l1) * (u2 - p2) + (u2 - p2)**2, 0))
    hi = dlt + math.sqrt(max((u1 - p1)**2 - 2 * phi * (u1 - p1) * (p2 - l2) + (p2 - l2)**2, 0))
    return dlt, lo, hi


R = list(csv.DictReader(open(os.path.join(D, "resultados_full.csv"), newline="")))
G = {int(r["idx"]): r for r in R}
assert sorted(G) == list(range(1319)) and len(R) == 1319
Q = {q["idx"]: q for q in map(json.loads, open(os.path.join(HERE, "questions_full.jsonl")))}
out = []; w = out.append
pct = lambda k, n: f"{k}/{n} = {100*k/n:.1f}% (IC95% {100*wilson(k, n)[0]:.1f}–{100*wilson(k, n)[1]:.1f})"

# ---------------- 1. métricas da GPU
v = list(G.values()); ns, nf = sum(T(r, "correct_strict") for r in v), sum(T(r, "correct_flex") for r in v)
val = [r for r in v if r["tempo_valido"] == "True"]
e2e = sum(f(r, "e2e_s") for r in val)
w("## GSM8K completo (1.319) — Qwen3-1.7B GRPO Q4_K_M, PS4 GPU (llama.cpp Vulkan, -ngl 99)\n")
w("Pipeline de 03/11 (mesmo SYSTEM, temperature 0, seed 42, max_tokens 320, sem pensar, mesmo template e grading.py); "
  "cliente no próprio PS4 (run_eval_full.py v2 → v3 → v4, mesma geração).\n")
w("### Métricas\n")
w("| | GPU (PS4) |\n|---|---|")
w(f"| acerto strict | {pct(ns, 1319)} |")
w(f"| acerto flex | {pct(nf, 1319)} |")
w(f"| tokens por resposta (média / mediana) | {st.mean(f(r,'predicted_n') for r in v):.1f} / {st.median(f(r,'predicted_n') for r in v):.0f} |")
w(f"| cortadas (320) | {sum(r['finish_reason'] == 'length' for r in v)} |")
w(f"| tokens de prompt processados (média) | {st.mean(f(r,'prompt_n') for r in v):.1f} |")
w(f"| tempo de prompt por resposta (s) | {st.mean(f(r,'prompt_ms') for r in val)/1000:.2f} |")
w(f"| tempo de geração por resposta (s) | {st.mean(f(r,'predicted_ms') for r in val)/1000:.2f} |")
w(f"| geração tokens/s (total tokens ÷ total tempo) | {sum(f(r,'predicted_n') for r in val)/sum(f(r,'predicted_ms') for r in val)*1000:.2f} |")
w(f"| segundos por resposta (ponta a ponta) | {e2e/len(val):.2f} |")
w(f"| segundos por resposta correta (flex) | {e2e/sum(T(r,'correct_flex') for r in val):.2f} |")
w(f"| tempos inválidos (pausa do vigia) | {len(v) - len(val)} |")

# ---------------- 2. pareamento com o Kaggle pelo texto da pergunta
K = list(csv.DictReader(open(KAG, newline="")))
by_text = {}
for r in K: by_text.setdefault(r["question"], []).append(r)
dup = {t: rs for t, rs in by_text.items() if len(rs) > 1}
pares, sem = [], []
for i, g in G.items():
    ks = by_text.get(Q[i]["question"], [])
    if len(ks) == 1: pares.append((g, ks[0]))
    else: sem.append(i)
assert all(g["gold"] == k["gold"] for g, k in pares), "gold diverge entre PS4 e Kaggle"
reg = [(grade(k["output"], k["gold"])) for _, k in pares]
conf = sum((s == (k["correct_strict"] == "True")) and (fl == (k["correct_flex"] == "True")) for (s, fl), (_, k) in zip(reg, pares))
w("\n### GPU (PS4, Q4_K_M) × Kaggle (v1, precisão cheia), pareado pelo texto da pergunta\n")
w(f"Pares: {len(pares)}/1319 (textos duplicados no Kaggle: {len(dup)}; sem par único: {len(sem)}). "
  f"As duas saídas foram corrigidas com o mesmo grading.py; o regrading reproduz as notas gravadas pelo Kaggle em {conf}/{len(pares)}.\n")
n = len(pares)
w("| | GPU (PS4) | Kaggle | trocas: só GPU acerta / só Kaggle acerta | McNemar exato (p) | diferença GPU − Kaggle (pontos, IC95% Newcombe) | mesmo veredito |\n|---|---|---|---|---|---|---|")
for nome, idx in (("strict", 0), ("flex", 1)):
    gk = [(T(g, f"correct_{nome}"), reg[j][idx]) for j, (g, _) in enumerate(pares)]
    a = sum(x and y for x, y in gk); b = sum(x and not y for x, y in gk); c = sum(y and not x for x, y in gk); d = n - a - b - c
    dl, lo, hi = newcombe_paired(a, b, c, d)
    w(f"| {nome} | {a+b}/{n} ({100*(a+b)/n:.1f}%) | {a+c}/{n} ({100*(a+c)/n:.1f}%) | {b} / {c} | {mcnemar(b, c):.3f} | "
      f"{100*dl:+.1f} ({100*lo:+.1f} a {100*hi:+.1f}) | {a+d}/{n} (ambos acertam {a}, ambos erram {d}) |")
ident = sum(g["output"].strip() == k["output"].strip() for g, k in pares)
w(f"\nTokens por resposta: GPU {st.mean(f(g,'predicted_n') for g, _ in pares):.1f} (mediana {st.median(f(g,'predicted_n') for g, _ in pares):.0f}) × "
  f"Kaggle {st.mean(float(k['n_tokens']) for _, k in pares):.1f} (mediana {st.median(float(k['n_tokens']) for _, k in pares):.0f}); "
  f"cortadas GPU {sum(g['finish_reason']=='length' for g, _ in pares)} × Kaggle {sum(k['truncated']=='True' for _, k in pares)}; "
  f"saída idêntica em {ident}/{n}.")

# ---------------- 3. questões 0–99 × tarefa 8
T8R = list(csv.DictReader(open(T8, newline="")))
w("\n### Questões 0–99: rodada completa × tarefa 8 (06/11)\n")
w("| braço da tarefa 8 | saídas idênticas | mesmo veredito flex | flex T8 | flex rodada (0–99) |\n|---|---|---|---|---|")
for arm in ("gpu", "cpu"):
    A = {int(r["idx"]): r for r in T8R if r["modelo"] == arm}
    w(f"| {arm} | {sum(A[i]['output'] == G[i]['output'] for i in range(100))}/100 | "
      f"{sum(T(A[i],'correct_flex') == T(G[i],'correct_flex') for i in range(100))}/100 | "
      f"{sum(T(A[i],'correct_flex') for i in range(100))} | {sum(T(G[i],'correct_flex') for i in range(100))} |")

# ---------------- 4. por bloco (a partir do log; o bloco 150–196 foi interrompido pelo travamento)
LOG = [l.rstrip("\n") for l in open(os.path.join(D, "resultados_full.log"))]
ts = lambda l: datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S").timestamp()
V = [l.split() for l in open(os.path.join(D, "temps_vigia.log")) if not l.startswith("#")]
V = [(int(x[0]), float(x[2]), float(x[3]), x[4]) for x in V]
EV = [l.split() for l in open(os.path.join(D, "vigia_eventos.txt"))]
pausas = [int(x[2]) for x in EV if len(x) > 3 and x[3] == "PAUSA"]
segs, cur, subida = [], None, None
for l in LOG:
    m = re.search(r"servidor GPU pronto em (\d+)s", l)
    if m: subida = f"{m.group(1)} s"
    m = re.search(r"bloco (\d+): servidor GPU \(re\)iniciado; subida ([\d.]+)s", l)
    if m: subida = f"{m.group(2)} s"
    m = re.search(r"bloco (\d+): idx (\d+)-(\d+) \((\d+)\), ([\d.]+) °C .*espera (\d+)s", l)
    if m:
        cur = {"bloco": int(m.group(1)), "ini": int(m.group(2)), "fim": int(m.group(3)), "t0": ts(l), "t1": None,
               "temp_ini": m.group(5), "espera": m.group(6), "subida": subida or "— (mesmo servidor)", "obs": ""}
        segs.append(cur); subida = None
    m = re.search(r" idx=\s*(\d+) ", l)
    if m and cur: cur["ult"] = int(m.group(1)); cur["t_ult"] = ts(l)
    if re.search(r"bloco \d+ fim:", l) and cur: cur["t1"] = ts(l); cur = None
    if "RESUMO" in l and cur:  # bloco interrompido
        cur["t1"] = cur["t_ult"]; cur["obs"] = f"interrompido após idx {cur['ult']} (travamento da GPU na {cur['ult']+1})"; cur["fim"] = cur["ult"]; cur = None
w("\n### Por bloco\n")
w("| bloco | idx | subida do servidor | início (°C, k10temp) | espera p/ esfriar (s) | máx ps4_fan / k10temp (°C) | fan1 máx | pausas do vigia | tempos inválidos | duração | obs |\n|---|---|---|---|---|---|---|---|---|---|---|")
for s in segs:
    vv = [x for x in V if s["t0"] <= x[0] <= s["t1"]]
    fans = [int(x[3]) for x in vv if x[3].isdigit()]
    inval = sum(G[i]["tempo_valido"] != "True" for i in range(s["ini"], s["fim"] + 1))
    np_ = sum(s["t0"] <= p <= s["t1"] for p in pausas)
    w(f"| {s['bloco']} | {s['ini']}–{s['fim']} | {s['subida']} | {s['temp_ini']} | {s['espera']} | "
      f"{max(x[1] for x in vv):.1f} / {max(x[2] for x in vv):.1f} | {max(fans) if fans else '—'} | {np_} | {inval} | "
      f"{(s['t1']-s['t0'])/60:.1f} min | {s['obs']} |")
w(f"\nMáxima geral: ps4_fan {max(x[1] for x in V):.1f} °C, k10temp {max(x[2] for x in V):.1f} °C (vigia, inclui os testes de 08/11 18:24–18:30). Pausas do vigia: {len(pausas)}.")

# ---------------- 5. execuções, tempo total e kernel
runs, r0 = [], None
for l in LOG:
    m = re.search(r"faixa (\d+)-(\d+): .*a fazer (\d+)", l)
    if m: r0 = (ts(l), l[:19], m.group(0))
    if l.endswith(" FIM") and r0: runs.append((r0[0], ts(l), r0[1], l[:19], r0[2])); r0 = None
w("\n### Execuções e tempo total\n")
w("| início | fim | duração | faixa |\n|---|---|---|---|")
for a, b, sa, sb, txt in runs:
    w(f"| {sa} | {sb} | {(b-a)/3600:.2f} h | {txt.split(':')[0]} |")
tot = sum(b - a for a, b, *_ in runs)
w(f"\nTempo em execução (soma das 4): {tot/3600:.2f} h; do primeiro início ao último FIM (inclui a parada e o reboot): "
  f"{(runs[-1][1]-runs[0][0])/3600:.2f} h. Soma dos tempos ponta a ponta das 1.319 respostas: {sum(f(r,'e2e_s') for r in v)/3600:.2f} h.")
kj = open(os.path.join(D, "kernel_janelas.txt")).read().strip().splitlines()
w("\n**Kernel (amdgpu|drm|gpu):** " + "; ".join(l for l in kj if not l.startswith("#")) +
  ". O travamento de 08/11 19:27:50 (idx 197, primeira execução) não deixou nenhuma linha do amdgpu.")
print("\n".join(out))
open(os.path.join(HERE, "resultado_full.md"), "x").write("\n".join(out) + "\n")
