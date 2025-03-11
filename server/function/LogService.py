"""
日志服务模块，负责初始化和管理应用日志
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json
import uuid
from functools import wraps
from typing import Dict, List, Optional, Callable
from flask import request, jsonify
from utils.response_handler import ResponseHandler, StatusCode

class LogService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LogService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.logger = None
        self.request_logs = []  # 请求记录列表
        self.MAX_LOGS = 100    # 最多保存100条记录
        self.websocket_service = None  # 将在init_websocket中设置
        
    def setup_logging(self, debug_mode: bool = False) -> logging.Logger:
        """配置日志系统
        
        Args:
            debug_mode: 是否启用调试模式
            
        Returns:
            logging.Logger: 配置好的日志记录器
        """
        # 创建日志目录
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 设置日志文件名
        log_file = os.path.join(log_dir, f'{datetime.now().strftime("%Y-%m-%d")}.log')
        
        # 设置日志级别
        log_level = logging.DEBUG if debug_mode else logging.INFO
        
        # 创建日志处理器
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10
        )
        
        console_handler = logging.StreamHandler()
        
        # 设置日志格式
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 设置日志级别
        file_handler.setLevel(log_level)
        console_handler.setLevel(log_level)
        
        # 创建logger
        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        
        # 清除现有的处理器
        logger.handlers = []
        
        # 添加处理器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 保存logger实例
        self.logger = logger
        
        return logger
        
    def init_app(self, app):
        """初始化应用日志"""
        # 添加处理器到应用
        if self.logger:
            app.logger.handlers = self.logger.handlers
        
    def get_logger(self):
        """获取logger实例"""
        return self.logger
        
    def info(self, message):
        """记录INFO级别日志"""
        if self.logger:
            self.logger.info(message)
            
    def warning(self, message):
        """记录WARNING级别日志"""
        if self.logger:
            self.logger.warning(message)
            
    def error(self, message):
        """记录ERROR级别日志"""
        if self.logger:
            self.logger.error(message)
            
    def debug(self, message):
        """记录DEBUG级别日志"""
        if self.logger:
            self.logger.debug(message)
        
    def init_websocket(self, websocket_service) -> None:
        """初始化WebSocket服务"""
        self.websocket_service = websocket_service
            
    def add_request_log(self, log_entry: Dict) -> None:
        """添加新的请求记录"""
        self.request_logs.insert(0, log_entry)
        if len(self.request_logs) > self.MAX_LOGS:
            self.request_logs.pop()
            
    def get_request_logs(self, method_filter: str = None, path_filter: str = None) -> List[Dict]:
        """获取请求记录"""
        filtered_logs = self.request_logs
        
        if method_filter:
            filtered_logs = [log for log in filtered_logs if log['method'] == method_filter.upper()]
        if path_filter:
            filtered_logs = [log for log in filtered_logs if path_filter in log['path']]
            
        return filtered_logs
        
    def clear_logs(self) -> None:
        """清除所有请求记录"""
        self.request_logs = []
        
    def format_log_entry(self, entry: Dict) -> str:
        """格式化日志条目为HTML"""
        return f"""
            <div class="request-log">
                <div class="timestamp">{entry['timestamp']}</div>
                <div>
                    <span class="method {entry['method']}">{entry['method']}</span>
                    <span class="path">{entry['path']}</span>
                    <span class="ip">from {entry['remote_addr']}</span>
                </div>
                <pre>{json.dumps(entry, indent=2, ensure_ascii=False)}</pre>
            </div>
        """

    def log_request(self, f: Callable) -> Callable:
        """请求日志记录装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 获取请求信息
            log_entry = {
                'id': str(uuid.uuid4()),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'method': request.method,
                'path': request.path,
                'args': dict(request.args),
                'form': dict(request.form),
                'headers': {k: v for k, v in request.headers.items()},
                'remote_addr': request.remote_addr,
                'request_data': request.get_json() if request.is_json else None
            }

            try:
                response = f(*args, **kwargs)
                
                # 检查是否为静态文件响应
                if request.path.startswith('/static/'):
                    log_entry['response'] = {
                        'status_code': 200,
                        'data': {
                            'type': 'static_file',
                            'path': request.path
                        }
                    }
                    return response
                    
                # 处理其他类型的响应
                if isinstance(response, tuple):
                    response_data, status_code = response
                else:
                    response_data = response
                    status_code = 200

                # 处理Response对象
                if hasattr(response_data, 'get_json'):
                    try:
                        response_data = response_data.get_json()
                    except:
                        response_data = {
                            'type': 'non_json_response',
                            'mimetype': response_data.mimetype if hasattr(response_data, 'mimetype') else 'unknown'
                        }
                elif hasattr(response_data, 'response'):
                    try:
                        response_data = response_data.response[0].decode('utf-8')
                        response_data = json.loads(response_data)
                    except:
                        response_data = str(response_data.response)

                log_entry['response'] = {
                    'status_code': status_code,
                    'data': response_data
                }

            except Exception as e:
                self.logger.error(f"请求处理失败: {str(e)}", exc_info=True)
                log_entry['response'] = {
                    'error': str(e),
                    'status_code': 500
                }
                response = jsonify(ResponseHandler.error(
                    code=StatusCode.SERVER_ERROR,
                    msg=f"服务器错误: {str(e)}"
                )), 500

            # 记录请求日志
            self.add_request_log(log_entry)

            # 通过WebSocket广播日志更新
            if self.websocket_service:
                self.websocket_service.broadcast_log_update(
                    self.get_request_logs(),
                    log_entry
                )

            return response

        return decorated_function

# 创建日志服务实例
log_service = LogService() 