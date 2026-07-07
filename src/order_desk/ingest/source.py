"""Pluggable email sources (Phase 6).

The pipeline consumes standardized emails regardless of where the raw message
came from. EmailSource abstracts that origin: a directory of .eml files is one
implementation; IMAP is another, left as an interface (decision A -- the
architecture supports a real mailbox without wiring credentials here).
"""

from __future__ import annotations

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
    """IMAP mailbox source -- interface only, not implemented.

    A production implementation would connect over IMAP (imaplib), SELECT the
    inbox, FETCH unseen messages (e.g. `SEARCH UNSEEN` then `FETCH (RFC822)`),
    yield each raw message, and mark it seen. Credentials would come from the
    environment, never from code or version control. It is deliberately left
    unimplemented: transport is a replaceable detail, and wiring a live mailbox
    needs credentials that break reproducibility. The standardization layer and
    the rest of the pipeline are identical whatever the source.
    """

    def __init__(self, host: str, username: str, password: str, mailbox: str = "INBOX") -> None:
        self.host = host
        self.username = username
        self.mailbox = mailbox
        self._password = password

    def fetch(self) -> Iterator[str]:
        raise NotImplementedError(
            "ImapSource is an interface stub; implement IMAP fetch for a live mailbox"
        )
