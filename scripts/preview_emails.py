"""Render sample emails for eyeballing; every email is contract-verified first."""

import argparse

from order_desk.renderer import render_email, verify_rendering
from order_desk.scenarios import generate_scenarios


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario-seed", type=int, default=20260702)
    parser.add_argument("--render-seed", type=int, default=31)
    parser.add_argument("--count", type=int, default=4)
    args = parser.parse_args()

    for scenario in generate_scenarios(args.count, seed=args.scenario_seed):
        email = render_email(scenario, args.render_seed)
        verify_rendering(scenario, email)
        placement = email.po_placement.value if email.po_placement else "-"
        print("=" * 72)
        print(f"{email.scenario_id}  layout={email.layout.value}  po={placement}")
        print(f"Subject: {email.subject}")
        print("-" * 72)
        print(email.body)


if __name__ == "__main__":
    main()
