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
    try:
        project_path = data.get('project_path')
        selection = data.get('selection', {})  # {file_path: version_id}
        
        print(f"[*] Simulation Requested for Project: {project_path}")
        print(f"   Selection: {selection}")
        
        if not project_path:
            return {"status": "error", "message": "未提供專案路徑", "output": ""}
            
        # 0. 清理舊的 Streamlit 行程 (避免 Port 佔用)
        try:
            # Use specific path validation or cleaner invocation if possible
            # But simple try-except usually suppresses errors. 
            # If this is causing 500, the exception must be very severe or syntax-related (checked).
            print("   [...] Killing old streamlit processes...")
            subprocess.run(["taskkill", "/f", "/im", "streamlit.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"   [!] Cleanup failed: {e}")
        
        # 1. 建立臨時執行目錄
        sim_dir = os.path.join(project_path, "_sim_temp")
        if os.path.exists(sim_dir):
            try:
                shutil.rmtree(sim_dir)
            except Exception as e:
                print(f"[!] 清理舊目錄失敗: {e}")
        
        try:
            os.makedirs(sim_dir, exist_ok=True)
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

            # 檢查是否為主程式 (偵測 main.py, App.py 或 3D Viewer App.py)
            is_entry = any(x in file_name.lower() for x in ['main.py', 'app.py', '3d viewer app.py'])
            if is_entry and not main_file:
                main_file = target_file_path
            
            # 寫入檔案
            try:
                with open(target_file_path, 'w', encoding='utf-8') as f:
                    f.write(code)
                files_written.append(relative_path)
                print(f"   [+] 寫入: {relative_path}")
            except Exception as e:
                conn.close()
                return {"status": "error", "message": f"寫入檔案失敗: {e}", "output": ""}
        
        conn.close()
        
        # 3. 檢查是否有進入檔案
        if not main_file:
            # 嘗試從 selection 中找到一個最像進入點的檔案
            entry_patterns = ['main.py', 'app.py', '3d viewer app.py']
            for pattern in entry_patterns:
                for fp, vid in selection.items():
                    if pattern in fp.lower():
                        main_file = os.path.join(sim_dir, os.path.relpath(fp, project_path))
                        break
                if main_file: break
                
            if not main_file:
                return {
                    "status": "error", 
                    "message": "找不到程式進入點 (需包含 main.py, App.py 或 3D Viewer App.py)", 
                    "output": "", 
                    "files": files_written
                }
        
        # 4. 執行程式
        print(f"   [>] 執行: {os.path.basename(main_file)}")
        
        # 取得 main.py 或進入點的 version_id，用於截圖
        main_file_rel_path = os.path.relpath(main_file, sim_dir)
        main_version_id = selection.get(main_file_rel_path)
        if not main_version_id:
            entry_patterns = ['main.py', 'app.py', '3d viewer app.py']
            for pattern in entry_patterns:
                for fp, vid in selection.items():
                    if pattern in fp.lower():
                        main_version_id = vid
                        break
                if main_version_id: break
            if not main_version_id and selection: # 如果還是沒有，就用第一個檔案的 version_id 作為代表
                main_version_id = list(selection.values())[0]

        # Detect Streamlit
        is_streamlit = False
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'import streamlit' in content:
                    is_streamlit = True
        except:
            pass

        # [Check for Desktop Launcher]
        launcher_name = "Desktop_Launcher.py"
        launcher_path = os.path.join(sim_dir, launcher_name)
        
        # If not in snapshot, try to copy from original project
        if not os.path.exists(launcher_path):
            orig_launcher = os.path.join(project_path, launcher_name)
            if os.path.exists(orig_launcher):
                try:
                    shutil.copy(orig_launcher, launcher_path)
                    print(f"   [+] Auto-included {launcher_name}")
                except:
                    pass

        try:
            # 決定執行模式
            if is_streamlit and os.path.exists(launcher_path):
                print("   [desktop] Launching via Desktop_Launcher.py")
                
                # 1. 背景啟動 Streamlit
                streamlit_cmd = [sys.executable, "-m", "streamlit", "run", main_file, "--server.headless=true", "--server.port=8501"]
                server_proc = subprocess.Popen(streamlit_cmd, cwd=sim_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # 2. 啟動 Desktop Launcher (會等待直到視窗關閉)
                launcher_cmd = [sys.executable, launcher_path]
                process = subprocess.Popen(launcher_cmd, cwd=sim_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                stdout_output, stderr_output = process.communicate() # Blocking wait
                
                # 3. 清理 Streamlit
                server_proc.kill()
                
                stdout = stdout_output.decode('utf-8', errors='ignore')
                stderr = stderr_output.decode('utf-8', errors='ignore')

                # AI 友好記錄：測試成功 (Desktop)
                log_ai_event(
                    project_path,
                    what_happened="用戶執行測試成功 (Desktop Mode)",
                    current_status="等待下一步指令",
                    test_result="成功",
                    error_message="",
                    screenshot_path="",
                    ai_summary=f"Desktop App 啟動並執行完畢。",
                    next_action="無"
                )

                # Desktop 模式執行結束後，不需要回傳 app_url 給前端開啟瀏覽器
                return {
                    "status": "success",
                    "message": "Desktop App 執行完畢",
                    "output": stdout,
                    "error": stderr if stderr else "",
                    "exit_code": process.returncode,
                    "files": files_written
                }

            else:
                # 原有邏輯：直接執行 (Streamlit Browser Mode 或 一般 Python Script)
                cmd = [sys.executable, main_file]
                if is_streamlit:
                    print(f"   [~] Streamlit app detected. Using 'streamlit run'...")
                    cmd = [sys.executable, "-m", "streamlit", "run", main_file, "--server.headless=true", "--browser.serverAddress=localhost"]

                process = subprocess.Popen(
                    cmd,
                    cwd=sim_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False 
                )
                
                wait_time = 5 if is_streamlit else 30
                stdout_output, stderr_output = process.communicate(timeout=wait_time)
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
            
            # If Streamlit, this is expected behavior (Server kept running)
            if is_streamlit:
                # ⭐ DO NOT KILL PROCESS. Let it run for user interaction.
                return {
                    "status": "success", 
                    "message": "測試啟動成功！ (視窗已開啟，請手動關閉)",
                    "output": "Streamlit app launched successfully in background.",
                    "app_url": "http://localhost:8501",
                    "error": "",
                    "exit_code": 0,
                    "files": files_written
                }

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
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Server Logic Crash (500 Error): {e}",
            "output": traceback.format_exc(),
            "error": str(e)
        }
