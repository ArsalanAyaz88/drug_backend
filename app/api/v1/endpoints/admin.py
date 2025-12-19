from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.services.settings import get_setting, set_setting
from app.services.settings_provider import settings_provider

router = APIRouter()


class SettingsQuery(BaseModel):
    keys: List[str]


class SettingIn(BaseModel):
    key: str
    value: str


@router.get("/settings")
def get_settings(keys: Optional[str] = None, db: Session = Depends(db_session), current_user: User = Depends(get_current_user)):
    # keys: comma-separated string
    if not keys:
        return {}
    result = {}
    for k in [k.strip() for k in keys.split(',') if k.strip()]:
        result[k] = get_setting(db, k, None)
    return result


@router.post("/settings")
def set_settings(item: SettingIn, db: Session = Depends(db_session), current_user: User = Depends(get_current_user)):
    row = set_setting(db, item.key, item.value)
    # refresh provider cache for this key
    settings_provider.reload(keys=[item.key])
    return {"key": row.key, "value": row.value}
