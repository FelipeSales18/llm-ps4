"""Congela a divisão dos itens em desenvolvimento / seleção / teste final (≈20 por categoria em cada), com semente fixa.
Itens que compartilham algum documento ficam SEMPRE no mesmo conjunto (sem vazamento de documento entre conjuntos).
Grava aval/divisao.json com os ids e o sha256 de cada arquivo de itens. Não regrava se já existir (use --forca conscientemente)."""
import hashlib, json, os, random, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); saida = os.path.join(AQUI, "divisao.json")
if os.path.exists(saida) and "--forca" not in sys.argv: sys.exit("divisao.json já existe (congelada). Não regrave depois de começar a usar.")
rng = random.Random(20261113); div = {"dev": [], "sel": [], "teste": []}; shas = {}; resumo = {}
for f in sorted(os.listdir(os.path.join(AQUI, "itens"))):
    if not f.endswith(".jsonl"): continue
    p = os.path.join(AQUI, "itens", f); shas[f] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    its = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]; pai = {x["id"]: x["id"] for x in its}; dono = {}
    def raiz(a):
        while pai[a] != a: a = pai[a]
        return a
    for x in its:
        for d in x.get("documentos") or []:
            k = hashlib.md5(d["texto"].encode()).hexdigest()
            if k in dono: pai[raiz(x["id"])] = raiz(dono[k])
            else: dono[k] = x["id"]
    grupos = {}
    for x in its: grupos.setdefault(raiz(x["id"]), []).append(x["id"])
    gs = sorted(grupos.values(), key=lambda g: g[0]); rng.shuffle(gs); gs.sort(key=len, reverse=True)  # grupos grandes primeiro; ordem aleatória entre iguais
    alvo = len(its) / 3; cont = {"dev": [], "sel": [], "teste": []}
    for g in gs:
        k = min(cont, key=lambda c: (len(cont[c]) + len(g) > alvo + 2, len(cont[c]), rng.random()))
        cont[k] += g
    for k in cont: div[k] += sorted(cont[k])
    resumo[f] = {k: len(v) for k, v in cont.items()} | {"grupos_de_documento": sum(len(g) > 1 for g in gs)}
json.dump({"semente": 20261113, "sha256_itens": shas, "resumo": resumo, **div}, open(saida, "w"), indent=1, ensure_ascii=False)
print(json.dumps(resumo, indent=1, ensure_ascii=False)); print({k: len(v) for k, v in div.items()})
