## Tarefa 11 — Q4_K_M no Fedora (CPU i5-10300H, llama.cpp dde879bc, -t 4), GSM8K completo (1.319)

Mesmo pipeline de 03/11 (SYSTEM, temperature 0, seed 42, max_tokens 320, sem pensar, template, -c 4096, grading.py); mesmo arquivo Q4_K_M do PS4 (d7771967…).

### Métricas

| | Fedora Q4_K_M |
|---|---|
| acerto strict | 833/1319 = 63.2% (IC95% 60.5–65.7) |
| acerto flex | 961/1319 = 72.9% (IC95% 70.4–75.2) |
| tokens por resposta (média / mediana) | 132.2 / 120 |
| cortadas (320) | 17 |
| tempo de prompt / geração por resposta (s) | 0.67 / 5.98 |
| geração tokens/s (total ÷ total) | 22.12 |
| segundos por resposta / por acerto (flex) | 6.67 / 9.15 |

### Fedora Q4_K_M × Kaggle (v1, precisão cheia) — 1.319, pareado pelo texto

| | Fedora | Kaggle | só Fedora acerta / só Kaggle acerta | McNemar exato (p) | Fedora − Kaggle (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 833/1319 (63.2%) | 1000/1319 (75.8%) | 79 / 246 | 4.2e-21 | -12.7 (-15.2 a -10.1) | 994/1319 |
| flex | 961/1319 (72.9%) | 1006/1319 (76.3%) | 85 / 130 | 0.00261 | -3.4 (-5.6 a -1.2) | 1104/1319 |

Saídas idênticas: 1/1319. Regra de decisão (flex): **não igual** (Δflex = -3.4 pts, McNemar p = 0.00261; falha: |Δ| = 3.4 > 1,5 e p ≤ 0,05).

### Fedora Q4_K_M × PS4 GPU Q4_K_M (gsm8k-full-gpu-20261108) — 1.319, mesmo arquivo de modelo

| | Fedora | PS4-GPU | só Fedora acerta / só PS4-GPU acerta | McNemar exato (p) | Fedora − PS4-GPU (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 833/1319 (63.2%) | 881/1319 (66.8%) | 80 / 128 | 0.00107 | -3.6 (-5.8 a -1.5) | 1111/1319 |
| flex | 961/1319 (72.9%) | 962/1319 (72.9%) | 67 / 68 | 1 | -0.1 (-1.8 a +1.7) | 1184/1319 |

Saídas idênticas: 295/1319. Regra de decisão (flex): **igual** (Δflex = -0.1 pts, McNemar p = 1: |Δ| ≤ 1,5 e p > 0,05).

### Fedora Q4_K_M × PS4 CPU Q4_K_M (tarefa 8) — questões 0–99

| | Fedora | PS4-CPU | só Fedora acerta / só PS4-CPU acerta | McNemar exato (p) | Fedora − PS4-CPU (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 70/100 (70.0%) | 74/100 (74.0%) | 9 / 13 | 0.523 | -4.0 (-13.3 a +5.4) | 78/100 |
| flex | 78/100 (78.0%) | 81/100 (81.0%) | 5 / 8 | 0.581 | -3.0 (-10.5 a +4.5) | 87/100 |

Saídas idênticas: 16/100. n = 100: pouca potência para detectar diferenças pequenas. Regra de decisão (flex): **não igual** (Δflex = -3.0 pts, McNemar p = 0.581; falha: |Δ| = 3.0 > 1,5).

### Referência: PS4 GPU × Kaggle (já reportado na análise de gsm8k-full-gpu-20261108)

| | PS4-GPU | Kaggle | só PS4-GPU acerta / só Kaggle acerta | McNemar exato (p) | PS4-GPU − Kaggle (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 881/1319 (66.8%) | 1000/1319 (75.8%) | 78 / 197 | 4.81e-13 | -9.0 (-11.4 a -6.6) | 1044/1319 |
| flex | 962/1319 (72.9%) | 1006/1319 (76.3%) | 86 / 130 | 0.00334 | -3.3 (-5.5 a -1.2) | 1103/1319 |

Regra de decisão (flex): **não igual** (Δflex = -3.3 pts, McNemar p = 0.00334; falha: |Δ| = 3.3 > 1,5 e p ≤ 0,05).

### Regra de decisão — resumo

Regra registrada no manifest.csv antes da rodada: **igual = |Δflex| ≤ 1,5 ponto E McNemar exato p > 0,05**.

| comparação | resultado |
|---|---|
| Fedora Q4_K_M × Kaggle (v1, precisão cheia) | **não igual** (Δflex = -3.4 pts, McNemar p = 0.00261; falha: |Δ| = 3.4 > 1,5 e p ≤ 0,05) |
| Fedora Q4_K_M × PS4 GPU Q4_K_M (gsm8k-full-gpu-20261108) | **igual** (Δflex = -0.1 pts, McNemar p = 1: |Δ| ≤ 1,5 e p > 0,05) |
| Fedora Q4_K_M × PS4 CPU Q4_K_M (tarefa 8) | **não igual** (Δflex = -3.0 pts, McNemar p = 0.581; falha: |Δ| = 3.0 > 1,5) |
| PS4 GPU × Kaggle (referência) | **não igual** (Δflex = -3.3 pts, McNemar p = 0.00334; falha: |Δ| = 3.3 > 1,5 e p ≤ 0,05) |

### Condições da rodada

- Blocos: 27; AC ligado em 26/27 (o bloco das questões 0–19 do teste rodou na bateria); subida do servidor 2–2 s; temperatura máxima da CPU (coretemp) 74 °C.
- packagekitd: 147 amostras de 60 s; rodando em 6 (CPU% máx 12.1).
- Tempo somado das respostas: 2.44 h.
- Correção (após a análise): das 6 amostras com packagekitd, 5 caíram dentro da rodada, todas entre 09:45:57 e 09:49:57 (CPU 12,1 → 1,9%), e 1 depois do fim (12:11:03); o amostrador ficou rodando além do fim porque o pgrep -f casava com a própria linha de comando e foi encerrado à mão.
