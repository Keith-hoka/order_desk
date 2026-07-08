"""Merge blended corrections into the SFT training set (Phase 9.3).

Turns the 150 blended over-extraction corrections into SFT examples (email ->
corrected gold, i.e. the ordered products only) and appends them to the full
Phase 3 training pool, producing train_flywheel.jsonl for retraining. The
corrections teach the adapter not to pull inquiry products into the order,
while the counter-examples keep it from over-suppressing genuine questioned
orders. Updates the SFT manifest with the new subset's composition and sha.
"""

import json
from pathlib import Path

from order_desk.flywheel.blended import case_to_record, generate_blended_cases
from order_desk.sft import (
    build_example,
    build_sft_pool,
    sha256_of,
    to_jsonl,
)

SFT_DIR = Path("data/sft")
CORRECTIONS_SEED = 90210  # same seed as the saved corrections.jsonl


def main() -> None:
    # rebuild the exact corrections (deterministic) and turn them into SFT examples
    corrections = generate_blended_cases(n=150, seed=CORRECTIONS_SEED, id_prefix="BLD-COR")
    correction_examples = [build_example(case_to_record(c)) for c in corrections]

    # build_sft_pool() already returns SFT examples ({id, messages})
    full_examples = build_sft_pool()

    merged = full_examples + correction_examples
    text = to_jsonl(merged)
    out_path = SFT_DIR / "train_flywheel.jsonl"
    out_path.write_text(text, encoding="utf-8")
    merged_sha = sha256_of(text)

    counter = sum(1 for c in corrections if c.is_counter_example)
    print(f"full pool: {len(full_examples)} examples")
    print(f"blended corrections: {len(correction_examples)} ({counter} counter-examples)")
    print(f"merged: {len(merged)} -> {out_path}")
    print(f"train_flywheel sha256: {merged_sha}")

    # update manifest with the flywheel subset
    manifest_path = SFT_DIR / "MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["subsets"]["flywheel"] = {
        "composition": {
            "n": len(merged),
            "base_full": len(full_examples),
            "blended_corrections": len(correction_examples),
            "counter_examples": counter,
            "corrections_seed": CORRECTIONS_SEED,
        },
        "sha256": merged_sha,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"updated {manifest_path} with 'flywheel' subset")


if __name__ == "__main__":
    main()
