# LLM-PS4: a GRPO-tuned Qwen3-1.7B solving math on a PlayStation 4

I fine-tuned Qwen3-1.7B with GRPO (LoRA) on GSM8K to answer in a fixed, machine-readable format, and ran it on a 2013 PlayStation 4 running Linux with llama.cpp, first on the CPU and then on the console's GPU through Vulkan.

**Summary**
- **GRPO taught the format without costing accuracy.** On the full GSM8K test set (n = 1,319, full precision), the tuned model ends in the requested `#### <number>` format 75.8% of the time, against 67.1% and 71.3% for the base model with the best prompts tested (instruction, 2-shot; McNemar p < 0.001 for both), while flexible accuracy stays the same (76.3% vs 76.6% for the base, p = 0.81).
- **The 4-bit model runs 1.56× faster on the PS4 GPU than on the PS4 CPU:** 11.2 s vs 17.5 s per answer on the same 100 questions, with no significant accuracy difference (flexible 77 vs 81, p = 0.29). On all 1,319 questions the GPU scores exactly like the same Q4_K_M file on an x86 CPU (72.9% vs 72.9%, p = 1.0).
- **4-bit quantization costs about 3.4 points** of flexible accuracy against the full-precision model (Q4_K_M: −3.3 on the PS4 GPU and −3.4 on a laptop CPU, both p = 0.003, n = 1,319), and it hurts the format more than the answers.

Model card: [felipedutrain/qwen3-1.7b-gsm8k-grpo](https://huggingface.co/felipedutrain/qwen3-1.7b-gsm8k-grpo) (the link works once the model is public).

## Results

Unless stated otherwise: greedy decoding, non-thinking mode, at most 320 new tokens, and this system prompt:

> Solve the math problem. Reason briefly, step by step. On the last line, write only the final answer as: #### &lt;number&gt;

**Strict** = the last `#### <number>` matches the reference. **Flexible** = the strict answer if present, otherwise the last number in the output (commas and `$` ignored). All comparisons are paired on the same questions; p-values are exact McNemar tests, and intervals are 95% (Wilson for accuracies, Newcombe for paired differences).

### 1. Base vs tuned, full GSM8K test (Kaggle, full precision, n = 1,319)

| Model | Strict | Flexible (95% CI) | Mean tokens | Truncated |
|---|---|---|---|---|
| Qwen3-1.7B (base) | 2.9% | 76.6% (74.2–78.8) | 149.6 | 40 (3.0%) |
| GRPO-tuned | **75.8%** | 76.3% (73.9–78.5) | **129.2** | **19 (1.4%)** |

- Flexible: 79 questions fixed and 83 broken, p = 0.81. Accuracy did not change.
- Strict: 963 fixed and 1 broken, p < 10⁻²⁰⁰. The format was learned.

### 2. Prompt baselines (base model, Kaggle, full precision, n = 1,319)

The fair comparison for the format is not the weak prompt above but the best prompts for the base model. System prompt for these runs: *"Solve the math problem step by step. Be concise. On the last line, write only the final answer in the format: #### &lt;number&gt;"*. The 2-shot prompt uses training questions 0 and 1. The tuned model was regraded with the same grader as the baselines.

| | Strict (95% CI) | Flexible (95% CI) | Tokens per answer | Prompt tokens |
|---|---|---|---|---|
| GRPO-tuned (regraded) | **75.7%** | **76.2%** | 129 | — |
| Base + instruction | 67.1% (64.5–69.6) | 75.2% (72.8–77.5) | 127.8 | 108 |
| Base + 2-shot | 71.3% (68.8–73.6) | 72.0% (69.5–74.4) | 89.4 | 282 |

- **Format:** the tuned model beats both prompts: +8.6 points vs instruction (186 vs 73 discordant questions, p < 0.0001) and +4.4 vs 2-shot (158 vs 100, p = 0.0004).
- **Accuracy:** tied with the instruction prompt (96 vs 83, p = 0.37). The 2-shot prompt shortens answers by 30% but loses 4.2 points of flexible accuracy (153 vs 98, p = 0.0006).

### 3. PS4: GPU vs CPU (Q4_K_M, first 100 test questions)

Same model file, same client, same options. Only the `llama-server` binary changes (Vulkan build with `-ngl 99` vs the original CPU build). The blocks were interleaved (GPU 0–49, CPU 0–49, GPU 50–99, CPU 50–99), each started after a cool-down.

| | GPU (Vulkan) | CPU (8 threads) | GPU/CPU |
|---|---|---|---|
| Strict | 70/100 | 74/100 | |
| Flexible | 77/100 | 81/100 | |
| Tokens per answer (mean) | 125.3 | 126.4 | |
| Prompt time per answer | 0.47 s | 3.12 s | 0.15 |
| Generation time per answer | 10.50 s | 14.15 s | 0.74 |
| Generation speed | 11.93 tok/s | 8.93 tok/s | 1.34 |
| **Seconds per answer** | **11.18** | **17.47** | **0.64 (1.56× faster)** |
| Seconds per correct answer (flexible) | 14.52 | 21.57 | |

- **Accuracy is statistically the same:** flexible 2 vs 6 discordant questions (p = 0.29), strict 3 vs 7 (p = 0.34), same verdict on 92/100. Only 27/100 outputs are identical, because the two backends round differently.
- **The CPU arm is reproducible:** its 100 outputs were identical, word for word, to a CPU run three days earlier.
- **Synthetic benchmark** (`llama-bench`, 2 rounds × 3 repetitions per arm): prompt processing 169.7 ± 0.2 vs 25.8 ± 0.1 tok/s (6.6×), generation 12.5 ± 0.0 vs 9.6 ± 0.1 tok/s (1.3×). The GPU helps the prompt much more than generation.

### 4. Full test set and quantization (n = 1,319)

| Configuration | Flexible (95% CI) | Strict (95% CI) | Tokens | Truncated | Seconds per answer |
|---|---|---|---|---|---|
| Kaggle, full precision (PyTorch) | **76.3%** (73.9–78.5) | **75.8%** | 129.2 | 19 | — |
| Q5_K_M, laptop CPU | 74.8% (72.3–77.0) | 57.6% (54.9–60.3) | 135.0 | 25 | 7.28 (laptop) |
| Q4_K_M, laptop CPU | 72.9% (70.4–75.2) | 63.2% (60.5–65.7) | 132.2 | 17 | 6.67 (laptop) |
| Q4_K_M, **PS4 GPU** | 72.9% (70.5–75.3) | 66.8% (64.2–69.3) | 131.2 | 24 | **11.57 (PS4)** |

The laptop is an Intel i5-10300H running the same llama.cpp commit on the CPU (4 threads). It was used only to separate quantization from backend, and its times are not PS4 measurements.

Paired comparisons (all n = 1,319):

| Comparison | Δ flexible (95% CI) | McNemar flexible | Δ strict (95% CI) | McNemar strict |
|---|---|---|---|---|
| PS4 GPU Q4_K_M − Kaggle | −3.3 (−5.5 to −1.2) | 86 vs 130, p = 0.003 | −9.0 (−11.4 to −6.6) | 78 vs 197, p < 0.001 |
| Laptop Q4_K_M − Kaggle | −3.4 (−5.6 to −1.2) | 85 vs 130, p = 0.003 | −12.7 (−15.2 to −10.1) | 79 vs 246, p < 0.001 |
| Laptop Q4_K_M − PS4 GPU Q4_K_M | **−0.1 (−1.8 to +1.7)** | 67 vs 68, **p = 1.0** | −3.6 (−5.8 to −1.5) | 80 vs 128, p = 0.001 |
| Q5_K_M − Kaggle | −1.5 (−3.5 to +0.5) | 79 vs 99, p = 0.15 | −18.2 (−20.9 to −15.5) | 64 vs 304, p < 0.001 |
| Q5_K_M − Q4_K_M (laptop) | +1.9 (−0.3 to +4.1) | 120 vs 95, p = 0.10 | −5.5 (−8.4 to −2.6) | 158 vs 231, p < 0.001 |

- **The PS4 GPU does not cost accuracy:** the same Q4_K_M file scores 72.9% on the PS4 GPU and on the laptop CPU. The ~3.4-point loss against Kaggle comes from Q4_K_M in llama.cpp, not from the GPU.
- **Q5_K_M sits in between:** it is not significantly better than Q4_K_M (p = 0.10) and not significantly worse than full precision (p = 0.15). Under the decision rule written down before the run ("recovers" = |Δ| ≤ 1.5 points and p > 0.05), it misses by 0.016 points: −1.516, less than one question.
- **The format is fragile, the answers are not:** strict accuracy moves by up to 9 points between configurations, with no order by precision (Q5_K_M 57.6% < Q4_K_M 63.2% < PS4 GPU 66.8%), while flexible accuracy stays within ~2 points.
- **The first 100 questions overestimate:** they gave 77–81% flexible on the PS4, against 72.9% on all 1,319.

## How the GPU was used without installing anything

The PS4's GPU (AMD "Liverpool", GCN 2) is supported by the `amdgpu` kernel driver of the PS4 Linux kernel, but the system had no Vulkan driver. Nothing was installed system-wide and no root access was used:

1. **Driver:** the RADV Vulkan driver (`libvulkan_radeon.so` and its ICD JSON) was extracted from a community-built Mesa package for the PS4 into a project folder. The package version was chosen to match the system's LLVM, and the archive was checked against the SHA-256 in the package database before extraction.
2. **Loading:** every GPU process runs with `VK_DRIVER_FILES` pointing to a copy of the ICD JSON with an absolute `library_path`, plus `MESA_SHADER_CACHE_DIR` and `XDG_CACHE_HOME` inside the project folder.
3. **llama.cpp:** built with `-DGGML_VULKAN=ON` against Vulkan and SPIR-V headers that were also extracted (with hash checks) into the project folder. The build ran under a temperature watchdog.
4. **What llama.cpp sees:** `AMD Liverpool (RADV LIVERPOOL)`, unified memory (4,479 MiB: 1 GiB VRAM + GTT), warp size 64, no fp16, no integer dot product and no matrix cores, so everything runs in fp32.

The scripts are in [`experiments/vulkan-check-20261105/`](experiments/vulkan-check-20261105/). This repository does not cover how to install Linux on the PS4.

## Limitations

- **One seed.** One training run, one seed. The accuracy results are about this run, not about GRPO in general.
- **A heavily reused test set.** The GSM8K test set was used for every decision in this project: prompts, token limit, quantization, GPU vs CPU. Decisions tuned on it may look better here than they would on fresh data.
- **The laptop as a third backend.** Quantization was separated from backend on an x86 laptop, not on the PS4 CPU, which only ran 100 questions. The laptop's outputs differ from both PS4 backends (16/100 identical to the PS4 CPU), so it is a third backend, not a stand-in for the PS4 CPU. The 1.56× speed-up was measured on 100 questions only.
- **Q8_0 and F16 not run.** They only ran a 20-question test, so the ~3.4-point loss cannot yet be split between 4-bit quantization and llama.cpp vs PyTorch.
- **One GPU hang.** In the first full run the GPU stopped producing tokens at question 197. The client waited 15 minutes, no `amdgpu` message appeared in the kernel log, and the HDMI console stopped working. After a reboot the same question took 6.7 s, and the remaining 1,122 questions finished with no hang. From then on the client restarted the server every 50 questions and used a 120 s timeout. The cause is unknown.
- **The format is fragile to quantization.** Strict accuracy changes by up to 9 points between quantizations and backends while flexible accuracy barely moves. Constrained decoding (e.g. a llama.cpp grammar for the last line) would likely fix the format, but it was not tested.
- **Other limits:** GSM8K only, English only, greedy decoding. The PS4 runs warm (76–80 °C under load) and temperature control between blocks is approximate.

## Reproduction

### Layout

```
notebooks/    Kaggle notebooks: 0.6B pilot and the 1.7B GRPO run (with outputs)
gguf/         make_gguf.sh (conversion pipeline), MANIFEST.csv, chat template
ps4/          PS4 inventory, CPU build and benchmark scripts, first PS4 results
eval-ps4/     first PS4 evaluation (CPU, 100 questions, base vs tuned): run_eval.py, grading.py
analise/      error analysis and token-limit study (Portuguese)
experiments/
  vulkan-check-20261105/      Vulkan checks, GPU build with watchdog, llama-bench GPU vs CPU
  ps4-eval-gpu-20261106/      GPU vs CPU on 100 questions (client on the LAN)
  gsm8k-full-gpu-20261108/    full GSM8K on the PS4 GPU (client on the PS4, resumable)
  quant-acc-fedora-20261109/  Q4_K_M and Q5_K_M on a laptop CPU (Q8_0/F16: 20-question tests only)
```

Every experiment folder has a `manifest.csv` with SHA-256 hashes of the model, template, questions, grader and scripts, the per-question results (CSV) and a summary (`resultado*.md`). The summaries and code comments are in Portuguese. All runs use llama.cpp commit [`dde879bc`](https://github.com/ggml-org/llama.cpp/commit/dde879bc4f954b809892fd0d660515f42536394a) and the same `grading.py`.

### Main commands

**Training and conversion:** run `notebooks/grpo_qwen3_1.7b_gsm8k.ipynb` on Kaggle (T4, `HF_TOKEN` secret), then `HF=$(command -v hf) WORK=./work bash gguf/make_gguf.sh`. Compare the hashes with `gguf/MANIFEST.csv`.

**Full GSM8K on the PS4 GPU** (client on the PS4, Python standard library only; it stops the chat server, pauses torrents, rests and cools down between blocks of 50, and restores everything at the end):

```bash
cd experiments/gsm8k-full-gpu-20261108
python3 -u run_eval_full.py --ini 0 --fim 1319 --saida resultados_full.csv --chat-final cpu
python3 analise_full.py          # writes resultado_full.md (needs the Kaggle eval_grpo.csv)
```

It is resumable: run the same command again and finished questions are skipped. Paths assume the project folder `/mnt/midia/llm-ps4` on the PS4 and the extracted driver described above.

**GPU vs CPU on 100 questions** (client on another machine on the LAN):

```bash
cd experiments/ps4-eval-gpu-20261106
PS4_HOST=<ps4-address> python3 run_eval_gpu.py
python3 analise.py ps4_eval_gpu_<stamp>.csv
```

**Quantization on an x86 CPU** (llama.cpp `llama-server` built with the same options):

```bash
cd experiments/quant-acc-fedora-20261109
for b in q4km q5km; do python3 -u run_quant.py --braco $b --ini 0 --fim 1319 || break; done
python3 analise_q4km.py && python3 analise_q5km.py
```

**Synthetic benchmark:** `experiments/vulkan-check-20261105/bench_vulkan.sh` (llama-bench, GPU and CPU interleaved, `-p 512 -n 128 -r 3`).

## Hardware and software

| | |
|---|---|
| Device | PlayStation 4: AMD Jaguar APU, 8 cores at ~1.6 GHz (AVX, no AVX2/FMA), GCN 2 GPU with 18 compute units |
| Memory | 8 GB GDDR5 shared; 1 GB reserved as VRAM, 6.8 GiB for the CPU |
| OS | Arch-based Linux on an external USB drive, PS4-specific kernel with `amdgpu` |
| Inference | llama.cpp `dde879bc`: CPU build (8 threads) and Vulkan build (RADV, `-ngl 99`), `-c 4096` |
| Training | Kaggle, 1× Tesla T4, unsloth + TRL GRPO, LoRA r = 16, 357 steps (~6 h) |

## Links

- Model card, merged weights, LoRA adapter, GGUF files and per-question outputs: [felipedutrain/qwen3-1.7b-gsm8k-grpo](https://huggingface.co/felipedutrain/qwen3-1.7b-gsm8k-grpo) (the link works once the model is public).
- llama.cpp: [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp)

## License

Code and documentation in this repository: [MIT](LICENSE), © 2026 Felipe Dutrain de Sales.

Third-party material keeps its own license:
- **Qwen3** model weights (and any derivative weights, such as the GGUF files and the tuned model) are under the **Apache License 2.0**.
- The **GSM8K** dataset (questions and reference answers that appear in the evaluation outputs and in `questions*.jsonl`) is under the **MIT License**.
