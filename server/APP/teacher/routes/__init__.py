# -*- coding: utf-8 -*-
"""
教师系统路由包
"""
from .admin import admin_bp
from .student import student_bp
from .public import public_bp
from .api import api_bp

__all__ = [
    'admin_bp',
    'student_bp', 
    'public_bp',
    'api_bp'
]
