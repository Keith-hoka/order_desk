"""Eyeball generated scenarios with their derived gold labels."""

import argparse
import json

from order_desk.catalog import load_catalog
from order_desk.customers import load_customers
from order_desk.scenarios import generate_scenarios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--count", type=int, default=3)
    args = parser.parse_args()

    catalog, book = load_catalog(), load_customers()
    for scenario in generate_scenarios(args.count, seed=args.seed):
        payload = {
            "scenario": scenario.model_dump(mode="json"),
            "gold_extraction": scenario.gold_extraction().model_dump(),
            "expected_asks": [a.value for a in scenario.expected_asks(book)],
            "expected_violations": [v.value for v in scenario.expected_violations(catalog)],
            "expected_route": scenario.expected_route(catalog, book).value,
        }
        print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
