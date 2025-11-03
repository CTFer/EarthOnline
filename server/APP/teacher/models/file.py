# -*- coding: utf-8 -*-
"""
文件模型
"""
import hashlib
import os
from typing import Optional, List, Dict, Any
from .base import BaseModel

class TeacherFile(BaseModel):
    """文件模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_file"
    
    def create_file(self, teacher_id: int, original_name: str, stored_name: str, 
                   file_path: str, file_size: int, file_type: str, mime_type: str) -> int:
        """创建文件记录"""
        # 计算文件MD5
        file_hash = self._calculate_file_hash(file_path)
        
        data = {
            'teacher_id': teacher_id,
            'original_name': original_name,
            'stored_name': stored_name,
            'file_path': file_path,
            'file_size': file_size,
            'file_type': file_type,
            'mime_type': mime_type,
            'hash_md5': file_hash
        }
        
        return self.insert(self.table_name, data)
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """计算文件MD5哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def get_by_teacher(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的所有文件"""
        return self.get_all(self.table_name, "teacher_id = ?", (teacher_id,))
    
    def get_active_files(self, teacher_id: int) -> List[Dict[str, Any]]:
        """获取教师的活跃文件"""
        return self.get_all(self.table_name, "teacher_id = ? AND status = 1", (teacher_id,))
    
    def get_by_type(self, teacher_id: int, file_type: str) -> List[Dict[str, Any]]:
        """根据类型获取文件"""
        return self.get_all(self.table_name, "teacher_id = ? AND file_type = ? AND status = 1", 
                          (teacher_id, file_type))
    
    def get_by_hash(self, file_hash: str) -> Optional[Dict[str, Any]]:
        """根据MD5哈希值获取文件"""
        query = f"SELECT * FROM {self.table_name} WHERE hash_md5 = ?"
        results = self.execute_query(query, (file_hash,))
        return results[0] if results else None
    
    def update_file_url(self, file_id: int, file_url: str) -> int:
        """更新文件访问URL"""
        return self.update_by_id(self.table_name, file_id, {'file_url': file_url})
    
    def delete_file(self, file_id: int) -> int:
        """删除文件（软删除）"""
        return self.update_by_id(self.table_name, file_id, {'status': 0})
    
    def get_file_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取文件统计信息"""
        # 总文件数
        total_query = f"SELECT COUNT(*) as count FROM {self.table_name} WHERE teacher_id = ?"
        total_results = self.execute_query(total_query, (teacher_id,))
        total_files = total_results[0]['count'] if total_results else 0
        
        # 总文件大小
        size_query = f"SELECT SUM(file_size) as total_size FROM {self.table_name} WHERE teacher_id = ? AND status = 1"
        size_results = self.execute_query(size_query, (teacher_id,))
        total_size = size_results[0]['total_size'] if size_results and size_results[0]['total_size'] else 0
        
        # 按类型统计
        type_query = """
            SELECT file_type, COUNT(*) as count, SUM(file_size) as total_size
            FROM teacher_file 
            WHERE teacher_id = ? AND status = 1 
            GROUP BY file_type
        """
        type_results = self.execute_query(type_query, (teacher_id,))
        type_stats = {}
        for row in type_results:
            type_stats[row['file_type']] = {
                'count': row['count'],
                'total_size': row['total_size'] or 0
            }
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'type_statistics': type_stats
        }
    
    def cleanup_orphaned_files(self, teacher_id: int) -> int:
        """清理孤立的文件记录"""
        # 查找没有关联材料的文件
        query = """
            DELETE FROM teacher_file 
            WHERE teacher_id = ? AND status = 1
            AND id NOT IN (
                SELECT DISTINCT f.id 
                FROM teacher_file f
                JOIN teacher_material m ON f.file_path = m.file_path
                WHERE f.teacher_id = ?
            )
        """
        return self.execute_update(query, (teacher_id, teacher_id))
