"""Collect (confidence, correct) pairs on the val split for calibration (4.5b).

Runs the fine-tuned adapter over val gold-bearing records via the remote
vLLM endpoint, aligns per-field confidence to correctness (norm_text
equality vs gold), and writes pairs to results/calibration/val_pairs.jsonl.
Val split only -- never test (SPEC eval-purity). The 400-call collection is
slow, so pairs are persisted to avoid re-running.
"""

import json
import os
import sys
from pathlib import Path

from order_desk.baseline import parse_extraction
from order_desk.calibration import field_correct
from order_desk.confidence import ITEM_FIELDS, ORDER_FIELDS, field_confidences
from order_desk.extract_client import VLLMExtractClient
from order_desk.materialize import build_all

OUT = Path("results/calibration/val_pairs.jsonl")


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
    base_url = os.environ.get("VLLM_BASE_URL", "")
    if not base_url:
        sys.exit("VLLM_BASE_URL not set")
    model = os.environ.get("ADAPTER_MODEL", "qwen3-4b-sft-full-r8")
    client = VLLMExtractClient(model, base_url, api_key=os.environ.get("VLLM_API_KEY", "EMPTY"))

    splits, _ = build_all()
    records = [r for r in splits["val"] if r["email_class"] in ("new_order", "amendment")]
    OUT.parent.mkdir(parents=True, exist_ok=True)

    pairs: list[dict] = []
    skipped = 0
    for i, record in enumerate(records):
        result = client.extract(record["subject"], record["body"])
        parsed, _ = parse_extraction(result.raw)
        if parsed is None:
            skipped += 1
            continue
        confs = field_confidences(result.raw, result.tokens, parsed)
        gold = record["gold_extraction"]
        pred = parsed.model_dump()
        for field in ORDER_FIELDS:
            if field in confs:
                pairs.append(
                    {
                        "field": field,
                        "confidence": confs[field],
                        "correct": field_correct(pred[field], gold[field]),
                    }
                )
        for idx, (pred_item, gold_item) in enumerate(
            zip(pred["line_items"], gold["line_items"], strict=False)
        ):
            for field in ITEM_FIELDS:
                path = f"line_items.{idx}.{field}"
                if path in confs:
                    pairs.append(
                        {
                            "field": f"line_items.{field}",
                            "confidence": confs[path],
                            "correct": field_correct(pred_item[field], gold_item[field]),
                        }
                    )
        if (i + 1) % 50 == 0:
            print(f"  [{i + 1}/{len(records)}] {len(pairs)} pairs", flush=True)

    OUT.write_text("\n".join(json.dumps(p) for p in pairs) + "\n", encoding="utf-8")
    print(f"wrote {OUT}: {len(pairs)} pairs from {len(records)} records ({skipped} unparsed)")


if __name__ == "__main__":
    main()
