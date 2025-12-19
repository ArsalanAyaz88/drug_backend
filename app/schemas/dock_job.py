from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DockJobBase(BaseModel):
    protein_id: int
    molecule_id: int

class DockJobCreate(DockJobBase):
    pass

class DockJobOut(DockJobBase):
    id: int
    status: str
    score: Optional[float] = None
    pose_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
