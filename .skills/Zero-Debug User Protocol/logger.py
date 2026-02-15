import logging
from logging.handlers import RotatingFileHandler

# 定義標準錯誤碼 (建議 3)
ERROR_CODES = {
    "TIMEOUT": "ZD-TIMEOUT-001",
    "FILE_IO": "ZD-IO-002",
    "RISK_BLOCKED": "ZD-RISK-003",
    "CIRCUIT_OPEN": "ZD-SERVICE-004",
    "UNKNOWN": "ZD-UNKNOWN-999"
}

def setup_system_logger():
    """設定結構化日誌與自動旋轉 (Rule 6)"""
    log_file = "system.log"
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s')
    
    handler = RotatingFileHandler(
        log_file, maxBytes=5*1024*1024, backupCount=5, encoding='utf-8'
    )
    handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)
    logging.info("SYSTEM_V2: Production logger initialized.")
