"""Reaplica os verificadores ATUAIS às respostas já gravadas (sem chamar o modelo), para que execuções feitas com versões
diferentes do verificador fiquem comparáveis. Uso: python3 aval/repontua.py resultado.jsonl [...]  (regrava no lugar; guarda .antes)"""
import json, os, shutil, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
from verifica import avalia
its = {}
for f in os.listdir(os.path.join(AQUI, "itens")):
    if f.endswith(".jsonl"):
        for l in open(os.path.join(AQUI, "itens", f), encoding="utf-8"):
            if l.strip(): i = json.loads(l); its[i["id"]] = i
for p in sys.argv[1:]:
    rs = [json.loads(l) for l in open(p, encoding="utf-8")]; antes = sum(bool(r.get("ok")) for r in rs)
    for r in rs:
        if "resposta" in r: r.update(avalia(its[r["id"]], r["resposta"]))
    if not os.path.exists(p + ".antes"): shutil.copy2(p, p + ".antes")
    open(p, "w", encoding="utf-8").write("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rs))
    print(f"{os.path.basename(p)}: acertos {antes} -> {sum(bool(r.get('ok')) for r in rs)} de {len(rs)}")
