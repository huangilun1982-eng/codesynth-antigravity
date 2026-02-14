import os

def validate_project_path(path: str) -> str:
    """
    驗證專案路徑的安全性
    防止路徑遍歷和訪問敏感目錄
    """
    # 1. 轉換為絕對路徑
    abs_path = os.path.abspath(path)
    
    # 2. 檢查路徑是否存在
    if not os.path.exists(abs_path):
        raise ValueError(f"路徑不存在: {abs_path}")
    
    # 3. 檢查是否為目錄
    if not os.path.isdir(abs_path):
        raise ValueError(f"不是目錄: {abs_path}")
    
    # 4. 檢查寫入權限
    if not os.access(abs_path, os.W_OK):
        raise ValueError(f"無寫入權限: {abs_path}")
    
    # 5. 禁止系統目錄（Windows 和 Linux）
    forbidden_patterns = [
        "C:\\Windows", "C:\\Program Files",  # Windows
        "/root", "/etc", "/sys", "/proc", "/boot"  # Linux
    ]
    
    for forbidden in forbidden_patterns:
        if abs_path.startswith(forbidden):
            raise ValueError(f"禁止訪問系統目錄: {abs_path}")
    
    return abs_path

def validate_file_path(file_path: str) -> str:
    """
    驗證檔案路徑的安全性
    防止路徑遍歷攻擊
    """
    # 禁止路徑遍歷
    if '..' in file_path:
        raise ValueError("非法檔案路徑：包含 '..'")
    
    # 禁止絕對路徑
    if os.path.isabs(file_path):
        raise ValueError("非法檔案路徑：不允許絕對路徑")
    
    # Normalized: Windows -> lowercase & backslash
    return os.path.normcase(file_path)
