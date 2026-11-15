#!/usr/bin/env bash
# P1 (execução no PS4): onde vai a memória do llama-server com Vulkan e quais opções de carga a reduzem.
# Para cada variante: sobe o servidor com o MESMO modelo (Qwen3-1.7B Q4_K_M, 1,1 GB), espera ficar pronto, mede memória do
# processo (anônima/arquivo), memória de GPU (GTT/VRAM), memória disponível do sistema e a velocidade de uma geração curta.
R=/mnt/midia/llm-ps4; A=$R/assistente; D=$A/medidas/p1_memoria; mkdir -p $D/cache/mesa $D/cache/xdg $D/tmp; M=${1:-$R/models/unsloth/Qwen3-1.7B-GGUF/Qwen3-1.7B-Q4_K_M.gguf}; P=8084
pgrep -x llama-server >/dev/null && { echo "há llama-server rodando"; exit 1; }
disp() { awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo; }
gpu() { echo "$(( $(cat /sys/class/drm/card*/device/mem_info_gtt_used | head -1) / 1048576 )) $(( $(cat /sys/class/drm/card*/device/mem_info_vram_used | head -1) / 1048576 ))"; }
echo "variante | carga_s | disp_antes | disp_depois | consumo | RssAnon | RssFile | GTT | VRAM | tok/s | prompt tok/s" > $D/resultado.txt
run() { nome=$1; shift; sync; sleep 5; m0=$(disp); t0=$(date +%s)
  env VK_DRIVER_FILES=$R/vulkan/mesa-ps4-extract2-20261106-152705/radeon_icd_local.json MESA_SHADER_CACHE_DIR=$D/cache/mesa XDG_CACHE_HOME=$D/cache/xdg TMPDIR=$D/tmp \
    $R/llama.cpp/build-vulkan/bin/llama-server -m "$M" -ngl 99 -c 8192 -t 8 --jinja --host 127.0.0.1 --port $P "$@" > $D/servidor_$nome.log 2>&1 &
  pid=$!; ok=0; for i in $(seq 1 240); do curl -s http://127.0.0.1:$P/health | grep -q '"ok"' && { ok=1; break; }; kill -0 $pid 2>/dev/null || break; sleep 1; done
  [ $ok = 1 ] || { echo "$nome | NÃO SUBIU" >> $D/resultado.txt; kill $pid 2>/dev/null; sleep 3; return; }
  t1=$(date +%s)
  v=$(curl -s http://127.0.0.1:$P/v1/chat/completions -H 'Content-Type: application/json' -d '{"messages":[{"role":"user","content":"Explique em um parágrafo o que é fotossíntese e por que ela é importante para a vida na Terra."}],"max_tokens":120,"temperature":0,"chat_template_kwargs":{"enable_thinking":false}}' | python3 -c "import json,sys; t=json.load(sys.stdin).get('timings',{}); print(round(t.get('predicted_per_second',0),2), round(t.get('prompt_per_second',0),1))")
  m1=$(disp); an=$(awk '/RssAnon/ {print int($2/1024)}' /proc/$pid/status); fi=$(awk '/RssFile/ {print int($2/1024)}' /proc/$pid/status)
  echo "$nome | $(( t1 - t0 )) | $m0 | $m1 | $(( m0 - m1 )) | $an | $fi | $(gpu | tr ' ' '|' | sed 's/|/ | /') | $(echo $v | sed 's/ / | /')" >> $D/resultado.txt
  kill $pid; sleep 6; }
run padrao
run mmap --load-mode mmap
run nohost --no-host
run mmap_nohost --load-mode mmap --no-host
run dio --load-mode dio
run ctx4096_padrao -c 4096
cat $D/resultado.txt
