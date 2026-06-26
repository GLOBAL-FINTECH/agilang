# AGILANG AIFlow Production Upgrade

This upgrade moves the AIFlow modules away from demo-only language and into production-facing APIs with explicit capability boundaries.

## What is production-usable now

| Area | Production-facing capability |
|---|---|
| Tokenizer | BPE train, encode, decode, save, load, special-token handling |
| LLM small model | Tokenizer-backed smoothed n-gram model with generation, perplexity, save/load |
| Transformer | Dependency-free CPU reference inference runtime with embeddings, multi-head attention, causal mask, feed-forward layers and persistence |
| ONNX | Descriptor executor plus optional real `.onnx` execution through `onnxruntime` |
| TorchCompat | PyTorch-style native subset: Tensor, nn.Module, Linear, activations, SGD, save/load |
| GPU dispatch | CPU production fallbacks and optional torch/cupy/backend detection/dispatch |
| Native GPU library gate | Shared-library discovery via `AGILANG_GPU_LIBRARY` / `AGILANG_CUDA_LIBRARY` |
| Distributed runtime | Local runtime and shared-filesystem allreduce coordinator |
| Image preprocessing | JSON-array loading, optional Pillow image loading/saving, resize, crop, grayscale, normalization |
| CLI | `agi ai ...` production commands for capability checks, tokenizers, language models, ONNX/GPU/distributed status and image preprocessing |
| Platform gate | `ai_capabilities()` and `ai_deployment_gate()` for deployment checks |

## Critical honesty boundary

`agilang.torch_compat` is a production-facing PyTorch-style subset built on AGILANG native tensors. It is **not** full PyTorch parity yet.

Full PyTorch parity means reimplementing or matching:

- thousands of operators
- dtype/device/storage system
- tensor dispatcher
- autograd coverage across all ops
- TorchScript / FX / Dynamo / compiler stack
- CUDA memory allocator and streams
- distributed torch runtime
- serialization and checkpoint compatibility
- years of numerical and hardware testing

AGILANG now has the correct internal place to grow that work: `agilang.torch_compat` for the high-level API and `agilang.cuda_backend` for native accelerator discovery.

## Install optional production AI dependencies

Base AGILANG remains dependency-light. For image and ONNX production work:

```bash
pip install "agilang[ai]"
```

For GPU ONNX Runtime environments:

```bash
pip install "agilang[ai-gpu]"
```

## CLI commands

```bash
# Capability report
agi ai capabilities
agi ai doctor
agi ai doctor --require-onnxruntime
agi ai doctor --require-gpu

# Tokenizer lifecycle
agi ai tokenizer-train --input corpus.txt --out models/tokenizer.json --merges 200
agi ai tokenizer-train --text "agilang builds ai" --out models/tokenizer.json
agi ai tokenizer-encode --model models/tokenizer.json --text "agilang builds ai" --bos --eos
agi ai tokenizer-decode --model models/tokenizer.json --ids "[2,4,5,3]"

# Small language model lifecycle
agi ai lm-train --input corpus.txt --out models/domain-lm.agi-model --order 3 --merges 200
agi ai lm-generate --model models/domain-lm.agi-model --prompt "agilang" --steps 32

# Backend status
agi ai onnx-status
agi ai gpu-status
agi ai distributed-status

# Image preprocessing
agi ai preprocess-image --input document.png --out storage/document.json --rows 224 --cols 224 --mode L
```

## TorchCompat API

```python
from agilang.torch_compat import tensor, nn, optim, mse_loss

x = tensor([[1.0, 2.0]])
model = nn.Sequential(
    nn.Linear(2, 4),
    nn.ReLU(),
    nn.Linear(4, 1),
)
y = model(x)
loss = mse_loss(y, tensor([[1.0]]))
loss.backward()
optimizer = optim.SGD(model.parameters(), lr=0.01)
optimizer.step()
```

## Native GPU library gate

```python
from agilang.cuda_backend import native_gpu_status, require_native_gpu

print(native_gpu_status())
require_native_gpu()
```

The loader checks `AGILANG_GPU_LIBRARY` and `AGILANG_CUDA_LIBRARY`, then standard package locations for AGILANG native GPU shared libraries.

## What remains external for heavy production

AGILANG should delegate large-scale AI workloads to audited external engines through interop until the native backend reaches equivalent coverage:

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

## Image preprocessing path

```python
from agilang.image_ops import image_preprocess, save_image

image = image_preprocess("document.png", rows=224, cols=224, mode="L", normalize=True)
save_image("storage/document.json", image)
```

Image loading supports JSON pixel arrays without extra dependencies. PNG/JPEG/WebP requires Pillow.

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
