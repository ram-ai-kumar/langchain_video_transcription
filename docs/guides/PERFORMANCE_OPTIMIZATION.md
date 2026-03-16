# Performance Optimization Guide

[← Back to Guides](./README.md)

This guide covers how the pipeline is engineered to run efficiently across hardware tiers — from a developer laptop to an enterprise GPU server — and how those engineering choices translate to operational and cost outcomes.

---

## Executive Summary

The pipeline is designed around three principles that directly serve a CXO-level agenda:

| Principle | Implementation | Business Outcome |
| --------- | -------------- | ---------------- |
| **Resource governance** | Sliding window scheduler (window=4, concurrency=2) | Predictable compute consumption; no runaway parallelism on shared infrastructure |
| **Hardware adaptability** | Automatic device detection (CPU / CUDA / MPS) | Runs optimally on existing hardware without re-configuration; no forced cloud spend |
| **Throughput vs. accuracy trade-off** | Configurable Whisper model size | Teams choose fidelity appropriate to their SLA, not a one-size-fits-all default |

---

## Scheduler: Sliding Window

All file tasks are dispatched through a **sliding window** that keeps resource pressure bounded regardless of directory size:

- **Window size: 4** — at most 4 files are loaded (2 running + 2 queued) at any moment
- **Concurrency: 2** — at most 2 files process simultaneously

As each file completes, the next enters the window. On a directory of 200 lecture recordings, the pipeline behaves identically to a directory of 5 — it never attempts to ingest the full list at once.

```text
Window: [F1, F2, F3, F4]   →  F1 done  →  Window: [F2, F3, F4, F5]
Running: F1, F2                             Running: F2, F3
Queued:  F3, F4                             Queued:  F4, F5
```

The scheduler constants live in `src/core/pipeline.py`:

```python
PIPELINE_WINDOW_SIZE = 4   # max tasks loaded at once
PIPELINE_CONCURRENCY = 2   # max tasks executing simultaneously
```

---

## Device Support

The pipeline auto-detects the best available compute device at startup. No manual configuration is required in standard deployments.

### NVIDIA GPU (CUDA)

Suitable for dedicated transcription servers or cloud GPU instances.

```bash
python main.py /path/to/media --device cuda
```

**Setup** (if not already installed):

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
python -c "import torch; print(torch.cuda.is_available())"
```

### Apple Silicon (MPS)

The default target for local use on M-series Macs (M1 through M4). No additional setup required beyond the standard `pip install torch`.

```bash
python main.py /path/to/media --device mps
python -c "import torch; print(torch.backends.mps.is_available())"
```

### CPU (Universal fallback)

Runs on any machine. Use when GPU is unavailable or when processing priority is low and compute headroom is limited.

```bash
python main.py /path/to/media --device cpu
```

---

## Transcription Model Selection

Whisper model choice is the primary accuracy-vs-speed lever. The pipeline defaults to `medium` — a calibrated balance for lecture-style content.

| Model  | Size    | RAM     | Recommended for                                    |
| ------ | ------- | ------- | -------------------------------------------------- |
| tiny   | 39 MB   | ~100 MB | Quick drafts, high-volume batch                    |
| base   | 74 MB   | ~200 MB | Internal tooling, non-critical transcripts         |
| small  | 244 MB  | ~500 MB | General-purpose, cost-sensitive deployments        |
| medium | 769 MB  | ~1.5 GB | **Default** — lecture content, technical vocabulary |
| large  | 1.55 GB | ~3 GB   | Compliance recordings, legal or medical content    |

```bash
python main.py /path/to/media --whisper-model large
```

---

## Configuration Reference

### CLI Flags

| Flag | Description | Default |
| ---- | ----------- | ------- |
| `--device` | Compute device (`auto`, `cpu`, `cuda`, `mps`) | `auto` |
| `--whisper-model` | Whisper model size | `medium` |
| `--batch-size` | Tasks per processing batch | `4` |
| `--max-workers` | Worker thread ceiling | auto-detect |
| `--no-optimizations` | Disable all performance optimizations | off |
| `--no-batch` | Disable batch processing | off |
| `--verbose` | Emit detailed performance and progress logs | off |

### Config File (`config.json`)

```json
{
  "enable_performance_optimizations": true,
  "device": "auto",
  "whisper_model": "medium",
  "use_batch_processing": true,
  "batch_size": 4,
  "max_workers": null
}
```

---

## Runtime Introspection

Query live performance state without modifying code:

```python
from src.processors.enhanced_audio_processor import EnhancedAudioProcessor

processor = EnhancedAudioProcessor(config)
info = processor.get_performance_info()
print(info["device_info"]["type"])     # e.g. "mps"
print(info["device_info"]["memory_gb"])
print(info["cached_models"])
```

Query optimal settings for the current machine:

```python
from src.utils.performance_optimizer import optimize_for_current_system

rec = optimize_for_current_system()
print(rec["optimal_device"].device_type.value)
print(rec["optimal_workers"])
```

---

## Troubleshooting

### CUDA out of memory

Reduce pressure on GPU VRAM:

```bash
python main.py /path/to/media --batch-size 2 --whisper-model small
```

### MPS unavailable

Requires macOS 12.0+ and PyTorch ≥ 1.12. Update and retry:

```bash
pip install --upgrade torch
python -c "import torch; print(torch.backends.mps.is_available())"
```

### Unexpectedly slow throughput

1. Confirm the active device with `--verbose` — CPU fallback may be in effect.
2. Check available RAM against the model size table above.
3. For large batches, ensure `--no-batch` is not set accidentally.

---

## Operational Guidance for Enterprise Deployments

- **Shared servers**: Keep `PIPELINE_CONCURRENCY = 2` to avoid monopolising GPU VRAM or LLM inference slots alongside other tenants.
- **Dedicated GPU nodes**: Raise `PIPELINE_CONCURRENCY` in `src/core/pipeline.py` after profiling; `4` is a safe upper bound for a single A100/H100 with `medium` model.
- **Air-gapped environments**: All models (Whisper, Ollama) are cached locally after first download — the pipeline runs fully offline thereafter. No data leaves the host.
- **Regulated content**: Use `--device cpu` to avoid MPS/CUDA kernel logs appearing in audit trails. Combine with `--whisper-model large` for maximum fidelity on compliance recordings.
