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
                user_data = result['data']
                # 检查是否是管理员
                if not user_data.get('isadmin'):
                    return ResponseHandler.error(
                        code=StatusCode.UNAUTHORIZED,
                        msg="该用户不是管理员"
                    )
                
                # 设置session
                session['is_admin'] = True
                session['user_id'] = user_data['id']
                session['username'] = user_data['username']
                session['nickname'] = user_data.get('nickname')
                session['login_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                session['login_ip'] = request.remote_addr
                
                logger.info(f"用户 {username} 登录成功")
                return ResponseHandler.success(
                    data=user_data,
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

            # 获取用户信息，包括所有字段
            cursor.execute('''
                SELECT id, username, password, created_at, isadmin, nickname, wechat_userid
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
                    data=dict(user),
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
            cursor.execute('''
                SELECT id, username, created_at, isadmin, nickname, wechat_userid 
                FROM users
            ''')
            users = [dict(row) for row in cursor.fetchall()]
            return ResponseHandler.success(data=users, msg="获取成功")
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
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

            # 插入新用户
            cursor.execute('''
                INSERT INTO users (
                    username, password, created_at, isadmin, nickname, wechat_userid
                ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
            ''', (
                data['username'],
                encrypted_password,
                data.get('isadmin', 0),
                data.get('nickname'),
                data.get('wechat_userid')
            ))

            user_id = cursor.lastrowid
            conn.commit()

            return ResponseHandler.success(
                data={"id": user_id},
                msg="添加成功"
            )
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"添加用户失败: {str(e)}")
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
            cursor.execute('''
                SELECT id, username, created_at, isadmin, nickname, wechat_userid 
                FROM users 
                WHERE id = ?
            ''', (user_id,))
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
            logger.error(f"获取用户信息失败: {str(e)}")
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
            if data.get('username'):
                cursor.execute('SELECT id FROM users WHERE username = ? AND id != ?', 
                             (data['username'], user_id))
                if cursor.fetchone():
                    return ResponseHandler.error(
                        code=StatusCode.USER_EXISTS,
                        msg="用户名已存在"
                    )

            # 构建更新语句
            update_fields = []
            params = []
            
            if data.get('username'):
                update_fields.append('username = ?')
                params.append(data['username'])
            
            if data.get('password'):
                update_fields.append('password = ?')
                params.append(self.encrypt_password(data['password']))
            
            if 'isadmin' in data:
                update_fields.append('isadmin = ?')
                params.append(data['isadmin'])
            
            if 'nickname' in data:
                update_fields.append('nickname = ?')
                params.append(data['nickname'])
            
            if 'wechat_userid' in data:
                update_fields.append('wechat_userid = ?')
                params.append(data['wechat_userid'])

            if not update_fields:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="没有需要更新的字段"
                )

            # 添加WHERE条件的参数
            params.append(user_id)
            
            # 执行更新
            cursor.execute(f'''
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE id = ?
            ''', params)

            conn.commit()
            return ResponseHandler.success(msg="更新成功")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"更新用户信息失败: {str(e)}")
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
            cursor.execute('SELECT isadmin FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            
            if not user:
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="用户不存在"
                )
                
            # 检查是否是管理员
            if user['isadmin']:
                return ResponseHandler.error(
                    code=StatusCode.OPERATION_FAILED,
                    msg="不能删除管理员用户"
                )

            # 删除用户
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()

            return ResponseHandler.success(msg="删除成功")
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"删除用户失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"删除用户失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

admin_service = AdminService()
