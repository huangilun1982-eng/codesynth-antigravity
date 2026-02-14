import os
import time
from datetime import datetime

# 截圖功能
try:
    import mss
    import mss.tools
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("[WARNING] mss 未安裝，截圖功能將無法使用。請執行：pip install mss")

def take_screenshot(project_path, version_id, file_path, error_msg, status, db_connection_factory=None):
    """
    測試失敗時自動截圖
    注意：db_connection_factory 是一個函數，調用後返回 (conn, db_path)
    """
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
            if sct.monitors:
                 # sct.monitors[0] is all monitors combined, sct.monitors[1] is the first one
                screenshot = sct.grab(sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0])
                # 保存
                mss.tools.to_png(screenshot.rgb, screenshot.size, output=screenshot_path)
        
        # 保存到資料庫 (如果提供了 DB Factory)
        if db_connection_factory:
            conn, _ = db_connection_factory(project_path)
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
