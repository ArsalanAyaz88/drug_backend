from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class Result(BaseModel):
    id: str
    status: str

@router.get("/{result_id}", response_model=Result)
async def get_result(result_id: str):
    return Result(id=result_id, status="completed")
