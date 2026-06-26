# AIFlow RGB Vision Classifier

This update extends AGILANG AIFlow vision from grayscale/single-channel kernels into RGB/multi-channel inference.

## Added

- `softmax()`
- `argmax()`
- `normalize_rgb()`
- `conv2d_multi_channel()`
- `dense_predict()`
- `image_classifier_pipeline()`
- `benchmark_conv2d()`

## End-to-end pipeline

```text
RGB image
-> normalize_rgb
-> conv2d_multi_channel
-> relu_image
-> maxpool2d
-> flatten
-> dense_predict
-> softmax
-> argmax
-> predicted label
```

## Worked example

```python
from agilang.vision_kernels_v2 import image_classifier_pipeline

image = [
    [[255, 0, 0], [0, 255, 0]],
    [[0, 0, 255], [255, 255, 255]],
]

kernel = [
    [[1, 0, 0], [0, 1, 0]],
    [[0, 0, 1], [1, 1, 1]],
]

weights = [[0.1, 2.0]]
labels = ["low", "high"]

print(image_classifier_pipeline(image, kernel, weights, labels, pool_size=1))
```

## Benchmark scaffold

```python
from agilang.vision_kernels_v2 import benchmark_conv2d
print(benchmark_conv2d(image, kernel, repeats=100))
```

This benchmark is intentionally honest: it reports AGILANG native reference speed first. Future C/WASM/GPU kernels should use this same benchmark to prove acceleration.

## Remaining work

- multi-filter Conv2D
- batched RGB images
- Conv2D backward gradients
- CNN layer integration with AIFlow Native
- image loading/resizing
- MNIST-style dataset example
- NumPy benchmark comparison
