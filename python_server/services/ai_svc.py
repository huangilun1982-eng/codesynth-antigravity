from database.connection import get_db
from utils.logger import server_logger as logger
import time
import uuid

# 生成唯一 session ID
_session_id = str(uuid.uuid4())[:8]

def log_ai_event(project_path, what_happened="", current_status="", 
                 test_result="", error_message="", screenshot_path="",
                 ai_summary="", next_action=""):
    """記錄 AI 友好事件到資料庫"""
    conn = None
    try:
        conn, _ = get_db(project_path)
        c = conn.cursor()
        c.execute('''INSERT INTO ai_friendly_log 
                     (session_id, timestamp, what_happened, current_status,
                      related_files, related_versions, test_result, 
                      error_message, screenshot_path, ai_summary, next_action)
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                 (_session_id, time.time(), what_happened, current_status,
                  "", "", test_result, error_message, screenshot_path,
                  ai_summary, next_action))
        conn.commit()
    except Exception as e:
        logger.error(f"AI Log 記錄失敗: {e}")
    finally:
        if conn:
            conn.close()

def get_ai_log(project_path, limit=20):
    """取得 AI 事件記錄"""
    conn = None
    try:
        conn, _ = get_db(project_path)
        c = conn.cursor()
        c.execute('''SELECT * FROM ai_friendly_log 
                     ORDER BY timestamp DESC LIMIT ?''', (limit,))
        columns = [desc[0] for desc in c.description]
        rows = c.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"取得 AI Log 失敗: {e}")
        return []
    finally:
        if conn:
            conn.close()
