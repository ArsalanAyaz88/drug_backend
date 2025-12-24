from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.admet import AdmetResult
from app.models.molecule import Molecule
from app.models.pipeline_job import PipelineJob
from app.models.protein import Protein
from app.services.admet_service import predict_admet_for_smiles
from app.services.chem import generate_molecules_placeholder
from app.services.pockets import detect_pockets
from app.services.target_features import analyze_pocket_features
from app.services.vina import dock_smiles_against_protein

logger = logging.getLogger(__name__)


def _update_job(db: Session, job: PipelineJob, **kwargs: Any) -> None:
    for k, v in kwargs.items():
        setattr(job, k, v)
    db.commit()
    db.refresh(job)


def _try_fpocket(protein_abs: str) -> Optional[List[Dict[str, Any]]]:
    """
    If fpocket is installed, run it and extract pocket bounding boxes.
    Falls back to None if unavailable or fails.
    """
    exe = shutil.which("fpocket") or shutil.which("fpocket.exe")
    if not exe:
        return None
    try:
        subprocess.run([exe, "-f", protein_abs], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_dir = os.path.join(os.path.dirname(protein_abs), f"{os.path.basename(protein_abs)}_out")
        pockets_txt = os.path.join(out_dir, "pockets", "pocket0", "pocket.pqr")
        if not os.path.exists(pockets_txt):
            return None
        # Crude parser: compute bbox of pocket0 atoms
        xs: List[float] = []
        ys: List[float] = []
        zs: List[float] = []
        with open(pockets_txt, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if not line.startswith("HETATM"):
                    continue
                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    xs.append(x)
                    ys.append(y)
                    zs.append(z)
                except Exception:
                    continue
        if not xs:
            return None
        pad = 4.0
        center = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
        size = ((max(xs) - min(xs)) + pad, (max(ys) - min(ys)) + pad, (max(zs) - min(zs)) + pad)
        return [{"center": center, "size": size, "method": "fpocket"}]
    except Exception as e:
        logger.warning("fpocket detection failed: %s", e)
        return None


def _select_center_size(pockets: List[Dict[str, Any]]) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    if not pockets:
        return ((0.0, 0.0, 0.0), (20.0, 20.0, 20.0))
    p = pockets[0]
    return tuple(p.get("center", (0.0, 0.0, 0.0))), tuple(p.get("size", (20.0, 20.0, 20.0)))  # type: ignore[return-value]


def run_pipeline_sync(job_id: int, max_molecules: int = 10, pocket: Optional[Dict[str, Any]] = None) -> None:
    """
    Concrete synchronous pipeline (CPU-friendly):
    1) pocket detection (fpocket if available, fallback to bbox heuristic)
    2) molecule sourcing (reuse existing + placeholder generation)
    3) docking loop via Vina
    4) ADMET scoring
    5) summary stub for retrosynthesis/protocol
    """
    db: Session = SessionLocal()
    try:
        job: Optional[PipelineJob] = db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
        if not job:
            return
        _update_job(db, job, status="running", progress=0.05, message="Starting pipeline")

        protein: Optional[Protein] = db.query(Protein).filter(Protein.id == job.protein_id).first()
        if not protein:
            _update_job(db, job, status="failed", message="Protein not found")
            return

        protein_abs = os.path.abspath(protein.path)

        # Step 1: pocket detection (or use provided)
        pockets = [pocket] if pocket else (_try_fpocket(protein_abs) or detect_pockets(protein.path))
        if not pockets:
            _update_job(db, job, status="failed", message="No pockets detected")
            return
        center, size = _select_center_size(pockets)
        pocket_for_gen = pockets[0]
        try:
            features = analyze_pocket_features(protein.path, pocket_for_gen)
            if features:
                pocket_for_gen = {**pocket_for_gen, "features": features}
                pockets[0] = pocket_for_gen
        except Exception:
            pass
        _update_job(db, job, current_step="pocket_detection", progress=0.18, message="Pocket detected")

        # Step 2: source molecules (existing recent + generate placeholders)
        existing = (
            db.query(Molecule)
            .filter(Molecule.creator_id == job.user_id)
            .order_by(Molecule.id.desc())
            .limit(max_molecules)
            .all()
        )
        generated: List[Molecule] = []
        need = max(0, max_molecules - len(existing))
        if need > 0:
            smiles_list = generate_molecules_placeholder(str(job.protein_id), need, pocket=pocket_for_gen)
            for s in smiles_list:
                m = Molecule(smiles=s, generated_for_protein_id=job.protein_id, creator_id=job.user_id)
                db.add(m)
                generated.append(m)
            db.commit()
            for m in generated:
                db.refresh(m)
        molecules = existing + generated
        if not molecules:
            _update_job(db, job, status="failed", message="No molecules available")
            return
        _update_job(
            db,
            job,
            current_step="molecule_selection",
            progress=0.28,
            message=f"{len(molecules)} molecules ready for docking",
        )

        # Step 3: docking loop
        dock_results: List[Dict[str, Any]] = []
        for idx, m in enumerate(molecules):
            try:
                pose_path, score = dock_smiles_against_protein(m.smiles, protein.path, center=center, size=size)
                m.score = score
                db.add(m)
                dock_results.append({"molecule_id": m.id, "smiles": m.smiles, "score": score, "pose_path": pose_path})
            except Exception as e:
                dock_results.append({"molecule_id": m.id, "smiles": m.smiles, "error": str(e)})
            prog = 0.28 + (0.4 * (idx + 1) / max(len(molecules), 1))
            _update_job(db, job, current_step="docking", progress=min(0.7, prog), message=f"Docked {idx+1}/{len(molecules)}")
        db.commit()
        dock_success = [r for r in dock_results if "score" in r]
        if not dock_success:
            _update_job(db, job, status="failed", message="Docking failed for all molecules")
            return

        dock_success = sorted(dock_success, key=lambda x: x["score"])
        top_for_admet = dock_success[: min(10, len(dock_success))]

        # Step 4: ADMET
        admet_results: List[Dict[str, Any]] = []
        for idx, r in enumerate(top_for_admet):
            try:
                res = predict_admet_for_smiles(r["smiles"])
                admet_results.append({**r, "admet": res})
                rec = AdmetResult(
                    molecule_id=r["molecule_id"],
                    user_id=job.user_id,
                    solubility=res.get("solubility") or 0.0,
                    toxicity=res.get("toxicity") or 0.0,
                    clearance=res.get("clearance") or 0.0,
                )
                db.add(rec)
            except Exception as e:
                admet_results.append({**r, "admet_error": str(e)})
            prog = 0.7 + (0.15 * (idx + 1) / max(len(top_for_admet), 1))
            _update_job(db, job, current_step="admet", progress=min(0.9, prog), message=f"ADMET {idx+1}/{len(top_for_admet)}")
        db.commit()

        # Step 5: placeholders for retrosynthesis / protocol
        summary = {
            "pockets": pockets[:1],
            "docking": dock_results,
            "admet": admet_results,
            "retrosynthesis": "pending (hook AiZynthFinder/ASKCOS here)",
            "protocol": "pending (LLM-based SOP generation)",
        }
        _update_job(
            db,
            job,
            status="completed",
            progress=1.0,
            current_step="complete",
            message="Pipeline finished",
            results=json.dumps(summary),
        )
    except Exception as e:
        try:
            _update_job(db, job, status="failed", message=str(e))  # type: ignore[arg-type]
        except Exception:
            pass
        logger.exception("Pipeline failed")
    finally:
        db.close()
