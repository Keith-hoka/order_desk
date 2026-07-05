"""Build the SFT dataset and curve subsets; hash-pin the manifest."""

import json
from pathlib import Path

from order_desk.materialize import to_jsonl
from order_desk.sft import build_manifest, build_sft_pool, curve_subsets

SFT_DIR = Path("data/sft")
MANIFEST_PATH = SFT_DIR / "MANIFEST.json"


def main() -> None:
    pool = build_sft_pool()
    subsets = curve_subsets(pool)
    manifest = build_manifest(pool, subsets)
    SFT_DIR.mkdir(parents=True, exist_ok=True)

    for label, examples in subsets.items():
        path = SFT_DIR / f"train_{label}.jsonl"
        path.write_text(to_jsonl(examples), encoding="utf-8")
        print(f"wrote {path} ({len(examples)} examples)")

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {MANIFEST_PATH}")
    print(f"\npool size (full): {manifest['pool_size']}")
    print(f"train split sha: {manifest['train_split_sha256'][:16]}")
    print(f"prompt bundle hash: {manifest['prompt_bundle_hash'][:16]}")
    print("\ncomposition:")
    for label, meta in manifest["subsets"].items():
        comp = meta["composition"]
        print(
            f"  {label:<6} n={comp['n']:<5} "
            f"new_order={comp['new_order']:<5} amendment={comp['amendment']:<4} "
            f"avg_items={comp['avg_line_items']:<6} sha={meta['sha256'][:12]}"
        )


if __name__ == "__main__":
    main()
