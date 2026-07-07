"""Route evaluation over the frozen sets, reusing Phase 2 classification (4.5).

Offline: reads records and the committed gpt-4o-mini classification
predictions, folds through the route map, prints routing accuracy vs
classification accuracy and route confusion for synthetic and human. Also
lists which human order-class emails trip the blend ask (qualitative).
"""

import json
from pathlib import Path

from order_desk.harness import load_source
from order_desk.pipeline.policy import detect_product_inquiry
from order_desk.pipeline.validator import route_gap, route_report


def load_predictions(name: str, source: str) -> dict[str, dict]:
    p = Path(f"results/predictions/{name}_{source}.jsonl")
    rows = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line]
    return {r["id"]: r for r in rows}


def show(source: str) -> None:
    records, _ = load_source(source)
    preds = load_predictions("gpt-4o-mini", source)
    report = route_report(records, preds)
    print(f"\n=== {source} (n={report['n']}) ===")
    print(f"  routing accuracy:        {report['routing_accuracy']:.4f}")
    print(f"  classification accuracy: {report['classification_accuracy']:.4f}")
    print(f"  route gap (harmless misclass): {route_gap(report):+.4f}")
    print(f"  invalid routes: {report['invalid_route']}")
    if report["route_confusion"]:
        print("  route confusion:")
        for k, v in report["route_confusion"].items():
            print(f"    {k}: {v}")


def blend_asks_on_human() -> None:
    records, _ = load_source("human")
    print("\n=== human blend-ask (qualitative; order-class emails tripping the heuristic) ===")
    hits = 0
    for r in records:
        if r["email_class"] in ("new_order", "amendment") and detect_product_inquiry(r["body"]):
            hits += 1
            print(f"  {r['id']} [{r['email_class']}] {r['subject']!r}")
    print(f"  {hits} order-class emails flagged")


def main() -> None:
    show("synthetic")
    show("human")
    blend_asks_on_human()


if __name__ == "__main__":
    main()
