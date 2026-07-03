# Frozen test fixlog

data/corpus/test.jsonl (and, from step 1.8, test_human.jsonl) are frozen
evaluation objects. The only legitimate reason to change frozen bytes is a
documented labeling or contract error. Every refreeze must:

1. state what was wrong, with record ids;
2. state why the fix cannot wait for a scheduled corpus version bump;
3. run `uv run python scripts/materialize_corpus.py --refreeze`;
4. commit the regenerated files, updated MANIFEST.json, and a log entry here
   in the same commit.

Comparisons across a refreeze boundary are invalid unless re-run.

## Log

(empty)
