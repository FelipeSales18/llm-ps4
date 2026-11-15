#!/usr/bin/env bash
# S1: confirmação no conjunto de SELEÇÃO (uma vez) de c2_ferr_dica × base0 no Qwen3-1.7B; depois ferramentas no Qwen3.5-4B (dev).
A=$HOME/LLM-PS4/assistente; G=$HOME/LLM-PS4/gguf/out; cd "$A" || exit 1
para() { [ -f logs/servidor_8090.pid ] && kill "$(cat logs/servidor_8090.pid)" 2>/dev/null; sleep 4; }
para; aval/servidor.sh $G/qwen3-1.7b-base-Q4_K_M.gguf 8090 4 6144 || exit 1
for c in base0 c2_ferr_dica; do echo "$(date +%T) === sel $c"; python3 aval/roda.py --config configs/$c.json --url http://127.0.0.1:8090 --divisao sel --saida aval/resultados/s1_q17_${c}_sel.jsonl --paralelo 4 --tempo-limite-item 600; done
para; aval/servidor.sh modelos/qwen3.5-4b-q4km/Qwen3.5-4B-Q4_K_M.gguf 8090 4 6144 || exit 1
echo "$(date +%T) === q4b c2_ferr_dica dev"; python3 aval/roda.py --config configs/c2_ferr_dica.json --url http://127.0.0.1:8090 --divisao dev --saida aval/resultados/q4b_c2_ferr_dica_dev.jsonl --paralelo 4 --tempo-limite-item 900
para; echo "S1 FIM $(date '+%F %T')"
