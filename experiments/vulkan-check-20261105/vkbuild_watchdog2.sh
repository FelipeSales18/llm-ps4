#!/usr/bin/env bash
# Tarefa 5b, vigia v2. A cada 10 s lê ps4_fan (temp1_input, fan1_input) e k10temp (temp1_input) e grava em temps2.log.
# Pausa/retoma SÓ os processos filhos do build (nunca o bash do painel do tmux: se ele parar, o tmux manda SIGCONT ao grupo).
#  - estado inicial: build pausado; retoma (kill -CONT) assim que a maior leitura estiver < 75 C (retomada autorizada).
#  - maior leitura >= 85 C: pausa; retoma quando < 75 C.
#  - acima de 80 C subindo mais de 1 C em 60 s: pausa, registra PAUSA_TAXA e sai (não retoma sozinho).
#  - registra a primeira vez que passar de 78 C (observação da ventoinha).
# Uso: bash vkbuild_watchdog2.sh <pasta_do_experimento> <sid_do_build>
set -u
export LC_ALL=C
E=$1; SID=$2
LOG="$E/temps2.log"; ST="$E/status.txt"
PS4H=$(dirname "$(grep -lx ps4_fan /sys/class/hwmon/hwmon*/name | head -1)")
K10H=$(dirname "$(grep -lx k10temp /sys/class/hwmon/hwmon*/name | head -1)")
[ -r "$PS4H/temp1_input" ] && [ -r "$K10H/temp1_input" ] || { echo "VIGIA2_ERRO $(date '+%F %T') sensores não encontrados" >> "$ST"; exit 1; }

filhos()   { ps -o pid= --sid "$SID" | tr -d ' ' | grep -vx "$SID"; }
parar()    { local r P; for r in 1 2 3; do P=$(filhos); [ -n "$P" ] && kill -STOP $P 2>/dev/null; done; }
seguir()   { local P; P=$(filhos); [ -n "$P" ] && kill -CONT $P 2>/dev/null; }
ativos()   { ps -o pid=,stat= --sid "$SID" | awk -v s="$SID" '$1!=s && $2!~/^[TZ]/' | wc -l; }
c()        { awk -v m="$1" 'BEGIN{printf "%.1f", m/1000}'; }

echo "VIGIA2 início $(date '+%F %T') sid=$SID ps4_fan=$PS4H k10temp=$K10H (pausa>=85, retoma<75, taxa>1C/min acima de 80)" >> "$ST"
echo "# hora ps4_fan_C k10temp_C fan1_input maior_C estado" >> "$LOG"
estado=pausado; n=0; cruzou=0; hist=()
while ! grep -q '^FIM' "$ST" 2>/dev/null; do
  tp=$(cat "$PS4H/temp1_input"); tk=$(cat "$K10H/temp1_input"); fan=$(cat "$PS4H/fan1_input" 2>/dev/null || echo NA)
  mx=$(( tp > tk ? tp : tk ))
  hist+=("$mx"); [ ${#hist[@]} -gt 7 ] && hist=("${hist[@]:1}")
  if [ $cruzou = 0 ] && [ $mx -gt 78000 ]; then
    cruzou=1; echo "CRUZOU_78 $(date '+%F %T') ps4_fan=$(c $tp) k10temp=$(c $tk) fan1=$fan" >> "$ST"
  fi
  if [ "$estado" = rodando ]; then
    if [ $mx -ge 85000 ]; then
      parar; estado=pausado; n=$((n+1))
      echo "PAUSA_85 #$n $(date '+%F %T') maior=$(c $mx) fan1=$fan ativos_restantes=$(ativos)" >> "$ST"
    elif [ $mx -gt 80000 ] && [ ${#hist[@]} -eq 7 ] && [ $(( mx - hist[0] )) -gt 1000 ]; then
      parar; n=$((n+1))
      echo "PAUSA_TAXA #$n $(date '+%F %T') maior=$(c $mx) subiu $(c $(( mx - hist[0] ))) C em 60 s, fan1=$fan ativos_restantes=$(ativos) — vigia saiu, aguardando autorização" >> "$ST"
      echo "$(date +%T) $(c $tp) $(c $tk) $fan $(c $mx) PAUSA_TAXA" >> "$LOG"
      exit 0
    fi
  elif [ $mx -lt 75000 ]; then
    seguir; estado=rodando
    echo "RETOMADA $(date '+%F %T') maior=$(c $mx) fan1=$fan" >> "$ST"
  fi
  echo "$(date +%T) $(c $tp) $(c $tk) $fan $(c $mx) $estado" >> "$LOG"
  timeout 10 tail -f /dev/null
done
echo "VIGIA2 fim $(date '+%F %T') pausas=$n máxima=$(awk '!/^#/ && NF>=5 {if($5>m)m=$5} END{print m}' "$LOG") C" >> "$ST"
