"""Pack the human slice into .eml files for ingest testing (Phase 6).

Writes data/human_eml/*.eml from the human records with mixed realism
(decision ii): most faithful, some with signatures, some HTML, and a couple of
constructed replies that quote a prior question -- exercising the
standardization layer and the reply-history ask on realistic content.
"""

import json
from pathlib import Path

from order_desk.ingest.pack import (
    pack_faithful,
    pack_html,
    pack_reply,
    pack_with_signature,
)

HUMAN = Path("data/human/test_human.jsonl")
OUT = Path("data/human_eml")


def main() -> None:
    records = [json.loads(line) for line in HUMAN.read_text(encoding="utf-8").splitlines() if line]
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.eml"):
        old.unlink()

    counts = {"faithful": 0, "signature": 0, "html": 0, "reply": 0}
    for i, record in enumerate(records):
        rid = record["id"]
        # deterministic mix: every 5th signature, every 7th html, rest faithful
        if i % 7 == 3:
            raw = pack_html(record)
            counts["html"] += 1
        elif i % 5 == 2:
            raw = pack_with_signature(record)
            counts["signature"] += 1
        else:
            raw = pack_faithful(record)
            counts["faithful"] += 1
        (OUT / f"{rid}.eml").write_text(raw, encoding="utf-8")

    # one constructed reply that quotes a prior question (the threading case)
    order_recs = [r for r in records if r["email_class"] in ("new_order", "amendment")]
    if order_recs:
        base = dict(order_recs[0], body="72 rolls please, same as last time.")
        raw = pack_reply(base, "How many rolls of packing tape did you need?", "<q-prior@x.com>")
        (OUT / f"{base['id']}-reply.eml").write_text(raw, encoding="utf-8")
        counts["reply"] += 1

    total = sum(counts.values())
    print(f"wrote {total} .eml files to {OUT}")
    print(f"  mix: {counts}")


if __name__ == "__main__":
    main()
