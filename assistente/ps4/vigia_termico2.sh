#!/usr/bin/env bash
# Proteção térmica das medições do assistente no PS4 (mesma política do vigia das rodadas anteriores do projeto):
# a cada 10 s lê ps4_fan e k10temp; com a maior leitura >= 85 °C pausa (SIGSTOP) todo llama-server; retoma (SIGCONT) abaixo de 75 °C.
# Registra temperaturas e eventos (com epoch, para marcar respostas afetadas). Encerra quando existir o arquivo parar_vigia.
set -u; export LC_ALL=C
D=/mnt/midia/llm-ps4/assistente/medidas; LOG=$D/temps_vigia.log; EV=$D/vigia_eventos.txt
PS4H=$(dirname "$(grep -lx ps4_fan /sys/class/hwmon/hwmon*/name | head -1)"); K10H=$(dirname "$(grep -lx k10temp /sys/class/hwmon/hwmon*/name | head -1)")
c() { awk -v m="$1" 'BEGIN{printf "%.1f", m/1000}'; }
echo "$(date '+%F %T') $(date +%s) VIGIA início (10 s; pausa >= 85 C, retoma < 75 C)" >> "$EV"; est=rodando
while [ ! -e "$D/parar_vigia" ]; do
  tp=$(cat "$PS4H/temp1_input"); tk=$(cat "$K10H/temp1_input"); mx=$(( tp > tk ? tp : tk )); n=$(pgrep -xc llama-server)
  if [ $est = rodando ] && [ $mx -ge 85000 ] && [ "$n" -gt 0 ]; then pkill -STOP -x llama-server; est=pausado; echo "$(date '+%F %T') $(date +%s) PAUSA maior=$(c $mx)" >> "$EV"
  elif [ $est = pausado ] && [ $mx -lt 75000 ]; then pkill -CONT -x llama-server; est=rodando; echo "$(date '+%F %T') $(date +%s) RETOMADA maior=$(c $mx)" >> "$EV"; fi
  md=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
  # guarda de memória: com menos de 150 MB disponíveis, encerra o llama-server da medição para o console não travar
  if [ "$n" -gt 0 ] && [ "$md" -lt 150 ]; then pkill -TERM -x llama-server; echo "$(date '+%F %T') $(date +%s) MEMORIA_BAIXA disponivel=${md}MB: llama-server encerrado" >> "$EV"; fi
  echo "$(date +%s) $(date +%T) $(c $tp) $(c $tk) $(c $mx) $n $est mem_disp=${md}MB" >> "$LOG"
  sleep 10
done
[ $est = pausado ] && pkill -CONT -x llama-server; echo "$(date '+%F %T') $(date +%s) VIGIA fim" >> "$EV"
