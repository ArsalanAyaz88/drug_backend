from __future__ import annotations
from typing import Optional, List
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue

from app.services.settings_provider import settings_provider

_CLIENT: Optional[QdrantClient] = None
_COLLECTION_DIM = 768  # ChemBERTa hidden size


def get_qdrant() -> Optional[QdrantClient]:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    url = settings_provider.get("QDRANT_URL") or "http://localhost:6333"
    api_key = settings_provider.get("QDRANT_API_KEY") or None
    try:
        _CLIENT = QdrantClient(url=url, api_key=api_key)
        return _CLIENT
    except Exception:
        return None


def get_collection_name() -> str:
    return settings_provider.get("QDRANT_COLLECTION") or "molecules_v1"


def ensure_collection() -> bool:
    client = get_qdrant()
    if client is None:
        return False
    coll = get_collection_name()
    try:
        client.get_collection(coll)
        return True
    except Exception:
        # create if not exists
        try:
            client.recreate_collection(
                collection_name=coll,
                vectors_config=VectorParams(size=_COLLECTION_DIM, distance=Distance.COSINE),
            )
            return True
        except Exception:
            return False


def upsert_point(id_: int, vector: List[float], payload: Optional[dict] = None) -> bool:
    client = get_qdrant()
    if client is None:
        return False
    if not ensure_collection():
        return False
    coll = get_collection_name()
    point = PointStruct(id=id_, vector=vector, payload=payload or {})
    client.upsert(collection_name=coll, points=[point])
    return True


def search_similar(vector: List[float], top_k: int = 10, user_id: Optional[int] = None) -> List[int]:
    client = get_qdrant()
    if client is None:
        return []
    if not ensure_collection():
        return []
    coll = get_collection_name()
    query_filter = None
    if user_id is not None:
        query_filter = Filter(must=[FieldCondition(key="user_id", match=MatchValue(value=user_id))])
    res = client.search(collection_name=coll, query_vector=vector, limit=top_k, query_filter=query_filter)
    return [int(p.id) for p in res]
