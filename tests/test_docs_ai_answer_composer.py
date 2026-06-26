from __future__ import annotations

from pathlib import Path

from agilang.docs_ai_answer_composer import ask_docs_ai, detect_intent, rank_answer_sources
from agilang.docs_ai_trainer import load_docs_dataset, train_docs_model


def _make_docs(root: Path) -> None:
    docs = root / "docs"
    docs.mkdir()
    (docs / "AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE.md").write_text(
        "# AGILANG AIFlow and Blockchain Deep Reference\n\n"
        "## Part 2: Blockchain Deep Reference\n\n"
        "AGILANG blockchain tooling includes blockchain app generator, genesis config, chain config, RPC server, mempool, transaction handling, state database, beacon simulation, validator concepts.\n\n"
        "Create a project:\n\n"
        "```bash\nagi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force\n```\n",
        encoding="utf-8",
    )
    (docs / "AGILANG_DOCS_AI_QA_AND_CODE_DEMO.md").write_text(
        "# AGILANG Docs AI Q&A and Code Task Demo\n\n"
        "This demo asks: How do I create a blockchain project in AGILANG? It is a docs AI evaluation page, not the primary blockchain guide.\n",
        encoding="utf-8",
    )
    (docs / "AGILANG_ERROR_DEBUGGING_DEEP_REFERENCE.md").write_text(
        "# AGILANG Error Handling and Debugging Deep Reference\n\n"
        "A 404 means not found. A 500 means server error. Use custom templates and logging.\n",
        encoding="utf-8",
    )


def test_detect_intent_blockchain():
    assert detect_intent("How do I create a blockchain project in AGILANG?") == "blockchain_project"


def test_blockchain_answer_is_clean_and_has_command(tmp_path):
    _make_docs(tmp_path)
    trained = train_docs_model(tmp_path, tmp_path / "model", merges=40, order=2, max_words=80)
    answer = ask_docs_ai(trained.out_dir, "How do I create a blockchain project in AGILANG?")

    assert answer["ok"] is True
    assert answer["intent"] == "blockchain_project"
    assert "Use the blockchain scaffold template" in answer["answer"]
    assert "agi new my-chain --template blockchain --chain-id 1900 --symbol SBQ --force" in answer["code"]
    assert not answer["answer"].startswith("AI doctor passes")
    assert "AI doctor passes" not in answer["code"]


def test_primary_blockchain_doc_ranks_above_demo_doc(tmp_path):
    _make_docs(tmp_path)
    trained = train_docs_model(tmp_path, tmp_path / "model", merges=40, order=2, max_words=80)
    chunks = load_docs_dataset(Path(trained.out_dir) / "agilang_docs_dataset.jsonl")
    sources = rank_answer_sources("How do I create a blockchain project in AGILANG?", chunks, top_k=2)

    assert sources[0].source == "docs/AGILANG_AI_BLOCKCHAIN_DEEP_REFERENCE.md"


def test_docs_training_question_can_use_docs_ai_source(tmp_path):
    _make_docs(tmp_path)
    (tmp_path / "docs" / "AGILANG_DOCS_AI_TRAINING_TEST.md").write_text(
        "# AGILANG Docs AI Training Test\n\nTrain with python tools/train_agilab_docs_ai.py --root . --out storage/agilab-docs-ai --smoke-test.\n",
        encoding="utf-8",
    )
    trained = train_docs_model(tmp_path, tmp_path / "model", merges=40, order=2, max_words=80)
    answer = ask_docs_ai(trained.out_dir, "How do I train the AGILANG docs AI model?")

    assert answer["intent"] == "docs_ai_training"
    assert "python tools/train_agilab_docs_ai.py" in answer["code"]
