#!/bin/bash
cd /mnt/midia/llm-ps4/llama.cpp
L=/mnt/midia/llm-ps4/logs/build_$(date +%Y%m%d_%H%M%S).log
{
echo "START $(date -Is)"
t0=$(date +%s)
nice -n 10 cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF || { echo "CONFIGURE_FAIL rc=$?"; exit 1; }
t1=$(date +%s)
nice -n 10 cmake --build build --config Release -j 6 --target llama-bench llama-cli; rc=$?
t2=$(date +%s)
echo "configure_s=$((t1-t0)) build_s=$((t2-t1)) total_s=$((t2-t0)) rc=$rc"
echo "END $(date -Is) rc=$rc"
} > "$L" 2>&1
ln -sf "$L" /mnt/midia/llm-ps4/logs/build_latest.log
