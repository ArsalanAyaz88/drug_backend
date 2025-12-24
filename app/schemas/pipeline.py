from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel


class PipelineJobOut(BaseModel):
    id: int
    user_id: int
    protein_id: int
    status: str
    current_step: Optional[str] = None
    strategy: Optional[str] = None
    progress: float
    message: Optional[str] = None
    results: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PipelineRunRequest(BaseModel):
    protein_id: int
    max_molecules: int = 10
    pocket: Optional[Dict[str, Any]] = None
