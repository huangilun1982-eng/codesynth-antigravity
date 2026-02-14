import sqlite3
import os

def get_db(project_path):
    """
    建立並回傳 (connection, db_path)
    同時負責初始化 Schema
    """
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
