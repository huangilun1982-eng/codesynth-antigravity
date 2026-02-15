import os  # <--- [FIXED] Added missing import
import logging
from typing import Dict, Any, Optional

# 引用專案模組
from logger import ERROR_CODES
from risk_engine import TaskType, RiskLevel, get_task_risk
from security_kernel import run_safe_write
from dependency_guard import CircuitBreaker

class ZeroDebugSkill:
    """
    零除錯技能核心協調器 (Zero-Debug Skill Coordinator)
    負責任務分派、風險評估、斷路器保護與錯誤攔截。
    """
    def __init__(self):
        # 將斷路器封裝在實例內部，避免全域污染 (Rule 1)
        self.io_breaker = CircuitBreaker("IO_Operations_Guard", max_failures=3, reset_timeout=30)
        self.state = "IDLE"  # 狀態機: IDLE / PROCESSING / COMPLETED / ERROR / UNAVAILABLE

    def execute(self, task: TaskType, **kwargs) -> Dict[str, Any]:
        """
        統一執行入口。保證不拋出 Traceback，只回傳結構化 JSON。
        """
        self.state = "PROCESSING"
        
        try:
            # 1. 風險評估
            risk = get_task_risk(task)
            
            # 2. 斷路器檢查 (僅針對高風險任務 Level C/D)
            if risk.value >= RiskLevel.C.value:
                if not self.io_breaker.can_execute():
                    self.state = "UNAVAILABLE"
                    return {
                        "status": "error",
                        "code": ERROR_CODES.get('CIRCUIT_OPEN', 'ZD-SERVICE-004'),
                        "message": "Service temporarily suspended due to repeated failures."
                    }

            # 3. 任務分派
            result_data = self._dispatch_task(task, kwargs)
            
            # 4. 成功後邏輯 (若為高風險任務，記錄成功以重置斷路器)
            if risk.value >= RiskLevel.C.value:
                self.io_breaker.record_success()

            self.state = "COMPLETED"
            return {"status": "success", "data": result_data}

        except TimeoutError:
            # 系統級超時 -> 扣血
            self.io_breaker.record_failure()
            self.state = "ERROR"
            logging.error(f"SKILL: Task {task.name} timed out.")
            return {
                "status": "error", 
                "code": ERROR_CODES.get('TIMEOUT', 'ZD-TIMEOUT-001'),
                "message": "Operation timed out."
            }
            
        except (ValueError, TypeError) as ve:
            # 使用者/驗證錯誤 -> 不扣血，僅回報 (Fix Issue #4 in Report)
            self.state = "ERROR"
            logging.warning(f"SKILL: Validation Error in {task.name}: {str(ve)}")
            return {
                "status": "error",
                "code": ERROR_CODES.get('RISK_BLOCKED', 'ZD-RISK-003'),
                "message": f"Input validation failed: {str(ve)}"
            }

        except Exception as e:
            # 未預期系統錯誤 -> 扣血
            self.io_breaker.record_failure()
            self.state = "ERROR"
            logging.critical(f"SKILL_CRASH: {str(e)}", exc_info=False) # No Traceback for user
            return {
                "status": "error", 
                "code": ERROR_CODES.get('UNKNOWN', 'ZD-UNKNOWN-999'),
                "message": "An internal protection fault occurred."
            }
        finally:
            # 狀態機重置 (若非不可用)
            if self.state != "UNAVAILABLE":
                self.state = "IDLE"

    def _dispatch_task(self, task: TaskType, params: Dict[str, Any]) -> Any:
        """
        內部任務分派器。
        """
        if task == TaskType.SAVE_CONFIG:
            return self._handle_save_config(params)
        
        elif task == TaskType.CALCULATE:
            return self._handle_calculate(params)
        
        elif task == TaskType.READ_DATA:
            return self._handle_read_data(params)
            
        elif task == TaskType.API_CALL:
            return self._handle_api_call(params)
            
        else:
            raise ValueError(f"Unsupported TaskType: {task}")

    # --- 個別任務處理器 (Handlers) ---

    def _handle_save_config(self, params: Dict[str, Any]) -> str:
        """處理設定檔寫入 (Level C)"""
        path = params.get("path")
        content = params.get("content")
        
        # 呼叫安全核心進行寫入
        run_safe_write(path, content, timeout=5)
        return f"Configuration saved safely to {path}"

    def _handle_calculate(self, params: Dict[str, Any]) -> int:
        """處理計算邏輯 (Level A)"""
        val = params.get("val")
        if not isinstance(val, (int, float)):
            raise TypeError("Parameter 'val' must be a number")
        return val * 2

    def _handle_read_data(self, params: Dict[str, Any]) -> str:
        """處理讀取 (Level B)"""
        path = params.get("path")
        if not path or not isinstance(path, str):
            raise ValueError("Invalid path")
            
        # 安全檢查：防止讀取工作目錄以外的檔案
        abs_path = os.path.abspath(path)
        base_dir = os.getcwd()
        if not abs_path.startswith(base_dir):
             raise ValueError(f"Security Access Denied: Path '{path}' is outside working directory.")

        if not os.path.exists(abs_path):
            raise ValueError(f"File not found: {path}")
            
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _handle_api_call(self, params: Dict[str, Any]) -> str:
        """處理外部 API (Level D) - 示範 stub"""
        # 在真實場景需加入 requests 與 timeout
        return "API response simulated"
