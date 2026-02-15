import logging
import time
from typing import Dict, Any, List, Optional
from database.connection import get_db
from utils.logger import server_logger

class StageService:
    def __init__(self, project_path: str):
        self.project_path = project_path

    def create_stage(self, name: str, description: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        擴展功能：建立一個新的階段 (Stage)
        items: [{"file_path": "...", "version_id": 123}, ...]
        """
        conn, _ = get_db(self.project_path)
        c = conn.cursor()
        
        try:
            # 1. Check if name exists
            c.execute("SELECT id FROM stages WHERE name = ?", (name,))
            if c.fetchone():
                return {"status": "error", "message": f"Stage '{name}' already exists."}

            # 2. Create Stage
            created_at = time.time()
            c.execute("INSERT INTO stages (name, description, created_at) VALUES (?, ?, ?)", 
                      (name, description, created_at))
            stage_id = c.lastrowid
            
            # 3. Add Items
            item_count = 0
            for item in items:
                file_path = item.get('file_path')
                version_id = item.get('version_id')
                
                if file_path and version_id:
                    c.execute("INSERT INTO stage_items (stage_id, file_path, version_id) VALUES (?, ?, ?)",
                              (stage_id, file_path, version_id))
                    item_count += 1
            
            conn.commit()
            server_logger.info(f"Stage '{name}' created with {item_count} items.")
            
            return {
                "status": "success", 
                "stage_id": stage_id,
                "item_count": item_count
            }

        except Exception as e:
            server_logger.error(f"Failed to create stage: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()

    def get_stages(self) -> List[Dict[str, Any]]:
        """列出所有階段"""
        conn, _ = get_db(self.project_path)
        c = conn.cursor()
        try:
            c.execute("SELECT id, name, description, created_at FROM stages ORDER BY created_at DESC")
            rows = c.fetchall()
            stages = []
            for r in rows:
                stages.append({
                    "id": r[0],
                    "name": r[1],
                    "description": r[2],
                    "created_at": r[3]
                })
            return stages
        finally:
            conn.close()

    def get_stage_items(self, stage_id: int) -> List[Dict[str, Any]]:
        """取得特定階段包含的檔案版本"""
        conn, _ = get_db(self.project_path)
        c = conn.cursor()
        try:
            c.execute("""
                SELECT file_path, version_id 
                FROM stage_items 
                WHERE stage_id = ?
            """, (stage_id,))
            rows = c.fetchall()
            return [{"file_path": r[0], "version_id": r[1]} for r in rows]
        finally:
            conn.close()
