import os
import shutil
import multiprocessing
import logging
import time

# 限制單次寫入最大為 10MB (Rule 10)
MAX_WRITE_SIZE = 10 * 1024 * 1024 

def _atomic_write_worker(path, content):
    """
    獨立進程寫入邏輯 (Worker Process)。
    注意：此函數必須是頂層函數 (Top-level) 以支援 Windows 的 pickling 機制。
    """
    temp_path = f"{path}.tmp"
    try:
        # 確保目標目錄存在
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # 原子寫入流程 (Rule 5)
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno()) # 強制寫入磁碟，防止斷電資料遺失
        
        # 原子替換 (POSIX & Windows 3.3+ 支援)
        os.replace(temp_path, path)
        
    except Exception as e:
        # 子進程內部的清理
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        # 重新拋出異常，讓父進程透過 exitcode 感知
        raise e

def run_safe_write(path: str, content: str, timeout: int = 5):
    """
    物理隔離寫入 (Level C 防護)。
    包含：輸入驗證、路徑檢查、備份容錯、進程隔離、超時強制殺除。
    """
    # 1. 輸入防禦驗證 (Rule 2)
    if not isinstance(path, str) or not path.strip():
        raise ValueError("Invalid path provided")
    if not isinstance(content, str):
        raise TypeError(f"Content must be string, got {type(content)}")
    
    # 路徑安全檢查：防止路徑遍歷攻擊 (Path Traversal)
    abs_path = os.path.abspath(path)
    base_dir = os.getcwd()
    if not abs_path.startswith(base_dir):
        # 在 Zero-Debug 模式下，通常限制只能寫入工作目錄
        # 若有特殊需求可放寬，但預設採取最嚴格標準
        raise ValueError(f"Security Access Denied: Path '{path}' is outside working directory.")

    # 2. 資源護欄 (Rule 10)
    if len(content.encode('utf-8')) > MAX_WRITE_SIZE:
        raise ValueError("Content exceeds maximum write size (10MB)")

    # 3. 備份機制 (Rule 5) - 容錯版
    if os.path.exists(abs_path):
        backup_path = f"{abs_path}.bak"
        try:
            shutil.copy2(abs_path, backup_path)
        except IOError as e:
            # 備份失敗不應阻止寫入，但需記錄警告
            logging.warning(f"SECURITY: Backup failed for {path} ({str(e)}). Proceeding with write.")

    # 4. 啟動隔離進程 (Rule 7)
    p = multiprocessing.Process(
        target=_atomic_write_worker, 
        args=(abs_path, content)
    )
    p.start()
    p.join(timeout)

    # 5. 超時與殭屍進程處理 (Rule 10 & Feasibility Fix)
    if p.is_alive():
        logging.error(f"SECURITY: Process {p.pid} timed out. Terminating...")
        p.terminate()
        # 給予作業系統回收時間
        p.join(timeout=1)
        
        # 若仍存活 (Windows 常見情況)，強制 Kill
        if p.is_alive():
            logging.critical(f"SECURITY: Process {p.pid} unresponsive. Sending SIGKILL.")
            p.kill()
            p.join()
        
        # 清理可能殘留的 tmp 檔案
        temp_path = f"{abs_path}.tmp"
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
                
        raise TimeoutError(f"Write operation timed out after {timeout}s")
    
    # 6. 檢查子進程退出狀態
    if p.exitcode != 0:
        raise IOError(f"Safe write subprocess failed with exit code {p.exitcode} (Check logs)")
