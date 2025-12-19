from __future__ import annotations
from typing import Optional, Dict
from threading import RLock
from app.db.session import SessionLocal
from app.services.settings import get_setting

class SettingsProvider:
    _cache: Dict[str, Optional[str]] = {}
    _lock = RLock()

    IMPORTANT_KEYS = {
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "QDRANT_COLLECTION",
        "CHEMBERT_MODEL",
        "VINA_PATH",
        "VINA_EXHAUSTIVENESS",
        "VINA_CENTER",
        "VINA_SIZE",
    }

    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        with cls._lock:
            if key in cls._cache:
                return cls._cache[key]
        # lazy load if not cached
        cls.reload(keys=[key])
        with cls._lock:
            return cls._cache.get(key, default)

    @classmethod
    def reload(cls, keys: Optional[list[str]] = None) -> None:
        with cls._lock:
            db = SessionLocal()
            try:
                target_keys = keys or list(cls.IMPORTANT_KEYS)
                for k in target_keys:
                    val = get_setting(db, k, None)
                    if val is not None:
                        cls._cache[k] = val
            finally:
                db.close()

# Convenience instance-like access
settings_provider = SettingsProvider
