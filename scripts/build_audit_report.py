"""Generate docs/audit_report.md from the filled verdict file."""

import json
import sys
from pathlib import Path

from order_desk.audit import SAMPLE_IDS_PATH, VERDICTS_PATH, load_frozen_test
from order_desk.audit_report import build_report
from order_desk.verdicts import VerdictError, parse_verdicts

REPORT_PATH = Path("docs/audit_report.md")


def main() -> None:
    sample = json.loads(SAMPLE_IDS_PATH.read_text(encoding="utf-8"))
    records = load_frozen_test()
    try:
        verdicts = parse_verdicts(VERDICTS_PATH.read_text(encoding="utf-8"), sample["ids"])
    except VerdictError as exc:
        sys.exit(f"INVALID: {exc}")
    try:
        report = build_report(records, verdicts)
    except RuntimeError as exc:
        sys.exit(f"REFUSED: {exc}")

    REPORT_PATH.write_text(report["markdown"], encoding="utf-8")

    print("per-class realism:")
    for cls, (true_count, total) in sorted(report["per_class"].items()):
        print(f"  {cls:<14} {true_count}/{total}")
    print(f"stratum rows: {len(report['stratum_rows'])}")
    flagged = [(n, s, f) for n, s, f in report["stratum_rows"] if f]
    if flagged:
        print("strata containing unrealistic records:")
        for name, sampled_n, false_n in flagged:
            print(f"  {name:<40} {false_n}/{sampled_n}")
    print("tag counts:")
    for (tag, qualifier), count in sorted(report["tag_counts"].items()):
        print(f"  {tag:<12} {qualifier:<14} {count}")
    if report["protocol_flags"]:
        print("protocol flags:")
        for record_id, notes in report["protocol_flags"]:
            print(f"  {record_id}: {notes}")
    print(f"\nunrealistic dossier ({len(report['evidence'])}):")
    for item in report["evidence"]:
        print("=" * 72)
        print(f"{item['id']}  layout={item['layout']}  po={item['po_placement']}")
        print(f"flags: {', '.join(item['flags']) or '—'}")
        for line in item["items"]:
            print(f"  - {line}")
        print(f"notes: {item['notes']}")
        print(f"Subject: {item['subject']}")
        print("-" * 72)
        print(item["body"])
    print(f"\nwrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
