from __future__ import annotations

import os
from typing import List, Dict, Any

import gemmi


def detect_pockets(protein_file_rel: str) -> List[Dict[str, Any]]:
    """
    Lightweight placeholder pocket detector.
    If fpocket is available, you can plug it here; for now we compute a coarse bounding box
    of the structure (or hetero atoms if present) as a single "pocket".
    """
    protein_abs = os.path.abspath(protein_file_rel)
    structure = gemmi.read_structure(protein_abs)
    atoms = []
    het_atoms = []
    for model in structure:
        for chain in model:
            for residue in chain:
                for atom in residue:
                    pos = atom.pos
                    atoms.append((pos.x, pos.y, pos.z))
                    if residue.het_flag == "H":
                        het_atoms.append((pos.x, pos.y, pos.z))

    coords = het_atoms or atoms
    if not coords:
        return []

    xs, ys, zs = zip(*coords)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    # Add padding to cover surrounding space
    pad = 4.0
    center = (
        (min_x + max_x) / 2.0,
        (min_y + max_y) / 2.0,
        (min_z + max_z) / 2.0,
    )
    size = (
        (max_x - min_x) + pad,
        (max_y - min_y) + pad,
        (max_z - min_z) + pad,
    )

    return [
        {
            "center": center,
            "size": size,
            "method": "bbox_heuristic",
            "note": "Coarse pocket (consider installing fpocket for detailed pockets)",
        }
    ]
