#!/usr/bin/env bash
# Tarefa 5b: compila só llama-bench e llama-cli com Vulkan (sem usar a GPU). Roda na janela "build" do tmux vkbuild.
# Uso: bash vkbuild_runner.sh <pasta_do_experimento>
set -u
export LC_ALL=C
export TMPDIR=/mnt/midia/llm-ps4/tmp-vkbuild/tmp
E=$1
L=/mnt/midia/llm-ps4/llama.cpp
mountpoint -q /mnt/midia || { echo "ABORTADO: /mnt/midia não está montado" | tee -a "$E/status.txt"; exit 1; }
ps -o pgid= $$ | tr -d ' ' > "$E/build.pgid"
T0=$(date +%s)
echo "INICIO $(date '+%F %T') pgid=$(cat "$E/build.pgid")" >> "$E/status.txt"
echo "TEMP_ANTES $(sensors 2>/dev/null | awk '/^temp1:/{printf "%s ", $2}')" >> "$E/status.txt"
nice -n 10 cmake --build "$L/build-vulkan" --target llama-bench llama-cli -j 6 > "$E/build.log" 2>&1
RC=$?
T1=$(date +%s)
echo "TEMP_DEPOIS $(sensors 2>/dev/null | awk '/^temp1:/{printf "%s ", $2}')" >> "$E/status.txt"
echo "FIM $(date '+%F %T') rc=$RC duracao_s=$((T1-T0))" >> "$E/status.txt"
tail -5 "$E/build.log"
echo "Build terminado: rc=$RC, $((T1-T0)) s"
