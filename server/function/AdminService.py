"""
管理员服务模块
处理管理员相关的业务逻辑
"""
import sqlite3
import hashlib
import os
import logging
from datetime import datetime
from functools import wraps
from flask import session, redirect, url_for, flash, request
from utils.response_handler import ResponseHandler, StatusCode

# 配置日志
logger = logging.getLogger(__name__)

class AdminService:
    def __init__(self):
        # 数据库路径
        self.DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'game.db')
        self._setup_logging()
        
    def _setup_logging(self):
        """设置日志配置"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
    def get_db_connection(self):
        """创建数据库连接"""
        try:
            conn = sqlite3.connect(self.DB_PATH)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def encrypt_password(self, password):
        """使用MD5加密密码"""
        if not password:
            raise ValueError("密码不能为空")
        return hashlib.md5(password.encode('utf-8')).hexdigest()

    def login(self, username, password):
        """管理员登录"""
        logger.info(f"尝试登录用户: {username}")
        try:
            if not username or not password:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="用户名和密码不能为空"
                )
                
            # 验证用户名和密码
            result = self.verify_user(username, password)
            
            if result['code'] == 0:
                # 设置session
                session['is_admin'] = True
                session['user_id'] = result['data']['id']
                session['username'] = result['data']['username']
                session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                session['login_ip'] = request.remote_addr
                
                logger.info(f"用户 {username} 登录成功")
                return ResponseHandler.success(
                    data=result['data'],
                    msg="登录成功"
                )
            else:
                logger.warning(f"用户 {username} 登录失败: {result['msg']}")
                return result
                
        except Exception as e:
            logger.error(f"登录过程发生错误: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.LOGIN_FAILED,
                msg=f"登录失败: {str(e)}"
            )

    def logout(self):
        """管理员登出"""
        try:
            username = session.get('username')
            logger.info(f"用户 {username} 正在登出")
            
            # 清除session
            session.pop('is_admin', None)
            session.pop('user_id', None)
            session.pop('username', None)
            session.pop('login_time', None)
            session.pop('login_ip', None)
            
            logger.info(f"用户 {username} 登出成功")
            return ResponseHandler.success(msg="登出成功")
        except Exception as e:
            logger.error(f"登出过程发生错误: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"登出失败: {str(e)}"
            )

    def admin_required(self, f):
        """管理员认证装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('is_admin'):
                logger.warning(f"未授权访问: {request.path}")
                return ResponseHandler.error(
                    code=StatusCode.UNAUTHORIZED,
                    msg="需要管理员权限"
                )
            return f(*args, **kwargs)
        return decorated_function

    def verify_user(self, username, password):
        """验证用户登录"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 获取用户信息，包括密码字段
            cursor.execute('''
                SELECT id, username, password, created_at
                FROM users 
                WHERE username = ?
            ''', (username,))

            user = cursor.fetchone()
            
            if not user:
                logger.warning(f"用户不存在: {username}")
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="用户不存在"
                )
                            
            if user['password'] == self.encrypt_password(password):
                logger.info(f"用户验证成功: {username}")
                return ResponseHandler.success(
                    data={
                        "id": user['id'],
                        "username": user['username'],
                        "created_at": user['created_at']
                    },
                    msg="验证成功"
                )
            else:
                logger.warning(f"密码错误: {username}")
                return ResponseHandler.error(
                    code=StatusCode.LOGIN_FAILED,
                    msg="用户名或密码错误"
                )

        except sqlite3.Error as e:
            logger.error(f"数据库操作失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.DB_QUERY_ERROR,
                msg=f"数据库查询失败: {str(e)}"
            )
        except Exception as e:
            logger.error(f"验证用户失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"验证用户失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def get_users(self):
        """获取所有用户"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, username, created_at FROM users')
            users = [dict(row) for row in cursor.fetchall()]
            return ResponseHandler.success(data=users, msg="获取成功")
        except Exception as e:
            print(f"获取用户列表失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取用户列表失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def add_user(self, data):
        """添加新用户"""
        conn = None
        try:
            # 验证必要字段
            if not data.get('username') or not data.get('password'):
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="用户名和密码不能为空"
                )

            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 检查用户名是否已存在
            cursor.execute('SELECT id FROM users WHERE username = ?', (data['username'],))
            if cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.USER_EXISTS,
                    msg="用户名已存在"
                )

            # 对密码进行MD5加密
            encrypted_password = self.encrypt_password(data['password'])

            cursor.execute('''
                INSERT INTO users (username, password, created_at)
                VALUES (?, ?, datetime('now'))
            ''', (data['username'], encrypted_password))

            user_id = cursor.lastrowid
            conn.commit()

            return ResponseHandler.success(
                data={"id": user_id},
                msg="添加成功"
            )
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"添加用户失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"添加用户失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def get_user(self, user_id):
        """获取指定用户"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()

            if user is None:
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="用户不存在"
                )

            return ResponseHandler.success(
                data=dict(user),
                msg="获取成功"
            )
        except Exception as e:
            print(f"获取用户信息失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取用户信息失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def update_user(self, user_id, data):
        """更新用户信息"""
        conn = None
        try:
            # 验证必要字段
            if not data.get('username'):
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="用户名不能为空"
                )

            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 检查用户是否存在
            cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="用户不存在"
                )

            # 检查新用户名是否与其他用户冲突
            cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', 
                         (data['username'], user_id))
            if cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.USER_EXISTS,
                    msg="用户名已存在"
                )

            if data.get('password'):
                # 如果更新包含密码，进行MD5加密
                encrypted_password = self.encrypt_password(data['password'])
                cursor.execute('''
                    UPDATE users 
                    SET username = ?, password = ?
                    WHERE id = ?
                ''', (data['username'], encrypted_password, user_id))
            else:
                cursor.execute('''
                    UPDATE users 
                    SET username = ?
                    WHERE id = ?
                ''', (data['username'], user_id))

            conn.commit()
            return ResponseHandler.success(msg="更新成功")
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"更新用户信息失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"更新用户信息失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def delete_user(self, user_id):
        """删除用户"""
        conn = None
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 检查用户是否存在
            cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="用户不存在"
                )

            # 删除用户
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()

            return ResponseHandler.success(msg="删除成功")
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"删除用户失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"删除用户失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

admin_service = AdminService()
