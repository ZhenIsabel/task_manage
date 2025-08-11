import logging
import logging.handlers
import os

import os
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
ICON_PATH = os.path.join(APP_ROOT, "icons")

def init_logging():
    """统一初始化日志配置"""
    log_dir = os.path.join(APP_ROOT, "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    main_log = os.path.join(log_dir, "app.log")
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.handlers.RotatingFileHandler(
                main_log, 
                maxBytes=5*1024*1024,  # 5MB轮转
                backupCount=3,
                encoding='utf-8'
            ),
            logging.StreamHandler()
        ]
    )