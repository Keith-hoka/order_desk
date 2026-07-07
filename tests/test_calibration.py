import random

from order_desk.calibration import (
    ConfidencePair,
    IsotonicCalibrator,
    apply_calibrator,
    expected_calibration_error,
    field_correct,
)


def test_field_correct_uses_norm_text() -> None:
    assert field_correct("PO-1", "PO-1")
    assert field_correct("PO-1 ", "PO-1")  # norm_text strips
    assert not field_correct("PO-1", "PO-2")
    assert field_correct(None, None)
    assert not field_correct("x", None)
    assert not field_correct(None, "x")
    assert field_correct(12, 12)  # coerced to str


def test_ece_zero_for_perfectly_calibrated() -> None:
    # Confidence exactly equals correctness rate in each bin -> ECE ~ 0.
    pairs = []
    for conf, rate in [(0.15, 0.15), (0.55, 0.55), (0.95, 0.95)]:
        n = 1000
        n_correct = int(round(rate * n))
        for i in range(n):
            pairs.append(ConfidencePair(conf, i < n_correct))
    report = expected_calibration_error(pairs, n_bins=10)
    assert report["ece"] < 0.01  # near-zero for a calibrated set


def test_ece_large_for_miscalibrated() -> None:
    # High confidence, low actual accuracy -> large ECE.
    pairs = [ConfidencePair(0.99, i < 500) for i in range(1000)]  # 0.99 conf, 0.5 acc
    report = expected_calibration_error(pairs, n_bins=10)
    assert report["ece"] > 0.4


def test_isotonic_maps_confidence_to_empirical_rate() -> None:
    # Confidence 0.9 but only 60% correct: calibrator should pull it down.
    rng = random.Random(0)
    pairs = [ConfidencePair(0.9, rng.random() < 0.6) for _ in range(2000)]
    calibrator = IsotonicCalibrator.fit(pairs)
    calibrated = calibrator.calibrate(0.9)
    assert 0.5 < calibrated < 0.7  # near the true 0.6 rate


def test_isotonic_is_monotonic() -> None:
    # Build data where higher confidence really is more often correct.
    rng = random.Random(1)
    pairs = []
    for _ in range(3000):
        conf = rng.random()
        pairs.append(ConfidencePair(conf, rng.random() < conf))  # P(correct) = conf
    calibrator = IsotonicCalibrator.fit(pairs)
    grid = [0.1, 0.3, 0.5, 0.7, 0.9]
    calibrated = [calibrator.calibrate(x) for x in grid]
    assert calibrated == sorted(calibrated)  # monotonic non-decreasing


def test_calibration_reduces_ece() -> None:
    rng = random.Random(2)
    # miscalibrated: confidence 0.95 but P(correct)=0.7
    pairs = [ConfidencePair(0.95, rng.random() < 0.7) for _ in range(2000)]
    before = expected_calibration_error(pairs)["ece"]
    calibrator = IsotonicCalibrator.fit(pairs)
    after = expected_calibration_error(apply_calibrator(pairs, calibrator))["ece"]
    assert after < before
    assert after < 0.05


def test_calibrator_json_roundtrip() -> None:
    pairs = [ConfidencePair(0.5 + 0.4 * (i % 2), i % 3 == 0) for i in range(100)]
    calibrator = IsotonicCalibrator.fit(pairs)
    restored = IsotonicCalibrator.from_json(calibrator.to_json())
    for x in (0.1, 0.5, 0.9):
        assert abs(calibrator.calibrate(x) - restored.calibrate(x)) < 1e-9
