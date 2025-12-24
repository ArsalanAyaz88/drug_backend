from __future__ import annotations
import hashlib
import os
import re
import shutil
import subprocess
from typing import Optional, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem

from app.core.config import settings
from app.services.settings_provider import settings_provider

POSES_DIR = os.path.join(settings.STORAGE_DIR, "poses")


def _ensure_dirs() -> None:
    os.makedirs(POSES_DIR, exist_ok=True)


def _vina_path() -> str:
    # Resolve AutoDock Vina executable robustly across platforms.
    # Preference: DB setting (VINA_PATH) -> env (VINA_PATH) -> .env/pydantic settings -> common names on PATH.
    configured = (
        settings_provider.get("VINA_PATH")
        or os.environ.get("VINA_PATH")
        or getattr(settings, "VINA_PATH", None)
    )

    candidates: list[Optional[str]] = []
    if configured:
        candidates.append(configured)
    # Common executable names (Windows and Linux)
    candidates.extend([
        "vina",
        "vina.exe",
        "vina-gpu",
        "vina-gpu.exe",
        "vina64",
        "vina64.exe",
    ])

    for c in candidates:
        if not c:
            continue
        # Absolute path specified
        if os.path.isabs(c):
            if os.path.exists(c):
                return c
            continue
        # Resolve via PATH
        resolved = shutil.which(c)
        if resolved:
            return resolved

    raise FileNotFoundError(
        "AutoDock Vina executable not found. Set VINA_PATH (in settings or environment) to the full path to vina(.exe), or add it to PATH."
    )


def _obabel_path() -> Optional[str]:
    # Prefer explicit paths from DB/env/.env settings, then PATH lookup
    return (
        settings_provider.get("OBABEL_PATH")
        or os.environ.get("OBABEL_PATH")
        or getattr(settings, "OBABEL_PATH", None)
        or shutil.which("obabel")
        or shutil.which("obabel.exe")
    )


def _parse_center(val: Optional[str]) -> Tuple[float, float, float]:
    if not val:
        return (0.0, 0.0, 0.0)
    parts = [p.strip() for p in str(val).split(",")]
    if len(parts) != 3:
        return (0.0, 0.0, 0.0)
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except Exception:
        return (0.0, 0.0, 0.0)


def _parse_size(val: Optional[str]) -> Tuple[float, float, float]:
    if not val:
        return (20.0, 20.0, 20.0)
    parts = [p.strip() for p in str(val).split(",")]
    if len(parts) != 3:
        return (20.0, 20.0, 20.0)
    try:
        return (float(parts[0]), float(parts[1]), float(parts[2]))
    except Exception:
        return (20.0, 20.0, 20.0)


def _parse_vina_affinity(text: str) -> Optional[float]:
    m = re.search(r"REMARK\s+VINA\s+RESULT:\s*([-+]?\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"RESULT:\s*([-+]?\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))
    m = re.search(r"^\s*1\s+([-+]?\d+(?:\.\d+)?)", text, flags=re.MULTILINE)
    if m:
        return float(m.group(1))
    m = re.search(r"Affinity:\s*([-+]?\d+(?:\.\d+)?)", text)
    if m:
        return float(m.group(1))
    return None


def prepare_ligand_pdbqt_from_smiles(smiles: str, out_path: str) -> None:
    from meeko import MoleculePreparation, PDBQTWriterLegacy

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError("Invalid SMILES for ligand")
    mol = Chem.AddHs(mol)
    # Embed and optimize 3D
    if AllChem.EmbedMolecule(mol, AllChem.ETKDG()) != 0:
        raise RuntimeError("Failed to embed ligand conformer")
    AllChem.UFFOptimizeMolecule(mol, 200)

    prep = MoleculePreparation()
    mol_setup = prep.prepare(mol)
    # Some Meeko versions return a list of MolSetup (one per model); pick the first.
    if isinstance(mol_setup, list):
        if not mol_setup:
            raise RuntimeError("Meeko preparation returned no setups for ligand")
        mol_setup = mol_setup[0]
    writer = PDBQTWriterLegacy()
    pdbqt_result = writer.write_string(mol_setup)
    # Some Meeko versions return (pdbqt_str, warnings) tuple; normalize to string
    if isinstance(pdbqt_result, tuple):
        pdbqt_str = pdbqt_result[0]
    else:
        pdbqt_str = pdbqt_result
    if not isinstance(pdbqt_str, str):
        raise RuntimeError("Unexpected Meeko writer output type; expected string")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(pdbqt_str)


def prepare_receptor_pdbqt_from_protein(in_path: str, out_path: str) -> None:
    # If already PDBQT, just copy
    if in_path.lower().endswith(".pdbqt"):
        shutil.copyfile(in_path, out_path)
        return
    # Prefer OpenBabel if available
    obabel = _obabel_path()
    if obabel is None:
        raise RuntimeError("OpenBabel (obabel) not found in PATH; cannot prepare receptor PDBQT")
    # -xr: remove waters; -xh: add hydrogens (older flag); use -p for pH if desired
    cmd = [obabel, in_path, "-O", out_path, "-xr", "-xh"]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def run_vina(
    receptor_pdbqt: str,
    ligand_pdbqt: str,
    out_pdbqt: str,
    log_path: str,
    center: Optional[Tuple[float, float, float]] = None,
    size: Optional[Tuple[float, float, float]] = None,
    exhaustiveness: Optional[str] = None,
) -> float:
    if center is None:
        cx, cy, cz = _parse_center(settings_provider.get("VINA_CENTER"))
    else:
        cx, cy, cz = center
    if size is None:
        sx, sy, sz = _parse_size(settings_provider.get("VINA_SIZE"))
    else:
        sx, sy, sz = size
    exhaust = exhaustiveness or settings_provider.get("VINA_EXHAUSTIVENESS") or "8"

    vina = _vina_path()
    cmd = [
        vina,
        "--receptor", receptor_pdbqt,
        "--ligand", ligand_pdbqt,
        "--center_x", str(cx),
        "--center_y", str(cy),
        "--center_z", str(cz),
        "--size_x", str(sx),
        "--size_y", str(sy),
        "--size_z", str(sz),
        "--exhaustiveness", str(exhaust),
        "--out", out_pdbqt,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    # Persist Vina console output to our log file for later inspection
    try:
        with open(log_path, "w", encoding="utf-8") as lf:
            if proc.stdout:
                lf.write(proc.stdout)
            if proc.stderr:
                if proc.stdout:
                    lf.write("\n")
                lf.write(proc.stderr)
    except Exception:
        pass
    if proc.returncode != 0:
        raise RuntimeError(f"Vina failed: {proc.stderr.strip() or proc.stdout.strip()}")

    best: Optional[float] = None
    try:
        if os.path.exists(out_pdbqt):
            with open(out_pdbqt, "r", encoding="utf-8", errors="ignore") as f:
                best = _parse_vina_affinity(f.read())
    except Exception:
        best = None

    if best is None and os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                best = _parse_vina_affinity(f.read())
        except Exception:
            pass

    if best is None:
        best = _parse_vina_affinity((proc.stdout or "") + "\n" + (proc.stderr or ""))

    if best is None:
        raise RuntimeError(f"Vina ran but affinity could not be parsed. See log: {log_path}")

    return best


def dock_smiles_against_protein(
    smiles: str,
    protein_file_rel: str,
    center: Optional[Tuple[float, float, float]] = None,
    size: Optional[Tuple[float, float, float]] = None,
) -> tuple[str, float]:
    _ensure_dirs()
    # Build absolute paths
    protein_abs = os.path.abspath(protein_file_rel)
    base = os.path.splitext(os.path.basename(protein_abs))[0]
    tag = hashlib.sha1(smiles.encode("utf-8")).hexdigest()[:10]
    ligand_out = os.path.join(POSES_DIR, f"lig_{base}_{tag}.pdbqt")
    receptor_out = os.path.join(POSES_DIR, f"rec_{base}.pdbqt")
    pose_out = os.path.join(POSES_DIR, f"pose_{base}_{tag}.pdbqt")
    log_out = os.path.join(POSES_DIR, f"vina_{base}_{tag}.log")

    prepare_ligand_pdbqt_from_smiles(smiles, ligand_out)
    prepare_receptor_pdbqt_from_protein(protein_abs, receptor_out)
    score = run_vina(receptor_out, ligand_out, pose_out, log_out, center=center, size=size)

    # Return pose path relative to CWD for consistency with other stored paths
    rel_pose = os.path.relpath(pose_out, start=os.getcwd())
    return rel_pose, score
