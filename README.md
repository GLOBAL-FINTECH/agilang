# AGILANG Programming Language, Web Framework, Blockchain Runtime, and AIFlow Platform

AGILANG is a modular programming language and application runtime for building web apps, APIs, dashboards, CMS/blog systems, real-time apps, blockchain-enabled applications, and native AI/ML workflows using `.agi` source files and `.ags` reactive templates.

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
| AIFlow | Native ML, CNN training, AGIRecord datasets, BPE tokenizer, transformer starter, ONNX reference runtime |
| Deployment | Vendored runtime support for portable generated projects |

---

## Install and basic commands

```bash
pip install -e .
agi --help
agi run examples/hello.agi
python -m pytest -q
python -m compileall -q agilang tests
```

---

# AGILANG AI runtime app generation

The AI runtime generator creates **AGILANG entrypoints**, not Python launchers.

```bash
agi new my-ai --template ai --force
cd my-ai
```

Generated root entrypoints:

```text
run.agi
dataset.agi
train.agi
infer.agi
cnn.agi
llm.agi
onnx.agi
gpu.agi
distributed.agi
benchmark.agi
transformer.agi
```

Generated source files:

```text
src/ai_runtime.agi
src/dataset.agi
src/train.agi
src/infer.agi
src/cnn.agi
src/llm.agi
src/onnx.agi
src/gpu.agi
src/distributed.agi
src/benchmark.agi
src/transformer.agi
```

The generator does **not** create app-facing Python launchers:

```text
run.py
train.py
infer.py
```

The current AGILANG implementation may still use a Python-hosted runtime internally, but the generated project surface is AGILANG-native.

---

## AI runtime commands, command by command

Show the AI runtime menu:

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

Run CNN workflow:

```bash
agi run cnn.agi
```

Run language model workflow:

```bash
agi run llm.agi
```

Run ONNX Tier 1 workflow:

```bash
agi run onnx.agi
```

Run GPU planner workflow:

```bash
agi run gpu.agi
```

Run distributed planner workflow:

```bash
agi run distributed.agi
```

Run benchmark workflow:

```bash
agi run benchmark.agi
```

Run transformer workflow:

```bash
agi run transformer.agi
```

Generate without vendored runtime:

```bash
agi new my-ai --template ai --no-vendor
```

---

## AI runtime project structure

```text
my-ai/
├─ agilang.toml
├─ .env.example
├─ run.agi
├─ dataset.agi
├─ train.agi
├─ infer.agi
├─ cnn.agi
├─ llm.agi
├─ onnx.agi
├─ gpu.agi
├─ distributed.agi
├─ benchmark.agi
├─ transformer.agi
├─ app/controllers/AiController.agi
├─ config/ai.agi
├─ config/ai.json
├─ routes/ai.agi
├─ src/
│  ├─ ai_runtime.agi
│  ├─ dataset.agi
│  ├─ train.agi
│  ├─ infer.agi
│  ├─ cnn.agi
│  ├─ llm.agi
│  ├─ onnx.agi
│  ├─ gpu.agi
│  ├─ distributed.agi
│  ├─ benchmark.agi
│  └─ transformer.agi
├─ resources/views/dashboard.ags
├─ storage/datasets/
├─ storage/models/
├─ storage/checkpoints/
└─ vendor/agilang/        optional vendored runtime
```

---

# AIFlow feature set

## 1. Dataset engine: AGIRecord

Files:

```text
agilang/agirecord.py
agilang/agirecord_indexed.py
```

Capabilities:

```text
AGIRecord dataset format
Indexed AGIRecord v2 random access
save/load
shuffle
batch
split
summary
```

Command:

```bash
agi run dataset.agi
```

Tests:

```bash
python -m pytest tests/test_ai_platform_70.py tests/test_ai_platform_100.py -q
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

Tests:

```bash
python -m pytest tests/test_ai_platform_100.py -q
```

---

## 3. Native tensors and autodiff

Files:

```text
agilang/ndtensor.py
agilang/ndtensor_broadcast.py
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

Tests:

```bash
python -m pytest tests/test_ndtensor.py tests/test_aiflow_native.py -q
```

---

## 4. CNN vision and training

Files:

```text
agilang/vision_kernels.py
agilang/vision_kernels_v2.py
agilang/cnn_layers.py
agilang/conv2d_training.py
agilang/cnn_optimizers.py
agilang/conv2d_multichannel_training.py
agilang/cnn_training_loop_v1.py
agilang/cnn_training_loop_v2.py
agilang/cnn_batch_trainer.py
```

Capabilities:

```text
single-channel Conv2D
RGB Conv2D
multi-filter Conv2D
Conv2D backward gradients
multi-channel gradients
multi-filter gradients
ReLU forward/backward
MaxPool forward/backward
Flatten
Dense classifier
Softmax cross-entropy
Adam updates
full native CNN classifier train_step
fit loop
evaluation
checkpoint helper
.agi-model save/load
```

Commands:

```bash
agi run cnn.agi
agi run train.agi
agi run infer.agi
```

Tests:

```bash
python -m pytest \
  tests/test_vision_kernels.py \
  tests/test_vision_kernels_v2.py \
  tests/test_cnn_layers.py \
  tests/test_conv2d_training.py \
  tests/test_cnn_optimizers.py \
  tests/test_conv2d_multichannel_training.py \
  tests/test_cnn_training_loop_v1.py \
  tests/test_cnn_training_loop_v2.py \
  -q
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

## 5. Tokenizer and language model starter

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

Command:

```bash
agi run llm.agi
```

Tests:

```bash
python -m pytest tests/test_ai_platform_100.py tests/test_ai_final_execution_layer.py -q
```

---

## 6. Transformer runtime

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

Command:

```bash
agi run transformer.agi
```

---

## 7. ONNX Tier 1 reference runtime

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

Command:

```bash
agi run onnx.agi
```

Boundary: this is a reference executor for descriptor dictionaries. Full ONNX file parsing and complete operator coverage are production-hardening work.

---

## 8. GPU runtime planner and kernel registry

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

Command:

```bash
agi run gpu.agi
```

Boundary: GPU dispatch points exist. Production CUDA/ROCm/DirectML/Metal kernels still need hardware-specific implementation.

---

## 9. Distributed training planner and runtime reference

Files:

```text
agilang/distributed_training.py
agilang/distributed_runtime.py
```

Capabilities:

```text
training node descriptors
distributed strategy planner
shard planner
local allreduce average reference
```

Command:

```bash
agi run distributed.agi
```

Boundary: local distributed math is implemented. Real network transport and multi-node execution are future production work.

---

## 10. Benchmarks

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

Command:

```bash
agi run benchmark.agi
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
  tests/test_ai_runtime_generator.py \
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
app/controllers/
config/app.agi
config/auth.agi
config/database.agi
routes/web.agi
routes/api.agi
resources/views/layout.ags
resources/views/home.ags
resources/views/login.ags
resources/views/register.ags
resources/views/forgot-password.ags
resources/views/reset-password.ags
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

---

# Critical generated-app rule

Generated AI runtime applications must use AGI entrypoints.

Correct:

```bash
agi run train.agi
```

Not the generated app pattern:

```bash
python train.py
```

Python can remain an internal host runtime while AGILANG matures toward native/C/GPU execution, but generated project files must be AGI-native.
