from __future__ import annotations

from agilang.ai_platform import ai_deployment_gate, require_ai_capability
from agilang.bpe_tokenizer import BPETokenizer
from agilang.distributed_runtime import DistributedConfig, DistributedRuntime, WorkerSpec, allreduce_average
from agilang.gpu_kernel_registry import default_registry, dispatch_kernel
from agilang.llm_trainer import LanguageModelBundle, train_ngram_lm
from agilang.onnx_tier1_runtime import execute_graph, onnx_runtime_status
from agilang.transformer_runtime import ProductionTransformerRuntime


def test_bpe_tokenizer_decode_and_persistence(tmp_path):
    tokenizer = BPETokenizer.train(["hello world", "hello agilang"], merges=20)
    ids = tokenizer.encode("hello world", add_bos=True, add_eos=True)
    assert "hello" in tokenizer.decode(ids)
    saved = tokenizer.save(tmp_path / "tokenizer.json")
    loaded = BPETokenizer.load(saved)
    assert loaded.encode("hello world") == tokenizer.encode("hello world")
    assert loaded.decode(tokenizer.encode("hello world")) == tokenizer.decode(tokenizer.encode("hello world"))


def test_transformer_runtime_predict_and_persist(tmp_path):
    runtime = ProductionTransformerRuntime.create(vocab_size=12, dim=8, heads=2, hidden_dim=16, layers=1, max_positions=16)
    result = runtime.predict_next([1, 2, 3])
    assert 0 <= result["token_id"] < 12
    assert abs(sum(result["probabilities"]) - 1.0) < 1e-6
    saved = runtime.save(tmp_path / "transformer.json")
    loaded = ProductionTransformerRuntime.load(saved)
    assert loaded.summary()["vocab_size"] == 12


def test_ngram_language_model_bundle(tmp_path):
    bundle = train_ngram_lm(["agilang builds ai", "agilang builds blockchain"], merges=30, order=2)
    assert isinstance(bundle.generate("agilang", steps=2), str)
    assert bundle.perplexity(["agilang builds ai"]) is not None
    saved = bundle.save(tmp_path / "lm.agi-model")
    loaded = LanguageModelBundle.load(saved)
    assert loaded.summary()["backend"] == "ngram"


def test_onnx_descriptor_runtime_and_status():
    graph = [
        {"op_type": "MatMul", "inputs": ["x", "w"], "output": "y"},
        {"op_type": "Add", "inputs": ["y", "b"], "output": "z"},
    ]
    env = execute_graph(graph, {"x": [[1, 2]], "w": [[3], [4]], "b": [[1]]})
    assert env["z"] == [[12.0]]
    status = onnx_runtime_status()
    assert status["descriptor_runtime"] is True


def test_kernel_registry_cpu_fallback():
    reg = default_registry()
    assert reg.dispatch("matmul", "cpu", [[1, 2]], [[3], [4]]) == [[11.0]]
    assert dispatch_kernel("relu", [-1, 2, 0], backend="auto") == [0.0, 2.0, 0.0]


def test_distributed_runtime_local_and_filesystem_single_worker(tmp_path):
    assert allreduce_average([[1, 3], [3, 5]]) == [2.0, 4.0]
    runtime = DistributedRuntime(DistributedConfig(backend="local", workers=1), WorkerSpec(0, 1))
    assert runtime.allreduce_average([5, 7]) == [5.0, 7.0]
    fs = DistributedRuntime(DistributedConfig(backend="filesystem", workers=1, run_dir=str(tmp_path)), WorkerSpec(0, 1, "run"))
    assert fs.allreduce_average([2, 4], step="s1") == [2.0, 4.0]


def test_ai_platform_deployment_gate():
    assert require_ai_capability("tokenizer")["production"] is True
    gate = ai_deployment_gate()
    assert gate["ok"] is True
    assert "capabilities" in gate["report"]
