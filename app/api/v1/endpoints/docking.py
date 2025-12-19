from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.dock_job import DockJob
from app.models.molecule import Molecule as MoleculeModel
from app.models.protein import Protein as ProteinModel
from app.schemas.dock_job import DockJobCreate, DockJobOut
from app.services.vina import dock_smiles_against_protein
from app.services.queue import get_queue
from app.services.tasks import task_run_docking
from app.services.export import pdbqt_to_sdf_bytes
from fastapi.responses import FileResponse, Response
import os
from app.services.celery_app import get_celery

router = APIRouter()


class DockRequest(BaseModel):
    protein_id: int
    molecule_id: int


@router.post("/run", response_model=DockJobOut)
def run_docking(
    req: DockRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    # Fetch inputs
    mol = db.query(MoleculeModel).filter(MoleculeModel.id == req.molecule_id).first()
    prot = db.query(ProteinModel).filter(ProteinModel.id == req.protein_id).first()
    if mol is None or prot is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Molecule or Protein not found")

    # Run Vina docking (CPU) and store pose
    pose_path, score = dock_smiles_against_protein(mol.smiles, prot.path)

    job = DockJob(
        protein_id=req.protein_id,
        molecule_id=req.molecule_id,
        user_id=current_user.id,
        status="completed",
        score=score,
        pose_path=pose_path,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/enqueue_celery", response_model=DockJobOut)
def enqueue_docking_celery(
    req: DockRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    # Create job with queued status
    job = DockJob(
        protein_id=req.protein_id,
        molecule_id=req.molecule_id,
        user_id=current_user.id,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    cel = get_celery()
    if cel is None:
        raise HTTPException(status_code=503, detail="Celery not available; set CELERY_BROKER_URL or use /enqueue")
    # Import inside function to ensure Celery app is initialized
    from app.services.celery_tasks import run_docking as celery_run_docking  # type: ignore
    # Use named task to avoid serialization of function
    cel.send_task("druggenix.run_docking", args=[job.id])
    return job


@router.post("/enqueue", response_model=DockJobOut)
def enqueue_docking(
    req: DockRequest,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    # Create job with queued status
    job = DockJob(
        protein_id=req.protein_id,
        molecule_id=req.molecule_id,
        user_id=current_user.id,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    q = get_queue()
    if q is None:
        raise HTTPException(status_code=503, detail="Queue not available; install Redis and RQ or run /run endpoint instead")
    q.enqueue(task_run_docking, job.id)
    return job


@router.get("/pose/{job_id}")
def download_pose(
    job_id: int,
    format: str = "pdbqt",
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    job = db.query(DockJob).filter(DockJob.id == job_id, DockJob.user_id == current_user.id).first()
    if not job or not job.pose_path:
        raise HTTPException(status_code=404, detail="Pose not found")
    pose_abs = os.path.abspath(job.pose_path)
    if format == "pdbqt":
        if not os.path.exists(pose_abs):
            raise HTTPException(status_code=404, detail="Pose file missing")
        return FileResponse(pose_abs, media_type="chemical/x-pdbqt", filename=os.path.basename(pose_abs))
    elif format == "sdf":
        data = pdbqt_to_sdf_bytes(pose_abs)
        if data is None:
            raise HTTPException(status_code=500, detail="Failed to convert pose to SDF (requires OpenBabel)")
        return Response(content=data, media_type="chemical/x-mdl-sdfile", headers={
            "Content-Disposition": f"attachment; filename=pose_{job_id}.sdf"
        })
    else:
        raise HTTPException(status_code=400, detail="Unsupported format; use pdbqt or sdf")


@router.get("/job/{job_id}", response_model=DockJobOut)
def get_job_status(
    job_id: int,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    job = db.query(DockJob).filter(DockJob.id == job_id, DockJob.user_id == current_user.id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
