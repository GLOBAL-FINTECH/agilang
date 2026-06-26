# AGILANG Programming Language, Web Framework, Blockchain Runtime, and AIFlow Platform

AGILANG is a modular programming language and application runtime for building web apps, APIs, dashboards, CMS/blog systems, real-time apps, blockchain-enabled applications, and native AI/ML workflows using `.agi` source files and `.ags` reactive templates.

AGILANG is designed to be simple to learn, lightweight to deploy, and structured like a modern full-stack framework.

```text
learn AGILANG -> create an app -> run .agi files -> train AI models -> deploy
```

**License:** MIT  
**Developed by:** Izukanji Sirwimba, AGILab, Izurex Enterprise Limited

---

## What AGILANG includes

| Area | Capability |
|---|---|
| Language | `.agi` source files, parser, runtime, CLI, syntax tooling |
| Templates | `.ags` reactive templates |
| Web framework | Laravel-style app structure, routes, controllers, config, auth pages |
| Blockchain | SBQ/EVM-style app generator, beacon, validators, RPC, mempool, consensus profile |
| AIFlow | Native ML, CNN training, dataset engine, tokenizer, transformer starter, ONNX reference runtime |
| Deployment | Vendored runtime support for portable generated projects |

---

## Install and basic commands

```bash
pip install -e .
```

Check the CLI:

```bash
agi --help
```

Run an AGILANG file:

```bash
agi run examples/hello.agi
```

Run tests:

```bash
python -m pytest -q
```

Compile check:

```bash
python -m compileall -q agilang tests
```

---

# AGILANG project generation

## Create an AI runtime app

The AI runtime generator creates **AGILANG entrypoints**, not Python launchers.

```bash
agi new my-ai --template ai
cd my-ai
```

Generated root files:

```text
run.agi
train.agi
infer.agi
dataset.agi
benchmark.agi
transformer.agi
```

Run the generated AI app:

```bash
agi run run.agi
```

Run dataset workflow:

```bash
agi run dataset.agi
```

Run training workflow:

```bash
agi run train.agi
```

Run inference workflow:

```bash
agi run infer.agi
```

Run benchmark workflow:

```bash
agi run benchmark.agi
```

Run transformer workflow:

```bash
agi run transformer.agi
```

Force recreate:

```bash
agi new my-ai --template ai --force
```

Generate without vendored runtime:

```bash
agi new my-ai --template ai --no-vendor
```

Important rule:

```text
Generated AI application entrypoints are .agi files.
The generator does not create run.py, train.py, infer.py, or benchmark.py as app-facing commands.
```

The current runtime backend may still be Python-hosted internally, but the generated project surface is AGILANG-native.

---

## AI runtime project structure

```text
my-ai/
├─ agilang.toml
├─ .env.example
├─ run.agi
├─ train.agi
├─ infer.agi
├─ dataset.agi
├─ benchmark.agi
├─ transformer.agi
├─ src/
│  ├─ ai_runtime.agi
│  ├─ train.agi
│  ├─ infer.agi
│  ├─ dataset.agi
│  ├─ benchmark.agi
│  └─ transformer.agi
├─ config/
│  └─ ai.json
├─ resources/views/
│  └─ dashboard.ags
├─ storage/
│  ├─ datasets/
│  └─ models/
└─ vendor/agilang/        optional vendored runtime
```

---

# AIFlow features

## 1. Dataset engine: AGIRecord

Files:

```text
agilang/agirecord.py
agilang/agirecord_indexed.py
```

Capabilities:

```text
AGIRecord dataset format
save/load
shuffle
batch
split
summary
indexed random access
```

Python-level test command:

```bash
python -m pytest tests/test_ai_platform_70.py tests/test_ai_platform_100.py -q
```

AGI app command:

```bash
agi run dataset.agi
```

Conceptual AGI workflow:

```agi
fn main() -> i32:
    print("Create AGIRecord dataset")
    print("Shuffle, batch, split, and index records")
    return 0
```

---

## 2. Image preprocessing

File:

```text
agilang/image_ops.py
```

Capabilities:

```text
pixel_scale
flip_left_right
flip_top_bottom
crop_center
resize_nearest
```

Test:

```bash
python -m pytest tests/test_ai_platform_100.py -q
```

---

## 3. Native tensors and autodiff

Files:

```text
agilang/ndtensor.py
agilang/aiflow_native.py
```

Capabilities:

```text
NDTensor
variable
matmul
mse
softmax
reverse-mode autodiff
SGD step
native dense training
```

Test:

```bash
python -m pytest tests/test_ndtensor.py tests/test_aiflow_native.py -q
```

---

## 4. CNN vision kernels

Files:

```text
agilang/vision_kernels.py
agilang/vision_kernels_v2.py
agilang/cnn_layers.py
```

Capabilities:

```text
single-channel Conv2D
RGB Conv2D
multi-filter Conv2D
ReLU
MaxPool
AvgPool
Flatten
softmax
image classifier pipeline
CNN .agi-model save/load
```

Test:

```bash
python -m pytest tests/test_vision_kernels.py tests/test_vision_kernels_v2.py tests/test_cnn_layers.py -q
```

---

## 5. CNN training

Files:

```text
agilang/conv2d_training.py
agilang/cnn_optimizers.py
agilang/conv2d_multichannel_training.py
agilang/cnn_training_loop_v1.py
agilang/cnn_training_loop_v2.py
agilang/cnn_batch_trainer.py
```

Capabilities:

```text
Conv2D forward
Conv2D backward
MSE loss
SGD kernel update
Adam kernel update
MaxPool backward
multi-channel Conv2D gradients
multi-filter Conv2D gradients
ReLU backward
Dense classifier backward
softmax cross-entropy
full native CNN classifier training loop
batch trainer
checkpoint helper
```

Run CNN training tests:

```bash
python -m pytest tests/test_conv2d_training.py tests/test_cnn_optimizers.py tests/test_conv2d_multichannel_training.py tests/test_cnn_training_loop_v1.py tests/test_cnn_training_loop_v2.py -q
```

Run generated AGI training entrypoint:

```bash
agi run train.agi
```

Complete CNN training pipeline:

```text
RGB image
-> multi-filter Conv2D
-> ReLU
-> MaxPool
-> Flatten
-> Dense classifier
-> Softmax loss
-> Dense backward
-> MaxPool backward
-> ReLU backward
-> Conv2D backward
-> Adam updates
```

---

## 6. Tokenizer and language model starter

Files:

```text
agilang/tokenizer_engine.py
agilang/bpe_tokenizer.py
agilang/llm_trainer.py
```

Capabilities:

```text
word tokenizer
BPE tokenizer starter
tiny language model training
next-token prediction
.agi-model save/load
```

Test:

```bash
python -m pytest tests/test_ai_platform_100.py tests/test_ai_final_execution_layer.py -q
```

Run generated transformer workflow:

```bash
agi run transformer.agi
```

Tiny LLM pipeline:

```text
text
-> BPE tokenizer
-> token ids
-> token pairs
-> tiny LM training
-> .agi-model
```

---

## 7. Transformer runtime

Files:

```text
agilang/transformer_blocks.py
agilang/transformer_runtime.py
```

Capabilities:

```text
Embedding descriptor
Attention descriptor
Transformer stack descriptor
layer_norm
attention_scores
attention_pool
feed_forward
transformer_block
```

Test:

```bash
python -m pytest tests/test_ai_platform_100.py -q
```

---

## 8. ONNX Tier 1 reference runtime

File:

```text
agilang/onnx_tier1_runtime.py
```

Implemented reference ops:

```text
Relu
Sigmoid
Softmax
MatMul
Add
Mul
Flatten
Reshape
Transpose
Gemm
```

Test:

```bash
python -m pytest tests/test_ai_final_execution_layer.py -q
```

The ONNX layer is a reference executor for descriptor dictionaries. Full ONNX file parsing and complete operator coverage are future production work.

---

## 9. GPU runtime planner and kernel registry

Files:

```text
agilang/gpu_runtime_plan.py
agilang/gpu_kernel_registry.py
```

Capabilities:

```text
CUDA backend detection plan
ROCm backend detection plan
DirectML backend detection plan
Metal backend detection plan
CPU fallback
kernel registry for matmul, conv2d, relu, softmax, attention
```

Test:

```bash
python -m pytest tests/test_ai_platform_100.py tests/test_ai_final_execution_layer.py -q
```

Important boundary:

```text
GPU dispatch points exist.
Production CUDA/ROCm/DirectML/Metal kernels still need hardware-specific implementation.
```

---

## 10. Distributed training planner and runtime reference

Files:

```text
agilang/distributed_training.py
agilang/distributed_runtime.py
```

Capabilities:

```text
training node descriptor
distributed strategy planner
shard planner
local allreduce average reference
```

Test:

```bash
python -m pytest tests/test_ai_platform_100.py tests/test_ai_final_execution_layer.py -q
```

Boundary:

```text
Local distributed math is implemented.
Real network transport and multi-node execution are future production work.
```

---

## 11. Benchmarks

File:

```text
agilang/ai_benchmarks.py
```

Capabilities:

```text
time_call
benchmark_suite
compare_reference
```

Run benchmark workflow in generated AI app:

```bash
agi run benchmark.agi
```

Run tests:

```bash
python -m pytest tests/test_ai_platform_70.py -q
```

---

# End-to-end AI runtime validation

Run all AI-related tests:

```bash
python -m pytest \
  tests/test_ai_toolkit.py \
  tests/test_aiflow.py \
  tests/test_aiflow_full.py \
  tests/test_aiflow_native.py \
  tests/test_ndtensor.py \
  tests/test_vision_kernels.py \
  tests/test_vision_kernels_v2.py \
  tests/test_cnn_layers.py \
  tests/test_conv2d_training.py \
  tests/test_cnn_optimizers.py \
  tests/test_conv2d_multichannel_training.py \
  tests/test_cnn_training_loop_v1.py \
  tests/test_cnn_training_loop_v2.py \
  tests/test_ai_platform_70.py \
  tests/test_ai_platform_100.py \
  tests/test_ai_final_execution_layer.py \
  -q
```

Run complete repository tests:

```bash
python -m pytest -q
```

Compile all modules:

```bash
python -m compileall -q agilang tests
```

---

# Blockchain generation

Create a blockchain project:

```bash
agi new cbac-chain --template blockchain --chain-id 1900 --symbol SBQ --force
cd cbac-chain
```

Generated blockchain entrypoints are AGI files:

```text
run.agi
chain.agi
rpc.agi
```

Run:

```bash
agi run run.agi
agi run chain.agi
agi run rpc.agi
```

Check chain status:

```bash
agi chain status --root .
```

Start RPC:

```bash
agi chain rpc --root . --host 127.0.0.1 --port 8545
```

Beacon commands:

```bash
agi beacon init --path . --chain-id 1900
agi beacon status
agi beacon produce-block
agi beacon attest
agi beacon finalize
agi beacon fork-choice
agi beacon simulate --validators 64 --epochs 2
```

Ethereum consensus profile commands:

```bash
agi chain ethereum-consensus-capabilities
agi chain ethereum-consensus-write-config --chain-id 901900
agi chain ethereum-consensus-check
agi chain ethereum-consensus-sim --slots 8
agi chain consensus-replacement-plan --network private-fork --consensus ethereum-pos-replica
```

---

# Web starter direction

AGILANG web apps should follow a Laravel-style layout:

```text
app/
  controllers/
config/
  app.agi
  auth.agi
  database.agi
routes/
  web.agi
  api.agi
resources/views/
  layout.ags
  home.ags
  login.ags
  register.ags
  forgot-password.ags
  reset-password.ags
storage/
public_html/
```

AGS is the default template engine. React, Vue, and raw HTML should remain optional front-end targets.

---

# Production boundary

AGILANG AIFlow now has a complete reference execution foundation:

```text
dataset -> preprocessing -> CNN training -> model save/load -> tokenizer -> transformer starter -> ONNX reference -> GPU planner -> distributed planner
```

Still required for production parity with TensorFlow/PyTorch:

```text
hardware-optimized CUDA/ROCm/DirectML/Metal kernels
full ONNX file parser and complete operator coverage
real multi-node network transport
large-scale transformer backpropagation
production LLM checkpointing and serving
```

The current system is suitable as a native AGILANG AI framework foundation and CPU reference runtime. Production acceleration comes next.
