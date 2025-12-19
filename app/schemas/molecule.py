from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class MoleculeBase(BaseModel):
    smiles: str
    generated_for_protein_id: Optional[int] = None

class MoleculeCreate(MoleculeBase):
    pass

class MoleculeOut(MoleculeBase):
    id: int
    score: Optional[float] = None
    created_at: datetime

    class Config:
        from_attributes = True
