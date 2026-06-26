# AGILANG AI, ML and Data Toolkit

AGILANG now includes dependency-free helpers for data processing, scientific computing, classical machine learning, lightweight neural-network training, visualization specs, model persistence and runtime resource detection.

## Capabilities

- CSV read/write
- dataset summaries and missing-value analysis
- missing-value filling
- train/test split
- min-max and standard scaling
- tensors: shape, zeros, random, dot, matrix multiplication, transpose, elementwise add/sub/mul
- activations: ReLU, sigmoid, softmax
- statistics: mean and variance
- linear regression
- logistic regression
- K-Means clustering
- decision stump classifier
- confusion matrix and accuracy
- small one-hidden-layer neural network
- model save/load using `.agi-model` JSON
- chart specs for AGS/web rendering
- runtime RAM/GPU capability reporting

## GPU/RAM policy

The dependency-free runtime works on CPU and can report RAM/GPU availability. A GPU with 2GB+ memory is treated as the minimum recommended GPU profile for accelerated AI backends. Heavy production training should bridge to CUDA, ROCm, PyTorch, TensorFlow or ONNX Runtime through AGILANG/Python interop while keeping AGILANG as the application language.

## Example

```agi
fn main() -> i32:
    let rows = [{"x": 1, "y": 2, "label": 0}, {"x": 4, "y": 8, "label": 1}]
    print("runtime", ai_runtime_info())
    let model = ml_linear_regression(rows, "y", ["x"])
    print("prediction", ml_predict_linear(model, {"x": 10}))
    return 0
```
