"""Fulfillment notifications (Phase 8).

Notify people when an order reaches the ERP or needs manual attention. Notifier
abstracts the destination, mirroring the tracing layer (Noop vs Langfuse):
MockNotifier records messages for offline tests, SlackWebhookNotifier is the
real path -- it POSTs to a Slack incoming-webhook URL read from the environment.
The webhook is outbound and self-contained, so it is fully reproducible: anyone
can point WEBHOOK at their own workspace's incoming webhook and see the messages
in their channel.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class NotifyEvent(StrEnum):
    ORDER_SUBMITTED = "order_submitted"
    NEEDS_MAPPING = "needs_mapping"


@dataclass
class Notification:
    event: NotifyEvent
    text: str


def order_submitted_message(po: str | None, order_id: str, n_lines: int, total_cents: int) -> str:
    ref = po or "(no PO)"
    dollars = f"${total_cents / 100:,.2f}"
    return (
        f"Order {ref} accepted into the ERP as {order_id} "
        f"— {n_lines} line{'s' if n_lines != 1 else ''}, {dollars}."
    )


def needs_mapping_message(po: str | None, unresolved: list[str], issues: list[str]) -> str:
    ref = po or "(no PO)"
    parts = []
    if unresolved:
        parts.append(f"{len(unresolved)} product(s) not matched to a SKU: {', '.join(unresolved)}")
    if issues:
        parts.append(f"{len(issues)} quantity issue(s): {', '.join(issues)}")
    detail = "; ".join(parts)
    return f"Order {ref} held for manual mapping — {detail}."


class Notifier(Protocol):
    def send(self, notification: Notification) -> None:
        """Deliver a notification."""
        ...


class MockNotifier:
    """Records notifications in memory for tests; sends nothing."""

    def __init__(self) -> None:
        self.sent: list[Notification] = []

    def send(self, notification: Notification) -> None:
        self.sent.append(notification)


class SlackWebhookNotifier:
    """Posts to a Slack incoming-webhook URL (the real path)."""

    def __init__(self, webhook_url: str, timeout: float = 10.0) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    def send(self, notification: Notification) -> None:
        payload = json.dumps({"text": notification.text}).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url, data=payload, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Slack webhook returned {resp.status}")


def build_notifier(webhook_url: str | None) -> Notifier:
    """Real notifier if a webhook is configured, else a mock that no-ops."""
    if webhook_url:
        return SlackWebhookNotifier(webhook_url)
    return MockNotifier()
