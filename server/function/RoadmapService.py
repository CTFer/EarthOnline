import sqlite3
import time
import json
import os
from flask import session
import hashlib

class RoadmapService:
    def __init__(self):
        self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'database',
                'roadmap.db'
            )
    def encrypt_password(self, password):
        """使用MD5加密密码"""
        return hashlib.md5(password.encode('utf-8')).hexdigest()
    def get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def roadmap_login(self, data):
        """
        用户登录
        :param data: 登录数据
        :return: 登录结果
        """
        try:
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return json.dumps({'code': 1, 'msg': '用户名和密码不能为空'})
            
            # 从数据库获取用户信息
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user WHERE username = ?', (username,))
            user = cursor.fetchone()
            
            # 验证密码
            if user and user['password'] == self.encrypt_password(password):
                # 登录成功，设置session
                session['user_id'] = user['id']
                session['username'] = user['username']
                
                return json.dumps({
                    'code': 0,
                    'msg': '登录成功',
                    'data': {
                        'username': user['username'],
                        'user_id': user['id']
                    }
                })
            else:
                return json.dumps({'code': 1, 'msg': '用户名或密码错误'})
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            return json.dumps({'code': 1, 'msg': '登录失败'})
        finally:
            if conn:
                conn.close()

    def roadmap_logout(self):
        """开发计划登出"""
        session.clear()
        return json.dumps({
            'code': 0,
            'msg': '登出成功',
            'data': None
        })

    # 以下的方法需要登录后才能使用
    def check_login(self):
        """检查是否登录"""
        if not session.get('username'):
            return json.dumps({
                'code': 0,
                'msg': '未登录',
                'data': None
            })
        else:
            return json.dumps({
                'code': 1,
                'msg': '已登录',
                'data': {
                    'username': session.get('username'),
                    'user_id': session.get('user_id')
                }
            })

    def get_roadmap(self):
        """获取所有开发计划"""
        login_result = json.loads(self.check_login())
        if login_result['code'] == 0:
            return login_result
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 计算一年前的时间戳
            one_year_ago = int(time.time()) - (365 * 24 * 60 * 60)
            
            cursor.execute('''
                SELECT * FROM roadmap 
                WHERE user_id = ? 
                AND edittime > ?
                ORDER BY "order" ASC
            ''', (session.get('user_id'), one_year_ago))
            
            tasks = [dict(row) for row in cursor.fetchall()]
            
            return json.dumps({
                'code': 0,
                'msg': '获取成功',
                'data': tasks
            })
            
        except Exception as e:
            print(f"获取开发计划失败: {str(e)}")
            return json.dumps({
                'code': 500,
                'msg': f'获取失败: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()

    def add_roadmap(self, data):
        """添加开发计划"""
        try:
            login_result = json.loads(self.check_login())
            if login_result['code'] == 0:
                return login_result
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 获取当前最大order值
            cursor.execute('SELECT MAX("order") FROM roadmap')
            max_order = cursor.fetchone()[0] or 0
            
            current_time = int(time.time())
            
            cursor.execute('''
                INSERT INTO roadmap (
                    name, description, status, color, 
                    addtime, edittime, "order", user_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('description'),
                data.get('status', 'PLANNED'),
                data.get('color', '#ffffff'),
                current_time,
                current_time,
                max_order + 1,
                session.get('user_id')
            ))
            
            conn.commit()
            
            return json.dumps({
                'code': 0,
                'msg': '添加成功',
                'data': cursor.lastrowid
            })
            
        except Exception as e:
            print(f"添加开发计划失败: {str(e)}")
            if conn:
                conn.rollback()
            return json.dumps({
                'code': 500,
                'msg': f'添加失败: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()

    def update_roadmap(self, roadmap_id, data):
        """更新开发计划"""
        try:
            login_result = json.loads(self.check_login())
            if login_result['code'] == 0:
                return login_result
            conn = self.get_db()
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            # 构建更新字段
            update_fields = []
            params = []
            
            if 'name' in data:
                update_fields.append('name = ?')
                params.append(data['name'])
            if 'description' in data:
                update_fields.append('description = ?')
                params.append(data['description'])
            if 'status' in data:
                update_fields.append('status = ?')
                params.append(data['status'])
            if 'color' in data:
                update_fields.append('color = ?')
                params.append(data['color'])
            if 'order' in data:
                update_fields.append('"order" = ?')
                params.append(data['order'])
                
            update_fields.append('edittime = ?')
            params.append(current_time)
            
            # 添加ID到参数列表
            params.append(roadmap_id)
            
            query = f'''
                UPDATE roadmap 
                SET {', '.join(update_fields)}
                WHERE id = ?
            '''
            
            cursor.execute(query, params)
            conn.commit()
            
            return json.dumps({
                'code': 0,
                'msg': '更新成功',
                'data': None
            })
            
        except Exception as e:
            print(f"更新开发计划失败: {str(e)}")
            if conn:
                conn.rollback()
            return json.dumps({
                'code': 500,
                'msg': f'更新失败: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()

    def delete_roadmap(self, roadmap_id):
        """删除开发计划"""
        try:
            login_result = json.loads(self.check_login())
            if login_result['code'] == 0:
                return login_result
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM roadmap WHERE id = ? AND user_id = ?', (roadmap_id, session.get('user_id')))
            conn.commit()
            
            return json.dumps({
                'code': 0,
                'msg': '删除成功',
                'data': None
            })
            
        except Exception as e:
            print(f"删除开发计划失败: {str(e)}")
            if conn:
                conn.rollback()
            return json.dumps({
                'code': 500,
                'msg': f'删除失败: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()

roadmap_service = RoadmapService()