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


def matched_pages(hits: list[dict], case: dict) -> set[int]:
    expected_source = case["source"]
    expected_pages = set(case.get("pages", [case["page"]]))
    return {
        hit["page"]
        for hit in hits
        if hit["source"] == expected_source and hit["page"] in expected_pages
    }


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
        ranks = {}
        for k in hits_by_k:
            top_hits = hits[:k]
            required_pages = set(case.get("required_pages", []))
            if required_pages:
                ranks[k] = (
                    k
                    if required_pages.issubset(matched_pages(top_hits, case))
                    else None
                )
            else:
                ranks[k] = next(
                    (rank for rank, hit in enumerate(top_hits, start=1)
                     if matches_expected(hit, case)),
                    None,
                )
        for k, rank in ranks.items():
            if rank is not None:
                hits_by_k[k] += 1
        expected = case.get("required_pages", case.get("pages", [case["page"]]))
        print(
            f"{case['question']}\n"
            f"  expected: {case['source']} page(s) {expected}\n"
            f"  Recall@3: {'PASS (rank ' + str(ranks[3]) + ')' if ranks[3] else 'MISS'}\n"
            f"  Recall@5: {'PASS (rank ' + str(ranks[5]) + ')' if ranks[5] else 'MISS'}"
        )

    total = len(cases)
    print(f"\nRecall@3: {hits_by_k[3]}/{total} = {hits_by_k[3] / total:.1%}")
    print(f"Recall@5: {hits_by_k[5]}/{total} = {hits_by_k[5] / total:.1%}")


if __name__ == "__main__":
    main()
