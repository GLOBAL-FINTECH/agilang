# AGILANG AIFlow Production Upgrade

This upgrade moves the AIFlow modules away from demo-only language and into production-facing APIs with explicit capability boundaries.

## What is production-usable now

| Area | Production-facing capability |
|---|---|
| Tokenizer | BPE train, encode, decode, save, load, special-token handling |
| LLM small model | Tokenizer-backed smoothed n-gram model with generation, perplexity, save/load |
| Transformer | Dependency-free CPU reference inference runtime with embeddings, multi-head attention, causal mask, feed-forward layers and persistence |
| ONNX | Descriptor executor plus optional real `.onnx` execution through `onnxruntime` |
| GPU dispatch | CPU production fallbacks and optional torch/cupy backend detection/dispatch |
| Distributed runtime | Local runtime and shared-filesystem allreduce coordinator |
| Platform gate | `ai_capabilities()` and `ai_deployment_gate()` for deployment checks |

## What remains external for heavy production

AGILANG should delegate large-scale AI workloads to audited external engines through interop:

- PyTorch / TorchScript
- ONNX Runtime / ONNX Runtime GPU
- TensorRT / TensorRT-LLM
- llama.cpp or vLLM for large language model serving
- NCCL / MPI / Ray / Torch Distributed for high-throughput distributed training

The native AGILANG path is designed for small-to-medium CPU applications, embedded AI, education, fintech scoring prototypes, document classification, and controlled domain models.

## New APIs

```python
from agilang import BPETokenizer, train_ngram_lm, ai_capabilities, ai_deployment_gate

# Tokenizer
tokenizer = BPETokenizer.train(["agilang builds ai"], merges=50)
ids = tokenizer.encode("agilang builds ai", add_bos=True, add_eos=True)
text = tokenizer.decode(ids)
tokenizer.save("models/tokenizer.json")

# Small language model
bundle = train_ngram_lm(["agilang builds ai", "agilang builds blockchain"], order=3)
bundle.save("models/domain-lm.agi-model")
print(bundle.generate("agilang", steps=8))

# Deployment gate
print(ai_capabilities())
print(ai_deployment_gate(require_onnxruntime=False, require_gpu=False))
```

## ONNX production path

```python
from agilang.onnx_tier1_runtime import load_onnx_model

model = load_onnx_model("model.onnx")
print(model.summary())
result = model.predict({"input": input_tensor})
```

If `onnxruntime` is not installed, this fails clearly instead of pretending descriptor execution is full ONNX support.

## GPU production path

```python
from agilang.gpu_kernel_registry import dispatch_kernel

result = dispatch_kernel("matmul", [[1, 2]], [[3], [4]], backend="auto")
```

The registry automatically uses accelerated backends only when installed and available. CPU fallback remains production-available.

## Distributed runtime

```python
from agilang.distributed_runtime import DistributedConfig, DistributedRuntime, WorkerSpec

runtime = DistributedRuntime(
    DistributedConfig(backend="filesystem", workers=2, run_dir="/shared/agilang-run"),
    WorkerSpec(worker_id=0, workers=2, run_id="job-001"),
)
mean_gradient = runtime.allreduce_average([1.0, 2.0, 3.0], step="epoch1-batch1")
```

For high-throughput clusters, bridge to NCCL/MPI/Ray/Torch Distributed instead of using the filesystem coordinator.
