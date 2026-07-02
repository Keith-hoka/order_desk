from collections import Counter

import pytest
from pydantic import ValidationError

from order_desk.corpus import ClassMix, generate_corpus, render_item, verify_item
from order_desk.schemas import EmailClass

SEED = 20260704


def test_class_mix_validation() -> None:
    ClassMix()
    with pytest.raises(ValidationError, match="every EmailClass"):
        ClassMix(weights={EmailClass.NEW_ORDER: 1.0})
    zeroed = {cls: 0.25 for cls in EmailClass}
    zeroed[EmailClass.OTHER] = 0.0
    with pytest.raises(ValidationError, match="positive"):
        ClassMix(weights=zeroed)


def test_corpus_composition_and_determinism() -> None:
    corpus = generate_corpus(2000, seed=SEED)
    again = generate_corpus(2000, seed=SEED)
    assert [i.model_dump_json() for i in corpus] == [i.model_dump_json() for i in again]
    other = generate_corpus(2000, seed=SEED + 1)
    assert [i.model_dump_json() for i in corpus] != [i.model_dump_json() for i in other]

    ids = [item.scenario_id for item in corpus]
    assert len(set(ids)) == len(ids)

    counts = Counter(item.email_class for item in corpus)
    for cls, weight in ClassMix().weights.items():
        assert abs(counts[cls] / 2000 - weight) < 0.04, (cls, counts[cls])


def test_corpus_full_contract_gate() -> None:
    corpus = generate_corpus(600, seed=SEED)
    assert {item.email_class for item in corpus} == set(EmailClass)
    for item in corpus:
        verify_item(item, render_item(item, seed=77))
