# -*- coding: utf-8 -*-
"""
文件服务
"""
import os
import uuid
import hashlib
from typing import Dict, Any, Optional
from ..models.file import TeacherFile

class FileService:
    """文件服务类"""
    
    def __init__(self, db_path: str = None, upload_folder: str = None):
        self.file_model = TeacherFile(db_path)
        self.upload_folder = upload_folder or os.path.join(os.path.dirname(__file__), '..', 'static', 'uploads')
        
        # 确保上传目录存在
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def save_file(self, teacher_id: int, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """保存文件"""
        try:
            # 验证文件类型和大小
            if not self.validate_file(file_data):
                return {
                    'success': False,
                    'message': '文件类型或大小不符合要求',
                    'data': None
                }
            
            # 生成唯一文件名
            file_extension = os.path.splitext(file_data['filename'])[1]
            stored_name = f"{uuid.uuid4()}{file_extension}"
            
            # 确定存储路径
            file_type = self.get_file_type(file_data['filename'])
            type_folder = os.path.join(self.upload_folder, file_type)
            os.makedirs(type_folder, exist_ok=True)
            
            file_path = os.path.join(type_folder, stored_name)
            
            # 保存文件
            with open(file_path, 'wb') as f:
                f.write(file_data['content'])
            
            # 获取文件信息
            file_size = os.path.getsize(file_path)
            mime_type = file_data.get('content_type', 'application/octet-stream')
            
            # 保存文件记录
            file_id = self.file_model.create_file(
                teacher_id=teacher_id,
                original_name=file_data['filename'],
                stored_name=stored_name,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type,
                mime_type=mime_type
            )
            
            # 生成访问URL
            file_url = self.generate_file_url(file_path)
            
            return {
                'success': True,
                'message': '文件保存成功',
                'data': {
                    'file_id': file_id,
                    'file_path': file_path,
                    'file_url': file_url,
                    'file_size': file_size
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'文件保存失败: {str(e)}',
                'data': None
            }
    
    def validate_file(self, file_data: Dict[str, Any]) -> bool:
        """验证文件类型和大小"""
        filename = file_data['filename']
        content = file_data['content']
        
        # 检查文件类型
        file_type = self.get_file_type(filename)
        if not file_type:
            return False
        
        # 检查文件大小
        file_size = len(content)
        max_sizes = {
            'video': 200 * 1024 * 1024,  # 200MB
            'audio': 50 * 1024 * 1024,   # 50MB
            'document': 20 * 1024 * 1024  # 20MB
        }
        
        if file_size > max_sizes.get(file_type, 20 * 1024 * 1024):
            return False
        
        return True
    
    def get_file_type(self, filename: str) -> Optional[str]:
        """根据文件名获取文件类型"""
        extension = os.path.splitext(filename)[1].lower()
        
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv']
        audio_extensions = ['.mp3', '.wav', '.m4a', '.aac', '.ogg']
        document_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
        
        if extension in video_extensions:
            return 'video'
        elif extension in audio_extensions:
            return 'audio'
        elif extension in document_extensions:
            return 'document'
        else:
            return None
    
    def generate_file_url(self, file_path: str) -> str:
        """生成文件访问URL"""
        # 将绝对路径转换为相对路径
        relative_path = os.path.relpath(file_path, self.upload_folder)
        return f"/teacher/static/uploads/{relative_path.replace(os.sep, '/')}"
    
    def get_file_info(self, file_id: int) -> Dict[str, Any]:
        """获取文件信息"""
        try:
            file_info = self.file_model.get_by_id(file_id)
            if not file_info:
                return {
                    'success': False,
                    'message': '文件不存在',
                    'data': None
                }
            
            return {
                'success': True,
                'data': file_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取文件信息失败: {str(e)}',
                'data': None
            }
    
    def delete_file(self, file_id: int) -> Dict[str, Any]:
        """删除文件"""
        try:
            # 获取文件信息
            file_info = self.file_model.get_by_id(file_id)
            if not file_info:
                return {
                    'success': False,
                    'message': '文件不存在',
                    'data': None
                }
            
            # 删除物理文件
            if os.path.exists(file_info['file_path']):
                os.remove(file_info['file_path'])
            
            # 删除数据库记录
            self.file_model.delete_file(file_id)
            
            return {
                'success': True,
                'message': '文件删除成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'文件删除失败: {str(e)}',
                'data': None
            }
    
    def get_teacher_files(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师的所有文件"""
        try:
            files = self.file_model.get_active_files(teacher_id)
            
            return {
                'success': True,
                'data': files
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取文件列表失败: {str(e)}',
                'data': None
            }
    
    def get_file_statistics(self, teacher_id: int) -> Dict[str, Any]:
        """获取文件统计信息"""
        try:
            stats = self.file_model.get_file_statistics(teacher_id)
            
            return {
                'success': True,
                'data': stats
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取文件统计失败: {str(e)}',
                'data': None
            }
    
    def cleanup_orphaned_files(self, teacher_id: int) -> Dict[str, Any]:
        """清理孤立的文件"""
        try:
            deleted_count = self.file_model.cleanup_orphaned_files(teacher_id)
            
            return {
                'success': True,
                'message': f'清理完成，删除了 {deleted_count} 个孤立文件',
                'data': {'deleted_count': deleted_count}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'清理文件失败: {str(e)}',
                'data': None
            }
