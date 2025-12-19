from __future__ import annotations
from typing import Dict

# Minimal wrapper for admet-ai.
# This module is optional at runtime; if package is missing, we fail gracefully.

def predict_admet_for_smiles(smiles: str) -> Dict[str, float]:
    try:
        from admet_ai import ADMETModel
    except ModuleNotFoundError as e:
        raise RuntimeError(f"admet-ai not available: {e}")
    except Exception as e:
        raise RuntimeError(f"admet-ai import failed: {e}")

    # Lazy load model per call to keep simple; in production cache the model
    model = ADMETModel()
    # Returns pandas.DataFrame
    df = model.predict([smiles])
    # Common fields (keys depend on package version); we map a few to our schema
    # Fallbacks default to None -> caller handles defaults
    sol = None
    tox = None
    clr = None
    # Try typical column names used by admet-ai
    for cand in ["Solubility", "solubility", "ESOL"]:
        if cand in df.columns:
            try:
                sol = float(df[cand].iloc[0])
            except Exception:
                pass
            break
    for cand in ["Toxicity", "toxicity", "AMES"]:
        if cand in df.columns:
            try:
                tox = float(df[cand].iloc[0])
            except Exception:
                pass
            break
    for cand in ["Clearance", "clearance", "CLint"]:
        if cand in df.columns:
            try:
                clr = float(df[cand].iloc[0])
            except Exception:
                pass
            break

    return {"solubility": sol, "toxicity": tox, "clearance": clr}
