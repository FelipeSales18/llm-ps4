# Inventário — LLM no PS4

Coletado em 2026-11-01 com o HD externo do PS4 conectado por USB a um Fedora (PS4 desligado).
Nada no sistema do PS4 foi alterado: a sda2 foi montada somente leitura.

## Distro

- **CachyOS Linux** (`ID=cachyos`, `ID_LIKE=arch`, `BUILD_ID=rolling`), lido em `sda2:/etc/os-release`.
- O rótulo da partição é `psxitarch`, mas o os-release diz CachyOS.

## Usuários (sda2:/etc/passwd)

| usuário | UID | GID | home | shell |
|---|---|---|---|---|
| ps4  | 1001 | 1001 | /home/ps4  | /usr/bin/fish |
| user | 1000 | 1000 | /home/user | /bin/fish |

## HD externo

`/dev/sda`: USB, modelo "BUP Slim BL", 1.8T.

| Partição | FS | Rótulo | UUID | Tamanho | Usado | Livre | No PS4 |
|---|---|---|---|---|---|---|---|
| sda1 | vfat (FAT32) | — | <ID_VFAT> | 100M | ? | ? | boot (não montada nesta sessão) |
| sda2 | ext4 | psxitarch | <UUID_SDA2> | 49G | 6.8G | 40G (15% usado) | `/` |
| sda3 | ext4 | jellyfin | <UUID_SDA3> | 1.8T | 29G | 1.7T (2% usado) | `/mnt/midia` |

O espaço livre da sda3 foi medido antes do download dos modelos (~4 GB).

## Pasta do projeto

- No PS4: `/mnt/midia/llm-ps4` (raiz da sda3, ext4).
- A raiz da sda3 tem permissão `drwxrwxrwx root:root`. As pastas de filmes pertencem ao UID 1000.
- A pasta `llm-ps4/` foi criada pelo UID 1000 do Fedora, que no PS4 corresponde ao usuário `user`, não ao `ps4` (1001).

## Riscos no fstab do PS4

Conteúdo de `sda2:/etc/fstab` (só registro; nada foi alterado):

```
UUID=<UUID_RAIZ_ANTIGA> /              ext4    defaults,noatime,commit=60 0 1
/dev/sdb3 /mnt/midia ext4 defaults,nofail 0 2
```

1. **A raiz aponta para um UUID diferente do atual da sda2.** No fstab está `<UUID_RAIZ_ANTIGA>`; o UUID atual da sda2 é `<UUID_SDA2>`. Como o PS4 dá boot, a raiz provavelmente vem do `root=` da linha de comando do kernel (sda1). A entrada do fstab parece desatualizada, e o systemd pode reclamar dela ou tentar fsck/remount de um dispositivo inexistente.
2. **Os filmes montam como `/dev/sdb3`, pelo nome do dispositivo.** Nomes `sdX` não são estáveis: se a ordem de detecção mudar (outro disco ou pendrive conectado, mudança de porta USB), `/mnt/midia` pode não montar (por causa do `nofail`, sem erro visível). Aí Jellyfin e `llm-ps4` ficariam vazios, ou outra partição seria montada no lugar. O mais seguro seria `UUID=<UUID_SDA3>` ou `LABEL=jellyfin`.

> Atualização da linha de comando do kernel (coletada com o PS4 ligado em 2026-11-01): `/proc/cmdline` **não tem `root=`**:
> `panic=0 clocksource=tsc consoleblank=0 net.ifnames=0 radeon.dpm=0 amdgpu.dpm=0 drm.debug=0 console=ttyS0,115200n8 console=tty0 video=HDMI-A-1:1920x1080@60`.
> A raiz é escolhida pelo initramfs ou pelo loader, não pelo fstab nem pelo cmdline. Em execução, `/` = `/dev/sdb2` (psxitarch) e `/mnt/midia` = `/dev/sdb3` (jellyfin).

## Memória de vídeo e kernel

- A configuração de boot reserva **1 GB de RAM para a GPU** (VRAM carve-out da APU).
  - Confirmado no dmesg: `amdgpu: VRAM: 1024M`, `1024M of VRAM memory ready`, `3455M of GTT memory ready`. Também em `/sys/class/drm/card0/device/mem_info_vram_total` = 1073741824.
  - **Efeito na CPU:** `MemTotal` = 6.8 GiB (7078948 kB), dos 8 GB GDDR5 físicos. O 1 GB da VRAM sai desse total.
  - **Variável de experimento:** num teste com Vulkan, o tamanho da VRAM (1 GB) limita o que cabe em `-ngl`, e o GTT (3455M) é memória do sistema compartilhada. Mudar a reserva de VRAM muda **tanto a RAM disponível para a CPU quanto a VRAM**. Registre o tamanho da VRAM junto de cada resultado de benchmark.
- Kernel: Linux 7.0.0, compilado especificamente para o PS4: **não atualizar o sistema** (`pacman -Syu`).
- Fuso do PS4: America/New_York (EST). Os horários do PS4 ficam 2 h atrás dos do Fedora (-03).

## CPU

- AMD Jaguar, `DG1101SKF84HV`, family 22 (0x16), model 19. 8 núcleos, 1 thread por núcleo, 2 módulos com 4 MiB de L2 no total. ~1.6 GHz (BogoMIPS 3187).
- `nproc` = 8.

| Flag | Presente |
|---|---|
| **avx** | ✅ sim |
| **avx2** | ❌ não |
| **fma** | ❌ não (sem FMA3) |
| **f16c** | ✅ sim |
| **bmi2** | ❌ não (só bmi1) |
| sse4_1 / sse4_2 / ssse3 | ✅ sim |

Consequência: o llama.cpp vai usar os caminhos AVX (sem AVX2/FMA), que são bem mais lentos que os de CPUs modernas.

## Memória

```
               total        used        free      shared  buff/cache   available
Mem:           6.8Gi       920Mi       4.8Gi        57Mi       1.3Gi       5.9Gi
Swap:          6.8Gi          0B       6.8Gi
```
Swap: só zram (`/dev/zram0`, 6.8G, prioridade 100). Não há swap em disco.

## Ferramentas

| Ferramenta | Versão |
|---|---|
| gcc / g++ | 15.2.1 20260209 |
| cmake | 4.3.1 |
| make | GNU Make 4.4.1 |
| ninja | 1.13.2 |
| git | 2.53.0 |
| python3 | 3.14.3 (venv ok) |
| pip | 26.0.1 |
| curl | 8.19.0 |
| wget | 1.25.0 |
| tmux | 3.6a |
| `/usr/bin/time` | **ausente** (pacote `time` não instalado) |
| vulkaninfo | **ausente** |

## Serviços (só registro)

`systemctl is-active jellyfin tailscaled` → `active`, `active`.

## Discos em execução

- `sda` (465.8G) é o disco interno do PS4, com partições do sistema da Sony. **Não mexer.**
- `sdb` é o HD externo: `sdb1` vfat 100M, `sdb2` psxitarch → `/` (40G livres), `sdb3` jellyfin → `/mnt/midia` (1.7T livres).

## Modelos (detalhes em models/MANIFEST.csv)

- Q8_0: repositórios oficiais `Qwen/Qwen3-0.6B-GGUF` e `Qwen/Qwen3-1.7B-GGUF`.
- **Troca registrada:** os repositórios oficiais só têm Q8_0. O Q4_K_M veio de `unsloth/Qwen3-0.6B-GGUF` e `unsloth/Qwen3-1.7B-GGUF`.
- Baixados com `hf download --revision <sha>` (huggingface_hub 2.4.0). As pastas `models/*/*/.cache/` são metadados do `hf`.
- Os 4 arquivos foram verificados: SHA256 igual ao `lfs.oid` da API, tamanho igual ao da API e cabeçalho `GGUF`.

## llama.cpp

- Repositório: https://github.com/ggml-org/llama.cpp em `/mnt/midia/llm-ps4/llama.cpp`
- **Commit: `dde879bc4f954b809892fd0d660515f42536394a`** (2026-11-01T01:46:43-05:00, "sycl: Try PkgConfig for LevelZero includes / libs (#31076)"). Versão `0.8.0-dev (build 12032)`.
- Build: `cmake -B build -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF` com GGML_NATIVE padrão (`-march=native`), mais `nice -n 10 cmake --build build --config Release -j 6 --target llama-bench llama-cli`, rodando em tmux.
- **Tempo de compilação:** configure 11 s + build 1001 s = **1012 s (~17 min)**, com gcc 15.2.1. Log em `logs/build_20261101_102410.log`.
- **system_info** (llama-cli com `-lv 4`):
  `n_threads = 8 (n_threads_batch = 8) / 8 | CPU : SSE3 = 1 | SSSE3 = 1 | AVX = 1 | F16C = 1 | LLAMAFILE = 1 | OPENMP = 1 | REPACK = 1 |`
  Nenhum "Illegal instruction".

## Benchmark 1 — CPU (2026-11-01, 1 GB de VRAM reservada)

`llama-bench -p 512 -n 128 -r 3 -t 4,8 -o csv`, com `nice -n 10`. CSVs em `results/bench_<modelo>_20261101.csv`.

| Modelo | Threads | Prompt pp512 (t/s) | Geração tg128 (t/s) | Pico RSS |
|---|---|---|---|---|
| Qwen3-0.6B-Q4_K_M | 4 | 38.28 ± 0.52 | 14.40 ± 0.00 | 520 MiB (532344 kB) |
| Qwen3-0.6B-Q4_K_M | 8 | 68.31 ± 0.26 | 23.36 ± 0.50 | (mesmo processo) |
| Qwen3-1.7B-Q4_K_M | 4 | 13.27 ± 0.32 | 5.82 ± 0.03 | 1.19 GiB (1252260 kB) |
| Qwen3-1.7B-Q4_K_M | 8 | 23.67 ± 0.57 | 8.35 ± 0.22 | (mesmo processo) |

- O pico de RSS é por execução do llama-bench, que cobre os dois valores de threads. Foi medido com `scripts/maxrss.py` (`ru_maxrss`), porque `/usr/bin/time` não existe no PS4.
- Sanidade (`results/sanity_1.7b.txt`): resposta **29** (correta). Prompt 17.9 t/s, geração 8.1 t/s.
  - ⚠️ O pico de RSS do llama-cli foi **5.44 GiB** (5702488 kB), porque o contexto padrão é o de treino (40960 tokens) e o cache KV ocupa ~4.5 GB. Isso fica perto do limite de 6.8 GiB com 1 GB de VRAM reservada. Nos próximos testes, use `-c` explícito (por exemplo `-c 4096`).
