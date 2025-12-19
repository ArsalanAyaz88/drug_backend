import os
import uuid
from fastapi import UploadFile
from app.core.config import settings


def save_protein_file(file: UploadFile) -> tuple[str, str]:
    ext = ".pdb" if file.filename.lower().endswith(".pdb") else ".cif"
    uid = uuid.uuid4().hex
    filename = f"{uid}{ext}"
    abs_path = os.path.join(settings.PROTEINS_DIR, filename)
    # ensure directory exists (in case startup hook didn't run yet)
    os.makedirs(settings.PROTEINS_DIR, exist_ok=True)
    with open(abs_path, "wb") as f:
        content = file.file.read()
        f.write(content)
    rel_path = os.path.relpath(abs_path, start=os.getcwd())
    fmt = "pdb" if ext == ".pdb" else "cif"
    return rel_path, fmt
