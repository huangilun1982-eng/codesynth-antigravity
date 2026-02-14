from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health_check")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
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
