# -*- coding: utf-8 -*-
"""
教师系统包初始化
"""
from .app import teacher_bp, create_teacher_blueprint

__version__ = '1.0.0'
__author__ = 'EarthOnline Team'
__description__ = '教师课后练习管理系统'

__all__ = [
    'teacher_bp',
    'create_teacher_blueprint'
]
