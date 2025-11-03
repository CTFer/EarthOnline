# -*- coding: utf-8 -*-
"""
班级服务
"""
from typing import Dict, Any, List
from ..models.class_model import TeacherClass
from ..models.student import TeacherStudent

class ClassService:
    """班级服务类"""
    
    def __init__(self, db_path: str = None):
        self.class_model = TeacherClass(db_path)
        self.student_model = TeacherStudent(db_path)
    
    def create_class(self, teacher_id: int, name: str, description: str = "") -> Dict[str, Any]:
        """创建班级"""
        try:
            class_id = self.class_model.create_class(teacher_id, name, description)
            
            return {
                'success': True,
                'message': '班级创建成功',
                'data': {'class_id': class_id}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'班级创建失败: {str(e)}',
                'data': None
            }
    
    def get_teacher_classes(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师的所有班级"""
        try:
            classes = self.class_model.get_class_with_student_count(teacher_id)
            
            return {
                'success': True,
                'data': classes
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取班级列表失败: {str(e)}',
                'data': None
            }
    
    def get_class_detail(self, class_id: int) -> Dict[str, Any]:
        """获取班级详情"""
        try:
            class_info = self.class_model.get_by_id(class_id)
            if not class_info:
                return {
                    'success': False,
                    'message': '班级不存在',
                    'data': None
                }
            
            # 获取班级学生列表
            students = self.class_model.get_students_in_class(class_id)
            
            return {
                'success': True,
                'data': {
                    'class_info': class_info,
                    'students': students
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取班级详情失败: {str(e)}',
                'data': None
            }
    
    def update_class(self, class_id: int, name: str = None, description: str = None) -> Dict[str, Any]:
        """更新班级信息"""
        try:
            self.class_model.update_class(class_id, name, description)
            
            return {
                'success': True,
                'message': '班级更新成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'班级更新失败: {str(e)}',
                'data': None
            }
    
    def delete_class(self, class_id: int) -> Dict[str, Any]:
        """删除班级"""
        try:
            self.class_model.deactivate_class(class_id)
            
            return {
                'success': True,
                'message': '班级删除成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'班级删除失败: {str(e)}',
                'data': None
            }
    
    def add_student_to_class(self, class_id: int, student_id: int) -> Dict[str, Any]:
        """将学生添加到班级"""
        try:
            self.student_model.add_to_class(student_id, class_id)
            
            return {
                'success': True,
                'message': '学生添加成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'学生添加失败: {str(e)}',
                'data': None
            }
    
    def remove_student_from_class(self, class_id: int, student_id: int) -> Dict[str, Any]:
        """将学生从班级移除"""
        try:
            self.student_model.remove_from_class(student_id, class_id)
            
            return {
                'success': True,
                'message': '学生移除成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'学生移除失败: {str(e)}',
                'data': None
            }
    
    def get_class_students(self, class_id: int) -> Dict[str, Any]:
        """获取班级学生列表"""
        try:
            students = self.class_model.get_students_in_class(class_id)
            
            return {
                'success': True,
                'data': students
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取班级学生失败: {str(e)}',
                'data': None
            }
    
    def get_class_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取班级统计信息"""
        try:
            classes = self.class_model.get_class_with_student_count(teacher_id)
            
            total_classes = len(classes)
            total_students = sum(cls['student_count'] for cls in classes)
            active_classes = len([cls for cls in classes if cls['status'] == 1])
            
            return {
                'success': True,
                'data': {
                    'total_classes': total_classes,
                    'active_classes': active_classes,
                    'total_students': total_students,
                    'classes': classes
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取班级统计失败: {str(e)}',
                'data': None
            }
