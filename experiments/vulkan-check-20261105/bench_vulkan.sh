#!/usr/bin/env bash
# Tarefa 7: benchmark do Qwen3-1.7B treinado (GRPO, Q4_K_M) no PS4, GPU (Vulkan) x CPU, blocos intercalados.
# Regras: torrents pausados no início e retomados no fim (trap, mesmo com erro); sem ffmpeg; repouso de 300 s e
# resfriamento até repouso + 3 C (k10temp, máx. 5 min) antes de cada bloco; temperatura registrada a cada 5 s;
# pausa (SIGSTOP só no llama-bench) com maior leitura >= 85 C e retomada < 75 C; para no primeiro erro.
# Uso (no PS4, dentro do tmux): bash bench_vulkan.sh <pasta_nova_do_experimento>
set -u
export LC_ALL=C
R=$1
ST="$R/status.txt"
DRV=/mnt/midia/llm-ps4/vulkan/mesa-ps4-extract2-20261106-152705
BV=/mnt/midia/llm-ps4/llama.cpp/build-vulkan/bin
BC=/mnt/midia/llm-ps4/llama.cpp/build/bin
M=/mnt/midia/llm-ps4/models/proprios/qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf
M_SHA=d7771967dc6e5a69a8c676f8d0103763062d44b5b581aa9c707bc60a4684722b
QBT=http://127.0.0.1:8080/api/v2/torrents
REST_S=300; COOL_DELTA=3000; COOL_MAX=300
export VK_DRIVER_FILES="$DRV/radeon_icd_local.json" MESA_SHADER_CACHE_DIR="$R/cache/mesa" XDG_CACHE_HOME="$R/cache/xdg" TMPDIR="$R/tmp"

log() { echo "$(date '+%F %T') $*" | tee -a "$ST"; }
PS4H=$(dirname "$(grep -lx ps4_fan /sys/class/hwmon/hwmon*/name | head -1)")
K10H=$(dirname "$(grep -lx k10temp /sys/class/hwmon/hwmon*/name | head -1)")
k10()   { cat "$K10H/temp1_input"; }
maior() { local a b; a=$(cat "$PS4H/temp1_input"); b=$(k10); echo $(( a > b ? a : b )); }
temps() { awk -v a="$(cat "$PS4H/temp1_input")" -v b="$(k10)" 'BEGIN{printf "ps4_fan=%.1f k10temp=%.1f", a/1000, b/1000}'; }
c()     { awk -v m="$1" 'BEGIN{printf "%.1f", m/1000}'; }

retomar_torrents() {
  local n h code faltam
  n=$( [ -s "$R/qbt_pausados.txt" ] && wc -l < "$R/qbt_pausados.txt" || echo 0 )
  if [ "$n" -gt 0 ]; then
    h=$(paste -sd'|' "$R/qbt_pausados.txt")
    code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' -X POST --data-urlencode "hashes=$h" "$QBT/start")
    timeout 3 tail -f /dev/null
    faltam=$(curl -s -m 10 "$QBT/info" | python3 -c 'import json,sys; hs=set(open(sys.argv[1]).read().split()); print(sum(1 for t in json.load(sys.stdin) if t["hash"] in hs and t["state"].startswith(("stopped","paused"))))' "$R/qbt_pausados.txt" 2>/dev/null)
    log "TORRENTS: $n retomado(s) (HTTP $code; ainda parados entre eles: ${faltam:-?})"
  else
    log "TORRENTS: 0 para retomar"
  fi
}
trap 'rc=$?; retomar_torrents; log "FIM rc=$rc"' EXIT
trap 'log "ERRO: sinal recebido"; exit 1' HUP INT TERM

mountpoint -q /mnt/midia || { log "ERRO: /mnt/midia não está montado"; exit 1; }
log "INÍCIO tarefa 7 — $(temps)"

# 1) torrents
info=$(curl -s -m 10 "$QBT/info") || { log "ERRO: API do qBittorrent não respondeu"; exit 1; }
printf '%s' "$info" | python3 -c 'import json,sys; [print(t["hash"]) for t in json.load(sys.stdin) if not t["state"].startswith(("stopped","paused"))]' > "$R/qbt_pausados.txt" \
  || { log "ERRO: resposta inválida da API do qBittorrent"; exit 1; }
n=$(wc -l < "$R/qbt_pausados.txt")
if [ "$n" -gt 0 ]; then
  code=$(curl -s -m 10 -o /dev/null -w '%{http_code}' -X POST --data-urlencode "hashes=$(paste -sd'|' "$R/qbt_pausados.txt")" "$QBT/stop")
  timeout 3 tail -f /dev/null
  ativos=$(curl -s -m 10 "$QBT/info" | python3 -c 'import json,sys; print(sum(1 for t in json.load(sys.stdin) if not t["state"].startswith(("stopped","paused"))))')
  log "TORRENTS: $n ativo(s) pausado(s) (HTTP $code; ativos agora: $ativos)"
  [ "$ativos" = 0 ] || { log "ERRO: ainda há torrents ativos"; exit 1; }
else
  log "TORRENTS: 0 ativo(s) para pausar"
fi

# 2) ffmpeg e modelo
if pgrep -a ffmpeg >> "$ST"; then log "ERRO: ffmpeg rodando"; exit 1; fi
got=$(sha256sum "$M" | cut -d' ' -f1)
[ "$got" = "$M_SHA" ] && log "MODELO: SHA256 OK ($(basename "$M"))" || { log "ERRO: SHA256 do modelo não bate ($got)"; exit 1; }

# 3) repouso
log "REPOUSO: ${REST_S}s ocioso"
timeout "$REST_S" tail -f /dev/null
REST=$(k10); ALVO=$(( REST + COOL_DELTA ))
log "REPOUSO: k10temp=$(c "$REST") C; alvo de resfriamento=$(c "$ALVO") C; $(temps)"

# 4) blocos
bloco() {  # n braço cmd...
  local n=$1 br=$2; shift 2
  local base="$R/bloco${n}_${br}"
  if pgrep -a ffmpeg >> "$ST"; then log "ERRO: ffmpeg rodando antes do bloco $n"; exit 1; fi
  local w=0
  while [ "$(k10)" -gt "$ALVO" ] && [ $w -lt $COOL_MAX ]; do timeout 15 tail -f /dev/null; w=$((w+15)); done
  local ating; ating=$( [ "$(k10)" -le "$ALVO" ] && echo sim || echo não )
  local t0; t0=$(date +%s)
  log "BLOCO $n $br: início; espera=${w}s atingiu_alvo=$ating; $(temps); load=$(cut -d' ' -f1-3 /proc/loadavg)"
  echo "# hora ps4_fan_C k10temp_C estado" > "${base}_temps.log"
  timeout -s KILL 1800 "$@" > "$base.json" 2> "$base.err" &
  local pid=$! mx=0 m est=rodando np=0 limite=$(( $(date +%s) + 1860 ))
  while kill -0 "$pid" 2>/dev/null && [ "$(date +%s)" -lt "$limite" ]; do
    m=$(maior); [ "$m" -gt "$mx" ] && mx=$m
    if [ $est = rodando ] && [ "$m" -ge 85000 ]; then
      pkill -STOP -P "$pid" 2>/dev/null; kill -STOP "$pid"; est=pausado; np=$((np+1)); log "BLOCO $n: PAUSA_85 #$np maior=$(c "$m")"
    elif [ $est = pausado ] && [ "$m" -lt 75000 ]; then
      kill -CONT "$pid"; pkill -CONT -P "$pid" 2>/dev/null; est=rodando; log "BLOCO $n: RETOMADA maior=$(c "$m")"
    fi
    echo "$(date +%T) $(c "$(cat "$PS4H/temp1_input")") $(c "$(k10)") $est" >> "${base}_temps.log"
    timeout 5 tail --pid="$pid" -f /dev/null
  done
  if kill -0 "$pid" 2>/dev/null; then log "ERRO: bloco $n preso (provável travamento da GPU)"; exit 1; fi
  wait "$pid"; local rc=$?
  local k ke; k=$(journalctl -k --no-pager --since "@$t0" 2>/dev/null | grep -iE 'amdgpu|drm|gpu')
  ke=$(printf '%s\n' "$k" | grep -ciE 'error|timeout|reset|fault|hang|fail|lockup')
  [ -n "$k" ] && printf '%s\n' "$k" > "${base}_kernel.txt"
  local res; res=$(python3 -c '
import json,sys
for r in json.load(open(sys.argv[1])):
    t = "pp%d" % r["n_prompt"] if r["n_prompt"] else "tg%d" % r["n_gen"]
    print("%s=%.2f±%.2f [%s]" % (t, r["avg_ts"], r["stddev_ts"], " ".join("%.2f" % s for s in r["samples_ts"])), end="  ")
' "$base.json" 2>/dev/null)
  log "BLOCO $n $br: fim rc=$rc duração=$(( $(date +%s) - t0 ))s máxima=$(c "$mx") C pausas=$np kernel_linhas=$( [ -n "$k" ] && printf '%s\n' "$k" | wc -l || echo 0) kernel_erros=$ke; $(temps)"
  log "BLOCO $n $br: ${res:-JSON inválido}"
  if [ "$rc" != 0 ] || [ "$ke" -gt 0 ] || [ -z "$res" ]; then log "ERRO no bloco $n: parando"; tail -5 "$base.err" >> "$ST"; exit 1; fi
}
bloco 1 gpu "$BV/llama-bench" -m "$M" -ngl 99 -p 512 -n 128 -r 3 -o json
bloco 2 cpu "$BC/llama-bench" -m "$M" -t 8 -p 512 -n 128 -r 3 -o json
bloco 3 gpu "$BV/llama-bench" -m "$M" -ngl 99 -p 512 -n 128 -r 3 -o json
bloco 4 cpu "$BC/llama-bench" -m "$M" -t 8 -p 512 -n 128 -r 3 -o json
( cd "$R" && find . -maxdepth 1 -type f ! -name sha256.txt ! -name status.txt | sort | xargs sha256sum > sha256.txt )
log "BLOCOS concluídos"
