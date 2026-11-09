#!/usr/bin/env python3
"""Tarefa 8: análise GPU (Vulkan) x CPU do treinado no PS4. Mesmas definições de métrica do resumo.py de 03/11.
Uso: python3 analise.py ps4_eval_gpu_<stamp>.csv   (lê também _blocos.csv, temps_vigia.log, vigia_eventos.txt
e ../../ps4-eval/ps4_eval_20261103_2112.csv). Escreve resultado.md."""
import csv, sys, os, math, statistics as st
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1]
R = list(csv.DictReader(open(path)))
by = {m: {int(r["idx"]): r for r in R if r["modelo"] == m} for m in ("gpu", "cpu")}
assert all(len(v) == 100 for v in by.values()), {k: len(v) for k, v in by.items()}
T = lambda r, k: r[k] == "True"
f = lambda r, k: float(r[k])
ts = lambda s: datetime.fromisoformat(s).timestamp()

# --- pausas do vigia -> perguntas afetadas (intervalo [inicio, inicio + e2e] cruza um intervalo de pausa)
pausas, aberta = [], None
for line in open(os.path.join(HERE, "vigia_eventos.txt")):
    p = line.split()
    if len(p) >= 4 and p[3] == "PAUSA": aberta = int(p[2])
    elif len(p) >= 4 and p[3] == "RETOMADA" and aberta is not None: pausas.append((aberta, int(p[2]))); aberta = None
if aberta is not None: pausas.append((aberta, float("inf")))
afetadas = {m: sorted(i for i, r in D.items()
                      if any(ts(r["inicio"]) - 1 <= b and a <= ts(r["inicio"]) + f(r, "e2e_s") + 1 for a, b in pausas))
            for m, D in by.items()}

def metricas(v):
    nf, ns = sum(T(r, "correct_flex") for r in v), sum(T(r, "correct_strict") for r in v)
    e2e = sum(f(r, "e2e_s") for r in v)
    return {
        "n (tempos válidos)": str(len(v)),
        "tokens por resposta (média / mediana)": f"{st.mean(f(r,'predicted_n') for r in v):.1f} / {st.median(f(r,'predicted_n') for r in v):.0f}",
        "cortadas (320)": str(sum(r["finish_reason"] == "length" for r in v)),
        "tokens de prompt processados (média)": f"{st.mean(f(r,'prompt_n') for r in v):.1f}",
        "tempo de prompt por resposta (s)": f"{st.mean(f(r,'prompt_ms') for r in v)/1000:.2f}",
        "tempo de geração por resposta (s)": f"{st.mean(f(r,'predicted_ms') for r in v)/1000:.2f}",
        "geração tokens/s (total tokens ÷ total tempo)": f"{sum(f(r,'predicted_n') for r in v)/sum(f(r,'predicted_ms') for r in v)*1000:.2f}",
        "segundos por resposta (ponta a ponta)": f"{e2e/len(v):.2f}",
        "segundos por resposta correta (flex)": f"{e2e/nf:.2f}" if nf else "—",
    }

out = []; w = out.append
w("## Tarefa 8: Qwen3-1.7B GRPO Q4_K_M no PS4, GPU (Vulkan, -ngl 99) × CPU (build original)\n")
w("### Acurácia (100 questões por braço)\n")
w("| | GPU | CPU |\n|---|---|---|")
for k, lab in (("correct_strict", "acerto strict"), ("correct_flex", "acerto flex")):
    w(f"| {lab} | {sum(T(r,k) for r in by['gpu'].values())}/100 | {sum(T(r,k) for r in by['cpu'].values())}/100 |")
w("\n### Tempos e tokens (todas as 100)\n")
M = {m: metricas(list(D.values())) for m, D in by.items()}
w("| | GPU | CPU | GPU/CPU |\n|---|---|---|---|")
for k in M["gpu"]:
    ratio = ""
    try:
        g, c = float(M["gpu"][k].split()[0]), float(M["cpu"][k].split()[0])
        if "s)" in k or "tokens/s" in k: ratio = f"{g/c:.2f}"
    except ValueError: pass
    w(f"| {k} | {M['gpu'][k]} | {M['cpu'][k]} | {ratio} |")
w(f"\n**Pausas do vigia:** {len(pausas)}. Perguntas com tempo inválido: GPU {afetadas['gpu'] or 'nenhuma'}; CPU {afetadas['cpu'] or 'nenhuma'}.")
if any(afetadas.values()):
    w("\n### Tempos sem as perguntas afetadas\n")
    M2 = {m: metricas([r for i, r in D.items() if i not in afetadas[m]]) for m, D in by.items()}
    w("| | GPU | CPU |\n|---|---|---|")
    for k in M2["gpu"]: w(f"| {k} | {M2['gpu'][k]} | {M2['cpu'][k]} |")
else:
    w("Sem pausas, os resultados \"com\" e \"sem\" as perguntas afetadas são idênticos à tabela acima.")

# --- McNemar (flex e strict) e vereditos
G, C = by["gpu"], by["cpu"]
def mcnemar(k):
    gc = sorted(i for i in G if T(G[i], k) and not T(C[i], k))
    cg = sorted(i for i in G if not T(G[i], k) and T(C[i], k))
    n, b = len(gc) + len(cg), min(len(gc), len(cg))
    p = min(1.0, 2 * sum(math.comb(n, j) for j in range(b + 1)) / 2 ** n) if n else 1.0
    same = sum(T(G[i], k) == T(C[i], k) for i in G)
    both = sum(T(G[i], k) and T(C[i], k) for i in G); none = sum(not T(G[i], k) and not T(C[i], k) for i in G)
    return gc, cg, p, same, both, none
w("\n### GPU × CPU, questão a questão\n")
for k, lab in (("correct_flex", "flex"), ("correct_strict", "strict")):
    gc, cg, p, same, both, none = mcnemar(k)
    w(f"- **{lab}:** GPU acerta e CPU erra em {len(gc)} {gc}; CPU acerta e GPU erra em {len(cg)} {cg}. "
      f"McNemar exato (bicaudal): p = {p:.3f}. Mesmo veredito em {same}/100 (ambos acertam {both}, ambos erram {none}).")
ident = sum(G[i]["output"].strip() == C[i]["output"].strip() for i in G)
w(f"- **Saída idêntica GPU × CPU:** {ident}/100. Mesmo número de tokens gerados: {sum(G[i]['predicted_n'] == C[i]['predicted_n'] for i in G)}/100.")

# --- CPU de hoje × treinado de 03/11
old = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "../../ps4-eval/ps4_eval_20261103_2112.csv"))) if r["modelo"] == "treinado"}
assert len(old) == 100
Mo = metricas(list(old.values()))
w("\n### CPU de hoje × treinado de 03/11 (mesmo binário build/, mesmo modelo)\n")
w("| | CPU hoje | 03/11 | GPU hoje |\n|---|---|---|---|")
w(f"| acerto flex | {sum(T(r,'correct_flex') for r in C.values())}/100 | {sum(T(r,'correct_flex') for r in old.values())}/100 | {sum(T(r,'correct_flex') for r in G.values())}/100 |")
w(f"| acerto strict | {sum(T(r,'correct_strict') for r in C.values())}/100 | {sum(T(r,'correct_strict') for r in old.values())}/100 | {sum(T(r,'correct_strict') for r in G.values())}/100 |")
for k in ("tokens por resposta (média / mediana)", "tempo de prompt por resposta (s)", "tempo de geração por resposta (s)",
          "geração tokens/s (total tokens ÷ total tempo)", "segundos por resposta (ponta a ponta)", "segundos por resposta correta (flex)", "cortadas (320)"):
    w(f"| {k} | {M['cpu'][k]} | {Mo[k]} | {M['gpu'][k]} |")
for lab, X in (("CPU hoje", C), ("GPU hoje", G)):
    ido = sum(X[i]["output"].strip() == old[i]["output"].strip() for i in X)
    samef = sum(T(X[i], "correct_flex") == T(old[i], "correct_flex") for i in X)
    w(f"- {lab} × 03/11: saída idêntica em {ido}/100; mesmo veredito flex em {samef}/100.")

# --- temperatura e ventoinha por bloco (vigia, a cada 5 s)
V = [l.split() for l in open(os.path.join(HERE, "temps_vigia.log")) if not l.startswith("#")]
V = [(int(a[0]), float(a[2]), float(a[3]), a[4], float(a[5])) for a in V]
bl = list(csv.DictReader(open(path.replace(".csv", "_blocos.csv"))))
w("\n### Temperatura por bloco (vigia a cada 5 s; k10temp no início/fim do run_eval)\n")
w("| bloco | braço | início k10temp (°C) | fim k10temp (°C) | máx ps4_fan | máx k10temp | fan1 (mín–máx) | atingiu alvo | espera (s) |\n|---|---|---|---|---|---|---|---|---|")
for b in bl:
    if b["bloco"] == "0":
        w(f"| 0 | repouso | {b['temp_ini_c']} | — | — | — | — | — | {b['espera_s']} |"); continue
    a, z = ts(b["inicio"]), ts(b["fim"])
    s = [v for v in V if a <= v[0] <= z]
    fans = [int(v[3]) for v in s if v[3].isdigit()]
    w(f"| {b['bloco']} | {b['modelo']} | {b['temp_ini_c']} | {b['temp_fim_c']} | {max(v[1] for v in s):.1f} | {max(v[2] for v in s):.1f} | "
      f"{min(fans)}–{max(fans)} | {b['atingiu_alvo']} | {b['espera_s']} |")
w(f"\nMáxima geral: ps4_fan {max(v[1] for v in V):.1f} °C, k10temp {max(v[2] for v in V):.1f} °C.")
first = next((v for v in V if v[3].isdigit() and int(v[3]) > 0), None)
if first:
    w(f"fan1_input > 0 pela primeira vez às {datetime.fromtimestamp(first[0]).strftime('%H:%M:%S')} com ps4_fan {first[1]:.1f} °C / k10temp {first[2]:.1f} °C.")
    for lo, hi in ((0, 76), (76, 78), (78, 80)):
        xs = [int(v[3]) for v in V if v[3].isdigit() and lo <= v[1] < hi]
        if xs: w(f"- ps4_fan em [{lo}, {hi}) °C: fan1 médio {st.mean(xs):.1f} (n={len(xs)}, máx {max(xs)})")
w("\n**Geração tokens/s por bloco:** " + ", ".join(
    f"bloco {b} ({by_m}): {sum(f(r,'predicted_n') for r in R if r['bloco']==str(b))/sum(f(r,'predicted_ms') for r in R if r['bloco']==str(b))*1000:.2f}"
    for b, by_m in ((1, "gpu"), (2, "cpu"), (3, "gpu"), (4, "cpu"))))
print("\n".join(out))
open(os.path.join(HERE, "resultado.md"), "x").write("\n".join(out) + "\n")
