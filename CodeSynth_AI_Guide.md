# 🤖 CodeSynth AI 使用指南

> **給 AI 協助者**：本文檔說明如何查詢 CodeSynth 專案狀態和歷程

---

## 快速開始

CodeSynth 是一個自動版本管理插件，提供以下 API 供 AI 查詢：

### 核心 API

**1. 查詢專案上下文** - 了解專案狀態、進度、問題
```bash
POST http://127.0.0.1:8000/api/ai/context
參數: {"project_path": "專案路徑"}
```

**2. 查看專案架構** - 了解有哪些檔案和組件
```bash
POST http://127.0.0.1:8000/api/get_index
參數: {"project_path": "專案路徑"}
```

**3. 查看版本歷史** - 檢視特定檔案的所有版本
```bash
POST http://127.0.0.1:8000/api/dashboard
參數: {"project_path": "專案路徑"}
```

---

## 常見場景

### 場景 1：用戶詢問專案進度

**用戶問：** "我的專案進展如何？"

**你應該：**
```bash
curl -X POST http://127.0.0.1:8000/api/ai/context \
  -H "Content-Type: application/json" \
  -d '{"project_path": "C:/path/to/project"}'
```

**返回資訊：**
```json
{
  "summary": "專案已進行 25 個操作，成功 18 次，失敗 7 次",
  "current_task": "用戶正在開發登入功能",
  "current_status": "等待測試",
  "recent_activities": [
    {
      "what": "用戶修改了 main.py",
      "status": "等待測試",
      "time": "15:30"
    }
  ],
  "successful_patterns": [...],
  "failed_attempts": [...]
}
```

**你的回應範例：**
```
"根據 CodeSynth 記錄，您的專案進展順利：
- 今天完成了 5 個操作
- 登入功能開發中（最後修改：15:30）
- 測試成功率：72% (18/25)
- 目前狀態：等待測試

建議：完成當前測試後可以進行下一功能"
```

---

### 場景 2：用戶想了解專案架構

**用戶問：** "這個專案有哪些檔案？"

**你應該：**
```bash
curl -X POST http://127.0.0.1:8000/api/get_index \
  -H "Content-Type: application/json" \
  -d '{"project_path": "C:/path/to/project"}'
```

**返回資訊：**
```json
{
  "project_name": "my-project",
  "total_files": 8,
  "files": {
    "server.py": {
      "lines": 720,
      "purpose": "伺服器程式",
      "dependencies": ["fastapi", "sqlite3"]
    },
    "main.py": {
      "lines": 180,
      "purpose": "主程式入口"
    }
  }
}
```

**你的回應範例：**
```
"您的專案包含 8 個檔案：

主要組件：
- server.py (720行) - 伺服器程式
- main.py (180行) - 主程式入口
- database.py (350行) - 資料庫操作

主要功能：版本控制、測試執行、AI 歷程記錄"
```

---

### 場景 3：用戶遇到問題尋求協助

**用戶問：** "為什麼測試失敗了？"

**你應該：**
1. 先查詢上下文
```bash
curl -X POST http://127.0.0.1:8000/api/ai/context \
  -d '{"project_path": "..."}'
```

2. 檢查 `recent_activities` 和 `failed_attempts`

3. 如果有截圖路徑，建議用戶查看：
```
"根據記錄，您在 15:30 執行測試時失敗了。
錯誤：TypeError: unsupported operand type(s)...
截圖已保存：screenshots/error_153000_123.png

建議查看截圖了解詳細情況"
```

---

### 場景 4：用戶要繼續開發

**用戶問：** "幫我繼續開發登入功能"

**你應該：**
1. 查詢上下文了解當前狀態
2. 查看 `successful_patterns`（什麼方法有效）
3. 查看 `failed_attempts`（什麼方法失敗了）
4. 基於歷史提供建議

```
"根據 CodeSynth 記錄：
- 登入功能已完成基本驗證（V1-V5）
- 密碼長度檢查在 V3 修正成功
- 會話管理尚未實作

建議下一步：實作會話管理功能"
```

---

## 最佳實踐

### ✅ 務必先查詢上下文

不要憑空猜測，始終：
```
1. 調用 /api/ai/context
2. 了解專案當前狀態
3. 基於實際資料提供建議
```

### ✅ 引用具體版本和時間

```
❌ "之前有個錯誤..."
✅ "在 15:30 的 V6 版本中遇到了 TypeError 錯誤"
```

### ✅ 避免重複失敗的嘗試

檢查 `failed_attempts`：
```json
{
  "failed_attempts": [
    {"what": "AI 建議使用異步處理", "error": "用戶不理解異步"}
  ]
}
```

看到這個，不要再建議異步處理。

### ✅ 參考成功模式

檢查 `successful_patterns`：
```json
{
  "successful_patterns": [
    {"what": "使用簡單的同步處理", "summary": "測試通過"}
  ]
}
```

優先建議類似的簡單方法。

---

## API 詳細參考

### POST /api/ai/context

**用途：** 獲取專案完整上下文

**請求：**
```json
{
  "project_path": "C:/path/to/project",
  "limit": 20  // 可選，預設 20
}
```

**返回：**
```json
{
  "summary": "專案摘要",
  "current_task": "當前任務",
  "current_status": "當前狀態",
  "recent_activities": [],  // 最近活動
  "successful_patterns": [],  // 成功經驗
  "failed_attempts": [],  // 失敗教訓
  "ai_notes": "用戶為非技術背景..."
}
```

### POST /api/get_index

**用途：** 獲取專案架構索引

**請求：**
```json
{
  "project_path": "C:/path/to/project"
}
```

**返回：**
```json
{
  "project_name": "專案名稱",
  "generated_at": "2024-12-21 23:00:00",
  "total_files": 8,
  "files": {
    "file.py": {
      "lines": 100,
      "purpose": "用途",
      "dependencies": []
    }
  }
}
```

### POST /api/dashboard

**用途：** 獲取版本控制資料

**請求：**
```json
{
  "project_path": "C:/path/to/project"
}
```

**返回：**
```json
{
  "files": {
    "main.py": [
      {
        "id": 1,
        "timestamp": 1234567890,
        "trigger": "Auto-Save",
        "status": "pending",
        "feature_tag": "login-feature"
      }
    ]
  }
}
```

---

## 重要提醒

### 用戶為非技術背景

CodeSynth 的目標用戶**不懂編程**，所以：
- ✅ 使用簡單易懂的語言
- ✅ 避免技術術語
- ✅ 提供具體步驟而非概念解釋

### 示範：好的回應 vs 壞的回應

**❌ 壞的回應：**
```
"你需要實作一個 async/await 模式的錯誤處理器，
 使用 try-catch 包裹 Promise.reject()..."
```

**✅ 好的回應：**
```
"根據記錄，測試在這一行失敗了。
 建議修改為：
 [具體的修改範例]
 
 這樣可以解決錯誤"
```

---

## 總結

**當用戶使用 CodeSynth 時，你應該：**

1. ✅ **始終先查詢** `/api/ai/context`
2. ✅ **了解歷史** - 什麼成功、什麼失敗
3. ✅ **基於實據** - 引用具體版本和時間
4. ✅ **簡單清楚** - 非技術背景用戶
5. ✅ **避免重複** - 不要重複失敗的方法

**CodeSynth 讓你能夠：**
- 📊 了解專案真實進度
- 🔍 查看完整歷程記錄
- 📸 看到錯誤截圖
- 💡 基於歷史提供精準建議

**這比盲目猜測有效得多！** 🚀
