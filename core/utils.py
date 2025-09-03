import logging
import logging.handlers
import os
import sys
import traceback

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
    
    # 设置全局异常处理器
    def handle_exception(exc_type, exc_value, exc_traceback):
        """全局异常处理器"""
        if issubclass(exc_type, KeyboardInterrupt):
            # 允许键盘中断正常处理
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger = logging.getLogger(__name__)
        logger.critical("未捕获的异常", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception