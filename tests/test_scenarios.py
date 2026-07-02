from datetime import UTC, datetime, timedelta

import pytest

from order_desk.catalog import Catalog, load_catalog
from order_desk.customers import CustomerBook, load_customers, po_regex
from order_desk.scenarios import (
    NUMBER_WORDS,
    RELATIVE_PHRASES,
    AddressStyle,
    Ask,
    DateStyle,
    LineItemScenario,
    MentionStyle,
    OrderScenario,
    Route,
    ScenarioFlags,
    UnitStyle,
    Violation,
    generate_scenarios,
)
from order_desk.schemas import EmailClass, ExtractedOrder

SEED = 20260702
N = 400


@pytest.fixture(scope="module")
def corpus() -> list[OrderScenario]:
    return generate_scenarios(N, seed=SEED)


@pytest.fixture(scope="module")
def catalog() -> Catalog:
    return load_catalog()


@pytest.fixture(scope="module")
def book() -> CustomerBook:
    return load_customers()


def test_generation_is_deterministic_per_seed() -> None:
    first = [s.model_dump_json() for s in generate_scenarios(30, seed=11)]
    second = [s.model_dump_json() for s in generate_scenarios(30, seed=11)]
    other = [s.model_dump_json() for s in generate_scenarios(30, seed=12)]
    assert first == second
    assert first != other


def test_gold_extractions_satisfy_contract(corpus: list[OrderScenario]) -> None:
    for scenario in corpus:
        gold = scenario.gold_extraction()
        assert len(gold.line_items) == len(scenario.items) >= 1
        ExtractedOrder.model_validate(gold.model_dump())
        assert scenario.email_class is EmailClass.NEW_ORDER


def test_quantity_surfaces_are_coherent(corpus: list[OrderScenario]) -> None:
    words = {v: k for k, v in NUMBER_WORDS.items()}
    saw_word = False
    for scenario in corpus:
        for item in scenario.items:
            assert (item.quantity_value is None) == (item.quantity_surface is None)
            if item.quantity_surface is None:
                continue
            if item.quantity_surface.isdigit():
                assert int(item.quantity_surface) == item.quantity_value
            else:
                saw_word = True
                assert words[item.quantity_surface] == item.quantity_value
    assert saw_word


def test_mentions_resolve_unless_typo(corpus: list[OrderScenario], catalog: Catalog) -> None:
    saw_typo = False
    for scenario in corpus:
        for item in scenario.items:
            resolved = catalog.resolve_sku(item.product_surface)
            if item.typo:
                saw_typo = True
                assert resolved is None
                assert catalog.resolve_sku(item.sku) is not None
            else:
                assert resolved is not None
                assert resolved.sku == item.sku
    assert saw_typo


def test_flags_match_realized_facts(
    corpus: list[OrderScenario], catalog: Catalog, book: CustomerBook
) -> None:
    for scenario in corpus:
        customer = book.resolve_customer(scenario.sender_email)
        assert customer is not None
        assert customer.customer_id == scenario.customer_id
        flags = scenario.flags
        assert flags.missing_quantity == any(i.quantity_value is None for i in scenario.items)
        assert flags.unsigned == (scenario.buyer_signature is None)
        assert flags.ambiguous_site == (
            scenario.address_mention is None and len(customer.delivery_addresses) > 1
        )
        assert flags.pack_size_trap == any(i.intended_packs is not None for i in scenario.items)
        assert flags.mention_typo == any(i.typo for i in scenario.items)
        resolved_active = [catalog.resolve_sku(i.sku) for i in scenario.items]
        assert flags.discontinued_item == any(
            p is not None and not p.active for p in resolved_active
        )
        if flags.missing_po:
            assert customer.po_template is not None
            assert scenario.po_surface is None
        if customer.po_template is None:
            assert not flags.missing_po
            assert scenario.po_surface is None
        for item in scenario.items:
            if item.intended_packs is not None:
                product = catalog.resolve_sku(item.sku)
                assert product is not None and product.pack_size is not None
                assert item.quantity_value == product.pack_size * item.intended_packs
                assert item.unit_surface is not None
                assert catalog.resolve_unit(item.unit_surface) is None


def test_routes_follow_precedence_and_cover_all(
    corpus: list[OrderScenario], catalog: Catalog, book: CustomerBook
) -> None:
    seen_routes: set[Route] = set()
    seen_violations: set[Violation] = set()
    for scenario in corpus:
        violations = scenario.expected_violations(catalog)
        asks = scenario.expected_asks(book)
        route = scenario.expected_route(catalog, book)
        seen_routes.add(route)
        seen_violations.update(violations)
        if violations:
            assert route is Route.EXCEPTION
        elif asks:
            assert route is Route.CLARIFICATION
        else:
            assert route is Route.TOUCHLESS
        if Ask.DELIVERY_SITE in asks:
            assert scenario.flags.ambiguous_site
    assert seen_routes == {Route.TOUCHLESS, Route.CLARIFICATION, Route.EXCEPTION}
    assert {
        Violation.DISCONTINUED,
        Violation.BELOW_MOQ,
        Violation.ABOVE_MAX,
        Violation.UNRESOLVABLE_PRODUCT,
        Violation.UNRESOLVABLE_UNIT,
    } <= seen_violations


def test_unit_mismatch_is_derivable(catalog: Catalog, book: CustomerBook) -> None:
    item = LineItemScenario(
        sku="TPE-CLR-201",
        product_surface="clear tape",
        mention_style=MentionStyle.ALIAS,
        typo=False,
        quantity_value=5000,
        quantity_surface="5000",
        unit_surface="pallets",
        unit_style=UnitStyle.ALIAS,
        item_note=None,
        intended_packs=None,
    )
    scenario = OrderScenario(
        scenario_id="SCN-999999",
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
        flags=ScenarioFlags(),
    )
    violations = scenario.expected_violations(catalog)
    assert violations == [Violation.UNIT_MISMATCH]
    assert scenario.expected_route(catalog, book) is Route.EXCEPTION


def test_dates_are_truth_first(corpus: list[OrderScenario]) -> None:
    seen: set[DateStyle] = set()
    for scenario in corpus:
        seen.add(scenario.date_style)
        if scenario.date_style is DateStyle.NONE:
            assert scenario.date_phrase is None and scenario.intended_date is None
        elif scenario.date_style is DateStyle.VAGUE:
            assert scenario.date_phrase is not None and scenario.intended_date is None
        elif scenario.date_style is DateStyle.ABSOLUTE:
            assert scenario.intended_date is not None
            delta = (scenario.intended_date - scenario.sent_at.date()).days
            assert 3 <= delta <= 14
            expected = f"{scenario.intended_date.day} {scenario.intended_date:%B}"
            assert scenario.date_phrase == expected
        else:
            assert scenario.intended_date is not None
            delta = (scenario.intended_date - scenario.sent_at.date()).days
            assert scenario.date_phrase == RELATIVE_PHRASES[delta]
    assert seen == set(DateStyle)


def test_po_surfaces_match_customer_templates(
    corpus: list[OrderScenario], book: CustomerBook
) -> None:
    for scenario in corpus:
        customer = book.resolve_customer(scenario.sender_email)
        assert customer is not None
        if scenario.po_surface is not None:
            assert customer.po_template is not None
            assert po_regex(customer.po_template).fullmatch(scenario.po_surface)


def test_ids_and_timestamps_are_stable_shape(corpus: list[OrderScenario]) -> None:
    for index, scenario in enumerate(corpus):
        assert scenario.scenario_id == f"SCN-{index:06d}"
        assert scenario.sent_at.year == 2026
        assert scenario.sent_at.utcoffset() in (timedelta(hours=10), timedelta(hours=11))
        assert 7 <= scenario.sent_at.hour <= 17


def test_surface_style_coverage(corpus: list[OrderScenario]) -> None:
    assert {i.mention_style for s in corpus for i in s.items} == set(MentionStyle)
    assert {i.unit_style for s in corpus for i in s.items} == set(UnitStyle)
    assert {s.address_style for s in corpus} == set(AddressStyle)


def test_trap_piece_counts_never_yield_range_violations(
    corpus: list[OrderScenario], catalog: Catalog
) -> None:
    checked = 0
    for scenario in corpus:
        traps = [i for i in scenario.items if i.intended_packs is not None]
        if not traps:
            continue
        isolated = scenario.model_copy(update={"items": traps})
        violations = isolated.expected_violations(catalog)
        assert Violation.UNRESOLVABLE_UNIT in violations
        assert Violation.ABOVE_MAX not in violations
        assert Violation.BELOW_MOQ not in violations
        checked += 1
    assert checked > 0


def test_injection_ledger_reconciles_per_scenario(
    corpus: list[OrderScenario], catalog: Catalog
) -> None:
    for scenario in corpus:
        violations = scenario.expected_violations(catalog)
        typo_items = [i for i in scenario.items if i.typo]
        trap_items = [i for i in scenario.items if i.intended_packs is not None]
        inactive_items = [i for i in scenario.items if not catalog.resolve_sku(i.sku).active]
        assert violations.count(Violation.UNRESOLVABLE_PRODUCT) == len(typo_items)
        assert violations.count(Violation.UNRESOLVABLE_UNIT) == len(trap_items)
        assert violations.count(Violation.DISCONTINUED) == len(inactive_items)

        for flag_name, violation, direction in (
            ("qty_below_moq", Violation.BELOW_MOQ, "below"),
            ("qty_above_max", Violation.ABOVE_MAX, "above"),
        ):
            flagged = getattr(scenario.flags, flag_name)
            if violation in violations:
                assert flagged, (flag_name, scenario.scenario_id)
            if flagged and violation not in violations:
                masks = []
                for item in typo_items:
                    if item.quantity_value is None or item.intended_packs is not None:
                        continue
                    product = catalog.resolve_sku(item.sku)
                    assert product is not None
                    breach = (
                        item.quantity_value < product.moq
                        if direction == "below"
                        else item.quantity_value > product.max_qty
                    )
                    if breach:
                        masks.append(item)
                assert masks, (flag_name, scenario.scenario_id)
