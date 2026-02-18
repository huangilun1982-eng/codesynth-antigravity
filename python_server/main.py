from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
# Add current directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.routes import snapshot, dashboard, simulation, ai, health, stage, skill, wizard, preview

# 統一版本號管理
APP_VERSION = "2.0.0"

app = FastAPI(
    title="CodeSynth Antigravity API",
    description="Modular backend for CodeSynth",
    version=APP_VERSION
)

# CORS middleware — 僅允許本機 Webview 和 localhost 來源
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "vscode-webview://*",
        "http://127.0.0.1:*",
        "http://localhost:*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 啟動時計算 server_root，存入 app.state 供所有 route 共用
server_root = os.path.dirname(os.path.abspath(__file__))
app.state.server_root = server_root
app.state.app_version = APP_VERSION

# Register routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(snapshot.router, prefix="/api", tags=["Snapshot"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(simulation.router, prefix="/api", tags=["Simulation"])
app.include_router(stage.router, prefix="/api/stage", tags=["Stage"])
app.include_router(skill.router, prefix="/api/skill", tags=["Skill"])
app.include_router(wizard.router, prefix="/api/wizard", tags=["Wizard"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])
app.include_router(preview.router, prefix="/api", tags=["Preview"]) # PREVIEW-03: 註冊預覽路由 (包含 /api/preview/init 和 /api/preview/{session_id})

# [Phase 9] Live Preview Infrastructure
# 注意：不再掛載 "." (python_server 自身)，改為只提供使用者預覽端點
# 實際掛載路徑會在 API 呼叫時動態指定使用者專案目錄
# 此處先不掛載靜態目錄，避免暴露後端原始碼

if __name__ == "__main__":
    print("==================================================")
    print(f"CodeSynth Antigravity Server v{APP_VERSION} (Modular)")
    print("==================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000)
