#!/usr/bin/env bash
# Tarefa 5b: vigia de temperatura. A cada 15 s registra a máxima; se passar de 75 C, pausa (SIGSTOP) o grupo
# de processos do build e sai. Não retoma sozinho: retomar exige autorização (kill -CONT -- -<pgid>).
# Uso: bash vkbuild_watchdog.sh <pasta_do_experimento>
set -u
export LC_ALL=C
E=$1
LIM=75
maxtemp() { sensors 2>/dev/null | awk '/^temp[0-9]+:/{v=$2; gsub(/[^0-9.]/,"",v); v+=0; if(v>m)m=v} END{print m+0}'; }
echo "VIGIA início $(date '+%F %T')" >> "$E/temps.log"
# espera o build registrar o pgid
n=0; while [ ! -s "$E/build.pgid" ] && [ $n -lt 30 ]; do timeout 1 tail -f /dev/null; n=$((n+1)); done
PG=$(cat "$E/build.pgid" 2>/dev/null) || { echo "VIGIA: sem pgid, saindo" >> "$E/temps.log"; exit 1; }
while ! grep -q '^FIM' "$E/status.txt" 2>/dev/null; do
  T=$(maxtemp)
  echo "$(date '+%T') $T" >> "$E/temps.log"
  if awk -v t="$T" -v l=$LIM 'BEGIN{exit !(t>l)}'; then
    kill -STOP -- "-$PG"
    echo "PAUSADO $(date '+%F %T') temp=$T C pgid=$PG (retomar: kill -CONT -- -$PG)" >> "$E/status.txt"
    echo "PAUSADO por temperatura: $T C"
    exit 0
  fi
  timeout 15 tail -f /dev/null
done
echo "VIGIA fim $(date '+%F %T') máxima registrada: $(awk 'NF==2{if($2>m)m=$2} END{print m}' "$E/temps.log") C" >> "$E/temps.log"
