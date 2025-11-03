# -*- coding: utf-8 -*-
"""
学生模型
"""
from typing import Optional, List, Dict, Any
from .base import BaseModel

class TeacherStudent(BaseModel):
    """学生模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_student"
    
    def create_student(self, teacher_id: int, name: str, student_no: str = None, **kwargs) -> int:
        """创建学生"""
        data = {
            'teacher_id': teacher_id,
            'name': name,
            'student_no': student_no,
            **kwargs
        }
        
        return self.insert(self.table_name, data)
    
    def get_by_teacher(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的所有学生"""
        return self.get_all(self.table_name, "teacher_id = ?", (teacher_id,))
    
    def get_active_students(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的活跃学生"""
        return self.get_all(self.table_name, "teacher_id = ? AND status = 1", (teacher_id,))
    
    def get_by_name(self, teacher_id: int, name: str) -> List[Dict[str, Any]]:
        """根据姓名搜索学生"""
        return self.get_all(self.table_name, "teacher_id = ? AND name LIKE ?", (teacher_id, f"%{name}%"))
    
    def add_to_class(self, student_id: int, class_id: int) -> int:
        """将学生添加到班级"""
        data = {
            'student_id': student_id,
            'class_id': class_id
        }
        
        return self.insert("teacher_student_class", data)
    
    def remove_from_class(self, student_id: int, class_id: int) -> int:
        """将学生从班级移除"""
        query = """
            UPDATE teacher_student_class 
            SET status = 0 
            WHERE student_id = ? AND class_id = ?
        """
        return self.execute_update(query, (student_id, class_id))
    
    def get_students_in_class(self, class_id: int) -> List[Dict[str, Any]]:
        """获取班级中的所有学生"""
        query = """
            SELECT s.*, sc.join_time
            FROM teacher_student s
            JOIN teacher_student_class sc ON s.id = sc.student_id
            WHERE sc.class_id = ? AND sc.status = 1 AND s.status = 1
            ORDER BY sc.join_time DESC
        """
        return self.execute_query(query, (class_id,))
    
    def get_student_classes(self, student_id: int) -> List[Dict[str, Any]]:
        """获取学生所属的班级"""
        query = """
            SELECT c.*, sc.join_time
            FROM teacher_class c
            JOIN teacher_student_class sc ON c.id = sc.class_id
            WHERE sc.student_id = ? AND sc.status = 1 AND c.status = 1
            ORDER BY sc.join_time DESC
        """
        return self.execute_query(query, (student_id,))
    
    def verify_student(self, class_code: str, student_name: str) -> Optional[Dict[str, Any]]:
        """验证学生身份（班级代码+姓名）"""
        query = """
            SELECT s.*, c.name as class_name, c.class_code
            FROM teacher_student s
            JOIN teacher_student_class sc ON s.id = sc.student_id
            JOIN teacher_class c ON sc.class_id = c.id
            WHERE c.class_code = ? AND s.name = ? 
            AND sc.status = 1 AND s.status = 1 AND c.status = 1
        """
        results = self.execute_query(query, (class_code, student_name))
        return results[0] if results else None
    
    def update_student(self, student_id: int, **kwargs) -> int:
        """更新学生信息"""
        return self.update_by_id(self.table_name, student_id, kwargs)
    
    def deactivate_student(self, student_id: int) -> int:
        """停用学生"""
        return self.update_by_id(self.table_name, student_id, {'status': 0})
    
    def activate_student(self, student_id: int) -> int:
        """激活学生"""
        return self.update_by_id(self.table_name, student_id, {'status': 1})
    
    def get_student_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取学生统计信息"""
        # 总学生数
        total_query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE teacher_id = ?"
        total_results = self.execute_query(total_query, (teacher_id,))
        total_students = total_results[0]['count'] if total_results else 0
        
        # 活跃学生数
        active_query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE teacher_id = ? AND status = 1"
        active_results = self.execute_query(active_query, (teacher_id,))
        active_students = active_results[0]['count'] if active_results else 0
        
        return {
            'total_students': total_students,
            'active_students': active_students,
            'inactive_students': total_students - active_students
        }
