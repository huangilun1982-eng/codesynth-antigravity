import sqlite3
import os


def _get_existing_columns(cursor, table_name: str) -> set:
    """使用 PRAGMA 取得現有欄位名稱"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_column(cursor, table_name: str, column_name: str, column_def: str, existing_columns: set):
    """確保欄位存在，不存在則新增"""
    if column_name not in existing_columns:
        try:
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def}")
            print(f"[INFO] DB Schema Updated: Added '{column_name}' column to '{table_name}'.")
        except Exception as e:
            print(f"[WARNING] Failed to add {column_name} column: {e}")


def get_db(project_path):
    """
    建立並回傳 (connection, db_path)
    同時負責初始化 Schema
    """
    db_path = os.path.join(project_path, "codesynth_history.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # 表 1: history (主要版本記錄)
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  file_path TEXT, 
                  content TEXT, 
                  timestamp REAL,
                  trigger TEXT,
                  status TEXT DEFAULT 'pending',
                  feature_tag TEXT)''')

    # Schema Migration — 使用 PRAGMA 檢查，避免重複 ALTER 或例外陷阱
    existing_cols = _get_existing_columns(c, "history")
    _ensure_column(c, "history", "status", "TEXT DEFAULT 'pending'", existing_cols)
    _ensure_column(c, "history", "feature_tag", "TEXT", existing_cols)

    # 表 2: components (Blueprint Mode - 舊版相容)
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

    # 表 5: stages (階段定義)
    c.execute('''CREATE TABLE IF NOT EXISTS stages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT UNIQUE,
                  description TEXT,
                  created_at REAL)''')

    # 表 6: stage_items (階段內容：Snapshot 組合)
    c.execute('''CREATE TABLE IF NOT EXISTS stage_items
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  stage_id INTEGER,
                  file_path TEXT,
                  version_id INTEGER,
                  FOREIGN KEY (stage_id) REFERENCES stages(id),
                  FOREIGN KEY (version_id) REFERENCES history(id))''')

    conn.commit()
    return conn, db_path
