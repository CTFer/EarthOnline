# -*- coding: utf-8 -*-
"""
教师服务
"""
from typing import Dict, Any, List
from ..models.user import TeacherUser
from ..models.class_model import TeacherClass
from ..models.student import TeacherStudent
from ..models.material import TeacherMaterial
from ..models.completion import TeacherCompletion

class TeacherService:
    """教师服务类"""
    
    def __init__(self, db_path: str = None):
        self.user_model = TeacherUser(db_path)
        self.class_model = TeacherClass(db_path)
        self.student_model = TeacherStudent(db_path)
        self.material_model = TeacherMaterial(db_path)
        self.completion_model = TeacherCompletion(db_path)
    
    def get_dashboard_data(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师仪表盘数据"""
        try:
            # 获取班级统计
            class_stats = self.class_model.get_class_with_student_count(teacher_id)
            total_classes = len(class_stats)
            total_students = sum(cls['student_count'] for cls in class_stats)
            
            # 获取学生统计
            student_stats = self.student_model.get_student_statistics(teacher_id)
            
            # 获取材料统计
            material_stats = self.material_model.get_material_statistics(teacher_id)
            
            # 获取完成统计
            completion_stats = self.completion_model.get_teacher_completion_statistics(teacher_id)
            
            # 获取即将到期的材料
            upcoming_materials = self.material_model.get_materials_by_deadline(teacher_id, 7)
            
            return {
                'success': True,
                'data': {
                    'classes': {
                        'total': total_classes,
                        'list': class_stats[:5]  # 最近5个班级
                    },
                    'students': student_stats,
                    'materials': material_stats,
                    'completion': completion_stats,
                    'upcoming_materials': upcoming_materials
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取仪表盘数据失败: {str(e)}',
                'data': None
            }
    
    def get_teacher_profile(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师详细资料"""
        try:
            teacher = self.user_model.get_by_id(teacher_id)
            if not teacher:
                return {
                    'success': False,
                    'message': '教师不存在',
                    'data': None
                }
            
            # 移除敏感信息
            teacher_data = {k: v for k, v in teacher.items() if k not in ['password']}
            
            return {
                'success': True,
                'data': teacher_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取教师资料失败: {str(e)}',
                'data': None
            }
    
    def update_teacher_profile(self, teacher_id: int, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新教师资料"""
        try:
            # 移除不允许更新的字段
            restricted_fields = ['id', 'phone', 'password', 'create_time', 'last_login']
            filtered_data = {k: v for k, v in profile_data.items() if k not in restricted_fields}
            
            if not filtered_data:
                return {
                    'success': False,
                    'message': '没有可更新的数据',
                    'data': None
                }
            
            # 更新资料
            self.user_model.update_profile(teacher_id, filtered_data)
            
            return {
                'success': True,
                'message': '更新成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'更新失败: {str(e)}',
                'data': None
            }
    
    def get_teacher_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师统计信息"""
        try:
            # 获取各类统计信息
            class_stats = self.class_model.get_class_with_student_count(teacher_id)
            student_stats = self.student_model.get_student_statistics(teacher_id)
            material_stats = self.material_model.get_material_statistics(teacher_id)
            completion_stats = self.completion_model.get_teacher_completion_statistics(teacher_id)
            
            return {
                'success': True,
                'data': {
                    'classes': {
                        'total': len(class_stats),
                        'active': len([cls for cls in class_stats if cls['status'] == 1])
                    },
                    'students': student_stats,
                    'materials': material_stats,
                    'completion': completion_stats
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取统计信息失败: {str(e)}',
                'data': None
            }
    
    def get_recent_activities(self, teacher_id: int, limit: int = 10) -> Dict[str, Any]:
        """获取最近活动"""
        try:
            # 获取最近创建的材料
            recent_materials = self.material_model.get_active_materials(teacher_id)[:limit]
            
            # 获取最近添加的学生
            recent_students = self.student_model.get_active_students(teacher_id)[:limit]
            
            # 获取最近创建的班级
            recent_classes = self.class_model.get_active_classes(teacher_id)[:limit]
            
            return {
                'success': True,
                'data': {
                    'materials': recent_materials,
                    'students': recent_students,
                    'classes': recent_classes
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取最近活动失败: {str(e)}',
                'data': None
            }
