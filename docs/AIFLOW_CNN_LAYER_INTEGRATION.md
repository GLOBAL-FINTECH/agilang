# AIFlow CNN Layer Integration

This upgrade connects AGILANG vision kernels into a CNN-style classifier layer.

## Added

- `conv2d_multi_filter()`
- `cnn_multi_filter_features()`
- `CNNClassifier`
- `load_cnn_classifier()`
- `.agi-model` save/load for CNN classifier models

## Pipeline

```text
RGB image
-> multi-filter Conv2D
-> ReLU
-> MaxPool
-> Flatten all feature maps
-> Dense classifier
-> Softmax
-> Predicted label
```

## Example

```python
from agilang.cnn_layers import CNNClassifier

model = CNNClassifier(
    kernels=[kernel_a, kernel_b],
    dense_weights=[[0.1, 2.0], [0.1, 2.0]],
    labels=["low", "high"],
    pool_size=1,
)

result = model.predict(image)
print(result["predicted_label"])
model.save("models/cnn.agi-model")
```

## Why this matters

AGILANG now has a complete native reference inference path for small CNN-style models:

```text
image -> features -> classification -> .agi-model
```

## Remaining work

- Conv2D backward gradients
- training CNN kernels, not only inference
- batched image tensors
- image loading/resizing helpers
- native C/WASM/GPU acceleration
- MNIST-style worked demo
