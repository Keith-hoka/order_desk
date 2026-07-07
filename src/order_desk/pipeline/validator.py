"""Routing evaluation for the pipeline (Phase 5).

Folds classification predictions through the deterministic route map and
scores routing against gold. Reuses the Phase 2 gpt-4o-mini classification
predictions -- the pipeline's classify node is the same prompt (snapshot-
pinned), same model, same structured-outputs enum, so those predictions are
exactly what the classify node produces. Fully offline; no network, no cost.

The key quantity is routing accuracy vs classification accuracy: because
several classes map to one route (new_order and amendment both -> EXTRACT), a
class error that preserves the route is not a routing error. Routing accuracy
>= classification accuracy, and the gap measures how many misclassifications
are routing-harmless.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from order_desk.pipeline.policy import RouteDecision, route_for_class
from order_desk.schemas import EmailClass


def _route_of(class_value: str | None) -> RouteDecision | None:
    if class_value is None:
        return None
    try:
        return route_for_class(EmailClass(class_value))
    except ValueError:
        return None  # unparseable label -> no route


def route_report(
    records: list[dict[str, Any]], predictions: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Routing accuracy, classification accuracy, and route confusion."""
    n = 0
    route_correct = 0
    class_correct = 0
    invalid_route = 0
    confusion: Counter[tuple[str, str]] = Counter()
    for record in records:
        rid = record["id"]
        if rid not in predictions:
            continue
        n += 1
        gold_class = record["email_class"]
        pred_class = predictions[rid].get("classification")
        gold_route = _route_of(gold_class)
        pred_route = _route_of(pred_class)
        if pred_class == gold_class:
            class_correct += 1
        if pred_route is None:
            invalid_route += 1
        elif pred_route == gold_route:
            route_correct += 1
        gr = gold_route.value if gold_route else "none"
        pr = pred_route.value if pred_route else "invalid"
        if gr != pr:
            confusion[(gr, pr)] += 1
    return {
        "n": n,
        "routing_accuracy": route_correct / n if n else 0.0,
        "classification_accuracy": class_correct / n if n else 0.0,
        "invalid_route": invalid_route,
        "route_confusion": {f"{g}->{p}": c for (g, p), c in sorted(confusion.items())},
    }


def route_gap(report: dict[str, Any]) -> float:
    """Routing-harmless misclassification rate: how much route beats class."""
    return report["routing_accuracy"] - report["classification_accuracy"]
