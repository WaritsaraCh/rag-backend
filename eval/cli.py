#!/usr/bin/env python3
"""
CLI to evaluate the LLM/RAG pipeline.
Usage examples:
- LLM-only:  python eval/cli.py --dataset eval/dataset_sample.json --mode llm
- RAG eval:  python eval/cli.py --dataset eval/dataset_sample.json --mode rag
"""

import argparse
import os
from eval.evaluator import load_dataset, evaluate_dataset, save_report


def main():
    parser = argparse.ArgumentParser(description="Evaluate LLM/RAG responses")
    parser.add_argument("--dataset", required=True, help="Path to dataset JSON")
    parser.add_argument("--mode", choices=["llm", "rag"], default="llm", help="Evaluation mode")
    parser.add_argument("--out", default=None, help="Path to save JSON report")

    args = parser.parse_args()

    dataset = load_dataset(args.dataset)
    report = evaluate_dataset(dataset, mode=args.mode)

    # Print summary
    s = report["summary"]
    print("\nEvaluation Summary")
    print("==================")
    print(f"Samples: {s['count']}")
    print(f"Exact match: {s['exact_match']:.3f}")
    print(f"Token F1: {s['token_f1']:.3f} (P={s['token_precision']:.3f}, R={s['token_recall']:.3f})")
    print(f"Embedding cosine: {s['embedding_cosine']:.3f}")
    print(f"Avg latency (sec): {s['avg_latency_sec']:.2f}")

    # Save report
    out_path = args.out or os.path.join(os.path.dirname(args.dataset), f"report_{args.mode}.json")
    save_report(report, out_path)
    print(f"\nSaved detailed report to: {out_path}")


if __name__ == "__main__":
    main()