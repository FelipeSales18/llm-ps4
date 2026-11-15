#!/usr/bin/env bash
# Roda NO NOTEBOOK: espera o disco do PS4 montar (fsck após o reinício), envia os scripts novos e religa vigia e fila do console.
A=$HOME/LLM-PS4/assistente; R=/mnt/midia/llm-ps4
until ssh -o ConnectTimeout=10 -o BatchMode=yes ps4 "test -d $R/assistente/modelos" 2>/dev/null; do sleep 60; done
echo "$(date +%T) disco montado"; cd $A
tar czf - aval/roda.py aval/verifica.py aval/resume.py runtime ps4 configs | ssh ps4 "tar xzf - -C $R/assistente" || exit 1
ssh ps4 bash -s <<'FIM'
R=/mnt/midia/llm-ps4; A=$R/assistente; Q=$R/experiments/wedit-fila-ps4; M=$A/modelos
rm -f $M/*.parcial $Q/PARAR $A/medidas/parar_vigia
cat > $Q/fila_ps4.txt <<TXT
# 13/11 14:20, após o 2º reinício. GPU só com a arquitetura Qwen3-1.7B (estável), em blocos; arquiteturas novas só em CPU.
MODO=gpu bash $A/ps4/mede_modelo3.sh g2_qwen3_17b_orig $R/models/unsloth/Qwen3-1.7B-GGUF/Qwen3-1.7B-Q4_K_M.gguf configs/base0.json dev 0 8192 --load-mode mmap > $A/medidas/g2_qwen3_17b_orig.out 2>&1
MODO=cpu bash $A/ps4/mede_modelo3.sh c_qwen3_17b_orig $R/models/unsloth/Qwen3-1.7B-GGUF/Qwen3-1.7B-Q4_K_M.gguf configs/base0.json dev 4 8192 --load-mode mmap > $A/medidas/c_qwen3_17b_orig.out 2>&1
MODO=cpu bash $A/ps4/mede_modelo3.sh c_qwen35_4b $M/Qwen3.5-4B-Q4_K_M.gguf configs/base0.json dev 4 8192 --load-mode mmap > $A/medidas/c_qwen35_4b.out 2>&1
TXT
: > $Q/fila_ps4_feitos.txt
sed -i 's/ -c 8192 -t 8 --jinja --host/ -c 8192 -t 8 --jinja --cache-ram 256 -np 1 --host/' $A/ps4/testa_memoria.sh
tmux new -d -s vigia_assistente "bash $A/ps4/vigia_termico2.sh"; tmux new -d -s weditfila "bash $Q/fila_ps4.sh"; sleep 5; tmux ls; tail -2 $Q/fila_ps4.log; ls $M
FIM
echo "$(date +%T) PS4 preparado"
