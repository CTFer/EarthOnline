# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-03-11 11:46:01
# LastEditTime: 2025-03-27 22:10:12
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
from config.config import SECURITY, PROD_SERVER
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
            
    def is_security_enabled(self):
        """检查安全配置是否启用"""
        return SECURITY.get('open', False)
            
    def check_suspicious_request(self, path):
        """检查可疑请求"""
        if not self.is_security_enabled():
            return False
            
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
        """检查User-Agent
        
        如果请求包含有效的API密钥，则跳过用户代理检查
        """
        if not self.is_security_enabled():
            return True
        
        # 检查是否有有效的API密钥（用于自动化工具和API客户端）
        api_key = request.headers.get('X-API-KEY')
        if api_key and api_key == PROD_SERVER['API_KEY']:
            # API密钥有效，允许请求通过
            print(f"[Security] 检测到有效的API密钥，跳过用户代理检查")
            return True
        
        user_agent = request.headers.get('User-Agent', '').lower()
        blocked_agents = ['zgrab', 'python-requests', 'curl', 'wget', 'postman']
        
        if any(agent in user_agent for agent in blocked_agents):
            logger.warning(f"检测到可疑User-Agent: {user_agent} 来自 {request.remote_addr}")
            return False
        return True
        
    def check_path_injection(self):
        """检查路径注入"""
        if not self.is_security_enabled():
            return True
            
        return not ('..' in request.path or '//' in request.path)
        
    def add_security_headers(self, response):
        """添加安全响应头"""
        if not self.is_security_enabled():
            return response
            
        for header, value in SECURITY['headers'].items():
            response.headers[header] = value
        return response
        
    def handle_404(self, e):
        """处理404错误"""
        if not self.is_security_enabled():
            return jsonify(ResponseHandler.error(
                code=StatusCode.NOT_FOUND,
                msg="请求的资源不存在"
            )), 404
            
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
        if not self.is_security_enabled():
            return None
            
        # 检查用户代理，如果不通过直接返回响应
        user_agent_check = self.check_user_agent()
        if user_agent_check is not True:  # 确保不会返回布尔值
            return jsonify({
                'code': 403,
                'msg': 'Forbidden: Invalid User-Agent'
            }), 403
            
        # 检查路径注入，如果不通过直接返回响应
        path_check = self.check_path_injection()
        if path_check is not True:  # 确保不会返回布尔值
            return jsonify({
                'code': 400,
                'msg': 'Bad Request: Invalid Path'
            }), 400
            
        # 检查通过，返回 None（表示继续处理请求）
        return None

# 创建安全服务实例
security_service = SecurityService() 