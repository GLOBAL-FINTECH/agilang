# AIFlow Native Autodiff Integration

This update connects AIFlow training to AGILANG's native `NDTensor` autodiff engine.

## Added

- `agilang.aiflow_native`
- `NativeDense`
- `NativeSequential`
- `native_linear_model()`
- `load_native_model()`
- training through `NDTensor.backward()`
- optimization through `sgd_step()`
- `.agi-model` save/load roundtrip

## Example

```python
from agilang.aiflow_native import native_linear_model

model = native_linear_model(input_dim=1, output_dim=1)
model.fit([[0], [1], [2], [3]], [[0], [2], [4], [6]], epochs=60, learning_rate=0.05)
print(model.predict([[4]]))
model.save("models/native.agi-model")
```

## Why this matters

AIFlow is no longer only a manually coded training loop. It now has a native path:

```text
AIFlow model -> NDTensor operations -> reverse-mode autodiff -> SGD update
```

This is the correct next layer for replacing TensorFlow gradually with AGILANG-native execution.

## Remaining engineering work

- bias broadcasting instead of single-row workaround
- multi-layer nonlinear native graph
- Adam/RMSProp on NDTensor parameters
- Conv2D forward/backward
- batching with vectorized gradients
- GPU kernels
