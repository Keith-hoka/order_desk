"""Render contract-verified samples of each non-order shape for eyeballing."""

import argparse

from order_desk.nonorder import (
    InquiryType,
    OtherType,
    generate_amendments,
    generate_cancellations,
    generate_inquiries,
    generate_others,
    render_amendment,
    render_cancellation,
    render_inquiry,
    render_other,
    verify_amendment,
    verify_cancellation,
    verify_inquiry,
    verify_other,
)


def show(label: str, sender: str, rendered) -> None:
    print("=" * 72)
    print(f"{rendered.scenario_id}  {label}")
    print(f"From: {sender}")
    print(f"Subject: {rendered.subject}")
    print("-" * 72)
    print(rendered.body)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20260704)
    parser.add_argument("--render-seed", type=int, default=77)
    args = parser.parse_args()

    amendments = generate_amendments(60, seed=args.seed)
    with_po = next(a for a in amendments if a.referenced_po is not None)
    temporal = next(a for a in amendments if a.temporal_ref is not None)
    for scenario in (with_po, temporal):
        rendered = render_amendment(scenario, args.render_seed)
        verify_amendment(scenario, rendered)
        show(f"amendment / {scenario.change_type.value}", scenario.sender_email, rendered)

    cancellations = generate_cancellations(40, seed=args.seed)
    no_po = next(c for c in cancellations if c.referenced_po is None)
    rendered = render_cancellation(no_po, args.render_seed)
    verify_cancellation(no_po, rendered)
    show("cancellation / temporal ref", no_po.sender_email, rendered)

    inquiries = generate_inquiries(40, seed=args.seed)
    quote = next(i for i in inquiries if i.inquiry_type is InquiryType.QUOTE_REQUEST)
    general = next(i for i in inquiries if i.inquiry_type is InquiryType.GENERAL)
    for scenario in (quote, general):
        rendered = render_inquiry(scenario, args.render_seed)
        verify_inquiry(scenario, rendered)
        show(f"inquiry / {scenario.inquiry_type.value}", scenario.sender_email, rendered)

    others = generate_others(40, seed=args.seed)
    misdirected = next(o for o in others if o.other_type is OtherType.MISDIRECTED)
    courier = next(o for o in others if o.other_type is OtherType.COURIER_NOTICE)
    for scenario in (misdirected, courier):
        rendered = render_other(scenario, args.render_seed)
        verify_other(scenario, rendered)
        show(f"other / {scenario.other_type.value}", scenario.sender_email, rendered)


if __name__ == "__main__":
    main()
