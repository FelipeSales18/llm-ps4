Revisei os cinco arquivos e a especificação. **Nenhum arquivo foi alterado; não acessei o conteúdo de `aval/itens/`.** Os trechos abaixo são propostas de correção.

1. **Alta — [aval/verifica.py:35](~/LLM-PS4/assistente/aval/verifica.py:35): extração altera números.**  
   Reproduzido: `-10 20` produz `-10, -20`; `12.34.56` vira `123456`. O sinal é propagado aos números seguintes e o fallback aceita agrupamentos inválidos. Preserve o sinal apenas no primeiro token e remova o fallback das linhas 49–51:

   ```python
   for i, p in enumerate(t.split()):
       out += numeros(("-" if neg and i == 0 else "") + p)
   # Depois das validações explícitas de formato:
   if not vals:
       continue
   ```

2. **Média — [aval/verifica.py:69](~/LLM-PS4/assistente/aval/verifica.py:69): inglês curto passa como português.**  
   Reproduzido: `"The answer is five."` retorna `indefinido`, aceito pelo verificador de português. Há evidência suficiente de inglês, mas o corte de seis palavras a descarta. Remova esse corte:

   ```python
   if pt + en < 2:
       return "indefinido"
   return "pt" if pt >= en else "en"
   ```

   A heurística continuará limitada; respostas numéricas ou contendo apenas código precisam poder permanecer indefinidas.

3. **Média — [aval/verifica.py:74](~/LLM-PS4/assistente/aval/verifica.py:74): “admite não saber” tem falsos positivos e negativos.**  
   Reproduzido: `"O desconhecido chegou ontem."` passa; `"Os documentos não contêm essa informação."` falha. Remova padrões genéricos e acrescente frases explícitas de ausência:

   ```python
   _NAO_SEI = [
       p for p in _NAO_SEI
       if p not in {r"desconhec", r"infelizmente nao"}
   ]
   _NAO_SEI += [r"\bnao contem (?:essa |a )?informacao\b"]
   ```

4. **Alta — [aval/verifica.py:85](~/LLM-PS4/assistente/aval/verifica.py:85) e [linha 145](~/LLM-PS4/assistente/aval/verifica.py:145): validação JSON permissiva e comparação inexata.**  
   Reproduzido: texto com lixo ao redor de `{"idade":34}` passa; `{"x":NaN}` passa sem verificações de valores; arrays podem satisfazer campos destinados a um objeto. `null` e `42`, embora JSON válidos, falham. Campo ausente também pode satisfazer valor esperado `null`.

   Analise o texto inteiro ou o conteúdo inteiro do bloco JSON, rejeitando constantes inválidas. Use exceção para falha, pois `None` representa JSON `null` válido:

   ```python
   def rejeita_constante(s):
       raise ValueError(s)

   b = re.search(r"```json[ \t]*\n(.*?)```", r, re.S)
   j = json.loads(b[1] if b else r, parse_constant=rejeita_constante)
   ```

   Quando houver campos/valores, exija objeto sem desembrulhar arrays. Para valores exatos, preserve tipos JSON e não converta strings em números:

   ```python
   num = lambda x: type(x) in (int, float)
   ok = c in j and num(j[c]) == num(esp) and j[c] == esp
   ```

5. **Baixa — [aval/verifica.py:124](~/LLM-PS4/assistente/aval/verifica.py:124): marcador adicional muda a contagem de listas.**  
   A especificação admite `-`, `*`, `•` e números; o código também aceita `–`. Reproduzido. Para seguir literalmente a especificação:

   ```python
   return sum(bool(re.match(r"\s*(?:[-*•]|\d+[.)])\s+\S", l))
              for l in t.splitlines())
   ```

6. **Alta — [aval/verifica.py:99](~/LLM-PS4/assistente/aval/verifica.py:99) e [linha 115](~/LLM-PS4/assistente/aval/verifica.py:115): código avaliado e sucesso divergem da especificação.**  
   A extração escolhe o maior bloco com `def`, em vez do primeiro. Além disso, basta aparecer `TESTES_OK` no stdout para aprovar, mesmo com `AssertionError` e código de saída 1 — confirmado com subprocesso simulado.

   ```python
   if m:
       return m[0]
   # Após executar:
   ok = p.returncode == 0 and p.stdout.splitlines()[-1:] == ["TESTES_OK"]
   return ok, (p.stdout + p.stderr)[-400:]
   ```

   Isso corrige processos que falharam; uma marca impressa pelo próprio interpretador não comprova execução dos testes contra código hostil.

7. **Alta — [aval/verifica.py:103](~/LLM-PS4/assistente/aval/verifica.py:103): a sandbox não oferece isolamento suficiente.**  
   Por leitura: sem `bwrap`, o código recebe acesso normal aos arquivos e à rede. Com `bwrap`, a raiz inteira continua legível e faltam limites de memória/CPU presentes no outro ramo. `capture_output=True` permite consumo ilimitado de memória; descendentes também precisam ser encerrados.

   **Limites de recursos da biblioteca padrão não constituem uma sandbox de segurança para Python arbitrário.** Sob a restrição de dependências, a opção segura é recusar execução no host até existir isolamento externo validado:

   ```python
   return False, "Execução desativada: sandbox de segurança indisponível"
   ```

   Para manter essa avaliação, use um ambiente isolado com filesystem mínimo, limites de recursos, saída limitada e encerramento do grupo de processos.

8. **Alta — [runtime/cliente.py:18](~/LLM-PS4/assistente/runtime/cliente.py:18): timeout de socket não mede ausência de tokens.**  
   `urlopen(timeout=N)` limita operações bloqueantes; não estabelece um prazo global nem mede progresso semântico. Bytes parciais e heartbeats podem manter leituras avançando sem produzir tokens. O `for linha in resp` também pode esperar uma linha completa. Isso explica **como** a espera pode ultrapassar N; sem registro da conexão, não comprova a causa específica dos 29 minutos. Silêncio absoluto no socket deveria provocar timeout. [Documentação do Python](https://docs.python.org/3.14/library/urllib.request.html).

   Proponho um vigia independente com `monotonic()`. Para interromper efetivamente a leitura, use `socket.shutdown()`. Uma implementação com `http.client` permite guardar o socket antes de `getresponse()`, sem depender dos atributos privados de `urllib`:

   ```python
   stop, expirou = threading.Event(), threading.Event()
   ultimo = [time.monotonic()]

   def vigia():
       while not stop.wait(0.1):
           if time.monotonic() - ultimo[0] >= N:
               expirou.set()
               try:
                   sock.shutdown(socket.SHUT_RDWR)
               except OSError:
                   pass
               return

   threading.Thread(target=vigia, daemon=True).start()
   ```

   Atualize `ultimo[0]` somente com texto, raciocínio ou fragmentos úteis de chamadas de ferramenta; comentários SSE e `usage` não contam. Envolva a leitura em:

   ```python
   finally:
       stop.set()
       if expirou.is_set():
           raise TimeoutError("Sem tokens pelo intervalo configurado")
   ```

   Apenas verificar o relógio dentro do `for` não resolve uma leitura bloqueada.

9. **Alta — [runtime/cliente.py:23](~/LLM-PS4/assistente/runtime/cliente.py:23): interrupções e erros SSE viram respostas normais.**  
   Reproduzido com respostas simuladas: EOF sem conclusão devolve texto parcial com `fim=None`; um evento `{"error":...}` é ignorado. JSON malformado também é descartado silenciosamente. Registre conclusão e propague erros:

   ```python
   if "error" in j:
       raise RuntimeError(j["error"])
   # Marcar recebeu_done ao encontrar [DONE].
   # Depois da leitura:
   if not recebeu_done or r["fim"] is None:
       raise ConnectionError("Streaming incompleto")
   ```

   Assim, `aval/roda.py` não pontua uma resposta parcial como execução concluída.

10. **Média — [runtime/cliente.py:40](~/LLM-PS4/assistente/runtime/cliente.py:40) e [runtime/assistente.py:59](~/LLM-PS4/assistente/runtime/assistente.py:59): IDs e raciocínio são perdidos no histórico de ferramentas.**  
    A sequência `assistant.tool_calls` → `tool.tool_call_id` está estruturada corretamente. Porém, o cliente descarta o ID recebido e inventa `c0_0`; determinados templates exigem formatos específicos. O histórico também omite `reasoning_content`, relevante para templates que preservam raciocínio entre chamadas. [Código do llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/common/chat.cpp).

    ```python
    # Na montagem dos fragmentos:
    if tc.get("id"):
        c["id"] = tc["id"]
    # Usar o mesmo ID no assistant e no resultado tool:
    identificador = c.get("id") or uuid.uuid4().hex[:9]
    mensagem_assistente["reasoning_content"] = r["raciocinio"]
    ```

11. **Média — [runtime/assistente.py:60](~/LLM-PS4/assistente/runtime/assistente.py:60): ferramenta desabilitada ainda executa.**  
    Confirmado com mock: com `ferramentas=[]`, uma chamada produzida pelo modelo a `estado_sistema` chega a `F.executa`. A lista permitida só controla o anúncio ao modelo. JSON inválido ainda é substituído por `{}`, podendo disparar ferramentas sem parâmetros.

    ```python
    if c["nome"] not in nomes:
        raise ValueError("Ferramenta desabilitada")
    args = json.loads(c["argumentos"] or "{}")
    if not isinstance(args, dict):
        raise ValueError("Argumentos devem ser objeto JSON")
    ```

    Valide também campos obrigatórios. Para recuperação pelo modelo, devolva esses erros como mensagens `tool`, sem executar a ferramenta.

12. **Média — [runtime/assistente.py:56](~/LLM-PS4/assistente/runtime/assistente.py:56) e [linha 66](~/LLM-PS4/assistente/runtime/assistente.py:66): métricas de tempo e tokens enganam.**  
    O “primeiro token” considera somente a última chamada. Num teste controlado, o primeiro token inicial chegou em `0,5 s`, mas a métrica retornou `5,3 s`. Chamadas contendo apenas ferramentas sequer marcam esse instante. Ausência de `usage` vira total zero.

    ```python
    if primeiro is None and r["t_primeiro"] is not None:
        primeiro = inicio_chamada - inicio + r["t_primeiro"]
    total_prompt = (None if any(x is None for x in prompts)
                    else sum(prompts))
    ```

    Use `monotonic()` em todas as durações e marque também progresso de ferramentas. `max_tokens` é renovado por rodada: se o limite pretendido for por pedido, mantenha saldo compartilhado.

13. **Média — [runtime/ferramentas.py:42](~/LLM-PS4/assistente/runtime/ferramentas.py:42) e [linha 32](~/LLM-PS4/assistente/runtime/ferramentas.py:32): normalização e formatação alteram contas.**  
    Reproduzido: `max(1,2)` quebra porque vira `max(1.2)`; `round(1.25,1)` vira sintaxe inválida; `5%2` deixa de representar módulo. Além disso, `1/300000` é arredondado para `0,000003`.

    Adote o contrato anunciado no esquema: ponto decimal, vírgula para argumentos, `%` como módulo; porcentagens usam `/100`. Remova as substituições globais conflitantes. Preserve a precisão disponível na saída:

    ```python
    from decimal import Decimal

    def _br(x):
        return format(Decimal(str(x)), "f").replace(".", ",")
    ```

14. **Alta — [runtime/ferramentas.py:16](~/LLM-PS4/assistente/runtime/ferramentas.py:16): a calculadora evita execução de código, mas permite exaustão de recursos.**  
    A whitelist de AST bloqueou `__import__(...).system(...)`. Entretanto, potências aninhadas de expoente 64 contornam o limite atual e fazem inteiros crescerem rapidamente. Examinei a AST, sem calcular esses valores. `1e309` também retorna infinito.

    Limite tamanho da expressão, quantidade de nós e resultados em **cada nó**, com estimativa anterior à potência:

    ```python
    if isinstance(n.op, ast.Pow) and isinstance(a, int) and b > 0:
        if a.bit_length() * b > 8192:
            raise ValueError("Resultado grande demais")
    # Após cada operação:
    if isinstance(v, float) and not math.isfinite(v):
        raise ValueError("Resultado não finito")
    ```

    Aplique também um teto de bits para constantes e demais resultados inteiros.

15. **Média — [aval/roda.py:26](~/LLM-PS4/assistente/aval/roda.py:26) e [linha 54](~/LLM-PS4/assistente/aval/roda.py:54): retomada e saída ocultam falhas.**  
    Por leitura: qualquer ID persistido vira “feito”, inclusive travamentos; reutilizar a saída com outra configuração mistura resultados. No modo paralelo, registros de travamento não provocam o código de saída 3 anunciado.

    ```python
    # Persistir assinatura da configuração/modelo em cada registro.
    feitos = {r["id"] for r in registros
              if r.get("assinatura") == assinatura and "erro" not in r}
    # um() deve devolver reg; após coletar os resultados:
    if any(r.get("travamento") for r in resultados):
        sys.exit(3)
    ```

**Verificação executada:** Python 3.14.8 com `-B`, compilação dos cinco arquivos em memória, exemplos sintéticos dos verificadores/calculadora e mocks de streaming, ferramentas e subprocesso. O vigia abortou em aproximadamente 41 ms para limite de 40 ms, com transporte simulado.

**Somente leitura:** isolamento real da sandbox, crescimento extremo da calculadora, retomada/paralelismo e compatibilidade com servidor real. Não executei código gerado nem modelo. O teste com socket local foi bloqueado pelo ambiente; não validei o streaming em rede.