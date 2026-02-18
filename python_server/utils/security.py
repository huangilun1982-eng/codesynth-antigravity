import os
import re


def validate_project_path(path: str) -> bool:
    """驗證專案路徑是否安全且合法"""
    if not path or not isinstance(path, str):
        raise ValueError("專案路徑不可為空")

    # 解析為絕對路徑後比對，防止 symlink/.. 繞過
    resolved = os.path.realpath(path)

    if not os.path.exists(resolved):
        raise ValueError(f"路徑不存在: {path}")
    if not os.path.isdir(resolved):
        raise ValueError(f"路徑不是目錄: {path}")
    if not os.access(resolved, os.W_OK):
        raise ValueError(f"無寫入權限: {path}")

    # 禁止系統敏感目錄
    _forbidden = _get_forbidden_dirs()
    resolved_lower = resolved.lower().replace("\\", "/")
    for forbidden in _forbidden:
        if resolved_lower == forbidden.lower().replace("\\", "/"):
            raise ValueError(f"禁止操作系統目錄: {path}")

    return True


def validate_file_path(file_path: str) -> bool:
    """驗證檔案相對路徑是否安全"""
    if not file_path or not isinstance(file_path, str):
        raise ValueError("檔案路徑不可為空")

    # 使用 normpath 正規化後檢查是否仍嘗試向上遍歷
    normalized = os.path.normpath(file_path)
    
    # 禁止絕對路徑
    if os.path.isabs(normalized):
        raise ValueError(f"不接受絕對路徑: {file_path}")

    # 禁止向上遍歷（normpath 後仍以 .. 開頭代表逃逸）
    if normalized.startswith(".."):
        raise ValueError(f"非法檔案路徑：嘗試路徑遍歷: {file_path}")

    return True


def validate_project_name(name: str) -> bool:
    """驗證專案名稱是否安全（僅允許字母、數字、底線、連字號、空格）"""
    if not name or not isinstance(name, str):
        raise ValueError("專案名稱不可為空")
    if not re.match(r'^[\w\- ]+$', name, re.UNICODE):
        raise ValueError(f"專案名稱包含非法字元: {name}")
    if len(name) > 100:
        raise ValueError("專案名稱過長（上限 100 字元）")
    return True


def _get_forbidden_dirs() -> list:
    """取得禁止操作的系統目錄清單"""
    forbidden = [
        "/", "/bin", "/sbin", "/usr", "/etc", "/var", "/tmp",
        "/home", "/root", "/boot", "/dev", "/proc", "/sys",
    ]
    
    if os.name == 'nt':
        # Windows 系統目錄
        system_root = os.environ.get('SystemRoot', 'C:\\Windows')
        forbidden.extend([
            system_root,
            os.path.join(system_root, 'System32'),
            'C:\\',
            'C:\\Program Files',
            'C:\\Program Files (x86)',
        ])
    
    return forbidden
