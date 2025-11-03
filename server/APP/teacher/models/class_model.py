# -*- coding: utf-8 -*-
"""
班级模型
"""
import random
import string
from typing import Optional, List, Dict, Any
from .base import BaseModel

class TeacherClass(BaseModel):
    """班级模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_class"
    
    def create_class(self, teacher_id: int, name: str, description: str = "") -> int:
        """创建班级"""
        # 生成唯一的班级代码
        class_code = self.generate_class_code()
        
        data = {
            'teacher_id': teacher_id,
            'class_code': class_code,
            'name': name,
            'description': description
        }
        
        return self.insert(self.table_name, data)
    
    def generate_class_code(self) -> str:
        """生成班级代码"""
        while True:
            # 生成6位随机字母数字组合
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            
            # 检查是否已存在
            query = f"SELECT COUNT(*) FROM {self.table_name} WHERE class_code = ?"
            results = self.execute_query(query, (code,))
            if results[0]['COUNT(*)'] == 0:
                return code
    
    def get_by_teacher(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的所有班级"""
        return self.get_all(self.table_name, "teacher_id = ?", (teacher_id,))
    
    def get_by_code(self, class_code: str) -> Optional[Dict[str, Any]]:
        """根据班级代码获取班级"""
        query = f"SELECT * FROM {self.table_name} WHERE class_code = ?"
        results = self.execute_query(query, (class_code,))
        return results[0] if results else None
    
    def get_active_classes(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的活跃班级"""
        return self.get_all(self.table_name, "teacher_id = ? AND status = 1", (teacher_id,))
    
    def update_class(self, class_id: int, name: str = None, description: str = None) -> int:
        """更新班级信息"""
        data = {}
        if name is not None:
            data['name'] = name
        if description is not None:
            data['description'] = description
        
        return self.update_by_id(self.table_name, class_id, data)
    
    def deactivate_class(self, class_id: int) -> int:
        """停用班级"""
        return self.update_by_id(self.table_name, class_id, {'status': 0})
    
    def activate_class(self, class_id: int) -> int:
        """激活班级"""
        return self.update_by_id(self.table_name, class_id, {'status': 1})
    
    def get_student_count(self, class_id: int) -> int:
        """获取班级学生数量"""
        query = """
            SELECT COUNT(*) as count 
            FROM teacher_student_class 
            WHERE class_id = ? AND status = 1
        """
        results = self.execute_query(query, (class_id,))
        return results[0]['count'] if results else 0
    
    def get_class_with_student_count(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取班级及其学生数量"""
        query = """
            SELECT c.*, 
                   COUNT(sc.student_id) as student_count
            FROM teacher_class c
            LEFT JOIN teacher_student_class sc ON c.id = sc.class_id AND sc.status = 1
            WHERE c.teacher_id = ? AND c.status = 1
            GROUP BY c.id
            ORDER BY c.create_time DESC
        """
        return self.execute_query(query, (teacher_id,))
