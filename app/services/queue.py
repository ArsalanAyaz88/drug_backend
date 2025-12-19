from __future__ import annotations
from typing import Optional
import os

try:
    import redis
    from rq import Queue
except Exception:  # pragma: no cover - optional dependency
    redis = None
    Queue = None  # type: ignore


_QUE: Optional[Queue] = None


def get_queue() -> Optional[Queue]:
    global _QUE
    if _QUE is not None:
        return _QUE
    if redis is None or Queue is None:
        return None
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    try:
        conn = redis.from_url(url)
        _QUE = Queue("druggenix", connection=conn)
        return _QUE
    except Exception:
        return None
