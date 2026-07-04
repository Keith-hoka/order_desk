"""Regenerate the committed prompt snapshots for the baseline/SFT contract."""

from pathlib import Path

from order_desk.prompts import classification_system_prompt, extraction_system_prompt

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "tests" / "snapshots"


def main() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    for name, text in (
        ("classification_prompt.txt", classification_system_prompt()),
        ("extraction_prompt.txt", extraction_system_prompt()),
    ):
        path = SNAPSHOT_DIR / name
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
