"""Evaluate retrieval recall against a small labeled question set."""

import argparse
import json
from pathlib import Path

from pipeline.retrieve import retrieve


def load_cases(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        cases = json.load(file)
    if not isinstance(cases, list):
        raise ValueError("Benchmark must be a JSON list.")
    return cases


def matches_expected(hit: dict, case: dict) -> bool:
    expected_source = case["source"]
    expected_pages = case.get("pages", [case["page"]])
    return (
        hit["source"] == expected_source
        and hit["page"] in expected_pages
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--benchmark",
        type=Path,
        default=Path("evaluation/benchmark.json"),
    )
    args = parser.parse_args()

    cases = load_cases(args.benchmark)
    if not cases:
        raise ValueError("Benchmark is empty.")

    hits_by_k = {3: 0, 5: 0}
    for case in cases:
        hits = retrieve(case["question"], k=5)
        ranks = {
            k: next(
                (rank for rank, hit in enumerate(hits[:k], start=1)
                 if matches_expected(hit, case)),
                None,
            )
            for k in hits_by_k
        }
        for k, rank in ranks.items():
            if rank is not None:
                hits_by_k[k] += 1
        print(
            f"{case['question']}\n"
            f"  expected: {case['source']} page(s) {case.get('pages', [case['page']])}\n"
            f"  Recall@3: {'PASS (rank ' + str(ranks[3]) + ')' if ranks[3] else 'MISS'}\n"
            f"  Recall@5: {'PASS (rank ' + str(ranks[5]) + ')' if ranks[5] else 'MISS'}"
        )

    total = len(cases)
    print(f"\nRecall@3: {hits_by_k[3]}/{total} = {hits_by_k[3] / total:.1%}")
    print(f"Recall@5: {hits_by_k[5]}/{total} = {hits_by_k[5] / total:.1%}")


if __name__ == "__main__":
    main()
