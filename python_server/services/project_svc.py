import os
import shutil
from typing import List, Dict, Any, Optional
from utils.security import validate_project_name
from utils.logger import server_logger as logger


class ProjectService:
    def __init__(self, server_root: str):
        self.server_root = server_root
        self.templates_dir = os.path.join(server_root, "templates")

    def list_templates(self) -> list:
        return [
            {"id": "empty", "name": "空白專案", "description": "一個乾淨的起點"},
            {"id": "webapp", "name": "Web App", "description": "含 HTML/CSS/JS 的前端專案"},
            {"id": "python", "name": "Python Starter", "description": "基本 Python 專案結構"}
        ]

    def create_project(self, name: str, path: str, template_id: str, skills: List[str] = None) -> dict:
        """建立專案（含路徑驗證）"""
        # SEC-06: 輸入驗證
        try:
            validate_project_name(name)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        if not path or not os.path.isdir(path):
            return {"status": "error", "message": f"基礎路徑不存在或不是目錄: {path}"}

        full_path = os.path.join(path, name)
        
        # 確認目標路徑不會逃逸出父目錄
        real_parent = os.path.realpath(path)
        real_target = os.path.realpath(full_path)
        if not real_target.startswith(real_parent):
            return {"status": "error", "message": "專案路徑不合法：路徑遍歷偵測"}

        if os.path.exists(full_path):
            return {"status": "error", "message": f"目錄已存在: {full_path}"}

        try:
            os.makedirs(full_path)
            logger.info(f"建立專案目錄: {full_path}")
        except Exception as e:
            return {"status": "error", "message": f"建立目錄失敗: {e}"}

        # 套用模板
        self._apply_template(full_path, template_id)

        # 安裝 skills
        if skills:
            from services.skill_svc import SkillService
            skill_svc = SkillService(self.server_root)
            for skill_id in skills:
                try:
                    skill_svc.install_skill(skill_id, full_path)
                except Exception as e:
                    logger.warning(f"安裝技能 {skill_id} 失敗: {e}")

        return {
            "status": "success",
            "message": f"專案 '{name}' 建立完成！",
            "path": full_path
        }

    def _apply_template(self, project_path: str, template_id: str):
        if template_id == "webapp":
            os.makedirs(os.path.join(project_path, "css"), exist_ok=True)
            os.makedirs(os.path.join(project_path, "js"), exist_ok=True)
            with open(os.path.join(project_path, "index.html"), 'w', encoding='utf-8') as f:
                f.write("<!DOCTYPE html>\n<html>\n<head>\n  <title>New Project</title>\n  <link rel='stylesheet' href='css/style.css'>\n</head>\n<body>\n  <h1>Hello, CodeSynth!</h1>\n  <script src='js/app.js'></script>\n</body>\n</html>")
            with open(os.path.join(project_path, "css", "style.css"), 'w', encoding='utf-8') as f:
                f.write("body { font-family: sans-serif; margin: 2rem; }")
            with open(os.path.join(project_path, "js", "app.js"), 'w', encoding='utf-8') as f:
                f.write("console.log('CodeSynth Project Initialized');")

        elif template_id == "python":
            with open(os.path.join(project_path, "main.py"), 'w', encoding='utf-8') as f:
                f.write("# CodeSynth Python Project\n\ndef main():\n    print('Hello, CodeSynth!')\n\nif __name__ == '__main__':\n    main()\n")
            with open(os.path.join(project_path, "requirements.txt"), 'w', encoding='utf-8') as f:
                f.write("# Add your dependencies here\n")

        # empty template: 不做任何事
