#!/usr/bin/env bash
# Copia para o PS4, um por vez, os GGUF do comparativo assim que cada download termina (manifesto local). Cópia para .parcial e mv no fim.
A=$HOME/LLM-PS4/assistente; D=/mnt/midia/llm-ps4/assistente/modelos
for n in qwen3.5-2b-q4km qwen3.5-4b-q4km minicpm5-2b-q4km granite-4.2-3b-q4km gemma-4-e2b-q4km; do
  until python3 -c "import json,sys; sys.exit(0 if '$n' in json.load(open('$A/modelos/MANIFEST.json')) else 1)" 2>/dev/null; do
    pgrep -f "modelos/baixa.py" >/dev/null || { echo "$(date +%T) $n: download não está no manifesto e o baixador parou"; continue 2; }; sleep 30; done
  f=$(python3 -c "import json; print(json.load(open('$A/modelos/MANIFEST.json'))['$n']['caminho'])"); b=$(basename "$f")
  ssh -o ConnectTimeout=20 ps4 "test -s $D/$b" && { echo "$(date +%T) $b já está no PS4"; continue; }
  scp -q "$A/modelos/$f" ps4:$D/$b.parcial && ssh ps4 "mv $D/$b.parcial $D/$b; sha256sum $D/$b | cut -c1-16" && echo "$(date +%T) $b copiado"
done; echo "$(date +%T) fim das cópias"
