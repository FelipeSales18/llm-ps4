# Como retomar o projeto "assistente local no PS4"

Pausado pelo usuário em **2026-11-13 16:13**. Nada está rodando: rodadas do notebook encerradas (resultados gravados são
retomáveis), agentes parados, verificação periódica cancelada. Histórico completo em `DIARIO.md` (ler o fim primeiro);
linha anterior (edição de pesos, fusão, quantização) em `../weight-edit/DIARIO.md`.

## Atualização de 14/11 21:50 (ler primeiro)
- Itens da avaliação corrigidos por auditoria (v2; originais em `aval/itens_v1_antes_auditoria/`); tudo repontuado.
- C2/C3 feitos: o modelo ajustado do usuário EMPATA com o original na mesma configuração (59,2% × 59,2%); raciocínio ligado descartado (3,6× o tempo, sem ganho).
- **Ferramentas pelo modelo (`c2_ferr_dica`): +7,5 pt no dev, mas −9,2 pt na SELEÇÃO → REJEITADA.** Melhor configuração confirmada: `configs/base0.json` (seleção 65,0%).
- Cliente de conversa pronto e com autoteste aprovado: `runtime/conversar.py` (falta testar com servidor real e no PS4).
- Próximo passo sugerido: ferramentas acionadas por regra (sem expor o esquema ao modelo), no dev; decidir 1.7B × Qwen3.5-4B; depois PS4.

## Onde paramos (estado de 13/11)
1. **Avaliação pronta e congelada:** 360 itens em PT-BR (`aval/itens/`), divisão em `aval/divisao.json` (120 dev / 120
   seleção / 120 teste). **Seleção e teste nunca foram executados.** Autoteste: `python3 aval/verifica.py --autoteste`
   (esperado: `TOTAL: 360 itens, 0 problemas`).
2. **Comparativo de modelos (dev, notebook/CPU, configuração neutra `configs/base0.json`):** chat atual 25,0%;
   Qwen3.5-2B 48,3%; Qwen3-1.7B original 55,8% (59,2% numa segunda rodada: o ruído é de ~3–4 pt); MiniCPM5-2B 56,7%;
   Gemma 4 E2B 62,5%; Granite 4.2 3B 63,3%; **Qwen3.5-4B 71,7%** (+15,8; p=0,004; ~4× mais lento). Resultados em
   `aval/resultados/m1nb_*_dev.jsonl`; resumo: `python3 aval/resume.py <referência.jsonl> <outros.jsonl>`.
3. **Instruções e ferramentas no Qwen3-1.7B (dev):** nada superou a configuração neutra. Instruções que pedem brevidade
   PIORAM (−11 a −12 pt); ferramentas levam a categoria "ferramentas" de 30% para 75%, mas foram testadas junto com uma
   instrução curta que derrubou o resto. Resultados em `aval/resultados/q17_*_dev.jsonl`.
4. **PS4:** a GPU travou 3 vezes em 13/11 com o executor novo (08:44, 13:32, 14:22; `amdgpu ring timeout`), inclusive com o
   Qwen3-1.7B, que tinha rodado ~22 h sem travar no protocolo antigo. Causa em aberto (hipótese: prompts longos e/ou
   streaming). Cada travamento exige reinício manual do console. No fim da sessão o PS4 não respondia por ssh.
   Configuração de servidor que economiza memória (medida): `--load-mode mmap --cache-ram 256 -np 1`.
   A configuração anterior do chat NÃO foi alterada: `/mnt/midia/llm-ps4/chat-gpu/comando.txt`.

## O que ficou pela metade (tudo retomável: o executor pula itens já gravados)
- `aval/c1_notebook.sh`: faltou terminar o prompt conciso no Qwen3.5-4B (113/120 em `q4b_c1_conciso_dev.jsonl`).
- `aval/c2_notebook.sh` (NÃO rodou): `base0` × `c2_ferr` (instrução original + calculadora + estado) × `c2_ferr_dica` ×
  `c2_rac` (raciocínio ligado). É o próximo teste mais importante: isola as ferramentas.
- `aval/c3_notebook.sh` (NÃO rodou): o modelo ajustado do usuário (publicado e refundido em fp32) com a mesma `base0` —
  responde "o original é melhor que o meu?" separando modelo de configuração.
- `revisao_itens/auditoria_itens.json`: auditoria de justiça dos itens feita pelo Codex (limites de palavras não
  informados ao assistente, verificações rígidas). **Não revisada nem aplicada.** Se aplicar, repontuar com
  `python3 aval/repontua.py <arquivos>` e conferir o autoteste.

## Para recomeçar (no notebook, na tomada)
```
cd ~/LLM-PS4/assistente
python3 aval/verifica.py --autoteste | tail -1            # confere a avaliação
nohup aval/c1_notebook.sh > logs/c1_notebook.log 2>&1 &   # termina o que faltou (pula o que já está feito)
nohup aval/c2_notebook.sh > logs/c2_notebook.log 2>&1 &   # espera o c1 e roda as ferramentas com a instrução original
nohup aval/c3_notebook.sh > logs/c3_notebook.log 2>&1 &   # espera os anteriores e mede o modelo ajustado
tail -f logs/c2_notebook.log
```
Servidor local avulso para testes: `aval/servidor.sh <modelo.gguf> 8090 4 6144` (parar: `kill $(cat logs/servidor_8090.pid)`).
Modelos baixados: `modelos/MANIFEST.json`. Uma execução avulsa:
`python3 aval/roda.py --config configs/base0.json --url http://127.0.0.1:8090 --divisao dev --saida aval/resultados/X.jsonl --paralelo 4`.

## Próximos passos, em ordem
1. Rodar C2 e C3; escolher a configuração do Qwen3-1.7B; confirmar UMA vez no conjunto de seleção (`--divisao sel`).
2. Decidir Qwen3-1.7B × Qwen3.5-4B (qualidade × tempo; o 4B é da família que travou a GPU).
3. PS4, depois de reiniciado: UM teste curto de prompt longo em lotes pequenos (`-b`/`-ub`) para entender o travamento;
   medições só com `ps4/mede_modelo3.sh` (blocos, descanso, parada no travamento) e `ps4/vigia_termico2.sh` em tmux.
   No console a fila fica em `/mnt/midia/llm-ps4/experiments/wedit-fila-ps4/` (há um arquivo `PARAR`; apagar para religar).
4. Quantização do modelo escolhido (imatrix com texto em português; lições em `../weight-edit/DIARIO.md`, 13/11 08:15).
5. Cliente de conversa com vigia de travamento e modo de reserva em CPU; teste final único (`--divisao teste`) contra
   `configs/ref_anterior.json`; relatório e instruções de reversão.

## Regras de trabalho combinadas
- Delegar ao Codex (`codex exec -m gpt-6.1-sol|gpt-6-luna|gpt-6.1-terra … < /dev/null`), nunca `gpt-6-astra`; subagentes
  Claude só Sonnet/Haiku. O Codex não vê seleção/teste quando propõe instruções.
- Rodadas longas sempre como script encadeado independente da sessão; registrar critério antes de cada rodada no `DIARIO.md`.
- Não reiniciar o PS4 remotamente; não mandar arquiteturas novas para a GPU do console sem necessidade.
