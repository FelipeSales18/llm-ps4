# Limite de tokens: simulação com os CSVs do Kaggle

Fonte: `analise/eval/eval_base.csv` e `eval_grpo.csv` (1319 questões do teste do GSM8K, geração greedy, limite original de 320).
Regra: se `n_tokens` passa do limite, a resposta conta como cortada e errada; se fica no limite ou abaixo, nada muda.
Os tempos são só de geração, a 8,4 tokens/s (PS4, Q4_K_M, 8 threads), sem o processamento do prompt.

| modelo | limite | flex | strict | tokens gerados (média) | cortadas | s/resposta | s/resposta correta (flex) |
|---|---|---|---|---|---|---|---|
| base | 160 | 54.66% (721) | 2.58% | 128.8 | 35.33% | 15.34 | 28.05 |
| base | 200 | 67.17% (886) | 2.81% | 139.3 | 18.12% | 16.58 | 24.68 |
| base | 256 | 73.84% (974) | 2.88% | 146.3 | 7.81% | 17.42 | 23.58 |
| base | 320 | 76.57% (1010) | 2.88% | 149.6 | 3.03% | 17.81 | 23.26 |
| treinado | 160 | 63.15% (833) | 62.93% | 118.5 | 22.37% | 14.11 | 22.34 |
| treinado | 200 | 71.95% (949) | 71.57% | 124.5 | 8.87% | 14.82 | 20.59 |
| treinado | 256 | 74.91% (988) | 74.53% | 127.8 | 3.26% | 15.21 | 20.31 |
| treinado | 320 | 76.27% (1006) | 75.82% | 129.2 | 1.44% | 15.38 | 20.16 |

**Recomendação: 320 tokens.** Nenhum limite menor entre os testados atende ao critério (queda de no máximo 0,5 ponto no flex do treinado em relação ao de 320):
- 160: queda de 13.12 ponto no flex.
- 200: queda de 4.32 ponto no flex.
- 256: queda de 1.36 ponto no flex.
- 320: queda de 0.00 ponto no flex.

Cortar não compensa: o treinado já é curto (mediana de 120 tokens). Limites menores economizam poucos tokens em média (256: 1.4 tokens, ~0.16 s por resposta) e perdem acertos nas questões longas, que são justamente as difíceis. O tempo por resposta correta piora em todos os limites menores.

Nota, fora dos quatro valores pedidos: varrendo limites inteiros, o menor que atende ao critério é **296** (flex 75,89%, queda de 0,38 ponto, 128,8 tokens médios). Economiza só 0,4 token por resposta em relação ao de 320, então não vale a pena.
