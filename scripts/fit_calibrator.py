"""Fit the isotonic calibrator and write the ECE report (4.5b).

Reads results/calibration/val_pairs.jsonl, computes ECE before, fits the
isotonic calibrator, computes ECE after, saves the calibrator artifact and a
markdown report. Val-derived only; the calibrator is pinned for serving use.
"""

import json
from pathlib import Path

from order_desk.calibration import (
    ConfidencePair,
    IsotonicCalibrator,
    apply_calibrator,
    expected_calibration_error,
)

PAIRS = Path("results/calibration/val_pairs.jsonl")
CALIBRATOR = Path("results/calibration/calibrator.json")
REPORT = Path("docs/phase4_calibration.md")


def load_pairs() -> list[ConfidencePair]:
    rows = [json.loads(line) for line in PAIRS.read_text(encoding="utf-8").splitlines() if line]
    return [ConfidencePair(r["confidence"], r["correct"]) for r in rows]


def bin_table(report: dict) -> str:
    lines = ["| bin | range | count | mean conf | accuracy | gap |", "|---|---|---|---|---|---|"]
    for b in report["bins"]:
        lines.append(
            f"| {b['bin']} | {b['lo']:.1f}-{b['hi']:.1f} | {b['count']} | "
            f"{b['mean_confidence']:.4f} | {b['accuracy']:.4f} | {b['gap']:.4f} |"
        )
    return "\n".join(lines)


def main() -> None:
    pairs = load_pairs()
    n_correct = sum(1 for p in pairs if p.correct)
    before = expected_calibration_error(pairs, n_bins=10)
    calibrator = IsotonicCalibrator.fit(pairs)
    after = expected_calibration_error(apply_calibrator(pairs, calibrator), n_bins=10)

    CALIBRATOR.parent.mkdir(parents=True, exist_ok=True)
    calibrator.save(CALIBRATOR)

    overall_acc = n_correct / len(pairs)
    REPORT.write_text(
        f"""# Phase 4.5 — confidence calibration (val split)

Isotonic calibrator fit on {len(pairs)} (confidence, correct) pairs from the
val split's gold-bearing records, scored with the fine-tuned adapter
(qwen3-4b-sft-full-r8) via the vLLM endpoint, xgrammar-constrained. Val only
-- never test. "Correct" uses the headline's norm_text equality.

## Summary

- Pairs: {len(pairs)}, overall field accuracy: {overall_acc:.4f}
- **ECE before calibration: {before["ece"]:.4f}**
- **ECE after calibration: {after["ece"]:.4f}**

## The xgrammar confidence problem, quantified

Raw confidence under xgrammar piles near 1.0, so most fields fall in the top
bin. The binned table below shows the actual distribution -- if nearly all
mass sits in the 0.9-1.0 bin, the raw scores carry little triage signal, and
the calibrator's job is to map that narrow high interval to its true
correctness rate rather than to spread a well-distributed score.

### Before calibration

{bin_table(before)}

### After calibration

{bin_table(after)}

## Interpretation

The calibrator is a monotonic map from raw confidence to empirical
correctness, saved as sorted knots ({CALIBRATOR}) and loadable at serving
time with pure-Python interpolation (no sklearn dependency in the service).
It is not wired into /extract in this phase -- that is an optional follow-up;
here it is produced and pinned as the basis for HITL review prioritization
(Phase 7), where a reviewer should see the lowest-calibrated-confidence
fields first.

Because the adapter is highly accurate on val and xgrammar inflates
confidence, ECE is expected to be modest before calibration; the value is in
exposing the confidence distribution honestly and providing a principled
mapping, not in a dramatic ECE reduction.
""",
        encoding="utf-8",
    )
    print(f"ECE before: {before['ece']:.4f}  after: {after['ece']:.4f}")
    print(f"overall accuracy: {overall_acc:.4f} over {len(pairs)} pairs")
    print(f"wrote {CALIBRATOR}")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    main()
