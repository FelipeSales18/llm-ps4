#!/usr/bin/env bash
# Tarefa 8: vigia do PS4 durante a avaliação. A cada 5 s registra ps4_fan, k10temp, fan1_input, se há ffmpeg e
# se o llama-server existe. Pausa (SIGSTOP) o llama-server com a maior leitura >= 85 C e retoma (SIGCONT) < 75 C;
# cada pausa/retomada vai para vigia_eventos.txt com hora (para marcar as perguntas afetadas). Sai quando $EXP/fim existir.
# Uso: bash vigia_eval.sh <pasta_do_experimento_no_PS4>
set -u
export LC_ALL=C
EXP=$1
LOG="$EXP/temps_vigia.log"; EV="$EXP/vigia_eventos.txt"
PS4H=$(dirname "$(grep -lx ps4_fan /sys/class/hwmon/hwmon*/name | head -1)")
K10H=$(dirname "$(grep -lx k10temp /sys/class/hwmon/hwmon*/name | head -1)")
c() { awk -v m="$1" 'BEGIN{printf "%.1f", m/1000}'; }
date +%s > "$EXP/t0_vigia"
echo "$(date '+%F %T') VIGIA início (pausa >= 85 C, retoma < 75 C)" >> "$EV"
echo "# epoch hora ps4_fan_C k10temp_C fan1 maior_C server ffmpeg estado" > "$LOG"
est=rodando
while [ ! -e "$EXP/fim" ]; do
  tp=$(cat "$PS4H/temp1_input"); tk=$(cat "$K10H/temp1_input"); fan=$(cat "$PS4H/fan1_input" 2>/dev/null || echo NA)
  mx=$(( tp > tk ? tp : tk ))
  srv=$(pgrep -x llama-server | tr '\n' ',' ); srv=${srv%,}
  ff=$(pgrep -c ffmpeg)
  if [ $est = rodando ] && [ $mx -ge 85000 ] && [ -n "$srv" ]; then
    kill -STOP ${srv//,/ } 2>/dev/null; est=pausado
    echo "$(date '+%F %T') $(date +%s) PAUSA maior=$(c $mx) pids=$srv" >> "$EV"
  elif [ $est = pausado ] && [ $mx -lt 75000 ]; then
    p=$(pgrep -x llama-server); [ -n "$p" ] && kill -CONT $p 2>/dev/null; est=rodando
    echo "$(date '+%F %T') $(date +%s) RETOMADA maior=$(c $mx)" >> "$EV"
  fi
  echo "$(date +%s) $(date +%T) $(c $tp) $(c $tk) $fan $(c $mx) ${srv:--} $ff $est" >> "$LOG"
  timeout 5 tail -f /dev/null
done
if [ $est = pausado ]; then p=$(pgrep -x llama-server); [ -n "$p" ] && kill -CONT $p; echo "$(date '+%F %T') $(date +%s) RETOMADA (fim)" >> "$EV"; fi
echo "$(date '+%F %T') VIGIA fim" >> "$EV"
