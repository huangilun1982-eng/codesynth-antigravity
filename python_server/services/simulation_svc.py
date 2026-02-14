import os
import shutil
import sys
import subprocess
from database.connection import get_db
from utils.screenshot import take_screenshot
from .ai_svc import log_ai_event

def start_simulation_logic(data: dict) -> dict:
    """
    執行測試模擬：
    1. 從資料庫提取選定版本的程式碼
    2. 建立臨時執行環境 _sim_temp
    3. 執行 main.py
    4. 返回執行結果
    """
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
                status='failed',
                db_connection_factory=get_db
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
            status='timeout',
            db_connection_factory=get_db
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
            status='error',
            db_connection_factory=get_db
        )
        
        return {
            "status": "error",
            "message": error_msg,
            "output": "",
            "error": str(e),
            "files": files_written,
            "screenshot": screenshot_path
        }
