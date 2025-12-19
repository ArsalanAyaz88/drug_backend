from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.admet import AdmetResult as AdmetModel
from app.schemas.user import UserOut
from app.models.molecule import Molecule as MoleculeModel
from app.services.admet_service import predict_admet_for_smiles

router = APIRouter()


class AdmetRequest(BaseModel):
    molecule_id: int


class AdmetResponse(BaseModel):
    id: int
    molecule_id: int
    solubility: float
    toxicity: float
    clearance: float


@router.post("/predict", response_model=AdmetResponse)
def predict_admet(
    req: AdmetRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    # Fetch molecule SMILES
    mol = db.query(MoleculeModel).filter(MoleculeModel.id == req.molecule_id).first()
    if not mol:
        raise HTTPException(status_code=404, detail="Molecule not found")

    # Real ADMET-AI inference (CPU)
    try:
        res = predict_admet_for_smiles(mol.smiles)
    except RuntimeError as e:
        msg = str(e)
        if "admet-ai not available" in msg.lower():
            raise HTTPException(status_code=503, detail="ADMET-AI is not installed on the server. Please install 'admet-ai' to enable this feature.")
        if "admet-ai import failed" in msg.lower():
            raise HTTPException(status_code=500, detail=f"ADMET-AI is installed but failed to import: {e}")
        raise
    sol = res.get("solubility") if res else None
    tox = res.get("toxicity") if res else None
    clr = res.get("clearance") if res else None
    rec = AdmetModel(
        molecule_id=req.molecule_id,
        user_id=current_user.id,
        solubility=sol if sol is not None else 0.0,
        toxicity=tox if tox is not None else 0.0,
        clearance=clr if clr is not None else 0.0,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return AdmetResponse(
        id=rec.id,
        molecule_id=rec.molecule_id,
        solubility=rec.solubility or 0.0,
        toxicity=rec.toxicity or 0.0,
        clearance=rec.clearance or 0.0,
    )
