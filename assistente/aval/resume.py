"""Resumo comparável de uma ou mais execuções da avaliação. Uso: python3 aval/resume.py resultado1.jsonl [resultado2.jsonl ...]
A 1ª é a referência das comparações pareadas (mesmos itens): diferença de acerto, IC95% por bootstrap e teste exato dos sinais."""
import json, math, random, sys
from math import comb
runs = [(p, {json.loads(l)["id"]: json.loads(l) for l in open(p, encoding="utf-8")}) for p in sys.argv[1:]]
ids = sorted(set.intersection(*[set(r) for _, r in runs])); cats = sorted({runs[0][1][i]["categoria"] for i in ids})
med = lambda xs: sorted(xs)[len(xs) // 2] if xs else float("nan"); p90 = lambda xs: sorted(xs)[int(.9 * (len(xs) - 1))] if xs else float("nan")
print(f"itens em comum: {len(ids)}\n")
print("| execução | acerto | " + " | ".join(cats) + " | vazias | cortadas | repetição | fora do idioma | erros | 1º token (s) med/p90 | total (s) med/p90 | tokens resp. | tok/s | pico RAM (MB) |")
print("|---|---|" + "---|" * len(cats) + "---|---|---|---|---|---|---|---|---|---|")
for p, r in runs:
    xs = [r[i] for i in ids]; ok = lambda ys: f"{100 * sum(bool(y.get('ok')) for y in ys) / max(1, len(ys)):.1f}%"
    tt = [x["t_total"] for x in xs if x.get("t_total")]; tp = [x["t_primeiro"] for x in xs if x.get("t_primeiro")]; tk = [x["tokens_resposta"] for x in xs if x.get("tokens_resposta")]
    ts = [x["tempos"]["predicted_per_second"] for x in xs if x.get("tempos") and x["tempos"].get("predicted_per_second")]
    idi = sum(any(v["tipo"] == "idioma" and not v["ok"] for v in x.get("verificacoes", [])) for x in xs); pico = max([x.get("pico_mb", 0) for x in xs] or [0])
    print(f"| {p.split('/')[-1].replace('.jsonl', '')} | **{ok(xs)}** ({sum(bool(x.get('ok')) for x in xs)}/{len(xs)}) | " + " | ".join(ok([x for x in xs if x['categoria'] == c]) for c in cats) +
          f" | {sum(bool(x.get('vazia')) for x in xs)} | {sum(bool(x.get('cortada')) for x in xs)} | {sum(bool(x.get('repeticao')) for x in xs)} | {idi} | {sum('erro' in x for x in xs)} | {med(tp):.1f}/{p90(tp):.1f} | {med(tt):.1f}/{p90(tt):.1f} | {sum(tk) / max(1, len(tk)):.0f} | {med(ts):.1f} | {pico or '—'} |")
if len(runs) > 1:
    ref = runs[0][1]; rnd = random.Random(0); print(f"\nPareado contra {runs[0][0].split('/')[-1]}:")
    for p, r in runs[1:]:
        d = [int(bool(r[i].get("ok"))) - int(bool(ref[i].get("ok"))) for i in ids]; u = sum(x > 0 for x in d); dn = sum(x < 0 for x in d); m = u + dn
        pv = min(1.0, 2 * sum(comb(m, k) for k in range(0, min(u, dn) + 1)) / 2 ** m) if m else 1.0
        bs = sorted(sum(rnd.choices(d, k=len(d))) / len(d) for _ in range(4000))
        print(f"  {p.split('/')[-1]}: Δ {100 * sum(d) / len(d):+.1f} pt (IC95% {100 * bs[100]:+.1f} a {100 * bs[3899]:+.1f}); ganhos/perdas +{u}/−{dn}; p={pv:.3g}")
