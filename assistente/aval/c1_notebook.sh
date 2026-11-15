#!/usr/bin/env bash
# C1 no notebook (dev, CPU): instruções, estado, ferramentas e busca sobre o Qwen3-1.7B original; depois o prompt conciso no Qwen3.5-4B.
A=$HOME/LLM-PS4/assistente; G=$HOME/LLM-PS4/gguf/out; cd "$A" || exit 1
while pgrep -f "^bash aval/m1_notebook.sh" >/dev/null || pgrep -f "aval/m1_notebook.sh" | grep -qv $$ && pgrep -x llama-server >/dev/null && pgrep -f "m1nb_" >/dev/null; do sleep 30; done
para() { [ -f logs/servidor_8090.pid ] && kill "$(cat logs/servidor_8090.pid)" 2>/dev/null; sleep 4; }
serie() { m=$1; pre=$2; shift 2; para; aval/servidor.sh "$m" 8090 4 6144 || return
  for c in "$@"; do out=aval/resultados/${pre}_${c}_dev.jsonl; echo "$(date +%T) === $pre $c"
    python3 aval/roda.py --config configs/$c.json --url http://127.0.0.1:8090 --divisao dev --saida "$out" --paralelo 4 --tempo-limite-item 600; done; para; }
serie $G/qwen3-1.7b-base-Q4_K_M.gguf q17 base0 c1_conciso c1_contexto c1_calculo c1_estado c1_ferr c1_busca
serie modelos/qwen3.5-4b-q4km/Qwen3.5-4B-Q4_K_M.gguf q4b c1_conciso
echo "C1 FIM $(date '+%F %T')"
