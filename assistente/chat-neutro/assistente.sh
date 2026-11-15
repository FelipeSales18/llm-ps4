#!/usr/bin/env bash
# Abre o assistente local no terminal. Sobe o servidor (tmux "chat-neutro") se ele não estiver no ar.
# Criado em 15/11/2026; para remover: rm ~/.local/bin/assistente
B=/mnt/midia/llm-ps4; D=$B/assistente/chat-neutro; URL=http://127.0.0.1:8081
export TMUX_TMPDIR=$B/chat-gpu/tmux
if ! curl -sf -m 3 $URL/health >/dev/null; then
  echo "Iniciando o servidor (uns 20 s)..."
  tmux kill-session -t chat-neutro 2>/dev/null
  tmux new -d -s chat-neutro "$(cat $D/comando.txt) 2>&1 | tee $B/chat-gpu/logs/llama-server_chat_neutro_$(date +%Y%m%d_%H%M).log"
  for i in $(seq 60); do curl -sf -m 3 $URL/health >/dev/null && break; sleep 2; done
  curl -sf -m 3 $URL/health >/dev/null || { echo "O servidor não subiu. Veja: tmux attach -t chat-neutro"; exit 1; }
fi
echo "Também no navegador de outro aparelho: http://$(ip -4 route get 1 2>/dev/null | sed -n "s/.*src \([0-9.]*\).*/\1/p"):8081"
exec python3 $B/assistente/runtime/conversar.py --config $D/config.json --url $URL --chave "$(cat /home/ps4/.config/llm-ps4/api-key)" "$@"
