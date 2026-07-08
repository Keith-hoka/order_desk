"""CI eval-regression gate (Phase 10).

Automates the no-regression decision from Phase 9's Gate 2: a candidate adapter
must not drop headline F1 below the baseline minus a tolerance, on each frozen
eval source. The gate reads committed eval reports (the source of truth) rather
than re-running the adapter -- eval is expensive and belongs in an offline run,
while the pass/fail judgement is cheap and belongs in CI. If committed reports
show a regression beyond tolerance, the gate fails the build.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REPORTS_DIR = Path("results/reports")
REGISTRY = Path("data/flywheel/adapter_registry.json")


@dataclass
class SourceResult:
    source: str
    baseline_f1: float
    candidate_f1: float
    tolerance: float

    @property
    def delta(self) -> float:
        return self.candidate_f1 - self.baseline_f1

    @property
    def regressed(self) -> bool:
        return self.candidate_f1 < self.baseline_f1 - self.tolerance


@dataclass
class GateResult:
    results: list[SourceResult]

    @property
    def passed(self) -> bool:
        return not any(r.regressed for r in self.results)


def read_headline_f1(report_path: Path) -> float:
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return float(data["extraction"]["headline"]["f1"])


def check_regression(registry_path: Path = REGISTRY, reports_dir: Path = REPORTS_DIR) -> GateResult:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    gate = registry["regression_gate"]
    tolerance = float(gate["tolerance"])

    results: list[SourceResult] = []
    for source, cfg in gate["sources"].items():
        baseline_f1 = read_headline_f1(reports_dir / cfg["baseline_report"])
        candidate_f1 = read_headline_f1(reports_dir / cfg["candidate_report"])
        results.append(
            SourceResult(
                source=source,
                baseline_f1=baseline_f1,
                candidate_f1=candidate_f1,
                tolerance=tolerance,
            )
        )
    return GateResult(results=results)


def format_report(gate: GateResult) -> str:
    lines = ["eval-regression gate", "=" * 52]
    lines.append(f"{'source':<12}{'baseline':>10}{'candidate':>12}{'delta':>10}{'':>8}")
    for r in gate.results:
        flag = "REGRESS" if r.regressed else "ok"
        lines.append(
            f"{r.source:<12}{r.baseline_f1:>10.4f}{r.candidate_f1:>12.4f}{r.delta:>+10.4f}{flag:>8}"
        )
    lines.append("=" * 52)
    lines.append(f"tolerance: {gate.results[0].tolerance:.4f}" if gate.results else "")
    lines.append(f"gate: {'PASS' if gate.passed else 'FAIL'}")
    return "\n".join(lines)
