"""RAGAS-style evaluation pipeline for HealthStream RAG.

Runs golden test set through the RAG pipeline using a FastAPI test client
(no live server required) and computes lightweight evaluation metrics:

  - Faithfulness      : keyword overlap between generated answer and ground truth
  - Answer Relevancy  : fraction of question terms found in the generated answer
  - Context Precision : fraction of expected citation IDs retrieved
  - Context Recall    : fraction of ground truth terms found in retrieved context

Also checks:
  - PHI Leakage      : scans answers for SSN / phone / MRN patterns
  - Patient Isolation: wrong patient_id must return 0 citations

Run with:
    cd solution/backend && MOCK_AUTH=true uv run python scripts/evaluate.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Bootstrap: add repo root to sys.path and configure env vars before imports
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("VECTOR_BACKEND", "chroma")
os.environ.setdefault("LLM_BACKEND", "anthropic")
os.environ.setdefault("EMBEDDER_BACKEND", "local")
os.environ.setdefault("MOCK_AUTH", "true")
os.environ.setdefault("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GOLDEN_TEST_SET_PATH = BACKEND_DIR / "data" / "golden_test_set.yaml"
SAMPLE_DATA_PATH = BACKEND_DIR / "data" / "sample_data.json"

# HIPAA PHI regex patterns
PHI_PATTERNS: dict[str, re.Pattern[str]] = {
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "Phone": re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    "MRN": re.compile(r"\bMRN[-:\s]?\d{6,10}\b", re.IGNORECASE),
}

# Wrong-patient token for isolation check
ISOLATION_PATIENT_TOKEN = "synthetic-patient-WRONG"

# Column widths for the results table
COL_ID = 12
COL_Q = 40
COL_FAITH = 11
COL_REL = 11
COL_CTX = 11
COL_PHI = 8
TABLE_WIDTH = COL_ID + COL_Q + COL_FAITH + COL_REL + COL_CTX * 2 + COL_PHI + 8


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class GoldenItem:
    """Single entry from the golden test set."""

    id: str
    question: str
    ground_truth: str
    source_type: str
    patient_id: str
    expected_citations: list[str] = field(default_factory=list)


@dataclass
class EvalResult:
    """Evaluation metrics for one golden item."""

    id: str
    question: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    phi_leaked: bool
    phi_patterns: list[str]


# ---------------------------------------------------------------------------
# Metric helpers (all O(n) keyword-overlap — no external deps required)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Lowercase word tokens, strip punctuation, min length 3."""
    return {w for w in re.findall(r"[a-z]{3,}", text.lower())}


def faithfulness_score(answer: str, ground_truth: str) -> float:
    """Fraction of ground-truth keywords present in the answer."""
    gt_tokens = _tokenize(ground_truth)
    if not gt_tokens:
        return 1.0
    ans_tokens = _tokenize(answer)
    overlap = gt_tokens & ans_tokens
    return round(len(overlap) / len(gt_tokens), 3)


def answer_relevancy_score(question: str, answer: str) -> float:
    """Fraction of question keywords found in the answer."""
    q_tokens = _tokenize(question)
    if not q_tokens:
        return 1.0
    ans_tokens = _tokenize(answer)
    overlap = q_tokens & ans_tokens
    return round(len(overlap) / len(q_tokens), 3)


def context_precision_score(
    expected_citations: list[str],
    retrieved_source_ids: list[str],
) -> float:
    """Fraction of expected citations found in the retrieved sources."""
    if not expected_citations:
        return 1.0
    retrieved_set = set(retrieved_source_ids)
    found = sum(1 for cid in expected_citations if cid in retrieved_set)
    return round(found / len(expected_citations), 3)


def context_recall_score(ground_truth: str, context_chunks: list[str]) -> float:
    """Fraction of ground truth terms found in retrieved context."""
    gt_tokens = _tokenize(ground_truth)
    if not gt_tokens:
        return 1.0
    context_text = " ".join(context_chunks)
    context_tokens = _tokenize(context_text)
    found = len(gt_tokens & context_tokens)
    return round(found / len(gt_tokens), 3)


def check_phi_leakage(answer: str) -> tuple[bool, list[str]]:
    """Return (leaked, list_of_pattern_names_matched)."""
    matched: list[str] = []
    for name, pattern in PHI_PATTERNS.items():
        if pattern.search(answer):
            matched.append(name)
    return bool(matched), matched


# ---------------------------------------------------------------------------
# App / test-client setup
# ---------------------------------------------------------------------------

def _build_test_client(chroma_dir: str):
    """Build a FastAPI TestClient with overridden dependencies."""
    from fastapi.testclient import TestClient

    from app.api.dependencies import get_embedder, get_query_controller, get_vector_db
    from app.api.main import create_app
    from app.api.query_controller import QueryController
    from app.embedders.local_embedder import LocalEmbedder
    from app.generators.anthropic_generator import AnthropicGenerator
    from app.vector_db.chroma_db import ChromaVectorDB

    get_vector_db.cache_clear()
    get_embedder.cache_clear()
    get_query_controller.cache_clear()

    db = ChromaVectorDB(persist_directory=chroma_dir)
    embedder = LocalEmbedder()
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    generator = AnthropicGenerator(api_key=api_key, model="claude-haiku-4-5-20250315")
    controller = QueryController(vector_db=db, embedder=embedder, generator=generator)

    app = create_app()
    app.dependency_overrides[get_vector_db] = lambda: db
    app.dependency_overrides[get_embedder] = lambda: embedder
    app.dependency_overrides[get_query_controller] = lambda: controller

    return TestClient(app), db, embedder


def _ingest_sample_data(
    client,
    sample_data: dict[str, Any],
    patient_id: str = "synthetic-patient-001",
) -> None:
    """POST all documents for *patient_id* into the running test app."""
    documents = sample_data["patients"][patient_id]["documents"]
    payload = {
        "documents": [
            {
                "text": doc["text"],
                "source_type": doc["source_type"],
                "source_id": doc["source_id"],
            }
            for doc in documents
        ]
    }
    response = client.post(
        "/api/v1/ingest",
        headers={"Authorization": f"Bearer {patient_id}"},
        json=payload,
    )
    if response.status_code != 200:
        print(f"  [WARN] Ingest returned {response.status_code}: {response.text}")


# ---------------------------------------------------------------------------
# Evaluation runners
# ---------------------------------------------------------------------------

def run_golden_evaluations(
    client,
    golden_items: list[GoldenItem],
) -> list[EvalResult]:
    """Run all golden Q&A pairs through the RAG pipeline and compute metrics."""
    results: list[EvalResult] = []
    for item in golden_items:
        response = client.post(
            "/api/v1/query",
            headers={"Authorization": f"Bearer {item.patient_id}"},
            json={"question": item.question},
        )
        if response.status_code != 200:
            print(f"  [WARN] {item.id} query returned {response.status_code}")
            continue

        data = response.json()
        answer: str = data.get("answer", "")
        retrieved_ids: list[str] = [c["source_id"] for c in data.get("citations", [])]

        phi_leaked, phi_patterns = check_phi_leakage(answer)

        results.append(
            EvalResult(
                id=item.id,
                question=item.question,
                faithfulness=faithfulness_score(answer, item.ground_truth),
                answer_relevancy=answer_relevancy_score(item.question, answer),
                context_precision=context_precision_score(
                    item.expected_citations, retrieved_ids
                ),
                context_recall=context_recall_score(
                    item.ground_truth,
                    [c.get("text_snippet", "") for c in data.get("citations", [])],
                ),
                phi_leaked=phi_leaked,
                phi_patterns=phi_patterns,
            )
        )
    return results


def run_patient_isolation_check(client) -> bool:
    """Query with a non-existent patient token — must return 0 citations."""
    response = client.post(
        "/api/v1/query",
        headers={"Authorization": f"Bearer {ISOLATION_PATIENT_TOKEN}"},
        json={"question": "What was my sleep score?"},
    )
    if response.status_code != 200:
        print(f"  [WARN] Isolation check returned {response.status_code}")
        return False
    data = response.json()
    citations = data.get("citations", [])
    retrieval_count = data.get("metadata", {}).get("retrieval_count", -1)
    return len(citations) == 0 and retrieval_count == 0


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def _fmt(val: float) -> str:
    return f"{val:.3f}"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 3] + "..."


def print_results_table(results: list[EvalResult]) -> None:
    """Print a formatted ASCII table of evaluation results."""
    header = (
        f"{'ID':<{COL_ID}} "
        f"{'Question':<{COL_Q}} "
        f"{'Faithful':>{COL_FAITH}} "
        f"{'Relevancy':>{COL_REL}} "
        f"{'CtxPrec':>{COL_CTX}} "
        f"{'CtxRec':>{COL_CTX}} "
        f"{'PHI':^{COL_PHI}}"
    )
    sep = "-" * TABLE_WIDTH

    print("\n" + sep)
    print(header)
    print(sep)

    for r in results:
        phi_flag = "LEAK!" if r.phi_leaked else "ok"
        print(
            f"{r.id:<{COL_ID}} "
            f"{_truncate(r.question, COL_Q):<{COL_Q}} "
            f"{_fmt(r.faithfulness):>{COL_FAITH}} "
            f"{_fmt(r.answer_relevancy):>{COL_REL}} "
            f"{_fmt(r.context_precision):>{COL_CTX}} "
            f"{_fmt(r.context_recall):>{COL_CTX}} "
            f"{phi_flag:^{COL_PHI}}"
        )

    print(sep)


def print_summary(results: list[EvalResult], isolation_ok: bool) -> None:
    """Print aggregate metrics and checks."""
    if not results:
        print("\n[ERROR] No results to summarise.")
        return

    avg_faith = sum(r.faithfulness for r in results) / len(results)
    avg_rel = sum(r.answer_relevancy for r in results) / len(results)
    avg_ctx = sum(r.context_precision for r in results) / len(results)
    avg_recall = sum(r.context_recall for r in results) / len(results)
    phi_count = sum(1 for r in results if r.phi_leaked)

    print(f"\n{'SUMMARY':=^{TABLE_WIDTH}}")
    print(f"  Total test cases    : {len(results)}")
    print(f"  Avg Faithfulness    : {avg_faith:.3f}  (keyword overlap answer ↔ ground truth)")
    print(f"  Avg Answer Relevancy: {avg_rel:.3f}  (question terms found in answer)")
    print(f"  Avg Context Precision: {avg_ctx:.3f}  (expected citations retrieved)")
    print(f"  Avg Context Recall  : {avg_recall:.3f}  (ground truth terms in context)")
    print(f"  PHI Leakage         : {phi_count} / {len(results)} answers flagged")
    print(f"  Patient Isolation   : {'PASS' if isolation_ok else 'FAIL'}")
    print("=" * TABLE_WIDTH)

    if phi_count > 0:
        print("\n[WARN] PHI patterns detected in answers:")
        for r in results:
            if r.phi_leaked:
                print(f"  {r.id}: {r.phi_patterns}")

    if not isolation_ok:
        print("\n[CRITICAL] Patient isolation check FAILED — cross-patient leakage risk!")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def load_golden_test_set(path: Path) -> list[GoldenItem]:
    """Parse golden_test_set.yaml into GoldenItem list."""
    with open(path) as fh:
        raw = yaml.safe_load(fh)
    items: list[GoldenItem] = []
    for entry in raw:
        items.append(
            GoldenItem(
                id=entry["id"],
                question=entry["question"],
                ground_truth=entry["ground_truth"],
                source_type=entry["source_type"],
                patient_id=entry["patient_id"],
                expected_citations=entry.get("expected_citations", []),
            )
        )
    return items


def main() -> None:
    """Entry point: build client, ingest data, run evaluation, print report."""
    print("HealthStream RAG — RAGAS Evaluation Pipeline")
    print("=" * TABLE_WIDTH)

    print("\n[1/5] Loading golden test set ...")
    golden_items = load_golden_test_set(GOLDEN_TEST_SET_PATH)
    print(f"      {len(golden_items)} test cases loaded from {GOLDEN_TEST_SET_PATH}")

    print("\n[2/5] Loading sample data ...")
    with open(SAMPLE_DATA_PATH) as fh:
        sample_data = json.load(fh)
    patient_count = len(sample_data["patients"])
    print(f"      {patient_count} patients found in {SAMPLE_DATA_PATH}")

    print("\n[3/5] Spinning up FastAPI test client + ingesting data ...")
    with tempfile.TemporaryDirectory() as chroma_dir:
        os.environ["CHROMA_PERSIST_DIRECTORY"] = chroma_dir
        client, _db, _embedder = _build_test_client(chroma_dir)

        _ingest_sample_data(client, sample_data, patient_id="synthetic-patient-001")
        doc_count = len(sample_data["patients"]["synthetic-patient-001"]["documents"])
        print(f"      {doc_count} documents ingested for synthetic-patient-001")

        print("\n[4/5] Running patient isolation check ...")
        isolation_ok = run_patient_isolation_check(client)
        status = "PASS" if isolation_ok else "FAIL"
        print(f"      Patient isolation: {status}")

        print("\n[5/5] Running golden Q&A evaluations ...")
        results = run_golden_evaluations(client, golden_items)
        print(f"      {len(results)} evaluations completed")

    print_results_table(results)
    print_summary(results, isolation_ok)


if __name__ == "__main__":
    main()
