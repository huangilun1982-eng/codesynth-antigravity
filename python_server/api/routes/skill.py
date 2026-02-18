from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from services.skill_svc import SkillService

router = APIRouter()

class InstallSkillRequest(BaseModel):
    project_path: str
    skill_id: str
    params: Dict[str, Any] = {}

@router.get("/list")
async def list_skills(request: Request):
    """列出所有可用的技能包"""
    svc = SkillService(request.app.state.server_root)
    skills = svc.list_skills()
    return {"status": "success", "skills": skills}

@router.post("/install")
async def install_skill(req: InstallSkillRequest, request: Request):
    """安裝指定的技能包到專案"""
    try:
        svc = SkillService(request.app.state.server_root)
        result = svc.install_skill(req.skill_id, req.project_path, req.params)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
