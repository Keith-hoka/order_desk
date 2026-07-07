"""Build the exception queue from human .eml via the pipeline (Phase 7.3).

Runs the packed human .eml corpus through ingest + pipeline, builds a
ReviewItem per email (priority from confidence band + asks + violations),
sorts by priority, and writes the queue JSON the review API serves. Requires
OPENAI_API_KEY and VLLM_BASE_URL/VLLM_API_KEY. Run once; the API reads the
result offline.
"""

import json
import os
import sys
from pathlib import Path

from order_desk.api.review_store import item_to_dict
from order_desk.calibration import IsotonicCalibrator
from order_desk.ingest.run import process_raw
from order_desk.ingest.source import EmlDirectorySource
from order_desk.pipeline.build import build_production_pipeline
from order_desk.review.priority import build_review_item, sort_queue

CALIBRATOR = Path("docs/phase4_calibrator.json")
EML_DIR = Path("data/human_eml")
OUT = Path("data/review_queue.json")


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set")
    base_url = os.environ.get("VLLM_BASE_URL", "")
    if not base_url:
        sys.exit("VLLM_BASE_URL not set")

    calibrator = IsotonicCalibrator.load(CALIBRATOR)
    app = build_production_pipeline(
        classifier_model=os.environ.get("CLASSIFIER_MODEL", "gpt-4o-mini"),
        adapter_model=os.environ.get("ADAPTER_MODEL", "qwen3-4b-sft-full-r8"),
        vllm_base_url=base_url,
        vllm_api_key=os.environ.get("VLLM_API_KEY", "EMPTY"),
    )
    source = EmlDirectorySource(EML_DIR)

    items = []
    raws = list(source.fetch())
    for i, raw in enumerate(raws):
        state = process_raw(app, raw)
        item = build_review_item(state, calibrator, f"EXC-{i:04d}")
        items.append(item)
        if (i + 1) % 10 == 0:
            print(f"  [{i + 1}/{len(raws)}] processed", flush=True)

    queue = sort_queue(items)
    OUT.write_text(
        json.dumps([item_to_dict(it) for it in queue], indent=2), encoding="utf-8"
    )

    # summary
    with_asks = sum(1 for it in queue if it.asks)
    with_band = sum(1 for it in queue if it.band_field_count > 0)
    with_viol = sum(1 for it in queue if it.violations)
    print(f"\nwrote {OUT}: {len(queue)} items")
    print(f"  with asks: {with_asks}, with band fields: {with_band}, with violations: {with_viol}")
    print("  top 5 by priority:")
    for it in queue[:5]:
        print(f"    {it.id} pri={it.priority:.1f} band={it.band_field_count} "
              f"asks={len(it.asks)} viol={len(it.violations)} :: {it.subject!r}")


if __name__ == "__main__":
    main()
