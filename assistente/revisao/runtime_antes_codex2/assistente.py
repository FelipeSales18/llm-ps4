"""Núcleo do assistente (só biblioteca padrão): transforma conversa + documentos + estado local numa resposta, de acordo com
uma CONFIGURAÇÃO (arquivo JSON). O MESMO código atende a avaliação (aval/roda.py) e o uso real (runtime/conversar.py), para
que o que é medido seja o que é entregue.

Campos da configuração (todos opcionais):
  sistema            instruções do assistente (texto)
  amostragem         parâmetros enviados ao servidor (temperature, top_p, top_k, min_p, presence_penalty, seed)
  raciocinio         true/false liga/desliga o modo de raciocínio do modelo; null deixa o padrão do template
  max_tokens         limite fixo de geração (senão, o do pedido); max_tokens_extra_raciocinio soma quando raciocinio=true
  injeta_data        true: informa data e hora no prompt de sistema (custa ~20 tokens)
  documentos         "colar" (documentos inteiros no contexto), "busca" (só os trechos mais relevantes, BM25) ou "ferramenta"
  trechos_busca      quantos trechos entram no modo "busca" (padrão 4)
  ferramentas        lista entre: calculadora, agora, estado_sistema, busca_documentos (o modelo decide chamar)
  injeta_estado      "nunca" | "regras": com "regras", perguntas sobre a máquina recebem o estado do sistema no contexto
  max_passos         nº máximo de rodadas de ferramenta (padrão 3)"""
import json, re, time, unicodedata
from cliente import conversa
import ferramentas as F

PADRAO = {"nome": "sem_nome", "sistema": None, "amostragem": {}, "raciocinio": None, "max_tokens": None, "max_tokens_extra_raciocinio": 0, "documentos": "colar",
          "trechos_busca": 4, "injeta_data": False, "ferramentas": [], "injeta_estado": "nunca", "max_passos": 3}
_MAQUINA = re.compile(r"\b(temperatura|esquent|quente|memoria|ram\b|disco|espaco|armazenamento|hd\b|ssd\b|uptime|ligad[oa] ha|processo|cpu\b|processador|cabe\b|console|ps4|maquina|computador|sistema)", re.I)


def carrega_config(caminho):
    c = dict(PADRAO); c.update(json.load(open(caminho, encoding="utf-8"))); return c


def _sa(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def monta_mensagens(cfg, mensagens, documentos=None, fixtures=None):
    ms = [dict(m) for m in mensagens]; pergunta = ms[-1]["content"]; sistema = cfg.get("sistema") or ""; extras = []
    if cfg.get("injeta_data"): extras.append("Agora: " + F.agora(fixtures) + ".")
    if cfg.get("injeta_estado") == "regras" and _MAQUINA.search(_sa(pergunta)): extras.append("Estado deste computador:\n" + F.estado_sistema(fixtures))
    if extras: sistema = (sistema + "\n\n" if sistema else "") + "\n".join(extras)
    if documentos and cfg.get("documentos") == "colar":
        ms[-1]["content"] = "\n\n".join(f"[Documento {i + 1}: {d.get('titulo', 'sem título')}]\n{d['texto']}" for i, d in enumerate(documentos)) + "\n\n" + pergunta
    elif documentos and cfg.get("documentos") == "busca":
        ms[-1]["content"] = "Trechos dos documentos do usuário relacionados à pergunta:\n\n" + F.busca_documentos(pergunta, documentos, cfg.get("trechos_busca", 4)) + "\n\nPergunta: " + pergunta
    return ([{"role": "system", "content": sistema}] if sistema else []) + ms


def responde(cfg, url, mensagens, documentos=None, fixtures=None, max_tokens=400, chave=None, ao_receber=None):
    """Uma resposta do assistente. Devolve o dict do cliente (da última chamada ao modelo), com t_primeiro/t_total contados
    desde o início e 'rastro' com todos os passos (modelo e ferramentas)."""
    t0 = time.time(); ms = monta_mensagens(cfg, mensagens, documentos, fixtures)
    nomes = [n for n in cfg.get("ferramentas") or [] if n in F.ESQUEMAS and (n != "busca_documentos" or documentos)]
    esquemas = [F.ESQUEMAS[n] for n in nomes] or None
    mt = (cfg.get("max_tokens") or max_tokens) + (cfg.get("max_tokens_extra_raciocinio", 0) if cfg.get("raciocinio") else 0)
    rastro = []; tp = tr = 0; r = None
    for passo in range(cfg.get("max_passos", 3) + 1):
        ultimo = passo == cfg.get("max_passos", 3)
        r = conversa(url, ms, amostragem=cfg.get("amostragem"), max_tokens=mt, raciocinio=cfg.get("raciocinio"), ferramentas=None if ultimo else esquemas, chave=chave, ao_receber=ao_receber, timeout=cfg.get("tempo_limite_s", 300))
        tp += r["tokens_prompt"] or 0; tr += r["tokens_resposta"] or 0
        rastro.append({"passo": "modelo", "tokens_prompt": r["tokens_prompt"], "tokens_resposta": r["tokens_resposta"], "t": round(r["t_total"], 2), "chamadas": [c["nome"] for c in r["chamadas"]]})
        if not r["chamadas"] or ultimo: break
        ms.append({"role": "assistant", "content": r["texto"] or "", "tool_calls": [{"id": f"c{passo}_{i}", "type": "function", "function": {"name": c["nome"], "arguments": c["argumentos"] or "{}"}} for i, c in enumerate(r["chamadas"])]})
        for i, c in enumerate(r["chamadas"]):
            try: args = json.loads(c["argumentos"] or "{}")
            except Exception: args = {}
            res = F.executa(c["nome"], args if isinstance(args, dict) else {}, documentos, fixtures)
            rastro.append({"passo": "ferramenta", "nome": c["nome"], "args": args, "resultado": res[:300]})
            ms.append({"role": "tool", "tool_call_id": f"c{passo}_{i}", "content": res})
    total = time.time() - t0; ant = total - r["t_total"]
    r["t_primeiro"] = None if r["t_primeiro"] is None else ant + r["t_primeiro"]; r["t_primeiro_texto"] = None if r["t_primeiro_texto"] is None else ant + r["t_primeiro_texto"]
    r["t_total"] = total; r["tokens_prompt_total"] = tp; r["tokens_resposta_total"] = tr; r["rastro"] = rastro
    return r
