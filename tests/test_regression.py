import json
from pathlib import Path

from order_desk.flywheel.regression import (
    check_regression,
    read_headline_f1,
)


def _write_report(path: Path, f1: float) -> None:
    path.write_text(json.dumps({"extraction": {"headline": {"f1": f1}}}), encoding="utf-8")


def _setup(tmp_path: Path, baseline_f1: dict, candidate_f1: dict, tolerance: float = 0.01):
    reports = tmp_path / "reports"
    reports.mkdir()
    registry = tmp_path / "registry.json"
    sources = {}
    for src in baseline_f1:
        _write_report(reports / f"base_{src}.json", baseline_f1[src])
        _write_report(reports / f"cand_{src}.json", candidate_f1[src])
        sources[src] = {
            "baseline_report": f"base_{src}.json",
            "candidate_report": f"cand_{src}.json",
        }
    registry.write_text(
        json.dumps({"regression_gate": {"tolerance": tolerance, "sources": sources}}),
        encoding="utf-8",
    )
    return registry, reports


def test_read_headline_f1(tmp_path: Path) -> None:
    p = tmp_path / "r.json"
    _write_report(p, 0.9418)
    assert read_headline_f1(p) == 0.9418


def test_no_regression_passes(tmp_path: Path) -> None:
    # candidate slightly higher -> pass
    reg, reps = _setup(
        tmp_path, {"synthetic": 0.99, "human": 0.95}, {"synthetic": 0.995, "human": 0.96}
    )
    result = check_regression(reg, reps)
    assert result.passed
    assert all(not r.regressed for r in result.results)


def test_within_tolerance_passes(tmp_path: Path) -> None:
    # candidate drops 0.009 < tolerance 0.01 -> pass (the Phase 9 human case)
    reg, reps = _setup(tmp_path, {"human": 0.9508}, {"human": 0.9418}, tolerance=0.01)
    result = check_regression(reg, reps)
    assert result.passed
    assert result.results[0].delta < 0  # dropped, but within tolerance
    assert not result.results[0].regressed


def test_beyond_tolerance_fails(tmp_path: Path) -> None:
    # candidate drops 0.05 > tolerance 0.01 -> fail
    reg, reps = _setup(tmp_path, {"human": 0.95}, {"human": 0.90}, tolerance=0.01)
    result = check_regression(reg, reps)
    assert not result.passed
    assert result.results[0].regressed


def test_regression_on_one_source_fails_gate(tmp_path: Path) -> None:
    # synthetic fine, human regresses -> whole gate fails
    reg, reps = _setup(
        tmp_path,
        {"synthetic": 0.99, "human": 0.95},
        {"synthetic": 0.99, "human": 0.88},
        tolerance=0.01,
    )
    result = check_regression(reg, reps)
    assert not result.passed
    regressed = [r.source for r in result.results if r.regressed]
    assert regressed == ["human"]


def test_real_registry_flywheel_passes() -> None:
    # the actual committed registry + reports: flywheel vs base, should PASS
    result = check_regression()
    assert result.passed  # Phase 9 decision: within tolerance on both sources
    by_source = {r.source: r for r in result.results}
    assert "synthetic" in by_source
    assert "human" in by_source
    # human dropped but within tolerance
    assert by_source["human"].delta < 0
    assert not by_source["human"].regressed
