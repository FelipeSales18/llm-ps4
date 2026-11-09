## GSM8K completo (1.319) — Qwen3-1.7B GRPO Q4_K_M, PS4 GPU (llama.cpp Vulkan, -ngl 99)

Pipeline de 03/11 (mesmo SYSTEM, temperature 0, seed 42, max_tokens 320, sem pensar, mesmo template e grading.py); cliente no próprio PS4 (run_eval_full.py v2 → v3 → v4, mesma geração).

### Métricas

| | GPU (PS4) |
|---|---|
| acerto strict | 881/1319 = 66.8% (IC95% 64.2–69.3) |
| acerto flex | 962/1319 = 72.9% (IC95% 70.5–75.3) |
| tokens por resposta (média / mediana) | 131.2 / 121 |
| cortadas (320) | 24 |
| tokens de prompt processados (média) | 71.0 |
| tempo de prompt por resposta (s) | 0.48 |
| tempo de geração por resposta (s) | 11.01 |
| geração tokens/s (total tokens ÷ total tempo) | 11.92 |
| segundos por resposta (ponta a ponta) | 11.57 |
| segundos por resposta correta (flex) | 15.86 |
| tempos inválidos (pausa do vigia) | 0 |

### GPU (PS4, Q4_K_M) × Kaggle (v1, precisão cheia), pareado pelo texto da pergunta

Pares: 1319/1319 (textos duplicados no Kaggle: 0; sem par único: 0). As duas saídas foram corrigidas com o mesmo grading.py; o regrading reproduz as notas gravadas pelo Kaggle em 1319/1319.

| | GPU (PS4) | Kaggle | trocas: só GPU acerta / só Kaggle acerta | McNemar exato (p) | diferença GPU − Kaggle (pontos, IC95% Newcombe) | mesmo veredito |
|---|---|---|---|---|---|---|
| strict | 881/1319 (66.8%) | 1000/1319 (75.8%) | 78 / 197 | 0.000 | -9.0 (-11.4 a -6.6) | 1044/1319 (ambos acertam 803, ambos erram 241) |
| flex | 962/1319 (72.9%) | 1006/1319 (76.3%) | 86 / 130 | 0.003 | -3.3 (-5.5 a -1.2) | 1103/1319 (ambos acertam 876, ambos erram 227) |

Tokens por resposta: GPU 131.2 (mediana 121) × Kaggle 129.2 (mediana 120); cortadas GPU 24 × Kaggle 19; saída idêntica em 0/1319.

### Questões 0–99: rodada completa × tarefa 8 (06/11)

| braço da tarefa 8 | saídas idênticas | mesmo veredito flex | flex T8 | flex rodada (0–99) |
|---|---|---|---|---|
| gpu | 100/100 | 100/100 | 77 | 77 |
| cpu | 27/100 | 92/100 | 81 | 77 |

### Por bloco

| bloco | idx | subida do servidor | início (°C, k10temp) | espera p/ esfriar (s) | máx ps4_fan / k10temp (°C) | fan1 máx | pausas do vigia | tempos inválidos | duração | obs |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0–49 | 4 s | 67.0 | 0 | 79.0 / 79.0 | 35 | 0 | 0 | 9.2 min |  |
| 2 | 50–99 | — (mesmo servidor) | 67.8 | 45 | 77.0 / 77.0 | 0 | 0 | 0 | 9.7 min |  |
| 3 | 100–149 | — (mesmo servidor) | 68.2 | 30 | 77.0 / 77.2 | 0 | 0 | 0 | 9.9 min |  |
| 4 | 150–196 | — (mesmo servidor) | 68.2 | 30 | 77.0 / 77.5 | 0 | 0 | 0 | 9.4 min | interrompido após idx 196 (travamento da GPU na 197) |
| 4 | 197–197 | 18 s | 69.1 | 0 | 72.0 / 72.2 | 0 | 0 | 0 | 0.1 min |  |
| 4 | 198–246 | 4 s | 66.9 | 0 | 78.0 / 78.6 | 33 | 0 | 0 | 9.7 min |  |
| 5 | 247–296 | 4.0 s | 66.4 | 0 | 79.0 / 79.2 | 37 | 0 | 0 | 9.4 min |  |
| 6 | 297–346 | 4.0 s | 67.2 | 45 | 76.0 / 76.6 | 0 | 0 | 0 | 10.1 min |  |
| 7 | 347–396 | 4.0 s | 67.0 | 30 | 79.0 / 79.0 | 20 | 0 | 0 | 9.4 min |  |
| 8 | 397–446 | 4.0 s | 67.8 | 75 | 78.0 / 78.8 | 30 | 0 | 0 | 10.4 min |  |
| 9 | 447–496 | 4.0 s | 68.2 | 90 | 78.0 / 78.8 | 33 | 0 | 0 | 8.9 min |  |
| 10 | 497–546 | 4.0 s | 68.2 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 9.1 min |  |
| 11 | 547–596 | 4.0 s | 67.6 | 30 | 76.0 / 76.6 | 0 | 0 | 0 | 9.4 min |  |
| 12 | 597–646 | 4.0 s | 67.5 | 30 | 77.0 / 77.0 | 0 | 0 | 0 | 10.6 min |  |
| 13 | 647–696 | 4.0 s | 67.8 | 30 | 76.0 / 76.5 | 0 | 0 | 0 | 9.0 min |  |
| 14 | 697–746 | 4.0 s | 67.2 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 9.7 min |  |
| 15 | 747–796 | 4.0 s | 67.2 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 11.2 min |  |
| 16 | 797–846 | 4.0 s | 67.2 | 30 | 76.0 / 76.6 | 0 | 0 | 0 | 10.4 min |  |
| 17 | 847–896 | 4.0 s | 67.2 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 9.8 min |  |
| 18 | 897–946 | 4.0 s | 67.5 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 10.4 min |  |
| 19 | 947–996 | 4.0 s | 67.2 | 30 | 76.0 / 76.8 | 0 | 0 | 0 | 9.8 min |  |
| 20 | 997–1046 | 4.0 s | 67.5 | 30 | 76.0 / 76.6 | 0 | 0 | 0 | 9.5 min |  |
| 21 | 1047–1096 | 4.0 s | 67.2 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 10.8 min |  |
| 22 | 1097–1146 | 4.0 s | 67.5 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 10.1 min |  |
| 23 | 1147–1196 | 4.0 s | 67.4 | 30 | 76.0 / 76.5 | 0 | 0 | 0 | 10.7 min |  |
| 24 | 1197–1246 | 4.0 s | 67.2 | 30 | 76.0 / 76.5 | 0 | 0 | 0 | 9.4 min |  |
| 25 | 1247–1296 | 4.0 s | 67.5 | 30 | 77.0 / 76.9 | 0 | 0 | 0 | 10.1 min |  |
| 26 | 1297–1318 | 4.0 s | 67.8 | 30 | 76.0 / 76.2 | 0 | 0 | 0 | 4.7 min |  |

Máxima geral: ps4_fan 79.0 °C, k10temp 79.2 °C (vigia, inclui os testes de 08/11 18:24–18:30). Pausas do vigia: 0.

### Execuções e tempo total

| início | fim | duração | faixa |
|---|---|---|---|
| 2026-11-08 18:42:55 | 2026-11-08 19:44:06 | 1.02 h | faixa 0-1318 |
| 2026-11-08 22:49:16 | 2026-11-08 22:54:49 | 0.09 h | faixa 197-197 |
| 2026-11-08 22:55:57 | 2026-11-08 23:10:50 | 0.25 h | faixa 197-246 |
| 2026-11-08 23:30:19 | 2026-11-09 03:22:27 | 3.87 h | faixa 0-1318 |

Tempo em execução (soma das 4): 5.23 h; do primeiro início ao último FIM (inclui a parada e o reboot): 8.66 h. Soma dos tempos ponta a ponta das 1.319 respostas: 4.24 h.

**Kernel (amdgpu|drm|gpu):** boot -1 (36affb65…), 18:42:55–19:44:06: 0; boot 0 (8eb17a35…), 22:49:16–03:22:27: 0. O travamento de 08/11 19:27:50 (idx 197, primeira execução) não deixou nenhuma linha do amdgpu.
