# -*- coding: utf-8 -*-
"""
教师用户模型
"""
import hashlib
from typing import Optional, List, Dict, Any
from .base import BaseModel

class TeacherUser(BaseModel):
    """教师用户模型类"""
    
    def __init__(self, db_path: str = None):
        super().__init__(db_path)
        self.table_name = "teacher_user"
    
    def create_user(self, username: str, password: str, name: str, phone: str = None, **kwargs) -> int:
        """创建教师用户"""
        # 密码加密
        encrypted_password = hashlib.md5(password.encode()).hexdigest()
        
        data = {
            'username': username,
            'password': encrypted_password,
            'name': name,
            **kwargs
        }
        
        if phone:
            data['phone'] = phone
        
        return self.insert(self.table_name, data)
    
    def get_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """根据手机号获取用户"""
        query = f"SELECT * FROM {self.table_name} WHERE phone = ?"
        results = self.execute_query(query, (phone,))
        return results[0] if results else None
    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        query = f"SELECT * FROM {self.table_name} WHERE username = ?"
        results = self.execute_query(query, (username,))
        return results[0] if results else None
    
    def get_by_username_or_phone(self, username_or_phone: str) -> Optional[Dict[str, Any]]:
        """根据用户名或手机号获取用户"""
        query = f"SELECT * FROM {self.table_name} WHERE username = ? OR phone = ?"
        results = self.execute_query(query, (username_or_phone, username_or_phone))
        return results[0] if results else None
    
    def verify_password(self, username_or_phone: str, password: str) -> bool:
        """验证密码（支持用户名或手机号）"""
        user = self.get_by_username_or_phone(username_or_phone)
        if not user:
            return False
        
        encrypted_password = hashlib.md5(password.encode()).hexdigest()
        return user['password'] == encrypted_password
    
    def update_password(self, user_id: int, new_password: str) -> int:
        """更新密码"""
        encrypted_password = hashlib.md5(new_password.encode()).hexdigest()
        return self.update_by_id(self.table_name, user_id, {'password': encrypted_password})
    
    def update_last_login(self, user_id: int) -> int:
        """更新最后登录时间"""
        from datetime import datetime
        return self.update_by_id(self.table_name, user_id, {
            'last_login': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    
    def get_active_users(self) -> List[Dict[str, Any]]:
        """获取所有活跃用户"""
        return self.get_all(self.table_name, "status = 1")
    
    def deactivate_user(self, user_id: int) -> int:
        """停用用户"""
        return self.update_by_id(self.table_name, user_id, {'status': 0})
    
    def activate_user(self, user_id: int) -> int:
        """激活用户"""
        return self.update_by_id(self.table_name, user_id, {'status': 1})
    
    def update_profile(self, user_id: int, profile_data: Dict[str, Any]) -> int:
        """更新用户资料"""
        # 移除不允许直接更新的字段
        restricted_fields = ['id', 'phone', 'password', 'create_time']
        filtered_data = {k: v for k, v in profile_data.items() if k not in restricted_fields}
        
        return self.update_by_id(self.table_name, user_id, filtered_data)
