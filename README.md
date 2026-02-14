# CodeSynth - AI 友善的專案版本控制系統

> **專為 AI 輔助開發設計的智能版本管理工具**
> 
> CodeSynth 是一個 VSCode Extension + Python FastAPI Server 的組合系統，提供自動版本快照、智能歷史追蹤、AI 友善的日誌記錄，以及直觀的 Webview 控制台界面。

---

## 目錄

- [系統概述](#系統概述)
- [核心概念](#核心概念)
- [系統架構](#系統架構)
- [完整 API 文檔](#完整-api-文檔)
- [工作原理](#工作原理)
- [數據庫 Schema](#數據庫-schema)
- [使用場景](#使用場景)
- [AI 集成指南](#ai-集成指南)
- [快速開始](#快速開始)

---

## 系統概述

### 什麼是 CodeSynth？

CodeSynth 是一個**自動化版本控制系統**，專為 AI 輔助的敏捷開發設計。它會：

1. **自動保存**：每次 `Ctrl+S` 保存檔案時，自動創建版本快照
2. **視覺化歷史**：通過 Webview 控制台顯示所有版本
3. **AI 友善日誌**：記錄開發歷程，供 AI 理解專案狀態
4. **快速回溯**：一鍵還原任意歷史版本
5. **批次掃描**：初次使用時可批次掃描整個專案

### 設計理念

**問題：** Git 對 AI 來說太複雜，commit、branch、merge 等概念不利於 AI 快速理解專案狀態。

**解決：** CodeSynth 提供：
- **時間線視圖**：所有版本按時間排列，一目了然
- **單一真相來源**：每個檔案的所有版本都在同一個地方
- **自動化**：無需手動 commit，保存即快照
- **AI 友善**：提供結構化的 JSON API 和專門的 AI 日誌表

---

## 核心概念

### 1. 版本快照 (Snapshot)

每次保存檔案時，CodeSynth 會創建一個**快照**：

```json
{
  "id": 123,
  "file_path": "main.py",
  "content": "def hello():\n    print('Hello')",
  "timestamp": 1703123456.789,
  "trigger": "Auto-Save",
  "status": "pending",
  "feature_tag": null
}
```

**關鍵屬性：**
- `id`: 唯一版本 ID
- `file_path`: 相對於專案根目錄的路徑
- `content`: 完整的檔案內容
- `timestamp`: Unix 時間戳
- `trigger`: 觸發來源（`Auto-Save` 或 `Initial Scan`）
- `status`: 狀態（`pending`/`success`/`failed`）
- `feature_tag`: 功能標籤（可選）

### 2. 組件藍圖 (Component Blueprint)

控制台中的**組件藍圖**視圖顯示：
- 每個檔案的所有版本
- 按檔案分組
- 每個版本的標籤和狀態

### 3. AI 友善日誌 (AI-Friendly Log)

專門為 AI 設計的結構化日誌表，記錄：
```json
{
  "session_id": "20231222-143000",
  "timestamp": 1703123456.789,
  "what_happened": "用戶修改了 main.py",
  "current_status": "等待測試",
  "related_files": ["main.py"],
  "related_versions": [123],
  "test_result": null,
  "ai_summary": "用戶正在編輯 main.py，已自動保存版本 123"
}
```

**用途：** AI 可以查詢此表快速了解專案發生了什麼事。

---

## 系統架構

CodeSynth 採用**前後端分離架構**：

```
┌─────────────────────┐         HTTP API          ┌─────────────────────┐
│                     │ ◄──────────────────────► │                     │
│  VSCode Extension   │                           │   Python Server     │
│   (TypeScript)      │                           │   (FastAPI)         │
│                     │                           │                     │
└─────────────────────┘                           └─────────────────────┘
         │                                                  │
         │ 監聽檔案保存                                      │ 操作資料庫
         ▼                                                  ▼
┌─────────────────────┐                           ┌─────────────────────┐
│  VSCode Workspace   │                           │    SQLite DB        │
│   (專案檔案)         │                           │  (快照 + AI 日誌)    │
└─────────────────────┘                           └─────────────────────┘
```

### Extension 職責

**位置：** `src/extension.ts`

**功能：**
1. **檔案監聽**：監聽 `onDidSaveTextDocument` 事件
2. **自動備份**：保存時調用 `/api/snapshot` API
3. **控制台 UI**：提供 Webview Panel 顯示歷史
4. **批次掃描**：初次使用時掃描整個專案
5. **自動刷新**：保存後自動刷新控制台

**關鍵代碼：**
```typescript
// 監聽檔案保存
const watcher = vscode.workspace.onDidSaveTextDocument(async (document) => {
    const projectPath = workspaceFolders[0].uri.fsPath;
    const relativePath = path.relative(projectPath, document.fileName);
    
    // 調用 API 保存快照
    await axios.post('http://127.0.0.1:8000/api/snapshot', {
        project_path: projectPath,
        file_path: relativePath,
        content: document.getText(),
        trigger: 'Auto-Save'
    });
    
    // 刷新控制台
    if (currentPanel) {
        await refreshCockpit();
    }
});
```

### Server 職責

**位置：** `server.py`

**功能：**
1. **API 服務**：提供 RESTful API
2. **資料庫操作**：SQLite CRUD
3. **路徑驗證**：防止路徑遍歷攻擊
4. **批次處理**：批次保存快照
5. **AI 日誌**：記錄開發事件

**技術棧：**
- FastAPI: Web 框架
- Uvicorn: ASGI Server
- SQLite: 資料庫（每個專案一個 .db 檔案）
- Pydantic: 數據驗證

---

## 完整 API 文檔

### 1. 保存單一快照

**端點：** `POST /api/snapshot`

**請求：**
```json
{
  "project_path": "/absolute/path/to/project",
  "file_path": "src/main.py",
  "content": "def hello():\n    print('Hello')",
  "trigger": "Auto-Save"
}
```

**回應：**
```json
{
  "status": "ok",
  "version_id": 123
}
```

**錯誤回應：**
```json
{
  "status": "error",
  "message": "專案路徑無效: 路徑不存在"
}
```

---

### 2. 批次保存快照

**端點：** `POST /api/batch_snapshot`

**請求：**
```json
{
  "project_path": "/absolute/path/to/project",
  "snapshots": [
    {
      "file_path": "main.py",
      "content": "print('Hello')",
      "trigger": "Initial Scan"
    },
    {
      "file_path": "utils.py",
      "content": "def util():\n    pass",
      "trigger": "Initial Scan"
    }
  ]
}
```

**回應：**
```json
{
  "status": "ok",
  "saved_count": 2,
  "failed_count": 0,
  "failed_files": []
}
```

---

### 3. 獲取控制台數據

**端點：** `POST /api/dashboard`

**請求：**
```json
{
  "project_path": "/absolute/path/to/project"
}
```

**回應：**
```json
{
  "files": {
    "main.py": [
      {
        "id": 123,
        "file_path": "main.py",
        "content": "...",
        "timestamp": 1703123456.789,
        "trigger": "Auto-Save",
        "status": "success",
        "feature_tag": "登入功能",
        "label": "12-22 01:19"
      },
      {
        "id": 122,
        "file_path": "main.py",
        "content": "...",
        "timestamp": 1703123400.000,
        "trigger": "Initial Scan",
        "status": "pending",
        "feature_tag": null,
        "label": "12-22 01:10"
      }
    ],
    "utils.py": [...]
  }
}
```

**數據結構：**
- 按檔案分組
- 每個檔案包含版本陣列
- 版本按時間倒序（最新在前）

---

### 4. 獲取版本內容

**端點：** `POST /api/get_version_content`

**請求：**
```json
{
  "project_path": "/absolute/path/to/project",
  "id": 123
}
```

**回應：**
```json
{
  "content": "def hello():\n    print('Hello')"
}
```

---

### 5. 更新版本狀態

**端點：** `POST /api/update_status`

**請求：**
```json
{
  "project_path": "/absolute/path/to/project",
  "version_id": 123,
  "status": "success"
}
```

**狀態選項：**
- `pending`: 等待測試（預設，灰色邊框）
- `success`: 測試通過（綠色邊框）
- `failed`: 測試失敗（紅色邊框）

**回應：**
```json
{
  "status": "ok"
}
```

---

### 6. 更新功能標籤

**端點：** `POST /api/update_feature_tag`

**請求：**
```json
{
  "project_path": "/absolute/path/to/project",
  "version_id": 123,
  "feature_tag": "登入功能"
}
```

**回應：**
```json
{
  "status": "ok"
}
```

---

### 7. 健康檢查

**端點：** `GET /api/health_check`

**回應：**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "schema_version": 2,
  "timestamp": "2023-12-22T01:19:00.000000",
  "features": {
    "version_control": true,
    "test_execution": true,
    "screenshot": false,
    "ai_history": true,
    "project_index": true,
    "schema_migration": true
  },
  "database": {
    "wal_mode": true,
    "concurrent_support": true
  }
}
```

---

## 工作原理

### 自動保存流程

```
1. 用戶修改檔案
   ↓
2. 按 Ctrl+S 保存
   ↓
3. Extension 偵測到 onDidSaveTextDocument 事件
   ↓
4. Extension 讀取檔案內容
   ↓
5. Extension 調用 POST /api/snapshot
   ↓
6. Server 驗證路徑和內容
   ↓
7. Server 插入資料庫
   ↓
8. Server 返回 {status: "ok", version_id: 123}
   ↓
9. Extension 顯示狀態訊息「✅ CodeSynth: 已備份 xxx.py」
   ↓
10. Extension 刷新控制台（如果已開啟）
    ↓
11. 控制台自動顯示新版本
```

### 批次掃描流程

```
1. 用戶點擊「掃描專案檔案」按鈕
   ↓
2. Extension 使用 vscode.workspace.findFiles 尋找檔案
   ↓
3. Extension 過濾掉 node_modules, .git 等目錄
   ↓
4. Extension 將檔案分批（每批 50 個）
   ↓
5. 對每批檔案並行讀取內容
   ↓
6. Extension 調用 POST /api/batch_snapshot
   ↓
7. Server 批次插入資料庫（單一事務）
   ↓
8. Extension 顯示進度「已掃描 100/500 個檔案」
   ↓
9. 完成後刷新控制台
```

### 控制台刷新流程

```
1. Extension 調用 POST /api/dashboard
   ↓
2. Server 查詢資料庫
  SELECT * FROM history WHERE file_path IN (...) ORDER BY timestamp DESC
   ↓
3. Server 將數據按檔案分組
   ↓
4. Server 返回 {files: {...}}
   ↓
5. Extension 更新 Webview HTML
   ↓
6. 用戶看到最新的版本列表
```

---

## 數據庫 Schema

每個專案有一個獨立的 `codesynth_history.db` SQLite 資料庫。

### 表 1: history

**用途：** 存儲所有版本快照

```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,           -- 檔案相對路徑
    content TEXT NOT NULL,             -- 完整內容
    timestamp REAL NOT NULL,           -- Unix 時間戳
    trigger TEXT,                      -- 觸發來源
    status TEXT DEFAULT 'pending',     -- pending/success/failed
    feature_tag TEXT                   -- 功能標籤（可選）
);
```

**索引：**
```sql
CREATE INDEX idx_file_path ON history(file_path);
CREATE INDEX idx_timestamp ON history(timestamp);
```

---

### 表 2: components

**用途：** Blueprint Mode（已棄用，保留用於向後相容）

```sql
CREATE TABLE components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_name TEXT UNIQUE,
    active INTEGER DEFAULT 1
);
```

---

### 表 3: screenshots

**用途：** 測試失敗時自動截圖

```sql
CREATE TABLE screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER,                -- 關聯的版本 ID
    file_path TEXT,                    -- 截圖檔案路徑
    screenshot_path TEXT,              -- 截圖存儲路徑
    error_message TEXT,                -- 錯誤訊息
    timestamp REAL,                    -- 時間戳
    test_status TEXT,                  -- 測試狀態
    FOREIGN KEY (version_id) REFERENCES history(id)
);
```

---

### 表 4: ai_friendly_log

**用途：** AI 友善的結構化日誌

```sql
CREATE TABLE ai_friendly_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,                   -- 會話 ID
    timestamp REAL,                    -- 時間戳
    what_happened TEXT,                -- 發生了什麼
    current_status TEXT,               -- 當前狀態
    related_files TEXT,                -- 相關檔案 (JSON array)
    related_versions TEXT,             -- 相關版本 (JSON array)
    test_result TEXT,                  -- 測試結果
    error_message TEXT,                -- 錯誤訊息
    screenshot_path TEXT,              -- 截圖路徑
    ai_summary TEXT,                   -- AI 摘要
    next_action TEXT                   -- 下一步建議
);
```

**查詢範例：**
```sql
-- 獲取最近 10 條事件
SELECT * FROM ai_friendly_log ORDER BY timestamp DESC LIMIT 10;

-- 獲取特定檔案的所有事件
SELECT * FROM ai_friendly_log WHERE related_files LIKE '%main.py%';
```

---

### 表 5: db_metadata

**用途：** 資料庫版本管理

```sql
CREATE TABLE db_metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);

INSERT INTO db_metadata (key, value) VALUES ('schema_version', '2');
```

---

## 使用場景

### 場景 1：AI 輔助開發

**問題：** AI 修改了多個檔案，需要追蹤變更。

**解決：**
1. AI 通過 Extension API 修改檔案
2. Extension 自動保存快照
3. AI 查詢 `/api/dashboard` 查看所有變更
4. AI 可以通過 `/api/get_version_content` 對比版本差異

---

### 場景 2：快速回溯

**問題：** 修改後發現有 bug，想回到之前的版本。

**解決：**
1. 開啟 CodeSynth 控制台
2. 選擇想要的版本
3. 右鍵 → 還原檔案
4. 檔案立即恢復到該版本

---

### 場景 3：功能標記

**問題：** 需要標記特定版本屬於哪個功能。

**解決：**
1. 右鍵版本 → 設定標籤
2. 輸入「登入功能」
3. 該版本顯示 🏷️ 登入功能
4. AI 可以查詢 `SELECT * FROM history WHERE feature_tag = '登入功能'`

---

### 場景 4：狀態管理

**問題：** 需要標記版本的測試狀態。

**解決：**
1. 右鍵版本 → 標記為成功/失敗
2. 版本邊框變色（綠色/紅色）
3. AI 可以查詢 `SELECT * FROM history WHERE status = 'success'`

---

## AI 集成指南

### AI 如何使用 CodeSynth

**1. 理解專案狀態**

```python
import requests

# 獲取所有版本
response = requests.post('http://127.0.0.1:8000/api/dashboard', json={
    'project_path': '/path/to/project'
})

files = response.json()['files']

# 分析每個檔案的最新版本
for file_path, versions in files.items():
    latest = versions[0]  # 最新版本
    print(f"{file_path}: {latest['label']} - {latest['status']}")
```

**2. 查詢 AI 日誌**

```python
import sqlite3

conn = sqlite3.connect('/path/to/project/codesynth_history.db')
cursor = conn.cursor()

# 獲取最近發生的事件
cursor.execute("""
    SELECT what_happened, current_status, ai_summary
    FROM ai_friendly_log
    ORDER BY timestamp DESC
    LIMIT 10
""")

for event in cursor.fetchall():
    print(f"{event[0]} - {event[1]}: {event[2]}")
```

**3. 比較版本差異**

```python
# 獲取兩個版本的內容
v1 = requests.post('http://127.0.0.1:8000/api/get_version_content', json={
    'project_path': '/path/to/project',
    'id': 122
}).json()['content']

v2 = requests.post('http://127.0.0.1:8000/api/get_version_content', json={
    'project_path': '/path/to/project',
    'id': 123
}).json()['content']

# 使用 difflib 比較
import difflib
diff = difflib.unified_diff(v1.splitlines(), v2.splitlines())
print('\n'.join(diff))
```

**4. 批次創建快照**

```python
# AI 修改了多個檔案後，批次保存
snapshots = [
    {"file_path": "main.py", "content": "...", "trigger": "AI-修改"},
    {"file_path": "utils.py", "content": "...", "trigger": "AI-修改"},
]

response = requests.post('http://127.0.0.1:8000/api/batch_snapshot', json={
    'project_path': '/path/to/project',
    'snapshots': snapshots
})

print(f"已保存 {response.json()['saved_count']} 個快照")
```

---

## 快速開始

### 前置條件

- VSCode 1.85+
- Python 3.11+
- Node.js 18+

### 安裝步驟

**1. 安裝 Python 依賴**

```bash
cd codesynth-antigravity
pip install fastapi uvicorn
```

**2. 編譯 Extension**

```bash
npm install
npm run compile
```

**3. 啟動 Server**

```bash
python server.py
```

應該看到：
```
==================================================
CodeSynth 控制台服務啟動中... (Port: 8000)
==================================================
[OK] 截圖功能已啟用
[OK] AI 友好歷程記錄已啟用
...
INFO: Uvicorn running on http://127.0.0.1:8000
```

**4. 啟動 Extension**

- 在 VSCode 中按 `F5`
- 這會開啟 Extension Development Host

**5. 開啟控制台**

- `Ctrl+Shift+P` → 輸入 "CodeSynth: 開啟控制台"

**6. 掃描專案**

- 點擊「🔍 掃描專案檔案」按鈕
- 等待掃描完成

**7. 測試自動保存**

- 修改任意檔案
- 按 `Ctrl+S` 保存
- 左下角應該顯示「✅ CodeSynth: 已備份 xxx」
- 控制台自動更新

---

## 常見問題

### Q: 為什麼保存後控制台沒有更新？

**A:** 檢查以下幾點：

1. **Server 是否運行？**
   ```bash
   netstat -ano | findstr :8000
   ```

2. **Extension 是否重新載入？**
   - 修改代碼後需要按 `Ctrl+R` 重新載入

3. **查看 Developer Tools Console**
   - `Ctrl+Shift+P` → "Developer: Toggle Developer Tools"
   - 查看是否有錯誤訊息

4. **查看 Server 日誌**
   - 運行 `python server.py` 的終端應該有輸出

---

### Q: 如何清空歷史記錄？

**A:** 刪除專案根目錄下的 `codesynth_history.db` 檔案，然後重新掃描。

---

### Q: 支援哪些檔案類型？

**A:** 所有文字檔案。自動過濾掉：
- `node_modules/`
- `.git/`
- `__pycache__/`
- `*.db`
- `*.pyc`
- `dist/`, `build/`, `out/`

---

### Q: 資料庫會不會太大？

**A:** 
- 每個快照約等於檔案大小
- 建議定期清理舊版本
- 或使用 `VACUUM` 指令壓縮資料庫

---

## 技術細節

### 安全性

**1. 路徑驗證**

```python
def validate_project_path(path: str) -> str:
    abs_path = os.path.abspath(path)
    
    # 禁止訪問系統目錄
    forbidden_dirs = ['/etc', '/sys', '/proc', 'C:\\Windows']
    for forbidden in forbidden_dirs:
        if abs_path.startswith(forbidden):
            raise ValueError(f"禁止訪問系統目錄: {forbidden}")
    
    return abs_path
```

**2. 檔案大小限制**

```python
MAX_SIZE = 10 * 1024 * 1024  # 10MB
if len(content) > MAX_SIZE:
    return {"status": "error", "message": "檔案過大"}
```

---

### 性能優化

**1. 批次處理**

- 將多個檔案合併成單一 API 請求
- 使用單一資料庫事務

**2. 並行讀取**

```typescript
// 每批 50 個檔案
const BATCH_SIZE = 50;

// 並行讀取內容
const contents = await Promise.all(
    batch.map(file => vscode.workspace.fs.readFile(file.uri))
);
```

**3. SQLite WAL 模式**

```sql
PRAGMA journal_mode=WAL;
```

- 允許並發讀寫
- 提升性能

---

### 錯誤處理

**Server 端：**

```python
try:
    # 業務邏輯
except ValueError as e:
    # 驗證錯誤
    return {"status": "error", "message": str(e)}
except Exception as e:
    # 未預期錯誤
    logging.error(f"Error: {type(e).__name__}: {e}")
    traceback.print_exc()
    return {"status": "error", "message": "內部錯誤"}
```

**Extension 端：**

```typescript
try {
    await axios.post('http://127.0.0.1:8000/api/snapshot', {...});
    vscode.window.setStatusBarMessage('✅ CodeSynth: 已備份', 3000);
} catch (error) {
    console.error('[CodeSynth] 保存失敗:', error);
    vscode.window.setStatusBarMessage('❌ CodeSynth: 備份失敗', 3000);
}
```

---

## 授權

MIT License

---


**CodeSynth - 讓 AI 完全理解您的專案歷史** 🚀
