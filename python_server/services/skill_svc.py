import os
import shutil
import json
import logging
from typing import List, Dict, Any

# Configure logger
logger = logging.getLogger("SkillService")

class SkillService:
    def __init__(self, server_root: str):
        self.server_root = server_root
        self.skills_dir = os.path.join(server_root, "skills")

    def list_skills(self) -> List[Dict[str, Any]]:
        """Scans the skills directory for valid skill packages."""
        skills = []
        if not os.path.exists(self.skills_dir):
            return skills

        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            manifest_path = os.path.join(item_path, "skill.json")
            
            if os.path.isdir(item_path) and os.path.exists(manifest_path):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                        # Add internal ID based on folder name
                        manifest['id'] = item 
                        skills.append(manifest)
                except Exception as e:
                    logger.error(f"Failed to load skill manifest for {item}: {e}")
        
        return skills

    def install_skill(self, skill_id: str, project_path: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Installs a skill into the target project."""
        if params is None:
            params = {}
        skill_path = os.path.join(self.skills_dir, skill_id)
        manifest_path = os.path.join(skill_path, "skill.json")

        if not os.path.exists(skill_path):
            return {"status": "error", "message": f"Skill '{skill_id}' not found."}

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)

            # 1. Copy Files
            files = manifest.get('files', [])
            for file_def in files:
                src_rel = file_def.get('source')
                dest_rel = file_def.get('destination')
                
                if not src_rel or not dest_rel:
                    continue

                src_file = os.path.join(skill_path, src_rel)
                dest_file = os.path.join(project_path, dest_rel)

                # SECURITY CHECK: Prevent Path Traversal
                # Ensure dest_file is actually inside project_path
                abs_project_path = os.path.abspath(project_path)
                abs_dest_file = os.path.abspath(dest_file)
                if not abs_dest_file.startswith(abs_project_path):
                     logger.warning(f"Blocked path traversal attempt: {dest_rel}")
                     continue

                # Create destination directory if needed
                os.makedirs(os.path.dirname(dest_file), exist_ok=True)

                # Read source/template
                with open(src_file, 'r', encoding='utf-8') as sf:
                    content = sf.read()

                # Simple Template Replacement (replace {{param}} with value)
                for key, value in params.items():
                    content = content.replace(f"{{{{{key}}}}}", str(value))

                # Write to destination
                with open(dest_file, 'w', encoding='utf-8') as df:
                    df.write(content)
                
                logger.info(f"Installed file: {dest_file}")

            # 2. Injection (Basic Append for now)
            # In a real implementation, we would use AST parsing for Python/JS
            injections = manifest.get('injections', [])
            for inject in injections:
                target_file_rel = inject.get('target')
                content_to_inject = inject.get('content')
                position = inject.get('position', 'append') # 'append', 'prepend'
                
                target_file = os.path.join(project_path, target_file_rel)
                if os.path.exists(target_file):
                    with open(target_file, 'r+', encoding='utf-8') as tf:
                        existing_content = tf.read()
                        if content_to_inject not in existing_content:
                            if position == 'append':
                                tf.write("\n" + content_to_inject + "\n")
                            elif position == 'prepend':
                                tf.seek(0)
                                tf.write(content_to_inject + "\n" + existing_content)
                            logger.info(f"Injected code into: {target_file}")

            return {"status": "success", "message": f"Skill '{manifest['name']}' installed successfully."}

        except Exception as e:
            logger.error(f"Failed to install skill {skill_id}: {e}")
            return {"status": "error", "message": str(e)}
