# -*- coding: utf-8 -*-
"""
通知服务
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from ..models.material import TeacherMaterial
from ..models.completion import TeacherCompletion
from ..models.class_model import TeacherClass
from ..models.student import TeacherStudent

class NotificationService:
    """通知服务类"""
    
    def __init__(self, db_path: str = None):
        self.material_model = TeacherMaterial(db_path)
        self.completion_model = TeacherCompletion(db_path)
        self.class_model = TeacherClass(db_path)
        self.student_model = TeacherStudent(db_path)
    
    def get_teacher_notifications(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师通知"""
        try:
            notifications = []
            
            # 获取即将到期的材料
            upcoming_materials = self.material_model.get_materials_by_deadline(teacher_id, 3)
            for material in upcoming_materials:
                notifications.append({
                    'type': 'deadline_reminder',
                    'title': '作业即将到期',
                    'message': f"材料《{material['title']}》将在 {material['deadline']} 到期",
                    'priority': 'high',
                    'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # 获取今日到期的材料
            today_materials = self.material_model.get_materials_by_deadline(teacher_id, 0)
            for material in today_materials:
                notifications.append({
                    'type': 'deadline_today',
                    'title': '作业今日到期',
                    'message': f"材料《{material['title']}》今日到期",
                    'priority': 'urgent',
                    'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            # 获取完成率低的材料
            low_completion_materials = self._get_low_completion_materials(teacher_id)
            for material in low_completion_materials:
                notifications.append({
                    'type': 'low_completion',
                    'title': '完成率较低',
                    'message': f"材料《{material['title']}》完成率仅为 {material['completion_rate']}%",
                    'priority': 'medium',
                    'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return {
                'success': True,
                'data': notifications
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取通知失败: {str(e)}',
                'data': None
            }
    
    def _get_low_completion_materials(self, teacher_id: int, threshold: float = 50.0) -> List[Dict[str, Any]]:
        """获取完成率低的材料"""
        try:
            materials = self.material_model.get_active_materials(teacher_id)
            low_completion_materials = []
            
            for material in materials:
                stats = self.completion_model.get_completion_statistics(material['id'])
                if stats['completion_rate'] < threshold:
                    material['completion_rate'] = stats['completion_rate']
                    low_completion_materials.append(material)
            
            return low_completion_materials
            
        except Exception as e:
            return []
    
    def get_dashboard_summary(self, teacher_id: int) -> Dict[str, Any]:
        """获取仪表盘摘要"""
        try:
            # 获取基础统计
            class_stats = self.class_model.get_class_with_student_count(teacher_id)
            student_stats = self.student_model.get_student_statistics(teacher_id)
            material_stats = self.material_model.get_material_statistics(teacher_id)
            completion_stats = self.completion_model.get_teacher_completion_statistics(teacher_id)
            
            # 获取通知
            notifications = self.get_teacher_notifications(teacher_id)
            
            return {
                'success': True,
                'data': {
                    'classes': {
                        'total': len(class_stats),
                        'active': len([cls for cls in class_stats if cls['status'] == 1])
                    },
                    'students': student_stats,
                    'materials': material_stats,
                    'completion': completion_stats,
                    'notifications': notifications['data'] if notifications['success'] else []
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取仪表盘摘要失败: {str(e)}',
                'data': None
            }
    
    def get_material_reminders(self, teacher_id: int) -> Dict[str, Any]:
        """获取材料提醒"""
        try:
            # 获取即将到期的材料
            upcoming_materials = self.material_model.get_materials_by_deadline(teacher_id, 7)
            
            reminders = []
            for material in upcoming_materials:
                # 计算剩余天数
                deadline = datetime.strptime(material['deadline'], '%Y-%m-%d %H:%M:%S')
                days_left = (deadline - datetime.now()).days
                
                reminders.append({
                    'material_id': material['id'],
                    'title': material['title'],
                    'deadline': material['deadline'],
                    'days_left': days_left,
                    'priority': 'high' if days_left <= 1 else 'medium'
                })
            
            return {
                'success': True,
                'data': reminders
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取材料提醒失败: {str(e)}',
                'data': None
            }
    
    def get_completion_alerts(self, teacher_id: int) -> Dict[str, Any]:
        """获取完成情况提醒"""
        try:
            # 获取完成率低的材料
            low_completion_materials = self._get_low_completion_materials(teacher_id, 30.0)
            
            alerts = []
            for material in low_completion_materials:
                stats = self.completion_model.get_completion_statistics(material['id'])
                alerts.append({
                    'material_id': material['id'],
                    'title': material['title'],
                    'completion_rate': stats['completion_rate'],
                    'total_count': stats['total_count'],
                    'completed_count': stats['completed_count'],
                    'priority': 'high' if stats['completion_rate'] < 20 else 'medium'
                })
            
            return {
                'success': True,
                'data': alerts
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取完成提醒失败: {str(e)}',
                'data': None
            }
