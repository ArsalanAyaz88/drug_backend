from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.molecule import Molecule as MoleculeModel
from app.models.protein import Protein as ProteinModel
from app.schemas.molecule import MoleculeOut
from app.services.chem import generate_molecules_placeholder
from app.services.pockets import detect_pockets
from app.services.target_features import analyze_pocket_features
from app.services.embedding import embed_smiles_chemberta
from app.services.qdrant_client import upsert_point, search_similar
from app.services.settings_provider import settings_provider
from app.services.export import smiles_iter_to_sdf_bytes

router = APIRouter()

class GenerateRequest(BaseModel):
    target_id: Optional[int] = Field(default=None, ge=1)
    protein_id: Optional[int] = Field(default=None, ge=1)
    num: int = Field(default=5, ge=1, le=100)
    pocket: Optional[Dict[str, Any]] = None
    pocket_idx: Optional[int] = Field(default=None, ge=0)


@router.post("/generate", response_model=List[MoleculeOut])
def generate_molecules(
    req: GenerateRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    if req.protein_id is not None and req.target_id is not None and req.protein_id != req.target_id:
        raise HTTPException(status_code=400, detail="Provide only one of protein_id or target_id")

    protein_id = req.protein_id if req.protein_id is not None else req.target_id
    if req.pocket_idx is not None and protein_id is None:
        raise HTTPException(status_code=400, detail="pocket_idx requires protein_id")

    pocket = req.pocket
    pocket_for_gen = pocket

    if protein_id is not None:
        prot = (
            db.query(ProteinModel)
            .filter(ProteinModel.id == protein_id, ProteinModel.uploader_id == current_user.id)
            .first()
        )
        if not prot:
            raise HTTPException(status_code=404, detail="Protein not found")
        if pocket is None:
            pockets = detect_pockets(prot.path)
            if not pockets:
                raise HTTPException(status_code=404, detail="No pockets detected")
            idx = req.pocket_idx if req.pocket_idx is not None else 0
            if idx < 0 or idx >= len(pockets):
                raise HTTPException(status_code=400, detail="Invalid pocket_idx")
            pocket = pockets[idx]
        features = analyze_pocket_features(prot.path, pocket) if pocket else {}
        pocket_for_gen = ({**pocket, "features": features} if pocket and features else pocket)

    target_marker = str(protein_id) if protein_id is not None else ("pocket" if pocket_for_gen else None)
    smiles_list = generate_molecules_placeholder(target_marker, req.num, pocket=pocket_for_gen)
    created: List[MoleculeModel] = []
    for s in smiles_list:
        m = MoleculeModel(
            smiles=s,
            generated_for_protein_id=protein_id,
            creator_id=current_user.id,
        )
        db.add(m)
        db.flush()  # obtain ID before commit
        # Real ChemBERTa embedding on CPU and Qdrant upsert (if available)
        model_name = settings_provider.get("CHEMBERT_MODEL") or None
        try:
            emb = embed_smiles_chemberta(s, model_name)
            upsert_point(id_=m.id, vector=emb, payload={"smiles": s, "user_id": current_user.id})
        except Exception:
            # Continue even if embedding/upsert fails
            pass
        created.append(m)
    db.commit()
    for m in created:
        db.refresh(m)
    return created


@router.get("/", response_model=List[MoleculeOut])
def list_molecules(
    db: Session = Depends(db_session), current_user: User = Depends(get_current_user)
):
    return (
        db.query(MoleculeModel)
        .filter(MoleculeModel.creator_id == current_user.id)
        .order_by(MoleculeModel.id.desc())
        .all()
    )


@router.get("/export.csv")
def export_molecules_csv(
    db: Session = Depends(db_session), current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(MoleculeModel)
        .filter(MoleculeModel.creator_id == current_user.id)
        .order_by(MoleculeModel.id.asc())
        .all()
    )
    csv = ["id,smiles,score"]
    for r in rows:
        csv.append(f"{r.id},{r.smiles},{'' if r.score is None else r.score}")
    content = "\n".join(csv) + "\n"
    return Response(content=content, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=molecules.csv"
    })


@router.get("/export.smi")
def export_molecules_smi(
    db: Session = Depends(db_session), current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(MoleculeModel)
        .filter(MoleculeModel.creator_id == current_user.id)
        .order_by(MoleculeModel.id.asc())
        .all()
    )
    lines = [f"{r.smiles} mol_{r.id}" for r in rows]
    content = "\n".join(lines) + "\n"
    return Response(content=content, media_type="text/plain", headers={
        "Content-Disposition": "attachment; filename=molecules.smi"
    })


class SearchRequest(BaseModel):
    smiles: str
    top_k: int = 10


@router.post("/search", response_model=List[int])
def search_molecules(
    req: SearchRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    try:
        model_name = settings_provider.get("CHEMBERT_MODEL") or None
        vec = embed_smiles_chemberta(req.smiles, model_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Embedding error: {e}")
    ids = search_similar(vector=vec, top_k=req.top_k, user_id=current_user.id)
    return ids


@router.get("/export.sdf")
def export_molecules_sdf(
    db: Session = Depends(db_session), current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(MoleculeModel)
        .filter(MoleculeModel.creator_id == current_user.id)
        .order_by(MoleculeModel.id.asc())
        .all()
    )
    sdf_bytes = smiles_iter_to_sdf_bytes(r.smiles for r in rows)
    return Response(content=sdf_bytes, media_type="chemical/x-mdl-sdfile", headers={
        "Content-Disposition": "attachment; filename=molecules.sdf"
    })
