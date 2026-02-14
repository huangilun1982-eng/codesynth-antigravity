from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sqlite3
import os
from services.memory_manager import memory_manager

router = APIRouter()

class AIContextRequest(BaseModel):
    project_path: str
    limit: int = 20

class InteractionLogRequest(BaseModel):
    user_query: str
    ai_response: str

@router.post("/context")
async def get_ai_context(request: AIContextRequest):
    # 1. Get Memory OS System Prompt
    system_prompt = memory_manager.get_system_context()

    # 2. Get Recent Logs from SQLite (Legacy/DB logs)
    db_path = os.path.join(request.project_path, "codesynth_history.db")
    logs = []
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM ai_friendly_log 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (request.limit,))
            logs = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            print(f"Error reading sqlite logs: {e}")

    return {
        "system_prompt": system_prompt,
        "recent_logs": logs
    }

@router.post("/log_interaction")
async def log_interaction(request: InteractionLogRequest):
    """
    Log interaction to Memory OS (Markdown logs)
    """
    try:
        memory_manager.log_interaction(request.user_query, request.ai_response)
        
        # Trigger background sync (fire and forget logic or await if fast)
        # For now we await it to ensure safety, or we could use BackgroundTasks
        await memory_manager.sync_memory()
        
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/memory")
async def get_memory_files():
    """
    Get raw memory files for UI display
    """
    return memory_manager.get_raw_memory()

@router.post("/condense_memory")
async def trigger_condense():
    """
    Triggers memory condensation (LLM Summarization)
    """
    await memory_manager.condense_memory()
    return {"status": "condensed"}

@router.post("/sync_memory")
async def trigger_sync():
    """
    Manually trigger memory sync
    """
    await memory_manager.sync_memory()
    return {"status": "synced"}
