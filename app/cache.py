import time
from collections.abc import Hashable


class TTLCache[V]:
    """In-memory cache whose entries expire `ttl` seconds after being stored."""

    def __init__(self, ttl: float) -> None:
        self.ttl = ttl
        self._data: dict[Hashable, tuple[float, V]] = {}

    def get(self, key: Hashable) -> V | None:
        hit = self._data.get(key)
        if hit is None:
            return None
        if time.monotonic() - hit[0] >= self.ttl:
            del self._data[key]
            return None
        return hit[1]

    def set(self, key: Hashable, value: V) -> None:
        now = time.monotonic()
        # drop expired entries so memory holds at most one TTL's worth of distinct keys
        for k in [k for k, (t, _) in self._data.items() if now - t >= self.ttl]:
            del self._data[k]
        self._data[key] = (now, value)
