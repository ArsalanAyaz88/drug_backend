from fastapi import APIRouter
from .endpoints import auth, workspace, proteins, molecules, docking, admet, results

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(workspace.router, prefix="/workspaces", tags=["workspaces"])
api_router.include_router(proteins.router, prefix="/proteins", tags=["proteins"])
api_router.include_router(molecules.router, prefix="/molecules", tags=["molecules"])
api_router.include_router(docking.router, prefix="/docking", tags=["docking"])
api_router.include_router(admet.router, prefix="/admet", tags=["admet"])
api_router.include_router(results.router, prefix="/results", tags=["results"])
