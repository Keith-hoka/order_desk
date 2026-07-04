"""Run a provider baseline over a frozen source.

Smoke mode (--limit N) writes an incomplete prediction file under a -smoke
name and dumps every raw output for eyeballing; it cannot be evaluated (the
harness demands complete files). Full runs write {name}_{source}.jsonl ready
for scripts/run_eval.py --predictions. The response cache is keyed on model,
variant, and prompt hash -- smoke spend is reused by the full run.
"""

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from order_desk.baseline import run_baseline, slug, summarize_sidecar, write_run
from order_desk.harness import load_source
from order_desk.prompts import prompt_bundle_hash

# Meta-estimate only; verify against the provider's current pricing page.
PRICES_PER_MTOK = {"gpt-4o-mini": (0.15, 0.60)}
CHUNK = 25


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=("synthetic", "human"), required=True)
    parser.add_argument("--provider", choices=("openai", "vllm"), default="openai")
    parser.add_argument("--base-url", default=None, help="vLLM OpenAI-compatible endpoint")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--variant", default="default")
    parser.add_argument("--name", default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    load_dotenv()
    if args.provider == "openai":
        if not os.environ.get("OPENAI_API_KEY"):
            sys.exit("OPENAI_API_KEY is not set (export it or put it in .env)")
        from order_desk.openai_client import OpenAIBaselineClient

        client = OpenAIBaselineClient(args.model)
    elif args.provider == "vllm":
        if not args.base_url:
            sys.exit("--base-url is required for --provider vllm")
        from order_desk.vllm_client import VLLMBaselineClient

        client = VLLMBaselineClient(
            args.model,
            args.base_url,
            variant=args.variant,
            api_key=os.environ.get("VLLM_API_KEY", "EMPTY"),
        )

    records, sha = load_source(args.source)
    if args.limit:
        records = records[: args.limit]
    name = args.name or slug(args.model)
    if args.variant != "default" and args.name is None:
        name = f"{name}-{args.variant}"
    if args.limit:
        name = f"{name}-smoke"

    predictions: list[dict] = []
    sidecar: list[dict] = []
    for start in range(0, len(records), CHUNK):
        part = records[start : start + CHUNK]
        preds, rows = run_baseline(part, client, model=args.model, variant=args.variant)
        predictions += preds
        sidecar += rows
        print(f"  [{min(start + CHUNK, len(records))}/{len(records)}] processed", flush=True)

    pred_path, side_path = write_run(name, args.source, predictions, sidecar)
    summary = summarize_sidecar(sidecar)
    rates = PRICES_PER_MTOK.get(args.model)
    cost = None
    if rates is not None:
        cost = summary["input_tokens"] / 1e6 * rates[0] + summary["output_tokens"] / 1e6 * rates[1]
    meta = {
        "provider": args.provider,
        "model": args.model,
        "resolved_models": sorted(getattr(client, "resolved_models", set())),
        "variant": args.variant,
        "source": args.source,
        "dataset_sha256": sha,
        "n_records": len(records),
        "prompt_bundle_hash": prompt_bundle_hash(),
        "summary": summary,
        "estimated_cost_usd": cost,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    meta_path = pred_path.with_name(pred_path.name.replace(".jsonl", ".meta.json"))
    meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {pred_path}")
    print(f"wrote {side_path}")
    print(f"wrote {meta_path}")
    print(f"resolved models: {', '.join(meta['resolved_models']) or '?'}")
    print(
        f"fresh calls: {summary['fresh']} (cached {summary['cached']})  "
        f"tokens in/out: {summary['input_tokens']}/{summary['output_tokens']}  "
        f"latency p50/p95: {summary['latency_p50']:.2f}s/{summary['latency_p95']:.2f}s"
    )
    if cost is not None:
        print(f"estimated fresh-call cost: ${cost:.4f}")
    elif args.provider == "vllm":
        print("cost: GPU-hour billed on the serving side (see Modal dashboard)")

    if args.limit:
        index = {record["id"]: record for record in records}
        print("\n--- smoke eyeball ---")
        for prediction in predictions:
            record = index[prediction["id"]]
            print("=" * 72)
            print(
                f"{prediction['id']}  gold={record['email_class']}  "
                f"pred={prediction['classification']}"
            )
            extraction = prediction["extraction"]
            if extraction is not None:
                parsed = "yes" if extraction["parsed"] is not None else "NO"
                print(f"repair_used={extraction['repair_used']}  parsed={parsed}")
                print(extraction["raw"])


if __name__ == "__main__":
    main()
