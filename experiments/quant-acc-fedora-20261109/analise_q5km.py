#!/usr/bin/env python3
"""Tarefa 11, braço Q5_K_M no Fedora (CPU, llama.cpp dde879bc, -t 4), mesmo pipeline do Q4_K_M.
Comparações pareadas contra: Kaggle (eval_grpo.csv v1, pelo texto da pergunta, recorrigido com o mesmo grading.py),
Q4_K_M do Fedora (resultados_q4km.csv) e GPU do PS4 (gsm8k-full-gpu-20261108). Regras (manifest.csv):
  recupera = Q5_K_M × Kaggle com |Δflex| <= 1,5 ponto E McNemar p > 0,05
  melhora  = Q5_K_M acima do Q4_K_M do Fedora (Δflex > 0) com McNemar p < 0,05 no flex
Uso: python3 analise_q5km.py  -> resultado_q5km.md"""
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


def comparar(pares, na, nb):
    n, linhas, res = len(pares), [], {}
    for k in ("strict", "flex"):
        a = sum(x[k] and y[k] for x, y in pares); b = sum(x[k] and not y[k] for x, y in pares)
        c = sum(y[k] and not x[k] for x, y in pares); d = n - a - b - c
        dl, lo, hi = newcombe(a, b, c, d); p = mcnemar(b, c); res[k] = (dl, lo, hi, p)
        linhas.append(f"| {k} | {a+b}/{n} ({100*(a+b)/n:.1f}%) | {a+c}/{n} ({100*(a+c)/n:.1f}%) | {b} / {c} | {p:.3g} | "
                      f"{100*dl:+.1f} ({100*lo:+.1f} a {100*hi:+.1f}) | {a+d}/{n} |")
    cab = (f"| | {na} | {nb} | só {na} acerta / só {nb} acerta | McNemar exato (p) | {na} − {nb} (pontos, IC95% Newcombe) | "
           f"mesmo veredito |\n|---|---|---|---|---|---|---|")
    return cab, linhas, res


Q = {q["idx"]: q for q in map(json.loads, open(os.path.join(HERE, "questions_full.jsonl")))}
F5 = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "resultados_q5km.csv"), newline=""))}
assert sorted(F5) == list(range(1319)), f"faltam questões: {1319 - len(F5)}"
F4 = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "resultados_q4km.csv"), newline=""))}
G = {int(r["idx"]): r for r in csv.DictReader(open(os.path.join(HERE, "../gsm8k-full-gpu-20261108/dados_ps4/resultados_full.csv"), newline=""))}
K = list(csv.DictReader(open(os.path.join(HERE, "../../ps4-eval/hf/eval/eval_grpo.csv"), newline="")))
byt = {}
for r in K: byt.setdefault(r["question"], []).append(r)
assert sorted(F4) == sorted(G) == list(range(1319))
acc = lambda r: {"strict": T(r, "correct_strict"), "flex": T(r, "correct_flex")}
kag = {}
for i in range(1319):
    ks = byt[Q[i]["question"]]; assert len(ks) == 1 and ks[0]["gold"] == F5[i]["gold"] == F4[i]["gold"] == G[i]["gold"]
    s, fl = grade(ks[0]["output"], ks[0]["gold"]); kag[i] = ({"strict": s, "flex": fl}, ks[0])

out = []; w = out.append
v = list(F5.values()); n = len(v); ns, nf = sum(T(r, "correct_strict") for r in v), sum(T(r, "correct_flex") for r in v)
pct = lambda k: f"{k}/{n} = {100*k/n:.1f}% (IC95% {100*wilson(k, n)[0]:.1f}–{100*wilson(k, n)[1]:.1f})"
e2e = sum(f(r, "e2e_s") for r in v)
w("## Tarefa 11 — Q5_K_M no Fedora (CPU i5-10300H, llama.cpp dde879bc, -t 4), GSM8K completo (1.319)\n")
w("Mesmo pipeline do braço Q4_K_M (run_quant.py f5811ab5…). Modelo qwen3-1.7b-gsm8k-grpo-Q5_K_M.gguf (366dbe4c…).\n")
w("### Métricas (com o Q4_K_M do Fedora ao lado)\n\n| | Q5_K_M | Q4_K_M |\n|---|---|---|")
v4 = list(F4.values())
def lin(nome, fn): w(f"| {nome} | {fn(v)} | {fn(v4)} |")
lin("acerto strict", lambda x: f"{sum(T(r,'correct_strict') for r in x)}/1319 = {100*sum(T(r,'correct_strict') for r in x)/1319:.1f}% (IC95% {100*wilson(sum(T(r,'correct_strict') for r in x),1319)[0]:.1f}–{100*wilson(sum(T(r,'correct_strict') for r in x),1319)[1]:.1f})")
lin("acerto flex", lambda x: f"{sum(T(r,'correct_flex') for r in x)}/1319 = {100*sum(T(r,'correct_flex') for r in x)/1319:.1f}% (IC95% {100*wilson(sum(T(r,'correct_flex') for r in x),1319)[0]:.1f}–{100*wilson(sum(T(r,'correct_flex') for r in x),1319)[1]:.1f})")
lin("tokens por resposta (média / mediana)", lambda x: f"{st.mean(f(r,'predicted_n') for r in x):.1f} / {st.median(f(r,'predicted_n') for r in x):.0f}")
lin("cortadas (320)", lambda x: str(sum(r['finish_reason'] == 'length' for r in x)))
lin("tempo de prompt / geração por resposta (s)", lambda x: f"{st.mean(f(r,'prompt_ms') for r in x)/1000:.2f} / {st.mean(f(r,'predicted_ms') for r in x)/1000:.2f}")
lin("geração tokens/s (total ÷ total)", lambda x: f"{sum(f(r,'predicted_n') for r in x)/sum(f(r,'predicted_ms') for r in x)*1000:.2f}")
lin("segundos por resposta", lambda x: f"{sum(f(r,'e2e_s') for r in x)/len(x):.2f}")
lin("segundos por acerto (flex)", lambda x: f"{sum(f(r,'e2e_s') for r in x)/sum(T(r,'correct_flex') for r in x):.2f}")

res_all = {}
for chave, titulo, pares, nb, extra in (
        ("kaggle", "Q5_K_M × Kaggle (v1, precisão cheia) — pareado pelo texto", [(acc(F5[i]), kag[i][0]) for i in range(1319)], "Kaggle",
         f"Saídas idênticas: {sum(F5[i]['output'].strip() == kag[i][1]['output'].strip() for i in range(1319))}/1319."),
        ("q4km", "Q5_K_M × Q4_K_M (ambos no Fedora, mesmo pipeline)", [(acc(F5[i]), acc(F4[i])) for i in range(1319)], "Q4_K_M",
         f"Saídas idênticas: {sum(F5[i]['output'] == F4[i]['output'] for i in range(1319))}/1319."),
        ("gpu", "Q5_K_M (Fedora) × Q4_K_M na GPU do PS4 (gsm8k-full-gpu-20261108)", [(acc(F5[i]), acc(G[i])) for i in range(1319)], "PS4-GPU",
         f"Saídas idênticas: {sum(F5[i]['output'] == G[i]['output'] for i in range(1319))}/1319.")):
    cab, linhas, res = comparar(pares, "Q5_K_M", nb); res_all[chave] = res
    w(f"\n### {titulo}\n"); w(cab); [w(l) for l in linhas]; w(f"\n{extra}")

dk, _, _, pk = res_all["kaggle"]["flex"]; d4, _, _, p4 = res_all["q4km"]["flex"]
recupera = abs(100 * dk) <= 1.5 and pk > 0.05
melhora = d4 > 0 and p4 < 0.05
w("\n### Regras de decisão (registradas no manifest.csv antes da rodada)\n")
w("| regra | condição | valores | aplica-se? |\n|---|---|---|---|")
w(f"| recupera | Q5_K_M × Kaggle: \\|Δflex\\| ≤ 1,5 ponto E McNemar p > 0,05 | Δflex = {100*dk:+.1f}; p = {pk:.3g} | **{'sim' if recupera else 'não'}** |")
w(f"| melhora | Q5_K_M acima do Q4_K_M do Fedora (Δflex > 0) com McNemar p < 0,05 no flex | Δflex = {100*d4:+.1f}; p = {p4:.3g} | **{'sim' if melhora else 'não'}** |")

bl = list(csv.DictReader(open(os.path.join(HERE, "resultados_q5km_blocos.csv"), newline="")))
pk_l = [l.split("packagekitd:")[-1].strip() for l in open(os.path.join(HERE, "packagekitd_cpu_q5km.log")) if "packagekitd:" in l]
com = [x for x in pk_l if x]
w("\n### Condições da rodada\n")
w(f"- Blocos: {len(bl)}; AC ligado em {sum(b['ac_online']=='1' for b in bl)}/{len(bl)} (o bloco do teste, questões 0–19, também na tomada); "
  f"subida do servidor {min(float(b['subida_s']) for b in bl):.0f}–{max(float(b['subida_s']) for b in bl):.0f} s; "
  f"temperatura máxima da CPU (coretemp) {max(float(b['temp_max_c']) for b in bl):.0f} °C.")
w(f"- packagekitd: {len(pk_l)} amostras (a cada ~60 s, presas ao processo do cliente); rodando em {len(com)}"
  + (f" (CPU% máx {max(map(float, com)):.1f})" if com else "") + ".")
w(f"- Tempo somado das respostas: {e2e/3600:.2f} h.")
print("\n".join(out))
open(os.path.join(HERE, "resultado_q5km.md"), "x").write("\n".join(out) + "\n")
