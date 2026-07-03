"""Audit ingest and report generation (step 1.8b).

Turns the filled verdict file into a committed report: per-class and
per-stratum realism, tag/qualifier tallies, protocol flags, and a verbatim
evidence dossier for every record judged unrealistic. The stratified sample
is diagnostic, not representative -- noise strata are oversampled by design,
so rates are read per stratum and never extrapolated to the corpus.

Label verification is architecturally a null-result check: gold labels are
derived from truth-first scenarios and machine contract-verified, so the
human pass is a redundant fuse. A finding would have meant a contract bug;
zero findings certifies the subsample and the machinery at once.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from order_desk.audit import _class_strata, _new_order_strata
from order_desk.customers import load_customers
from order_desk.verdicts import VerdictProgress, progress

NOTE_TAG_PREFIXES = ("quirk:", "protocol:")


def parse_note_tags(notes: str) -> list[tuple[str, str | None]]:
    """Extract (tag, qualifier) pairs; the qualifier is the next plain token."""
    tokens = [token.strip(",.;") for token in notes.split()]
    pairs: list[tuple[str, str | None]] = []
    for index, token in enumerate(tokens):
        if not token.startswith(NOTE_TAG_PREFIXES):
            continue
        qualifier = None
        if index + 1 < len(tokens) and not tokens[index + 1].startswith(NOTE_TAG_PREFIXES):
            qualifier = tokens[index + 1]
        pairs.append((token, qualifier))
    return pairs


def _item_line(item: dict[str, Any]) -> str:
    qty = item["quantity_surface"] or "—"
    unit = item["unit_surface"] or "—"
    extras = [f"style={item['unit_style']}"]
    if item["typo"]:
        extras.append("typo")
    if item["intended_packs"] is not None:
        extras.append(f"trap(packs={item['intended_packs']})")
    if item["price_surface"]:
        extras.append(f"price={item['price_surface']}")
    return f"{qty} {unit} × {item['product_surface']} ({', '.join(extras)})"


def _evidence(record: dict[str, Any], verdict: dict[str, Any]) -> dict[str, Any]:
    scenario = record["scenario"]
    flags = [name for name, value in scenario.get("flags", {}).items() if value]
    render = record.get("render") or {}
    return {
        "id": record["id"],
        "notes": verdict["notes"],
        "subject": record["subject"],
        "body": record["body"],
        "layout": render.get("layout"),
        "po_placement": render.get("po_placement"),
        "flags": flags,
        "items": [_item_line(item) for item in scenario.get("items", [])],
    }


def build_report(records: list[dict[str, Any]], verdicts: list[dict[str, Any]]) -> dict[str, Any]:
    prog = progress(verdicts)
    if prog.partial_lines or prog.pending_lines:
        raise RuntimeError("verdicts are not fully filled; finish the audit first")

    index = {record["id"]: record for record in records}
    by_id = {verdict["id"]: verdict for verdict in verdicts}
    sampled = [index[verdict["id"]] for verdict in verdicts]

    per_class: dict[str, tuple[int, int]] = {}
    for verdict in verdicts:
        cls = index[verdict["id"]]["email_class"]
        true_count, total = per_class.get(cls, (0, 0))
        per_class[cls] = (true_count + (verdict["realistic"] is True), total + 1)

    book = load_customers()
    rows: list[tuple[str, int, int]] = []
    order_sampled = [r for r in sampled if r["email_class"] == "new_order"]
    for name, _minimum, predicate in _new_order_strata(book):
        members = [r for r in order_sampled if predicate(r)]
        false = sum(1 for r in members if by_id[r["id"]]["realistic"] is False)
        rows.append((f"new_order/{name}", len(members), false))
    for cls in ("amendment", "cancellation", "inquiry", "other"):
        cls_sampled = [r for r in sampled if r["email_class"] == cls]
        for name, _minimum, predicate in _class_strata(cls):
            members = [r for r in cls_sampled if predicate(r)]
            false = sum(1 for r in members if by_id[r["id"]]["realistic"] is False)
            rows.append((f"{cls}/{name}", len(members), false))

    tag_counts: Counter[tuple[str, str]] = Counter()
    protocol_flags: list[tuple[str, str]] = []
    for verdict in verdicts:
        for tag, qualifier in parse_note_tags(verdict["notes"]):
            if tag.startswith("protocol:"):
                protocol_flags.append((verdict["id"], verdict["notes"]))
            else:
                tag_counts[(tag, qualifier or "—")] += 1

    evidence = [_evidence(index[v["id"]], v) for v in verdicts if v["realistic"] is False]
    label_findings = [v["id"] for v in verdicts if v["labels_correct"] is False]

    markdown = _render_markdown(
        prog, per_class, rows, tag_counts, protocol_flags, evidence, label_findings
    )
    return {
        "per_class": per_class,
        "stratum_rows": rows,
        "tag_counts": tag_counts,
        "protocol_flags": protocol_flags,
        "evidence": evidence,
        "label_findings": label_findings,
        "markdown": markdown,
    }


def _render_markdown(
    prog: VerdictProgress,
    per_class: dict[str, tuple[int, int]],
    rows: list[tuple[str, int, int]],
    tag_counts: Counter[tuple[str, str]],
    protocol_flags: list[tuple[str, str]],
    evidence: list[dict[str, Any]],
    label_findings: list[str],
) -> str:
    lines = [
        "# Audit report — frozen test subsample (step 1.8)",
        "",
        f"Sample: n={prog.total} of the frozen test split (n=1000), coverage-first",
        "stratified (data/audit/sample_ids.json). Noise strata are oversampled by",
        "design: every rate below is diagnostic per stratum, not a corpus estimate.",
        "",
        "## Label verification",
        "",
    ]
    if label_findings:
        lines.append(f"- findings ({len(label_findings)}): {', '.join(label_findings)}")
    else:
        lines += [
            f"- {prog.labels_true}/{prog.total} labels_correct, zero findings: the",
            "  expected null result. Gold is derived from truth-first scenarios and",
            "  machine contract-verified; this human pass is a redundant fuse, and a",
            "  finding here would have meant a contract bug. The SPEC §7",
            "  human-certified subsample is hereby certified.",
        ]
    lines += [
        "",
        "## Realism (on-sample)",
        "",
        f"- overall: {prog.realistic_true}/{prog.total} realistic",
        "",
        "| class | realistic | sampled |",
        "|---|---|---|",
    ]
    for cls, (true_count, total) in sorted(per_class.items()):
        lines.append(f"| {cls} | {true_count} | {total} |")
    lines += [
        "",
        "## Per-stratum realism",
        "",
        "| stratum | sampled | unrealistic |",
        "|---|---|---|",
    ]
    for name, sampled_n, false_n in rows:
        lines.append(f"| {name} | {sampled_n} | {false_n} |")
    lines += ["", "## Note tags", "", "| tag | qualifier | count |", "|---|---|---|"]
    for (tag, qualifier), count in sorted(tag_counts.items()):
        lines.append(f"| {tag} | {qualifier} | {count} |")
    lines += ["", "## Protocol flags", ""]
    if protocol_flags:
        lines += [f"- {record_id}: {notes}" for record_id, notes in protocol_flags]
    else:
        lines.append("(none)")
    lines += ["", "## Unrealistic records — evidence dossier", ""]
    for item in evidence:
        lines += [
            f"### {item['id']}",
            "",
            f"- notes: {item['notes']}",
            f"- layout={item['layout']} · po_placement={item['po_placement']}",
            f"- flags: {', '.join(item['flags']) or '—'}",
        ]
        lines += [f"- item: {line}" for line in item["items"]]
        lines += [
            "",
            f"Subject: {item['subject']}",
            "",
            "```text",
            item["body"].rstrip(),
            "```",
            "",
        ]
    lines += [
        "## Adjudication",
        "",
        "Pending — step 1.8b2 fills this section after per-record adjudication and",
        "the fix-vs-record decision. This is the cheap refreeze window (no baseline",
        "numbers exist yet); see docs/frozen_test_fixlog.md for the ritual.",
        "",
    ]
    return "\n".join(lines)
