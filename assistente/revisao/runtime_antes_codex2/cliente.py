"""Cliente mínimo (só biblioteca padrão) do llama-server: conversa por /v1/chat/completions com streaming, medindo o tempo
até o primeiro token, o tempo total e os contadores de tokens devolvidos pelo servidor."""
import json, time, urllib.request


def conversa(url, mensagens, amostragem=None, max_tokens=400, raciocinio=None, ferramentas=None, chave=None, extra=None, timeout=900, ao_receber=None):
    """Devolve dict: texto, raciocinio, chamadas (tool_calls), fim (finish_reason), t_primeiro, t_primeiro_texto, t_total,
    tokens_prompt, tokens_resposta, tempos (do servidor, se vierem)."""
    corpo = {"messages": mensagens, "stream": True, "max_tokens": max_tokens, "stream_options": {"include_usage": True}, "timings_per_token": False}
    corpo.update(amostragem or {})
    if raciocinio is not None: corpo["chat_template_kwargs"] = {"enable_thinking": bool(raciocinio)}
    if ferramentas: corpo["tools"] = ferramentas
    corpo.update(extra or {})
    cab = {"Content-Type": "application/json"}
    if chave: cab["Authorization"] = "Bearer " + chave
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(corpo).encode(), headers=cab)
    t0 = time.time(); r = {"texto": "", "raciocinio": "", "chamadas": {}, "fim": None, "t_primeiro": None, "t_primeiro_texto": None, "tokens_prompt": None, "tokens_resposta": None, "tempos": None}
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for linha in resp:
            linha = linha.decode("utf-8", "replace").strip()
            if not linha.startswith("data:"): continue
            dado = linha[5:].strip()
            if dado == "[DONE]": break
            try: j = json.loads(dado)
            except Exception: continue
            if j.get("usage"):
                r["tokens_prompt"] = j["usage"].get("prompt_tokens"); r["tokens_resposta"] = j["usage"].get("completion_tokens")
            if j.get("timings"): r["tempos"] = j["timings"]
            for ch in j.get("choices", []):
                d = ch.get("delta", {}) or {}
                if d.get("reasoning_content"):
                    if r["t_primeiro"] is None: r["t_primeiro"] = time.time() - t0
                    r["raciocinio"] += d["reasoning_content"]
                if d.get("content"):
                    if r["t_primeiro"] is None: r["t_primeiro"] = time.time() - t0
                    if r["t_primeiro_texto"] is None: r["t_primeiro_texto"] = time.time() - t0
                    r["texto"] += d["content"]
                    if ao_receber: ao_receber(d["content"])
                for tc in d.get("tool_calls") or []:
                    c = r["chamadas"].setdefault(tc.get("index", 0), {"nome": "", "argumentos": ""})
                    f = tc.get("function", {}) or {}
                    c["nome"] += f.get("name") or ""; c["argumentos"] += f.get("arguments") or ""
                if ch.get("finish_reason"): r["fim"] = ch["finish_reason"]
    r["t_total"] = time.time() - t0; r["chamadas"] = [r["chamadas"][k] for k in sorted(r["chamadas"])]
    return r
