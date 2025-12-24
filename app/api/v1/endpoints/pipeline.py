from typing import Optional, Dict, Any
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.models.user import User
from app.models.pipeline_job import PipelineJob
from app.models.protein import Protein
from app.schemas.pipeline import PipelineJobOut, PipelineRunRequest
from app.services.pipeline_orchestrator import run_pipeline_sync

router = APIRouter()


@router.post("/run", response_model=PipelineJobOut)
def run_pipeline(
    req: PipelineRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    prot: Optional[Protein] = (
        db.query(Protein)
        .filter(Protein.id == req.protein_id, Protein.uploader_id == current_user.id)
        .first()
    )
    if not prot:
        raise HTTPException(status_code=404, detail="Protein not found")

    job = PipelineJob(
        user_id=current_user.id,
        protein_id=req.protein_id,
        status="queued",
        progress=0.0,
        message="Queued",
        strategy="pocket_provided" if req.pocket else None,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    # Fire-and-forget background execution (synchronous pipeline for now)
    background_tasks.add_task(run_pipeline_sync, job.id, req.max_molecules, req.pocket)

    return job


@router.get("/job/{job_id}", response_model=PipelineJobOut)
def get_job_status(
    job_id: int,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    job = (
        db.query(PipelineJob)
        .filter(PipelineJob.id == job_id, PipelineJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/stream/{job_id}")
async def stream_job_status(
    job_id: int,
    db: Session = Depends(db_session),
    current_user: User = Depends(get_current_user),
):
    job = (
        db.query(PipelineJob)
        .filter(PipelineJob.id == job_id, PipelineJob.user_id == current_user.id)
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        while True:
            db.refresh(job)
            payload = PipelineJobOut.model_validate(job).model_dump(mode="json")
            # Ensure all fields (e.g., datetime) are JSON-serializable
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            if job.status in ("completed", "failed"):
                break
            await asyncio.sleep(2)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
