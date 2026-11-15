# Diário — assistente local no PS4 (nova direção do projeto)

Começa em 2026-11-13 00:00. O diário anterior (edição de pesos, fusão, quantização) está em
`../weight-edit/DIARIO.md` e continua sendo a fonte dos números citados aqui.

## 2026-11-13 00:00 — Mudança de direção, revisão do estado e prioridades

### Diretriz do usuário (resumo fiel)
Objetivo principal: **o melhor assistente possível rodando localmente no PS4** — útil, confiável, bom em português, com
tempo de resposta aceitável. A edição de pesos foi um experimento e deixa de ser o centro. Liberdade de abordagem.
Pedidos: revisar o que existe e separar ganho de capacidade / formato / recuperação de perdas / velocidade /
inconclusivo; trabalhar para o produto (avaliação proporcional ao hardware: conversa em PT, instruções, documentos,
raciocínio prático, tarefas técnicas, ferramentas; medir qualidade, erros factuais, repetição, respostas incompletas,
tempo até o primeiro token, tempo total, memória; verificações objetivas; IA maior não é a única evidência; separar
desenvolvimento, seleção e teste final); usar agentes quando ajudar (sem simular colaboração); investigar primeiro
template/tokens/parada/raciocínio/amostragem antes de culpar os pesos (em particular a recomendação oficial do Qwen
contra decodificação gulosa × nossos ecos — como HIPÓTESE); comparar poucas alternativas de modelo; otimização de
instruções com IA maior (GEPA/DSPy); ferramentas locais; recuperação e memória se houver benefício medido; quantização;
otimização no PS4 por medição; edição de pesos só com hipótese específica. Recursos: notebook e PS4 livres; sem Kaggle,
sem GPU de treino, sem serviços pagos novos; o assistente final roda no PS4 sem IA maior, sem notebook e sem internet;
mudanças de sistema reversíveis; ferramentas com acesso mínimo. Antes de cada rodada: problema, por que pode funcionar,
referência, resultado que justifica manter, orçamento e critério de parada. Entrega: melhor configuração pronta, comando
simples para iniciar e conversar, código e artefatos reproduzíveis, comparação com a referência anterior, limitações e
regressões, instruções para voltar à configuração anterior.

### Estado herdado, classificado (o que se sustenta)
| achado | tipo | situação |
|---|---|---|
| GRPO ensinou o formato `#### n` sem mudar o acerto (Kaggle, n=1319) | formato | sustenta (do projeto original) |
| Edições de pesos no modelo original (ganho, posto reduzido, temperatura; 186 edições) | capacidade | sem ganho; negativo restrito a essas famílias e a uma triagem pequena (n=140, sem poder para 1–2 pt) |
| α=1,5 no vetor de tarefa: estrito +4,5 pt, flex inalterado; macro de 8 famílias −0,34 (IC −0,94 a +0,25) | formato | sustenta como formato; capacidade geral ausente; parte do ganho é supressão de eco |
| Fusão do LoRA em bf16 descartou 93% dos elementos do delta (~20% do sinal sobrou); refusão em fp32 reproduz o Kaggle (110/120 saídas idênticas) | recuperação de perda (fusão) | demonstrado em pesos e comportamento; efeito no arquivo do PS4 em medição (F1) |
| Q4_K_M perde ~3,2 pt de acerto frente a Q8_0 (p=0,005), que iguala o Kaggle | recuperação de perda (quantização) | sustenta (auditado); só medido em GSM8K |
| imatrix no Q4_K_M: KL −56%; acerto +1,7 pt (p=0,15); ecos voltam no checkpoint degradado | quantização | inconclusivo no acerto (n sem poder); custo de formato/tempo naquele checkpoint |
| Respostas ~4% mais curtas com α=1,5 (mesmos tok/s) | tamanho de resposta, não velocidade | sustenta |
| Estrito oficial do GSM8K | problema de avaliação | refém do eco `#### <number>`; reportar também o tolerante |
| BBH com limite de 320 tokens | problema de avaliação | cortes e laços; não mede raciocínio |
| n=1319 no PS4 | problema de avaliação | só detecta ≳2,5–3 pt; GSM8K-teste reutilizado ≥10 vezes |
Conclusão que orienta o produto: **nada do que foi feito aumentou capacidade**; o que existe são recuperações de perdas
de um modelo especializado em formato de matemática. Para um assistente geral, esse modelo provavelmente não é a base certa.

### Trabalhos em andamento: o que termina e o que fica preservado
- PS4: F1 (refundido fp32 em Q4_K_M, GSM8K completo) segue até ≈04:10 e fecha a hipótese da fusão no arquivo implantado;
  depois o reteste de determinismo RT (100 questões, ~20 min). F2 (refundido Q8_0, 5 h) ADIADO (`fila_ps4_adiada.txt`).
- Notebook: a triagem de quantização por KL termina (≈1 h; o método vale para qualquer base). ADIADOS, com comandos
  prontos em `../weight-edit/fila_adiada.txt`: GPTQ no formato q4_K, TEST dos candidatos da etapa 1 (`base_gd25`,
  `base_ld25`; aprovados no VAL, expectativa nula), X1, B1, TEST do refundido, D2. Nada foi apagado.
- Referência anterior do produto (preservada, não será sobrescrita): `/mnt/midia/llm-ps4/chat-gpu/comando.txt` —
  `llama-server` Vulkan com `qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf`, `-c 4096 -n 320 --jinja`, template do treino, porta 8081.

### Premissas adotadas (registradas para não perguntar)
1. "Aceitável" = resposta típica completa em até ~30 s e primeiro token em até ~3 s no PS4; um modelo 2–3× mais lento só
   entra se for claramente melhor na avaliação.
2. Memória: o PS4 tem 6,8 GB de RAM (≈4 GB livres); o limite de 1,1 GB do arquivo deixa de valer; teto prático ≈3,5 GB
   de modelo + contexto, a confirmar por medição.
3. O assistente é em PT-BR por padrão; uso típico: conversa, dúvidas, textos, contas, documentos do usuário, tarefas
   técnicas simples, estado do próprio console.
4. O produto é o conjunto (modelo, quantização, template/amostragem, instruções, ferramentas, cliente de conversa).
5. Sem treino: melhorias vêm de escolha de modelo, configuração, instruções, ferramentas, recuperação e quantização.

### Prioridades (em ordem) e por quê
1. **Régua do produto.** Sem uma avaliação própria, qualquer escolha vira opinião; o GSM8K mede a coisa errada e já
   foi gasto. 360 itens novos em PT-BR (6 categorias × 60), com verificação objetiva e autoteste dos verificadores,
   divididos em desenvolvimento / seleção / teste final (120 cada, estratificado). Executor único (API do
   `llama-server`) que mede acerto, idioma, repetição, corte, tempo até o primeiro token, tempo total, tokens e memória.
2. **Diagnóstico de configuração antes de pesos.** Template, tokens especiais, parada, modo de raciocínio, amostragem
   e limites. Hipótese a testar (barata): a decodificação gulosa, que o Qwen desaconselha, contribui para ecos e laços.
3. **Qual modelo.** Comparar poucas bases (o Qwen3-1.7B original como referência, o ajustado atual, e 2–3 alternativas
   até ~4 B) no conjunto de desenvolvimento no notebook; medir velocidade e memória reais no PS4 só dos finalistas.
4. **Ferramentas e fluxo.** Calculadora, data/hora, estado do sistema e busca em documentos, com roteamento simples e
   acesso mínimo; cliente de conversa com um comando. Medir se melhoram a avaliação.
5. **Instruções.** Otimização do prompt de sistema e de exemplos curtos com análise de erros por IA maior, no conjunto
   de desenvolvimento, aceitando mudanças só se o conjunto de seleção confirmar.
6. **Quantização e execução no PS4** do modelo escolhido (imatrix representativa em PT, precisão por tensor, cache de
   prompt, contexto), guiadas por medição dos gargalos.
7. **Teste final** uma única vez, no PS4, contra a referência anterior; entrega com procedimento de reversão.
Edição de pesos: só volta se aparecer hipótese específica (por exemplo, GPTQ no formato q4_K para o modelo escolhido).

### Agentes realmente disponíveis (verificado por uso nesta sessão)
Ferramenta de agentes com modelos Opus, Sonnet e Haiku (e o próprio modelo desta sessão); tipos geral, exploração e
planejamento. Já usados hoje: 2 Opus + 1 Sonnet + 1 Haiku (revisão) e 1 Opus (implementação). Lançados às 00:10:
3 autores de itens (Opus: raciocínio+ferramentas; Opus: documentos+técnico; Sonnet: conversa+instruções) e 2 pesquisas
com fontes (Opus: modelos candidatos e recomendações oficiais de geração; Sonnet: GEPA/DSPy/smolagents/ferramentas no
llama.cpp/recuperação). Regra após o OOM de 22:37: agentes não rodam computação pesada; eu coordeno as máquinas.

## 2026-11-13 08:20 — Madrugada perdida por bloqueio da sessão; retomada
- **O que aconteceu:** às ~00:20 a conta atingiu o limite de uso de 5 horas (os cinco agentes lançados às 00:10 morreram
  com erro 429); o limite voltou às 03:10, relancei os agentes, e em seguida o login da sessão expirou (erro de
  autenticação) até o usuário refazer o login às ~08:05. Nenhum agente chegou a gravar arquivo: `aval/itens/` estava vazio.
  As máquinas continuaram sozinhas (filas independentes da sessão): a triagem de quantização terminou às 03:00 e o PS4
  concluiu F1 (04:25) e o reteste RT (04:52); depois disso o PS4 ficou ocioso ~3 h e o notebook ~5 h.
- **Lição operacional:** agentes consomem a cota do usuário e a sessão inteira para quando ela acaba. Daqui em diante:
  autores em Sonnet (não Opus), gravando em lotes para não perder trabalho; pesquisa pontual feita por mim; e as máquinas
  sempre com fila própria carregada, para não dependerem da sessão.
- **Resultados da linha anterior que fecharam** (detalhe em `../weight-edit/DIARIO.md`, entrada de 13/11 08:15): F1 confirma
  no PS4 que a fusão correta recupera o formato (estrito 66,8→71,7%; ecos 83→1; acerto numérico igual; 5% menos tempo por
  acerto); o PS4 é determinístico (100/100 saídas idênticas no reteste); a imatrix corta pela metade a divergência do
  Q4_K_M e cada degrau de bits (Q5, Q6) corta de novo pela metade.
- **Feito para o produto até aqui:** especificação da avaliação (`aval/ESPECIFICACAO.md`); verificadores objetivos com
  autoteste e execução de código em sandbox (`aval/verifica.py`, testado); cliente com medição de tempo até o primeiro
  token (`runtime/cliente.py`); núcleo do assistente v0 (`runtime/assistente.py`); executor retomável (`aval/roda.py`) e
  resumo com comparação pareada (`aval/resume.py`).
- **Em curso (08:20):** três autores Sonnet escrevendo os 360 itens em lotes, com autoteste a cada lote. Verificação de
  saúde a cada 30 min reprogramada para o projeto novo.
- **Próximos passos imediatos (meus, sem agentes):** conferir a recomendação oficial de geração do Qwen3; fixar a lista
  curta de modelos e baixar os GGUF; experimento E1 de configuração (guloso × amostragem recomendada × raciocínio) sobre
  ecos e laços; medir memória e velocidade dos candidatos no PS4 enquanto os itens ficam prontos.

## 2026-11-13 08:55 — Fontes conferidas; lista curta de modelos; E1 (configuração) pré-registrado e lançado
- **Recomendação oficial do Qwen3** (cartão `Qwen/Qwen3-1.7B`, seção Best Practices, lido hoje): com raciocínio,
  `Temperature=0.6, TopP=0.95, TopK=20, MinP=0` e "DO NOT use greedy decoding, as it can lead to performance degradation
  and endless repetitions"; sem raciocínio, "we suggest using `Temperature=0.7, TopP=0.8, TopK=20, MinP=0`"; para laços,
  `presence_penalty` entre 0 e 2 (1,5 se forem graves), com risco de mistura de idiomas; o raciocínio vem LIGADO por padrão
  e não deve voltar no histórico. O aviso contra o guloso está no item do modo com raciocínio; para o modo sem raciocínio
  a amostragem é "sugerida". Todas as nossas medições até aqui usaram guloso sem raciocínio.
- **Modelos pequenos de 2026 (existência, tamanho e licença conferidos anonimamente na API do Hugging Face; eu não os
  conhecia de antemão — qualidade só se sabe medindo):**
  | candidato | parâmetros | GGUF Q4_K_M | repositório (revisão) | licença | observação |
  | Qwen3.5-2B | 2,27 B | 1,28 GB | unsloth/Qwen3.5-2B-GGUF (f6d5376b) | Apache-2.0 | sucessor direto da nossa base; multimodal |
  | Qwen3.5-4B | 4,66 B | 2,74 GB | unsloth/Qwen3.5-4B-GGUF (e87f1764) | Apache-2.0 | ~2,5× mais lento por token |
  | MiniCPM5-2B | 2,52 B | 1,56 GB | openbmb/MiniCPM5-2B-GGUF (8ad02b78) | Apache-2.0 | cartão declara só en/zh: risco em português |
  | Granite 4.2 3B | ~3 B | 2,24 GB | ibm-granite/granite-4.2-3b-GGUF (c40945d7) | Apache-2.0 | foco em ferramentas/empresa |
  | Gemma 4 E2B | 5,1 B brutos | 3,11 GB | unsloth/gemma-4-E2B-it-GGUF (0314792d) | Apache-2.0 | no limite da RAM do PS4; conferir suporte |
  | referências | 1,72 B | 1,11 GB | Qwen3-1.7B original e o ajustado atual (já no disco) | Apache-2.0 | |
  Fora: Gemma 4 E4B (4,98 GB, não cabe com folga), modelos ≥ 8 B. Download em curso (`modelos/baixa.py`, manifesto com sha).
- **E1 — problema:** ecos do literal `#### <number>` (até 18% das respostas) e laços/cortes em raciocínio longo.
  **Por que pode funcionar:** o guloso prende o modelo em continuações repetitivas; o próprio fabricante desaconselha.
  **Referência:** guloso sem raciocínio (o que sempre usamos). **Intervenções:** amostragem oficial sem raciocínio
  (duas sementes, para medir a variação da própria amostragem) e a mesma com `presence_penalty=1,5`.
  **Dados (só investigação):** 300 questões do GSM8K-TREINO (`gsm_sel`) e 120 itens de BBH do VAL antigo, limite de 320
  tokens; modelo = GRPO bf16 em Q8_0 (o mais propenso a eco). Depois, só o BBH no Qwen3-1.7B original Q8_0.
  **Medidas:** ecos, respostas com repetição, cortes, acerto numérico (flex) e respostas com `Answer:` no BBH.
  **Mantém-se a amostragem recomendada como padrão do produto se:** reduzir ecos+cortes em ≥ 50% sem perder mais de 2 pt
  de acerto numérico (média das duas sementes). Se o acerto cair mais que isso, a hipótese "guloso é o culpado" fica
  rejeitada para o modo sem raciocínio e o guloso continua como referência.
  **Orçamento:** ≤ 2 h de CPU do notebook; interrompe se o servidor falhar.

## 2026-11-13 08:45 — Avaliação congelada; M1 (comparativo de modelos no PS4) pré-registrado e em fila
(Correção de relógio: as duas entradas anteriores foram escritas entre 08:10 e 08:25, não 08:20/08:55.)
- **Avaliação pronta:** 360 itens (6 categorias × 60) escritos por três agentes Sonnet a partir da especificação; autoteste
  `verifica.py --autoteste`: 360 itens, 0 problemas (toda referência passa, toda resposta errada falha), no notebook e no
  PS4. Divisão congelada em `aval/divisao.json` (semente 20261113; 120 dev / 120 seleção / 120 teste, 20 por categoria;
  itens que compartilham documento ficam no mesmo conjunto). Limitações conhecidas dos verificadores (relatadas pelos
  autores): respostas muito curtas não têm idioma verificável; `numero` aceita o gabarito em qualquer ponto da resposta;
  `admite_nao_saber` depende de uma lista de expressões; perguntas "sem resposta" só pegam as invenções previstas.
  Ajuste meu: a heurística de idioma deixou de contar "as", "no", "do" e "São" (nome próprio) como português.
  O conjunto de TESTE não será executado nem lido até a configuração final estar congelada.
- **Runtime:** `runtime/ferramentas.py` (calculadora por análise sintática, sem eval; data/hora; estado do sistema só
  leitura; busca BM25 em Python puro) e `runtime/assistente.py` v1 (ferramentas pela API `tools` do servidor, busca ou
  colagem de documentos, estado injetado por regra). Teste manual no Qwen3.5-2B: a chamada da calculadora funciona, mas é
  FRÁGIL — com a mesma pergunta, acrescentar a linha de data ao prompt de sistema fez o modelo responder de cabeça (e
  errar). Não vou ajustar isso por tentativa: vira experimento no conjunto de desenvolvimento.
- **M1 — problema:** escolher a base do assistente. **Por que pode funcionar:** a geração de 2026 (Qwen3.5, MiniCPM5,
  Granite 4.2, Gemma 4) é mais nova que o Qwen3-1.7B e o modelo atual é especializado em formato de matemática.
  **Referências:** `ref_anterior` (configuração atual do chat: modelo ajustado, sem instruções, raciocínio no padrão,
  320 tokens) e o Qwen3-1.7B original com a configuração neutra `base0`. **Medição:** no PRÓPRIO PS4 (GPU), conjunto de
  desenvolvimento inteiro (120 itens), `ps4/mede_modelo.sh`: acerto por categoria, vazias, cortes, repetição, idioma,
  tempo até o primeiro token, tempo total, tokens/s, memória do processo e do sistema, tempo de carga.
  **Critério para um candidato seguir adiante:** acerto no dev ≥ 8 pontos acima do Qwen3-1.7B original (com 120 itens,
  diferenças menores não se distinguem de ruído) **e** caber na memória (consumo do sistema ≤ ~4 GB) **e** tempo total
  mediano ≤ 30 s; um candidato ≥ 2× mais lento que outro só o supera se ganhar ≥ 8 pontos dele. Os dois melhores seguem
  para ferramentas/instruções e depois para o conjunto de seleção. **Orçamento:** ~6 h de PS4 para 7 execuções;
  interrompo um modelo se não carregar ou se o tempo mediano passar de 90 s.
  Fila do console (`wedit-fila-ps4`): ref_anterior (em curso, 08:28) → Qwen3-1.7B original → Qwen3.5-2B → Qwen3.5-4B →
  MiniCPM5-2B → Granite 4.2 3B → Gemma 4 E2B; cada linha espera o arquivo chegar (`ps4/envia_modelos.sh` copia em sequência).
- **No notebook:** E1 em curso (guloso × amostragem; fim ≈ 10:00); downloads: Qwen3.5-2B, 4B e MiniCPM5 prontos.
- **08:36 — Proteção térmica:** a verificação de saúde mostrou o PS4 em 77–78 °C com a rodada contínua (as rodadas antigas
  descansavam 5 min a cada 50 questões e tinham um vigia). Instalei `ps4/vigia_termico.sh` (tmux `vigia_assistente`), com a
  mesma política do vigia do projeto: pausa todo `llama-server` com a maior leitura ≥ 85 °C e retoma abaixo de 75 °C;
  eventos com epoch em `medidas/vigia_eventos.txt`, para marcar respostas afetadas. Sem pausas até agora.

## 2026-11-13 08:55 — Memória no PS4: o modelo ocupa mais que o arquivo; guarda de memória e P1 pré-registrado
- Pedido do usuário: garantir que os modelos escolhidos CABEM no PS4 e manter verificação a cada meia hora (já agendada:
  aos 17 e 47 de cada hora, enquanto a sessão existir; e as máquinas têm guardas próprias, independentes da sessão).
- **Medição com a rodada em curso (modelo de 1,107 GB, contexto 4096):** processo `llama-server` com 1.295 MB de memória
  ANÔNIMA (só 65 MB mapeados do arquivo) + memória de GPU 1.329 MB de GTT e 551 MB de VRAM; limites do driver: GTT 3.455 MB,
  VRAM 1.024 MB. Ou seja, os pesos existem duas vezes (cópia do processo + GPU): custo real ≈ 2–3× o arquivo.
  Consequência provável: Qwen3.5-2B (1,28 GB) e MiniCPM5 (1,56 GB) cabem; Granite 3B (2,24 GB) fica apertado; Qwen3.5-4B
  (2,74 GB) e Gemma 4 E2B (3,11 GB) provavelmente NÃO cabem com carga total na GPU. A confirmar medindo, não supondo.
- **Guardas instaladas (preservar o acesso ao console):** `ps4/mede_modelo2.sh` não carrega modelo cujo arquivo + 900 MB
  exceda a memória disponível, e desiste (registrando `"cabe": false`) se após a carga sobrarem < 400 MB ou o swap crescer
  > 300 MB; `ps4/vigia_termico2.sh` encerra o `llama-server` se a memória disponível cair abaixo de 150 MB, além da pausa
  térmica (≥ 85 °C). As linhas pendentes da fila do console já usam o script novo.
- **P1 — problema:** a cópia dupla dos pesos limita o tamanho de modelo utilizável. **Por que pode funcionar:** o servidor
  tem modos de carga (`--load-mode mmap|dio`, `--no-host`) que podem evitar a cópia anônima. **Referência:** carga padrão.
  **Medidas:** memória anônima e mapeada do processo, GTT/VRAM, memória disponível, tempo de carga, tokens/s de geração e
  de prompt, com o mesmo modelo de 1,1 GB em 6 variantes (~1 min cada). **Mantém-se** a variante que reduzir o consumo do
  sistema em ≥ 25% sem perder mais de 5% de tokens/s. Entra na fila do console logo após a referência, antes dos modelos.
- 08:50: os candidatos rodam com `-np 1` (um slot: o prefixo do prompt de sistema fica em cache entre pedidos, como no uso real; a referência anterior fica como estava, com os 4 slots padrão). Downloads dos 5 candidatos concluídos (manifesto em `modelos/MANIFEST.json`).

## 2026-11-13 09:10 — GPU do PS4 TRAVADA desde 08:44 (precisa de reinício manual); erro de protocolo meu; continuação por CPU
- **Fato:** às 08:44:32, 16 min depois de iniciar a referência no PS4, o kernel registrou `amdgpu … ring comp_1.0.0 timeout`
  (processo `llama-server`) e `GPU reset begin!` — o reinício da GPU nunca terminou: o trabalhador do kernel
  `amdgpu-reset-dev` está em estado D (ininterrupto), o `llama-server` virou zumbi e novas inicializações do Vulkan falham
  (`amdgpu_query_gpu_info_init failed`, `Failed to initialize parser -125`). A memória de GPU (1,9 GB) ficou presa.
  O console responde por ssh; a CPU funciona. **A GPU só volta com reinício do PS4, que é manual (o Linux do console
  depende do procedimento de boot do usuário): NÃO vou reiniciar.** Registro do kernel guardado em
  `medidas/ref_anterior/kernel_travamento_0844.txt` (no PS4). A verificação das 09:02 detectou (38 itens parados há 14 min).
- **Causa provável (hipótese apoiada no histórico do projeto):** uso contínuo e quente da GPU. O único travamento anterior
  (08/11, questão 197) também veio após ~45 min de servidor contínuo a 77 °C; as cinco rodadas completas seguintes, com o
  protocolo de blocos de 50 questões + reinício do servidor + descanso até esfriar, somaram ~22 h sem travar. Hoje rodei
  contínuo, com raciocínio ligado e 4 slots, a 77–78 °C. **Erro meu:** meu executor novo abandonou o protocolo de blocos do
  projeto; vi a temperatura às 08:35 e só acrescentei a pausa a 85 °C.
- **Consequências para o produto (achado de confiabilidade, não só de avaliação):** (1) o assistente precisa de um vigia de
  travamento (sem tokens por N segundos ⇒ encerrar o servidor) e de um modo de CPU como reserva; (2) uso longo e quente da
  GPU é arriscado: ciclos curtos, descanso e limite de temperatura bem abaixo de 77 °C; (3) um travamento exige reinício
  manual do console — é uma limitação séria e vai para o relatório.
- **Fila do PS4 parada** (arquivo PARAR); 38/120 itens da referência gravados (retomável). Vigia térmico/memória segue ativo.
- **Outro achado de memória:** o `llama-server` tem cache de prompts em RAM com padrão de 8192 MiB (`--cache-ram`); no
  notebook o servidor do E1 chegou a 8,8 GB e empurrou 5 GB para o swap. No PS4 (6,9 GB) esse padrão é perigoso: o produto
  e as medições passam a fixar `--cache-ram` pequeno.
- **Plano até o usuário reiniciar o console:** qualidade dos modelos medida no NOTEBOOK (CPU; o acerto não depende do
  backend de forma relevante — nas rodadas antigas o flex coincidiu entre CPU e GPU), e no PS4 só medições em CPU
  (modo de reserva). Velocidade/memória em GPU e o teste P1 ficam para depois do reinício, já com protocolo de blocos.

## 2026-11-13 13:20 — Sessão bloqueada 09:35–13:10 (limite de uso); E1 concluído: o guloso NÃO explica ecos nem laços; M1 no notebook
- **Bloqueio:** o limite de uso da conta parou a sessão de novo por ~3,5 h. O E1 terminou sozinho às 11:01; o notebook ficou
  ocioso 2 h depois disso. O PS4 saiu da rede às 09:33 (reinício pelo usuário, presumo) e ainda não voltou (13:12).
  Medida tomada: tudo que é rodada longa passa a ser script encadeado independente da sessão, com o passo seguinte já
  incluído, e eu gasto menos mensagens.
- **E1 (critério escrito antes: manter a amostragem recomendada se reduzir ecos+cortes ≥ 50% sem perder > 2 pt):**
  | modelo ajustado (bf16, Q8_0), 300 questões do GSM8K-treino | acerto | estrito | ecos | cortadas |
  | guloso | 83,0% | 212 | 41 | 7 |
  | amostragem oficial sem raciocínio, semente 42 | 82,3% | 204 | 43 | 9 |
  | idem, semente 7 | 82,3% | 215 | 36 | 9 |
  | BBH, 120 itens, limite de 320 tokens | acerto | com `Answer:` | cortadas | repetição |
  | ajustado, guloso | 56 | 72 | 52 | 12 |
  | ajustado, oficial (sementes 42 / 7) | 46 / 56 | 61 / 68 | 59 / 52 | 18 / 6 |
  | original, guloso / oficial | 47 / 45 | 57 / 59 | 58 / 63 | 12 / 9 |
  Ecos 41 → 43 / 36 (p=0,87); acerto −0,7 pt (p=0,85); cortes e repetição no BBH sem melhora (as duas sementes da própria
  amostragem diferem entre si tanto quanto do guloso). **Hipótese rejeitada para o modo sem raciocínio:** a decodificação
  gulosa não é a causa dos ecos nem dos cortes. Os ecos são do checkpoint degradado pela fusão (somem no refundido e no
  Kaggle); os cortes do BBH são do limite de 320 tokens. O aviso do fabricante vale para o modo COM raciocínio, que não
  testei aqui. Decisão: a amostragem não é alavanca de qualidade nesta configuração; uso a sugerida pelo fabricante por
  padrão (não piora) e trato guloso × amostragem como detalhe, não como correção.
- **M1 passou para o notebook (13:13):** `aval/m1_notebook.sh` (independente da sessão, retomável), conjunto de
  desenvolvimento, CPU, 4 slots: Qwen3.5-2B → Qwen3-1.7B original → referência anterior → MiniCPM5-2B → Qwen3.5-4B →
  Granite 4.2 3B → Gemma 4 E2B. Mede QUALIDADE; velocidade e memória no PS4 ficam para quando o console voltar
  (`ps4/mede_modelo3.sh`, protocolo de blocos, pronto para enviar).

## 2026-11-13 14:10 — M1 parcial (notebook); P1 (memória) resolvido; SEGUNDO travamento da GPU, agora com o Qwen3.5-2B
- **M1, conjunto de desenvolvimento (120 itens), notebook/CPU** (`aval/resultados/m1nb_*_dev.jsonl`, `aval/resume.py`):
  | execução | acerto | conversa | documentos | ferramentas | instruções | raciocínio | técnico | vazias | cortadas |
  | referência anterior (ajustado, sem instruções, raciocínio ligado, 320 tokens) | 25,0% | 50 | 40 | 10 | 45 | 0 | 5 | 67 | 90 |
  | Qwen3-1.7B original + base0 | 56,7% | 70 | 70 | 30 | 55 | 65 | 50 | 0 | 11 |
  | Qwen3.5-2B + base0 | 50,0% | 35 | 70 | 25 | 80 | 55 | 35 | 0 | 48 |
  | MiniCPM5-2B + base0 | 56,7% | 60 | 80 | 30 | 70 | 40 | 60 | 0 | 17 |
  Contra o Qwen3-1.7B original: referência anterior −31,7 pt (IC95% −41,7 a −20,8; p=7e-8); Qwen3.5-2B −6,7 (p=0,28);
  MiniCPM5-2B 0,0 (p=1). **Pelo critério (≥ +8 pt), nenhum modelo de 2 B supera o Qwen3-1.7B original.** O grande ganho
  até aqui é de CONFIGURAÇÃO: a referência anterior devolve 67 respostas vazias em 120 porque o raciocínio (ligado por
  padrão) consome os 320 tokens. Ressalva de avaliação: 48 respostas do Qwen3.5-2B foram cortadas pelo limite do item
  (só 14 delas corretas); o modelo é prolixo (170 tokens em média contra 119) — pode estar sendo penalizado por limites
  apertados; a conferir antes de descartá-lo de vez. Em curso: Qwen3.5-4B, depois Granite 3B e Gemma 4 E2B.
- **P1 (modos de carga, PS4/GPU, modelo de 1,1 GB) — resolvido:** com `--cache-ram 256 -np 1` a memória anônima do processo
  cai de 1.295 MB para 60–80 MB: a "cópia dupla" era o cache de prompts e os 4 slots, não os pesos. Consumo do sistema
  1,1–1,4 GB (GTT 1,06–1,3 GB + VRAM até 1 GB); `--load-mode mmap` economiza mais ~280 MB e carrega em 4 s; geração
  12,1 tok/s em todas as variantes. Logo o custo real é ≈ 1,2× o arquivo e o Qwen3.5-4B (2,74 GB) caberia. Adoto
  `--load-mode mmap --cache-ram 256 -np 1` como padrão do servidor no PS4 (critério: ≥ 25% menos consumo sem perder velocidade — atendido frente ao que rodava de manhã).
- **Segundo travamento da GPU, 13:32:59:** 6 segundos depois do PRIMEIRO pedido ao Qwen3.5-2B, a 69 °C, logo após o P1
  rodar seis cargas do Qwen3-1.7B sem problema. Kernel: `ring comp_1.1.0 timeout`, reinício da GPU em laço. Portanto NÃO é
  só calor: o Qwen3.5-2B (arquitetura nova) derruba o Vulkan deste console na primeira geração. (O travamento da manhã foi
  com o modelo ajustado, raciocínio ligado e 4 slots, após 16 min; causa ainda em aberto.) O limite de tempo do cliente
  não disparou (29 min parado): precisa virar um vigia por relógio. Fila do console parada; a GPU precisa de novo reinício.
- **Decisões:** (1) arquiteturas novas NÃO vão mais para a GPU do PS4 sem necessidade: como nenhum modelo de 2 B supera
  o Qwen3-1.7B original, não há motivo para arriscar; (2) a base do assistente tende a ser o Qwen3-1.7B original, estável
  em ~22 h de GPU; o 4B só entra se ganhar ≥ 8 pt no notebook, e então é testado primeiro em CPU no console;
  (3) próximo passo de maior retorno: configuração, limites de resposta, ferramentas e instruções sobre o Qwen3-1.7B.

## 2026-11-13 15:05 — Terceiro travamento da GPU; Codex como agente; M1 quase completo; C1 encadeado
- **GPU (14:22):** travou pela 3ª vez, agora com o Qwen3-1.7B original, 4 min após o início, a 70 °C, com `--load-mode mmap
  --cache-ram 256 -np 1`, no bloco 1 (25 itens feitos; maior prompt processado 704 tokens; o seguinte teria ~720). O vigia por
  relógio encerrou a medição e a fila parou sozinha. Comum aos 3 travamentos e ausente das ~22 h antigas: meu cliente (streaming)
  e prompts longos (documentos). Hipótese a testar com UM teste curto após o próximo reinício: processar o prompt em lotes
  pequenos (`-b`/`-ub`). Decisão do usuário (14:40): terminar primeiro tudo o que dá no notebook; PS4 depois.
- **Delegação:** o usuário autorizou o Codex CLI no lugar dos subagentes (modelos sol, luna, terra; nunca astra). Tarefa 1
  (sol, só leitura): revisão com 15 achados em `revisao/codex_1_resposta.md`. Tarefa 2 (gpt-6-luna): correções aplicadas em
  cliente (vigia por relógio, erros de SSE), assistente (ferramenta desabilitada não executa, ids, métricas), calculadora
  (limites de recursos) e verificadores (números, JSON estrito, código); autoteste 360/0 conferido por mim; reverti a
  remoção da vírgula decimal/“15%” na calculadora. Resultados antigos repontuados com `aval/repontua.py` (≤ 2 acertos de
  diferença por execução). Tarefa 3 (sol): análise das 53 falhas do Qwen3-1.7B no dev (`revisao/codex_3_resposta.md`,
  `analise_erros.json`): 38 do modelo (13 contas/calendário), 7 de configuração (estado da máquina indisponível), 8 suspeitas
  de avaliação (tetos de palavras não informados ao assistente, substrings rígidas) e 2 falsos positivos. Três prompts
  candidatos em `revisao/prompts_candidatos.json`.
- **M1 (dev, notebook, repontuado):** referência anterior 25,0%; Qwen3-1.7B original 55,8%; Qwen3.5-2B 48,3%; MiniCPM5-2B
  56,7%; Granite 4.2 3B 63,3% (+7,5; p=0,19; 58 cortes); **Qwen3.5-4B 71,7% (+15,8; IC +5,0 a +25,8; p=0,004; 46 cortes;
  ~4× o tempo total)**. Pelo critério, só o 4B supera o 1.7B; mas é lento e é da família que travou a GPU. Gemma em curso.
- **C1 (pré-registro):** problema = falhas de configuração e instrução no Qwen3-1.7B. Intervenções (cada uma contra `base0`
  no MESMO servidor/rodada, dev): três prompts do Codex; estado do sistema injetado por regra; calculadora por chamada do
  modelo; documentos por busca BM25. Mantém-se o que ganhar ≥ 5 pt no dev sem piorar tempo mediano em mais de 30%; a
  combinação vencedora vai ao conjunto de SELEÇÃO, e só fica se lá repetir ganho > 0 com IC que exclua perda de 5 pt.
  Também: prompt conciso no Qwen3.5-4B (reduz cortes?). Orçamento ≈ 2,5 h de notebook (`aval/c1_notebook.sh`).

## 2026-11-13 16:05 — M1 fechado; C1: instruções curtas PIORAM; ferramentas ajudam só na categoria delas; C2 encadeado
- **M1 final (dev, repontuado):** chat atual 25,0%; Qwen3.5-2B 48,3%; Qwen3-1.7B 55,8%; MiniCPM5-2B 56,7%; Gemma 4 E2B 62,5%
  (+6,7; p=0,24); Granite 4.2 3B 63,3% (+7,5; p=0,19); Qwen3.5-4B 71,7% (+15,8; p=0,004). Só o 4B passa no critério.
- **C1 (Qwen3-1.7B, dev, mesma rodada; `base0` repetida deu 59,2% — a mesma configuração variou 3,4 pt entre rodadas com 4
  slots em paralelo, o que dá a escala do ruído):**
  | configuração | acerto | ferramentas | raciocínio | técnico | documentos | tokens | tempo mediano |
  | base0 | 59,2% | 30 | 70 | 65 | 65 | 123 | 13,4 s |
  | prompt conciso (Codex) | 46,7% (−12,5; p=0,03) | 20 | 40 | 30 | 65 | 34 | 5,3 s |
  | prompt contexto (Codex) | 48,3% (−10,8; p=0,04) | 20 | 40 | 30 | 60 | 41 | 5,2 s |
  | prompt cálculo (Codex) | 56,7% (−2,5) | 35 | 45 | 50 | 75 | 61 | 8,3 s |
  | base0 + estado por regra | 56,7% (−2,5) | 40 | 55 | 55 | 65 | 121 | 13,4 s |
  | prompt cálculo + calculadora + estado | 56,7% (−2,5) | **75** | 55 | 25 | 40 | 40 | 11,4 s |
  | base0 + busca BM25 | 54,2% (−5,0; p=0,18) | 25 | 55 | 50 | 70 | 127 | 12,9 s |
  **Pelo critério (≥ +5 pt), nada se mantém.** Leituras: (1) mandar o modelo pequeno ser breve corta o raciocínio em voz
  alta e derruba contas e código — as três instruções do Codex são DESCARTADAS; (2) ferramentas funcionam onde importam
  (categoria ferramentas 30→75), mas vieram junto com o prompt curto, que derrubou técnico e documentos; (3) busca em vez de
  colar não ajuda com documentos curtos. Próximo teste isola as ferramentas com a instrução original.
- **C2 (pré-registro; mesmo critério do C1):** `base0` de novo (referência da rodada) × `c2_ferr` (base0 + calculadora +
  estado por regra) × `c2_ferr_dica` (mais uma frase mandando usar a calculadora) × `c2_rac` (raciocínio ligado, amostragem
  oficial, +700 tokens; mede também o custo em tempo). Encadeado após o prompt conciso no Qwen3.5-4B (em curso).
- Codex tarefa 4 (terra): auditoria de justiça dos 360 itens entregue em `revisao_itens/auditoria_itens.json`; a revisar.

## 2026-11-13 16:15 — PAUSA a pedido do usuário
- Encerrados às 16:13: `c1_notebook.sh` (parou no prompt conciso do Qwen3.5-4B, 113/120), `c2_notebook.sh` e `c3_notebook.sh`
  (não chegaram a rodar), servidor local, verificação periódica. Nenhum agente em execução. PS4 sem resposta por ssh no
  momento da pausa (fila do console já estava parada com o arquivo PARAR; não consegui parar o vigia térmico nem confirmar o estado).
- Estado, comandos de retomada e próximos passos em `RETOMADA.md`. Nada foi apagado; a configuração anterior do chat no
  PS4 não foi alterada. Conjuntos de seleção e teste continuam intocados.

## 2026-11-14 19:50 — Retomada
- Autoteste 360/0. Notebook NA BATERIA (avisado ao usuário). PS4 fora da rede. Relançados c1 (resto), c2 e c3 encadeados.
- **19:58 — Auditoria de justiça dos itens aplicada (itens v2).** O Codex (terra, sem ver respostas de modelos) propôs 90
  mudanças: 52 restrições cobradas mas não pedidas ao assistente (tetos de palavras etc.), 32 verificações rígidas, 4
  frouxas, 2 gabaritos suspeitos. Apliquei as 82 que tinham verificação proposta e passam no autoteste (referência passa,
  errada falha); 7–8 casos sem proposta ficaram como estavam (exigem reescrever exemplos). Originais em
  `aval/itens_v1_antes_auditoria/`. Autoteste: 360/0. A divisão dev/sel/teste não muda (mesmos ids); o sha dos arquivos em
  `divisao.json` refere-se à v1. Tudo repontuado com `aval/repontua.py` (cópias `.antes`). Dev, itens v2:
  chat atual 27,5%; Qwen3.5-2B 54,2%; Qwen3-1.7B 58,3% (63,3% na 2ª rodada); MiniCPM5 60,0%; Granite 67,5%; Gemma 68,3%;
  Qwen3.5-4B 77,5%. As conclusões não mudam de sentido. O prompt conciso no Qwen3.5-4B deu 57,5% (−20 pt): brevidade
  imposta piora também o modelo maior.

## 2026-11-14 21:10 — C2 e C3 concluídos (dev, itens v2); S1 (seleção) pré-registrado e lançado
- **C2 (Qwen3-1.7B, mesma rodada):** base0 59,2%; `c2_ferr` (calculadora + estado por regra) 60,8% (+1,7); **`c2_ferr_dica`
  (o mesmo + uma frase mandando usar a calculadora) 66,7% (+7,5; IC95% 0,0 a +15,8; +17/−8; p=0,11)**, ferramentas 30→70,
  tempo mediano 15,2 s contra 14,3 s; `c2_rac` (raciocínio ligado, +700 tokens) 57,5% (−1,7), 17 respostas vazias e tempo
  mediano 51,5 s (3,6×). Critério do C1/C2 (≥ +5 pt sem piorar o tempo > 30%): **só `c2_ferr_dica` passa**; raciocínio
  ligado é DESCARTADO neste modelo (não melhora e triplica o tempo).
- **C3 (modelo ajustado do usuário com a mesma base0):** publicado (bf16) 59,2% (0,0 contra o original; 7/7); refundido
  fp32 57,5% (−1,7; 5/7). **O original NÃO é melhor que o ajustado para uso geral: empatam.** A diferença de 27,5% × ~59%
  do chat atual é toda de configuração (raciocínio ligado + 320 tokens + sem instruções).
- **S1 — confirmação no conjunto de SELEÇÃO (primeiro e único uso para esta decisão):** `c2_ferr_dica` × `base0`, Qwen3-1.7B.
  Critério escrito antes (do C1): fica se o ganho for > 0 com IC95% que exclua perda de 5 pt. Depois, no dev, a mesma
  configuração no Qwen3.5-4B (as ferramentas somam no modelo maior?).

## 2026-11-14 21:50 — S1: a configuração com ferramentas é REJEITADA no conjunto de seleção
- Qwen3-1.7B, 120 itens de seleção (primeiro uso), mesma rodada: `base0` 65,0% (78/120) × `c2_ferr_dica` 55,8% (67/120);
  **Δ −9,2 pt (IC95% −17,5 a −0,8; +9/−20; p=0,06)**. Por categoria (base0→ferramentas): instruções 60→30, conversa 55→45,
  documentos 60→50, técnico 75→65, ferramentas 65→70, raciocínio 75→75. Tempo mediano 18,4 s → 17,2 s.
- **Decisão pelo critério escrito antes (ganho > 0 com IC excluindo perda de 5 pt): REJEITADA.** O +7,5 do dev não se
  repetiu; virou perda. O ganho na categoria "ferramentas" que aparecia no dev (30→70) quase some na seleção (65→70),
  onde a configuração neutra já acerta 65% desses itens, e o custo aparece nas outras categorias — sobretudo instruções.
  Não investiguei o porquê nos itens de seleção, para não gastá-los como desenvolvimento; hipótese não testada: a presença
  do esquema de ferramentas no prompt muda o formato das respostas (JSON, listas) em pedidos que não precisam de ferramenta.
- **Estado da configuração:** a melhor configuração CONFIRMADA continua sendo a neutra `configs/base0.json` (instrução curta
  em português, raciocínio desligado, data injetada, documentos colados). Dev 58–63%, seleção 65,0%; contra 27,5% do chat
  atual no dev. Nenhuma instrução nova, ferramenta, busca ou raciocínio ligado superou a neutra de forma confirmada.
- O conjunto de seleção foi usado UMA vez para esta decisão; qualquer nova variante de ferramentas precisa nascer no dev e
  só voltar à seleção com hipótese nova (por exemplo, ferramentas acionadas por regra, sem expor o esquema ao modelo).
- Em curso até o fim, sem decisão pendente: `c2_ferr_dica` no Qwen3.5-4B (dev). Nada mais será iniciado.

### 15/11 — resultado do último passo do S1 (Qwen3.5-4B, dev, terminou 14/11 22:37)
- Qwen3.5-4B, dev, notebook/CPU: base0 77,5% (93/120) × `c2_ferr_dica` 85,8% (103/120); Δ +8,3 pt (IC95% +1,7 a +15,8; +15/−5; p=0,04). Ferramentas 45→85%, instruções 80→90%; demais iguais (±5). 1 erro; tempo mediano 64→86 s, 1º token 4,5→13 s.
- Leitura: é resultado de DESENVOLVIMENTO. No Qwen3-1.7B o mesmo ganho no dev (+7,5) virou −9,2 na seleção; portanto isto NÃO aprova ferramentas no 4B. Diferença a notar: no 4B a categoria instruções não caiu no dev (no 1.7B também não caía no dev). Só uma rodada de seleção decide.
- Nada mais foi iniciado (instrução do usuário: parar após a decisão).

### 15/11 14:11 — chat do PS4 trocado para a configuração neutra (pedido do usuário)
- Original intocado: `/mnt/midia/llm-ps4/chat-gpu/comando.txt` (sha256 c456bfd3…) e `models/proprios/chat_template_treinado.jinja`.
- Novo: `/mnt/midia/llm-ps4/assistente/chat-neutro/comando.txt` + `chat_template_neutro.jinja` (cópia do template com instrução de sistema padrão de base0 + data via `strftime_now` quando o cliente não manda system). Flags mudadas: `-n 400 --reasoning off --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0 --cache-ram 256`. Mesmo modelo (GRPO publicado Q4_K_M), GPU, porta 8081, mesma chave.
- Rodando em tmux: `TMUX_TMPDIR=/mnt/midia/llm-ps4/chat-gpu/tmux tmux attach -t chat-neutro`; log em `chat-gpu/logs/llama-server_chat_neutro_*.log`.
- Teste: 1 pergunta (data + 15% de 240) → correta, sem raciocínio, 91 tokens, 11,9 tok/s, sem timeout de GPU. Não é medição.
- Diferença para base0 medido: sem semente fixa; se a interface web mandar amostragem/system próprios, eles prevalecem.
- Reverter: `tmux kill-session -t chat-neutro` e iniciar com o `comando.txt` original.
- 15/11 14:40 — comando `assistente` no PS4 (`~/.local/bin/assistente`): sobe o servidor em tmux se preciso e abre `runtime/conversar.py` com `chat-neutro/config.json` (base0 sem semente). Runtime do PS4 atualizado (anterior em `assistente/runtime_antes_20261115`). Testado com servidor real: 1 pergunta ok. PS4 não tem ambiente gráfico nem navegador (só tty + biblioteca wayland); interface web no próprio console exigiria instalar compositor + navegador — não feito, depende do usuário.
