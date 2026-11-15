#!/usr/bin/env bash
# C3 (dev): o modelo AJUSTADO do usuário com a MESMA configuração neutra base0 — separa efeito do modelo do efeito da configuração.
A=$HOME/LLM-PS4/assistente; G=$HOME/LLM-PS4/gguf/out; W=$HOME/LLM-PS4/weight-edit/candidatos/gguf; cd "$A" || exit 1
while pgrep -f "^bash aval/c[12]_notebook.sh" >/dev/null; do sleep 30; done
para() { [ -f logs/servidor_8090.pid ] && kill "$(cat logs/servidor_8090.pid)" 2>/dev/null; sleep 4; }
for par in "grpo_bf16:$G/qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf" "grpo_fp32:$W/qwen3-1.7b-grpo-fp32merge-Q4_K_M.gguf"; do n=${par%%:*}; m=${par#*:}
  para; aval/servidor.sh "$m" 8090 4 6144 --chat-template-file $G/chat_template_treinado.jinja || continue; echo "$(date +%T) === $n"
  python3 aval/roda.py --config configs/base0.json --url http://127.0.0.1:8090 --divisao dev --saida aval/resultados/q17c_${n}_base0_dev.jsonl --paralelo 4 --tempo-limite-item 600; done
para; echo "C3 FIM $(date '+%F %T')"
