"""Regenerate the committed JSON-schema snapshot for the extraction contract."""

import json
from pathlib import Path

from order_desk.schemas import ExtractedOrder

path = (
    Path(__file__).resolve().parent.parent / "tests" / "snapshots" / "extracted_order.schema.json"
)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(ExtractedOrder.model_json_schema(), indent=2, sort_keys=True) + "\n")
print(f"wrote {path}")
