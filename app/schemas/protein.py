from pydantic import BaseModel
from datetime import datetime

class ProteinBase(BaseModel):
    filename: str
    format: str

class ProteinOut(ProteinBase):
    id: int
    path: str
    created_at: datetime

    class Config:
        from_attributes = True
