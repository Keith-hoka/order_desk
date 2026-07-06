"""Aggregate the data-scaling curve and rank ablation from adapter eval reports."""

import json
from pathlib import Path

REPORTS = Path("results/reports")

CURVE = [
    "qwen3-4b-sft-500-r16-xgrammar",
    "qwen3-4b-sft-1000-r16-xgrammar",
    "qwen3-4b-sft-2000-r16-xgrammar",
    "qwen3-4b-sft-full-r16",
]
RANKS = ["qwen3-4b-sft-full-r8-xgrammar", "qwen3-4b-sft-full-r16", "qwen3-4b-sft-full-r32-xgrammar"]
REFS = {"gpt-4o-mini": "gpt-4o-mini", "qwen3-4b baseline": "qwen3-4b-instruct-2507-xgrammar"}


def row(name: str) -> dict | None:
    path = REPORTS / f"{name}_synthetic.json"
    if not path.exists():
        return None
    r = json.loads(path.read_text(encoding="utf-8"))
    ex = r["extraction"]
    it = r["item_semantics"]
    return {
        "headline_f1": ex["headline"]["f1"],
        "span_gap": it["span_gap"],
        "product_exact": it["product_exact_rate"],
        "alignment_f1": ex["alignment"]["f1"],
        "halluc": ex["headline"]["hallucination_rate"],
        "parse_rate": ex["validity"]["parse_rate"],
    }


def show(title: str, names: list[str], labeller=lambda n: n) -> None:
    print(f"\n{title}")
    print(
        f"  {'run':<26} {'headline':>9} {'span_gap':>9} {'prod_ex':>8} "
        f"{'align':>7} {'halluc':>7} {'parse':>7}"
    )
    for name in names:
        r = row(name)
        if r is None:
            print(f"  {labeller(name):<26} (missing)")
            continue
        print(
            f"  {labeller(name):<26} {r['headline_f1']:>9.4f} {r['span_gap']:>9.4f} "
            f"{r['product_exact']:>8.4f} {r['alignment_f1']:>7.4f} "
            f"{r['halluc']:>7.4f} {r['parse_rate']:>7.4f}"
        )


def main() -> None:
    sizes = {
        "qwen3-4b-sft-500-r16-xgrammar": "500",
        "qwen3-4b-sft-1000-r16-xgrammar": "1000",
        "qwen3-4b-sft-2000-r16-xgrammar": "2000",
        "qwen3-4b-sft-full-r16": "full (3600)",
    }
    ranks = {
        "qwen3-4b-sft-full-r8-xgrammar": "r8",
        "qwen3-4b-sft-full-r16": "r16",
        "qwen3-4b-sft-full-r32-xgrammar": "r32",
    }
    show("data-scaling curve (rank 16)", CURVE, lambda n: sizes[n])
    show("rank ablation (full data)", RANKS, lambda n: ranks[n])
    show("references", list(REFS.values()), lambda n: next(k for k, v in REFS.items() if v == n))


if __name__ == "__main__":
    main()
