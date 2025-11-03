# -*- coding: utf-8 -*-
"""
材料服务
"""
import os
import uuid
from typing import Dict, Any, List
from ..models.material import TeacherMaterial
from ..models.completion import TeacherCompletion
from ..models.student import TeacherStudent

class MaterialService:
    """材料服务类"""
    
    def __init__(self, db_path: str = None):
        self.material_model = TeacherMaterial(db_path)
        self.completion_model = TeacherCompletion(db_path)
        self.student_model = TeacherStudent(db_path)
    
    def create_material(self, teacher_id: int, title: str, material_type: str, 
                       file_name: str, file_path: str, **kwargs) -> Dict[str, Any]:
        """创建材料"""
        try:
            material_id = self.material_model.create_material(
                teacher_id, title, material_type, file_name, file_path, **kwargs
            )
            
            return {
                'success': True,
                'message': '材料创建成功',
                'data': {'material_id': material_id}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'材料创建失败: {str(e)}',
                'data': None
            }
    
    def get_teacher_materials(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师的所有材料"""
        try:
            materials = self.material_model.get_active_materials(teacher_id)
            
            return {
                'success': True,
                'data': materials
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取材料列表失败: {str(e)}',
                'data': None
            }
    
    def get_material_detail(self, material_id: int) -> Dict[str, Any]:
        """获取材料详情"""
        try:
            material = self.material_model.get_by_id(material_id)
            if not material:
                return {
                    'success': False,
                    'message': '材料不存在',
                    'data': None
                }
            
            # 获取材料分发对象
            targets = self.material_model.get_material_targets(material_id)
            
            # 获取完成统计
            completion_stats = self.completion_model.get_completion_statistics(material_id)
            
            return {
                'success': True,
                'data': {
                    'material': material,
                    'targets': targets,
                    'completion_stats': completion_stats
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取材料详情失败: {str(e)}',
                'data': None
            }
    
    def distribute_material(self, material_id: int, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分发材料"""
        try:
            success_count = 0
            failed_count = 0
            
            for target in targets:
                try:
                    if target['type'] == 'class':
                        self.material_model.distribute_to_class(material_id, target['id'])
                    elif target['type'] == 'student':
                        self.material_model.distribute_to_student(material_id, target['id'])
                    success_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"分发失败: {e}")
            
            return {
                'success': True,
                'message': f'材料分发完成，成功: {success_count}，失败: {failed_count}',
                'data': {
                    'success_count': success_count,
                    'failed_count': failed_count
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'材料分发失败: {str(e)}',
                'data': None
            }
    
    def get_student_materials(self, student_id: int) -> Dict[str, Any]:
        """获取学生的材料列表"""
        try:
            materials = self.material_model.get_student_materials(student_id)
            
            return {
                'success': True,
                'data': materials
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取学生材料失败: {str(e)}',
                'data': None
            }
    
    def update_material(self, material_id: int, **kwargs) -> Dict[str, Any]:
        """更新材料信息"""
        try:
            self.material_model.update_material(material_id, **kwargs)
            
            return {
                'success': True,
                'message': '材料更新成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'材料更新失败: {str(e)}',
                'data': None
            }
    
    def delete_material(self, material_id: int) -> Dict[str, Any]:
        """删除材料"""
        try:
            self.material_model.delete_material(material_id)
            
            return {
                'success': True,
                'message': '材料删除成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'材料删除失败: {str(e)}',
                'data': None
            }
    
    def get_material_completions(self, material_id: int) -> Dict[str, Any]:
        """获取材料完成情况"""
        try:
            completions = self.completion_model.get_material_completions(material_id)
            
            return {
                'success': True,
                'data': completions
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取完成情况失败: {str(e)}',
                'data': None
            }
    
    def update_completion_status(self, material_id: int, student_id: int, 
                               status: int, progress: int = None, last_position: int = None) -> Dict[str, Any]:
        """更新完成状态"""
        try:
            self.completion_model.update_completion_status(
                material_id, student_id, status, progress, last_position
            )
            
            return {
                'success': True,
                'message': '状态更新成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'状态更新失败: {str(e)}',
                'data': None
            }
    
    def get_material_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取材料统计信息"""
        try:
            stats = self.material_model.get_material_statistics(teacher_id)
            
            return {
                'success': True,
                'data': stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取材料统计失败: {str(e)}',
                'data': None
            }
    
    def get_upcoming_materials(self, teacher_id: int, days: int = 7) -> Dict[str, Any]:
        """获取即将到期的材料"""
        try:
            materials = self.material_model.get_materials_by_deadline(teacher_id, days)
            
            return {
                'success': True,
                'data': materials
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取即将到期材料失败: {str(e)}',
                'data': None
            }
