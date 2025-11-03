# -*- coding: utf-8 -*-
"""
认证服务
"""
from typing import Optional, Dict, Any
from ..models.user import TeacherUser
from ..models.student import TeacherStudent

class AuthService:
    """认证服务类"""
    
    def __init__(self, db_path: str = None):
        self.user_model = TeacherUser(db_path)
        self.student_model = TeacherStudent(db_path)
    
    def teacher_login(self, username: str, password: str) -> Dict[str, Any]:
        """教师登录（支持用户名或手机号）"""
        try:
            # 验证用户存在（支持用户名或手机号）
            user = self.user_model.get_by_username_or_phone(username)
            if not user:
                return {
                    'success': False,
                    'message': '用户名或手机号不存在',
                    'data': None
                }
            
            # 验证密码
            if not self.user_model.verify_password(username, password):
                return {
                    'success': False,
                    'message': '密码错误',
                    'data': None
                }
            
            # 检查用户状态
            if user['status'] != 1:
                return {
                    'success': False,
                    'message': '账户已被禁用',
                    'data': None
                }
            
            # 更新最后登录时间
            self.user_model.update_last_login(user['id'])
            
            # 返回用户信息（不包含密码）
            user_data = {k: v for k, v in user.items() if k != 'password'}
            
            return {
                'success': True,
                'message': '登录成功',
                'data': user_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'登录失败: {str(e)}',
                'data': None
            }
    
    def teacher_register(self, username: str, password: str, name: str, phone: str = None, **kwargs) -> Dict[str, Any]:
        """教师注册"""
        try:
            # 检查用户名是否已存在
            existing_user = self.user_model.get_by_username(username)
            if existing_user:
                return {
                    'success': False,
                    'message': '用户名已被注册',
                    'data': None
                }
            
            # 如果提供了手机号，检查手机号是否已存在
            if phone:
                existing_phone = self.user_model.get_by_phone(phone)
                if existing_phone:
                    return {
                        'success': False,
                        'message': '手机号已被注册',
                        'data': None
                    }
            
            # 创建新用户
            user_id = self.user_model.create_user(username, password, name, phone, **kwargs)
            
            return {
                'success': True,
                'message': '注册成功',
                'data': {'user_id': user_id}
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'注册失败: {str(e)}',
                'data': None
            }
    
    def reset_password(self, username_or_phone: str, new_password: str) -> Dict[str, Any]:
        """重置密码（支持用户名或手机号）"""
        try:
            user = self.user_model.get_by_username_or_phone(username_or_phone)
            if not user:
                return {
                    'success': False,
                    'message': '用户不存在',
                    'data': None
                }
            
            # 更新密码
            self.user_model.update_password(user['id'], new_password)
            
            return {
                'success': True,
                'message': '密码重置成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'密码重置失败: {str(e)}',
                'data': None
            }
    
    def student_verify(self, class_code: str, student_name: str) -> Dict[str, Any]:
        """学生验证（班级代码+姓名）"""
        try:
            student = self.student_model.verify_student(class_code, student_name)
            if not student:
                return {
                    'success': False,
                    'message': '班级ID或姓名错误',
                    'data': None
                }
            
            # 返回学生信息
            return {
                'success': True,
                'message': '验证成功',
                'data': student
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'验证失败: {str(e)}',
                'data': None
            }
    
    def get_teacher_info(self, teacher_id: int) -> Dict[str, Any]:
        """获取教师信息"""
        try:
            teacher = self.user_model.get_by_id(teacher_id)
            if not teacher:
                return {
                    'success': False,
                    'message': '教师不存在',
                    'data': None
                }
            
            # 移除敏感信息
            teacher_data = {k: v for k, v in teacher.items() if k not in ['password']}
            
            return {
                'success': True,
                'message': '获取成功',
                'data': teacher_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'获取失败: {str(e)}',
                'data': None
            }
    
    def update_teacher_profile(self, teacher_id: int, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新教师资料"""
        try:
            # 移除不允许更新的字段
            restricted_fields = ['id', 'phone', 'password', 'create_time', 'last_login']
            filtered_data = {k: v for k, v in profile_data.items() if k not in restricted_fields}
            
            if not filtered_data:
                return {
                    'success': False,
                    'message': '没有可更新的数据',
                    'data': None
                }
            
            # 更新资料
            self.user_model.update_profile(teacher_id, filtered_data)
            
            return {
                'success': True,
                'message': '更新成功',
                'data': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'更新失败: {str(e)}',
                'data': None
            }
