import json

import pytest

from order_desk.audit import build_pack, load_frozen_test
from order_desk.audit_report import build_report, parse_note_tags


@pytest.fixture(scope="module")
def records():
    return load_frozen_test()


@pytest.fixture(scope="module")
def pack(records):
    return build_pack(records)


def _filled(pack, *, false_id=None, notes=""):
    verdicts = [json.loads(line) for line in pack["verdicts"].splitlines()]
    for verdict in verdicts:
        verdict["realistic"] = True
        verdict["labels_correct"] = True
    if false_id is not None:
        target = next(v for v in verdicts if v["id"] == false_id)
        target["realistic"] = False
        target["notes"] = notes
    return verdicts


def test_tag_parsing_pairs_and_boundaries() -> None:
    pairs = parse_note_tags("quirk:a jarring, quirk:b fine; protocol:nulls quirk:c")
    assert ("quirk:a", "jarring") in pairs
    assert ("quirk:b", "fine") in pairs
    assert ("protocol:nulls", None) in pairs
    assert ("quirk:c", None) in pairs
    assert parse_note_tags("no tags here") == []


def test_report_requires_fully_filled(pack, records) -> None:
    template = [json.loads(line) for line in pack["verdicts"].splitlines()]
    with pytest.raises(RuntimeError, match="not fully filled"):
        build_report(records, template)


def test_report_aggregates_single_finding(pack, records) -> None:
    index = {record["id"]: record for record in records}
    false_id = next(i for i in pack["ids"] if index[i]["email_class"] == "new_order")
    verdicts = _filled(pack, false_id=false_id, notes="quirk:a jarring")
    report = build_report(records, verdicts)
    true_count, total = report["per_class"]["new_order"]
    assert (true_count, total) == (71, 72)
    assert [item["id"] for item in report["evidence"]] == [false_id]
    assert report["label_findings"] == []
    assert report["tag_counts"][("quirk:a", "jarring")] == 1
    assert any(false_n == 1 for _n, _s, false_n in report["stratum_rows"])
    assert all(false_n <= 1 for _n, _s, false_n in report["stratum_rows"])


def test_markdown_carries_sections_and_dossier(pack, records) -> None:
    index = {record["id"]: record for record in records}
    false_id = next(i for i in pack["ids"] if index[i]["email_class"] == "new_order")
    markdown = build_report(records, _filled(pack, false_id=false_id, notes="quirk:a jarring"))[
        "markdown"
    ]
    for header in (
        "# Audit report",
        "## Label verification",
        "## Per-stratum realism",
        "## Unrealistic records",
        "## Adjudication",
    ):
        assert header in markdown
    assert false_id in markdown
