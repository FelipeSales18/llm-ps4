#!/usr/bin/env bash
# Sobe um llama-server local (notebook, CPU) para desenvolvimento. Uso: aval/servidor.sh <modelo.gguf> [porta=8090] [slots=4] [ctx_por_slot=8192] [opções extras...]
# Para parar: kill $(cat $HOME/LLM-PS4/assistente/logs/servidor_<porta>.pid)
M=$1; P=${2:-8090}; N=${3:-4}; C=${4:-8192}; shift 4 2>/dev/null || shift $#
L=$HOME/LLM-PS4/assistente/logs
nohup $HOME/LLM-PS4/gguf/llama.cpp/build-server/bin/llama-server -m "$M" --host 127.0.0.1 --port "$P" -np "$N" -c $((C * N)) -t 4 -ngl 0 --jinja --cache-ram 512 "$@" > "$L/servidor_$P.log" 2>&1 &
echo $! > "$L/servidor_$P.pid"
for i in $(seq 1 120); do curl -s "http://127.0.0.1:$P/health" | grep -q '"ok"' && { echo "servidor pronto na porta $P (pid $(cat $L/servidor_$P.pid))"; exit 0; }; sleep 1; done
echo "servidor NÃO ficou pronto; ver $L/servidor_$P.log"; tail -5 "$L/servidor_$P.log"; exit 1
