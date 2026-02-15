from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from services.skill_svc import SkillService

router = APIRouter()

class ListSkillsRequest(BaseModel):
    pass # No params needed for now

class InstallSkillRequest(BaseModel):
    project_path: str
    skill_id: str
    params: Dict[str, Any] = {}

@router.get("/list")
async def list_skills():
    """列出所有可用的技能包"""
    # SkillService needs server root path to find skills folder
    # Assuming python_server is the CWD or relative to it
    server_root = os.getcwd() 
    if os.path.basename(server_root) != "python_server":
       # If running from project root, python_server is a subdir
       server_root = os.path.join(server_root, "python_server")
    
    svc = SkillService(server_root)
    skills = svc.list_skills()
    return {"status": "success", "skills": skills}

@router.post("/install")
async def install_skill(req: InstallSkillRequest):
    """安裝指定的技能包到專案"""
    try:
        server_root = os.getcwd()
        if os.path.basename(server_root) != "python_server":
           server_root = os.path.join(server_root, "python_server")
           
        svc = SkillService(server_root)
        result = svc.install_skill(req.skill_id, req.project_path, req.params)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
