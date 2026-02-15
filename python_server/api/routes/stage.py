from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import os

from services.stage_svc import StageService
from utils.logger import server_logger

router = APIRouter()

# Pydantic Models for Request/Response
class StageItem(BaseModel):
    file_path: str
    version_id: int

class CreateStageRequest(BaseModel):
    project_path: str
    name: str
    description: Optional[str] = ""
    items: List[StageItem]

class GetStageRequest(BaseModel):
    project_path: str

@router.post("/create")
async def create_stage(req: CreateStageRequest):
    """建立新的階段 (Snapshot Group)"""
    try:
        if not os.path.exists(req.project_path):
            raise HTTPException(status_code=404, detail="Project path not found")
            
        svc = StageService(req.project_path)
        
        # Convert Pydantic items to dicts
        items_dict = [item.dict() for item in req.items]
        
        result = svc.create_stage(req.name, req.description, items_dict)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
            
        return result
        
    except Exception as e:
        server_logger.error(f"API Error in create_stage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/list")
async def list_stages(req: GetStageRequest):
    """列出所有階段"""
    try:
        svc = StageService(req.project_path)
        stages = svc.get_stages()
        return {"status": "success", "stages": stages}
    except Exception as e:
        server_logger.error(f"API Error in list_stages: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/items")
async def get_stage_items(req: GetStageRequest, stage_id: int = Body(..., embed=True)):
    """取得特定階段的內容"""
    try:
        svc = StageService(req.project_path)
        items = svc.get_stage_items(stage_id)
        return {"status": "success", "items": items}
    except Exception as e:
        server_logger.error(f"API Error in get_stage_items: {e}")
        raise HTTPException(status_code=500, detail=str(e))
