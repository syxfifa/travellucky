from fastapi import APIRouter, HTTPException
from ...config import get_runtime_settings
router = APIRouter(prefix="/settings", tags=["settings"])
@router.get("")
async def read_settings():
    return {"success": True, "data": get_runtime_settings()}
@router.put("")
async def save_settings():
    raise HTTPException(405, "Configuration is managed by environment variables. Recreate the container after changes.")
