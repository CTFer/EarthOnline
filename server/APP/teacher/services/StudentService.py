# -*- coding: utf-8 -*-
"""
学生服务
"""
from typing import Dict, Any, List
from ..models.student import TeacherStudent
from ..models.class_model import TeacherClass

class StudentService:
    """学生服务类"""
    
    def __init__(self, db_path: str = None):
        self.student_model = TeacherStudent(db_path)
        self.class_model = TeacherClass(db_path)
    
    def create_student(self, teacher_id: int, name: str, **kwargs) -> Dict[str, Any]:
        """创建学生"""
        try:
            student_id = self.student_model.create_student(teacher_id, name, **kwargs)
            
            return {
                'success': True,
                'message': '学生创建成功',
                'data': {'student_id': student_id}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'学生创建失败: {str(e)}',
                'data': None
            }
    
    def get_teacher_students(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师的所有学生"""
        try:
            students = self.student_model.get_active_students(teacher_id)
            
            return {
                'success': True,
                'data': students
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取学生列表失败: {str(e)}',
                'data': None
            }
    
    def get_student_detail(self, student_id: int) -> Dict[str, Any]:
        """获取学生详情"""
        try:
            student = self.student_model.get_by_id(student_id)
            if not student:
                return {
                    'success': False,
                    'message': '学生不存在',
                    'data': None
                }
            
            # 获取学生所属班级
            classes = self.student_model.get_student_classes(student_id)
            
            return {
                'success': True,
                'data': {
                    'student': student,
                    'classes': classes
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取学生详情失败: {str(e)}',
                'data': None
            }
    
    def update_student(self, student_id: int, **kwargs) -> Dict[str, Any]:
        """更新学生信息"""
        try:
            self.student_model.update_student(student_id, **kwargs)
            
            return {
                'success': True,
                'message': '学生信息更新成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'学生信息更新失败: {str(e)}',
                'data': None
            }
    
    def delete_student(self, student_id: int) -> Dict[str, Any]:
        """删除学生"""
        try:
            self.student_model.deactivate_student(student_id)
            
            return {
                'success': True,
                'message': '学生删除成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'学生删除失败: {str(e)}',
                'data': None
            }
    
    def search_students(self, teacher_id: int, name: str) -> Dict[str, Any]:
        """搜索学生"""
        try:
            students = self.student_model.get_by_name(teacher_id, name)
            
            return {
                'success': True,
                'data': students
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'搜索学生失败: {str(e)}',
                'data': None
            }
    
    def get_student_classes(self, student_id: int) -> Dict[str, Any]:
        """获取学生所属班级"""
        try:
            classes = self.student_model.get_student_classes(student_id)
            
            return {
                'success': True,
                'data': classes
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取学生班级失败: {str(e)}',
                'data': None
            }
    
    def add_student_to_class(self, student_id: int, class_id: int) -> Dict[str, Any]:
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
    
    def remove_student_from_class(self, student_id: int, class_id: int) -> Dict[str, Any]:
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
    
    def get_student_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取学生统计信息"""
        try:
            stats = self.student_model.get_student_statistics(teacher_id)
            
            return {
                'success': True,
                'data': stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取学生统计失败: {str(e)}',
                'data': None
            }
    
    def batch_import_students(self, teacher_id: int, students_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量导入学生"""
        try:
            success_count = 0
            failed_count = 0
            failed_students = []
            
            for student_data in students_data:
                try:
                    # 添加教师ID
                    student_data['teacher_id'] = teacher_id
                    
                    # 创建学生
                    student_id = self.student_model.create_student(**student_data)
                    success_count += 1
                    
                    # 如果指定了班级，添加到班级
                    if 'class_id' in student_data:
                        self.student_model.add_to_class(student_id, student_data['class_id'])
                        
                except Exception as e:
                    failed_count += 1
                    failed_students.append({
                        'name': student_data.get('name', '未知'),
                        'error': str(e)
                    })
            
            return {
                'success': True,
                'message': f'批量导入完成，成功: {success_count}，失败: {failed_count}',
                'data': {
                    'success_count': success_count,
                    'failed_count': failed_count,
                    'failed_students': failed_students
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'批量导入失败: {str(e)}',
                'data': None
            }
