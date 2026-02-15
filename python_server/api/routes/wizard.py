from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
from services.project_svc import ProjectService

router = APIRouter()

class CreateProjectRequest(BaseModel):
    name: str
    path: str
    template_id: str
    skills: List[str] = []

@router.get("/templates")
async def list_templates():
    """List available project templates."""
    server_root = os.getcwd()
    if os.path.basename(server_root) != "python_server":
       server_root = os.path.join(server_root, "python_server")
       
    svc = ProjectService(server_root)
    return {"status": "success", "templates": svc.list_templates()}

@router.post("/create")
async def create_project(req: CreateProjectRequest):
    """Create a new project."""
    try:
        server_root = os.getcwd()
        if os.path.basename(server_root) != "python_server":
           server_root = os.path.join(server_root, "python_server")
           
        svc = ProjectService(server_root)
        result = svc.create_project(req.name, req.path, req.template_id, req.skills)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
            
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
