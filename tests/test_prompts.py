import hashlib
import inspect
from pathlib import Path

from order_desk.prompts import (
    classification_system_prompt,
    extraction_system_prompt,
    format_email,
    prompt_bundle_hash,
)
from order_desk.schemas import EmailClass, ExtractedOrder, LineItem

SNAPSHOT_DIR = Path(__file__).parent / "snapshots"
REGEN_HINT = (
    "prompt contract drifted; if intentional, run "
    "`uv run python scripts/write_prompt_snapshots.py` and commit the result"
)


def test_classification_snapshot_matches() -> None:
    committed = (SNAPSHOT_DIR / "classification_prompt.txt").read_text(encoding="utf-8")
    assert classification_system_prompt() == committed, REGEN_HINT


def test_extraction_snapshot_matches() -> None:
    committed = (SNAPSHOT_DIR / "extraction_prompt.txt").read_text(encoding="utf-8")
    assert extraction_system_prompt() == committed, REGEN_HINT


def test_extraction_prompt_is_derived_from_schema() -> None:
    prompt = extraction_system_prompt()
    assert inspect.cleandoc(ExtractedOrder.__doc__ or "") in prompt
    for model in (ExtractedOrder, LineItem):
        for name, field in model.model_fields.items():
            assert name in prompt
            assert field.description in prompt
    assert "null quantity" in prompt  # the amendment capture convention


def test_classification_prompt_covers_every_class() -> None:
    prompt = classification_system_prompt()
    for member in EmailClass:
        assert prompt.count(member.value) >= 2  # definition line + closing list
    assert "Output only the label." in prompt


def test_format_email_known_answer() -> None:
    formatted = format_email("Tape order", "Hi,\n\nSend tape.\n")
    assert formatted == "Subject: Tape order\n\nHi,\n\nSend tape.\n"


def test_prompts_are_deterministic() -> None:
    assert classification_system_prompt() == classification_system_prompt()
    assert extraction_system_prompt() == extraction_system_prompt()
    assert prompt_bundle_hash() == prompt_bundle_hash()
    assert len(prompt_bundle_hash()) == 64


def test_bundle_hash_binds_to_snapshots() -> None:
    bundle = "\x1f".join(
        [
            (SNAPSHOT_DIR / "classification_prompt.txt").read_text(encoding="utf-8"),
            (SNAPSHOT_DIR / "extraction_prompt.txt").read_text(encoding="utf-8"),
            format_email("<SUBJECT>", "<BODY>"),
        ]
    )
    assert prompt_bundle_hash() == hashlib.sha256(bundle.encode("utf-8")).hexdigest()
