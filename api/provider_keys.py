"""Session-memory store for reviewer (BYOK) provider keys.

Keys live only in this process's memory, keyed by an opaque ref. A
provider_key_refs row records ownership/expiry so the leased worker can
fetch the key exactly once over the trusted channel. Nothing here is
persisted, logged, or sent to containers.
"""

import secrets
import time
from dataclasses import dataclass

from . import config


@dataclass
class KeyEntry:
    key: str
    user_id: str
    expires_at: float


_store: dict[str, KeyEntry] = {}


def put(user_id: str, api_key: str) -> str:
    """Store a key and return its opaque reference."""
    _purge()
    ref = secrets.token_urlsafe(24)
    _store[ref] = KeyEntry(
        key=api_key,
        user_id=user_id,
        expires_at=time.monotonic() + config.PROVIDER_KEY_TTL_SECONDS,
    )
    return ref


def get(ref: str) -> KeyEntry | None:
    _purge()
    return _store.get(ref)


def remove(ref: str) -> None:
    _store.pop(ref, None)


def remove_for_user(user_id: str) -> int:
    doomed = [r for r, e in _store.items() if e.user_id == user_id]
    for r in doomed:
        _store.pop(r, None)
    return len(doomed)


def _purge() -> None:
    now = time.monotonic()
    for ref in [r for r, e in _store.items() if e.expires_at <= now]:
        _store.pop(ref, None)
