"""Verdict-file parsing and progress reporting for the audit loop (step 1.8).

The verdict file carries hours of human labor, so structural checking is
strict and pinpoints line numbers: any JSON error, key drift, non-boolean
verdict value, or id reordering is rejected outright. Progress counts a
record as filled only when both booleans are set; a record with exactly one
boolean set is reported as partial so a sitting never ends half-judged by
accident.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict

ALLOWED_KEYS = {"id", "realistic", "labels_correct", "notes"}


class VerdictError(ValueError):
    """The verdict file is structurally invalid."""


class VerdictProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    filled: int
    partial_lines: list[int]
    pending_lines: list[int]
    realistic_true: int
    realistic_false: int
    labels_true: int
    labels_false: int
    findings: list[str]
    unrealistic: list[str]
    quirk_tags: dict[str, int]


def parse_verdicts(text: str, expected_ids: list[str]) -> list[dict[str, Any]]:
    verdicts: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            raise VerdictError(f"line {lineno}: blank line (do not insert blank lines)")
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise VerdictError(f"line {lineno}: invalid JSON ({exc})") from exc
        if not isinstance(obj, dict) or set(obj) != ALLOWED_KEYS:
            raise VerdictError(
                f"line {lineno}: keys must be exactly id/realistic/labels_correct/notes"
            )
        for key in ("realistic", "labels_correct"):
            if obj[key] not in (True, False, None):
                raise VerdictError(f"line {lineno}: {key} must be true, false, or null")
        if not isinstance(obj["notes"], str):
            raise VerdictError(f"line {lineno}: notes must be a string")
        verdicts.append(obj)
    ids = [verdict["id"] for verdict in verdicts]
    for lineno, (got, want) in enumerate(zip(ids, expected_ids, strict=False), start=1):
        if got != want:
            raise VerdictError(
                f"line {lineno}: id {got!r} does not match expected {want!r} "
                "(lines must keep the original order)"
            )
    if len(ids) != len(expected_ids):
        raise VerdictError(f"{len(ids)} lines, expected {len(expected_ids)}")
    return verdicts


def progress(verdicts: list[dict[str, Any]]) -> VerdictProgress:
    partial: list[int] = []
    pending: list[int] = []
    filled = 0
    quirk_tags: dict[str, int] = {}
    realistic_true = realistic_false = labels_true = labels_false = 0
    findings: list[str] = []
    unrealistic: list[str] = []
    for lineno, verdict in enumerate(verdicts, start=1):
        realistic, correct = verdict["realistic"], verdict["labels_correct"]
        if realistic is None and correct is None:
            pending.append(lineno)
        elif realistic is None or correct is None:
            partial.append(lineno)
        else:
            filled += 1
        if realistic is True:
            realistic_true += 1
        elif realistic is False:
            realistic_false += 1
            unrealistic.append(verdict["id"])
        if correct is True:
            labels_true += 1
        elif correct is False:
            labels_false += 1
            findings.append(verdict["id"])
        for token in verdict["notes"].split():
            tag = token.rstrip(",.;")
            if tag.startswith("quirk:"):
                quirk_tags[tag] = quirk_tags.get(tag, 0) + 1
    return VerdictProgress(
        total=len(verdicts),
        filled=filled,
        partial_lines=partial,
        pending_lines=pending,
        realistic_true=realistic_true,
        realistic_false=realistic_false,
        labels_true=labels_true,
        labels_false=labels_false,
        findings=findings,
        unrealistic=unrealistic,
        quirk_tags=quirk_tags,
    )
