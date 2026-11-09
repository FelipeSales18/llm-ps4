#!/usr/bin/env bash
# Tarefa 6: primeiro uso do backend Vulkan do llama.cpp no PS4. Um passo por execução.
# Uso (do Fedora): ssh ps4 'bash -s -- <6a|6b|6c>' < run_vulkan.sh
# Grava só em /mnt/midia/llm-ps4/experiments/vulkan-run-20261106/. Sem sudo, sem instalar.
set -u
export LC_ALL=C
PASSO=${1:?passo}
R=/mnt/midia/llm-ps4/experiments/vulkan-run-20261106
DRV=/mnt/midia/llm-ps4/vulkan/mesa-ps4-extract2-20261106-152705
B=/mnt/midia/llm-ps4/llama.cpp/build-vulkan/bin
M=/mnt/midia/llm-ps4/models/unsloth/Qwen3-0.6B-GGUF/Qwen3-0.6B-Q4_K_M.gguf
M_SHA=ac2d97712095a558e31573f62f466a3f9d93990898b0ec79d7c974c1780d524a   # MANIFEST.csv, linha do 0.6B
PROMPT='What is 17 * 23? Answer with just the number.'

mountpoint -q /mnt/midia || { echo "ABORTADO: /mnt/midia não está montado"; exit 1; }
if [ "$PASSO" = 6a ]; then
  [ -e "$R" ] && { echo "ABORTADO: $R já existe"; exit 1; }
  mkdir -p "$R/cache/mesa" "$R/cache/xdg" "$R/tmp" || exit 1
else
  [ -f "$R/6a.ok" ] || { echo "ABORTADO: 6a não passou"; exit 1; }
fi
[ "$PASSO" = 6c ] && { [ -f "$R/6b.ok" ] || { echo "ABORTADO: 6b não passou"; exit 1; }; }

export VK_DRIVER_FILES="$DRV/radeon_icd_local.json" MESA_SHADER_CACHE_DIR="$R/cache/mesa" XDG_CACHE_HOME="$R/cache/xdg" TMPDIR="$R/tmp"
PS4H=$(dirname "$(grep -lx ps4_fan /sys/class/hwmon/hwmon*/name | head -1)")
K10H=$(dirname "$(grep -lx k10temp /sys/class/hwmon/hwmon*/name | head -1)")
temps() { awk -v a="$(cat $PS4H/temp1_input)" -v b="$(cat $K10H/temp1_input)" 'BEGIN{printf "ps4_fan=%.1f k10temp=%.1f maior=%.1f", a/1000, b/1000, (a>b?a:b)/1000}'; }
maior() { local a b; a=$(cat $PS4H/temp1_input); b=$(cat $K10H/temp1_input); echo $(( a > b ? a : b )); }

prechecagem() {
  if pgrep -a ffmpeg; then echo "PARADO: há ffmpeg rodando"; exit 1; fi
  local w=0
  while [ "$(maior)" -ge 74000 ]; do
    [ $w -ge 300 ] && { echo "PARADO: temperatura >= 74 C por 5 min ($(temps))"; exit 1; }
    timeout 15 tail -f /dev/null; w=$((w+15))
  done
  echo "pré-checagem ok: sem ffmpeg; $(temps)${w:+ (esperou ${w}s)}"
}

# rodar <nome> <timeout_s> cmd...   (stdout -> $R/<nome>.out, stderr -> $R/<nome>.err, temperaturas -> $R/<nome>_temps.log)
rodar() {
  local nome=$1 to=$2; shift 2
  echo; echo "===== $nome: $* ====="
  prechecagem
  echo "temperatura antes: $(temps)"
  local t0; t0=$(date +%s)
  timeout -s KILL "$to" "$@" < /dev/null > "$R/$nome.out" 2> "$R/$nome.err" &
  local pid=$! fim=$(( $(date +%s) + to + 30 )) mx=0 m quente=0
  while kill -0 "$pid" 2>/dev/null && [ "$(date +%s)" -lt "$fim" ]; do
    m=$(maior); [ "$m" -gt "$mx" ] && mx=$m
    echo "$(date +%T) $(temps)" >> "$R/${nome}_temps.log"
    if [ "$m" -ge 85000 ]; then kill -KILL "$pid" 2>/dev/null; quente=1; echo "MORTO: temperatura >= 85 C"; fi
    timeout 5 tail --pid="$pid" -f /dev/null
  done
  if kill -0 "$pid" 2>/dev/null; then RC=999; echo "PROCESSO PRESO após ${to}+30 s (provável travamento da GPU)"; else wait "$pid"; RC=$?; fi
  [ $quente = 1 ] && RC=998
  echo "código de saída: $RC$([ "$RC" = 137 ] && echo ' (morto pelo timeout)'); duração: $(( $(date +%s) - t0 )) s; máxima durante: $(awk -v m=$mx 'BEGIN{printf "%.1f", m/1000}') C"
  echo "temperatura depois: $(temps)"
  echo "--- kernel (amdgpu|drm|gpu) desde o início do passo:"
  local k; k=$(journalctl -k --no-pager --since "@$t0" 2>/dev/null | grep -iE 'amdgpu|drm|gpu')
  echo "${k:-(nenhuma linha nova)}"
  KERR=$(printf '%s\n' "$k" | grep -ciE 'error|timeout|reset|fault|hang|fail|lockup')
  echo "linhas novas de erro no kernel: $KERR"
  echo "--- gravações novas em ~ ou /tmp (fora qBittorrent): $(find ~ /tmp -newermt "@$t0" -user "$(id -u)" 2>/dev/null | grep -vi qbittorrent | head -5 | tr '\n' ' ')"
  if [ "$RC" != 0 ] || [ "$KERR" -gt 0 ]; then echo "ERRO no passo $nome: parando"; tail -15 "$R/$nome.err"; exit 1; fi
}

echo "########## Tarefa $PASSO — $(date '+%F %T') ##########"
case "$PASSO" in
6a)
  rodar 6a_list_devices 60 "$B/llama-bench" --list-devices
  echo "--- saída (stdout+stderr):"; cat "$R/6a_list_devices.out" "$R/6a_list_devices.err"
  if grep -qiE 'vulkan' "$R/6a_list_devices.out" "$R/6a_list_devices.err"; then touch "$R/6a.ok"; echo "RESULTADO 6a: GPU listada"; else echo "RESULTADO 6a: GPU NÃO listada — parando"; exit 1; fi
  ;;
6b)
  echo "--- SHA256 do modelo (manifesto: $M_SHA)"
  got=$(sha256sum "$M" | cut -d' ' -f1); echo "obtido:   $got"
  [ "$got" = "$M_SHA" ] && echo "HASH OK" || { echo "PARADO: hash do modelo não bate"; exit 1; }
  rodar 6b_bench_gpu 300 "$B/llama-bench" -m "$M" -ngl 99 -p 16 -n 8 -r 1
  echo "--- stdout:"; cat "$R/6b_bench_gpu.out"
  echo "--- stderr (ggml_vulkan / avisos):"; grep -iE 'ggml_vulkan|warn|error' "$R/6b_bench_gpu.err" | head -20
  touch "$R/6b.ok"
  ;;
6c)
  for ngl in 99 0; do
    rodar "6c_cli_ngl$ngl" 300 "$B/llama-cli" -m "$M" -ngl $ngl -st --simple-io -c 2048 -n 64 --temp 0 -rea off -p "$PROMPT"
    echo "--- resposta (stdout de -ngl $ngl):"; cat "$R/6c_cli_ngl$ngl.out"; echo
    echo "--- stderr (offload, ggml_vulkan, desempenho):"; grep -iE 'ggml_vulkan|offload|layers|prompt eval|eval time|t/s|tokens per second' "$R/6c_cli_ngl$ngl.err" | head -15
  done
  ;;
*) echo "passo inválido"; exit 1;;
esac
( cd "$R" && find . -maxdepth 1 -type f ! -name sha256.txt | sort | xargs sha256sum > sha256.txt )
echo "Pronto: $PASSO"
