"""Confidence calibration for the extraction service (Phase 4.5).

Raw per-field confidence under xgrammar piles at ~1.0 with almost no
discrimination (the grammar prunes the token distribution, so logprobs sit
near zero). Calibration learns a monotonic map from raw confidence to
empirical correctness on the val split -- never test, per SPEC eval-purity --
and ECE quantifies the gap before and after.

The calibrator is isotonic regression: non-parametric, monotonic, and it
handles the confidence-piled-at-1.0 shape by mapping the narrow high
interval to its actual correctness rate. It is fit on (confidence, correct)
pairs where "correct" uses the same norm_text equality as the headline
metric -- no new judgment introduced.

The fitted calibrator is an artifact (JSON: sorted x->y knots), loadable at
serving time; this module produces it and the ECE report but does not wire
it into /extract (that is an optional follow-up).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from order_desk.scoring import norm_text


@dataclass(frozen=True)
class ConfidencePair:
    confidence: float
    correct: bool


def field_correct(pred_value: object, gold_value: object) -> bool:
    """Whether a predicted field value matches gold, by the headline's norm_text rule."""
    if pred_value is None or gold_value is None:
        return pred_value is None and gold_value is None
    return norm_text(str(pred_value)) == norm_text(str(gold_value))


def expected_calibration_error(pairs: list[ConfidencePair], n_bins: int = 10) -> dict[str, object]:
    """Binned ECE: weighted mean over bins of |mean confidence - accuracy|."""
    if not pairs:
        return {"ece": 0.0, "n": 0, "bins": []}
    bins: list[list[ConfidencePair]] = [[] for _ in range(n_bins)]
    for pair in pairs:
        # clamp to [0, 1); confidence of exactly 1.0 goes in the last bin
        idx = min(int(pair.confidence * n_bins), n_bins - 1)
        bins[idx].append(pair)
    total = len(pairs)
    ece = 0.0
    bin_report = []
    for i, bucket in enumerate(bins):
        if not bucket:
            continue
        mean_conf = sum(p.confidence for p in bucket) / len(bucket)
        accuracy = sum(1 for p in bucket if p.correct) / len(bucket)
        weight = len(bucket) / total
        gap = abs(mean_conf - accuracy)
        ece += weight * gap
        bin_report.append(
            {
                "bin": i,
                "lo": i / n_bins,
                "hi": (i + 1) / n_bins,
                "count": len(bucket),
                "mean_confidence": round(mean_conf, 4),
                "accuracy": round(accuracy, 4),
                "gap": round(gap, 4),
            }
        )
    return {"ece": round(ece, 6), "n": total, "bins": bin_report}


class IsotonicCalibrator:
    """Monotonic confidence -> calibrated-probability map (isotonic regression)."""

    def __init__(self, x_knots: list[float], y_knots: list[float]) -> None:
        self.x_knots = x_knots
        self.y_knots = y_knots

    @classmethod
    def fit(cls, pairs: list[ConfidencePair]) -> IsotonicCalibrator:
        from sklearn.isotonic import IsotonicRegression

        xs = [p.confidence for p in pairs]
        ys = [1.0 if p.correct else 0.0 for p in pairs]
        model = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
        model.fit(xs, ys)
        # sample the fitted function at the sorted unique inputs as knots
        unique_x = sorted(set(xs))
        knots_y = model.predict(unique_x)
        return cls(list(unique_x), [float(y) for y in knots_y])

    def calibrate(self, confidence: float) -> float:
        """Piecewise-linear interpolation over the stored knots."""
        xs, ys = self.x_knots, self.y_knots
        if not xs:
            return confidence
        if confidence <= xs[0]:
            return ys[0]
        if confidence >= xs[-1]:
            return ys[-1]
        # binary-search the interval
        lo, hi = 0, len(xs) - 1
        while hi - lo > 1:
            mid = (lo + hi) // 2
            if xs[mid] <= confidence:
                lo = mid
            else:
                hi = mid
        x0, x1, y0, y1 = xs[lo], xs[hi], ys[lo], ys[hi]
        if x1 == x0:
            return y0
        t = (confidence - x0) / (x1 - x0)
        return y0 + t * (y1 - y0)

    def to_json(self) -> str:
        return json.dumps({"x_knots": self.x_knots, "y_knots": self.y_knots}, indent=2)

    @classmethod
    def from_json(cls, text: str) -> IsotonicCalibrator:
        data = json.loads(text)
        return cls(data["x_knots"], data["y_knots"])

    def save(self, path: Path) -> None:
        path.write_text(self.to_json(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> IsotonicCalibrator:
        return cls.from_json(path.read_text(encoding="utf-8"))


def apply_calibrator(
    pairs: list[ConfidencePair], calibrator: IsotonicCalibrator
) -> list[ConfidencePair]:
    return [ConfidencePair(calibrator.calibrate(p.confidence), p.correct) for p in pairs]
