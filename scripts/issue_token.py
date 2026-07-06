"""Issue a dev/demo JWT for the extraction API (local convenience only).

Production token issuance belongs to an upstream identity system; this script
just signs a token with the local JWT_SECRET for testing and demos.
"""

import argparse
import os
import sys
from pathlib import Path

from order_desk.api.auth import issue_token


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sub", default="dev-client")
    parser.add_argument("--ttl", type=int, default=3600)
    args = parser.parse_args()

    load_dotenv()
    secret = os.environ.get("JWT_SECRET", "")
    if not secret:
        sys.exit("JWT_SECRET is not set (export it or put it in .env)")
    print(issue_token(secret, args.sub, ttl_seconds=args.ttl))


if __name__ == "__main__":
    main()
