# AIFlow Native Vision Kernels

This update adds the first real CPU/reference CNN-style image operations for AGILANG AIFlow.

## Added

- `image_shape()`
- `normalize_image()`
- `flatten()`
- `conv2d_single_channel()`
- `maxpool2d()`
- `avgpool2d()`
- `relu_image()`
- `image_to_patches()`
- `cnn_feature_pipeline()`

## Example

```python
from agilang.vision_kernels import cnn_feature_pipeline

image = [
    [0, 0, 0],
    [0, 255, 0],
    [0, 0, 0],
]

kernel = [[1, 1], [1, 1]]
print(cnn_feature_pipeline(image, kernel, pool_size=2))
```

## Why this matters

TensorFlow replacement needs working CNN operations, not just architecture descriptors.
This module gives AGILANG a correctness-first reference implementation for image and video frame processing.

## Current boundary

Implemented now:

```text
single-channel Conv2D forward
MaxPool2D forward
AvgPool2D forward
Flatten
patch extraction
image normalization
simple CNN feature pipeline
```

Remaining:

```text
multi-channel Conv2D
Conv2D backward gradients
batched images
GPU kernels
image loading/resizing
CNN layer integration with NativeSequential
```
