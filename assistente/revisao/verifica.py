"""Verificadores objetivos da avaliação do assistente (só biblioteca padrão; roda igual no notebook e no PS4).
Especificação: aval/ESPECIFICACAO.md. Uso como biblioteca: avalia(item, resposta) -> dict.
Autoteste dos itens (a resposta de referência tem de passar; a errada tem de falhar):
    python3 aval/verifica.py --autoteste [arquivo.jsonl ...]"""
import json, os, re, shutil, subprocess, sys, tempfile, unicodedata

AQUI = os.path.dirname(os.path.abspath(__file__))


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def limpa(resposta):
    """Resposta final em texto: sem bloco de raciocínio e sem espaços nas pontas."""
    r = re.sub(r"<think>.*?</think>", "", resposta or "", flags=re.S)
    r = re.sub(r"<think>.*\Z", "", r, flags=re.S)  # raciocínio que não fechou (cortado)
    return r.strip()


def _norm(s, v):
    if v.get("ignora_caixa", True): s = s.lower()
    if v.get("ignora_acentos", True): s = sem_acento(s)
    return s


# ---------------------------------------------------------------- números (formato brasileiro e americano)
_NUM = re.compile(r"(?<![\w.,])[-−–]?\d[\d.,  ]*\d|(?<![\w.,])[-−–]?\d")


def numeros(texto):
    """Lista de conjuntos de valores possíveis, um por número encontrado (ambiguidades viram alternativas)."""
    out = []
    for m in _NUM.finditer(texto):
        t = m.group(0).replace(" ", " ").strip(); neg = t[:1] in "-−–"; t = t.lstrip("-−–").strip()
        t = re.sub(r"(?<=\d) (?=\d{3}(?:\D|$))", "", t)  # 1 234 567 -> 1234567
        if " " in t:  # "3 e 4", "10 20": números separados
            for p in t.split():
                out += numeros(("-" if neg else "") + p)
            continue
        t = t.rstrip(".,")
        if not t: continue
        vals = set()
        if re.fullmatch(r"\d+", t): vals.add(float(t))
        if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?", t): vals.add(float(t.replace(".", "").replace(",", ".")))  # 1.234,56
        if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?", t): vals.add(float(t.replace(",", "")))                  # 1,234.56
        if re.fullmatch(r"\d+,\d+", t): vals.add(float(t.replace(",", ".")))                                   # 3,5
        if re.fullmatch(r"\d+\.\d+", t): vals.add(float(t))                                                     # 3.5
        if not vals:
            try: vals.add(float(t.replace(".", "").replace(",", ".")))
            except ValueError: continue
        out.append({-x for x in vals} | vals if False else ({-x for x in vals} if neg else vals))
    return out


def _bate(vals, alvo, v):
    tol = max(float(v.get("tol", 0) or 0), abs(alvo) * float(v.get("tol_rel", 0) or 0), 1e-9)
    return any(abs(x - alvo) <= tol for x in vals)


# ---------------------------------------------------------------- idioma
_PT = set("de que não nao é para com uma um os da em você voce por mais como se ou foi está também tambem já muito pode seu sua isso essa esse na dos das ao aos pelo pela mas porque quando então entao tem ter ser estou vai são pra nos nas uma seus suas meu minha".split())  # sem "as", "no", "do" (existem em inglês)
_EN = set("the and is are of to you that this with for it was have not be can will your would which from they there what about their has been were when".split())


def idioma(texto):
    ws = [w for w in re.findall(r"[A-Za-zÀ-ÿ]+", texto) if not (w[0].isupper() and w.lower() in ("são", "sao"))]  # "São Paulo" não conta como português
    ws = [w.lower() for w in ws]; pt = sum(w in _PT for w in ws); en = sum(w in _EN for w in ws)
    if len(ws) < 6 or pt + en < 2: return "indefinido"
    return "pt" if pt >= en else "en"


# ---------------------------------------------------------------- "não sei"
_NAO_SEI = [r"nao sei", r"nao tenho (como|acesso|essa|esse|a |o |informac|conhecimento|dados)", r"nao (consigo|posso|e possivel|da para|da pra|ha como|tem como) (saber|informar|dizer|afirmar|determinar|responder|verificar|confirmar|acessar)",
            r"nao consta", r"nao (informa|menciona|especifica|diz|traz|indica|cita|aparece|fala|esta (no|na|em)|foi (informad|mencionad|dit|fornecid)|ha (informac|mencao|dados|nada))",
            r"voce nao (me )?(disse|informou|contou|falou|mencionou)", r"sem (essa )?informac", r"(nenhuma|nao encontrei|nao achei|nao localizei) (informac|mencao|referencia|dado)", r"nao (encontrei|achei|localizei)", r"desconhec",
            r"nao (esta|estao) (disponive|especificad|presente|descrit)", r"nao posso (afirmar|garantir)", r"infelizmente nao"]


def admite_nao_saber(texto):
    t = sem_acento(texto.lower()); return any(re.search(p, t) for p in _NAO_SEI)


# ---------------------------------------------------------------- JSON e código
def extrai_json(texto):
    cands = re.findall(r"```(?:json)?\s*(.*?)```", texto, flags=re.S) + [texto]
    for c in cands:
        c = c.strip()
        for ini, fim in (("{", "}"), ("[", "]")):
            i, j = c.find(ini), c.rfind(fim)
            if i >= 0 and j > i:
                try: return json.loads(c[i:j + 1])
                except Exception: pass
    return None


def extrai_codigo(texto):
    m = re.findall(r"```(?:python|py)?[ \t]*\n(.*?)```", texto, flags=re.S)
    if m: return max(m, key=lambda b: ("def " in b, len(b)))
    return texto if "def " in texto else None


def roda_python(codigo, testes, limite_s=8):
    """Executa código + asserts num processo isolado (bwrap se existir; senão, limites de recurso). Devolve (ok, saída)."""
    prog = codigo + "\n\n" + "\n".join(testes) + "\nprint('TESTES_OK')\n"
    with tempfile.TemporaryDirectory() as d:
        open(os.path.join(d, "p.py"), "w").write(prog)
        base = [sys.executable, "-I", "-S", "p.py"]
        if shutil.which("bwrap"):
            cmd = ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/home", "--tmpfs", "/tmp", "--bind", d, "/tmp/caixa", "--chdir", "/tmp/caixa", "--unshare-all", "--die-with-parent", "--new-session"] + base
        else:
            cmd = ["bash", "-c", "ulimit -v 1048576 -t %d; cd %s; exec %s" % (limite_s, d, " ".join(base))]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=limite_s + 4, cwd=d)
            return "TESTES_OK" in p.stdout, (p.stdout + p.stderr)[-400:]
        except subprocess.TimeoutExpired:
            return False, "tempo esgotado"
        except Exception as e:
            return False, repr(e)


# ---------------------------------------------------------------- verificações
def _itens_lista(t):
    return sum(bool(re.match(r"\s*(?:[-*•–]|\d+[.)])\s+\S", l)) for l in t.splitlines())


def checa(v, r):
    """Uma verificação sobre a resposta limpa r. Devolve (passou, detalhe)."""
    tp = v["tipo"]
    if tp == "contem": return _norm(v["valor"], v) in _norm(r, v), v["valor"]
    if tp == "contem_algum": return any(_norm(x, v) in _norm(r, v) for x in v["valores"]), "|".join(v["valores"])[:60]
    if tp == "nao_contem": return _norm(v["valor"], v) not in _norm(r, v), v["valor"]
    if tp in ("regex", "nao_regex"):
        fl = re.S | (re.I if "i" in v.get("flags", "i") else 0) | (re.M if "m" in v.get("flags", "") else 0)
        achou = bool(re.search(v["valor"], r, fl)); return (achou if tp == "regex" else not achou), v["valor"][:60]
    if tp == "numero": return any(_bate(vals, float(v["valor"]), v) for vals in numeros(r)), str(v["valor"])
    if tp == "numero_final":
        ns = numeros(r); return bool(ns) and _bate(ns[-1], float(v["valor"]), v), str(v["valor"])
    if tp == "max_palavras": return len(r.split()) <= v["valor"], f"{len(r.split())} palavras"
    if tp == "min_palavras": return len(r.split()) >= v["valor"], f"{len(r.split())} palavras"
    if tp == "max_linhas": return len([l for l in r.splitlines() if l.strip()]) <= v["valor"], ""
    if tp == "n_itens_lista": return _itens_lista(r) == v["valor"], f"{_itens_lista(r)} itens"
    if tp == "comeca_com": return _norm(r.strip(), v).startswith(_norm(v["valor"], v)), v["valor"]
    if tp == "termina_com": return _norm(r.strip(), v).rstrip(" .!\"'*").endswith(_norm(v["valor"], v).rstrip(" .!")), v["valor"]
    if tp == "json_valido":
        j = extrai_json(r)
        if j is None: return False, "sem JSON"
        if isinstance(j, list) and v.get("campos"): j = j[0] if j and isinstance(j[0], dict) else {}
        for c in v.get("campos", []):
            if not isinstance(j, dict) or c not in j: return False, f"falta campo {c}"
        for c, esp in v.get("valores", {}).items():
            got = j.get(c) if isinstance(j, dict) else None
            if isinstance(esp, (int, float)) and not isinstance(esp, bool):
                try: ok = abs(float(str(got).replace(",", ".")) - esp) <= 1e-6 + 1e-6 * abs(esp)
                except Exception: ok = False
            else: ok = sem_acento(str(got).strip().lower()) == sem_acento(str(esp).strip().lower())
            if not ok: return False, f"{c}={got!r}"
        return True, ""
    if tp == "idioma":
        if v["valor"] == "qualquer": return True, ""
        lg = idioma(r); return lg in (v["valor"], "indefinido"), lg
    if tp == "codigo_python":
        c = extrai_codigo(r)
        if not c: return False, "sem código"
        return roda_python(c, v["testes"])
    if tp == "admite_nao_saber": return admite_nao_saber(r), ""
    raise ValueError(f"tipo de verificação desconhecido: {tp}")


def repeticao(r):
    """Sinal barato de laço: mesma linha não trivial 4+ vezes, ou mais de 35% dos 5-gramas de palavras repetidos."""
    ls = [l.strip() for l in r.splitlines() if len(l.strip()) > 12]
    if ls and max(ls.count(x) for x in set(ls)) >= 4: return True
    w = r.split()
    if len(w) < 60: return False
    g = [" ".join(w[i:i + 5]) for i in range(len(w) - 4)]
    return 1 - len(set(g)) / len(g) > 0.35


def avalia(item, resposta):
    r = limpa(resposta); vs = list(item.get("verificacao", []))
    if not any(v["tipo"] == "idioma" for v in vs): vs.append({"tipo": "idioma", "valor": "pt"})
    det = []
    for v in vs:
        try: ok, d = checa(v, r)
        except Exception as e: ok, d = False, f"erro no verificador: {e!r}"
        det.append({"tipo": v["tipo"], "ok": bool(ok), "detalhe": str(d)[:120]})
    return {"ok": bool(r) and all(x["ok"] for x in det), "vazia": not r, "repeticao": repeticao(r), "verificacoes": det,
            "idioma": idioma(r), "palavras": len(r.split())}


CAMPOS = ("id", "categoria", "mensagens", "verificacao", "resposta_referencia", "resposta_errada")

if __name__ == "__main__":
    if "--autoteste" not in sys.argv: sys.exit(__doc__)
    arqs = [a for a in sys.argv[1:] if not a.startswith("--")] or sorted(os.path.join(AQUI, "itens", f) for f in os.listdir(os.path.join(AQUI, "itens")) if f.endswith(".jsonl"))
    tot = ruins = 0; ids = set()
    for a in arqs:
        prob = []; n = 0
        for ln, l in enumerate(open(a, encoding="utf-8"), 1):
            if not l.strip(): continue
            try: it = json.loads(l)
            except Exception as e: prob.append(f"linha {ln}: JSON inválido ({e})"); continue
            n += 1; falta = [c for c in CAMPOS if c not in it]
            if falta: prob.append(f"{it.get('id', ln)}: faltam campos {falta}"); continue
            if it["id"] in ids: prob.append(f"{it['id']}: id repetido")
            ids.add(it["id"])
            if it["mensagens"][-1]["role"] != "user": prob.append(f"{it['id']}: a última mensagem não é do usuário")
            a1, a2 = avalia(it, it["resposta_referencia"]), avalia(it, it["resposta_errada"])
            if not a1["ok"]: prob.append(f"{it['id']}: a REFERÊNCIA não passa: " + "; ".join(f"{x['tipo']}({x['detalhe']})" for x in a1["verificacoes"] if not x["ok"]))
            if a2["ok"]: prob.append(f"{it['id']}: a resposta ERRADA passa em tudo")
        tot += n; ruins += len(prob); print(f"{os.path.basename(a)}: {n} itens, {len(prob)} problemas")
        for p in prob: print("   ", p[:260])
    print(f"TOTAL: {tot} itens, {ruins} problemas")
