# -*- coding: utf-8 -*-
"""
完成状态模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from .base import BaseModel

class TeacherCompletion(BaseModel):
    """完成状态模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_completion"
    
    def create_completion(self, material_id: int, student_id: int) -> int:
        """创建完成状态记录"""
        data = {
            'material_id': material_id,
            'student_id': student_id,
            'status': 0,
            'progress': 0,
            'last_position': 0
        }
        
        return self.insert(self.table_name, data)
    
    def get_by_material_and_student(self, material_id: int, student_id: int) -> Optional[Dict[str, Any]]:
        """根据材料和学生获取完成状态"""
        query = f"SELECT * FROM {self.table_name} WHERE material_id = ? AND student_id = ?"
        results = self.execute_query(query, (material_id, student_id))
        return results[0] if results else None
    
    def update_completion_status(self, material_id: int, student_id: int, 
                               status: int, progress: int = None, last_position: int = None) -> int:
        """更新完成状态"""
        data = {'status': status}
        
        if progress is not None:
            data['progress'] = progress
        if last_position is not None:
            data['last_position'] = last_position
        
        if status == 1:
            data['complete_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return self.update_by_id(self.table_name, 
                               self._get_completion_id(material_id, student_id), data)
    
    def _get_completion_id(self, material_id: int, student_id: int) -> int:
        """获取完成状态记录的ID"""
        completion = self.get_by_material_and_student(material_id, student_id)
        if completion:
            return completion['id']
        else:
            # 如果不存在，创建新记录
            return self.create_completion(material_id, student_id)
    
    def get_student_completions(self, student_id: int) -> List[Dict[str, Any]]:
        """获取学生的所有完成状态"""
        query = """
            SELECT c.*, m.title, m.type, m.deadline
            FROM teacher_completion c
            JOIN teacher_material m ON c.material_id = m.id
            WHERE c.student_id = ?
            ORDER BY m.deadline ASC
        """
        return self.execute_query(query, (student_id,))
    
    def get_material_completions(self, material_id: int) -> List[Dict[str, Any]]:
        """获取材料的所有完成状态"""
        query = """
            SELECT c.*, s.name as student_name, s.student_no
            FROM teacher_completion c
            JOIN teacher_student s ON c.student_id = s.id
            WHERE c.material_id = ?
            ORDER BY c.complete_time DESC
        """
        return self.execute_query(query, (material_id,))
    
    def get_completion_statistics(self, material_id: int) -> Dict[str, Any]:
        """获取材料完成统计"""
        # 总人数
        total_query = """
            SELECT COUNT(DISTINCT mt.target_id) as total
            FROM teacher_material_target mt
            WHERE mt.material_id = ?
        """
        total_results = self.execute_query(total_query, (material_id,))
        total_count = total_results[0]['total'] if total_results else 0
        
        # 已完成人数
        completed_query = f"""
            SELECT COUNT(*) as completed
            FROM {self.table_name}
            WHERE material_id = ? AND status = 1
        """
        completed_results = self.execute_query(completed_query, (material_id,))
        completed_count = completed_results[0]['completed'] if completed_results else 0
        
        # 完成率
        completion_rate = (completed_count / total_count * 100) if total_count > 0 else 0
        
        return {
            'total_count': total_count,
            'completed_count': completed_count,
            'completion_rate': round(completion_rate, 2)
        }
    
    def get_teacher_completion_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师的完成统计"""
        # 总作业数
        total_query = """
            SELECT COUNT(*) as total
            FROM teacher_material
            WHERE teacher_id = ? AND status = 1
        """
        total_results = self.execute_query(total_query, (teacher_id,))
        total_materials = total_results[0]['total'] if total_results else 0
        
        # 已完成作业数
        completed_query = """
            SELECT COUNT(DISTINCT c.material_id) as completed
            FROM teacher_completion c
            JOIN teacher_material m ON c.material_id = m.id
            WHERE m.teacher_id = ? AND c.status = 1
        """
        completed_results = self.execute_query(completed_query, (teacher_id,))
        completed_materials = completed_results[0]['completed'] if completed_results else 0
        
        # 今日到期作业数
        today_deadline_query = """
            SELECT COUNT(*) as today_deadline
            FROM teacher_material
            WHERE teacher_id = ? AND status = 1
            AND date(deadline) = date('now')
        """
        today_results = self.execute_query(today_deadline_query, (teacher_id,))
        today_deadline = today_results[0]['today_deadline'] if today_results else 0
        
        return {
            'total_materials': total_materials,
            'completed_materials': completed_materials,
            'today_deadline': today_deadline
        }
    
    def mark_as_completed(self, material_id: int, student_id: int) -> int:
        """标记为已完成"""
        return self.update_completion_status(material_id, student_id, 1, 100)
    
    def mark_as_incomplete(self, material_id: int, student_id: int) -> int:
        """标记为未完成"""
        return self.update_completion_status(material_id, student_id, 0, 0)
    
    def update_progress(self, material_id: int, student_id: int, progress: int, last_position: int = None) -> int:
        """更新进度"""
        return self.update_completion_status(material_id, student_id, 0, progress, last_position)
