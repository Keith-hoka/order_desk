"""Realized-rate report: what the config promises vs what the corpus does."""

import argparse
from collections import Counter

from order_desk.catalog import load_catalog
from order_desk.customers import load_customers
from order_desk.scenarios import ScenarioFlags, generate_scenarios


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
        print(f"  {name:<20} {flag_counts[name] / n:6.3f}")
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


if __name__ == "__main__":
    main()
