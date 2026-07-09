"""Reset the review queue to its pristine seed.

The working queue (data/review_queue.json) is rewritten on every review, so a
demo dirties it. The seed is version-controlled and never written to: 66
exceptions, all pending, exactly as Phase 7's pipeline produced them.

The seed is committed rather than rebuilt because build_review_queue.py needs
the fine-tuned adapter on a GPU plus API keys -- its own docstring says "run
once; the API reads the result offline". Committing that one run's output is
what makes the repo clone-and-demo.

The seed carries no org_id: it predates tenancy. The store's deserialiser
attributes it to the demo org on load, so the Phase 11 migration path runs every
time the queue is read, rather than being a one-off script.
"""

import shutil
from pathlib import Path

SEED = Path("data/review_queue.seed.json")
WORKING = Path("data/review_queue.json")


def main() -> None:
    if not SEED.exists():
        raise SystemExit(f"missing seed: {SEED}")
    shutil.copyfile(SEED, WORKING)
    print(f"reset {WORKING} from {SEED} (66 pending exceptions)")


if __name__ == "__main__":
    main()
