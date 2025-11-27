# -*- coding: utf-8 -*-

"""
WorkData应用初始化文件
提供Flask蓝图注册功能
"""
from .app import create_workdata_blueprint, workdata_bp

__all__ = ['create_workdata_blueprint', 'workdata_bp']