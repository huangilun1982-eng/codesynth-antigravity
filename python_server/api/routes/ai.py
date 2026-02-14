from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
import os

router = APIRouter()

class AIContextRequest(BaseModel):
    project_path: str
    limit: int = 20

@router.post("/context")
async def get_ai_context(request: AIContextRequest):
    db_path = os.path.join(request.project_path, "codesynth_history.db")
    if not os.path.exists(db_path):
        return {"error": "Database not found"}

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get recent logs
        cursor.execute("""
            SELECT * FROM ai_friendly_log 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (request.limit,))
        
        logs = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return {"logs": logs}
    except Exception as e:
        return {"error": str(e)}
