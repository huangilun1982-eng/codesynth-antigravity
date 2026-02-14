# server.py - 專案控制台後端
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import sqlite3
import os
import sys
import time
from datetime import datetime
import json
import subprocess
from pathlib import Path
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import logging

# Schema 版本控制
DB_VERSION = 2  # 當前資料庫 Schema 版本

# 截圖功能
try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("[WARNING] mss 未安裝，截圖功能將無法使用。請執行：pip install mss")

# CodeSynth 專注於版本管理
# AI 功能請使用 Antigravity 對話

app = FastAPI()

class SnapshotRequest(BaseModel):
    project_path: str
    file_path: str
    content: str
    trigger: str

# ==========================================
# 安全性：輸入驗證
# ==========================================

def validate_project_path(path: str) -> str:
    """
    驗證專案路徑的安全性
    防止路徑遍歷和訪問敏感目錄
    """
    # 1. 轉換為絕對路徑
    abs_path = os.path.abspath(path)
    
    # 2. 檢查路徑是否存在
    if not os.path.exists(abs_path):
        raise ValueError(f"路徑不存在: {abs_path}")
    
    # 3. 檢查是否為目錄
    if not os.path.isdir(abs_path):
        raise ValueError(f"不是目錄: {abs_path}")
    
    # 4. 檢查寫入權限
    if not os.access(abs_path, os.W_OK):
        raise ValueError(f"無寫入權限: {abs_path}")
    
    # 5. 禁止系統目錄（Windows 和 Linux）
    forbidden_patterns = [
        "C:\\Windows", "C:\\Program Files",  # Windows
        "/root", "/etc", "/sys", "/proc", "/boot"  # Linux
    ]
    
    for forbidden in forbidden_patterns:
        if abs_path.startswith(forbidden):
            raise ValueError(f"禁止訪問系統目錄: {abs_path}")
    
    return abs_path

def validate_file_path(file_path: str) -> str:
    """
    驗證檔案路徑的安全性
    防止路徑遍歷攻擊
    """
    # 禁止路徑遍歷
    if '..' in file_path:
        raise ValueError("非法檔案路徑：包含 '..'")
    
    # 禁止絕對路徑
    if os.path.isabs(file_path):
        raise ValueError("非法檔案路徑：不允許絕對路徑")
    
    return file_path

def get_db(project_path):
    db_path = os.path.join(project_path, "codesynth_history.db")
    conn = sqlite3.connect(db_path)
    # 確保資料表存在
    # 建立簡單的歷史表：哪個檔案、什麼時候、內容是什麼
    c = conn.cursor()
    
    # [Mod] Phase 5: Add status column
    # Check if 'status' column exists in history
    try:
        c.execute("SELECT status FROM history LIMIT 1")
    except sqlite3.OperationalError:
        # Column missing, add it
        try:
            c.execute("ALTER TABLE history ADD COLUMN status TEXT DEFAULT 'pending'")
            print("[INFO] DB Schema Updated: Added 'status' column.")
        except: pass

    # [Mod] Feature Tag System: Add feature_tag column
    try:
        c.execute("SELECT feature_tag FROM history LIMIT 1")
    except sqlite3.OperationalError:
        # Column missing, add it
        try:
            c.execute("ALTER TABLE history ADD COLUMN feature_tag TEXT")
            print("[INFO] DB Schema Updated: Added 'feature_tag' column.")
        except: pass

    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  file_path TEXT, 
                  content TEXT, 
                  timestamp REAL,
                  trigger TEXT,
                  status TEXT DEFAULT 'pending',
                  feature_tag TEXT)''') # 功能標籤
                  
    # 表 2: components (Blueprint Mode - 舊版相容)
    # 用於維持「組件化」的視圖
    c.execute('''CREATE TABLE IF NOT EXISTS components
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  component_name TEXT UNIQUE,
                  active INTEGER DEFAULT 1)''')
    
    # 表 3: screenshots (測試失敗自動截圖)
    c.execute('''CREATE TABLE IF NOT EXISTS screenshots
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  version_id INTEGER,
                  file_path TEXT,
                  screenshot_path TEXT,
                  error_message TEXT,
                  timestamp REAL,
                  test_status TEXT,
                  FOREIGN KEY (version_id) REFERENCES history(id))''')
    
    # 表 4: ai_friendly_log (AI 友好的歷程記錄)
    c.execute('''CREATE TABLE IF NOT EXISTS ai_friendly_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  session_id TEXT,
                  timestamp REAL,
                  what_happened TEXT,
                  current_status TEXT,
                  related_files TEXT,
                  related_versions TEXT,
                  test_result TEXT,
                  error_message TEXT,
                  screenshot_path TEXT,
                  ai_summary TEXT,
                  next_action TEXT)''')
    
    conn.commit()
    return conn, db_path

# ==========================================
# AI 友好歷程記錄函數
# ==========================================

import uuid
import json

def get_session_id():
    """獲取或生成當前工作階段 ID"""
    # 簡單實作：使用當天日期作為 session_id
    from datetime import datetime
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
        print(f"📝 AI Log: {what_happened}")
    except Exception as e:
        print(f"⚠️ AI Log 記錄失敗: {e}")

@app.post("/api/simulation/start")
async def start_simulation(data: dict):
    """
    執行測試模擬：
    1. 從資料庫提取選定版本的程式碼
    2. 建立臨時執行環境 _sim_temp
    3. 執行 main.py
    4. 返回執行結果
    """
    import subprocess
    import shutil
    
    project_path = data.get('project_path')
    selection = data.get('selection', {})  # {file_path: version_id}
    
    print(f"🚀 Simulation Requested for Project: {project_path}")
    print(f"   Selection: {selection}")
    
    if not project_path:
        return {"status": "error", "message": "未提供專案路徑", "output": ""}
    
    # 1. 建立臨時執行目錄
    sim_dir = os.path.join(project_path, "_sim_temp")
    if os.path.exists(sim_dir):
        try:
            shutil.rmtree(sim_dir)
        except Exception as e:
            print(f"⚠️ 清理舊目錄失敗: {e}")
    
    try:
        os.makedirs(sim_dir)
    except Exception as e:
        return {"status": "error", "message": f"建立執行目錄失敗: {e}", "output": ""}
    
    # 2. 從資料庫提取程式碼並寫入檔案
    conn, _ = get_db(project_path)
    c = conn.cursor()
    
    main_file = None
    files_written = []
    
    for file_path, version_id in selection.items():
        # 從 history 表取得程式碼
        c.execute("SELECT content FROM history WHERE id=?", (version_id,))
        row = c.fetchone()
        
        if not row:
            conn.close()
            return {"status": "error", "message": f"找不到版本 ID: {version_id}", "output": ""}
        
        code = row[0]
        
        # 決定檔案名稱
        file_name = os.path.basename(file_path)
        # 確保子目錄結構被保留
        relative_path = os.path.relpath(file_path, project_path)
        target_file_path = os.path.join(sim_dir, relative_path)
        os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

        # 檢查是否為主程式
        if 'main.py' in file_name.lower(): # 應該是檢查完整的相對路徑
            main_file = target_file_path
        
        # 寫入檔案
        try:
            with open(target_file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            files_written.append(relative_path)
            print(f"   ✅ 寫入: {relative_path}")
        except Exception as e:
            conn.close()
            return {"status": "error", "message": f"寫入檔案失敗: {e}", "output": ""}
    
    conn.close()
    
    # 3. 檢查是否有 main.py
    if not main_file:
        # 嘗試從 selection 中找到一個作為 main_file
        for fp, vid in selection.items():
            if 'main.py' in fp.lower():
                main_file = os.path.join(sim_dir, os.path.relpath(fp, project_path))
                break
        if not main_file:
            return {"status": "error", "message": "未選擇 main.py，無法執行", "output": "", "files": files_written}
    
    # 4. 執行程式
    print(f"   🔥 執行: {os.path.basename(main_file)}")
    
    # 取得 main.py 的 version_id，用於截圖
    main_file_rel_path = os.path.relpath(main_file, sim_dir)
    main_version_id = selection.get(main_file_rel_path)
    if not main_version_id:
        # 如果 main_file_rel_path 不在 selection 裡 (例如是 project_path/main.py)
        # 則嘗試從 selection 中找到第一個 main.py 的 version_id
        for fp, vid in selection.items():
            if 'main.py' in fp.lower():
                main_version_id = vid
                break
        if not main_version_id and selection: # 如果還是沒有，就用第一個檔案的 version_id 作為代表
            main_version_id = list(selection.values())[0]

    try:
        process = subprocess.Popen(
            [sys.executable, main_file],
            cwd=sim_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False # Changed to False to handle decoding manually
        )
        
        stdout_output, stderr_output = process.communicate(timeout=30)
        stdout = stdout_output.decode('utf-8', errors='ignore')
        stderr = stderr_output.decode('utf-8', errors='ignore')
        
        if process.returncode == 0:
            return {
                "status": "success",
                "message": "執行成功",
                "output": stdout,
                "error": stderr if stderr else "",
                "exit_code": 0,
                "files": files_written
            }
        else:
            error_msg = f"執行失敗 (Exit Code: {process.returncode})"
            
            # ⭐ 測試失敗時自動截圖
            screenshot_path = take_screenshot(
                project_path,
                version_id=main_version_id,
                file_path='main.py',
                error_msg=stderr or stdout or error_msg,
                status='failed'
            )
            
            # AI 友好記錄：測試失敗
            log_ai_event(
                project_path,
                what_happened="用戶執行測試失敗",
                current_status="遇到問題需要修正",
                test_result="失敗",
                error_message=stderr or stdout or error_msg,
                screenshot_path=screenshot_path,
                ai_summary=f"測試執行失敗：{error_msg}。已自動截圖保存問題畫面。",
                next_action="建議查看錯誤訊息或截圖，修正代碼後重新測試"
            )
            
            return {
                "status": "failed",
                "message": error_msg,
                "output": stdout,
                "error": stderr,
                "exit_code": process.returncode,
                "files": files_written,
                "screenshot": screenshot_path  # 返回截圖路徑
            }
    
    except subprocess.TimeoutExpired:
        process.kill()
        error_msg = "執行逾時 (超過 30 秒)"
        
        # ⭐ 超時也截圖
        screenshot_path = take_screenshot(
            project_path,
            version_id=main_version_id,
            file_path='main.py',
            error_msg=error_msg,
            status='timeout'
        )
        
        return {
            "status": "timeout",
            "message": error_msg,
            "output": "",
            "error": "Process killed due to timeout",
            "files": files_written,
            "screenshot": screenshot_path
        }
    except Exception as e:
        error_msg = f"執行過程發生錯誤: {str(e)}"
        
        # ⭐ 錯誤也截圖
        screenshot_path = take_screenshot(
            project_path,
            version_id=main_version_id if main_version_id else 0,
            file_path='main.py',
            error_msg=error_msg,
            status='error'
        )
        
        return {
            "status": "error",
            "message": error_msg,
            "output": "",
            "error": str(e),
            "files": files_written,
            "screenshot": screenshot_path
        }

@app.post("/api/snapshot")
async def save_snapshot(req: SnapshotRequest):
    """保存單一檔案快照 - 帶完整錯誤處理"""
    conn = None
    try:
        print(f"[DEBUG] 收到快照請求: {req.file_path}")
        
        # 1. 驗證專案路徑
        try:
            project_path = validate_project_path(req.project_path)
            print(f"[DEBUG] 專案路徑驗證通過: {project_path}")
        except ValueError as e:
            print(f"[ERROR] 專案路徑驗證失敗: {e}")
            return {"status": "error", "message": f"專案路徑無效: {str(e)}"}
        except Exception as e:
            print(f"[ERROR] 專案路徑驗證異常: {type(e).__name__}: {e}")
            return {"status": "error", "message": f"路徑驗證錯誤: {str(e)}"}
        
        # 2. 驗證檔案路徑
        try:
            file_path = validate_file_path(req.file_path)
            print(f"[DEBUG] 檔案路徑驗證通過: {file_path}")
        except ValueError as e:
            print(f"[ERROR] 檔案路徑驗證失敗: {e}")
            return {"status": "error", "message": f"檔案路徑無效: {str(e)}"}
        except Exception as e:
            print(f"[ERROR] 檔案路徑驗證異常: {type(e).__name__}: {e}")
            return {"status": "error", "message": f"路徑驗證錯誤: {str(e)}"}
        
        # 3. 檔案大小檢查
        content_size = len(req.content)
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        if content_size > MAX_SIZE:
            error_msg = f"檔案過大 ({content_size/1024/1024:.1f}MB)，限制 10MB"
            print(f"[ERROR] {error_msg}")
            return {"status": "error", "message": error_msg}
        
        # 4. 取得資料庫連接
        try:
            conn, _ = get_db(project_path)
            c = conn.cursor()
            print(f"[DEBUG] 資料庫連接成功")
        except Exception as e:
            print(f"[ERROR] 資料庫連接失敗: {type(e).__name__}: {e}")
            return {"status": "error", "message": f"資料庫連接失敗: {str(e)}"}
        
        # 5. 插入資料庫（帶重試機制）
        version_id = None
        for attempt in range(5):
            try:
                c.execute("""INSERT INTO history 
                            (file_path, content, timestamp, trigger, status)
                            VALUES (?, ?, ?, ?, 'pending')""",
                         (file_path, req.content, time.time(), req.trigger))
                conn.commit()
                version_id = c.lastrowid
                print(f"[OK] 已保存快照: {file_path} (version_id: {version_id})")
                break
            except sqlite3.OperationalError as e:
                if attempt < 4 and "locked" in str(e).lower():
                    print(f"[WARNING] 資料庫鎖定，重試 {attempt + 1}/5")
                    time.sleep(0.1)
                else:
                    print(f"[ERROR] 資料庫操作失敗: {e}")
                    raise
            except Exception as e:
                print(f"[ERROR] 插入資料庫失敗: {type(e).__name__}: {e}")
                raise
        
        # 6. 記錄 AI 事件（非關鍵，失敗不影響主流程）
        try:
            log_ai_event(
                project_path,
                what_happened=f"用戶修改了 {file_path}",
                current_status="等待測試",
                related_files=file_path
            )
        except Exception as e:
            print(f"[WARNING] AI 事件記錄失敗（不影響主流程）: {e}")
        
        return {"status": "ok", "version_id": version_id}
        
    except Exception as e:
        # 捕獲所有未預期的異常
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"[ERROR] save_snapshot 未預期錯誤: {error_type}: {error_msg}")
        
        # 打印完整堆疊以便調試
        import traceback
        traceback.print_exc()
        
        # 嘗試回滾事務
        if conn:
            try:
                conn.rollback()
                print(f"[DEBUG] 事務已回滾")
            except Exception as rollback_error:
                print(f"[WARNING] 回滾失敗: {rollback_error}")
        
        return {"status": "error", "message": f"保存失敗: {error_type}: {error_msg}"}
        
    finally:
        # 確保關閉連接
        if conn:
            try:
                conn.close()
                print(f"[DEBUG] 資料庫連接已關閉")
            except Exception as close_error:
                print(f"[WARNING] 關閉連接失敗: {close_error}")


@app.post("/api/update_status")
async def update_status(data: dict):
    """
    更新特定版本的狀態 (Success/Failed)
    """
    project_path = data.get('project_path')
    ver_id = data.get('id')
    status = data.get('status') # 'success' or 'failed' or 'pending'
    
    conn, _ = get_db(project_path)
    c = conn.cursor()
    c.execute("UPDATE history SET status=? WHERE id=?", (status, ver_id))
    conn.commit()
    conn.close()
    return {"status": "updated"}

@app.post("/api/batch_snapshot")
async def batch_snapshot(data: dict):
    """批次保存多個檔案快照"""
    conn = None
    try:
        project_path = validate_project_path(data['project_path'])
        snapshots = data.get('snapshots', [])
        
        if not snapshots:
            return {"status": "error", "message": "沒有要保存的快照"}
        
        conn, _ = get_db(project_path)
        c = conn.cursor()
        
        success_count = 0
        errors = []
        MAX_SIZE = 10 * 1024 * 1024  # 10MB
        
        for snapshot in snapshots:
            try:
                file_path = validate_file_path(snapshot['file_path'])
                content = snapshot['content']
                trigger = snapshot.get('trigger', 'Batch Scan')
                
                # 檔案大小檢查
                if len(content) > MAX_SIZE:
                    errors.append({
                        'file': file_path,
                        'error': f'檔案過大 ({len(content)/1024/1024:.1f}MB)，限制 10MB'
                    })
                    continue
                
                # 插入資料庫
                c.execute("""INSERT INTO history 
                            (file_path, content, timestamp, trigger, status)
                            VALUES (?, ?, ?, ?, 'pending')""",
                         (file_path, content, time.time(), trigger))
                
                success_count += 1
                
            except ValueError as e:
                errors.append({
                    'file': snapshot.get('file_path', 'unknown'),
                    'error': str(e)
                })
            except Exception as e:
                errors.append({
                    'file': snapshot.get('file_path', 'unknown'),
                    'error': f'儲存失敗: {str(e)}'
                })
        
        conn.commit()
        
        return {
            'status': 'ok',
            'success_count': success_count,
            'total': len(snapshots),
            'errors': errors
        }
        
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        print(f"[ERROR] 批次快照失敗: {e}")
        if conn:
            conn.rollback()
        return {"status": "error", "message": "批次保存失敗"}
    finally:
        if conn:
            conn.close()

@app.post("/api/dashboard")
async def get_dashboard_data(data: dict):
    """
    核心功能：回傳「藍圖」資料
    格式：{ "main.py": [v1, v2...], "utils.py": [v1, v2...] }
    """
    project_path = data.get('project_path')
    if not os.path.exists(os.path.join(project_path, "codesynth_history.db")):
        return {"files": {}}

    conn, _ = get_db(project_path)
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
        
    conn.close()
    return {"files": dashboard}

@app.post("/api/get_version_content")
async def get_version_content(data: dict):
    """取得特定版本的程式碼內容"""
    conn, _ = get_db(data['project_path'])
    c = conn.cursor()
    c.execute("SELECT content FROM history WHERE id=?", (data['id'],))
    row = c.fetchone()
    conn.close()
    return {"content": row[0] if row else ""}

# ==========================================
# 功能標籤 API 端點
# ==========================================

@app.post("/api/update_tag")
async def update_tag(data: dict):
    """更新單一版本的功能標籤"""
    project_path = data.get('project_path')
    version_id = data.get('version_id')
    feature_tag = data.get('feature_tag')
    
    conn, _ = get_db(project_path)
    c = conn.cursor()
    c.execute("UPDATE history SET feature_tag=? WHERE id=?", 
              (feature_tag, version_id))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"已更新版本 {version_id} 的標籤"}

@app.post("/api/batch_update_tags")
async def batch_update_tags(data: dict):
    """批次更新多個版本的功能標籤"""
    project_path = data.get('project_path')
    version_ids = data.get('version_ids')  # list of version IDs
    feature_tag = data.get('feature_tag')
    
    conn, _ = get_db(project_path)
    c = conn.cursor()
    
    for version_id in version_ids:
        c.execute("UPDATE history SET feature_tag=? WHERE id=?", 
                  (feature_tag, version_id))
    
    conn.commit()
    conn.close()
    
    return {
        "status": "success", 
        "message": f"已為 {len(version_ids)} 個版本更新標籤",
        "count": len(version_ids)
    }

@app.post("/api/get_tags")
async def get_tags(data: dict):
    """取得專案中所有功能標籤清單"""
    project_path = data.get('project_path')
    
    conn, _ = get_db(project_path)
    c = conn.cursor()
    c.execute("SELECT DISTINCT feature_tag FROM history WHERE feature_tag IS NOT NULL ORDER BY feature_tag")
    tags = [row[0] for row in c.fetchall()]
    conn.close()
    
    return {"tags": tags}

@app.post("/api/get_versions_by_tag")
async def get_versions_by_tag(data: dict):
    """依功能標籤取得相關版本"""
    project_path = data.get('project_path')
    feature_tag = data.get('feature_tag')
    
    conn, _ = get_db(project_path)
    c = conn.cursor()
    c.execute("""SELECT id, file_path, timestamp, trigger, status 
                 FROM history 
                 WHERE feature_tag=? 
                 ORDER BY file_path, timestamp DESC""", 
              (feature_tag,))
    
    rows = c.fetchall()
    conn.close()
    
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

# ==========================================
# 測試失敗自動截圖功能
# ==========================================

def take_screenshot(project_path, version_id, file_path, error_msg, status):
    """測試失敗時自動截圖"""
    if not MSS_AVAILABLE:
        print("[WARNING] 截圖功能不可用：mss 未安裝")
        return None
    
    try:
        # 建立截圖目錄
        screenshots_dir = os.path.join(project_path, "screenshots")
        os.makedirs(screenshots_dir, exist_ok=True)
        
        # 生成檔名
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"error_{timestamp_str}_{version_id}.png"
        screenshot_path = os.path.join(screenshots_dir, filename)
        
        # 截圖
        with mss.mss() as sct:
            # 截取主螢幕
            screenshot = sct.grab(sct.monitors[1])
            # 保存
            mss.tools.to_png(screenshot.rgb, screenshot.size, output=screenshot_path)
        
        # 保存到資料庫
        conn, _ = get_db(project_path)
        c = conn.cursor()
        c.execute("""INSERT INTO screenshots 
                     (version_id, file_path, screenshot_path, 
                      error_message, timestamp, test_status)
                     VALUES (?, ?, ?, ?, ?, ?)""",
                  (version_id, file_path, screenshot_path, 
                   error_msg, time.time(), status))
        conn.commit()
        conn.close()
        
        print(f"📸 已自動截圖: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"❌ 截圖失敗: {e}")
        return None

@app.post("/api/screenshots")
async def get_screenshots(data: dict):
    """取得版本的所有截圖"""
    version_id = data.get('version_id')
    project_path = data.get('project_path')
    
    conn, _ = get_db(project_path)
    c = conn.cursor()
    c.execute("""SELECT id, screenshot_path, error_message, timestamp, test_status 
                 FROM screenshots 
                 WHERE version_id=? 
                 ORDER BY timestamp DESC""", 
              (version_id,))
    
    screenshots = []
    for row in c.fetchall():
        screenshots.append({
            "id": row[0],
            "path": row[1],
            "error": row[2],
            "timestamp": row[3],
            "status": row[4]
        })
    
    conn.close()
    return {"screenshots": screenshots}

# ==========================================
# AI 上下文查詢 API
# ==========================================

@app.post("/api/ai/context")
async def get_ai_context(data: dict):
    """
    為 AI 提供完整的專案上下文
    讓 AI 快速理解專案進度和狀態
    """
    project_path = data.get('project_path')
    limit = data.get('limit', 20)  # 最近N條記錄
    
    conn, _ = get_db(project_path)
    c = conn.cursor()
    
    # 1. 獲取最近的歷程記錄
    c.execute("""SELECT what_happened, current_status, test_result, 
                        error_message, screenshot_path, ai_summary, 
                        timestamp
                 FROM ai_friendly_log 
                 WHERE session_id = ?
                 ORDER BY timestamp DESC 
                 LIMIT ?""", 
              (get_session_id(), limit))
    
    recent_activities = []
    for row in c.fetchall():
        recent_activities.append({
            "what": row[0],
            "status": row[1],
            "result": row[2],
            "error": row[3],
            "screenshot": row[4],
            "summary": row[5],
            "time": time.strftime('%H:%M', time.localtime(row[6]))
        })
    
    # 2. 分析當前狀態
    c.execute("""SELECT current_status, what_happened 
                 FROM ai_friendly_log 
                 ORDER BY timestamp DESC LIMIT 1""")
    latest = c.fetchone()
    current_task = latest[1] if latest else "尚未開始"
    current_status = latest[0] if latest else "等待開始"
    
    # 3. 成功模式（最近成功的事件）
    c.execute("""SELECT what_happened, ai_summary 
                 FROM ai_friendly_log 
                 WHERE test_result = '成功' 
                 ORDER BY timestamp DESC LIMIT 5""")
    successful_patterns = [{"what": r[0], "summary": r[1]} for r in c.fetchall()]
    
    # 4. 失敗教訓（最近失敗的嘗試）
    c.execute("""SELECT what_happened, error_message, screenshot_path 
                 FROM ai_friendly_log 
                 WHERE test_result = '失敗' 
                 ORDER BY timestamp DESC LIMIT 5""")
    failed_attempts = [{
        "what": r[0], 
        "error": r[1], 
        "screenshot": r[2]
    } for r in c.fetchall()]
    
    # 5. 生成專案摘要
    c.execute("SELECT COUNT(*) FROM ai_friendly_log")
    total_events = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM ai_friendly_log WHERE test_result = '成功'")
    success_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM ai_friendly_log WHERE test_result = '失敗'")
    failed_count = c.fetchone()[0]
    
    conn.close()
    
    return {
        "summary": f"專案已進行 {total_events} 個操作，成功 {success_count} 次，失敗 {failed_count} 次",
        "current_task": current_task,
        "current_status": current_status,
        "recent_activities": recent_activities,
        "successful_patterns": successful_patterns,
        "failed_attempts": failed_attempts,
        "ai_notes": "用戶為非技術背景，建議使用簡單易懂的語言"
    }

# ==========================================
# 專案索引生成 API
# ==========================================

@app.post("/api/generate_index")
async def generate_project_index(data: dict):
    """
    生成專案索引檔案
    自動掃描並記錄所有組件資訊
    """
    project_path = data.get('project_path')
    
    try:
        # 1. 掃描專案檔案
        files_info = scan_project_files(project_path)
        
        # 2. 生成索引結構
        index = {
            "project_name": os.path.basename(project_path),
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": len(files_info),
            "files": files_info,
            "architecture_notes": "由 CodeSynth 自動生成的專案索引",
            "ai_mode": "hybrid",  # hybrid, ai-driven, human-maintained
            "version": "1.0"
        }
        
        # 3. 保存索引檔案
        index_path = os.path.join(project_path, "project_index.json")
        with open(index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        print(f"📋 已生成專案索引: {index_path}")
        
        return {
            "status": "success",
            "index_path": index_path,
            "total_files": len(files_info),
            "summary": f"已分析 {len(files_info)} 個檔案"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"生成索引失敗: {str(e)}"
        }

def scan_project_files(project_path):
    """掃描專案並收集檔案資訊"""
    files_info = {}
    
    # 要排除的目錄和檔案
    exclude_dirs = {
        'node_modules', '.git', '__pycache__', '.vscode', 
        'temp_simulation', '_sim_temp', 'screenshots',
        '.gemini', 'venv', 'env', 'dist', 'build'
    }
    
    exclude_extensions = {'.pyc', '.pyo', '.db', '.png', '.jpg', '.gif'}
    
    # 遍歷專案目錄
    for root, dirs, files in os.walk(project_path):
        # 過濾排除的目錄
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            # 過濾排除的檔案
            if any(file.endswith(ext) for ext in exclude_extensions):
                continue
            
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, project_path)
            
            # 收集檔案資訊
            try:
                stat = os.stat(file_path)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = len(content.splitlines())
                
                files_info[relative_path] = {
                    "size_bytes": stat.st_size,
                    "lines": lines,
                    "last_modified": time.strftime('%Y-%m-%d %H:%M', time.localtime(stat.st_mtime)),
                    "extension": os.path.splitext(file)[1],
                    "purpose": analyze_file_purpose(file, content),
                    "ai_managed": False,  # 預設為人類維護
                    "dependencies": extract_dependencies(content),
                    "ai_summary": "待 AI 分析"
                }
            except Exception as e:
                print(f"[WARNING] 無法分析 {relative_path}: {e}")
                continue
    
    return files_info

def analyze_file_purpose(filename, content):
    """簡單分析檔案用途"""
    # 根據檔名判斷
    name_lower = filename.lower()
    
    if 'main' in name_lower:
        return "主程式入口"
    elif 'server' in name_lower:
        return "伺服器程式"
    elif 'test' in name_lower:
        return "測試程式"
    elif 'config' in name_lower:
        return "配置檔案"
    elif 'util' in name_lower or 'helper' in name_lower:
        return "工具函數"
    elif 'database' in name_lower or 'db' in name_lower:
        return "資料庫操作"
    elif filename.endswith('.json'):
        return "JSON 配置或資料"
    elif filename.endswith('.md'):
        return "文檔說明"
    else:
        return "程式邏輯"

def extract_dependencies(content):
    """提取檔案依賴"""
    dependencies = []
    
    # Python import
    import_lines = [line.strip() for line in content.split('\n') 
                   if line.strip().startswith(('import ', 'from '))]
    
    for line in import_lines[:5]:  # 只取前5個
        if 'import ' in line:
            # 簡單提取模組名
            parts = line.split()
            if len(parts) >= 2:
                module = parts[1].split('.')[0]
                if module not in ['os', 'sys', 'time', 'json']:  # 排除標準庫
                    dependencies.append(module)
    
    return dependencies[:5]  # 最多5個

@app.post("/api/get_index")
async def get_project_index(data: dict):
    """獲取專案索引"""
    project_path = data.get('project_path')
    index_path = os.path.join(project_path, "project_index.json")
    
    if os.path.exists(index_path):
        with open(index_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {"status": "not_found", "message": "索引檔案不存在，請先生成"}

# ==========================================
# 健康檢查 API
# ==========================================

@app.get("/health")
async def health_check():
    """
    健康檢查端點
    用於確認伺服器運行狀態和功能可用性
    """
    health_status = {
        "status": "healthy",
        "version": "1.0.0",
        "schema_version": DB_VERSION,
        "timestamp": datetime.now().isoformat(),
        "features": {
            "version_control": True,
            "test_execution": True,
            "screenshot": MSS_AVAILABLE,
            "ai_history": True,
            "project_index": True,
            "schema_migration": True
        },
        "database": {
            "wal_mode": True,
            "concurrent_support": True
        }
    }
    
    return health_status

@app.get("/")
async def root():
    """根端點 - 返回基本資訊"""
    return {
        "service": "CodeSynth API Server",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "ai_context": "/api/ai/context",
            "generate_index": "/api/generate_index",
            "dashboard": "/api/dashboard"
        }
    }

if __name__ == "__main__":
    print("=" * 50)
    print("CodeSynth 控制台服務啟動中... (Port: 8000)")
    print("=" * 50)
    if MSS_AVAILABLE:
        print("[OK] 截圖功能已啟用")
    else:
        print("[WARNING] 截圖功能未啟用（mss 未安裝）")
    print("[OK] AI 友好歷程記錄已啟用")
    print("[OK] 專案索引生成已啟用")
    print("[OK] Schema 版本管理已啟用")
    print("=" * 50)
    uvicorn.run(app, host="127.0.0.1", port=8000)
