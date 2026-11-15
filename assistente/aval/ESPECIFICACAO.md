# Avaliação do assistente local no PS4 — especificação dos itens

Objetivo: medir se o ASSISTENTE (modelo + instruções + ferramentas + parâmetros de geração) resolve tarefas reais, em
português do Brasil, com verificação OBJETIVA sempre que possível. O mesmo item roda no notebook (desenvolvimento) e no PS4.

## Arquivos
Um arquivo JSONL por categoria em `aval/itens/<categoria>.jsonl` (UTF-8, um objeto JSON por linha). Categorias:
`conversa`, `instrucoes`, `documentos`, `raciocinio`, `tecnico`, `ferramentas`. 60 itens por categoria, ids `<cat>-001`…

## Esquema de um item
```json
{
 "id": "raciocinio-001",
 "categoria": "raciocinio",
 "subtipo": "rótulo curto livre (ex.: 'porcentagem', 'datas', 'unidades')",
 "mensagens": [{"role": "user", "content": "..."}],
 "documentos": [{"titulo": "...", "texto": "..."}],
 "fixtures": {"estado_sistema": {...}, "agora": "2026-11-13T10:30:00-03:00"},
 "verificacao": [ ... ],
 "resposta_referencia": "uma resposta CORRETA e natural, que DEVE passar em todas as verificações",
 "resposta_errada": "uma resposta plausível porém ERRADA, que DEVE falhar em pelo menos uma verificação",
 "rubrica": "o que um avaliador humano olharia além das verificações (1–2 frases)",
 "max_tokens": 400
}
```
- `mensagens`: conversa até a vez do assistente. Pode ter turnos anteriores (`assistant` fixos) para testar contexto.
  NÃO inclua mensagem de sistema: o prompt de sistema é do produto. Escreva como um usuário brasileiro real escreveria
  (às vezes informal, com abreviações ou pequenos erros de digitação), sem dizer ao modelo como será corrigido.
- `documentos` (opcional): textos que o usuário "tem" (contas, manuais, e-mails, atas, artigos curtos; 150–900 palavras
  cada; no máximo 3). O produto decide se cola no contexto ou busca neles. A pergunta deve EXIGIR o documento
  (fatos inventados, específicos: nomes, valores, datas), para não ser respondível de memória.
- `fixtures` (opcional): respostas determinísticas das ferramentas locais para este item. `estado_sistema` pode ter
  `cpu_temp_c`, `mem_total_mb`, `mem_livre_mb`, `disco_livre_gb`, `disco_total_gb`, `uptime_h`, `processos` (lista de
  {"nome","cpu_pct","mem_mb"}); `agora` é a data/hora "atual" em ISO 8601.
- `max_tokens`: limite de geração razoável para a tarefa (80–600).

## Verificações (todas precisam passar para o item contar como correto)
Lista de objetos; a verificação é feita sobre a RESPOSTA FINAL em texto do assistente (depois de ferramentas, sem bloco de
raciocínio). Tipos:
- `{"tipo":"contem","valor":"texto","ignora_caixa":true,"ignora_acentos":true}` — substring.
- `{"tipo":"contem_algum","valores":["a","b"],...}` — pelo menos uma das alternativas (use para sinônimos/variações).
- `{"tipo":"nao_contem","valor":"texto",...}`
- `{"tipo":"regex","valor":"expressão Python","flags":"i"}` e `{"tipo":"nao_regex",...}`
- `{"tipo":"numero","valor":1234.5,"tol":0.01,"tol_rel":0.0}` — algum número na resposta é igual ao valor dentro da
  tolerância. A extração aceita formato brasileiro e americano: `1.234,5`, `1234.5`, `1 234,5`, `R$ 1.234,50`, `35%`.
- `{"tipo":"numero_final","valor":...,"tol":...}` — o ÚLTIMO número da resposta.
- `{"tipo":"max_palavras","valor":40}`, `{"tipo":"min_palavras","valor":5}`, `{"tipo":"max_linhas","valor":3}`
- `{"tipo":"n_itens_lista","valor":5}` — número de linhas que começam com marcador (`-`, `*`, `•`) ou `1.`/`1)`.
- `{"tipo":"comeca_com","valor":"..."}`, `{"tipo":"termina_com","valor":"..."}` (ignorando espaços nas pontas)
- `{"tipo":"json_valido","campos":["nome","idade"]}` — a resposta (ou o bloco ```json) é JSON válido com esses campos;
  opcional `"valores":{"idade":34}` para conferir valores exatos.
- `{"tipo":"idioma","valor":"pt"}` — a resposta está em português (heurística por palavras funcionais). Aplicada
  automaticamente a todo item, a menos que o item traga `{"tipo":"idioma","valor":"en"}` ou `"qualquer"`.
- `{"tipo":"codigo_python","testes":["assert f(2)==4","assert f(-1)==1"],"funcao":"f"}` — extrai o primeiro bloco de
  código Python da resposta, executa em sandbox com tempo limite e roda os asserts.
- `{"tipo":"admite_nao_saber"}` — a resposta diz claramente que a informação não está disponível / não sabe / não consta
  (para perguntas sem resposta no documento ou sobre fatos que o modelo não tem como saber). Combine com `nao_contem`
  dos valores que um modelo inventaria.
Regras para escrever verificações:
1. Devem aceitar QUALQUER resposta correta e natural (use `contem_algum`, tolerâncias e regex flexíveis) e rejeitar as
   erradas mais prováveis. Evite depender de uma frase exata.
2. Sempre que a tarefa tiver resposta única (número, nome, data, valor do documento), verifique-a.
3. Para pedidos de formato ("responda em 3 tópicos", "só o número", "em JSON", "no máximo 20 palavras"), verifique o formato.
4. `resposta_referencia` e `resposta_errada` são OBRIGATÓRIAS e servem de autoteste dos verificadores.
5. Nada de itens copiados de benchmarks públicos; escreva tudo do zero, com dados inventados e plausíveis para o Brasil.
6. Confira a aritmética duas vezes. Um gabarito errado invalida o item.

## O que cada categoria deve cobrir (60 itens cada; variar dificuldade: ~1/3 fácil, 1/3 média, 1/3 difícil para um modelo de 1–4 B)
- `conversa`: diálogo útil em PT-BR (explicar, aconselhar, resumir o que o usuário disse, manter contexto de 2–4 turnos,
  lembrar um dado dito antes, pedir esclarecimento quando o pedido é ambíguo, tom adequado, não inventar fatos pessoais).
  Verificações típicas: idioma, retomada de um dado do contexto, tamanho, não inventar.
- `instrucoes`: seguir restrições explícitas (formato, tamanho, estrutura, tom, idioma, o que incluir/excluir, ordem,
  transformar texto: reescrever, traduzir, extrair campos para JSON, classificar em rótulos dados).
- `documentos`: perguntas sobre os `documentos` do item (valor, data, responsável, comparação entre dois trechos,
  condição/exceção, soma de itens de uma tabela em texto) e ~20% de perguntas SEM resposta no documento.
- `raciocinio`: problemas práticos do dia a dia com resposta numérica ou categórica única (troco, juros simples,
  porcentagem, regra de três, unidades, receita, combustível, parcelas, datas e dias da semana com `fixtures.agora`,
  fusos, agendas com restrições, lógica curta). Não dependem de ferramentas, mas podem se beneficiar de calculadora.
- `tecnico`: tarefas de quem mexe com computador (escrever função Python curta testável, corrigir bug, explicar o que
  um comando de shell faz, dar o comando para uma tarefa, regex, SQL simples, Git, interpretar mensagem de erro,
  conceitos de redes/Linux). Sempre que possível com `codigo_python` ou verificação do comando/elemento essencial.
- `ferramentas`: pedidos que só se resolvem bem com ferramentas locais: contas com números grandes ou muitas casas
  (calculadora), perguntas sobre o estado da máquina (`fixtures.estado_sistema`: "tá quente?", "quanto de disco livre?",
  "que processo mais usa memória?"), data/hora (`fixtures.agora`), busca em 2–3 `documentos` longos, e combinações em 2
  passos (ex.: "quanto por cento do disco está ocupado?"). Inclua ~15% de itens em que NÃO se deve usar ferramenta
  (pergunta trivial/conversa), verificando só a resposta. A verificação é sempre sobre a resposta final.
