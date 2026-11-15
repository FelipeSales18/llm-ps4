"""Ferramentas locais do assistente (só biblioteca padrão, somente leitura, sem rede, sem executar comandos do usuário).
Acesso mínimo: a calculadora avalia apenas aritmética por análise sintática (sem eval); o estado do sistema lê /proc, /sys e
o uso de disco; a busca só enxerga os documentos que o usuário colocou na pasta de documentos (ou os do item, na avaliação).
Na avaliação, `fixtures` substitui relógio e estado da máquina por valores determinísticos."""
import ast, math, operator, os, re, shutil, time, unicodedata
from decimal import Decimal
from collections import Counter

# ---------------------------------------------------------------- calculadora
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUN = {"sqrt": math.sqrt, "raiz": math.sqrt, "abs": abs, "round": round, "arredonda": round, "log": math.log, "ln": math.log, "log10": math.log10, "exp": math.exp,
        "sin": math.sin, "cos": math.cos, "tan": math.tan, "min": min, "max": max, "sum": lambda *a: sum(a), "soma": lambda *a: sum(a), "fatorial": math.factorial, "factorial": math.factorial}
_CONST = {"pi": math.pi, "e": math.e}


def _av(n):
    if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
        if isinstance(n.value, int) and n.value.bit_length() > 8192: raise ValueError("número grande demais")
        if isinstance(n.value, float) and not math.isfinite(n.value): raise ValueError("número não finito")
        return n.value
    if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
        a, b = _av(n.left), _av(n.right)
        if isinstance(n.op, ast.Pow):
            if abs(b) > 4096: raise ValueError("potência grande demais")
            if isinstance(a, int) and isinstance(b, int) and b > 0 and a.bit_length() * b > 8192: raise ValueError("resultado grande demais")
        v = _OPS[type(n.op)](a, b)
        if isinstance(v, int) and v.bit_length() > 8192: raise ValueError("resultado grande demais")
        if isinstance(v, float) and not math.isfinite(v): raise ValueError("resultado não finito")
        return v
    if isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
        v = _OPS[type(n.op)](_av(n.operand))
        if isinstance(v, int) and v.bit_length() > 8192: raise ValueError("resultado grande demais")
        return v
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id.lower() in _FUN and not n.keywords:
        args = [_av(a) for a in n.args]
        if n.func.id.lower() in ("fatorial", "factorial") and (len(args) != 1 or args[0] > 500): raise ValueError("fatorial grande demais")
        v = _FUN[n.func.id.lower()](*args)
        if isinstance(v, int) and v.bit_length() > 8192: raise ValueError("resultado grande demais")
        if isinstance(v, float) and not math.isfinite(v): raise ValueError("resultado não finito")
        return v
    if isinstance(n, ast.Name) and n.id.lower() in _CONST: return _CONST[n.id.lower()]
    if isinstance(n, ast.Tuple): raise ValueError("use ponto como separador decimal e não use separador de milhar")
    raise ValueError("expressão não suportada")


def _br(x):
    """Formata sem descartar casas decimais disponíveis."""
    s = format(Decimal(str(x)), "f"); i, sep, d = s.partition(".")
    sinal = "-" if i.startswith("-") else ""; i = i.lstrip("-")
    i = f"{int(i):,}".replace(",", ".")
    return sinal + i + ("," + d.rstrip("0") if sep and d.rstrip("0") else "")


def calculadora(expressao):
    """Avalia aritmética: + - * / ** % parênteses, sqrt/raiz, abs, round, log, exp, min, max, soma, fatorial, pi."""
    e = str(expressao).strip().replace("×", "*").replace("÷", "/").replace("^", "**").replace("−", "-").replace("R$", "")
    # tolerância a formato brasileiro (o usuário e o modelo escrevem assim): "15%" = 15/100; e, quando NÃO há chamada de função
    # (onde a vírgula separa argumentos), "1.234,56" = 1234.56 e "3,5" = 3.5
    e = re.sub(r"(\d)\s*%(?!\s*[\d(])", r"\1/100", e)
    if not re.search(r"[A-Za-z_]\w*\s*\(", e):
        e = re.sub(r"(?<=\d)\.(?=\d{3}(?:\D|$))(?=[\d.]*,\d)", "", e); e = re.sub(r"(?<=\d),(?=\d)", ".", e)
    try:
        if len(e) > 1000: raise ValueError("expressão longa demais")
        arv = ast.parse(e, mode="eval")
        if sum(1 for _ in ast.walk(arv)) > 128: raise ValueError("expressão complexa demais")
        v = _av(arv.body)
    except ZeroDivisionError: return "Erro: divisão por zero."
    except Exception as ex: return f"Erro: não consegui calcular '{expressao}' ({ex}). Use só números e operadores, com ponto decimal."
    if isinstance(v, complex): return "Erro: resultado não é um número real."
    if isinstance(v, float) and not math.isfinite(v): return "Erro: resultado não finito."
    return f"{expressao} = {_br(v)}" + (f" (valor exato: {v!r})" if isinstance(v, float) and abs(v) >= 1e15 else "")


# ---------------------------------------------------------------- data e hora
_DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]


def agora(fixtures=None):
    from datetime import datetime
    iso = (fixtures or {}).get("agora")
    d = datetime.fromisoformat(iso) if iso else datetime.now().astimezone()
    return f"{_DIAS[d.weekday()]}, {d.day} de {_MESES[d.month - 1]} de {d.year}, {d:%H:%M}" + (f" (fuso {d:%z})" if d.tzinfo else "")


# ---------------------------------------------------------------- estado do sistema (somente leitura)
def _estado_real():
    e = {}
    try:
        m = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo")}; e["mem_total_mb"] = m["MemTotal"] // 1024; e["mem_livre_mb"] = m["MemAvailable"] // 1024
    except Exception: pass
    try:
        u = shutil.disk_usage(os.environ.get("ASSISTENTE_DISCO", "/")); e["disco_total_gb"] = round(u.total / 1e9, 1); e["disco_livre_gb"] = round(u.free / 1e9, 1)
    except Exception: pass
    try: e["uptime_h"] = round(float(open("/proc/uptime").read().split()[0]) / 3600, 1)
    except Exception: pass
    try:
        ts = []
        for z in sorted(os.listdir("/sys/class/hwmon")):
            for f in os.listdir(f"/sys/class/hwmon/{z}"):
                if re.fullmatch(r"temp\d+_input", f): ts.append(int(open(f"/sys/class/hwmon/{z}/{f}").read()) / 1000)
        if ts: e["cpu_temp_c"] = round(max(ts), 1)
    except Exception: pass
    try:
        ps = []
        for p in os.listdir("/proc"):
            if p.isdigit():
                try:
                    s = open(f"/proc/{p}/status").read(); nome = s.split("Name:")[1].split()[0]; rss = int(s.split("VmRSS:")[1].split()[0]) // 1024 if "VmRSS:" in s else 0
                    ps.append({"nome": nome, "mem_mb": rss})
                except Exception: pass
        e["processos"] = sorted(ps, key=lambda x: -x["mem_mb"])[:5]
    except Exception: pass
    return e


def estado_sistema(fixtures=None):
    e = (fixtures or {}).get("estado_sistema") or _estado_real(); ls = []
    if "cpu_temp_c" in e: ls.append(f"Temperatura da CPU: {e['cpu_temp_c']} °C")
    if "mem_total_mb" in e and "mem_livre_mb" in e:
        usada = e["mem_total_mb"] - e["mem_livre_mb"]; ls.append(f"Memória: {e['mem_livre_mb']} MB livres de {e['mem_total_mb']} MB ({usada} MB em uso, {100 * usada / e['mem_total_mb']:.1f}% usada)")
    if "disco_total_gb" in e and "disco_livre_gb" in e:
        oc = e["disco_total_gb"] - e["disco_livre_gb"]; ls.append(f"Disco: {e['disco_livre_gb']} GB livres de {e['disco_total_gb']} GB ({oc:.1f} GB ocupados, {100 * oc / e['disco_total_gb']:.1f}% ocupado)")
    if "uptime_h" in e: ls.append(f"Ligado há {e['uptime_h']} horas ({e['uptime_h'] / 24:.1f} dias)")
    for p in e.get("processos", []):
        ls.append(f"Processo {p.get('nome')}: " + ", ".join(x for x in (f"CPU {p['cpu_pct']}%" if "cpu_pct" in p else "", f"memória {p['mem_mb']} MB" if "mem_mb" in p else "") if x))
    for k, v in e.items():
        if k not in ("cpu_temp_c", "mem_total_mb", "mem_livre_mb", "disco_total_gb", "disco_livre_gb", "uptime_h", "processos"): ls.append(f"{k}: {v}")
    return "\n".join(ls) or "Estado do sistema indisponível."


# ---------------------------------------------------------------- busca em documentos (BM25 em Python puro)
def _tok(s):
    s = "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    return [w for w in re.findall(r"[a-z0-9]+", s) if len(w) > 1]


def trechos(documentos, palavras=130, passo=100):
    """Divide os documentos em trechos de ~130 palavras com sobreposição, respeitando parágrafos quando possível."""
    out = []
    for i, d in enumerate(documentos):
        w = d["texto"].split()
        for j in range(0, max(1, len(w) - palavras + passo), passo):
            out.append({"doc": i, "titulo": d.get("titulo", f"Documento {i + 1}"), "texto": " ".join(w[j:j + palavras])})
            if j + palavras >= len(w): break
    return out


def busca_documentos(consulta, documentos, k=4):
    """Devolve os k trechos mais relevantes (BM25) dos documentos disponíveis, com o título de origem."""
    if not documentos: return "Não há documentos disponíveis."
    ts = trechos(documentos); toks = [_tok(t["titulo"] + " " + t["texto"]) for t in ts]; q = _tok(consulta)
    N = len(ts); md = sum(len(t) for t in toks) / max(1, N); df = Counter(w for t in toks for w in set(t)); sc = []
    for t in toks:
        c = Counter(t); s = 0.0
        for w in q:
            if w in c: s += math.log(1 + (N - df[w] + .5) / (df[w] + .5)) * c[w] * 2.5 / (c[w] + 1.5 * (.25 + .75 * len(t) / md))
        sc.append(s)
    ordem = sorted(range(N), key=lambda i: -sc[i])[:k]
    if not ordem or sc[ordem[0]] <= 0: return "Nenhum trecho relevante encontrado nos documentos."
    return "\n\n".join(f"[{ts[i]['titulo']}] {ts[i]['texto']}" for i in sorted(ordem) if sc[i] > 0)


# ---------------------------------------------------------------- descrição para o modelo (API de ferramentas do llama-server)
ESQUEMAS = {
    "calculadora": {"type": "function", "function": {"name": "calculadora", "description": "Calcula uma expressão aritmética com exatidão. Use para qualquer conta que não seja trivial.",
                    "parameters": {"type": "object", "properties": {"expressao": {"type": "string", "description": "Expressão só com números e operadores, por exemplo: (1250.50 * 12) / 3 ou 2**10 ou sqrt(144)"}}, "required": ["expressao"]}}},
    "agora": {"type": "function", "function": {"name": "agora", "description": "Informa a data, o dia da semana e a hora atuais.", "parameters": {"type": "object", "properties": {}}}},
    "estado_sistema": {"type": "function", "function": {"name": "estado_sistema", "description": "Informa o estado deste computador: temperatura, memória, disco, tempo ligado e processos principais.", "parameters": {"type": "object", "properties": {}}}},
    "busca_documentos": {"type": "function", "function": {"name": "busca_documentos", "description": "Procura nos documentos do usuário os trechos que tratam de um assunto.",
                         "parameters": {"type": "object", "properties": {"consulta": {"type": "string", "description": "Palavras-chave do que procurar"}}, "required": ["consulta"]}}},
}


def executa(nome, args, documentos=None, fixtures=None):
    try:
        if nome == "calculadora": return calculadora(args.get("expressao", args.get("expression", "")))
        if nome == "agora": return agora(fixtures)
        if nome == "estado_sistema": return estado_sistema(fixtures)
        if nome == "busca_documentos": return busca_documentos(args.get("consulta", args.get("query", "")), documentos or [])
        return f"Erro: ferramenta desconhecida '{nome}'."
    except Exception as e:
        return f"Erro ao executar {nome}: {e}"


if __name__ == "__main__":
    for e in ("3847 * 9261", "1234.56 + 10", "2^47", "sqrt(2)", "15 / 100 * 80", "1000 * (1 + 0.012)**24", "fatorial(12)", "max(1,2)", "round(1.25,1)", "5%2", "__import__('os').system('ls')", "10/0"): print(calculadora(e))
    print(agora({"agora": "2026-11-13T10:30:00-03:00"})); print(estado_sistema()[:300])
    print(busca_documentos("multa por atraso no aluguel", [{"titulo": "Contrato", "texto": "O aluguel vence no dia 5. " * 30 + "Em caso de atraso, a multa é de 10% sobre o valor do aluguel."}, {"titulo": "Manual", "texto": "A fritadeira deve ser limpa após o uso. " * 40}])[:300])
