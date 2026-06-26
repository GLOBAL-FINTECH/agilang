# AIFlow Native v2

This patch adds the next AGILANG-native training layer:

- row-bias broadcasting
- broadcast gradient reduction
- native activation bridge
- multi-layer dense models
- ReLU / sigmoid / tanh / linear activations
- batched full-dataset training
- `.agi-model` save/load

Target flow:

```text
NativeSequentialV2 -> NativeDenseV2 -> NDTensor matmul -> broadcast bias -> activation -> MSE -> backward -> SGD
```

This moves AGILANG closer to a native TensorFlow replacement while keeping the system simple and auditable before GPU kernels are added.
