from pydantic import BaseModel

class SnapshotRequest(BaseModel):
    project_path: str
    file_path: str
    content: str
    trigger: str
