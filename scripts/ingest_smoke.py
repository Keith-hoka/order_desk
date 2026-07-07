"""End-to-end ingest smoke: packed .eml -> standardize -> pipeline (Phase 6).

Takes a few packed human .eml files (some with signatures/HTML noise),
standardizes them, runs the real pipeline, and prints the routing +
extraction. The point is to confirm standardization is lossless on clean
content: extraction from a noisy .eml should match extraction from the raw
body. Requires OPENAI_API_KEY and VLLM_BASE_URL/VLLM_API_KEY.
"""

import json
import os
import sys
from pathlib import Path

from order_desk.ingest.run import process_raw
from order_desk.ingest.standardize import standardize_email
from order_desk.pipeline.build import build_production_pipeline, run_email


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

    # pick a few order-class packed .eml files (prefer noisy ones)
    human = {json.loads(line)["id"]: json.loads(line)
             for line in Path("data/human/test_human.jsonl").read_text().splitlines() if line}
    eml_dir = Path("data/human_eml")
    order_ids = [rid for rid, r in human.items()
                 if r["email_class"] in ("new_order", "amendment")][:5]

    app = build_production_pipeline(
        classifier_model=os.environ.get("CLASSIFIER_MODEL", "gpt-4o-mini"),
        adapter_model=os.environ.get("ADAPTER_MODEL", "qwen3-4b-sft-full-r8"),
        vllm_base_url=base_url,
        vllm_api_key=os.environ.get("VLLM_API_KEY", "EMPTY"),
    )

    for rid in order_ids:
        eml_path = eml_dir / f"{rid}.eml"
        if not eml_path.exists():
            continue
        raw = eml_path.read_text(encoding="utf-8")
        std = standardize_email(raw)
        # via ingest (from .eml)
        state_eml = process_raw(app, raw)
        # via raw body directly (the original human body)
        state_raw = run_email(app, human[rid]["subject"], human[rid]["body"])

        print("=" * 72)
        print(f"{rid}: {std.subject!r}")
        eml_items = [i.product_text for i in state_eml.extraction.line_items] \
            if state_eml.extraction else []
        raw_items = [i.product_text for i in state_raw.extraction.line_items] \
            if state_raw.extraction else []
        print(f"  route (eml): {state_eml.route.value}   route (raw): {state_raw.route.value}")
        print(f"  items (from .eml): {eml_items}")
        print(f"  items (from raw):  {raw_items}")
        match = eml_items == raw_items and state_eml.route == state_raw.route
        print(f"  LOSSLESS: {match}")
        if state_eml.asks:
            print(f"  asks: {state_eml.asks}")


if __name__ == "__main__":
    main()
