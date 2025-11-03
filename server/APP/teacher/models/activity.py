# -*- coding: utf-8 -*-
"""
活动模型
"""
from typing import Optional, List, Dict, Any
from .base import BaseModel

class TeacherActivity(BaseModel):
    """活动模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_activity"
    
    def create_activity(self, teacher_id: int, title: str, start_time: str, 
                       end_time: str, **kwargs) -> int:
        """创建活动"""
        data = {
            'teacher_id': teacher_id,
            'title': title,
            'start_time': start_time,
            'end_time': end_time,
            **kwargs
        }
        
        return self.insert(self.table_name, data)
    
    def get_by_teacher(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的所有活动"""
        return self.get_all(self.table_name, "teacher_id = ?", (teacher_id,))
    
    def get_active_activities(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的活跃活动"""
        return self.get_all(self.table_name, "teacher_id = ? AND status = 1", (teacher_id,))
    
    def get_public_activities(self) -> List[Dict[str, Any]]:
        """获取公开活动"""
        query = """
            SELECT a.*, u.name as teacher_name
            FROM teacher_activity a
            JOIN teacher_user u ON a.teacher_id = u.id
            WHERE a.status = 1
            ORDER BY a.start_time DESC
        """
        return self.execute_query(query)
    
    def get_upcoming_activities(self, teacher_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """获取即将开始的活动"""
        query = """
            SELECT * FROM teacher_activity
            WHERE teacher_id = ? AND status = 1
            AND start_time > datetime('now')
            ORDER BY start_time ASC
            LIMIT ?
        """
        return self.execute_query(query, (teacher_id, limit))
    
    def get_past_activities(self, teacher_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取过去的活动"""
        query = """
            SELECT * FROM teacher_activity
            WHERE teacher_id = ? AND status = 1
            AND end_time < datetime('now')
            ORDER BY end_time DESC
            LIMIT ?
        """
        return self.execute_query(query, (teacher_id, limit))
    
    def update_activity(self, activity_id: int, **kwargs) -> int:
        """更新活动信息"""
        return self.update_by_id(self.table_name, activity_id, kwargs)
    
    def deactivate_activity(self, activity_id: int) -> int:
        """停用活动"""
        return self.update_by_id(self.table_name, activity_id, {'status': 0})
    
    def activate_activity(self, activity_id: int) -> int:
        """激活活动"""
        return self.update_by_id(self.table_name, activity_id, {'status': 1})
    
    def get_activity_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取活动统计信息"""
        # 总活动数
        total_query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE teacher_id = ?"
        total_results = self.execute_query(total_query, (teacher_id,))
        total_activities = total_results[0]['count'] if total_results else 0
        
        # 即将开始的活动
        upcoming_query = """
            SELECT COUNT(*) as count 
            FROM teacher_activity
            WHERE teacher_id = ? AND status = 1
            AND start_time > datetime('now')
        """
        upcoming_results = self.execute_query(upcoming_query, (teacher_id,))
        upcoming_count = upcoming_results[0]['count'] if upcoming_results else 0
        
        # 已结束的活动
        past_query = """
            SELECT COUNT(*) as count 
            FROM teacher_activity
            WHERE teacher_id = ? AND status = 1
            AND end_time < datetime('now')
        """
        past_results = self.execute_query(past_query, (teacher_id,))
        past_count = past_results[0]['count'] if past_results else 0
        
        return {
            'total_activities': total_activities,
            'upcoming_activities': upcoming_count,
            'past_activities': past_count
        }
