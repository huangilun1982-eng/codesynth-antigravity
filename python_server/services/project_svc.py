import os
import shutil
import logging
from typing import List, Dict, Any
from services.skill_svc import SkillService

logger = logging.getLogger("ProjectService")

class ProjectService:
    def __init__(self, server_root: str):
        self.server_root = server_root
        self.templates_dir = os.path.join(server_root, "templates")
        self.skill_svc = SkillService(server_root)

    def list_templates(self) -> List[Dict[str, str]]:
        """List available project templates."""
        # Hardcoded for now, or scan a 'templates' folder
        return [
            {"id": "empty", "name": "Empty Project", "description": "A clean slate."},
            {"id": "webapp", "name": "Web Application", "description": "HTML, CSS, JS starter with Live Preview support."},
            {"id": "python", "name": "Python Script", "description": "Basic Python development setup."}
        ]

    def create_project(self, name: str, path: str, template_id: str, skills: List[str]) -> Dict[str, Any]:
        """Creates a new project directory, applies template, and installs skills."""
        try:
            full_path = os.path.join(path, name)
            
            # 1. Create Directory
            if os.path.exists(full_path):
                 return {"status": "error", "message": f"Directory '{full_path}' already exists."}
            
            os.makedirs(full_path)
            logger.info(f"Created project directory: {full_path}")

            # 2. Apply Template
            self._apply_template(full_path, template_id)

            # 3. Install Skills
            results = []
            for skill_id in skills:
                res = self.skill_svc.install_skill(skill_id, full_path)
                results.append(res)

            return {
                "status": "success", 
                "message": f"Project '{name}' created successfully.",
                "path": full_path,
                "skill_results": results
            }

        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return {"status": "error", "message": str(e)}

    def _apply_template(self, project_path: str, template_id: str):
        """Generates basic files based on template ID."""
        if template_id == "empty":
            pass # Do nothing
        
        elif template_id == "webapp":
            # Create index.html
            index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Web App</title>
    <style>
        body { font-family: sans-serif; padding: 2rem; }
    </style>
</head>
<body>
    <h1>Hello, World!</h1>
    <p>Welcome to your new web application.</p>
</body>
</html>"""
            with open(os.path.join(project_path, "index.html"), "w", encoding='utf-8') as f:
                f.write(index_html)
            
            # Create css/js folders
            os.makedirs(os.path.join(project_path, "assets"), exist_ok=True)

        elif template_id == "python":
            main_py = """def main():
    print("Hello from Python!")

if __name__ == "__main__":
    main()
"""
            with open(os.path.join(project_path, "main.py"), "w", encoding='utf-8') as f:
                f.write(main_py)
            
            with open(os.path.join(project_path, "requirements.txt"), "w", encoding='utf-8') as f:
                f.write("# Add your dependencies here\n")

        logger.info(f"Applied template '{template_id}' to {project_path}")
