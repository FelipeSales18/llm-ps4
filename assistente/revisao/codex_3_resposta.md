Gravei os [três prompts candidatos](revisao/prompts_candidatos.json) e a [análise auditável por ID](revisao/analise_erros.json). Li exclusivamente os cinco arquivos autorizados e só escrevi em `revisao/`.

**Fatos contados nos arquivos.** São os mesmos 120 itens, com entradas, verificações e limites iguais. O 1.7B passou em **67/120 (55,8%)** e falhou em 53. Houve 11 respostas cortadas, das quais sete reprovaram. Os JSONL não incluem os textos dos documentos; diagnósticos documentais têm essa limitação.

**Classificação manual das 53 reprovações.** Atribuí uma causa principal por item; estas causas são interpretações, não campos dos arquivos.

| Causa principal | Quantidade | Dois exemplos curtos |
|---|---:|---|
| Conta ou calendário errado | 13 | `ferramentas-007`: divisão errada; `raciocinio-029`: soma de dias errada |
| Restrição de formato ou transformação | 6 | `instrucoes-017`: número como string; `instrucoes-054`: 38 palavras para limite de 20 |
| Afirmação inventada ou sem base | 3 | `conversa-047`: capital inventada; `documentos-009`: presume upload simétrico |
| Intenção ou dado relevante ignorado | 4 | `raciocinio-007`: ignora rendimento original; `raciocinio-037`: ignora reserva |
| Conhecimento, código ou classificação | 12 | `tecnico-005`: segundo menor em vez de maior; `instrucoes-026`: processador classificado como esporte |
| Estado indisponível pela configuração | 7 | `ferramentas-020`: temperatura ausente; `ferramentas-024`: ocupação do disco ausente |
| Avaliação suspeita como motivo principal | 8 | `documentos-015`: rejeita “desligar”; `documentos-021`: rejeita datas por extenso |
| **Total** | **53** | |

**Corte é uma marca sobreposta:** sete reprovações tiveram corte. Exemplos: `tecnico-004` repete exemplos sem entregar a função; `instrucoes-057` consome o orçamento em subtópicos antes de completar a lista. Corte registrado não demonstra que aumentar tokens corrigiria a resposta.

**Responsabilidade — interpretação.** A divisão principal fica em **38 modelo, sete configuração e oito suspeitas de avaliação**, com contribuições sobrepostas:

- **Modelo:** operações, classificação, conhecimento, código e leitura. Instruções podem ajudar, mas não há ganho demonstrado dos novos prompts.
- **Configuração:** `base0` injeta data e cola documentos, mas não habilita ferramentas nem injeta estado. Os sete itens de estado falham nos dois modelos. Admitir falta de acesso é adequado; `ferramentas-033` ainda inventa RAM disponível a partir da exigência do jogo.
- **Tokens/instruções:** há verbosidade evitável. Nenhuma tarefa do 1.7B demonstra exigir mais tokens que o limite para uma solução concisa.

**Suspeitas de avaliação injusta:**

- `conversa-035`: rejeição exclusivamente por ausência de palavras prescritas; isso não avalia toda resposta pertinente.
- `conversa-024`, `conversa-056`, `conversa-057`: tetos de 150/70/70 palavras não informados ao assistente.
- `documentos-015`: “desligar” não corresponde à substring exigida “desligu”.
- `documentos-021`: “17 de novembro a 28 de novembro” equivale às datas exigidas.
- `instrucoes-032`: a simplificação existe, mas citar o original ativa palavras proibidas implicitamente.
- `tecnico-047`: “unificação” descreve merge, mas falta nas alternativas. Há imprecisão conceitual concorrente; falso negativo não confirmado.
- `tecnico-036`: “totalmente” perde para vocabulário restrito, porém existe erro real sobre datas reconhecidas; manter reprovação.
- No **4B**, também: `instrucoes-020` rejeita “Prata”; `instrucoes-021` impõe objeto/formato de data implicitamente, embora também haja ano acrescentado. Tetos ocultos explicam as reprovações registradas de `conversa-031/016/018/034/059` e `ferramentas-057`.

Há **falsos positivos**: `raciocinio-053` passa nos dois modelos apesar de concluírem 52 e seis semanas, respectivamente; seriam sete. Em `raciocinio-007`, o 4B passa contendo resultados contraditórios. Portanto, as taxas brutas não certificam qualidade integral.

**Prompts propostos — hipóteses.** O JSON contém:

- `conciso_e_formato`: 81 palavras; reduzir verbosidade, cortes e violações estruturais.
- `contexto_e_incerteza`: 87 palavras; preservar condições e admitir informação ausente.
- `calculo_ferramentas_e_codigo`: 89 palavras; melhorar formulação, consulta a ferramentas e entrega de código.

São regras gerais, sem IDs ou gabaritos. JSON e tamanhos foram validados; os prompts ainda não foram executados.

**Ferramentas e roteamento — recomendação.**

- **Estado atual da máquina:** coletar/injetar estado; porcentagens seguem para calculadora. Prompt sozinho não recupera esses dados.
- **Data/hora:** consultar relógio quando ausente; usar calendário determinístico para prazos, fusos e dias da semana. A data já injetada não impediu erros.
- **Calculadora:** encaminhar contas exatas, valores monetários, parcelas, raízes e conversões. Conferir a expressão: condição ignorada também produz cálculo errado.
- **Documentos:** usar o contexto disponível; buscar quando documentos estiverem fora dele ou forem extensos. Recuperar condições e exceções pertinentes.
- **Conversa trivial:** resposta direta.

**Comparação registrada e decisão.**

| Tipo, 20 itens cada | 1.7B | 4B |
|---|---:|---:|
| Conversa | 14 | 12 |
| Instruções | 10 | 17 |
| Documentos | 14 | 18 |
| Raciocínio | 13 | 16 |
| Técnico | 10 | 15 |
| Ferramentas | 6 | 8 |

O 4B ganha em 31 itens e regride em 12: **+15,8 pontos percentuais líquidos**. Tem 46 cortes, contra 11; o tempo total registrado é 3,95 vezes maior, sem comprovação de medição no PS4.

**Minha opinião:** priorizar 1.7B com concisão e ferramentas; reservar 4B para código e instruções complexas. Estes dados não justificam pagar aproximadamente três vezes a latência em toda interação.