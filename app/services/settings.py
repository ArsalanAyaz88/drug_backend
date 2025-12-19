from typing import Optional
from sqlalchemy.orm import Session
from app.models.setting import Setting


def get_setting(db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
    row = db.query(Setting).filter(Setting.key == key).first()
    return row.value if row else default


def set_setting(db: Session, key: str, value: str) -> Setting:
    row = db.query(Setting).filter(Setting.key == key).first()
    if row:
        row.value = value
    else:
        row = Setting(key=key, value=value)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row
