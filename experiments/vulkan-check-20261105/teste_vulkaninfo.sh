#!/usr/bin/env bash
# Tarefa 4c, parte 2: primeiro uso da GPU, SÓ vulkaninfo (consulta). Sem sudo, sem instalar.
# Grava só em /mnt/midia/llm-ps4/experiments/. Uso (do Fedora):
#   ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=8 ps4 'bash -s' < teste_vulkaninfo.sh
# A saída bruta (no PS4) contém UUIDs: não publicar sem revisar.
set -u
export LC_ALL=C
D=/mnt/midia/llm-ps4/vulkan/mesa-ps4-extract2-20261106-152705
ICD="$D/radeon_icd_local.json"
VI="$D/root/usr/bin/vulkaninfo"
echo; echo "########## 4c parte 2 (vulkaninfo) — $(date '+%F %T') ##########"

# ---------- Passo 1: checagens ----------
mountpoint /mnt/midia || { echo "ABORTADO: /mnt/midia não está montado"; exit 1; }
OUT="/mnt/midia/llm-ps4/experiments/vulkaninfo-test-$(date +%Y%m%d-%H%M%S)"
[ -e "$OUT" ] && { echo "ABORTADO: $OUT já existe"; exit 1; }
mkdir -p "$OUT" || exit 1
echo "Pasta de saída: $OUT"
( cd "$D" && sha256sum -c --quiet sha256.txt ) && echo "sha256 da pasta do driver: OK" \
  || { echo "ABORTADO: sha256 da pasta do driver não bate"; exit 1; }

echo; echo "===== passo 1: transcodificação (pgrep -a ffmpeg) ====="
if pgrep -a ffmpeg; then echo "PARADO: há ffmpeg rodando"; exit 1; fi
echo "(nenhum ffmpeg)"

echo; echo "===== passo 1: temperatura ====="
maxtemp() { sensors 2>/dev/null | awk '/^temp[0-9]+:/{v=$2; gsub(/[^0-9.]/,"",v); v+=0; if(v>m)m=v} END{print m+0}'; }
sensors 2>/dev/null | grep -E '^[a-z0-9_]+-|temp|fan'
T=$(maxtemp); echo "máxima: $T C"
[ "$T" = 0 ] && { echo "PARADO: não consegui ler a temperatura"; exit 1; }
waited=0
while awk -v t="$T" 'BEGIN{exit !(t>70)}'; do
  [ "$waited" -ge 300 ] && { echo "PARADO: acima de 70 C por 5 min ($T C)"; exit 1; }
  timeout 30 tail -f /dev/null; waited=$((waited+30))
  T=$(maxtemp); echo "após ${waited}s: $T C"
done
echo "temperatura ok: $T C (≤ 70)"
echo "--- uptime antes:"; uptime
T0=$(date +%s)

# Linhas do kernel desde o início do teste e contagem de erros nelas
klog()  { journalctl -k --no-pager --since "@$T0" 2>/dev/null | grep -iE 'amdgpu|drm|gpu|radv|ring|fence'; }
kerrs() { klog | grep -ciE 'error|timeout|reset|fault|hang|fail|lockup'; }

# Executa o vulkaninfo com timeout -s KILL 60 e um vigia de 90 s (processo preso em D não morre com KILL)
run_vi() {  # rótulo  arquivo  env_extra(ou "")  args...
  local label=$1 file=$2 extra=$3; shift 3
  echo "--- $label ($(date '+%T')): ${extra:+$extra }VK_DRIVER_FILES=<pasta>/radeon_icd_local.json vulkaninfo $*"
  env VK_DRIVER_FILES="$ICD" $extra timeout -s KILL 60 "$VI" "$@" > "$file" 2>&1 &
  local pid=$!
  timeout 90 tail --pid="$pid" -f /dev/null
  if kill -0 "$pid" 2>/dev/null; then RC=999; echo "PROCESSO PRESO após 90 s (provável travamento da GPU)"; return; fi
  wait "$pid"; RC=$?
  echo "código de saída: $RC$([ "$RC" = 137 ] && echo ' (morto pelo timeout de 60 s)')"
}

posteste() {
  echo; echo "===== passo 3: kernel desde o início do teste ====="
  klog || echo "(nenhuma linha nova de amdgpu/drm/gpu)"
  echo "linhas novas com erro/timeout/reset/fault/hang/fail: $(kerrs)"
  echo; echo "===== passo 3: journalctl -k -b (amdgpu|drm|gpu), últimas 20 ====="
  journalctl -k -b --no-pager 2>/dev/null | grep -iE 'amdgpu|drm|gpu' | tail -20
  echo; echo "===== passo 3: temperatura e uptime depois ====="
  sensors 2>/dev/null | grep -E '^[a-z0-9_]+-|temp|fan'; uptime
  ( cd "$OUT" && sha256sum -- * > sha256.txt 2>/dev/null )
  echo; echo "Pronto: $OUT"
}

# ---------- Passo 2: teste ----------
echo; echo "===== passo 2: vulkaninfo --summary ====="
run_vi "1ª execução" "$OUT/vulkaninfo_summary.txt" "" --summary; RC1=$RC
cat "$OUT/vulkaninfo_summary.txt"
[ "$RC1" = 999 ] && { posteste; echo "RESULTADO: processo preso; nada mais executado"; exit 2; }
NE=$(kerrs)

if [ "$RC1" != 0 ]; then
  if [ "$RC1" = 137 ] || [ "$NE" -gt 0 ]; then
    echo "Falhou com sinais de travamento (código $RC1, erros novos no kernel: $NE): NÃO repito."
  else
    echo; echo "===== passo 2: repetição com VK_LOADER_DEBUG=error,warn ====="
    run_vi "2ª execução" "$OUT/vulkaninfo_summary_debug.txt" "VK_LOADER_DEBUG=error,warn" --summary
    cat "$OUT/vulkaninfo_summary_debug.txt"
  fi
elif [ "$NE" -gt 0 ]; then
  echo "Saiu com 0, mas há $NE linha(s) novas de erro no kernel: NÃO rodo o vulkaninfo completo."
else
  echo; echo "===== passo 2b: vulkaninfo completo (só para os heaps de memória) ====="
  run_vi "completo" "$OUT/vulkaninfo_full.txt" ""
  if [ "$RC" != 999 ]; then
    echo "--- seção de memória:"
    awk '/^VkPhysicalDeviceMemoryProperties/{f=1} f&&/^VkPhysicalDeviceFeatures/{exit} f' "$OUT/vulkaninfo_full.txt" \
      | grep -vE '^\s*(budget|usage)\s*=' | head -90
    echo "--- linhas de erro/aviso no completo:"
    grep -iE 'error|warn|fail' "$OUT/vulkaninfo_full.txt" | head -20 || echo "(nenhuma)"
  fi
fi
posteste
