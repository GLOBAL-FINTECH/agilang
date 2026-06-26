# AGILANG Native ND Tensor Autodiff Engine

This stage adds the core native tensor/autodiff layer required for AGILANG to move from a TensorFlow-style wrapper toward a real AI training engine.

## Added

- `NDTensor`
- `ndtensor()`
- `variable()`
- rank-0, rank-1 and rank-2 tensor storage
- shape tracking
- `tolist()` and `item()`
- elementwise add, subtract, multiply and power
- `sum()`
- `mean()`
- `relu()`
- `sigmoid()`
- `matmul()`
- `mse()`
- `softmax()`
- reverse-mode autodiff graph traversal
- `backward()`
- `sgd_step()`

## Example

```python
from agilang.ndtensor import ndtensor, variable, mse, sgd_step

w = variable(0.0, name="w")
for _ in range(25):
    pred = w * ndtensor(2.0)
    loss = mse(pred, ndtensor(4.0))
    loss.backward()
    sgd_step([w], learning_rate=0.05)

print(w.item())
```

## Why this matters

TensorFlow replacement cannot be real without three major pieces:

```text
native tensor storage
autodiff
optimized kernels
```

This update adds the first serious native implementation of tensor storage and autodiff. It is intentionally simple and auditable before adding C/WASM/GPU kernels.

## Current boundary

Implemented now:

```text
scalar/vector/matrix tensors
reverse-mode autodiff for common operations
matmul gradients
SGD training step
```

Still required:

```text
broadcasting
higher-rank ND kernels
slicing/indexing gradients
Conv2D kernels
RNN/attention kernels
GPU kernels
memory planner
operation fusion
ONNX import/export
```
