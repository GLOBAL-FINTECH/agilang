# AIFlow Full TensorFlow Replacement Roadmap

AIFlow is being expanded from a TensorFlow-style foundation into a full AGILANG AI training stack.

## Added in this stage

- `Variable`
- `GradientTape` scalar-gradient starter
- `Adam`
- `RMSProp`
- `Dataset.from_tensor_slices()`
- `shuffle()`
- `batch()`
- `map()`
- architecture specifications for:
  - `Conv2D`
  - `MaxPool2D`
  - `Flatten`
  - `Dropout`
  - `Embedding`
  - `LSTM`
  - `MultiHeadAttention`
- GPU backend descriptors:
  - CUDA
  - ROCm
  - DirectML
  - native CPU
- compatibility bridge descriptors:
  - TensorFlow
  - PyTorch
  - ONNX

## Honest replacement status

AIFlow now has a fuller replacement architecture, but it is not yet a complete TensorFlow equivalent.

Implemented now:

```text
native training API
basic tensor helpers
sequential dense model
model save/load
scalar GradientTape
Adam/RMSProp optimizer primitives
dataset batching/shuffling
CNN/RNN/Transformer architecture descriptors
GPU backend detection descriptors
compatibility bridge descriptors
```

Still required for real full replacement:

```text
ND tensor storage engine
autodiff graph engine
vectorized CPU kernels
CUDA kernels
ROCm kernels
DirectML kernels
Conv2D forward/backward implementation
pooling forward/backward implementation
embedding lookup training
LSTM/GRU forward/backward implementation
attention forward/backward implementation
dataset streaming from disk/audio/video
model serving runtime
ONNX import/export
TensorFlow/PyTorch migration tools
distributed training
training dashboard
```

## Target developer experience

```agi
let model = aiflow.Sequential([
  aiflow.layers.Conv2D(32, 3, activation="relu"),
  aiflow.layers.MaxPool2D(2),
  aiflow.layers.Flatten(),
  aiflow.layers.Dense(10, activation="softmax")
])

model.compile(optimizer=aiflow.optimizers.Adam(0.001), loss="categorical_crossentropy")
model.fit(train, epochs=10, batch_size=32)
model.save("models/image.agi-model")
```

## Production strategy

1. Use AGILANG native API for simple and medium models.
2. Use TensorFlow/PyTorch bridge for heavy production GPU training while AGILANG kernels mature.
3. Build native ND tensor and autodiff next.
4. Add GPU kernels after CPU correctness is verified.
5. Add ONNX import/export for model exchange.
