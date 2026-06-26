# AGILANG AIFlow and Blockchain Deep Reference

This document teaches the deeper AGILANG AIFlow and blockchain development areas. It is designed for developers who already understand the beginner wiki and now want to build AI-enabled and blockchain-enabled applications.

---

# Part 1: AIFlow Deep Reference

## 1. What AIFlow is

AIFlow is the AGILANG AI/ML layer. It includes:

```text
AGIRecord datasets
image preprocessing
CNN training
BPE tokenizer
small language model bundle
transformer runtime
ONNX descriptor executor
ONNX Runtime bridge
TorchCompat
GPU backend status gate
distributed runtime coordinator
```

Check capabilities:

```bash
agi ai capabilities
agi ai doctor
```

---

## 2. AI project structure

Recommended structure:

```text
my-ai-app/
├─ agilang.toml
├─ src/
│  ├─ ai_runtime.agi
│  ├─ dataset.agi
│  ├─ train.agi
│  ├─ infer.agi
│  ├─ cnn.agi
│  ├─ llm.agi
│  ├─ onnx.agi
│  ├─ gpu.agi
│  └─ distributed.agi
├─ storage/
│  ├─ datasets/
│  ├─ models/
│  ├─ checkpoints/
│  └─ predictions/
└─ config/
   └─ ai.json
```

Generate an AI runtime app:

```bash
agi new my-ai --template ai --force
```

---

## 3. Dataset design

Use a consistent sample shape.

Classification dataset sample:

```json
{
  "input": [[0.0, 0.1], [0.2, 0.3]],
  "label": 1,
  "meta": {
    "source": "demo",
    "id": "sample-001"
  }
}
```

Text dataset sample:

```json
{
  "text": "AGILANG builds AI apps",
  "label": "technology"
}
```

Professional dataset rules:

```text
[ ] Keep input shape consistent
[ ] Keep labels consistent
[ ] Track source metadata
[ ] Split train/test
[ ] Avoid leaking test data into training
[ ] Version datasets
```

---

## 4. Image preprocessing

Command:

```bash
agi ai preprocess-image --input document.png --out storage/document.json --rows 224 --cols 224 --mode L
```

Python API:

```python
from agilang.image_ops import image_preprocess, save_image

image = image_preprocess("document.png", rows=224, cols=224, mode="L", normalize=True)
save_image("storage/document.json", image)
```

Supported production pattern:

```text
image file -> load_image -> resize -> normalize -> JSON/tensor input -> model
```

---

## 5. CNN development

A simple CNN training flow:

```text
image input
-> convolution
-> ReLU
-> maxpool
-> flatten
-> dense classifier
-> softmax loss
-> backward pass
-> optimizer update
-> save .agi-model
```

Use CNN for:

```text
document classification
simple image recognition
KYC document quality checks
small visual prototypes
educational model training
```

Boundary:

```text
AGILANG CNN is useful for small/medium CPU-reference work.
For heavy production vision, bridge to ONNX Runtime, PyTorch, TensorRT, or another production backend.
```

---

## 6. BPE tokenizer

Train:

```bash
agi ai tokenizer-train --input corpus.txt --out models/tokenizer.json --merges 200
```

Encode:

```bash
agi ai tokenizer-encode --model models/tokenizer.json --text "agilang builds ai" --bos --eos
```

Decode:

```bash
agi ai tokenizer-decode --model models/tokenizer.json --ids "[2,4,5,3]"
```

Python API:

```python
from agilang.bpe_tokenizer import BPETokenizer

tokenizer = BPETokenizer.train(["agilang builds ai"], merges=50)
ids = tokenizer.encode("agilang builds ai", add_bos=True, add_eos=True)
text = tokenizer.decode(ids)
tokenizer.save("models/tokenizer.json")
```

---

## 7. Small language model bundle

Train:

```bash
agi ai lm-train --input corpus.txt --out models/domain-lm.agi-model --order 3 --merges 200
```

Generate:

```bash
agi ai lm-generate --model models/domain-lm.agi-model --prompt "agilang" --steps 32
```

Use for:

```text
small domain text generation
autocomplete prototypes
classification helpers
education
controlled offline demos
```

Boundary:

```text
This is not GPT-scale training. For large language models, use external engines through interop.
```

---

## 8. TorchCompat

TorchCompat gives a PyTorch-style API on AGILANG native tensors.

```python
from agilang.torch_compat import tensor, nn, optim, mse_loss

x = tensor([[1.0, 2.0]])
y_true = tensor([[1.0]])

model = nn.Sequential(
    nn.Linear(2, 4),
    nn.ReLU(),
    nn.Linear(4, 1),
)

y_pred = model(x)
loss = mse_loss(y_pred, y_true)
loss.backward()

optimizer = optim.SGD(model.parameters(), lr=0.01)
optimizer.step()
```

Check status:

```python
from agilang.torch_compat import torch_compat_status
print(torch_compat_status())
```

Boundary:

```text
TorchCompat is a PyTorch-style AGILANG subset, not full PyTorch parity.
```

---

## 9. ONNX Runtime bridge

Check status:

```bash
agi ai onnx-status
```

Load real ONNX model when `onnxruntime` is installed:

```python
from agilang.onnx_tier1_runtime import load_onnx_model

model = load_onnx_model("model.onnx")
print(model.summary())
result = model.predict({"input": input_tensor})
```

Boundary:

```text
Descriptor executor is built in. Real .onnx execution requires optional onnxruntime.
```

---

## 10. GPU backend and deployment gates

Check GPU status:

```bash
agi ai gpu-status
```

Native GPU gate:

```python
from agilang.cuda_backend import native_gpu_status, require_native_gpu

print(native_gpu_status())
require_native_gpu()
```

Environment variables:

```text
AGILANG_GPU_LIBRARY
AGILANG_CUDA_LIBRARY
```

Boundary:

```text
CPU fallback and optional backend detection are implemented. Full native CUDA parity requires compiled shared libraries, kernels, memory management, stream handling, autograd integration, and GPU CI.
```

---

## 11. Distributed runtime

Status:

```bash
agi ai distributed-status
```

Filesystem coordinator example:

```python
from agilang.distributed_runtime import DistributedConfig, DistributedRuntime, WorkerSpec

runtime = DistributedRuntime(
    DistributedConfig(backend="filesystem", workers=2, run_dir="/shared/agilang-run"),
    WorkerSpec(worker_id=0, workers=2, run_id="job-001"),
)

mean_gradient = runtime.allreduce_average([1.0, 2.0, 3.0], step="epoch1-batch1")
```

Boundary:

```text
For high-throughput clusters, bridge to NCCL, MPI, Ray, or Torch Distributed.
```

---

## 12. AI production checklist

```text
[ ] Dataset versioned
[ ] Input shape documented
[ ] Training/test split created
[ ] Model file saved
[ ] Tokenizer saved with model if text model
[ ] Inference path tested
[ ] AI doctor passes
[ ] Optional backend installed if needed
[ ] No private data in logs
[ ] Model limitations documented
```

---

# Part 2: Blockchain Deep Reference

## 13. What AGILANG blockchain provides

AGILANG blockchain tooling includes:

```text
blockchain app generator
genesis config
chain config
RPC server
mempool
transaction handling
state database
beacon simulation
validator concepts
Ethereum consensus profile commands
```

Create a project:

```bash
agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force
```

---

## 14. Blockchain project structure

```text
my-chain/
├─ agilang.toml
├─ run.agi
├─ chain.agi
├─ rpc.agi
├─ src/
│  ├─ main.agi
│  ├─ chain.agi
│  ├─ rpc.agi
│  ├─ staking.agi
│  └─ devnet.agi
├─ config/
│  ├─ genesis.json
│  ├─ validators.json
│  ├─ rpc.json
│  └─ network.json
└─ storage/
```

---

## 15. Chain identity

Important values:

```text
chain_id
symbol
network name
genesis hash
RPC URL
currency decimals
```

Example:

```bash
agi new copper-chain --template blockchain --chain-id 901900 --symbol COPPER --force
```

Professional rule: never reuse a public chain ID for a different private chain.

---

## 16. Genesis config

Genesis defines the starting state.

Common fields:

```text
chain_id
alloc/accounts
balances
validators
initial timestamp
network name
```

Professional rules:

```text
[ ] Keep genesis in version control
[ ] Never put private keys in genesis
[ ] Document initial accounts
[ ] Keep chain_id consistent across config, RPC and wallet setup
```

---

## 17. Transactions

A transaction should include:

```text
from
to
value
nonce
gas/gas limit
chain_id
signature or authorization proof
```

Validation checklist:

```text
[ ] value is not negative
[ ] sender exists
[ ] sender has enough balance
[ ] nonce is correct
[ ] chain_id matches
[ ] signature is valid if required
[ ] gas rules are enforced
```

---

## 18. RPC server

Start RPC:

```bash
agi chain rpc --root . --host 127.0.0.1 --port 8545
```

Check status:

```bash
agi chain status --root .
```

Professional RPC rules:

```text
[ ] Bind private RPC to 127.0.0.1 unless intentionally public
[ ] Add rate limits
[ ] Do not expose admin/private APIs publicly
[ ] Log errors safely
[ ] Validate JSON-RPC input
```

---

## 19. Beacon and validator simulation

Beacon status:

```bash
agi beacon status
```

Simulate:

```bash
agi beacon simulate --validators 64 --epochs 2
```

Beacon commands:

```bash
agi beacon init --path . --chain-id 1900
agi beacon produce-block
agi beacon attest
agi beacon finalize
agi beacon fork-choice
```

Boundary:

```text
AGILANG beacon is a custom/private simulation path. It is not an official Ethereum mainnet validator client.
```

---

## 20. Ethereum consensus profile

Commands:

```bash
agi chain ethereum-consensus-capabilities
agi chain ethereum-consensus-write-config --chain-id 901900
agi chain ethereum-consensus-check
agi chain ethereum-consensus-sim --slots 8
agi chain consensus-replacement-plan --network private-fork --consensus ethereum-pos-replica
```

Use for:

```text
private Ethereum-derived design planning
validator architecture simulation
execution/consensus split understanding
```

Boundary:

```text
Live Ethereum mainnet validation requires official Ethereum clients.
```

---

## 21. Blockchain error handling

Common errors:

```text
invalid chain ID
bad genesis config
insufficient balance
negative transaction value
nonce mismatch
RPC port already in use
database locked
validator missing
```

Fix examples:

```text
invalid chain ID -> align config/genesis/rpc/wallet chain ID
insufficient balance -> fund account in genesis or reject transaction
nonce mismatch -> fetch account nonce before signing
RPC port in use -> change port or stop existing process
```

---

## 22. Blockchain production checklist

```text
[ ] Unique chain ID
[ ] Genesis reviewed
[ ] Validators configured
[ ] RPC protected
[ ] State database backed up
[ ] Error logs enabled
[ ] Test transactions pass
[ ] Reorg/finality behavior tested
[ ] No private keys committed
[ ] Explorer/wallet config matches chain ID
```

---

## 23. Full AI + blockchain app idea

Build:

```text
AI-powered blockchain dashboard
```

Features:

```text
chain status page
RPC health endpoint
validator dashboard
AI anomaly summary
transaction risk scoring prototype
custom 404/500 pages
admin login
```

Route map:

```text
GET /dashboard
GET /chain/status
GET /validators
GET /api/chain/status
GET /api/ai/capabilities
POST /api/ai/score-transaction
```

---

## Final rule

Use AGILANG AIFlow and blockchain systems professionally:

```text
validate inputs
protect secrets
document boundaries
write tests
run doctor/status commands
avoid false production claims
use external audited backends where necessary
```
