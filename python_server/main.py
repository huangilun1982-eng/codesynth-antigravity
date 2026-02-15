from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
# Add current directory to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.routes import snapshot, dashboard, simulation, ai, health, stage

app = FastAPI(
    title="CodeSynth Antigravity API",
    description="Modular backend for CodeSynth",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
# Register routers
app.include_router(snapshot.router, prefix="/api", tags=["Snapshot"])
app.include_router(dashboard.router, prefix="/api", tags=["Dashboard"])
app.include_router(simulation.router, prefix="/api", tags=["Simulation"])
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(stage.router, prefix="/api/stage", tags=["Stage"])
from api.routes import skill
app.include_router(skill.router, prefix="/api/skill", tags=["Skill"])

from api.routes import wizard
app.include_router(wizard.router, prefix="/api/wizard", tags=["Wizard"])

# AI & Memory OS Router
app.include_router(ai.router, prefix="/api/ai", tags=["AI"])

# [Phase 9] Live Preview Infrastructure
# Mount project root to /preview for simple browser access
from fastapi.staticfiles import StaticFiles
# Serve current working directory (project root)
app.mount("/preview", StaticFiles(directory=".", html=True), name="preview")

if __name__ == "__main__":
    print("==================================================")
    print("CodeSynth Antigravity Server v2.0 (Modular)")
    print("==================================================")
    uvicorn.run(app, host="127.0.0.1", port=8000)
