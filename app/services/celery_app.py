from __future__ import annotations
from typing import Optional
import os

try:
    from celery import Celery
except Exception:  # pragma: no cover - optional dependency
    Celery = None  # type: ignore

from app.services.settings_provider import settings_provider

_CELERY: Optional["Celery"] = None


def get_celery() -> Optional["Celery"]:
    global _CELERY
    if _CELERY is not None:
        return _CELERY
    if Celery is None:
        return None
    broker = settings_provider.get("CELERY_BROKER_URL") or os.environ.get("CELERY_BROKER_URL")
    backend = settings_provider.get("CELERY_RESULT_BACKEND") or os.environ.get("CELERY_RESULT_BACKEND")
    if not broker:
        return None
    app = Celery("druggenix", broker=broker, backend=backend or None)
    # Minimal config; users can extend via env
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
    )
    _CELERY = app
    return _CELERY
