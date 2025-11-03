# -*- coding: utf-8 -*-
"""
教师系统配置文件
"""
import os

class TeacherConfig:
    """教师系统配置类"""
    
    # 数据库配置
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'teacher.db')
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024  # 200MB
    ALLOWED_EXTENSIONS = {
        'video': ['mp4', 'avi', 'mov', 'wmv', 'flv'],
        'audio': ['mp3', 'wav', 'm4a', 'aac', 'ogg'],
        'document': ['pdf', 'doc', 'docx', 'txt', 'rtf']
    }
    
    # 文件大小限制
    MAX_FILE_SIZES = {
        'video': 200 * 1024 * 1024,  # 200MB
        'audio': 50 * 1024 * 1024,   # 50MB
        'document': 20 * 1024 * 1024  # 20MB
    }
    
    # 安全配置
    SECRET_KEY = 'teacher-system-secret-key-2025'
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # 分页配置
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    
    # 通知配置
    NOTIFICATION_TYPES = {
        'deadline_reminder': '作业即将到期',
        'deadline_today': '作业今日到期',
        'low_completion': '完成率较低',
        'new_material': '新作业发布',
        'system_notice': '系统通知'
    }
    
    # 材料类型配置
    MATERIAL_TYPES = {
        'video': '视频',
        'audio': '音频',
        'document': '文档'
    }
    
    # 难度等级配置
    DIFFICULTY_LEVELS = {
        'beginner': '初级',
        'intermediate': '中级',
        'advanced': '高级'
    }
    
    # 年龄段配置
    AGE_GROUPS = {
        'preschool': '学前班',
        'elementary': '小学',
        'middle': '中学',
        'high': '高中',
        'adult': '成人'
    }
    
    # 课程类型配置
    COURSE_TYPES = {
        'online': '线上课程',
        'offline': '线下课程',
        'hybrid': '混合课程'
    }
    
    # 活动类型配置
    ACTIVITY_TYPES = {
        'lecture': '讲座',
        'workshop': '工作坊',
        'seminar': '研讨会',
        'demo': '演示课',
        'other': '其他'
    }
    
    # 文件存储配置
    STORAGE_CONFIG = {
        'local': {
            'enabled': True,
            'path': UPLOAD_FOLDER
        },
        'oss': {
            'enabled': False,
            'access_key': '',
            'secret_key': '',
            'bucket': '',
            'endpoint': ''
        }
    }
    
    # 缓存配置
    CACHE_CONFIG = {
        'enabled': True,
        'type': 'memory',  # memory, redis
        'ttl': 3600  # 1小时
    }
    
    # 日志配置
    LOG_CONFIG = {
        'level': 'INFO',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': os.path.join(os.path.dirname(__file__), '..', 'logs', 'teacher.log'),
        'max_size': 10 * 1024 * 1024,  # 10MB
        'backup_count': 5
    }
    
    # 邮件配置
    EMAIL_CONFIG = {
        'enabled': False,
        'smtp_server': '',
        'smtp_port': 587,
        'username': '',
        'password': '',
        'from_email': ''
    }
    
    # 短信配置
    SMS_CONFIG = {
        'enabled': False,
        'provider': '',  # aliyun, tencent
        'access_key': '',
        'secret_key': '',
        'sign_name': ''
    }
    
    @classmethod
    def get_upload_path(cls, file_type: str) -> str:
        """获取文件上传路径"""
        type_folder = os.path.join(cls.UPLOAD_FOLDER, file_type)
        os.makedirs(type_folder, exist_ok=True)
        return type_folder
    
    @classmethod
    def get_file_url(cls, file_path: str) -> str:
        """生成文件访问URL"""
        relative_path = os.path.relpath(file_path, cls.UPLOAD_FOLDER)
        return f"/teacher/static/uploads/{relative_path.replace(os.sep, '/')}"
    
    @classmethod
    def validate_file_type(cls, filename: str) -> str:
        """验证文件类型"""
        extension = os.path.splitext(filename)[1].lower()
        
        for file_type, extensions in cls.ALLOWED_EXTENSIONS.items():
            if extension in extensions:
                return file_type
        
        return None
    
    @classmethod
    def get_max_file_size(cls, file_type: str) -> int:
        """获取文件大小限制"""
        return cls.MAX_FILE_SIZES.get(file_type, 20 * 1024 * 1024)
