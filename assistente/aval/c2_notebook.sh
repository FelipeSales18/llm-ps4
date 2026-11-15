#!/usr/bin/env bash
# C2 no notebook (dev): ferramentas com a instrução original (que não encurta o raciocínio) e raciocínio ligado, no Qwen3-1.7B.
A=$HOME/LLM-PS4/assistente; G=$HOME/LLM-PS4/gguf/out; cd "$A" || exit 1
while pgrep -f "^bash aval/c1_notebook.sh" >/dev/null; do sleep 30; done
para() { [ -f logs/servidor_8090.pid ] && kill "$(cat logs/servidor_8090.pid)" 2>/dev/null; sleep 4; }
para; aval/servidor.sh $G/qwen3-1.7b-base-Q4_K_M.gguf 8090 4 6144 || exit 1
for c in base0 c2_ferr c2_ferr_dica c2_rac; do echo "$(date +%T) === $c"; python3 aval/roda.py --config configs/$c.json --url http://127.0.0.1:8090 --divisao dev --saida aval/resultados/q17b_${c}_dev.jsonl --paralelo 4 --tempo-limite-item 900; done
para; echo "C2 FIM $(date '+%F %T')"
