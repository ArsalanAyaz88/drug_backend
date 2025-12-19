from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.protein import Protein as ProteinModel
from app.schemas.protein import ProteinOut
from app.services.storage import save_protein_file

router = APIRouter()


@router.post("/upload", response_model=ProteinOut)
def upload_protein(
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    name = file.filename.lower()
    if not (name.endswith(".pdb") or name.endswith(".cif")):
        raise HTTPException(status_code=400, detail="Only .pdb or .cif files are supported")
    path, fmt = save_protein_file(file)
    record = ProteinModel(
        filename=file.filename,
        path=path,
        format=fmt,
        uploader_id=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/", response_model=List[ProteinOut])
def list_proteins(
    db: Session = Depends(db_session), current_user: User = Depends(get_current_user)
):
    return db.query(ProteinModel).filter(ProteinModel.uploader_id == current_user.id).all()
