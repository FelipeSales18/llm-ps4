#!/usr/bin/env python3
"""Monta relatorio.md a partir de analise_dados.json, extra_dados.json, dos CSVs e da
classificação manual dos 40 erros (abaixo)."""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(f"{HERE}/analise_dados.json"))
X = json.load(open(f"{HERE}/extra_dados.json"))
G = {int(r["idx"]): r for r in csv.DictReader(open(f"{HERE}/eval/eval_grpo.csv"))}
B = {int(r["idx"]): r for r in csv.DictReader(open(f"{HERE}/eval/eval_base.csv"))}

# ---- classificação manual (e) ----
C, R, E, X_, T, Q = ("conta errada", "raciocínio errado", "enunciado mal lido",
                     "certa, extração/formato errado", "cortada", "gabarito discutível")
CLS = {
    78: (E, "Aplicou juros compostos; o enunciado diz 5% *do preço original* (120 + 3×6 = 138)."),
    97: (E, "Ignorou \"after 3 days\": parou em 97 por dia (×3 = 291)."),
    151: (R, "Multiplicou o aluguel de $25 pelo número de alunos; o certo é (25 + 1,5×10)×3×4."),
    178: (E, "Leu \"2 extra classes\" como 2 aulas por semana e ignorou as 6 aulas diárias."),
    219: (R, "Calculou o desvio (210 mi) mas usou 200/70 no tempo."),
    241: (E, "Ignorou \"50 miles less\" no terceiro trecho (usou 175 em vez de 125)."),
    299: (C, "Montagem certa; 204 + 160 + 330 = 694, escreveu 700."),
    311: (R, "Não deduziu 8 lápis por caixa a partir de 3 caixas + 2 = 26; disse que não dava e respondeu 72."),
    344: (E, "Achou s = 20 corretamente e respondeu 100 − 20 = 80 (não era o perguntado)."),
    350: (R, "Calculou o custo de Dasha (36) e esqueceu de subtrair o bracelete (36 − 30)."),
    366: (R, "Tratou as 315 bananas da semana como consumo de um dia (faltou ÷7)."),
    400: (C, "Montagem certa; 50 + 70 + 140 + 240 = 500, escreveu 480."),
    426: (C, "24 − 5 − 10 = 9, escreveu 10; o resto propagou o erro."),
    449: (R, "Pagou só o 3º mês com 260 funcionários; faltou somar os três meses (220 + 240 + 260)."),
    457: (E, "Modelou a 2ª leva como x + 20 em vez de 20 carros."),
    461: (E, "Parou na altura atual (70); a pergunta é antes do verão (−3)."),
    475: (E, "Contou 20 caixas em cada dia do fim de semana; eram 20 no total."),
    499: (T, "Montou Dinar = x − 10 (o certo é x + 10), achou 35/3, entrou em \"recheck\" e foi cortada."),
    524: (Q, "Respondeu a energia economizada (5 h × 0,9 kW × 30 = 135); o gold 81 é o consumo restante. O enunciado pede \"save\"."),
    564: (E, "No 3º ano dobrou 36; o enunciado dobra o total construído até então (48)."),
    599: (R, "Multiplicou vezes × semanas e esqueceu os km por volta (25 e 60)."),
    605: (E, "Ignorou que 15 copos foram para canela; dividiu os 27 nas fileiras."),
    632: (E, "Leu os 5% como de todas as velas, não das perigosas; concluiu 0 e usou \\boxed{} sem ####."),
    677: (R, "Subtraiu perda e ganho (1,75 − 1,25); a diferença entre as opções é a soma."),
    679: (E, "\"Parents\" = 2 adultos; contou 1."),
    689: (R, "Dividiu $6 por $1,50 = 4 e tratou como 4 *conjuntos* de 3 bolas."),
    692: (E, "Ignorou o \"1/2 bail\" por milha e leu seis notas de $5 como $50."),
    709: (R, "Na volta, tratou \"roubou 2/3 do restante\" como 2/3 de 6 em vez de inverter (6 = 1/3)."),
    773: (R, "Esqueceu de descontar as vendas deste ano (45) ao calcular o 2º ano."),
    830: (Q, "140 000 + 20 000 = 160 000 é leitura razoável; o gold soma também as 2000 iniciais."),
    965: (E, "\"Drops 1 of each\" = uma flor de cada grupo (22 pétalas); subtraiu 4 pétalas."),
    968: (R, "Somou o estacionamento ao pagamento em vez de subtrair."),
    1055: (E, "Respondeu quantas babás seriam necessárias; a pergunta é quantas vezes cortar grama."),
    1059: (R, "Dividiu o lucro por 4 (copos/h) em vez de pelas 9 horas de venda."),
    1085: (X_, "Resposta 100 centavos = $1, que está certo; a unidade em centavos faz a extração dar 100."),
    1098: (E, "Calculou um dia (9 h) e ignorou \"every day for 3 weeks\" (×21)."),
    1123: (C, "Montagem certa; 1090 + 157 + 74 + 102 = 1423, escreveu 1323."),
    1132: (R, "Supôs 36 cachorros-quentes preparados; eram 36 + 18 = 54."),
    1135: (R, "Multiplicou aulas × horas e ignorou os $15/hora."),
    1290: (E, "Tratou \"$50\" pela metade do terreno como $50 por m²."),
}
assert sorted(CLS) == D["amostra_erros"]["idx"], "amostra diferente da sorteada"

# ---- classificação das 19 cortadas do treinado (a) ----
TRUNC = {
    "loop de reverificação (refaz a mesma álgebra após resultado impossível)": [63, 499, 659, 740, 770, 954, 1276],
    "saída degenerada (número com dezenas de zeros)": [918],
    "longa, sem repetição, cortada antes de terminar": [127, 527, 539, 791, 894, 910, 1044, 1081, 1279],
    "cortada logo no \"####\"": [274, 707],
}
assert sorted(sum(TRUNC.values(), [])) == sorted(D["trunc_grpo"]["idx"])

L = []
w = L.append
tg, tb = D["tamanho_grpo"], D["tamanho_base"]
dg, db = D["desperdicio_grpo"], D["desperdicio_base"]
rg, rb = D["rep_grpo"], D["rep_base"]
xg, xb = X["grpo"], X["base"]
F = D["flips"]

w("# Análise de erros: qwen3-1.7b-gsm8k-grpo × base\n")
w("Fonte: `eval/eval_base.csv` e `eval/eval_grpo.csv` de `felipedutrain/qwen3-1.7b-gsm8k-grpo`, "
  "revisão `a29e720349ee301bb987fdff2ea568fa74d931a3` (teste completo do GSM8K, 1319 questões, limite de 320 tokens). "
  "Tokens contados com o tokenizer do modelo treinado. Scripts: `analisa.py`, `extra.py`, `gera_relatorio.py`; "
  "números brutos em `analise_dados.json` e `extra_dados.json`.\n")
w("| | base | treinado |\n|---|---|---|")
w(f"| acerto flex | {sum(r['correct_flex']=='True' for r in B.values())}/1319 | {sum(r['correct_flex']=='True' for r in G.values())}/1319 |")
w(f"| acerto strict | {sum(r['correct_strict']=='True' for r in B.values())}/1319 | {sum(r['correct_strict']=='True' for r in G.values())}/1319 |")
w(f"| cortadas (320 tokens) | {D['trunc_base']['n']} | {D['trunc_grpo']['n']} |")
w(f"| tokens por resposta (média / mediana) | {tb['todos']['media']} / {tb['todos']['mediana']} | {tg['todos']['media']} / {tg['todos']['mediana']} |\n")

# a
w("## a. Respostas cortadas\n")
w(f"- **Base:** {D['trunc_base']['n']} cortadas, {D['trunc_base']['flex_ok']} acertam no flex. "
  f"{D['trunc_base']['com_rep8']} têm algum trecho de 8 palavras repetido; {D['trunc_base']['com_loop(8gram>=3x)']} repete um trecho 3 vezes ou mais.")
w(f"- **Treinado:** {D['trunc_grpo']['n']} cortadas, {D['trunc_grpo']['flex_ok']} acerta no flex (1081, por sorte: o último número escrito era 4). "
  f"{D['trunc_grpo']['com_rep8']} têm trecho de 8 palavras repetido.\n")
w("**Há loop?** Não há loop de tokens no sentido clássico (a mesma frase repetida sem fim), com uma exceção: o idx 918 "
  "termina num número com ~90 zeros. O padrão que aparece é outro: em 7 das 19 o modelo monta a equação errada, "
  "obtém um resultado impossível (idade negativa, pontos fracionários), escreve \"let's recheck\" e **refaz a mesma "
  "álgebra, idêntica**, até acabar o orçamento. Ele nunca muda a montagem. As demais são problemas longos que não "
  "terminam em 320 tokens, e duas foram cortadas logo depois do `####`.\n")
w("| tipo | n | idx |\n|---|---|---|")
for k, v in TRUNC.items():
    w(f"| {k} | {len(v)} | {', '.join(map(str, v))} |")
w("")
w("Saídas completas do treinado (as 19):\n")
for i in D["trunc_grpo"]["idx"]:
    r = G[i]
    w(f"<details><summary>idx {i}: gold {r['gold']}, flex {r['correct_flex']}</summary>\n")
    w("**Pergunta:** " + r["question"] + "\n")
    w("```text\n" + r["output"] + "\n```\n</details>\n")

# b
w("## b. Repetição em geral (trechos de 8+ palavras repetidos na mesma resposta)\n")
w("| | base | treinado |\n|---|---|---|")
w(f"| respostas com algum 8-grama repetido | {rb['n_com_rep8']} ({rb['pct']}%) | {rg['n_com_rep8']} ({rg['pct']}%) |")
w(f"| … com o mesmo 8-grama 3 vezes ou mais | {rb['n_rep8_3x_ou_mais']} | {rg['n_rep8_3x_ou_mais']} |")
w(f"| … que também foram cortadas | {rb['rep8_entre_trunc']} | {rg['rep8_entre_trunc']} |")
w(f"| acerto flex com repetição / sem | {rb['flex_acc_com_rep']} / {rb['flex_acc_sem_rep']} | {rg['flex_acc_com_rep']} / {rg['flex_acc_sem_rep']} |\n")
w("O treinado repete um pouco menos (4,2% contra 5,5%). Nos dois, repetir é sinal forte de erro: o acerto cai de ~78% para ~40%. "
  "Fora das cortadas, a maior parte das repetições é estrutural e inofensiva: a mesma fórmula reescrita "
  "(`$$ x + (x + 20) …`), ou linhas paralelas como \"Large buttons received: $ 20 \\div 3 = 6 $\". Repetição em laço é rara "
  "(2 respostas em cada modelo).\n")

# c
w("## c. Desperdício\n")
w(f"**Depois do `####` final:** o treinado fecha com `#### <número>` em {dg['com_####_final']} de 1319 respostas, e só "
  f"{dg['algo_depois_do_####']} têm algo depois: `#### 2:00 pm` (horário, certo), `#### 2.666...` e dois com duas respostas na mesma linha (`#### 86 42`, `#### 80 150`). Na média dá "
  f"{dg['tokens_depois_media_global']} token por resposta, ou seja, **zero na prática**. "
  f"(O base escreve `#### <number> 109`, copiando o placeholder do prompt, e quase nunca fecha no formato.)\n")
w("**Texto que não faz conta**, estimado por linha, com o tokenizer do modelo:\n")
w("| categoria | base (tokens/resp, % do gerado) | treinado |\n|---|---|---|")
w(f"| linhas sem número nem operação (\"Let's break it down…\", \"We are given:\", \"Final answer\") | {db['tokens_sem_conta_por_resposta_media']} ({db['pct_dos_tokens_gerados']}%) | {dg['tokens_sem_conta_por_resposta_media']} ({dg['pct_dos_tokens_gerados']}%) |")
w(f"| linhas que só listam dados do enunciado (números todos da questão, sem operação) | {xb['tok_listagem_dados_por_resp']} ({xb['pct_listagem']}%) | {xg['tok_listagem_dados_por_resp']} ({xg['pct_listagem']}%) |")
w(f"| formatação (linhas `$$`, `**`, `\\text{{}}`; aproximado) | {xb['tok_formatacao_por_resp']} ({xb['pct_formatacao']}%) | {xg['tok_formatacao_por_resp']} ({xg['pct_formatacao']}%) |")
w(f"| loops de reverificação (\"recheck\", \"not possible\", \"Wait\") | {xb['resp_com_recheck']} resp., {xb['tok_medios_recheck']} tok cada, acerto {xb['acc_flex_recheck']} | {xg['resp_com_recheck']} resp., {xg['tok_medios_recheck']} tok cada, acerto {xg['acc_flex_recheck']} |\n")
w(f"Somando as três primeiras linhas, o treinado gasta **~{round(dg['tokens_sem_conta_por_resposta_media']+xg['tok_listagem_dados_por_resp']+xg['tok_formatacao_por_resp'])} tokens por resposta "
  f"(~{round(dg['pct_dos_tokens_gerados']+xg['pct_listagem']+xg['pct_formatacao'])}% do gerado)** com coisas que não são conta. "
  f"No base são ~{round(db['tokens_sem_conta_por_resposta_media']+xb['tok_listagem_dados_por_resp']+xb['tok_formatacao_por_resp'])} (~{round(db['pct_dos_tokens_gerados']+xb['pct_listagem']+xb['pct_formatacao'])}%). "
  "É um teto: listar os dados às vezes ajuda o modelo. Os loops de reverificação são poucos (9), mas cada um queima o orçamento inteiro e nenhum acerta.\n")
w("Frases sem conta mais comuns:\n")
w("| frase | base | treinado |\n|---|---|---|")
cb, cg = dict(db["linhas_mais_comuns"]), dict(dg["linhas_mais_comuns"])
for k in ["let's break it down step by step", "final answer", "we are given", "let's define the variables",
          "simplify", "from the problem", "according to the problem"]:
    w(f"| {k} | {cb.get(k, '<15ª')} | {cg.get(k, '<15ª')} |")
w(f"\nRespostas que abrem com \"Let's solve/break…\": base {db['abre_com_lets_solve_break']['n']}, treinado {dg['abre_com_lets_solve_break']['n']} (~9 tokens cada). "
  "O treino já cortou quase toda a verborragia: o treinado em geral começa direto em \"1. …\" ou \"Let x be…\".\n")

# d
w("## d. Tamanho (n_tokens) no treinado\n")
w("| | n | média | mediana | p90 | mín | máx |\n|---|---|---|---|---|---|---|")
for k, lab in (("acertos", "acertos"), ("erros", "erros"), ("todos", "todos")):
    s = tg[k]
    w(f"| {lab} | {s['n']} | {s['media']} | {s['mediana']} | {s['p90']} | {s['min']} | {s['max']} |")
w(f"\nPara comparar, no base: acertos {tb['acertos']['media']} / {tb['acertos']['mediana']} / p90 {tb['acertos']['p90']}; erros {tb['erros']['media']} / {tb['erros']['mediana']} / p90 {tb['erros']['p90']}.\n")
w("Acerto por faixa de tamanho (treinado):\n")
w("| tokens | n | acerto flex |\n|---|---|---|")
for h in tg["hist"]:
    w(f"| {h['faixa']} | {h['n']} | {h['acc_flex']} |")
w("\nAs respostas erradas são ~25% mais longas. O acerto cai a partir de ~150 tokens e despenca em 320 (cortadas). "
  "O tamanho é sintoma de dificuldade, não causa: questões mais longas pedem mais passos (ver f).\n")

# e
w("## e. 40 erros sorteados do treinado\n")
w(f"Sorteio com `random.seed({D['amostra_erros']['semente']})`, `random.sample` de {D['amostra_erros']['n_erros']} respostas com `correct_flex = False`. "
  "A classificação é manual e tem algo de subjetivo: \"enunciado mal lido\" quando o modelo ignora ou interpreta mal um dado ou o que é perguntado; "
  "\"raciocínio errado\" quando lê certo mas combina as operações errado. "
  "Criei uma categoria extra, \"gabarito discutível\", para dois casos em que a resposta do modelo é defensável.\n")
from collections import Counter
cnt = Counter(c for c, _ in CLS.values())
w("| categoria | n | % |\n|---|---|---|")
for c in (E, R, C, T, X_, Q):
    w(f"| {c} | {cnt[c]} | {round(100*cnt[c]/40)}% |")
w("")
w("| idx | gold | resposta | tok | categoria | justificativa |\n|---|---|---|---|---|---|")
import re
for i in sorted(CLS):
    r = G[i]
    m = re.findall(r"####\s*([^\n]*)", r["output"])
    ans = m[-1].strip()[:14] if m else "(sem ####)"
    c, j = CLS[i]
    w(f"| {i} | {r['gold']} | {ans} | {r['n_tokens']} | {c} | {j} |")
w("\nQuase todos os erros (32 de 40) são de **interpretação ou de lógica**: dado ignorado, relação invertida, pergunta respondida errada. "
  "Erro aritmético puro é raro (4), e só um caso foi cortado. Em 10 dos 40 o base acertava.\n")

# f
fo, fi = F["base_ok_grpo_erro"], F["base_erro_grpo_ok"]
ao, ae = F["ambos_ok"], F["ambos_erro"]
w("## f. Trocas: base acerta e treinado erra (83) × o contrário (79)\n")
w("| | base ✓ treinado ✗ | base ✗ treinado ✓ | ambos ✓ | ambos ✗ |\n|---|---|---|---|---|")
rows = [("n", "n"), ("palavras na questão (média)", "q_palavras_media"), ("números na questão (média)", "q_numeros_media"),
        ("tokens do base (mediana)", "tok_base_mediana"), ("tokens do treinado (mediana)", "tok_grpo_mediana"),
        ("base cortado (%)", "trunc_base_pct"), ("treinado cortado (%)", "trunc_grpo_pct"),
        ("porcentagem (%)", "porcentagem_pct"), ("fração (%)", "fração_pct"), ("dinheiro (%)", "dinheiro_pct"),
        ("tempo (%)", "tempo_pct"), ("taxa/velocidade (%)", "taxa/velocidade_pct"), ("comparação more/less/times (%)", "comparação (more/less/times)_pct")]
for lab, k in rows:
    w(f"| {lab} | {fo[k]} | {fi[k]} | {ao[k]} | {ae[k]} |")
fd = X["fisher_dinheiro"]
w("\nO que os números mostram:\n")
w(f"- **As trocas acontecem nas questões difíceis, nos dois sentidos.** Os dois grupos têm questões mais longas "
  f"(~50 palavras, 4 números) do que as que ambos acertam (~40, 3 números), e parecidas com as que ambos erram. "
  f"Saldo: 79 − 83 = −4 no flex, o que é empate. A maior parte da troca parece ruído em problemas que ficam no limite da capacidade do modelo.")
w(f"- **Tamanho:** o treinado é ~30 tokens mais curto nos dois grupos (diferença mediana {fo['delta_tokens_grpo_menos_base_mediana']} e {fi['delta_tokens_grpo_menos_base_mediana']}). "
  "Encurtar não explica nem os ganhos nem as perdas.")
w(f"- **Cortes:** nas 79 que o treinado ganhou, o base tinha sido cortado em {fi['perdedor_cortado']} ({fi['trunc_base_pct']}%) e o treinado em nenhuma; "
  f"nas 83 que perdeu, o treinado foi cortado em {fo['perdedor_cortado']} ({fo['trunc_grpo_pct']}%). Parte do ganho vem de terminar a tempo.")
w(f"- **Dinheiro:** problemas com $, preço ou custo aparecem mais nas perdas ({fd['base_ok_grpo_erro']}) do que nos ganhos ({fd['base_erro_grpo_ok']}); Fisher bicaudal p = {fd['p_bicaudal']}. "
  "Mas testei 6 categorias, e com correção de Bonferroni (p × 6 ≈ 0,15) isso não se sustenta. É uma pista, não uma conclusão.")
w(f"- **Formato:** só {X['grpo_sem_####_nas_83']} das 83 perdas não têm `#### <número>`, então as perdas não vêm de formato.\n")

# conclusão
w("## Conclusão: dá para atacar com edição direta de pesos?\n")
w("1. Desperdício verbal já é pequeno no treinado: ~2,5% dos tokens em frases sem conta, nada depois do `####` e ~14 tokens/resposta de listagem de dados e formatação (~18 tokens, ~14%, somando tudo). Editar pesos para cortar isso economizaria pouco, e listar os dados provavelmente ajuda.")
w("2. A única falha sistemática bem delimitada é o loop de reverificação: ao chegar num resultado impossível, o modelo refaz a mesma álgebra sem mudar a montagem. São 9 respostas (0,7%), com ~300 tokens cada e 0% de acerto.")
w("3. Esse loop é um alvo melhor para decodificação (cortar ao detectar \"recheck\" com repetição, ou penalizar n-gramas repetidos) do que para edição de pesos; com 9 exemplos não há dados para localizar e validar uma direção ou um circuito.")
w("4. Os erros de verdade (80% da amostra) são de interpretação e de lógica, diferentes de questão para questão. Não é um fato isolado nem um formato, então não vejo alvo para edição pontual (ROME, steering, ablação).")
w("5. Resposta direta: não encontrei um padrão de desperdício ou de falha sistemática grande o bastante para justificar edição direta de pesos; o ganho possível está em decodificação (loops) e em mais treino de leitura do enunciado.")

open(f"{HERE}/relatorio.md", "w").write("\n".join(L) + "\n")
print("ok", len(L), "linhas")
