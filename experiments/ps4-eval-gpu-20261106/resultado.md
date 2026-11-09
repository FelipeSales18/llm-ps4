## Tarefa 8: Qwen3-1.7B GRPO Q4_K_M no PS4, GPU (Vulkan, -ngl 99) × CPU (build original)

### Acurácia (100 questões por braço)

| | GPU | CPU |
|---|---|---|
| acerto strict | 70/100 | 74/100 |
| acerto flex | 77/100 | 81/100 |

### Tempos e tokens (todas as 100)

| | GPU | CPU | GPU/CPU |
|---|---|---|---|
| n (tempos válidos) | 100 | 100 | 1.00 |
| tokens por resposta (média / mediana) | 125.3 / 112 | 126.4 / 112 |  |
| cortadas (320) | 0 | 0 |  |
| tokens de prompt processados (média) | 69.9 | 69.9 |  |
| tempo de prompt por resposta (s) | 0.47 | 3.12 | 0.15 |
| tempo de geração por resposta (s) | 10.50 | 14.15 | 0.74 |
| geração tokens/s (total tokens ÷ total tempo) | 11.93 | 8.93 | 1.34 |
| segundos por resposta (ponta a ponta) | 11.18 | 17.47 |  |
| segundos por resposta correta (flex) | 14.52 | 21.57 |  |

**Pausas do vigia:** 0. Perguntas com tempo inválido: GPU nenhuma; CPU nenhuma.
Sem pausas, os resultados "com" e "sem" as perguntas afetadas são idênticos à tabela acima.

### GPU × CPU, questão a questão

- **flex:** GPU acerta e CPU erra em 2 [78, 96]; CPU acerta e GPU erra em 6 [4, 9, 26, 34, 67, 69]. McNemar exato (bicaudal): p = 0.289. Mesmo veredito em 92/100 (ambos acertam 75, ambos erram 17).
- **strict:** GPU acerta e CPU erra em 3 [73, 78, 96]; CPU acerta e GPU erra em 7 [4, 26, 29, 33, 34, 67, 69]. McNemar exato (bicaudal): p = 0.344. Mesmo veredito em 90/100 (ambos acertam 67, ambos erram 23).
- **Saída idêntica GPU × CPU:** 27/100. Mesmo número de tokens gerados: 33/100.

### CPU de hoje × treinado de 03/11 (mesmo binário build/, mesmo modelo)

| | CPU hoje | 03/11 | GPU hoje |
|---|---|---|---|
| acerto flex | 81/100 | 81/100 | 77/100 |
| acerto strict | 74/100 | 74/100 | 70/100 |
| tokens por resposta (média / mediana) | 126.4 / 112 | 126.4 / 112 | 125.3 / 112 |
| tempo de prompt por resposta (s) | 3.12 | 3.09 | 0.47 |
| tempo de geração por resposta (s) | 14.15 | 13.78 | 10.50 |
| geração tokens/s (total tokens ÷ total tempo) | 8.93 | 9.17 | 11.93 |
| segundos por resposta (ponta a ponta) | 17.47 | 17.15 | 11.18 |
| segundos por resposta correta (flex) | 21.57 | 21.17 | 14.52 |
| cortadas (320) | 0 | 0 | 0 |
- CPU hoje × 03/11: saída idêntica em 100/100; mesmo veredito flex em 100/100.
- GPU hoje × 03/11: saída idêntica em 27/100; mesmo veredito flex em 92/100.

### Temperatura por bloco (vigia a cada 5 s; k10temp no início/fim do run_eval)

| bloco | braço | início k10temp (°C) | fim k10temp (°C) | máx ps4_fan | máx k10temp | fan1 (mín–máx) | atingiu alvo | espera (s) |
|---|---|---|---|---|---|---|---|---|
| 0 | repouso | 64.75 | — | — | — | — | — | 300 |
| 1 | gpu | 65.25 | 77.0 | 79.0 | 79.0 | 0–28 | True | 1 |
| 2 | cpu | 68.0 | 75.625 | 79.0 | 79.5 | 0–35 | False | 314 |
| 3 | gpu | 67.75 | 74.625 | 79.0 | 79.1 | 0–42 | True | 116 |
| 4 | cpu | 67.75 | 74.5 | 78.0 | 78.5 | 0–0 | True | 35 |

Máxima geral: ps4_fan 79.0 °C, k10temp 79.5 °C.
fan1_input > 0 pela primeira vez às 17:31:58 com ps4_fan 79.0 °C / k10temp 79.0 °C.
- ps4_fan em [0, 76) °C: fan1 médio 0.1 (n=190, máx 8)
- ps4_fan em [76, 78) °C: fan1 médio 9.7 (n=279, máx 40)
- ps4_fan em [78, 80) °C: fan1 médio 21.6 (n=252, máx 42)

**Geração tokens/s por bloco:** bloco 1 (gpu): 11.93, bloco 2 (cpu): 8.89, bloco 3 (gpu): 11.94, bloco 4 (cpu): 8.97
