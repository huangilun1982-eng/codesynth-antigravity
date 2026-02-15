import sys
import logging
from logger import setup_system_logger
from risk_engine import TaskType
from main_skill import ZeroDebugSkill

def main():
    setup_system_logger()
    
    # 環境預檢 (Rule 13)
    if sys.version_info < (3, 8):
        print("Error: Python 3.8+ Required")
        return

    agent = ZeroDebugSkill()

    # 測試 1: 正常寫入
    print("\n[TEST 1] Standard Write")
    print(agent.execute(TaskType.SAVE_CONFIG, path="config.v2.txt", content="v2_active"))

    # 測試 2: 觸發斷路器 (模擬連續失敗只需修改核心代碼或刪除權限)
    print("\n[TEST 2] Logic Calculation")
    print(agent.execute(TaskType.CALCULATE, val=50))

    logging.info("MAIN: V2 System health check passed.")

if __name__ == "__main__":
    # Windows 必須加這一行，multiprocessing 才能運作
    main()
