# AGILANG AIFlow TensorFlow-Style Replacement Layer

AIFlow is AGILANG's native training API inspired by TensorFlow/Keras, but simplified for AGILANG developers.

## Goal

The goal is not to copy TensorFlow line-for-line. The goal is to make the common workflow easier:

```text
load data -> create tensors -> define model -> compile -> fit -> evaluate -> predict -> save
```

## Current capabilities

- `Tensor`
- `constant()`
- `convert_to_tensor()`
- `zeros()`
- `ones()`
- `matmul()`
- `Dense` layer
- `Sequential` model
- `SGD` optimizer
- MSE loss
- Binary cross-entropy loss
- Binary accuracy metric
- `fit()` training loop
- `predict()`
- `evaluate()`
- `save()` / `load_model()` using `.agi-model`
- Keras-style namespace:
  - `keras.Sequential`
  - `keras.layers.Dense`
  - `keras.optimizers.SGD`
  - `keras.losses.binary_crossentropy`
  - `keras.metrics.binary_accuracy`

## Example

```python
from agilang.aiflow import keras

model = keras.Sequential([
    keras.layers.Dense(4, activation="relu", input_shape=[1]),
    keras.layers.Dense(1, activation="linear"),
])
model.compile(optimizer=keras.optimizers.SGD(0.01), loss="mse")
model.fit([[0], [1], [2], [3]], [[0], [2], [4], [6]], epochs=80)
print(model.predict([[4]]))
model.save("models/demo.agi-model")
```

## TensorFlow replacement boundary

AIFlow is now a TensorFlow-style foundation. It is not yet a full replacement for:

- CUDA/cuDNN kernels
- full automatic differentiation graph engine
- CNN layers
- RNN/LSTM/GRU layers
- Transformer layers
- distributed training
- TensorBoard
- SavedModel compatibility
- dataset streaming engine
- ONNX import/export

## Roadmap to full replacement

1. Add native ND tensor operations.
2. Add automatic differentiation tape.
3. Add Conv2D, pooling, dropout, embedding, LSTM, GRU and attention layers.
4. Add GPU backend adapters: CUDA, ROCm, DirectML.
5. Add streaming datasets for audio, image and video.
6. Add model serving runtime for AGILANG web routes.
7. Add TensorFlow/PyTorch import bridges so users can migrate models.
8. Add AGILANG-native model format and optimizer passes.

## Production recommendation

Use AIFlow native for small and medium AGILANG models. Use TensorFlow/PyTorch bridge for heavy GPU training until AGILANG native GPU kernels mature.
