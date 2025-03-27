"""
速率限制服务模块
处理应用程序的请求速率限制
"""
import logging
import time
from collections import defaultdict
from config.config import SECURITY, PROD_SERVER
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
        if ip not in self.request_counts:
            self.request_counts[ip] = []
            return
            
        now = time.time()
        window = SECURITY['rate_limit']['window']
        cutoff = now - window
        
        # 保留最近 window 秒内的记录
        self.request_counts[ip] = [t for t in self.request_counts[ip] if t > cutoff]
        
    def is_enabled(self):
        """检查速率限制是否启用"""
        return SECURITY['rate_limit']['enabled']
        
    def check_rate_limit(self, request):
        """
        检查请求是否超过速率限制
        
        Args:
            request: Flask 请求对象
        
        Returns:
            如果超过限制，返回 429 响应；否则返回 None
        """
        if not self.is_enabled() or request.method == 'OPTIONS':
            return None
        
        # 获取客户端 IP
        client_ip = request.remote_addr
        
        # 检查白名单
        if client_ip in SECURITY.get('white_ips', []):
            return None
            
        # 检查是否有效的API密钥
        api_key = request.headers.get('X-API-Key')
        if api_key and api_key == PROD_SERVER['API_KEY']:
            return None
        
        # 获取当前时间
        current_time = int(time.time())
        
        # 获取该 IP 的请求记录
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = []
        
        # 清理过期的请求记录
        window_start = current_time - SECURITY['rate_limit']['window']
        self.request_counts[client_ip] = [t for t in self.request_counts[client_ip] if t >= window_start]
        
        # 检查是否超过限制
        if len(self.request_counts[client_ip]) >= SECURITY['rate_limit']['limit']:
            # 超过限制，返回 429 响应
            logger.warning(f"IP {client_ip} 请求过于频繁，已被限制")
            return jsonify({
                'code': 429,
                'msg': '请求过于频繁，请稍后再试'
            }), 429
        
        # 记录本次请求
        self.request_counts[client_ip].append(current_time)
        
        # 未超过限制，返回 None
        return None
        
    def get_remaining_requests(self, ip):
        """获取剩余请求数量"""
        if not self.is_enabled():
            return None
            
        self._clean_old_requests(ip)
        
        now = time.time()
        current_count = sum(1 for t in self.request_counts[ip] if t > now - SECURITY['rate_limit']['window'])
        
        return SECURITY['rate_limit']['limit'] - current_count
        
    def handle_rate_limit(self, request):
        """处理速率限制
        
        Returns:
            如果超过限制，返回错误响应；否则返回 None
        """
        if not self.is_enabled():
            return None
            
        if request.path.startswith(('/static/', '/.well-known/')):
            return None
            
        client_ip = request.remote_addr
        
        # 检查白名单
        if client_ip in SECURITY.get('white_ips', []):
            return None
            
        # 检查是否超过速率限制
        limit_result = self.check_rate_limit(request)
        if limit_result is not None:
            # 已在 check_rate_limit 中返回了响应
            return limit_result
            
        # 未超过限制
        return None

# 创建速率限制服务实例
rate_limit_service = RateLimitService() 