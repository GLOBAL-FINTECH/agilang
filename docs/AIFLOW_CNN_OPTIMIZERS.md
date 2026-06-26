# AIFlow CNN Optimizers and Pooling Gradients

This update adds the next training pieces for native CNN learning in AGILANG.

## Added

- Adam optimizer state for Conv2D kernels
- Adam update for a 2D kernel and scalar bias
- MaxPool2D forward pass with max-position mask
- MaxPool2D backward pass using that mask

## Training flow

```text
Conv2D output
-> MaxPool2D forward records max positions
-> loss gradient arrives from later layer
-> MaxPool2D backward routes gradient to the winning pixels
-> Conv2D backward calculates filter gradients
-> Adam update changes kernel weights and bias
```

## Why this matters

SGD is simple and useful, but Adam usually gives more stable learning for neural networks. MaxPool backward is also required for training CNNs that include pooling.

## Current boundary

Implemented now:

```text
single-channel Conv2D gradients
SGD kernel update
Adam kernel update
MaxPool backward gradient routing
```

Remaining:

```text
multi-channel Conv2D backward
multi-filter Conv2D backward
batched image training
complete CNN training loop
GPU kernels
```
