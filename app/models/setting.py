from sqlalchemy import Column, Integer, String, DateTime, func, UniqueConstraint
from app.db.base_class import Base

class Setting(Base):
    __tablename__ = "settings"
    __table_args__ = (UniqueConstraint("key", name="uq_settings_key"),)

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(128), nullable=False, index=True)
    value = Column(String(2048), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
