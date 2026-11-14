import time
from collections.abc import Callable, Hashable


class TTLCache[V]:
    """In-memory cache whose entries expire `ttl` seconds after being stored.

    Holds at most `max_size` entries and, when `sizeof` is given, at most
    `max_bytes` in total, evicting the oldest first, so distinct keys (e.g. junk
    query params) can't grow it without bound.
    """

    def __init__(
        self,
        ttl: float,
        max_size: int = 1024,
        max_bytes: int | None = None,
        sizeof: Callable[[V], int] | None = None,
    ) -> None:
        self.ttl = ttl
        self.max_size = max_size
        self.max_bytes = max_bytes
        self._sizeof = sizeof
        self._bytes = 0
        # key -> (stored at, value, size); insertion order == age order,
        # because `set` re-inserts updated keys at the end
        self._data: dict[Hashable, tuple[float, V, int]] = {}

    def get(self, key: Hashable) -> V | None:
        entry = self.get_entry(key)
        return entry[0] if entry is not None else None

    def get_entry(self, key: Hashable) -> tuple[V, float] | None:
        """-> (value, seconds until it expires), or None on a miss."""
        hit = self._data.get(key)
        if hit is None:
            return None
        left = self.ttl - (time.monotonic() - hit[0])
        if left <= 0:
            self._delete(key)
            return None
        return hit[1], left

    def set(self, key: Hashable, value: V) -> None:
        now = time.monotonic()
        size = self._sizeof(value) if self._sizeof is not None else 0
        self._delete(key)
        self._data[key] = (now, value, size)
        self._bytes += size

        # oldest entries sit at the front: drop expired or over-budget ones there,
        # stopping at the first live one, so this is cheap rather than a full scan
        while self._data:
            oldest, (t, _, _) = next(iter(self._data.items()))
            if now - t < self.ttl and not self._over_budget():
                break
            self._delete(oldest)

    def _over_budget(self) -> bool:
        too_big = self.max_bytes is not None and self._bytes > self.max_bytes
        return too_big or len(self._data) > self.max_size

    def _delete(self, key: Hashable) -> None:
        if (entry := self._data.pop(key, None)) is not None:
            self._bytes -= entry[2]
