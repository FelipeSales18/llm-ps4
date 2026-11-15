Implementei as alterações somente nos cinco arquivos permitidos.

- **1 — aplicado:** corrigi a propagação do sinal e removi a interpretação permissiva de números malformados.
- **2 — aplicado:** o idioma não descarta mais respostas curtas com evidência suficiente.
- **3 — aplicado:** removi padrões genéricos de “não sei” e acrescentei a frase explícita de ausência de informação.
- **4 — aplicado:** validação de JSON estrita, rejeição de constantes inválidas e comparação de valores que preserva tipos.
- **5 — aplicado:** removi o travessão longo da contagem de itens de lista.
- **6 — aplicado:** seleção do primeiro bloco de código e aprovação só com saída final `TESTES_OK` e código de saída zero.
- **7 — não aplicado:** a revisão condicionava essa mudança a uma alteração pequena e segura com `bwrap`. O `bwrap` disponível não inicia neste ambiente por restrições de permissão; a detecção agora usa o ramo de limites existente quando ele não funciona.
- **8 e 9 — aplicados:** o cliente usa relógio monotônico para detectar ausência de progresso útil, interrompe a leitura e lança erro com “travamento”. Erros SSE, JSON inválido, interrupções e streams sem conclusão não viram respostas normais.
- **10 — aplicado:** preservei os IDs das chamadas e o raciocínio no histórico de ferramentas.
- **11 — aplicado:** chamadas de ferramentas são verificadas contra a lista habilitada; argumentos inválidos ou incompletos geram mensagem de erro sem executar a ferramenta.
- **12 — parcialmente aplicado:** corrigi a métrica do primeiro token, contabilizei progresso de ferramentas e deixei totais desconhecidos como `None` se faltar `usage`. O limite de tokens continua valendo por rodada.
- **13 — aplicado:** mantive ponto decimal, vírgula como separador de argumentos, `%` como módulo e precisão disponível na formatação.
- **14 — aplicado:** limitei tamanho e complexidade da expressão, tamanho dos inteiros e resultados não finitos.
- **15 — aplicado:** registros incluem assinatura da configuração e retomada ignora erros; travamentos também levam ao código de saída 3 em execução paralela.

**Verificações:** o autoteste terminou com `TOTAL: 360 itens, 0 problemas`. `python3 runtime/ferramentas.py` e testes sintéticos passaram: cinco cenários do cliente, seis casos da calculadora e mocks do assistente para IDs, métricas e bloqueio de ferramenta desabilitada.