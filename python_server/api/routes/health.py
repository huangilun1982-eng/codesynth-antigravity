from fastapi import APIRouter, Request
from datetime import datetime

router = APIRouter()

@router.get("/health_check")
async def health_check(request: Request):
    version = getattr(request.app.state, 'app_version', 'unknown')
    return {
        "status": "healthy",
        "version": version,
        "schema_version": 2,
        "timestamp": datetime.now().isoformat(),
        "features": {
            "version_control": True,
            "test_execution": True,
            "screenshot": True,
            "ai_history": True,
            "project_index": True,
            "schema_migration": True,
            "modular_backend": True
        },
        "database": {
            "wal_mode": True,
            "concurrent_support": True
        }
    }
