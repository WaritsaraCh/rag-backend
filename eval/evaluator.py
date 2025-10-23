"""
LLM/RAG evaluation utilities.
- Runs prompts through the model
- Computes simple metrics: exact match, token F1, embedding cosine similarity
- Supports LLM-only and RAG modes
"""

import time
import json
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer

from utils.llm import generate_answer
from database.operations import retrieve_docs
from config.settings import get_config


def normalize_text(s: str) -> str:
    return (s or "").strip().lower()


def tokenize(s: str) -> List[str]:
    return [t for t in normalize_text(s).split() if t]


def token_f1(pred: str, ref: str) -> Dict[str, float]:
    p_tokens = tokenize(pred)
    r_tokens = tokenize(ref)
    if not p_tokens and not r_tokens:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not p_tokens or not r_tokens:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    p_set = set(p_tokens)
    r_set = set(r_tokens)
    inter = len(p_set & r_set)
    precision = inter / len(p_set)
    recall = inter / len(r_set)
    if precision + recall == 0:
        f1 = 0.0
    else:
        f1 = 2 * precision * recall / (precision + recall)
    return {"precision": precision, "recall": recall, "f1": f1}


class EmbeddingSim:
    def __init__(self, model_name: str):
        self.model = SentenceTransformer(model_name)
    
    def cosine(self, a: str, b: str) -> float:
        embeddings = self.model.encode([a, b], normalize_embeddings=True)
        v1, v2 = embeddings[0], embeddings[1]
        return float(np.dot(v1, v2))


def evaluate_one(sample: Dict[str, Any], mode: str, embedder: EmbeddingSim) -> Dict[str, Any]:
    """Evaluate a single sample.
    sample: {id, question, reference_answer, use_retrieval?}
    mode: 'llm' or 'rag'
    """
    q = sample.get("question", "")
    ref = sample.get("reference_answer", "")
    use_retrieval = sample.get("use_retrieval", mode == "rag")

    # Prepare docs and history
    docs = []
    history = []
    if mode == "rag" and use_retrieval:
        try:
            docs = retrieve_docs(q)
        except Exception as e:
            print(f"⚠️  Retrieval failed for '{q}': {e}. Falling back to LLM-only.")
            docs = []

    start = time.time()
    ans = generate_answer(q, docs, history)
    latency = time.time() - start

    exact = 1.0 if normalize_text(ans) == normalize_text(ref) else 0.0
    tf1 = token_f1(ans, ref)
    cos = embedder.cosine(ans, ref) if ref else 0.0

    return {
        "id": sample.get("id"),
        "question": q,
        "reference_answer": ref,
        "answer": ans,
        "latency_sec": latency,
        "metrics": {
            "exact_match": exact,
            "token_f1": tf1,
            "embedding_cosine": cos,
        }
    }


def summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(results)
    if n == 0:
        return {"count": 0}
    exact = np.mean([r["metrics"]["exact_match"] for r in results])
    f1 = np.mean([r["metrics"]["token_f1"]["f1"] for r in results])
    prec = np.mean([r["metrics"]["token_f1"]["precision"] for r in results])
    rec = np.mean([r["metrics"]["token_f1"]["recall"] for r in results])
    cos = np.mean([r["metrics"]["embedding_cosine"] for r in results])
    lat = np.mean([r["latency_sec"] for r in results])
    return {
        "count": n,
        "exact_match": exact,
        "token_precision": prec,
        "token_recall": rec,
        "token_f1": f1,
        "embedding_cosine": cos,
        "avg_latency_sec": lat,
    }


def evaluate_dataset(dataset: List[Dict[str, Any]], mode: str = "llm") -> Dict[str, Any]:
    cfg = get_config()
    embedder = EmbeddingSim(getattr(cfg, "EMBEDDING_MODEL", "BAAI/bge-m3"))
    results = [evaluate_one(s, mode, embedder) for s in dataset]
    summary = summarize(results)
    return {"mode": mode, "summary": summary, "results": results}


def load_dataset(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_report(report: Dict[str, Any], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)