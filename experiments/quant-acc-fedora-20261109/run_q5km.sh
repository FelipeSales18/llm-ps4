#!/usr/bin/env bash
# Tarefa 11: braço Q5_K_M completo (retoma do que já está em resultados_q5km.csv), mesmo pipeline do Q4_K_M.
# Amostrador do packagekitd preso ao processo do cliente (encerra junto com ele).
cd "$(dirname "$0")" || exit 1
echo "$(date '+%F %T') packagekitd ao iniciar: $(ps -C packagekitd -o pcpu= 2>/dev/null | tr -d ' ' | sed 's/^$/não está rodando/;s/^[0-9]/rodando, CPU% &/')" >> resultados_q5km.log
PYTHONDONTWRITEBYTECODE=1 systemd-inhibit --what=sleep:idle --who=quant-acc --why='GSM8K Q5_K_M (tarefa 11)' \
  python3 -u run_quant.py --braco q5km --ini 0 --fim 1319 &
C=$!
while kill -0 "$C" 2>/dev/null; do
  echo "$(date '+%F %T') packagekitd: $(ps -C packagekitd -o pcpu= 2>/dev/null | tr -d ' ')" >> packagekitd_cpu_q5km.log
  timeout 60 tail --pid="$C" -f /dev/null
done
wait "$C"; echo "$(date '+%F %T') cliente terminou com código $?" >> resultados_q5km.log
