## Tarefa 11 — Q5_K_M no Fedora (CPU i5-10300H, llama.cpp dde879bc, -t 4), GSM8K completo (1.319)

Mesmo pipeline do braço Q4_K_M (run_quant.py f5811ab5…). Modelo qwen3-1.7b-gsm8k-grpo-Q5_K_M.gguf (366dbe4c…).

### Métricas (com o Q4_K_M do Fedora ao lado)

| | Q5_K_M | Q4_K_M |
|---|---|---|
| acerto strict | 760/1319 = 57.6% (IC95% 54.9–60.3) | 833/1319 = 63.2% (IC95% 60.5–65.7) |
| acerto flex | 986/1319 = 74.8% (IC95% 72.3–77.0) | 961/1319 = 72.9% (IC95% 70.4–75.2) |
| tokens por resposta (média / mediana) | 135.0 / 123 | 132.2 / 120 |
| cortadas (320) | 25 | 17 |
| tempo de prompt / geração por resposta (s) | 0.69 / 6.57 | 0.67 / 5.98 |
| geração tokens/s (total ÷ total) | 20.56 | 22.12 |
| segundos por resposta | 7.28 | 6.67 |
| segundos por acerto (flex) | 9.73 | 9.15 |

### Q5_K_M × Kaggle (v1, precisão cheia) — pareado pelo texto

| | Q5_K_M | Kaggle | só Q5_K_M acerta / só Kaggle acerta | McNemar exato (p) | Q5_K_M − Kaggle (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 760/1319 (57.6%) | 1000/1319 (75.8%) | 64 / 304 | 1.6e-38 | -18.2 (-20.9 a -15.5) | 951/1319 |
| flex | 986/1319 (74.8%) | 1006/1319 (76.3%) | 79 / 99 | 0.154 | -1.5 (-3.5 a +0.5) | 1141/1319 |

Saídas idênticas: 51/1319.

### Q5_K_M × Q4_K_M (ambos no Fedora, mesmo pipeline)

| | Q5_K_M | Q4_K_M | só Q5_K_M acerta / só Q4_K_M acerta | McNemar exato (p) | Q5_K_M − Q4_K_M (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 760/1319 (57.6%) | 833/1319 (63.2%) | 158 / 231 | 0.000252 | -5.5 (-8.4 a -2.6) | 930/1319 |
| flex | 986/1319 (74.8%) | 961/1319 (72.9%) | 120 / 95 | 0.101 | +1.9 (-0.3 a +4.1) | 1104/1319 |

Saídas idênticas: 0/1319.

### Q5_K_M (Fedora) × Q4_K_M na GPU do PS4 (gsm8k-full-gpu-20261108)

| | Q5_K_M | PS4-GPU | só Q5_K_M acerta / só PS4-GPU acerta | McNemar exato (p) | Q5_K_M − PS4-GPU (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 760/1319 (57.6%) | 881/1319 (66.8%) | 133 / 254 | 7.79e-10 | -9.2 (-12.0 a -6.3) | 932/1319 |
| flex | 986/1319 (74.8%) | 962/1319 (72.9%) | 124 / 100 | 0.124 | +1.8 (-0.4 a +4.0) | 1095/1319 |

Saídas idênticas: 1/1319.

### Regras de decisão (registradas no manifest.csv antes da rodada)

| regra | condição | valores | aplica-se? |
|---|---|---|---|
| recupera | Q5_K_M × Kaggle: \|Δflex\| ≤ 1,5 ponto E McNemar p > 0,05 | Δflex = -1.5; p = 0.154 | **não** |
| melhora | Q5_K_M acima do Q4_K_M do Fedora (Δflex > 0) com McNemar p < 0,05 no flex | Δflex = +1.9; p = 0.101 | **não** |

### Condições da rodada

- Blocos: 27; AC ligado em 27/27 (o bloco do teste, questões 0–19, também na tomada); subida do servidor 1–2 s; temperatura máxima da CPU (coretemp) 78 °C.
- packagekitd: 158 amostras (a cada ~60 s, presas ao processo do cliente); rodando em 5 (CPU% máx 10.3).
- Tempo somado das respostas: 2.67 h.
