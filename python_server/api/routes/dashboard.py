from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from services.query_svc import (
    get_dashboard_data_logic, 
    get_version_content_logic, 
    update_status_logic,
    update_tag_logic,
    batch_update_tags_logic,
    get_tags_logic,
    get_versions_by_tag_logic,
    get_screenshots_logic
)

router = APIRouter()

# SEC-04: Pydantic 模型驗證所有 API 輸入
class ProjectPathRequest(BaseModel):
    project_path: str

class VersionContentRequest(BaseModel):
    project_path: str
    id: int

class UpdateStatusRequest(BaseModel):
    project_path: str
    id: int
    status: str

class UpdateTagRequest(BaseModel):
    project_path: str
    version_id: int
    feature_tag: str

class BatchUpdateTagsRequest(BaseModel):
    project_path: str
    version_ids: List[int]
    feature_tag: str

class GetVersionsByTagRequest(BaseModel):
    project_path: str
    feature_tag: str

class ScreenshotsRequest(BaseModel):
    project_path: str
    version_id: int


@router.post("/dashboard")
async def api_get_dashboard(req: ProjectPathRequest):
    return get_dashboard_data_logic(req.project_path)

@router.post("/get_version_content")
async def api_get_version_content(req: VersionContentRequest):
    return get_version_content_logic(req.project_path, req.id)

@router.post("/update_status")
async def api_update_status(req: UpdateStatusRequest):
    return update_status_logic(req.project_path, req.id, req.status)

@router.post("/update_tag")
async def api_update_tag(req: UpdateTagRequest):
    return update_tag_logic(req.project_path, req.version_id, req.feature_tag)

@router.post("/batch_update_tags")
async def api_batch_update_tags(req: BatchUpdateTagsRequest):
    return batch_update_tags_logic(req.project_path, req.version_ids, req.feature_tag)

@router.post("/get_tags")
async def api_get_tags(req: ProjectPathRequest):
    return get_tags_logic(req.project_path)

@router.post("/get_versions_by_tag")
async def api_get_versions_by_tag(req: GetVersionsByTagRequest):
    return get_versions_by_tag_logic(req.project_path, req.feature_tag)

@router.post("/screenshots")
async def api_get_screenshots(req: ScreenshotsRequest):
    return get_screenshots_logic(req.project_path, req.version_id)
