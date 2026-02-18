import os
import time
from database.connection import get_db

def get_dashboard_data_logic(project_path: str) -> dict:
    """
    核心功能：回傳「藍圖」資料
    格式：{ "main.py": [v1, v2...], "utils.py": [v1, v2...] }
    """
    if not os.path.exists(os.path.join(project_path, "codesynth_history.db")):
        return {"files": {}}

    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        
        # 1. 找出所有檔案
        c.execute("SELECT DISTINCT file_path FROM history ORDER BY file_path")
        files = [r[0] for r in c.fetchall()]
        
        dashboard = {}
        for f in files:
            # [Mod] Fix UI Clutter: Ignore external files or .gemini folder
            if f.startswith("..") or ".gemini" in f or os.path.isabs(f):
                continue

            # 2. 找出每個檔案的所有版本 (只取 ID, 時間, 觸發原因, status, feature_tag)
            c.execute("SELECT id, timestamp, trigger, status, feature_tag FROM history WHERE file_path=? ORDER BY id DESC", (f,))
            versions = []
            for r in c.fetchall():
                ts = time.strftime('%m-%d %H:%M', time.localtime(r[1]))
                st = r[3] if r[3] else 'pending'
                ft = r[4] if r[4] else None  # feature_tag
                versions.append({
                    "id": r[0], 
                    "label": f"[{ts}] {r[2]}", 
                    "full_time": ts, 
                    "status": st,
                    "feature_tag": ft
                })
            dashboard[f] = versions
            
        return {"files": dashboard}
    finally:
        conn.close()

def get_version_content_logic(project_path: str, version_id: int) -> dict:
    """取得特定版本的程式碼內容"""
    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        c.execute("SELECT content FROM history WHERE id=?", (version_id,))
        row = c.fetchone()
        return {"content": row[0] if row else ""}
    finally:
        conn.close()

def update_status_logic(project_path: str, version_id: int, status: str) -> dict:
    """
    更新特定版本的狀態 (Success/Failed)
    """
    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        c.execute("UPDATE history SET status=? WHERE id=?", (status, version_id))
        conn.commit()
        return {"status": "updated"}
    finally:
        conn.close()

def update_tag_logic(project_path: str, version_id: int, feature_tag: str) -> dict:
    """更新單一版本的功能標籤"""
    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        c.execute("UPDATE history SET feature_tag=? WHERE id=?", 
                  (feature_tag, version_id))
        conn.commit()
        return {"status": "success", "message": f"已更新版本 {version_id} 的標籤"}
    finally:
        conn.close()

def batch_update_tags_logic(project_path: str, version_ids: list, feature_tag: str) -> dict:
    """批次更新多個版本的功能標籤"""
    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        
        for version_id in version_ids:
            c.execute("UPDATE history SET feature_tag=? WHERE id=?", 
                      (feature_tag, version_id))
        
        conn.commit()
        return {
            "status": "success", 
            "message": f"已為 {len(version_ids)} 個版本更新標籤",
            "count": len(version_ids)
        }
    finally:
        conn.close()

def get_tags_logic(project_path: str) -> dict:
    """取得專案中所有功能標籤清單"""
    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        c.execute("SELECT DISTINCT feature_tag FROM history WHERE feature_tag IS NOT NULL ORDER BY feature_tag")
        tags = [row[0] for row in c.fetchall()]
        return {"tags": tags}
    finally:
        conn.close()

def get_versions_by_tag_logic(project_path: str, feature_tag: str) -> dict:
    """依功能標籤取得相關版本"""
    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        c.execute("""SELECT id, file_path, timestamp, trigger, status 
                     FROM history 
                     WHERE feature_tag=? 
                     ORDER BY file_path, timestamp DESC""", 
                  (feature_tag,))
        
        rows = c.fetchall()
        
        # 組織為 {file_path: [versions]}
        result = {}
        for row in rows:
            file_path = row[1]
            if file_path not in result:
                result[file_path] = []
            result[file_path].append({
                "id": row[0],
                "timestamp": row[2],
                "trigger": row[3],
                "status": row[4]
            })
        
        return {"versions": result, "tag": feature_tag}
    finally:
        conn.close()

def get_screenshots_logic(project_path: str, version_id: int) -> dict:
    """取得特定版本的截圖"""
    conn, _ = get_db(project_path)
    try:
        c = conn.cursor()
        c.execute("""SELECT screenshot_path, error_message, test_status, timestamp 
                     FROM screenshots WHERE version_id=?
                     ORDER BY timestamp DESC""", (version_id,))
        rows = c.fetchall()
        screenshots = []
        for r in rows:
            screenshots.append({
                "image_path": r[0],
                "error": r[1],
                "status": r[2],
                "timestamp": r[3]
            })
        return {"screenshots": screenshots}
    finally:
        conn.close()
