from __future__ import annotations

import os
from typing import Any, Dict, Iterable, Optional, Tuple

import gemmi

_STANDARD_AA = {
    "ALA",
    "ARG",
    "ASN",
    "ASP",
    "CYS",
    "GLN",
    "GLU",
    "GLY",
    "HIS",
    "ILE",
    "LEU",
    "LYS",
    "MET",
    "PHE",
    "PRO",
    "SER",
    "THR",
    "TRP",
    "TYR",
    "VAL",
}

_HYDROPHOBIC = {"ALA", "VAL", "LEU", "ILE", "MET", "PHE", "TRP", "PRO"}
_AROMATIC = {"PHE", "TYR", "TRP", "HIS"}
_POSITIVE = {"LYS", "ARG", "HIS"}
_NEGATIVE = {"ASP", "GLU"}

_HBOND_DONOR = {"SER", "THR", "TYR", "LYS", "ARG", "HIS", "ASN", "GLN", "TRP", "CYS"}
_HBOND_ACCEPTOR = {"ASP", "GLU", "SER", "THR", "TYR", "HIS", "ASN", "GLN", "CYS"}


def _as_tuple3(val: Any) -> Optional[Tuple[float, float, float]]:
    if val is None:
        return None
    if isinstance(val, (list, tuple)) and len(val) == 3:
        try:
            return (float(val[0]), float(val[1]), float(val[2]))
        except Exception:
            return None
    return None


def _bbox_from_center_size(
    center: Tuple[float, float, float], size: Tuple[float, float, float]
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float]]:
    cx, cy, cz = center
    sx, sy, sz = size
    half = (sx / 2.0, sy / 2.0, sz / 2.0)
    min_xyz = (cx - half[0], cy - half[1], cz - half[2])
    max_xyz = (cx + half[0], cy + half[1], cz + half[2])
    return min_xyz, max_xyz


def _in_bbox(x: float, y: float, z: float, min_xyz: Tuple[float, float, float], max_xyz: Tuple[float, float, float]) -> bool:
    return (
        min_xyz[0] <= x <= max_xyz[0]
        and min_xyz[1] <= y <= max_xyz[1]
        and min_xyz[2] <= z <= max_xyz[2]
    )


def _residue_key(chain: gemmi.Chain, residue: gemmi.Residue) -> str:
    try:
        num = residue.seqid.num
    except Exception:
        num = "?"
    icode = ""
    try:
        icode = residue.seqid.icode.strip()
    except Exception:
        icode = ""
    return f"{chain.name}:{residue.name}{num}{icode}"


def analyze_pocket_features(protein_file_rel: str, pocket: Dict[str, Any]) -> Dict[str, Any]:
    center = _as_tuple3(pocket.get("center"))
    size = _as_tuple3(pocket.get("size"))
    if center is None or size is None:
        return {}

    volume = float(size[0]) * float(size[1]) * float(size[2])
    min_xyz, max_xyz = _bbox_from_center_size(center, size)

    protein_abs = os.path.abspath(protein_file_rel)
    structure = gemmi.read_structure(protein_abs)

    residue_counts: Dict[str, int] = {}
    residue_ids: list[str] = []

    hydrophobic = 0
    aromatic = 0
    positive = 0
    negative = 0
    hbd = 0
    hba = 0

    for model in structure:
        for chain in model:
            for residue in chain:
                if residue.het_flag == "H":
                    continue
                name = residue.name.strip().upper()
                if name not in _STANDARD_AA:
                    continue

                inside = False
                for atom in residue:
                    pos = atom.pos
                    if _in_bbox(pos.x, pos.y, pos.z, min_xyz, max_xyz):
                        inside = True
                        break
                if not inside:
                    continue

                residue_counts[name] = residue_counts.get(name, 0) + 1
                residue_ids.append(_residue_key(chain, residue))

                if name in _HYDROPHOBIC:
                    hydrophobic += 1
                if name in _AROMATIC:
                    aromatic += 1
                if name in _POSITIVE:
                    positive += 1
                if name in _NEGATIVE:
                    negative += 1
                if name in _HBOND_DONOR:
                    hbd += 1
                if name in _HBOND_ACCEPTOR:
                    hba += 1

    total = sum(residue_counts.values())
    hydrophobic_fraction = (hydrophobic / total) if total else 0.0

    out: Dict[str, Any] = {
        "pocket_volume": volume,
        "center": center,
        "size": size,
        "residues_total": total,
        "residue_counts": residue_counts,
        "hydrophobic_residues": hydrophobic,
        "hydrophobic_fraction": hydrophobic_fraction,
        "aromatic_residues": aromatic,
        "positive_residues": positive,
        "negative_residues": negative,
        "net_charge": positive - negative,
        "hbond_donor_residues": hbd,
        "hbond_acceptor_residues": hba,
    }

    if residue_ids:
        out["residues"] = residue_ids[:50]

    return out
