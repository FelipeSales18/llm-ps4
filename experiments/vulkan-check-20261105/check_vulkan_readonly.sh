#!/usr/bin/env bash
# Checagem SÓ DE LEITURA do Vulkan no PS4 (Projeto LLM-PS4).
# Sem sudo, sem instalar pacotes, sem tocar em serviços. Grava só em /mnt/midia/llm-ps4/experiments/.
# Uso (do Fedora):  ssh ps4 'bash -s' < check_vulkan_readonly.sh
# Saída contém dados da máquina: NÃO publicar sem revisar (IPs, UUIDs, MAC).
set -u

mountpoint -q /mnt/midia || { echo "ABORTADO: /mnt/midia não está montado"; exit 1; }
OUT="/mnt/midia/llm-ps4/experiments/vulkan-check-$(date +%Y%m%d-%H%M%S)"
[ -e "$OUT" ] && { echo "ABORTADO: $OUT já existe"; exit 1; }
mkdir -p "$OUT" || exit 1

sec() { echo; echo "===== $1 ====="; }
run() { echo "\$ $*"; timeout 20 "$@" 2>&1; echo "[código $?]"; }

{
sec "sistema";        run uname -r; run ldd --version
sec "GPU no PCI";     run sh -c "lspci -nnk | grep -iA3 -E 'vga|display|3d'"
sec "driver kernel";  run sh -c "lsmod | grep -E '^(amdgpu|radeon|drm)'"
sec "/dev/dri";       run ls -l /dev/dri /dev/dri/by-path
sec "grupos";         run id
sec "memória GPU (amdgpu)"
for f in /sys/class/drm/card*/device/mem_info_{vram,gtt,vis_vram}_total; do
  [ -r "$f" ] && echo "$f: $(( $(cat "$f") / 1048576 )) MiB"
done
sec "log do kernel (GPU)"
run sh -c "journalctl -k -b --no-pager 2>/dev/null | grep -iE 'amdgpu|radeon|liverpool|gladius|drm|gpu' | grep -viE 'ether|wlan|mac' | tail -60"
sec "pacotes (pacman -Q, só leitura)"
run sh -c "pacman -Q | grep -iE 'mesa|vulkan|libdrm|shaderc|glslang|spirv|cmake'"
sec "ICDs Vulkan";    run sh -c "ls -l /usr/share/vulkan/icd.d/ /etc/vulkan/icd.d/ 2>&1"
sec "ferramentas";    run sh -c "for t in vulkaninfo glslc glslangValidator cmake gcc g++; do printf '%s: ' \$t; command -v \$t || echo ausente; done"
sec "memória CPU";    run free -h
sec "temperatura";    run sh -c "cat /sys/class/thermal/thermal_zone*/temp 2>/dev/null; sensors 2>/dev/null | head -20"
} > "$OUT/checagem.txt" 2>&1

# vulkaninfo inicializa o driver (só consulta, mas é o único passo que fala com a GPU).
if command -v vulkaninfo >/dev/null; then
  timeout 30 vulkaninfo --summary > "$OUT/vulkaninfo_summary.txt" 2>&1; echo "código $?" >> "$OUT/vulkaninfo_summary.txt"
fi

sha256sum "$OUT"/* > "$OUT/sha256.txt"
echo "Pronto: $OUT"
cat "$OUT/checagem.txt" "$OUT/vulkaninfo_summary.txt" 2>/dev/null
