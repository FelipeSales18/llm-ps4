"""Cliente mínimo (só biblioteca padrão) do llama-server com streaming SSE."""
import http.client, json, socket, threading, time, urllib.parse


def conversa(url, mensagens, amostragem=None, max_tokens=400, raciocinio=None, ferramentas=None, chave=None, extra=None, timeout=900, ao_receber=None):
    """Devolve resposta, chamadas e métricas; timeout mede inatividade útil do streaming."""
    corpo = {"messages": mensagens, "stream": True, "max_tokens": max_tokens, "stream_options": {"include_usage": True}, "timings_per_token": False}
    corpo.update(amostragem or {})
    if raciocinio is not None: corpo["chat_template_kwargs"] = {"enable_thinking": bool(raciocinio)}
    if ferramentas: corpo["tools"] = ferramentas
    corpo.update(extra or {})
    cab = {"Content-Type": "application/json"}
    if chave: cab["Authorization"] = "Bearer " + chave
    u = urllib.parse.urlsplit(url.rstrip("/") + "/v1/chat/completions")
    cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    conn = cls(u.hostname, u.port, timeout=timeout)
    t0 = time.monotonic(); ultimo = [t0]; stop = threading.Event(); expirou = threading.Event(); lock = threading.Lock()
    r = {"texto": "", "raciocinio": "", "chamadas": {}, "fim": None, "t_primeiro": None, "t_primeiro_texto": None, "tokens_prompt": None, "tokens_resposta": None, "tempos": None}
    def vigia():
        while not stop.wait(min(.1, max(.01, timeout / 10))):
            with lock:
                vencido = time.monotonic() - ultimo[0] >= timeout
            if vencido:
                expirou.set()
                try:
                    if conn.sock: conn.sock.shutdown(socket.SHUT_RDWR)
                except OSError: pass
                return
    th = threading.Thread(target=vigia, daemon=True); th.start()
    def progresso():
        with lock:
            agora = time.monotonic()
            if agora - ultimo[0] >= timeout: expirou.set()
            else: ultimo[0] = agora
        falha_travamento()
    def falha_travamento(e=None):
        with lock:
            if time.monotonic() - ultimo[0] >= timeout: expirou.set()
        if expirou.is_set(): raise TimeoutError(f"travamento: nenhum token ou evento útil por {timeout:g} segundos") from e
    try:
        conn.request("POST", (u.path or "/") + ("?" + u.query if u.query else ""), body=json.dumps(corpo).encode(), headers=cab)
        resp = conn.getresponse()
        if resp.status < 200 or resp.status >= 300:
            detalhe = resp.read(1000).decode("utf-8", "replace")
            raise ConnectionError(f"HTTP {resp.status}: {detalhe}")
        buffer = b""; recebeu_done = False
        while True:
            try: linha = resp.readline()
            except (OSError, http.client.HTTPException) as e:
                falha_travamento(e)
                raise ConnectionError("Interrupção durante o streaming SSE") from e
            if not linha: break
            if not linha.endswith(b"\n") and not resp.isclosed():
                buffer += linha; continue
            linha = buffer + linha; buffer = b""
            linha = linha.decode("utf-8", "replace").strip()
            if not linha.startswith("data:"): continue
            dado = linha[5:].strip()
            if dado == "[DONE]": recebeu_done = True; break
            try: j = json.loads(dado)
            except (ValueError, TypeError) as e: raise ConnectionError("Evento SSE contém JSON inválido") from e
            if not isinstance(j, dict): raise ConnectionError("Evento SSE inválido")
            if j.get("error"): raise RuntimeError(f"Erro SSE: {j['error']}")
            if j.get("usage"):
                r["tokens_prompt"] = j["usage"].get("prompt_tokens"); r["tokens_resposta"] = j["usage"].get("completion_tokens")
            if j.get("timings"): r["tempos"] = j["timings"]
            for ch in j.get("choices", []):
                d = ch.get("delta", {}) or {}
                if d.get("reasoning_content"):
                    progresso()
                    if r["t_primeiro"] is None: r["t_primeiro"] = time.monotonic() - t0
                    r["raciocinio"] += d["reasoning_content"]
                if d.get("content"):
                    progresso()
                    if r["t_primeiro"] is None: r["t_primeiro"] = time.monotonic() - t0
                    if r["t_primeiro_texto"] is None: r["t_primeiro_texto"] = time.monotonic() - t0
                    r["texto"] += d["content"]
                    if ao_receber: ao_receber(d["content"])
                for tc in d.get("tool_calls") or []:
                    f = tc.get("function", {}) or {}; nome = f.get("name") or ""; argumentos = f.get("arguments") or ""
                    if nome or argumentos: progresso()
                    c = r["chamadas"].setdefault(tc.get("index", 0), {"nome": "", "argumentos": ""})
                    if tc.get("id"):
                        if c.get("id") and c["id"] != tc["id"]: raise ConnectionError("ID de chamada de ferramenta inconsistente")
                        c["id"] = tc["id"]
                    c["nome"] += nome; c["argumentos"] += argumentos
                if ch.get("finish_reason"): r["fim"] = ch["finish_reason"]
        falha_travamento()
        if not recebeu_done or r["fim"] is None: raise ConnectionError("Streaming SSE incompleto: faltou [DONE] ou finish_reason")
    except (OSError, http.client.HTTPException) as e:
        falha_travamento(e)
        raise ConnectionError("Interrupção durante o streaming SSE") from e
    finally:
        stop.set(); conn.close(); th.join(.2)
    r["t_total"] = time.monotonic() - t0; r["chamadas"] = [r["chamadas"][k] for k in sorted(r["chamadas"])]
    return r
