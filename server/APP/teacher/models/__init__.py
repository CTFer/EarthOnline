# -*- coding: utf-8 -*-
"""
教师系统数据模型包
"""
from .base import BaseModel
from .user import TeacherUser
from .class_model import TeacherClass
from .student import TeacherStudent
from .material import TeacherMaterial
from .completion import TeacherCompletion
from .activity import TeacherActivity
from .course import TeacherCourse
from .file import TeacherFile

__all__ = [
    'BaseModel',
    'TeacherUser',
    'TeacherClass', 
    'TeacherStudent',
    'TeacherMaterial',
    'TeacherCompletion',
    'TeacherActivity',
    'TeacherCourse',
    'TeacherFile'
]
