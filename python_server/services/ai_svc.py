import json
import time
from datetime import datetime
from database.connection import get_db

def get_session_id():
    """獲取或生成當前工作階段 ID"""
    # 簡單實作：使用當天日期作為 session_id
    return datetime.now().strftime("%Y%m%d")

def log_ai_event(project_path, what_happened, current_status, **kwargs):
    """自動記錄事件到 AI 友好日誌"""
    try:
        conn, _ = get_db(project_path)
        c = conn.cursor()
        
        session_id = get_session_id()
        timestamp = time.time()
        
        # 提取可選參數
        related_files = json.dumps(kwargs.get('related_files', []))
        related_versions = json.dumps(kwargs.get('related_versions', []))
        test_result = kwargs.get('test_result')
        error_message = kwargs.get('error_message')
        screenshot_path = kwargs.get('screenshot_path')
        ai_summary = kwargs.get('ai_summary')
        next_action = kwargs.get('next_action')
        
        c.execute("""INSERT INTO ai_friendly_log 
                     (session_id, timestamp, what_happened, current_status,
                      related_files, related_versions, test_result, error_message,
                      screenshot_path, ai_summary, next_action)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (session_id, timestamp, what_happened, current_status,
                   related_files, related_versions, test_result, error_message,
                   screenshot_path, ai_summary, next_action))
        
        conn.commit()
        conn.close()
        print(f"[+] AI Log: {what_happened}")
    except Exception as e:
        print(f"[!] AI Log 記錄失敗: {e}")
