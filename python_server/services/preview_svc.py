import os
import uuid
import time
from typing import Dict
from fastapi.responses import FileResponse, HTMLResponse
from fastapi import HTTPException
from utils.security import validate_project_path, validate_file_path
from utils.logger import server_logger as logger

# session_id -> { path: project_path, created_at: timestamp }
PREVIEW_SESSIONS: Dict[str, Dict] = {}
SESSION_TTL = 3600 * 24  # 24 hours

WELCOME_HTML = """
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>歡迎使用 CodeSynth</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background-color: #1e1e1e; color: #d4d4d4; }
        .container { text-align: center; max-width: 600px; padding: 2rem; border: 1px solid #333; border-radius: 8px; background-color: #252526; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h1 { color: #4ec9b0; margin-bottom: 1rem; }
        p { margin-bottom: 2rem; line-height: 1.6; }
        .icon { font-size: 4rem; margin-bottom: 1rem; display: block; }
        .highlight { color: #ce9178; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <span class="icon">🚀</span>
        <h1>專案準備就緒</h1>
        <p>
            看起來您目前還沒有建立 <span class="highlight">index.html</span> 首頁。<br>
            若您不熟悉程式碼，請使用 <b>CodeSynth Cockpit</b> 面板中的<br>
            <b>「精靈 (Wizard)」</b> 功能來快速建立您的第一個專案。
        </p>
        <p style="color: #858585; font-size: 0.9em;">(建立完成後，請點擊上方重新整理按鈕以預覽您的作品)</p>
    </div>
</body>
</html>
"""

EDITOR_JS = """
(function() {
    console.log("[CodeSynth] Visual Editor Active");
    
    // 定義可編輯的元素選擇器
    const EDITABLE_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'span', 'li', 'a', 'button', 'td', 'th', 'div'];
    
    // 樣式注入
    const style = document.createElement('style');
    style.innerHTML = `
        [contenteditable="true"]:hover { outline: 1px dashed #4ec9b0; cursor: text; }
        [contenteditable="true"]:focus { outline: 2px solid #4ec9b0; background: rgba(78, 201, 176, 0.1); }
        .cs-saving { opacity: 0.5; transition: opacity 0.2s; }
        #cs-toast { position: fixed; bottom: 20px; right: 20px; background: #333; color: white; padding: 8px 16px; border-radius: 4px; display: none; z-index: 9999; }
    `;
    document.head.appendChild(style);
    
    // Toast 提示
    const toast = document.createElement('div');
    toast.id = "cs-toast";
    document.body.appendChild(toast);
    
    function showToast(msg, error=false) {
        toast.textContent = msg;
        toast.style.display = 'block';
        toast.style.background = error ? '#d9534f' : '#333';
        setTimeout(() => toast.style.display = 'none', 3000);
    }

    // 初始化編輯器
    function initEditor() {
        const elements = document.querySelectorAll(EDITABLE_TAGS.join(','));
        elements.forEach(el => {
            // 排除無文字內容的空元素或含有子元素的容器 (簡單版)
            if (el.children.length === 0 && el.textContent.trim().length > 0) {
                el.setAttribute('contenteditable', 'true');
                el.dataset.original = el.textContent; // Store original
                
                el.addEventListener('focus', function() {
                    this.dataset.original = this.textContent;
                });
                
                el.addEventListener('blur', function() {
                    const newText = this.textContent;
                    const oldText = this.dataset.original;
                    
                    if (newText !== oldText) {
                        saveChange(oldText, newText, this);
                    }
                });
                
                // 防止 Enter 換行產生 div
                el.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.blur();
                    }
                });
            }
        });
    }

    async function saveChange(original, newText, element) {
        element.classList.add('cs-saving');
        showToast("Saving...");
        
        try {
            // 從 URL 推測 Session ID (需後端配合注入或從 path 解析)
            // 當前 URL: /api/preview/{session_id}/{path...}
            const pathParts = window.location.pathname.split('/');
            // url: /api/preview/{guid}/{file.html}
            // parts: ["", "api", "preview", "{guid}", "{file.html}"]
            const sessionId = pathParts[3]; 
            const filePath = pathParts.slice(4).join('/') || 'index.html';
            
            const resp = await fetch(`/api/preview/${sessionId}/update`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    file_path: filePath,
                    original_text: original,
                    new_text: newText
                })
            });
            
            if (resp.ok) {
                const data = await resp.json();
                showToast("Saved!");
                element.dataset.original = newText; // update original
            } else {
                const err = await resp.json();
                showToast("Save Failed: " + err.detail, true);
                element.textContent = original; // Revert
            }
        } catch (e) {
            showToast("Network Error", true);
            element.textContent = original;
        } finally {
            element.classList.remove('cs-saving');
        }
    }
    
    // 延遲執行以確保 DOM Ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initEditor);
    } else {
        initEditor();
    }
})();
"""

class PreviewService:
    # ... create_session 保持不變 ...
    
    def update_file_content(self, session_id: str, file_path: str, original_text: str, new_text: str):
        """更新檔案內容 (簡單文字替換)"""
        session = PREVIEW_SESSIONS.get(session_id)
        if not session:
            logger.warning(f"更新無效 Session: {session_id}")
            raise HTTPException(status_code=404, detail="Session expired")
            
        project_root = session['path']
        full_path = os.path.join(project_root, file_path)
        
        # 安全性: `validate_file_path`
        if not os.path.exists(full_path):
             raise HTTPException(status_code=404, detail="File not found")
             
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if original_text not in content:
                raise HTTPException(status_code=409, detail="Original text not found (file may have changed)")
                
            # 只替換第一個出現的匹配項，避免誤傷
            new_content = content.replace(original_text, new_text, 1)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            logger.info(f"Visual Edit Updated: {file_path}")
            return {"status": "success"}
            
        except Exception as e:
            logger.error(f"Visual Edit Error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    def create_session(self, project_path: str) -> str:
        """建立預覽 Session，返回 session_id"""
        try:
            validate_project_path(project_path)
            
            # 清理過期 Sessions
            current_time = time.time()
            expired = [sid for sid, data in PREVIEW_SESSIONS.items() 
                      if current_time - data['created_at'] > SESSION_TTL]
            for sid in expired:
                del PREVIEW_SESSIONS[sid]
            
            # 產生新 Session
            session_id = str(uuid.uuid4())
            PREVIEW_SESSIONS[session_id] = {
                "path": project_path,
                "created_at": current_time
            }
            logger.info(f"建立預覽 Session: {session_id} -> {project_path}")
            return session_id
            
        except ValueError as e:
            logger.warning(f"建立預覽失敗 (路徑無效): {e}")
            raise HTTPException(status_code=400, detail=str(e))

    def get_file_response(self, session_id: str, file_path: str):
        """取得 Session 對應專案的檔案"""
        session = PREVIEW_SESSIONS.get(session_id)
        if not session:
            logger.warning(f"存取無效 Session: {session_id}")
            raise HTTPException(status_code=404, detail="Session expired or invalid")
            
        project_root = session['path']
        
        # 安全驗證 relative path
        try:
            validate_file_path(file_path)
        except ValueError as e:
            logger.warning(f"非法檔案路徑請求: {file_path} ({e})")
            raise HTTPException(status_code=403, detail="Invalid file path")
            
        # 組合並檢查最終路徑
        full_path = os.path.join(project_root, file_path)
        resolved_path = os.path.realpath(full_path)
        resolved_root = os.path.realpath(project_root)
        
        if not resolved_path.startswith(resolved_root):
             logger.warning(f"路徑逃逸攔截: {full_path}")
             raise HTTPException(status_code=403, detail="Access denied")
             
        if not os.path.exists(full_path):
            # UX-01: 若請求的是 index.html 但檔案不存在，返回引導頁面
            if file_path.endswith("index.html"):
                 return HTMLResponse(content=WELCOME_HTML, status_code=200)

            raise HTTPException(status_code=404, detail="File not found")
            
        if not os.path.isfile(full_path):
             raise HTTPException(status_code=404, detail="Not a file")

        # VIZ-01: HTML 檔案注入視覺化編輯器腳本
        if full_path.lower().endswith('.html'):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 注入腳本 (簡單附加在 body 結束前)
                injection = f'<script>{EDITOR_JS}</script>'
                if '</body>' in content:
                    content = content.replace('</body>', injection + '</body>', 1)
                else:
                    content += injection
                    
                return HTMLResponse(content=content)
            except Exception as e:
                logger.error(f"Failed to inject editor script: {e}")
                # Fallback to normal file response
                return FileResponse(full_path)

        return FileResponse(full_path)
