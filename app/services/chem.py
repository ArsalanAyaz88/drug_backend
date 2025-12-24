from typing import List

# Placeholder ChemBERT/ChemBERTa molecule generator
# Replace with real model inference later

def generate_molecules_placeholder(
    target_id: str | None, num: int = 5, pocket: dict | None = None
) -> List[str]:
    """
    Very lightweight SMILES generator that slightly varies substituents.
    If a protein target is provided, we bias toward adding polar groups to improve
    docking hydrogen bonding potential.
    """
    base = "C1=CC=CC=C1"  # benzene as base
    polar = ["O", "N", "F", "Cl"]
    hydrophobic = ["C", "CC", "CCC"]
    hydrogen_bond = ["NO", "ON", "CN", "NC"]
    acidic = ["C(=O)O", "S(=O)(=O)O"]
    basic = ["N", "CN", "CCN"]

    # Baseline bias: polar when a target is present, hydrophobic otherwise
    variants = polar if target_id else hydrophobic

    # Pocket-aware tweaks: very coarse heuristics using pocket box volume
    if pocket and isinstance(pocket, dict):
        features = pocket.get("features") if isinstance(pocket.get("features"), dict) else None
        size = pocket.get("size")
        volume = None
        if size and len(size) == 3:
            try:
                volume = float(size[0]) * float(size[1]) * float(size[2])
            except Exception:
                # Fall back to default variants if pocket size cannot be parsed
                variants = polar if target_id else hydrophobic

        if features is not None:
            try:
                fvol = features.get("pocket_volume")
                if fvol is not None:
                    volume = float(fvol)
            except Exception:
                pass

        if volume is not None:
            if volume < 800:
                variants = ["O", "N", "F"] + hydrogen_bond
            elif volume > 3000:
                variants = ["CC", "CCC", "CCO", "CCN", "CCl"]
            else:
                variants = ["O", "N", "Cl", "CO", "CN"]

        if features is not None:
            try:
                hf = features.get("hydrophobic_fraction")
                if hf is not None:
                    hf = float(hf)
                    if hf >= 0.6:
                        variants = ["C", "CC", "CCC", "Cl", "F", "CCl"]
                    elif hf <= 0.3:
                        variants = ["O", "N", "CO", "CN"] + hydrogen_bond
            except Exception:
                pass

            try:
                net_charge = features.get("net_charge")
                if net_charge is not None:
                    nc = float(net_charge)
                    if nc <= -1:
                        variants = basic + variants
                    elif nc >= 1:
                        variants = acidic + variants
            except Exception:
                pass

            try:
                hbd = features.get("hbond_donor_residues")
                hba = features.get("hbond_acceptor_residues")
                if hbd is not None and hba is not None:
                    hbd = float(hbd)
                    hba = float(hba)
                    if hbd > hba:
                        variants = ["O", "CO", "C(=O)O", "C#N"] + variants
                    elif hba > hbd:
                        variants = ["N", "CN", "NC"] + variants
            except Exception:
                pass

        # If pocket detection method hints at fpocket, lean into polar/H-bond
        if pocket.get("method") and "pocket" in str(pocket.get("method")).lower():
            variants = ["O", "N", "F"] + hydrogen_bond + variants

        seen = set()
        deduped: List[str] = []
        for v in variants:
            if v in seen:
                continue
            seen.add(v)
            deduped.append(v)
        variants = deduped
    out: List[str] = []
    for i in range(num):
        suffix = variants[i % len(variants)]
        out.append(f"{base}{suffix}")
    return out


def embed_smiles_placeholder(smiles: str) -> list[float]:
    # Simple deterministic hash-based embedding stub
    h = sum(ord(c) for c in smiles)
    return [(h % 97) / 97.0, (h % 193) / 193.0, (h % 389) / 389.0]
