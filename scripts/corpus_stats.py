"""Realized-rate report: what the config promises vs what the corpus does."""

import argparse
import sys
from collections import Counter

from order_desk.catalog import Catalog, load_catalog
from order_desk.customers import load_customers
from order_desk.scenarios import (
    LineItemScenario,
    OrderScenario,
    ScenarioFlags,
    Violation,
    generate_scenarios,
)


def _typo_masks_range_truth(item: LineItemScenario, catalog: Catalog, violation: Violation) -> bool:
    """True when a corrupted mention hides a truth-level range breach."""
    if not item.typo or item.quantity_value is None or item.intended_packs is not None:
        return False
    product = catalog.resolve_sku(item.sku)
    assert product is not None, item.sku
    if violation is Violation.BELOW_MOQ:
        return item.quantity_value < product.moq
    return item.quantity_value > product.max_qty


def _injection_ledger(corpus: list[OrderScenario], catalog: Catalog) -> tuple[list[str], list[str]]:
    """Exact accounting between injected noise flags and derivable violations.

    Range flags may be masked only by a typo landing on the out-of-range item
    (possible only when it is the sole normal item), verified against the true
    SKU. The remaining pairs must correspond one-to-one. Any other gap is an
    oracle or generator defect and fails the report.
    """
    lines: list[str] = []
    failures: list[str] = []

    for flag_name, violation in (
        ("qty_below_moq", Violation.BELOW_MOQ),
        ("qty_above_max", Violation.ABOVE_MAX),
    ):
        flagged = [s for s in corpus if getattr(s.flags, flag_name)]
        violated, masked, unexplained = 0, 0, []
        for scenario in flagged:
            if violation in scenario.expected_violations(catalog):
                violated += 1
            elif any(_typo_masks_range_truth(i, catalog, violation) for i in scenario.items):
                masked += 1
            else:
                unexplained.append(scenario.scenario_id)
        lines.append(
            f"  {flag_name:<20} flagged {len(flagged):>4}   "
            f"violated {violated:>4}   typo-masked {masked:>4}"
        )
        if unexplained:
            failures.append(f"{flag_name} unexplained: {unexplained}")

    instances = Counter(v for s in corpus for v in s.expected_violations(catalog))
    for flag_name, violation in (
        ("mention_typo", Violation.UNRESOLVABLE_PRODUCT),
        ("pack_size_trap", Violation.UNRESOLVABLE_UNIT),
        ("discontinued_item", Violation.DISCONTINUED),
        ("price_mismatch", Violation.PRICE_MISMATCH),
    ):
        flagged_n = sum(getattr(s.flags, flag_name) for s in corpus)
        count = instances[violation]
        lines.append(f"  {flag_name:<20} flagged {flagged_n:>4}   instances {count:>4}")
        if flagged_n != count:
            failures.append(f"{flag_name} {flagged_n} != {violation.value} {count}")

    return lines, failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260703)
    parser.add_argument("--count", type=int, default=2000)
    args = parser.parse_args()

    catalog, book = load_catalog(), load_customers()
    corpus = generate_scenarios(args.count, seed=args.seed)
    n = len(corpus)

    flag_counts: Counter[str] = Counter()
    for scenario in corpus:
        for name, value in scenario.flags.model_dump().items():
            flag_counts[name] += bool(value)
    routes = Counter(s.expected_route(catalog, book).value for s in corpus)
    violations = Counter(v.value for s in corpus for v in s.expected_violations(catalog))
    asks = Counter(a.value for s in corpus for a in s.expected_asks(book))
    items_per = Counter(len(s.items) for s in corpus)

    print(f"scenarios: {n} (seed {args.seed})")
    print("\nflag rates:")
    for name in ScenarioFlags.model_fields:
        print(f"  {name:<20} {flag_counts[name]:>4}  {flag_counts[name] / n:6.3f}")
    print("\nroutes:")
    for name, count in routes.most_common():
        print(f"  {name:<20} {count / n:6.3f}")
    print("\nviolations per 1k scenarios:")
    for name, count in violations.most_common():
        print(f"  {name:<22} {1000 * count / n:6.1f}")
    print("\nasks per 1k scenarios:")
    for name, count in asks.most_common():
        print(f"  {name:<20} {1000 * count / n:6.1f}")
    print("\nitems per order:")
    for k in sorted(items_per):
        print(f"  {k}: {items_per[k] / n:6.3f}")

    lines, failures = _injection_ledger(corpus, catalog)
    print("\ninjection ledger (flags vs derivable violations):")
    for line in lines:
        print(line)
    if failures:
        sys.exit("LEDGER FAILURE: " + "; ".join(failures))


if __name__ == "__main__":
    main()
