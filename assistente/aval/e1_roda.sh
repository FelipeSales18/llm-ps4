#!/usr/bin/env bash
# Condução do E1 (independente da sessão). Log em logs/e1.log; resultados em aval/resultados/e1_*.jsonl (retomável).
A=$HOME/LLM-PS4/assistente; G=$HOME/LLM-PS4/gguf/out; cd "$A" || exit 1
para() { [ -f logs/servidor_8090.pid ] && kill "$(cat logs/servidor_8090.pid)" 2>/dev/null; sleep 3; }
para; aval/servidor.sh $G/qwen3-1.7b-gsm8k-grpo-Q8_0.gguf 8090 4 4096 --chat-template-file $G/chat_template_treinado.jinja || exit 1
for c in guloso oficial oficial_s2; do python3 aval/e1_config.py http://127.0.0.1:8090 $c aval/resultados/e1_grpo_$c.jsonl --paralelo 4; done
para; aval/servidor.sh $G/qwen3-1.7b-base-Q8_0.gguf 8090 4 4096 --chat-template-file $G/chat_template_treinado.jinja || exit 1
for c in guloso oficial; do python3 aval/e1_config.py http://127.0.0.1:8090 $c aval/resultados/e1_base_$c.jsonl --paralelo 4 --so bbh; done
para; echo "E1 FIM $(date '+%F %T')"
