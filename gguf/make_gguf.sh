#!/usr/bin/env bash
# Reproduz os GGUF do projeto: Qwen3-1.7B (base) e o modelo treinado com GRPO,
# pelo mesmo pipeline e no mesmo commit do llama.cpp usado no PS4.
#
# Saída em $WORK/out/: qwen3-1.7b-{base,gsm8k-grpo}-{F16,Q4_K_M,Q8_0}.gguf,
# chat_template_treinado.jinja e MANIFEST.csv.
#
# Requisitos: git, gcc/g++, python3 (testado com 3.14), ~20 GB livres e o CLI `hf`
# (huggingface_hub) logado (`hf auth login`) com acesso ao repositório do modelo treinado.
#
# Uso:  HF=/caminho/para/hf WORK=./work bash make_gguf.sh
set -euo pipefail

WORK=${WORK:-$PWD/work}
HF=${HF:-hf}
LLAMA_COMMIT=dde879bc4f954b809892fd0d660515f42536394a
BASE_REPO=Qwen/Qwen3-1.7B
BASE_REV=70d244cc86ccca08cf5af4e1e306ecf908b1ad5e
TRAINED_REPO=felipedutrain/qwen3-1.7b-gsm8k-grpo
TRAINED_REV=a29e720349ee301bb987fdff2ea568fa74d931a3

mkdir -p "$WORK" && cd "$WORK"

# 1. llama.cpp no commit fixo; compila só o necessário (sem libcurl).
[ -d llama.cpp ] || git clone https://github.com/ggml-org/llama.cpp llama.cpp
git -C llama.cpp checkout -q "$LLAMA_COMMIT"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -U pip cmake
.venv/bin/pip install -q -r llama.cpp/requirements/requirements-convert_hf_to_gguf.txt
( cd llama.cpp
  ../.venv/bin/cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
  ../.venv/bin/cmake --build build -j --target llama-quantize llama-cli )
QUANT=llama.cpp/build/bin/llama-quantize

# 2. Modelos com revisão fixada. Repita --exclude para cada padrão:
#    `--exclude a b` faria o hf tratar "b" como nome de arquivo.
"$HF" download "$BASE_REPO" --revision "$BASE_REV" --local-dir hf/qwen3-1.7b-base
"$HF" download "$TRAINED_REPO" --revision "$TRAINED_REV" \
    --exclude "lora/*" --exclude "eval/*" --local-dir hf/qwen3-1.7b-gsm8k-grpo

# 3. O checkpoint base guarda lm_head.weight separado (shard 2), embora a config diga
#    tie_word_embeddings=true. Confere que ele é idêntico a embed_tokens e monta uma
#    pasta sem ele, para o GGUF base ter 310 tensores, como o treinado (pesos amarrados).
python3 - <<'EOF'
import json, struct, hashlib, os
d = 'hf/qwen3-1.7b-base/'
assert json.load(open(d + 'config.json'))['tie_word_embeddings'] is True
idx = json.load(open(d + 'model.safetensors.index.json'))['weight_map']
def raw(key):
    with open(d + idx[key], 'rb') as f:
        n = struct.unpack('<Q', f.read(8))[0]; h = json.loads(f.read(n)); m = h[key]
        f.seek(8 + n + m['data_offsets'][0])
        return f.read(m['data_offsets'][1] - m['data_offsets'][0])
assert raw('lm_head.weight') == raw('model.embed_tokens.weight'), 'lm_head != embed_tokens'
os.makedirs('hf-tied/qwen3-1.7b-base', exist_ok=True)
shard_lm = idx['lm_head.weight']
del idx['lm_head.weight']
assert shard_lm not in set(idx.values()), 'o shard do lm_head tem outros tensores'
for f in os.listdir(d):
    if f in (shard_lm, 'model.safetensors.index.json') or f.startswith('.'):
        continue
    dst = f'hf-tied/qwen3-1.7b-base/{f}'
    if not os.path.lexists(dst):
        os.symlink(os.path.abspath(d + f), dst)
j = json.load(open(d + 'model.safetensors.index.json')); j['weight_map'] = idx
json.dump(j, open('hf-tied/qwen3-1.7b-base/model.safetensors.index.json', 'w'), indent=2)
print('lm_head == embed_tokens; pasta hf-tied/qwen3-1.7b-base pronta')
EOF

# 4. Converte para F16 e quantiza (Q4_K_M e Q8_0, sem imatrix), igual para os dois.
#    O nome da pasta de origem vira general.name no GGUF; por isso a pasta "tied"
#    mantém o nome qwen3-1.7b-base.
mkdir -p out
declare -A SRC=([base]=hf-tied/qwen3-1.7b-base [gsm8k-grpo]=hf/qwen3-1.7b-gsm8k-grpo)
for n in base gsm8k-grpo; do
  .venv/bin/python llama.cpp/convert_hf_to_gguf.py "${SRC[$n]}" --outtype f16 \
      --outfile "out/qwen3-1.7b-$n-F16.gguf"
  for q in Q4_K_M Q8_0; do
    "$QUANT" "out/qwen3-1.7b-$n-F16.gguf" "out/qwen3-1.7b-$n-$q.gguf" "$q"
  done
done

# 5. Chat template embutido no GGUF do treinado (usado no PS4 para os dois modelos).
PYTHONPATH=llama.cpp/gguf-py .venv/bin/python - <<'EOF'
from gguf import GGUFReader
r = GGUFReader('out/qwen3-1.7b-gsm8k-grpo-Q4_K_M.gguf')
assert len(r.tensors) == 310
open('out/chat_template_treinado.jinja', 'w').write(r.fields['tokenizer.chat_template'].contents())
EOF

# 6. Manifesto.
{
  echo "arquivo,modelo_origem,revisao,quant,tamanho_bytes,sha256,llama_cpp_commit,data"
  for n in base gsm8k-grpo; do
    if [ "$n" = base ]; then R=$BASE_REPO; S=$BASE_REV; else R=$TRAINED_REPO; S=$TRAINED_REV; fi
    for q in F16 Q4_K_M Q8_0; do
      f=out/qwen3-1.7b-$n-$q.gguf
      echo "$(basename "$f"),$R,$S,$q,$(stat -c %s "$f"),$(sha256sum "$f" | cut -d' ' -f1),$LLAMA_COMMIT,$(date -r "$f" --iso-8601=seconds)"
    done
  done
  f=out/chat_template_treinado.jinja
  echo "$(basename "$f"),$TRAINED_REPO,$TRAINED_REV,chat_template,$(stat -c %s "$f"),$(sha256sum "$f" | cut -d' ' -f1),$LLAMA_COMMIT,$(date -r "$f" --iso-8601=seconds)"
} > out/MANIFEST.csv
column -s, -t out/MANIFEST.csv
