"""Pluggable email sources (Phase 6).

The pipeline consumes standardized emails regardless of where the raw message
came from. EmailSource abstracts that origin: a directory of .eml files is one
implementation; IMAP is another, left as an interface (decision A -- the
architecture supports a real mailbox without wiring credentials here).
"""

from __future__ import annotations

import imaplib
from collections.abc import Iterator
from pathlib import Path
from typing import Protocol


class EmailSource(Protocol):
    def fetch(self) -> Iterator[str]:
        """Yield raw RFC 822 message strings."""
        ...


class EmlDirectorySource:
    """Read .eml files from a directory, sorted by name for determinism."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)

    def fetch(self) -> Iterator[str]:
        for path in sorted(self.directory.glob("*.eml")):
            yield path.read_text(encoding="utf-8")


class ImapSource:
    """Live IMAP mailbox source: yield unseen messages, newest run first seen.

    Connects over IMAP-SSL, SELECTs the mailbox, SEARCHes UNSEEN and FETCHes
    each as RFC822 (which marks it \\Seen server-side, so a message is consumed
    once). Credentials come from the caller -- typically the environment, never
    code or version control.
    """

    def __init__(self, host: str, username: str, password: str, mailbox: str = "INBOX") -> None:
        self.host = host
        self.username = username
        self.mailbox = mailbox
        self._password = password

    def fetch(self, limit: int | None = None) -> Iterator[str]:
        """Yield unseen messages; `limit` keeps only the most recent ones."""
        conn = imaplib.IMAP4_SSL(self.host)
        try:
            conn.login(self.username, self._password)
            conn.select(self.mailbox)
            _, data = conn.search(None, "UNSEEN")
            nums = data[0].split()
            if limit is not None:
                nums = nums[-limit:]  # highest sequence numbers = most recent
            for num in nums:
                _, msg_data = conn.fetch(num, "(RFC822)")
                yield msg_data[0][1].decode("utf-8", errors="replace")
        finally:
            conn.logout()
