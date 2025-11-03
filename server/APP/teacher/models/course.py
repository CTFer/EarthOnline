# -*- coding: utf-8 -*-
"""
课程模型
"""
from typing import Optional, List, Dict, Any
from .base import BaseModel

class TeacherCourse(BaseModel):
    """课程模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_course"
    
    def create_course(self, teacher_id: int, name: str, **kwargs) -> int:
        """创建课程"""
        data = {
            'teacher_id': teacher_id,
            'name': name,
            **kwargs
        }
        
        return self.insert(self.table_name, data)
    
    def get_by_teacher(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的所有课程"""
        return self.get_all(self.table_name, "teacher_id = ?", (teacher_id,))
    
    def get_active_courses(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的活跃课程"""
        return self.get_all(self.table_name, "teacher_id = ? AND status = 1", (teacher_id,))
    
    def get_public_courses(self) -> List[Dict[str, Any]]:
        """获取公开课程"""
        query = """
            SELECT c.*, u.name as teacher_name
            FROM teacher_course c
            JOIN teacher_user u ON c.teacher_id = u.id
            WHERE c.status = 1
            ORDER BY c.create_time DESC
        """
        return self.execute_query(query)
    
    def get_courses_by_difficulty(self, teacher_id: int, difficulty: str) -> List[Dict[str, Any]]:
        """根据难度获取课程"""
        return self.get_all(self.table_name, "teacher_id = ? AND difficulty = ? AND status = 1", 
                          (teacher_id, difficulty))
    
    def get_courses_by_age(self, teacher_id: int, target_age: str) -> List[Dict[str, Any]]:
        """根据年龄段获取课程"""
        return self.get_all(self.table_name, "teacher_id = ? AND target_age = ? AND status = 1", 
                          (teacher_id, target_age))
    
    def get_online_courses(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取线上课程"""
        return self.get_all(self.table_name, "teacher_id = ? AND is_online = 1 AND status = 1", (teacher_id,))
    
    def get_offline_courses(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取线下课程"""
        return self.get_all(self.table_name, "teacher_id = ? AND is_online = 0 AND status = 1", (teacher_id,))
    
    def update_course(self, course_id: int, **kwargs) -> int:
        """更新课程信息"""
        return self.update_by_id(self.table_name, course_id, kwargs)
    
    def deactivate_course(self, course_id: int) -> int:
        """停用课程"""
        return self.update_by_id(self.table_name, course_id, {'status': 0})
    
    def activate_course(self, course_id: int) -> int:
        """激活课程"""
        return self.update_by_id(self.table_name, course_id, {'status': 1})
    
    def get_course_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取课程统计信息"""
        # 总课程数
        total_query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE teacher_id = ?"
        total_results = self.execute_query(total_query, (teacher_id,))
        total_courses = total_results[0]['count'] if total_results else 0
        
        # 按类型统计
        type_query = """
            SELECT is_online, COUNT(*) as count 
            FROM teacher_course 
            WHERE teacher_id = ? AND status = 1 
            GROUP BY is_online
        """
        type_results = self.execute_query(type_query, (teacher_id,))
        online_count = 0
        offline_count = 0
        for row in type_results:
            if row['is_online'] == 1:
                online_count = row['count']
            else:
                offline_count = row['count']
        
        # 按难度统计
        difficulty_query = """
            SELECT difficulty, COUNT(*) as count 
            FROM teacher_course 
            WHERE teacher_id = ? AND status = 1 
            GROUP BY difficulty
        """
        difficulty_results = self.execute_query(difficulty_query, (teacher_id,))
        difficulty_stats = {row['difficulty']: row['count'] for row in difficulty_results}
        
        return {
            'total_courses': total_courses,
            'online_courses': online_count,
            'offline_courses': offline_count,
            'difficulty_statistics': difficulty_stats
        }
