# AIFlow Multi-Channel Conv2D Training

This update extends native Conv2D training from grayscale single-channel filters to RGB and multi-filter convolution gradients.

## Added

- `conv2d_multi_channel_forward()`
- `conv2d_multi_channel_backward()`
- `conv2d_multi_filter_forward()`
- `conv2d_multi_filter_backward()`
- `mse_feature_maps()`

## Training path

```text
RGB image
-> multi-channel Conv2D forward
-> feature-map loss
-> multi-channel backward
-> gradient for image
-> gradient for each RGB kernel channel
-> gradient for each bias
```

## Why this matters

Real computer vision uses multi-channel images and many filters. This module gives AGILANG the reference math needed to train RGB convolution filters natively.

## Remaining work

- Adam update for multi-channel kernels
- batch training over many images
- ReLU backward and MaxPool backward integration into this full path
- CNN Sequential training loop
- GPU acceleration
