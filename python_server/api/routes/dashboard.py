from fastapi import APIRouter
from services.query_svc import (
    get_dashboard_data_logic, 
    get_version_content_logic, 
    update_status_logic,
    update_tag_logic,
    batch_update_tags_logic,
    get_tags_logic,
    get_versions_by_tag_logic
)

router = APIRouter()

@router.post("/dashboard")
async def api_get_dashboard(data: dict):
    return get_dashboard_data_logic(data.get('project_path'))

@router.post("/get_version_content")
async def api_get_version_content(data: dict):
    return get_version_content_logic(data.get('project_path'), data.get('id'))

@router.post("/update_status")
async def api_update_status(data: dict):
    return update_status_logic(data.get('project_path'), data.get('id'), data.get('status'))

@router.post("/update_tag")
async def api_update_tag(data: dict):
    return update_tag_logic(data.get('project_path'), data.get('version_id'), data.get('feature_tag'))

@router.post("/batch_update_tags")
async def api_batch_update_tags(data: dict):
    return batch_update_tags_logic(data.get('project_path'), data.get('version_ids'), data.get('feature_tag'))

@router.post("/get_tags")
async def api_get_tags(data: dict):
    return get_tags_logic(data.get('project_path'))

@router.post("/get_versions_by_tag")
async def api_get_versions_by_tag(data: dict):
    return get_versions_by_tag_logic(data.get('project_path'), data.get('feature_tag'))

@router.post("/screenshots")
async def api_get_screenshots(data: dict):
    from services.query_svc import get_screenshots_logic
    return get_screenshots_logic(data.get('project_path'), data.get('version_id'))
