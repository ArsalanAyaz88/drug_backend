from __future__ import annotations
import os
import shutil
import tempfile
from io import BytesIO
from typing import Iterable, Optional

from rdkit import Chem


def smiles_iter_to_sdf_bytes(smiles_iter: Iterable[str]) -> bytes:
    suppl = []
    mols = []
    for i, smi in enumerate(smiles_iter, start=1):
        m = Chem.MolFromSmiles(smi)
        if m is None:
            continue
        m.SetProp("_Name", f"mol_{i}")
        mols.append(m)
    bio = BytesIO()
    writer = Chem.SDWriter(bio)
    for m in mols:
        writer.write(m)
    writer.flush()
    # RDKit SDWriter to file-like may not close; ensure bytes copy
    data = bio.getvalue()
    writer.close()
    return data


def pdbqt_to_sdf_bytes(pdbqt_path: str) -> Optional[bytes]:
    obabel = shutil.which("obabel") or shutil.which("obabel.exe")
    if obabel is None:
        return None
    if not os.path.exists(pdbqt_path):
        return None
    with tempfile.TemporaryDirectory() as td:
        out_path = os.path.join(td, "pose.sdf")
        cmd = [obabel, pdbqt_path, "-O", out_path]
        import subprocess
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0 or not os.path.exists(out_path):
            return None
        with open(out_path, "rb") as f:
            return f.read()
