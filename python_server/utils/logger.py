import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Define log directory
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Log file path
LOG_FILE = os.path.join(LOG_DIR, "codesynth_server.log")

def key_value_formatter(record):
    """Formats log record as key-value pairs for easy parsing."""
    timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"timestamp={timestamp} level={record.levelname} logger={record.name} message=\"{record.getMessage()}\""
    
    if record.exc_info:
        log_entry += f" exception=\"{record.exc_info[0].__name__}: {record.exc_info[1]}\""
        
    return log_entry

class KeyValueFormatter(logging.Formatter):
    def format(self, record):
        return key_value_formatter(record)

def get_logger(name: str):
    """
    Returns a configured logger instance.
    Enforces:
    - Structured logging (Key-Value)
    - Log rotation (Max 5MB, 5 backups)
    - Console output for dev
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent duplicate handlers
    if logger.hasHandlers():
        return logger

    # 1. File Handler (Rotating)
    file_handler = RotatingFileHandler(
        LOG_FILE, 
        maxBytes=5*1024*1024, # 5MB limit
        backupCount=5,        # 5 backups
        encoding='utf-8'
    )
    file_handler.setFormatter(KeyValueFormatter())
    logger.addHandler(file_handler)

    # 2. Console Handler (Standard Format for readability)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger

# Global logger for general server events
server_logger = get_logger("server")
