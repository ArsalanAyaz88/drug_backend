from typing import List
from functools import lru_cache


MODEL_NAME_DEFAULT = "DeepChem/ChemBERTa-77M-MLM"


@lru_cache(maxsize=1)
def _load_model(model_name: str = MODEL_NAME_DEFAULT):
    from transformers.models.auto import AutoTokenizer, AutoModel
    import torch

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.eval()
    return tokenizer, model


def embed_smiles_chemberta(smiles: str, model_name: str | None = None) -> List[float]:
    import torch
    tokenizer, model = _load_model(model_name or MODEL_NAME_DEFAULT)
    with torch.no_grad():
        inputs = tokenizer(smiles, return_tensors="pt", padding=True, truncation=True)
        outputs = model(**inputs)
        # Mean-pool last hidden state
        last_hidden = outputs.last_hidden_state  # [batch, seq, hidden]
        mask = inputs["attention_mask"].unsqueeze(-1)  # [batch, seq, 1]
        masked = last_hidden * mask
        summed = masked.sum(dim=1)
        counts = mask.sum(dim=1).clamp(min=1)
        mean = summed / counts
        vec = mean[0].cpu().tolist()
        return vec
