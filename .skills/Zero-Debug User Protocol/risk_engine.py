from enum import Enum

class TaskType(Enum):
    SAVE_CONFIG = "save_config"
    READ_DATA = "read_data"
    API_CALL = "api_call"
    CALCULATE = "calculate"

class RiskLevel(Enum):
    A = 1  # 低風險 (純計算)
    B = 2  # 中風險 (讀取)
    C = 3  # 高風險 (寫入/刪除)
    D = 4  # 外部風險 (API)

def get_task_risk(task_type: TaskType) -> RiskLevel:
    """精確定義每個任務的風險等級"""
    risk_mapping = {
        TaskType.SAVE_CONFIG: RiskLevel.C,
        TaskType.READ_DATA: RiskLevel.B,
        TaskType.API_CALL: RiskLevel.D,
        TaskType.CALCULATE: RiskLevel.A
    }
    return risk_mapping.get(task_type, RiskLevel.C)
