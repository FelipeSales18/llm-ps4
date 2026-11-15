#!/usr/bin/env bash
# M1 no NOTEBOOK (CPU): qualidade dos modelos no conjunto de desenvolvimento, enquanto a GPU do PS4 está indisponível.
# Independente da sessão; retomável (o executor pula itens já gravados). Log: logs/m1_notebook.log
A=$HOME/LLM-PS4/assistente; G=$HOME/LLM-PS4/gguf/out; cd "$A" || exit 1
para() { [ -f logs/servidor_8090.pid ] && kill "$(cat logs/servidor_8090.pid)" 2>/dev/null; sleep 4; }
um() { # nome  gguf  config  [extras do servidor]
  n=$1; m=$2; c=$3; shift 3; out=aval/resultados/m1nb_${n}_dev.jsonl
  [ -s "$out" ] && [ "$(wc -l < "$out")" -ge 120 ] && { echo "$(date +%T) $n já completo"; return; }
  para; echo "$(date +%T) === $n"; aval/servidor.sh "$m" 8090 4 6144 "$@" || { echo "$(date +%T) $n: servidor NÃO subiu"; return; }
  python3 aval/roda.py --config "$c" --url http://127.0.0.1:8090 --divisao dev --saida "$out" --paralelo 4 --pid-servidor "$(cat logs/servidor_8090.pid)" --tempo-limite-item 600
  para; }
um qwen35_2b      modelos/qwen3.5-2b-q4km/Qwen3.5-2B-Q4_K_M.gguf              configs/base0.json
um qwen3_17b_orig $G/qwen3-1.7b-base-Q4_K_M.gguf                              configs/base0.json
um ref_anterior   $G/qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf                        configs/ref_anterior.json --chat-template-file $G/chat_template_treinado.jinja
um minicpm5_2b    modelos/minicpm5-2b-q4km/MiniCPM5-2B-Q4_K_M.gguf            configs/base0.json
um qwen35_4b      modelos/qwen3.5-4b-q4km/Qwen3.5-4B-Q4_K_M.gguf              configs/base0.json
um granite42_3b   modelos/granite-4.2-3b-q4km/granite-4.2-3b-Q4_K_M.gguf      configs/base0.json
um gemma4_e2b     modelos/gemma-4-e2b-q4km/gemma-4-E2B-it-Q4_K_M.gguf         configs/base0.json
echo "M1 NOTEBOOK FIM $(date '+%F %T')"
