"""Materialize the corpus; the first run performs the one-time test freeze."""

import argparse
import sys

from order_desk.materialize import (
    CORPUS_DIR,
    FROZEN_TEST,
    MANIFEST_PATH,
    build_all,
    manifest_to_text,
    to_jsonl,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refreeze",
        action="store_true",
        help="overwrite the frozen test split (record it in docs/frozen_test_fixlog.md)",
    )
    args = parser.parse_args()

    splits, manifest = build_all()
    test_text = to_jsonl(splits["test"])
    CORPUS_DIR.mkdir(parents=True, exist_ok=True)

    if FROZEN_TEST.exists() and not args.refreeze:
        if FROZEN_TEST.read_text(encoding="utf-8") != test_text:
            sys.exit(
                "REFUSED: regenerated test split differs from frozen data/corpus/test.jsonl.\n"
                "If intentional, rerun with --refreeze and record the reason in\n"
                "docs/frozen_test_fixlog.md."
            )
        print("freeze intact: regenerated test split matches frozen bytes")
    else:
        FROZEN_TEST.write_text(test_text, encoding="utf-8")
        print(f"{'REFROZE' if args.refreeze else 'froze'} {FROZEN_TEST} (1000 records)")
        if args.refreeze:
            print("record this refreeze in docs/frozen_test_fixlog.md")

    for name in ("train", "val"):
        path = CORPUS_DIR / f"{name}.jsonl"
        path.write_text(to_jsonl(splits[name]), encoding="utf-8")
        print(f"wrote {path} ({len(splits[name])} records)")

    MANIFEST_PATH.write_text(manifest_to_text(manifest), encoding="utf-8")
    print(f"wrote {MANIFEST_PATH}")

    print("\ncomposition:")
    for name, meta in manifest["splits"].items():
        counts = "  ".join(f"{cls}:{count}" for cls, count in sorted(meta["counts"].items()))
        print(f"  {name:<6} n={meta['n']:<5} {counts}")
        print(f"         sha256={meta['sha256']}")
    print("\ncross-split exact-duplicate stats (measured; template classes expected nonzero):")
    for label, per_class in manifest["duplicate_stats"].items():
        row = "  ".join(f"{cls}:{count}" for cls, count in sorted(per_class.items()))
        print(f"  {label}: {row}")


if __name__ == "__main__":
    main()
