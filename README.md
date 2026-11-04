# LLM-PS4: a GRPO-tuned Qwen3-1.7B solving math on a PlayStation 4

I fine-tuned Qwen3-1.7B with reinforcement learning (GRPO + LoRA) on GSM8K and ran it locally on a 2013 PlayStation 4 running Linux (8-core AMD Jaguar, no AVX2, 6.8 GiB of usable RAM) with llama.cpp. The goal was shorter, machine-readable answers, because every generated token is expensive on hardware this weak.

**Results at a glance**
- **Format compliance: 2.9% → 75.8%** on the full GSM8K test set (1,319 questions), with **no loss in accuracy** (76.6% → 76.3%, paired McNemar p = 0.81).
- **14% fewer tokens** per answer and half as many truncated answers (Kaggle, full precision).
- **Runs on the PS4** at 9.2 tokens/s, about 17 s per answer, 81/100 correct; after Q4_K_M quantization the results stay within ±2 questions of the full-precision run.
- **What did not work:** accuracy did not improve, and the shorter answers did not translate into a measurable speedup on the PS4 (17.2 s vs 17.4 s per answer). Both results are reported below with the data.

<!-- Demo: add a GIF or screenshot of the PS4 answering a question here -->

- Trained model (merged weights, LoRA adapter, GGUF Q4_K_M / Q8_0): [felipedutrain/qwen3-1.7b-gsm8k-grpo](https://huggingface.co/felipedutrain/qwen3-1.7b-gsm8k-grpo)
- Kaggle notebooks: links will be added later (the executed notebooks are in [`notebooks/`](notebooks/)).

## Results

### GSM8K test set (Kaggle, full 1319 questions)

Greedy decoding, non-thinking mode, at most 320 new tokens, same system prompt for both models:

> Solve the math problem. Reason briefly, step by step. On the last line, write only the final answer as: #### &lt;number&gt;

| Model | Strict | Flexible | Mean tokens | Truncated |
|---|---|---|---|---|
| Qwen3-1.7B (base) | 2.9% | 76.6% | 150 | 3.0% |
| GRPO-tuned | **75.8%** | 76.3% | **129** | **1.4%** |

- **Strict:** the last `#### <number>` matches the reference. **Flexible:** the strict answer if
  present, otherwise the last number in the output. Commas and `$` are ignored.
- Flexible accuracy did not change: paired McNemar test p = 0.81 (79 questions fixed, 83 broken).
- What changed: the format (strict 2.9% → 75.8%), answer length (−14% tokens) and truncations (halved).

### On the PS4 (llama.cpp, Q4_K_M, first 100 test questions)

Server on the PS4, client on the LAN, `temperature 0`, `max_tokens 320`, blocks interleaved
(base 0–49, tuned 0–49, base 50–99, tuned 50–99) with a cool-down before each block.
Both models used the tuned model's chat template.

| | base | tuned |
|---|---|---|
| Strict (format) | 10% | **74%** |
| Flexible | 77% | 81% |
| Tokens per answer (mean) | 128.3 | 126.4 |
| Prompt time per answer | 3.08 s | 3.09 s |
| Generation time per answer | 13.99 s | 13.78 s |
| Generation speed | 9.17 tok/s | 9.17 tok/s |
| Seconds per answer (end to end) | 17.4 | 17.2 |
| Seconds per correct answer | 22.6 | 21.2 |

- **No speed gain:** on these 100 questions the base model was already about as short as the tuned one
  (128 vs 126 tokens), so both take ~17 s per answer.
- **Matches Kaggle:** flexible accuracy is within ±2 questions of the Kaggle run on the same 100
  questions (base 77 vs 79, tuned 81 vs 79). The outputs are not identical (different runtime and
  quantization), but the verdict per question agrees on 88 of 100 for both models.
- The 81 vs 77 gap on 100 questions (11 fixed, 7 broken) is within noise.
- Files: [`ps4/results/ps4_eval_20261103_2112_resumo.md`](ps4/results/ps4_eval_20261103_2112_resumo.md)
  and the per-question CSV next to it.

### Token limit (simulated from the Kaggle outputs)

Because decoding is greedy, an answer with a lower limit is identical up to the cut. Simulating
limits of 160 / 200 / 256 / 320 on the full test set, **320 stays the best choice**: even 256 costs
1.4 points of flexible accuracy for the tuned model while saving only ~1.4 tokens per answer, and
the time per *correct* answer gets worse at every lower limit. See
[`analise/limite_tokens.md`](analise/limite_tokens.md) (in Portuguese).

### Error analysis (tuned model, Kaggle outputs)

Full report (in Portuguese): [`analise/relatorio.md`](analise/relatorio.md).

- **Wasted tokens are already low:** nothing after the final `####`, and ~18 tokens per answer
  (~14%) go to text without arithmetic, restated data or formatting (vs ~38 / ~26% for the base).
- **One clear failure mode:** when the model reaches an impossible value (negative age, fractional
  points) it writes "let's recheck" and redoes the *same* algebra until the limit. 9 answers (0.7%),
  ~300 tokens each, 0% correct.
- **Most errors are understanding errors:** in a random sample of 40 wrong answers, 17 misread the
  problem, 15 had wrong reasoning, 4 arithmetic slips, 1 truncation, 1 extraction issue (right
  answer in cents) and 2 debatable reference answers.
- Errors are not systematic: most are misreadings or reasoning mistakes that vary from question to question. The recheck loop is better handled at decoding time (e.g. a repetition penalty) than by retraining.

## Hardware and software

| | |
|---|---|
| Device | PlayStation 4, AMD Jaguar APU, 8 cores @ ~1.6 GHz, AVX + F16C, **no AVX2/FMA** |
| Memory | 8 GB GDDR5, 1 GB reserved as VRAM → 6.8 GiB for the CPU, zram swap |
| OS | CachyOS (Arch-based) on an external USB drive, PS4-specific kernel |
| Inference | llama.cpp commit [`dde879bc`](https://github.com/ggml-org/llama.cpp/commit/dde879bc4f954b809892fd0d660515f42536394a), CPU only, 8 threads, `-c 4096` |
| Training | Kaggle, 1× Tesla T4, unsloth + TRL GRPO, LoRA r = 16, 357 steps (~6 h) |

Inventory of the PS4 setup (in Portuguese): [`ps4/INVENTARIO.md`](ps4/INVENTARIO.md).
This repository does not cover how to install Linux on the PS4.

## Repository layout

```
notebooks/   executed Kaggle notebooks: 0.6B pilot and the 1.7B GRPO run (with outputs)
gguf/        make_gguf.sh (exact conversion pipeline), MANIFEST.csv, chat template
ps4/         PS4 inventory, build/benchmark scripts and all PS4 results
eval-ps4/    run_eval.py (PS4 measurement), grading.py, resumo.py and the summary
analise/     error analysis and token-limit scripts and reports (Portuguese)
```

## How to reproduce

### 1. Training (Kaggle)

Open `notebooks/grpo_qwen3_1.7b_gsm8k.ipynb` on Kaggle with **GPU T4 ×2**, Internet on, and a
secret `HF_TOKEN` (Add-ons → Secrets). The notebook evaluates the base model, trains, evaluates
again on the full test set and uploads the merged model, LoRA adapter and per-question outputs
(`eval/`) to Hugging Face. Change the repository name before running. The 0.6B notebook is the
pilot that validated the pipeline.

### 2. GGUF conversion (any Linux x86-64)

```bash
hf auth login                      # needs read access to the model repo
HF=$(command -v hf) WORK=./work bash gguf/make_gguf.sh
```

The script pins llama.cpp `dde879bc` and both model revisions, converts to F16, drops the base
checkpoint's duplicated `lm_head` (after checking it is byte-identical to the tied embeddings, so
both GGUFs have the same 310 tensors), quantizes to Q4_K_M and Q8_0 without imatrix, extracts the
chat template and writes `MANIFEST.csv`. Compare the SHA-256 values with [`gguf/MANIFEST.csv`](gguf/MANIFEST.csv).

### 3. llama.cpp on the PS4

```bash
git clone https://github.com/ggml-org/llama.cpp && cd llama.cpp
git checkout dde879bc4f954b809892fd0d660515f42536394a
cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF
cmake --build build -j 6 --target llama-bench llama-cli llama-server   # ~17 min on the Jaguar
```

`ps4/scripts/build.sh` and `ps4/scripts/bench1.sh` are the exact scripts used (paths under `/mnt/midia/llm-ps4`).

### 4. PS4 measurement

On the PS4, create an API key (`openssl rand -hex 32 > ~/.config/llm-ps4/api-key; chmod 600 …`).
On the client, set up an `ssh ps4` alias, build `eval-ps4/questions.jsonl` from the published
evaluation file, then run the measurement:

```bash
hf download felipedutrain/qwen3-1.7b-gsm8k-grpo eval/eval_base.csv eval/eval_grpo.csv --local-dir eval-ps4/hf
python3 - <<'EOF'
import csv, json
rows = [r for r in csv.DictReader(open('eval-ps4/hf/eval/eval_base.csv')) if int(r['idx']) < 100]
with open('eval-ps4/questions.jsonl', 'w') as f:
    for r in rows:
        f.write(json.dumps({'idx': int(r['idx']), 'question': r['question'], 'gold': r['gold']}) + '\n')
EOF
PS4_HOST=<PS4_IP> python3 eval-ps4/run_eval.py      # ~70 min
python3 eval-ps4/resumo.py eval-ps4/ps4_eval_<stamp>.csv
```

`run_eval.py` starts `llama-server` in tmux on the PS4 (one model at a time, port 8081), rests the
PS4 for 5 minutes, waits for the APU temperature to return to rest + 3 °C before each block (at most
5 minutes), and records llama.cpp's own prompt/generation timings per answer.
`grading.py` reproduces the notebook's strict/flexible grading exactly (0 disagreements on all
2638 Kaggle outputs).

### 5. Analysis

Put `eval_base.csv` and `eval_grpo.csv` in `analise/eval/`, then run `limite.py` (token limits),
`analisa.py` and `extra.py` (statistics) and `gera_relatorio.py` (report). `analisa.py` and `extra.py`
count tokens with the tuned model's `tokenizer.json`; adjust the path at the top of each script.

## What I learned

- **Estimates are not measurements.** The Kaggle numbers suggested ~2.4 s saved per answer on the PS4; measuring found 0.24 s, because on those questions the base model already answered briefly.
- **Same pipeline, or it is not a comparison.** The base checkpoint stores a duplicated `lm_head`; converted as-is, its Q4_K_M GGUF was 16% larger (18% for F16 and Q8_0), which alone would likely have made it slower on a memory-bound CPU.
- **Chat templates change behavior.** Just switching to the tuned model's template raised the base model's format compliance from 3% to 10%.
- **Greedy decoding makes some experiments free.** Token limits can be simulated from existing outputs without running the model again.
- **On the Jaguar, generation is memory-bound.** Going from 4 to 8 threads made prompt processing 1.8× faster but generation only 1.4× faster (Qwen3-1.7B Q4_K_M; 1.6× for Qwen3-0.6B).
- **A format reward works fast; accuracy is harder.** In one run (one seed, ~1,400 training prompts), GRPO fixed the format but did not change accuracy.

## Limitations

- One training run with one seed. The flexible accuracy difference on Kaggle is not significant.
- The PS4 measurement covers only 100 questions; differences of a few questions are noise.
- On the PS4 both models used the tuned model's chat template (to keep the prompt identical);
  this helped the base model's format (strict 3% on Kaggle → 10% on the PS4).
- The PS4 runs a Q4_K_M quantization in llama.cpp, while Kaggle evaluated the full-precision model
  in PyTorch, so outputs differ token by token.
- Temperature control is approximate: the PS4 heats up to ~76 °C within a block, and one block
  started 0.75 °C above its target. Generation speed was the same in every block (9.16–9.19 tok/s).
- The error classification of the 40 sampled answers is manual and partly subjective.
- GSM8K only, English only, greedy decoding, CPU only (no GPU/Vulkan offload was tested).

## License

Code and documentation in this repository: [MIT](LICENSE), © 2026 Felipe Dutrain de Sales.

Third-party material keeps its own license:
- **Qwen3** model weights (and any derivative weights, such as the GGUF files and the tuned model)
  are under the **Apache License 2.0**.
- The **GSM8K** dataset (questions and reference answers that appear in the evaluation outputs) is
  under the **MIT License**.
