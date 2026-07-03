import json

import pytest

from order_desk.audit import build_pack, load_frozen_test
from order_desk.verdicts import VerdictError, parse_verdicts, progress


@pytest.fixture(scope="module")
def pack():
    return build_pack(load_frozen_test())


def test_template_parses_with_zero_progress(pack) -> None:
    report = progress(parse_verdicts(pack["verdicts"], pack["ids"]))
    assert report.total == len(pack["ids"])
    assert report.filled == 0
    assert report.partial_lines == []
    assert len(report.pending_lines) == report.total


def test_filled_partial_findings_and_tags(pack) -> None:
    lines = pack["verdicts"].splitlines()
    first = json.loads(lines[0])
    first.update(realistic=True, labels_correct=False, notes="quirk:a jarring, gold wrong")
    second = json.loads(lines[1])
    second.update(realistic=False)
    lines[0] = json.dumps(first, sort_keys=True)
    lines[1] = json.dumps(second, sort_keys=True)
    report = progress(parse_verdicts("\n".join(lines) + "\n", pack["ids"]))
    assert report.filled == 1
    assert report.partial_lines == [2]
    assert report.findings == [first["id"]]
    assert report.unrealistic == [second["id"]]
    assert report.quirk_tags == {"quirk:a": 1}


def test_json_error_pinpoints_line(pack) -> None:
    lines = pack["verdicts"].splitlines()
    lines[4] = lines[4][:-1]
    with pytest.raises(VerdictError, match="line 5"):
        parse_verdicts("\n".join(lines) + "\n", pack["ids"])


def test_reordering_is_rejected(pack) -> None:
    lines = pack["verdicts"].splitlines()
    lines[0], lines[1] = lines[1], lines[0]
    with pytest.raises(VerdictError, match="line 1.*order"):
        parse_verdicts("\n".join(lines) + "\n", pack["ids"])


def test_non_boolean_values_are_rejected(pack) -> None:
    lines = pack["verdicts"].splitlines()
    broken = json.loads(lines[0])
    broken["realistic"] = "yes"
    lines[0] = json.dumps(broken, sort_keys=True)
    with pytest.raises(VerdictError, match="true, false, or null"):
        parse_verdicts("\n".join(lines) + "\n", pack["ids"])


def test_key_drift_and_truncation_are_rejected(pack) -> None:
    lines = pack["verdicts"].splitlines()
    extra = json.loads(lines[0])
    extra["comment"] = "x"
    tampered = "\n".join([json.dumps(extra, sort_keys=True), *lines[1:]]) + "\n"
    with pytest.raises(VerdictError, match="keys must be exactly"):
        parse_verdicts(tampered, pack["ids"])
    with pytest.raises(VerdictError, match="expected"):
        parse_verdicts("\n".join(lines[:-1]) + "\n", pack["ids"])
