from typing import List

# Placeholder ChemBERT/ChemBERTa molecule generator
# Replace with real model inference later

def generate_molecules_placeholder(target_id: str | None, num: int = 5) -> List[str]:
    base = "C1=CC=CC=C1"  # benzene as base
    out = []
    for i in range(num):
        out.append(base + "C" * (i % 3))
    return out


def embed_smiles_placeholder(smiles: str) -> list[float]:
    # Simple deterministic hash-based embedding stub
    h = sum(ord(c) for c in smiles)
    return [(h % 97) / 97.0, (h % 193) / 193.0, (h % 389) / 389.0]
