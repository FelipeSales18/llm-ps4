#!/bin/bash
# Primeiro benchmark CPU (1 GB de VRAM reservada).
B=/mnt/midia/llm-ps4; cd $B/llama.cpp
D=$(date +%Y%m%d); R=$B/results; W="python3 -I $B/scripts/maxrss.py"
LOG=$B/logs/bench1_$(date +%Y%m%d_%H%M%S).log
{
echo "START $(date -Is) commit=$(git rev-parse HEAD) vram=1GB"
for m in Qwen3-0.6B-Q4_K_M Qwen3-1.7B-Q4_K_M; do
  f=$B/models/unsloth/${m%-Q4_K_M}-GGUF/$m.gguf
  echo "== $m  $(date -Is)"
  $W nice -n 10 ./build/bin/llama-bench -m "$f" -p 512 -n 128 -r 3 -t 4,8 -o csv \
     > $R/bench_${m}_${D}.csv 2> $R/bench_${m}_${D}.stderr.txt
  echo "rc=$? $(grep -E 'Maximum resident|Elapsed' $R/bench_${m}_${D}.stderr.txt | tr -s '\t\n' '  ')"
done
echo "== sanity $(date -Is)"
$W nice -n 10 ./build/bin/llama-cli -m $B/models/unsloth/Qwen3-1.7B-GGUF/Qwen3-1.7B-Q4_K_M.gguf \
   --jinja -n 256 -st --simple-io \
   -p "Joana tem 3 caixas com 12 lápis cada e dá 7 lápis para a irmã. Quantos lápis sobram? /no_think" \
   < /dev/null > $R/sanity_1.7b.txt 2>&1
echo "rc=$?"
echo "END $(date -Is)"
} > $LOG 2>&1
ln -sf $LOG $B/logs/bench1_latest.log
