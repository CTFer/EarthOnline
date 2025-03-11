# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-03-11 11:46:01
# LastEditTime: 2025-03-11 19:52:54
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

"""
安全服务模块
处理应用程序的安全相关功能
"""
import logging
from flask import request, jsonify
from config.config import SECURITY
from utils.response_handler import ResponseHandler, StatusCode

logger = logging.getLogger(__name__)

class SecurityService:
    """安全服务类"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SecurityService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """初始化安全服务"""
        if not hasattr(self, 'initialized'):
            self.initialized = True
            
    def check_suspicious_request(self, path):
        """检查可疑请求"""
        suspicious_paths = [
            'wp-', 'wordpress', 'admin', 'setup', 'install',
            'phpmy', 'mysql', 'sql', 'database',
            '.env', '.git', '.svn',
            'shell', 'cmd', 'cgi',
            'config', 'conf', 'cfg',
            'php', 'asp', 'aspx', 'jsp'
        ]
        
        path = path.lower()
        is_suspicious = any(p in path for p in suspicious_paths)
        
        if is_suspicious:
            logger.warning(f"检测到可疑请求: {request.path} 来自 {request.remote_addr}")
            return True
        return False
        
    def check_user_agent(self):
        """检查User-Agent"""
        user_agent = request.headers.get('User-Agent', '').lower()
        blocked_agents = ['zgrab', 'python-requests', 'curl', 'wget', 'postman']
        
        if any(agent in user_agent for agent in blocked_agents):
            logger.warning(f"检测到可疑User-Agent: {user_agent} 来自 {request.remote_addr}")
            return False
        return True
        
    def check_request_method(self):
        """检查请求方法"""
        return request.method in SECURITY['cors']['allowed_methods']
        
    def check_path_injection(self):
        """检查路径注入"""
        return not ('..' in request.path or '//' in request.path)
        
    def add_security_headers(self, response):
        """添加安全响应头"""
        for header, value in SECURITY['headers'].items():
            response.headers[header] = value
        return response
        
    def handle_404(self, e):
        """处理404错误"""
        if self.check_suspicious_request(request.path):
            response = jsonify({
                'code': 403,
                'msg': 'Forbidden'
            })
            response.status_code = 403
            return response
        
        return jsonify(ResponseHandler.error(
            code=StatusCode.NOT_FOUND,
            msg="请求的资源不存在"
        )), 404
        
    def security_check(self):
        """请求安全检查"""
        if not self.check_user_agent():
            return jsonify({
                'code': 403,
                'msg': 'Forbidden'
            }), 403
            
        if not self.check_request_method():
            return jsonify({
                'code': 405,
                'msg': 'Method Not Allowed'
            }), 405
            
        if not self.check_path_injection():
            return jsonify({
                'code': 400,
                'msg': 'Bad Request'
            }), 400
            
        return None

# 创建安全服务实例
security_service = SecurityService() 