from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from services.preview_svc import PreviewService

router = APIRouter()
svc = PreviewService()

class PreviewInitRequest(BaseModel):
    project_path: str

@router.post("/preview/init")
async def api_init_preview(req: PreviewInitRequest):
    """初始化預覽 Session，取得 session_id"""
    try:
        session_id = svc.create_session(req.project_path)
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

class PreviewUpdateRequest(BaseModel):
    file_path: str
    original_text: str
    new_text: str

@router.post("/preview/{session_id}/update")
async def api_update_preview_file(session_id: str, req: PreviewUpdateRequest):
    """視覺化編輯更新"""
    try:
        return svc.update_file_content(session_id, req.file_path, req.original_text, req.new_text)
    except Exception as e:
        # Check specific http exception
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/preview/{session_id}/{file_path:path}")
async def api_get_preview_file(session_id: str, file_path: str):
    """取得預覽檔案"""
    if not file_path or file_path == "":
        file_path = "index.html"
    elif file_path.endswith("/"):
        file_path += "index.html"
        
    return svc.get_file_response(session_id, file_path)
