"""Code claims about small in-memory snippets.

Half the cases pair a real bug with a claim that correctly identifies it;
the other half pair a superficially similar but actually-safe snippet with
a claim that wrongly accuses it of the same bug — the near-miss is the
point, not the bug itself.
"""

from __future__ import annotations

from elenchus.bench.case import BenchCase
from elenchus.claim import Verdict

CASES: list[BenchCase] = [
    BenchCase(
        id="code-01",
        domain="code",
        assertion=(
            "The add_tag function in tags.py has a bug: the mutable default argument "
            "tags=[] is shared across every call that doesn't pass its own list."
        ),
        context="See tags.py.",
        files={
            "tags.py": (
                "def add_tag(item, tag, tags=[]):\n    tags.append((item, tag))\n    return tags\n"
            )
        },
        ideal_verdict=Verdict.UPHOLD,
        note="Real bug: classic mutable default argument.",
    ),
    BenchCase(
        id="code-02",
        domain="code",
        assertion=(
            "The increment function in counter.py has a mutable default argument bug, "
            "just like a naive counter=[] default would."
        ),
        context="See counter.py.",
        files={
            "counter.py": (
                "def increment(counter=None):\n"
                "    if counter is None:\n"
                "        counter = []\n"
                "    counter.append(1)\n"
                "    return counter\n"
            )
        },
        ideal_verdict=Verdict.REJECT,
        note="counter=None + reinitialize inside is the correct, safe pattern.",
    ),
    BenchCase(
        id="code-03",
        domain="code",
        assertion=(
            "paginate in pages.py has an off-by-one bug: since Python slicing excludes "
            "the end index, subtracting 1 from end drops the last item of every page."
        ),
        context="See pages.py.",
        files={
            "pages.py": (
                "def paginate(items, page, per_page):\n"
                "    start = (page - 1) * per_page\n"
                "    end = start + per_page - 1\n"
                "    return items[start:end]\n"
            )
        },
        ideal_verdict=Verdict.UPHOLD,
        note="Real bug: the extra -1 drops the last item.",
    ),
    BenchCase(
        id="code-04",
        domain="code",
        assertion=(
            "paginate in pages2.py has an off-by-one bug: it returns one extra item per "
            "page beyond what per_page should allow."
        ),
        context="See pages2.py.",
        files={
            "pages2.py": (
                "def paginate(items, page, per_page):\n"
                "    start = (page - 1) * per_page\n"
                "    end = start + per_page\n"
                "    return items[start:end]\n"
            )
        },
        ideal_verdict=Verdict.REJECT,
        note="This version has no -1; it's the correct slice.",
    ),
    BenchCase(
        id="code-05",
        domain="code",
        assertion=(
            "is_expired in session.py will raise a TypeError if expires_at is "
            "timezone-aware, because datetime.utcnow() returns a naive datetime and "
            "Python won't compare naive and aware datetimes."
        ),
        context="See session.py.",
        files={
            "session.py": (
                "from datetime import datetime\n\n"
                "def is_expired(expires_at):\n"
                "    return expires_at < datetime.utcnow()\n"
            )
        },
        ideal_verdict=Verdict.UPHOLD,
        note="Real bug: datetime.utcnow() is naive.",
    ),
    BenchCase(
        id="code-06",
        domain="code",
        assertion=(
            "is_expired in session2.py will raise a TypeError when comparing expires_at "
            "against the current time, due to a naive/aware datetime mismatch."
        ),
        context="See session2.py.",
        files={
            "session2.py": (
                "from datetime import datetime, timezone\n\n"
                "def is_expired(expires_at):\n"
                "    return expires_at < datetime.now(timezone.utc)\n"
            )
        },
        ideal_verdict=Verdict.REJECT,
        note="datetime.now(timezone.utc) is aware; no mismatch if expires_at is aware too.",
    ),
    BenchCase(
        id="code-07",
        domain="code",
        assertion=(
            "bump in lock.py leaks the lock forever if key is not a string, because the "
            "TypeError is raised between acquire() and release() and the lock is never "
            "released on that path."
        ),
        context="See lock.py.",
        files={
            "lock.py": (
                "import threading\n"
                "_lock = threading.Lock()\n\n"
                "def bump(key, counts):\n"
                "    _lock.acquire()\n"
                "    if not isinstance(key, str):\n"
                '        raise TypeError("key must be a string")\n'
                "    counts[key] = counts.get(key, 0) + 1\n"
                "    _lock.release()\n"
            )
        },
        ideal_verdict=Verdict.UPHOLD,
        note="Real bug: no try/finally or context manager around the lock.",
    ),
    BenchCase(
        id="code-08",
        domain="code",
        assertion=(
            "bump in lock2.py can leave the lock permanently held if key is not a "
            "string, because the exception happens before the lock is released."
        ),
        context="See lock2.py.",
        files={
            "lock2.py": (
                "import threading\n"
                "_lock = threading.Lock()\n\n"
                "def bump(key, counts):\n"
                "    with _lock:\n"
                "        if not isinstance(key, str):\n"
                '            raise TypeError("key must be a string")\n'
                "        counts[key] = counts.get(key, 0) + 1\n"
            )
        },
        ideal_verdict=Verdict.REJECT,
        note="The `with` statement releases the lock even when the exception propagates.",
    ),
    BenchCase(
        id="code-09",
        domain="code",
        assertion=(
            "get_user in cache.py has a critical security vulnerability: it lets any "
            "authenticated user read any other user's private data through a crafted "
            "locale parameter, similar to a SQL injection attack."
        ),
        context="See cache.py.",
        files={
            "cache.py": (
                "_cache = {}\n\n"
                'def get_user(db, user_id, locale="en"):\n'
                '    key = f"user:{locale}"\n'
                "    if key not in _cache:\n"
                "        _cache[key] = db.fetch_user(user_id)\n"
                "    return _cache[key]\n"
            )
        },
        ideal_verdict=Verdict.REVISE,
        note=(
            "Real bug: the cache key omits user_id, so users sharing a locale are "
            "served each other's cached data - a cross-user data leak. But it is a "
            "caching/authorization bug, not remotely similar to SQL injection; the "
            "comparison should be struck, not the underlying finding."
        ),
    ),
    BenchCase(
        id="code-10",
        domain="code",
        assertion=(
            "notify_all in notify.py creates the send() coroutines but never awaits "
            "them, so no notifications are actually sent."
        ),
        context="See notify.py.",
        files={
            "notify.py": (
                "import asyncio\n\n"
                "async def send(email, message):\n"
                "    await asyncio.sleep(0)\n"
                '    return f"sent {message} to {email}"\n\n'
                "async def notify_all(emails, message):\n"
                "    for email in emails:\n"
                "        send(email, message)\n"
            )
        },
        ideal_verdict=Verdict.UPHOLD,
        note="Real bug: missing await, coroutine is created but never scheduled.",
    ),
]
