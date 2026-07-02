from datetime import UTC, datetime

import pytest

from order_desk.customers import load_customers
from order_desk.renderer import (
    TEAM_CLOSERS,
    ContractViolation,
    Layout,
    PoPlacement,
    RenderedEmail,
    render_email,
    verify_rendering,
)
from order_desk.scenarios import (
    AddressStyle,
    DateStyle,
    LineItemScenario,
    MentionStyle,
    OrderScenario,
    ScenarioFlags,
    UnitStyle,
    generate_scenarios,
)

SCEN_SEED = 20260702
RENDER_SEED = 31
N = 400


@pytest.fixture(scope="module")
def corpus() -> list[OrderScenario]:
    return generate_scenarios(N, seed=SCEN_SEED)


@pytest.fixture(scope="module")
def rendered(corpus: list[OrderScenario]) -> list[RenderedEmail]:
    return [render_email(scenario, RENDER_SEED) for scenario in corpus]


def test_every_email_passes_contracts(
    corpus: list[OrderScenario], rendered: list[RenderedEmail]
) -> None:
    for scenario, email in zip(corpus, rendered, strict=True):
        verify_rendering(scenario, email)


def test_render_is_deterministic_and_seed_sensitive(
    corpus: list[OrderScenario], rendered: list[RenderedEmail]
) -> None:
    again = [render_email(scenario, RENDER_SEED) for scenario in corpus]
    assert [e.model_dump() for e in again] == [e.model_dump() for e in rendered]
    other = [render_email(scenario, RENDER_SEED + 1) for scenario in corpus]
    differing = sum(
        a.subject != b.subject or a.body != b.body for a, b in zip(rendered, other, strict=True)
    )
    assert differing >= int(0.9 * len(corpus))


def test_render_is_pure_and_order_independent(
    corpus: list[OrderScenario], rendered: list[RenderedEmail]
) -> None:
    before = [scenario.model_dump_json() for scenario in corpus]
    _ = [render_email(scenario, RENDER_SEED) for scenario in corpus]
    assert [scenario.model_dump_json() for scenario in corpus] == before
    lone = render_email(corpus[7], RENDER_SEED)
    assert lone.model_dump() == rendered[7].model_dump()


def _handcrafted() -> OrderScenario:
    item = LineItemScenario(
        sku="FLM-HND-101",
        product_surface="pallet wrap",
        mention_style=MentionStyle.ALIAS,
        typo=False,
        quantity_value=12,
        quantity_surface="12",
        unit_surface="rolls",
        unit_style=UnitStyle.ALIAS,
        item_note=None,
        price_cents=780,
        price_surface="$7.80",
        intended_packs=None,
    )
    return OrderScenario(
        scenario_id="SCN-999997",
        customer_id="CUST-0002",
        sender_email="marcus.yeo@redgumfurniture.com.au",
        sent_at=datetime(2026, 3, 2, 9, 30, tzinfo=UTC),
        buyer_signature="Marcus",
        po_surface="4512345678",
        date_style=DateStyle.NONE,
        date_phrase=None,
        intended_date=None,
        address_style=AddressStyle.NONE,
        address_mention=None,
        address_label_truth="Dandenong plant",
        order_note=None,
        items=[item],
        flags=ScenarioFlags(prices_stated=True),
    )


def test_verifier_catches_tampering() -> None:
    scenario = _handcrafted()
    email = render_email(scenario, RENDER_SEED)
    verify_rendering(scenario, email)

    broken = email.model_copy(update={"body": email.body.replace("pallet wrap", "the film")})
    with pytest.raises(ContractViolation, match="missing"):
        verify_rendering(scenario, broken)

    broken = email.model_copy(update={"body": email.body + "\nNeed them by 4pm.\n"})
    with pytest.raises(ContractViolation, match="digit-closure"):
        verify_rendering(scenario, broken)

    broken = email.model_copy(update={"body": email.body + "\nPlease pack them tight.\n"})
    with pytest.raises(ContractViolation, match="term-closure"):
        verify_rendering(scenario, broken)

    wrong = (
        PoPlacement.SUBJECT_ONLY
        if email.po_placement is not PoPlacement.SUBJECT_ONLY
        else PoPlacement.BODY_ONLY
    )
    broken = email.model_copy(update={"po_placement": wrong})
    with pytest.raises(ContractViolation, match="placement"):
        verify_rendering(scenario, broken)


def test_style_dimension_coverage(
    corpus: list[OrderScenario], rendered: list[RenderedEmail]
) -> None:
    assert {email.layout for email in rendered} == set(Layout)
    assert {email.po_placement for email in rendered if email.po_placement is not None} == set(
        PoPlacement
    )
    assert any(closer in email.body for email in rendered for closer in TEAM_CLOSERS)

    book = load_customers()
    unsigned_personal = 0
    for scenario, email in zip(corpus, rendered, strict=True):
        if scenario.buyer_signature is not None:
            continue
        customer = book.resolve_customer(scenario.sender_email)
        assert customer is not None
        contact = next(c for c in customer.contacts if c.email == scenario.sender_email)
        if contact.role != "shared mailbox":
            unsigned_personal += 1
            assert email.body.rstrip().endswith(f"{customer.style.signoff},")
    assert unsigned_personal > 0
