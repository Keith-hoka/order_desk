"""Evaluate blended over-extraction: base vs flywheel adapter (Phase 9.5, Gate 1).

Runs both adapters over the held-out blended slice and reports line-item
precision and recall, split by case type. The flywheel adapter should raise
precision on non-counter cases (it stops pulling the inquired product into the
order -- less over-extraction, fewer false-positive line items) while holding
recall on counter-examples (it still extracts genuinely-ordered products that
happen to be phrased as questions -- no over-suppression). Requires the LoRA
endpoint serving both adapters.
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from order_desk.baseline import parse_extraction
from order_desk.extract_client import VLLMExtractClient
from order_desk.flywheel.blended import case_to_record, generate_blended_cases
from order_desk.schemas import ExtractedOrder
from order_desk.scoring import score_extraction

BASE = "qwen3-4b-sft-full-r8"
FLYWHEEL = "qwen3-4b-sft-flywheel-r8"
FLYWHEEL_500 = "qwen3-4b-sft-flywheel_500-r8"


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


@dataclass
class Agg:
    gold_items: int = 0
    pred_items: int = 0
    matched: int = 0

    def add(self, tally) -> None:
        self.gold_items += tally.alignment.gold_items
        self.pred_items += tally.alignment.pred_items
        self.matched += tally.alignment.matched

    @property
    def precision(self) -> float:
        return self.matched / self.pred_items if self.pred_items else 0.0

    @property
    def recall(self) -> float:
        return self.matched / self.gold_items if self.gold_items else 0.0


def evaluate(client: VLLMExtractClient, cases: list[dict]) -> dict[str, Agg]:
    non_counter, counter = Agg(), Agg()
    for case in cases:
        gold = ExtractedOrder.model_validate(case["gold_extraction"])
        result = client.extract(case["subject"], case["body"])
        pred, _ = parse_extraction(result.raw)  # None on parse failure
        tally = score_extraction(gold, pred)
        bucket = counter if case["is_counter_example"] else non_counter
        bucket.add(tally)
    return {"non_counter": non_counter, "counter": counter}


def main() -> None:
    load_dotenv()
    base_url = os.environ.get("VLLM_BASE_URL")
    api_key = os.environ.get("VLLM_API_KEY", "EMPTY")
    if not base_url:
        sys.exit("VLLM_BASE_URL not set")

    # regenerate the held-out slice deterministically, carrying the counter flag
    slice_cases = generate_blended_cases(n=50, seed=70131, id_prefix="BLD-EVL")
    cases = []
    for c in slice_cases:
        rec = case_to_record(c)
        rec["is_counter_example"] = c.is_counter_example
        cases.append(rec)

    n_nc = sum(1 for c in cases if not c["is_counter_example"])
    n_c = len(cases) - n_nc
    print(f"blended slice: {len(cases)} ({n_nc} non-counter, {n_c} counter)\n")

    results = {}
    for adapter in (BASE, FLYWHEEL, FLYWHEEL_500):
        print(f"running {adapter} ...", flush=True)
        client = VLLMExtractClient(adapter, base_url, api_key=api_key)
        results[adapter] = evaluate(client, cases)

    b = results[BASE]
    ff = results[FLYWHEEL]
    f5 = results[FLYWHEEL_500]

    def row(label: str, bv: float, fv: float, f5v: float) -> None:
        print(f"{label:<26}{bv:>13.4f}{fv:>15.4f}{f5v:>16.4f}")

    print("\n" + "=" * 70)
    print(f"{'metric':<26}{'base full-r8':>13}{'flywheel-full':>15}{'flywheel-500':>16}")
    print("-" * 70)
    row(
        "non-counter precision",
        b["non_counter"].precision,
        ff["non_counter"].precision,
        f5["non_counter"].precision,
    )
    row(
        "non-counter recall",
        b["non_counter"].recall,
        ff["non_counter"].recall,
        f5["non_counter"].recall,
    )
    row("counter recall", b["counter"].recall, ff["counter"].recall, f5["counter"].recall)
    row(
        "counter precision",
        b["counter"].precision,
        ff["counter"].precision,
        f5["counter"].precision,
    )
    print("=" * 70)

    for name, r in [("flywheel-full", ff), ("flywheel-500", f5)]:
        gain = r["non_counter"].precision - b["non_counter"].precision
        drop = b["counter"].recall - r["counter"].recall
        gate1 = gain > 0 and drop < 0.05
        print(
            f"{name}: precision gain {gain:+.4f}, counter recall {-drop:+.4f} "
            f"-> Gate 1 {'PASS' if gate1 else 'FAIL'}"
        )


if __name__ == "__main__":
    main()
