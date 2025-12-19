from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.workspace import Workspace as WorkspaceModel
from app.schemas.workspace import WorkspaceCreate, WorkspaceOut

router = APIRouter()


@router.get("/", response_model=List[WorkspaceOut])
def list_workspaces(
    db: Session = Depends(db_session), current_user: User = Depends(get_current_user)
):
    items = db.query(WorkspaceModel).filter(WorkspaceModel.owner_id == current_user.id).all()
    return items


@router.post("/", response_model=WorkspaceOut)
def create_workspace(
    ws: WorkspaceCreate,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    item = WorkspaceModel(name=ws.name, owner_id=current_user.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
