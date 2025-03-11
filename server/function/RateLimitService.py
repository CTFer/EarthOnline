"""
速率限制服务模块
处理应用程序的请求速率限制
"""
import logging
import time
from collections import defaultdict
from config.config import SECURITY
from flask import request, jsonify
from utils.response_handler import ResponseHandler, StatusCode

logger = logging.getLogger(__name__)

class RateLimitService:
    """速率限制服务类"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RateLimitService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """初始化速率限制服务"""
        if not hasattr(self, 'initialized'):
            self.request_counts = defaultdict(list)  # IP -> [(timestamp, count), ...]
            self.initialized = True
            
    def _clean_old_requests(self, ip):
        """清理过期的请求记录"""
        now = time.time()
        window = SECURITY['rate_limit']['window']
        self.request_counts[ip] = [
            (ts, count) for ts, count in self.request_counts[ip]
            if now - ts < window
        ]
        
    def check_rate_limit(self, ip):
        """检查是否超过速率限制"""
        if not SECURITY['rate_limit']['enabled']:
            return True
            
        self._clean_old_requests(ip)
        
        now = time.time()
        current_count = sum(count for _, count in self.request_counts[ip])
        
        if current_count >= SECURITY['rate_limit']['limit']:
            logger.warning(f"IP {ip} 超过速率限制")
            return False
            
        # 添加新的请求记录
        self.request_counts[ip].append((now, 1))
        return True
        
    def get_remaining_requests(self, ip):
        """获取剩余可用请求数"""
        if not SECURITY['rate_limit']['enabled']:
            return float('inf')
            
        self._clean_old_requests(ip)
        current_count = sum(count for _, count in self.request_counts[ip])
        return max(0, SECURITY['rate_limit']['limit'] - current_count)
        
    def handle_rate_limit(self):
        """处理速率限制检查"""
        ip = request.remote_addr
        if ip in SECURITY['white_ips']:
            return None
        if not self.check_rate_limit(ip):
            response = jsonify(ResponseHandler.error(
                code=StatusCode.FORBIDDEN,
                msg="请求过于频繁，请稍后再试"
            ))
            response.status_code = 429
            return response
            
        return None

# 创建速率限制服务实例
rate_limit_service = RateLimitService() 