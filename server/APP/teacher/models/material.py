# -*- coding: utf-8 -*-
"""
材料模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import BaseModel

class TeacherMaterial(BaseModel):
    """材料模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_material"
    
    def create_material(self, teacher_id: int, title: str, material_type: str, 
                       file_name: str, file_path: str, **kwargs) -> int:
        """创建材料"""
        data = {
            'teacher_id': teacher_id,
            'title': title,
            'type': material_type,
            'file_name': file_name,
            'file_path': file_path,
            **kwargs
        }
        
        return self.insert(self.table_name, data)
    
    def get_by_teacher(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的所有材料"""
        return self.get_all(self.table_name, "teacher_id = ?", (teacher_id,))
    
    def get_active_materials(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的活跃材料"""
        return self.get_all(self.table_name, "teacher_id = ? AND status = 1", (teacher_id,))
    
    def get_by_type(self, teacher_id: int, material_type: str) -> List[Dict[str, Any]]:
        """根据类型获取材料"""
        return self.get_all(self.table_name, "teacher_id = ? AND type = ? AND status = 1", 
                          (teacher_id, material_type))
    
    def get_public_materials(self) -> List[Dict[str, Any]]:
        """获取公开材料"""
        return self.get_all(self.table_name, "is_public = 1 AND status = 1")
    
    def distribute_to_class(self, material_id: int, class_id: int) -> int:
        """分发材料到班级"""
        data = {
            'material_id': material_id,
            'target_type': 'class',
            'target_id': class_id
        }
        
        return self.insert("teacher_material_target", data)
    
    def distribute_to_student(self, material_id: int, student_id: int) -> int:
        """分发材料到学生"""
        data = {
            'material_id': material_id,
            'target_type': 'student',
            'target_id': student_id
        }
        
        return self.insert("teacher_material_target", data)
    
    def get_student_materials(self, student_id: int) -> List[Dict[str, Any]]:
        """获取学生的材料列表"""
        query = """
            SELECT DISTINCT m.*, 
                   CASE WHEN c.status = 1 THEN 1 ELSE 0 END as is_completed
            FROM teacher_material m
            JOIN teacher_material_target mt ON m.id = mt.material_id
            LEFT JOIN teacher_completion c ON m.id = c.material_id AND c.student_id = ?
            WHERE (mt.target_type = 'student' AND mt.target_id = ?)
               OR (mt.target_type = 'class' AND mt.target_id IN (
                   SELECT class_id FROM teacher_student_class 
                   WHERE student_id = ? AND status = 1
               ))
            AND m.status = 1
            ORDER BY m.deadline ASC, m.create_time DESC
        """
        return self.execute_query(query, (student_id, student_id, student_id))
    
    def get_material_targets(self, material_id: int) -> List[Dict[str, Any]]:
        """获取材料的分发对象"""
        query = """
            SELECT mt.*, 
                   CASE 
                       WHEN mt.target_type = 'class' THEN c.name
                       WHEN mt.target_type = 'student' THEN s.name
                   END as target_name
            FROM teacher_material_target mt
            LEFT JOIN teacher_class c ON mt.target_type = 'class' AND mt.target_id = c.id
            LEFT JOIN teacher_student s ON mt.target_type = 'student' AND mt.target_id = s.id
            WHERE mt.material_id = ?
        """
        return self.execute_query(query, (material_id,))
    
    def update_material(self, material_id: int, **kwargs) -> int:
        """更新材料信息"""
        return self.update_by_id(self.table_name, material_id, kwargs)
    
    def delete_material(self, material_id: int) -> int:
        """删除材料（软删除）"""
        return self.update_by_id(self.table_name, material_id, {'status': 0})
    
    def get_materials_by_deadline(self, teacher_id: int, days: int = 7) -> List[Dict[str, Any]]:
        """获取即将到期的材料"""
        query = """
            SELECT * FROM teacher_material 
            WHERE teacher_id = ? AND status = 1 
            AND deadline IS NOT NULL 
            AND deadline <= datetime('now', '+{} days')
            ORDER BY deadline ASC
        """.format(days)
        return self.execute_query(query, (teacher_id,))
    
    def get_material_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取材料统计信息"""
        # 总材料数
        total_query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE teacher_id = ?"
        total_results = self.execute_query(total_query, (teacher_id,))
        total_materials = total_results[0]['count'] if total_results else 0
        
        # 按类型统计
        type_query = """
            SELECT type, COUNT(*) as count 
            FROM teacher_material 
            WHERE teacher_id = ? AND status = 1 
            GROUP BY type
        """
        type_results = self.execute_query(type_query, (teacher_id,))
        type_stats = {row['type']: row['count'] for row in type_results}
        
        # 即将到期的材料
        deadline_query = """
            SELECT COUNT(*) as count 
            FROM teacher_material 
            WHERE teacher_id = ? AND status = 1 
            AND deadline IS NOT NULL 
            AND deadline <= datetime('now', '+7 days')
        """
        deadline_results = self.execute_query(deadline_query, (teacher_id,))
        upcoming_deadline = deadline_results[0]['count'] if deadline_results else 0
        
        return {
            'total_materials': total_materials,
            'type_statistics': type_stats,
            'upcoming_deadline': upcoming_deadline
        }
