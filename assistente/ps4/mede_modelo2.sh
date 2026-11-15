#!/usr/bin/env bash
# Mede um modelo NO PS4 (GPU via Vulkan) com o MESMO executor da avaliação: tempo de carga, memória (processo e sistema),
# tempo até o primeiro token, tempo total, tokens/s e acerto numa amostra. Não toca na configuração anterior do chat.
# Uso: mede_modelo.sh <nome> <arquivo.gguf> <config.json> [divisao=dev] [itens_por_categoria=4] [contexto=8192] [extras do servidor...]
R=/mnt/midia/llm-ps4; A=$R/assistente; N=$1; M=$2; CFG=$3; DIV=${4:-dev}; K=${5:-4}; CTX=${6:-8192}; shift 6 2>/dev/null || shift $#; P=8083
D=$A/medidas/$N; mkdir -p $D/cache/mesa $D/cache/xdg $D/tmp; cd $A || exit 1
pgrep -x llama-server >/dev/null && { echo "já há um llama-server rodando; não vou disputar a GPU"; exit 1; }
disp() { awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo; }
swp() { awk '/SwapTotal/ {t=$2} /SwapFree/ {f=$2} END {print int((t-f)/1024)}' /proc/meminfo; }
naocabe() { echo "{\"nome\": \"$N\", \"cabe\": false, \"motivo\": \"$1\", \"quando\": \"$(date '+%F %T')\"}" > $D/medida.json; cat $D/medida.json; exit 0; }
# GUARDA DE MEMÓRIA (preserva o acesso ao console): não carrega um modelo que não caiba com folga, e desiste se o sistema começar a usar swap
tam=$(( $(stat -c %s "$M") / 1048576 )); m0=$(disp); s0=$(swp)
[ $(( tam + 900 )) -gt $m0 ] && naocabe "arquivo de ${tam} MB + ~900 MB de contexto/trabalho > ${m0} MB disponíveis"
t0=$(date +%s.%N)
env VK_DRIVER_FILES=$R/vulkan/mesa-ps4-extract2-20261106-152705/radeon_icd_local.json MESA_SHADER_CACHE_DIR=$D/cache/mesa XDG_CACHE_HOME=$D/cache/xdg TMPDIR=$D/tmp \
  $R/llama.cpp/build-vulkan/bin/llama-server -m "$M" -ngl 99 -c $CTX -t 8 --jinja --host 127.0.0.1 --port $P "$@" > $D/servidor.log 2>&1 &
pid=$!; ok=0
for i in $(seq 1 300); do curl -s http://127.0.0.1:$P/health | grep -q '"ok"' && { ok=1; break; }; kill -0 $pid 2>/dev/null || break; sleep 1; done
[ $ok = 1 ] || { echo "servidor não subiu"; tail -15 $D/servidor.log; kill $pid 2>/dev/null; exit 1; }
t1=$(date +%s.%N); m1=$(disp); s1=$(swp)
if [ $m1 -lt 400 ] || [ $(( s1 - s0 )) -gt 300 ]; then kill $pid; sleep 3; naocabe "após a carga sobraram ${m1} MB disponíveis e o swap cresceu $(( s1 - s0 )) MB"; fi
python3 aval/roda.py --config "$CFG" --url http://127.0.0.1:$P --divisao $DIV ${K:+--por-categoria $K} --saida $D/roda_${DIV}.jsonl --pid-servidor $pid > $D/roda.log 2>&1
m2=$(disp); hwm=$(awk '/VmHWM/ {print int($2/1024)}' /proc/$pid/status); rss=$(awk '/VmRSS/ {print int($2/1024)}' /proc/$pid/status); temp=$(sensors 2>/dev/null | awk '/temp1|Tdie|edge/ {print $2; exit}')
kill $pid; sleep 3
python3 aval/resume.py $D/roda_${DIV}.jsonl > $D/resumo.md 2>&1
python3 - <<PY > $D/medida.json
import json, os
print(json.dumps({"nome": "$N", "gguf": "$M", "bytes": os.path.getsize("$M"), "contexto": $CTX, "carga_s": round($t1 - $t0, 1), "mem_disponivel_antes_mb": $m0, "apos_carga_mb": $m1, "apos_avaliacao_mb": $m2, "cabe": True, "swap_antes_mb": $s0, "swap_depois_mb": $(swp),
                  "consumo_sistema_mb": $m0 - $m2, "rss_mb": $rss, "pico_rss_mb": $hwm, "temperatura": "$temp", "config": "$CFG", "quando": "$(date '+%F %T')"}, ensure_ascii=False))
PY
cat $D/medida.json; echo; cat $D/resumo.md
