"""Run the full pipeline on sample emails against real backends (Phase 5).

Requires OPENAI_API_KEY (gpt-4o-mini classifier) and VLLM_BASE_URL/
VLLM_API_KEY (Modal adapter). Exercises classify -> route -> extract ->
validate end-to-end and prints the resulting state per email.
"""

import os
import sys
from pathlib import Path

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


SAMPLES = [
    (
        "blended order+question",
        "OC-1184-3 stretch film + a question",
        "Hi, please send 12 rolls of machine stretch film to our Botany warehouse "
        "against PO OC-1184-3. Also, do you stock 20mm bubble wrap? Thanks, Dana",
    ),
    (
        "plain new order",
        "Restock - thermal labels",
        "Please send 20 rolls of thermal labels to the Eagle Farm store. Regards, Sam",
    ),
    (
        "inquiry only",
        "lead time question",
        "Hi, what's your typical lead time on pallet wrap these days? Cheers, Alex",
    ),
    (
        "cancellation",
        "cancel OC-9931",
        "Please cancel our order OC-9931, we no longer need it. Thanks, Jo",
    ),
]


def main() -> None:
    load_dotenv()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set")
    base_url = os.environ.get("VLLM_BASE_URL", "")
    if not base_url:
        sys.exit("VLLM_BASE_URL not set")

    app = build_production_pipeline(
        classifier_model=os.environ.get("CLASSIFIER_MODEL", "gpt-4o-mini"),
        adapter_model=os.environ.get("ADAPTER_MODEL", "qwen3-4b-sft-full-r8"),
        vllm_base_url=base_url,
        vllm_api_key=os.environ.get("VLLM_API_KEY", "EMPTY"),
    )

    for label, subject, body in SAMPLES:
        state = run_email(app, subject, body)
        print("=" * 72)
        print(f"{label}: {subject!r}")
        cls = state.classification
        print(
            f"  class={cls.email_class.value} (conf {cls.confidence:.3f})  "
            f"route={state.route.value}"
        )
        if state.extraction is not None:
            items = state.extraction.line_items
            print(
                f"  extraction: PO={state.extraction.customer_po_text!r} "
                f"items={[i.product_text for i in items]}"
            )
        if state.asks:
            print(f"  asks: {state.asks}")
        if state.violations:
            print(f"  violations: {state.violations}")


if __name__ == "__main__":
    main()
