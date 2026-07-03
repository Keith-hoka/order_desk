"""Validate verdicts.jsonl structure and report audit progress."""

import json
import sys

from order_desk.audit import SAMPLE_IDS_PATH, VERDICTS_PATH
from order_desk.verdicts import VerdictError, parse_verdicts, progress


def main() -> None:
    sample = json.loads(SAMPLE_IDS_PATH.read_text(encoding="utf-8"))
    try:
        verdicts = parse_verdicts(VERDICTS_PATH.read_text(encoding="utf-8"), sample["ids"])
    except VerdictError as exc:
        sys.exit(f"INVALID: {exc}")

    report = progress(verdicts)
    print(f"progress: {report.filled}/{report.total} filled")
    if report.partial_lines:
        print(f"  PARTIAL lines (one boolean still null): {report.partial_lines}")
    if report.pending_lines:
        head = ", ".join(str(n) for n in report.pending_lines[:8])
        more = "" if len(report.pending_lines) <= 8 else f" (+{len(report.pending_lines) - 8} more)"
        print(f"  next pending lines: {head}{more}")
    print(
        f"realistic: {report.realistic_true} true / {report.realistic_false} false   "
        f"labels_correct: {report.labels_true} true / {report.labels_false} false"
    )
    if report.quirk_tags:
        tags = "  ".join(f"{tag}={count}" for tag, count in sorted(report.quirk_tags.items()))
        print(f"quirk tags: {tags}")
    if report.findings:
        print(f"label findings ({len(report.findings)}): {', '.join(report.findings)}")
    if report.unrealistic:
        print(f"unrealistic ({len(report.unrealistic)}): {', '.join(report.unrealistic)}")
    if report.partial_lines:
        sys.exit(1)


if __name__ == "__main__":
    main()
