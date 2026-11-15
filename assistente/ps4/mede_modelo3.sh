#!/usr/bin/env bash
# Mede um modelo NO PS4 com o executor da avaliação, seguindo o PROTOCOLO DE BLOCOS do projeto (lição do travamento de 13/11):
# blocos curtos de trabalho, servidor derrubado e religado a cada bloco, descanso até esfriar, parada no primeiro travamento.
# Guardas: não carrega modelo que não caiba; desiste se sobrar pouca memória ou o swap crescer; cache de prompts limitado.
# Uso: MODO=gpu|cpu mede_modelo3.sh <nome> <arquivo.gguf> <config.json> [divisao=dev] [itens_por_categoria=0(todos)] [contexto=8192] [extras do servidor...]
R=/mnt/midia/llm-ps4; A=$R/assistente; N=$1; M=$2; CFG=$3; DIV=${4:-dev}; K=${5:-0}; CTX=${6:-8192}; shift 6 2>/dev/null || shift $#; P=8083
MODO=${MODO:-gpu}; BLOCO_S=${BLOCO_S:-480}; DESCANSO_MAX=${DESCANSO_MAX:-300}; ALVO_C=${ALVO_C:-68}; LIMITE_ITEM=${LIMITE_ITEM:-150}
D=$A/medidas/$N; mkdir -p $D/cache/mesa $D/cache/xdg $D/tmp; cd $A || exit 1; say() { echo "$(date '+%F %T') $*" | tee -a $D/blocos.log; }
vivos() { ps -eo stat,comm | awk '$2=="llama-server" && $1 !~ /Z/' | wc -l; }
[ "$(vivos)" -gt 0 ] && { echo "já há um llama-server ativo; não vou disputar a máquina"; exit 1; }
disp() { awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo; }
swp() { awk '/SwapTotal/ {t=$2} /SwapFree/ {f=$2} END {print int((t-f)/1024)}' /proc/meminfo; }
temp() { t=0; for f in /sys/class/hwmon/hwmon*/temp1_input; do v=$(cat $f 2>/dev/null || echo 0); [ $v -gt $t ] && t=$v; done; echo $(( t / 1000 )); }
naocabe() { echo "{\"nome\": \"$N\", \"modo\": \"$MODO\", \"cabe\": false, \"motivo\": \"$1\", \"quando\": \"$(date '+%F %T')\"}" > $D/medida.json; cat $D/medida.json; exit 0; }
if [ $MODO = gpu ]; then BIN=$R/llama.cpp/build-vulkan/bin/llama-server; OFF="-ngl 99"; FATOR=2; else BIN=$R/llama.cpp/build/bin/llama-server; OFF=""; FATOR=1; fi
tam=$(( $(stat -c %s "$M") / 1048576 )); m0=$(disp); s0=$(swp)
[ $(( tam * FATOR + 700 )) -gt $m0 ] && naocabe "arquivo de ${tam} MB x ${FATOR} (cópias medidas no modo $MODO) + 700 MB > ${m0} MB disponíveis"
bloco=0; carga=""; m1=""; hwm=0; rss=0
while :; do
  bloco=$((bloco + 1)); t0=$(date +%s.%N)
  env VK_DRIVER_FILES=$R/vulkan/mesa-ps4-extract2-20261106-152705/radeon_icd_local.json MESA_SHADER_CACHE_DIR=$D/cache/mesa XDG_CACHE_HOME=$D/cache/xdg TMPDIR=$D/tmp \
    $BIN -m "$M" $OFF -c $CTX -t 8 --jinja --cache-ram 256 -np 1 --host 127.0.0.1 --port $P "$@" >> $D/servidor.log 2>&1 &
  pid=$!; ok=0
  for i in $(seq 1 300); do curl -s -m 3 http://127.0.0.1:$P/health | grep -q '"ok"' && { ok=1; break; }; kill -0 $pid 2>/dev/null || break; sleep 1; done
  [ $ok = 1 ] || { say "bloco $bloco: servidor NÃO subiu"; tail -8 $D/servidor.log; kill -9 $pid 2>/dev/null; exit 1; }
  [ -z "$carga" ] && { carga=$(awk -v a=$t0 -v b=$(date +%s.%N) 'BEGIN{printf "%.1f", b-a}'); m1=$(disp); s1=$(swp)
    if [ $m1 -lt 400 ] || [ $(( s1 - s0 )) -gt 300 ]; then kill $pid; sleep 3; naocabe "após a carga sobraram ${m1} MB disponíveis e o swap cresceu $(( s1 - s0 )) MB"; fi; }
  say "bloco $bloco: servidor pronto; temperatura $(temp) °C; memória disponível $(disp) MB"
  timeout -k 5 $(( BLOCO_S + LIMITE_ITEM + 90 )) python3 aval/roda.py --config "$CFG" --url http://127.0.0.1:$P --divisao $DIV $( [ "$K" != 0 ] && echo --por-categoria $K ) --saida $D/roda_${DIV}.jsonl --pid-servidor $pid --max-segundos $BLOCO_S --tempo-limite-item $LIMITE_ITEM >> $D/roda.log 2>&1; rc=$?; [ $rc = 124 ] && rc=3   # vigia por relógio: bloco que não termina = travamento
  h=$(awk '/VmHWM/ {print int($2/1024)}' /proc/$pid/status 2>/dev/null); [ "${h:-0}" -gt $hwm ] && hwm=$h; rss=$(awk '/VmRSS/ {print int($2/1024)}' /proc/$pid/status 2>/dev/null); m2=$(disp)
  kill $pid 2>/dev/null; for i in 1 2 3 4 5 6 7 8; do kill -0 $pid 2>/dev/null || break; sleep 1; done; kill -9 $pid 2>/dev/null
  say "bloco $bloco: fim (código $rc); $(wc -l < $D/roda_${DIV}.jsonl) itens gravados; temperatura $(temp) °C"
  if [ $rc = 3 ]; then say "TRAVAMENTO: parando esta medição (não religo o servidor)"; journalctl -k --no-pager --since "-10min" 2>/dev/null | grep -i -E "amdgpu|drm" | tail -5 >> $D/blocos.log; break; fi
  [ $rc = 4 ] || break
  t=0; while [ $(temp) -gt $ALVO_C ] && [ $t -lt $DESCANSO_MAX ]; do sleep 15; t=$((t + 15)); done; say "descanso de ${t}s; temperatura $(temp) °C (alvo $ALVO_C)"
done
python3 aval/resume.py $D/roda_${DIV}.jsonl > $D/resumo.md 2>&1
python3 - <<PY > $D/medida.json
import json, os
print(json.dumps({"nome": "$N", "modo": "$MODO", "gguf": "$M", "bytes": os.path.getsize("$M"), "contexto": $CTX, "cabe": True, "carga_s": float("${carga:-0}"), "mem_disponivel_antes_mb": $m0, "apos_carga_mb": ${m1:-0},
                  "apos_avaliacao_mb": ${m2:-0}, "consumo_sistema_mb": $m0 - ${m2:-0}, "rss_mb": ${rss:-0}, "pico_rss_mb": $hwm, "swap_antes_mb": $s0, "swap_depois_mb": $(swp), "blocos": $bloco, "codigo_final": $rc, "config": "$CFG", "quando": "$(date '+%F %T')"}, ensure_ascii=False))
PY
cat $D/medida.json; echo; cat $D/resumo.md
[ $rc = 3 ] && exit 3; exit 0
