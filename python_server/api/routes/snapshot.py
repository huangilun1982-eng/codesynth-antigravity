from fastapi import APIRouter
from models.schemas import SnapshotRequest
from services.snapshot_svc import save_snapshot, batch_save_snapshot

router = APIRouter()

@router.post("/snapshot")
async def api_save_snapshot(req: SnapshotRequest):
    return save_snapshot(req.dict())

@router.post("/batch_snapshot")
async def api_batch_snapshot(data: dict):
    return batch_save_snapshot(data)
