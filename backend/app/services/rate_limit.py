"""Limits failed sign-in attempts so passwords can't be guessed over and over.

Counts are kept in memory (no table), so they reset when the server restarts.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status

MAX_FAILURES_PER_ACCOUNT = 8   # wrong tries allowed for one email
MAX_FAILURES_PER_ADDRESS = 40  # or from one IP (higher because offices share one IP)
WINDOW_SECONDS = 15 * 60       # in 15 minutes


def _limit(key: str) -> int:
    return MAX_FAILURES_PER_ADDRESS if key.startswith("ip:") else MAX_FAILURES_PER_ACCOUNT


_attempts: dict[str, deque] = defaultdict(deque)
_lock = threading.Lock()


def _prune(q: deque, now: float) -> None:
    # drop tries older than 15 minutes
    while q and now - q[0] > WINDOW_SECONDS:
        q.popleft()


def check(*keys: str) -> None:
    """Raise 429 if any key has too many recent failures."""
    now = time.monotonic()
    with _lock:
        for key in keys:
            q = _attempts.get(key)
            if q is None:
                continue
            _prune(q, now)
            if len(q) >= _limit(key):
                wait = int(WINDOW_SECONDS - (now - q[0])) // 60 + 1
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"Too many sign-in attempts. Please wait about {wait} minute{'s' if wait != 1 else ''} and try again.",
                )


def record_failure(*keys: str) -> None:
    now = time.monotonic()
    with _lock:
        for key in keys:
            q = _attempts[key]
            _prune(q, now)
            q.append(now)


def reset(*keys: str) -> None:
    # called after a successful sign in
    with _lock:
        for key in keys:
            _attempts.pop(key, None)