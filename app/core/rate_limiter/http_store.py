import time
import threading


class InMemoryRateLimitStore:
    """Sliding window sederhana per key, disimpan di memori.

    Tiap key menyimpan daftar timestamp request. Request dianggap valid jika
    jumlah request dalam window (misal 60 detik) kurang dari limit.
    """

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self._limit = limit
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window_seconds

        with self._lock:
            timestamps = self._requests.setdefault(key, [])

            # buang timestamp yang sudah lewat window
            timestamps = [ts for ts in timestamps if ts > cutoff]
            self._requests[key] = timestamps

            if len(timestamps) >= self._limit:
                return False

            timestamps.append(now)
            return True
