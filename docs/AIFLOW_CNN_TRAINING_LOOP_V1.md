# AIFlow CNN Training Loop v1

This update implements the first half of the complete native CNN training loop.

## Added

- ReLU forward for feature maps
- ReLU backward using activation masks
- Adam optimizer state for multi-filter RGB kernels
- Adam update for multi-filter kernels and biases
- One-step feature extractor training

## Current pipeline

```text
RGB image
-> multi-filter Conv2D
-> ReLU
-> feature-map loss
-> ReLU backward
-> multi-filter Conv2D backward
-> Adam update
```

## Why this matters

This connects the already implemented RGB Conv2D gradients into a real optimization loop. Kernels can now move from error toward a target feature map.

## Second half still remaining

```text
MaxPool integration
-> Flatten
-> Dense classifier
-> softmax loss
-> classifier backward
-> full CNN classifier training
-> save complete CNN model
```
