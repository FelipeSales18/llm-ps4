#!/usr/bin/env bash
# Tarefa 10: vigia da rodada GSM8K completa. A cada 10 s registra ps4_fan, k10temp, fan1_input e ffmpeg em temps_vigia.log.
# Pausa (SIGSTOP) só o servidor da avaliação (pid em servidor.pid) com a maior leitura >= 85 C e retoma (SIGCONT) < 75 C.
# Eventos com epoch em vigia_eventos.txt (o cliente usa para marcar tempo_valido). Sai quando existir parar_vigia.
# Uso: bash vigia_full.sh <pasta_do_experimento>
set -u
export LC_ALL=C
EXP=$1
LOG="$EXP/temps_vigia.log"; EV="$EXP/vigia_eventos.txt"
PS4H=$(dirname "$(grep -lx ps4_fan /sys/class/hwmon/hwmon*/name | head -1)")
K10H=$(dirname "$(grep -lx k10temp /sys/class/hwmon/hwmon*/name | head -1)")
c() { awk -v m="$1" 'BEGIN{printf "%.1f", m/1000}'; }
echo "$(date '+%F %T') $(date +%s) VIGIA início (10 s; pausa >= 85 C, retoma < 75 C)" >> "$EV"
[ -s "$LOG" ] || echo "# epoch hora ps4_fan_C k10temp_C fan1 maior_C servidor ffmpeg estado" > "$LOG"
est=rodando; pausado_pid=""
while [ ! -e "$EXP/parar_vigia" ]; do
  tp=$(cat "$PS4H/temp1_input"); tk=$(cat "$K10H/temp1_input"); fan=$(cat "$PS4H/fan1_input" 2>/dev/null || echo NA)
  mx=$(( tp > tk ? tp : tk ))
  pid=$(cat "$EXP/servidor.pid" 2>/dev/null); [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null && pid=""
  ff=$(pgrep -c ffmpeg)
  if [ $est = rodando ] && [ $mx -ge 85000 ] && [ -n "$pid" ]; then
    kill -STOP "$pid"; est=pausado; pausado_pid=$pid
    echo "$(date '+%F %T') $(date +%s) PAUSA maior=$(c $mx) pid=$pid" >> "$EV"
  elif [ $est = pausado ] && [ $mx -lt 75000 ]; then
    kill -CONT "$pausado_pid" 2>/dev/null; est=rodando
    echo "$(date '+%F %T') $(date +%s) RETOMADA maior=$(c $mx)" >> "$EV"
  fi
  echo "$(date +%s) $(date +%T) $(c $tp) $(c $tk) $fan $(c $mx) ${pid:--} $ff $est" >> "$LOG"
  timeout 10 tail -f /dev/null
done
if [ $est = pausado ]; then kill -CONT "$pausado_pid" 2>/dev/null; echo "$(date '+%F %T') $(date +%s) RETOMADA_FIM" >> "$EV"; fi
echo "$(date '+%F %T') $(date +%s) VIGIA fim" >> "$EV"
