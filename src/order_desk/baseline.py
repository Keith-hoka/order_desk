"""Baseline runner core (step 2.2).

Provider-agnostic two-stage pipeline: classify every record, and only when
the predicted class is order-bearing (new_order / amendment) run extraction
-- pipeline-faithful end-to-end semantics, so a classification mistake that
loses an order costs extraction recall in the report, and non-order records
never spend an extraction call.

Locked decisions:
- BaselineClient is the provider boundary: run_stage(stage, system, user,
  record_id) -> raw text + token counts + latency. Adapters (OpenAI in 2.3,
  Modal/vLLM in 2.4) own temperature, retries, constrained decoding, and
  pricing; the core stays deterministic and fully offline-testable.
- Read-through disk cache under results/cache (gitignored): one JSON file
  per record x stage in a directory keyed by model, variant, and the prompt
  bundle hash prefix; every entry carries the full hash and any mismatch is
  a miss. A rerun under an unchanged contract makes zero client calls;
  editing the prompt contract changes the hash and re-spends by design.
- Repair is one deterministic transform: unwrap a markdown fence, then
  slice from the first '{' to the last '}'. repair_used is True only when
  the parsed output actually came through the transform; if both the direct
  and repaired parses fail, parsed is None and repair_used False --
  parse_rate carries the failure, repair_rate counts successful repairs.
- Classification normalization is trivial-only (whitespace, surrounding
  quotes/backticks, one trailing period, casefold). Anything else passes
  through for the harness to brand invalid; the runner never guesses.
- Latency/token accounting rides in a separate sidecar file (the prediction
  contract is frozen with extra="forbid"); aggregates cover fresh calls
  only, since cached replays cost nothing and would pollute latency.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import ValidationError

from order_desk.harness import _percentile  # same-package private reuse, as with _align_items
from order_desk.materialize import to_jsonl
from order_desk.prompts import (
    classification_system_prompt,
    extraction_system_prompt,
    format_email,
    prompt_bundle_hash,
)
from order_desk.schemas import ExtractedOrder
from order_desk.scoring import ORDER_BEARING

Stage = Literal["classify", "extract"]
_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")
_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass(frozen=True)
class StageResult:
    raw: str
    input_tokens: int
    output_tokens: int
    latency_s: float


class BaselineClient(Protocol):
    def run_stage(self, stage: Stage, system: str, user: str, record_id: str) -> StageResult: ...


def slug(text: str) -> str:
    return _SLUG_RE.sub("-", text)


class ResponseCache:
    def __init__(self, root: Path, model: str, variant: str, prompt_hash: str) -> None:
        self.model = model
        self.variant = variant
        self.prompt_hash = prompt_hash
        self.dir = root / f"{slug(model)}__{slug(variant)}__{prompt_hash[:12]}"

    def _path(self, record_id: str, stage: Stage) -> Path:
        return self.dir / f"{record_id}.{stage}.json"

    def get(self, record_id: str, stage: Stage) -> StageResult | None:
        path = self._path(record_id, stage)
        if not path.exists():
            return None
        entry = json.loads(path.read_text(encoding="utf-8"))
        if (
            entry.get("prompt_hash") != self.prompt_hash
            or entry.get("model") != self.model
            or entry.get("variant") != self.variant
        ):
            return None  # stale contract: treat as a miss and refetch
        return StageResult(
            raw=entry["raw"],
            input_tokens=entry["input_tokens"],
            output_tokens=entry["output_tokens"],
            latency_s=entry["latency_s"],
        )

    def put(self, record_id: str, stage: Stage, result: StageResult) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "model": self.model,
            "variant": self.variant,
            "prompt_hash": self.prompt_hash,
            "record_id": record_id,
            "stage": stage,
            **asdict(result),
        }
        self._path(record_id, stage).write_text(
            json.dumps(entry, sort_keys=True) + "\n", encoding="utf-8"
        )


def normalize_label(raw: str) -> str | None:
    text = raw.strip().strip("`\"'").strip()
    if text.endswith("."):
        text = text[:-1]
    text = text.strip().casefold()
    return text or None


def repair_json_text(raw: str) -> str | None:
    """One deterministic repair; None when no object shape exists to slice."""
    text = raw.strip()
    fence = _FENCE_RE.search(text)
    if fence is not None:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return None
    return text[start : end + 1]


def _try_parse(text: str) -> ExtractedOrder | None:
    try:
        return ExtractedOrder.model_validate_json(text)
    except ValidationError:
        return None


def parse_extraction(raw: str) -> tuple[ExtractedOrder | None, bool]:
    direct = _try_parse(raw)
    if direct is not None:
        return direct, False
    repaired = repair_json_text(raw)
    if repaired is not None and repaired != raw.strip():
        fixed = _try_parse(repaired)
        if fixed is not None:
            return fixed, True
    return None, False


def _stage(
    cache: ResponseCache,
    client: BaselineClient,
    stage: Stage,
    system: str,
    user: str,
    record_id: str,
) -> tuple[StageResult, bool]:
    hit = cache.get(record_id, stage)
    if hit is not None:
        return hit, True
    result = client.run_stage(stage, system, user, record_id)
    cache.put(record_id, stage, result)
    return result, False


def _sidecar_row(record_id: str, stage: Stage, cached: bool, result: StageResult) -> dict[str, Any]:
    return {
        "id": record_id,
        "stage": stage,
        "cached": cached,
        "latency_s": result.latency_s,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
    }


def run_baseline(
    records: list[dict[str, Any]],
    client: BaselineClient,
    *,
    model: str,
    variant: str = "default",
    cache_root: Path = Path("results/cache"),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Run the two-stage pipeline; returns (prediction dicts, sidecar rows)."""
    cache = ResponseCache(cache_root, model, variant, prompt_bundle_hash())
    classify_system = classification_system_prompt()
    extract_system = extraction_system_prompt()
    predictions: list[dict[str, Any]] = []
    sidecar: list[dict[str, Any]] = []
    for record in records:
        user = format_email(record["subject"], record["body"])
        label_result, label_cached = _stage(
            cache, client, "classify", classify_system, user, record["id"]
        )
        sidecar.append(_sidecar_row(record["id"], "classify", label_cached, label_result))
        label = normalize_label(label_result.raw)
        extraction: dict[str, Any] | None = None
        if label in ORDER_BEARING:
            ext_result, ext_cached = _stage(
                cache, client, "extract", extract_system, user, record["id"]
            )
            sidecar.append(_sidecar_row(record["id"], "extract", ext_cached, ext_result))
            parsed, repair_used = parse_extraction(ext_result.raw)
            extraction = {
                "raw": ext_result.raw,
                "parsed": parsed.model_dump() if parsed is not None else None,
                "repair_used": repair_used,
            }
        predictions.append({"id": record["id"], "classification": label, "extraction": extraction})
    return predictions, sidecar


def summarize_sidecar(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fresh = [row for row in rows if not row["cached"]]
    latencies = sorted(row["latency_s"] for row in fresh)
    return {
        "calls": len(rows),
        "cached": len(rows) - len(fresh),
        "fresh": len(fresh),
        "input_tokens": sum(row["input_tokens"] for row in fresh),
        "output_tokens": sum(row["output_tokens"] for row in fresh),
        "latency_p50": _percentile(latencies, 0.5),
        "latency_p95": _percentile(latencies, 0.95),
    }


def write_run(
    name: str,
    source: str,
    predictions: list[dict[str, Any]],
    sidecar: list[dict[str, Any]],
    out_dir: Path = Path("results/predictions"),
) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pred_path = out_dir / f"{name}_{source}.jsonl"
    side_path = out_dir / f"{name}_{source}.sidecar.jsonl"
    pred_path.write_text(to_jsonl(predictions), encoding="utf-8")
    side_path.write_text(to_jsonl(sidecar), encoding="utf-8")
    return pred_path, side_path
