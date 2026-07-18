"""Per-org settings a customer configures from the UI (currently: the Slack
webhook fulfilment notifies).

Deliberately separate from the OrgStore: that record drives quota enforcement
(and an unknown org is unlimited by design), so storing UI settings there
would silently change a tenant's quota the moment they saved a webhook.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


EMPTY_MAILBOX = {"host": "", "address": "", "password": ""}


class OrgSettings(Protocol):
    def get_webhook(self, org_id: str) -> str: ...
    def set_webhook(self, org_id: str, url: str) -> None: ...
    def get_mailbox(self, org_id: str) -> dict: ...
    def set_mailbox(self, org_id: str, host: str, address: str, password: str) -> None: ...


class InMemoryOrgSettings:
    def __init__(self) -> None:
        self._webhooks: dict[str, str] = {}
        self._mailboxes: dict[str, dict] = {}

    def get_webhook(self, org_id: str) -> str:
        return self._webhooks.get(org_id, "")

    def set_webhook(self, org_id: str, url: str) -> None:
        self._webhooks[org_id] = url

    def get_mailbox(self, org_id: str) -> dict:
        return self._mailboxes.get(org_id, dict(EMPTY_MAILBOX))

    def set_mailbox(self, org_id: str, host: str, address: str, password: str) -> None:
        self._mailboxes[org_id] = {"host": host, "address": address, "password": password}


class JsonOrgSettings:
    """File-backed settings so a customer's webhook survives restarts."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        if self.path.exists():
            self._data: dict[str, dict] = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            self._data = {}

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def get_webhook(self, org_id: str) -> str:
        return self._data.get(org_id, {}).get("slack_webhook_url", "")

    def set_webhook(self, org_id: str, url: str) -> None:
        self._data.setdefault(org_id, {})["slack_webhook_url"] = url
        self._persist()

    def get_mailbox(self, org_id: str) -> dict:
        return self._data.get(org_id, {}).get("mailbox", dict(EMPTY_MAILBOX))

    def set_mailbox(self, org_id: str, host: str, address: str, password: str) -> None:
        # demo-grade plaintext at rest; a production deployment would encrypt
        # this file or hold the secret in a vault
        self._data.setdefault(org_id, {})["mailbox"] = {
            "host": host,
            "address": address,
            "password": password,
        }
        self._persist()
