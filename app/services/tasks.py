from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.dock_job import DockJob
from app.models.molecule import Molecule
from app.models.protein import Protein
from app.models.admet import AdmetResult
from app.services.vina import dock_smiles_against_protein
from app.services.admet_service import predict_admet_for_smiles


def task_run_docking(dock_job_id: int) -> None:
    db: Session = SessionLocal()
    try:
        job = db.query(DockJob).filter(DockJob.id == dock_job_id).first()
        if not job:
            return
        job.status = "running"
        db.commit()
        db.refresh(job)
        mol = db.query(Molecule).filter(Molecule.id == job.molecule_id).first()
        prot = db.query(Protein).filter(Protein.id == job.protein_id).first()
        if not mol or not prot:
            job.status = "failed"
            db.commit()
            return
        pose_path, score = dock_smiles_against_protein(mol.smiles, prot.path)
        job.pose_path = pose_path
        job.score = score
        job.status = "completed"
        db.commit()
    except Exception:
        try:
            job = db.query(DockJob).filter(DockJob.id == dock_job_id).first()
            if job:
                job.status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


def task_run_admet(molecule_id: int, user_id: int) -> Optional[int]:
    db: Session = SessionLocal()
    try:
        mol = db.query(Molecule).filter(Molecule.id == molecule_id).first()
        if not mol:
            return None
        res = predict_admet_for_smiles(mol.smiles)
        rec = AdmetResult(
            molecule_id=molecule_id,
            user_id=user_id,
            solubility=res.get("solubility") or 0.0,
            toxicity=res.get("toxicity") or 0.0,
            clearance=res.get("clearance") or 0.0,
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec.id
    finally:
        db.close()
