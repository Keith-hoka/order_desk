"""Build the audit pack (sample ids, sheet, verdict template) from the frozen test."""

import json
import sys
from collections import Counter

from order_desk.audit import (
    AUDIT_DIR,
    AUDIT_SEED,
    SAMPLE_IDS_PATH,
    SHEET_PATH,
    VERDICTS_PATH,
    build_pack,
    load_frozen_test,
)
from order_desk.materialize import MANIFEST_PATH


def main() -> None:
    records = load_frozen_test()
    pack = build_pack(records)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    if VERDICTS_PATH.exists():
        existing = [
            json.loads(line)["id"]
            for line in VERDICTS_PATH.read_text(encoding="utf-8").splitlines()
            if line
        ]
        if existing != pack["ids"]:
            sys.exit(
                "REFUSED: data/audit/verdicts.jsonl exists with different ids than the\n"
                "computed sample. Move it aside deliberately if you mean to restart."
            )
        print("verdicts.jsonl exists with matching ids; leaving it untouched")
    else:
        VERDICTS_PATH.write_text(pack["verdicts"], encoding="utf-8")
        print(f"wrote {VERDICTS_PATH} ({len(pack['ids'])} lines)")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    SAMPLE_IDS_PATH.write_text(
        json.dumps(
            {
                "audit_seed": AUDIT_SEED,
                "test_sha256": manifest["splits"]["test"]["sha256"],
                "n": len(pack["ids"]),
                "ids": pack["ids"],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    SHEET_PATH.write_text(pack["sheet"], encoding="utf-8")
    print(f"wrote {SAMPLE_IDS_PATH}")
    print(f"wrote {SHEET_PATH}")

    index = {record["id"]: record["email_class"] for record in records}
    counts = Counter(index[i] for i in pack["ids"])
    print("\ncomposition:")
    for cls, count in sorted(counts.items()):
        print(f"  {cls:<14} {count}")
    print(f"  total          {len(pack['ids'])}")
    print("\ncoverage (min -> got):")
    for name, minimum, got in pack["coverage_rows"]:
        print(f"  {name:<40} {minimum:>3} -> {got:>3}")


if __name__ == "__main__":
    main()
