"""File-based storage for Fortnox OAuth tokens.

Fortnox refresh tokens are single-use: every refresh returns a new pair that
must be persisted immediately, so all writes go through an atomic replace.
"""

import json
import os
import tempfile
import time
from dataclasses import asdict, dataclass

from .config import DATA_DIR

TOKENS_PATH = DATA_DIR / "tokens.json"


@dataclass
class Tokens:
    access_token: str
    refresh_token: str
    expires_at: float  # unix timestamp
    scope: str = ""

    @property
    def is_expired(self) -> bool:
        # 60s safety margin so we never send a token about to lapse
        return time.time() >= self.expires_at - 60


def save(tokens: Tokens) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(asdict(tokens), f)
    os.replace(tmp, TOKENS_PATH)


def load() -> Tokens | None:
    try:
        with open(TOKENS_PATH) as f:
            return Tokens(**json.load(f))
    except (FileNotFoundError, json.JSONDecodeError, TypeError):
        return None


def clear() -> None:
    TOKENS_PATH.unlink(missing_ok=True)
