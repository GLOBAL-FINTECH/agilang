# AGILANG AI / ML Training Toolkit

AGILANG AI is designed to make data analysis, machine learning, deep learning, scientific computing, audio, speech, video, and model deployment simpler than Python while preserving compatibility with mature Python AI backends during the transition.

## Architecture

```text
AGILANG syntax             simple training language
AGILANG native tensors     dependency-light tensor/scientific layer
AGILANG ML                 regression, classification, clustering, preprocessing
AGILANG deep learning      starter neural-network trainer and model format
Backend bridge             TensorFlow/PyTorch optional acceleration
Runtime intelligence       CPU/RAM/GPU detection and backend selection
Visualization              AGS/web chart specifications
Model artifacts            .agi-model JSON format
```

## Backend selection

AGILANG chooses the backend using runtime intelligence:

| Environment | Recommended backend |
|---|---|
| CPU only | `agilang-native` |
| GPU 2GB+ with TensorFlow | `tensorflow` |
| GPU 2GB+ with PyTorch | `torch` |
| Small models | `agilang-native` |
| CNN/RNN/Transformer training | TensorFlow/PyTorch bridge until native GPU matures |

## Core APIs

```agi
let info = ai_runtime_info()
let backend = ai_select_backend()
let x = tensor([[1, 2], [3, 4]])
let y = tensor_matmul(x, tensor([[5], [6]]))
```

## Data processing

```agi
let rows = [
  {"x": 1, "y": 2},
  {"x": 2, "y": 4},
  {"x": 3, "y": 6}
]
print(dataset_summary(rows))
print(minmax_scale(rows, ["x", "y"]))
```

## Machine learning

```agi
let model = linear_regression(rows, ["x"], "y")
print(predict_linear(model, {"x": 10}))
```

## Deep learning starter

```agi
let model = neural_network_train([[0], [1], [2]], [[0], [2], [4]], hidden=4, epochs=100)
print(neural_network_predict(model, [3]))
```

## Audio and video pipeline descriptors

```agi
print(audio_pipeline("speech_to_text"))
print(video_pipeline("object_detection"))
```

## Model save/load

```agi
model_save("models/demo.agi-model", model)
let loaded = model_load("models/demo.agi-model")
```

## Production direction

1. Native tensor API first.
2. TensorFlow/PyTorch bridge for big model training.
3. Native C/WASM/GPU backend later.
4. AGS visualization dashboard for training metrics.
5. Model serving through AGILANG web routes.

The goal is not to copy Python line-for-line. The goal is to give developers a simpler AGILANG interface while allowing mature AI backends underneath until AGILANG native acceleration is ready.
