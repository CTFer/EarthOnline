import sqlite3
import time
import json
import os
from flask import session, request
import hashlib
import requests
from config.config import PROD_SERVER, ENV,Roadmap_SYNC_TIME

class RoadmapService:
    def __init__(self):
        self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                'database',
                'roadmap.db'
            )
        # 上次同步时间
        self.last_sync_time = 0
    # 

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
        try:
            # 检查API密钥
            api_key = request.headers.get('X-API-Key')
            if api_key and api_key == PROD_SERVER['API_KEY']:
                print("[Roadmap] API key authentication successful")
                # API密钥验证通过，返回默认用户信息
                return json.dumps({
                    'code': 1,  # 1 表示已登录
                    'msg': 'API密钥验证通过',
                    'data': {
                        'username': 'emanon',
                        'user_id': 1  # 默认用户ID
                    }
                })
            
            # 检查session登录
            if not session.get('username'):
                print("[Roadmap] Session authentication failed")
                return json.dumps({
                    'code': 0,  # 0 表示未登录
                    'msg': '未登录',
                    'data': None
                })
            
            print(f"[Roadmap] Session authentication successful for user: {session.get('username')}")
            return json.dumps({
                'code': 1,  # 1 表示已登录
                'msg': '已登录',
                'data': {
                    'username': session.get('username'),
                    'user_id': session.get('user_id')
                }
            })
        except Exception as e:
            print(f"[Roadmap] Login check error: {str(e)}")
            return json.dumps({
                'code': 0,
                'msg': f'登录检查失败: {str(e)}',
                'data': None
            })

    def sync_from_prod(self):
        """从生产环境同步数据到本地
        
        同步流程：
        1. 环境检查：确保只在本地环境运行
        2. 准备同步：构建请求头，包含API密钥和上次同步时间
        3. 获取数据：从生产环境获取增量更新数据
        4. 处理数据：将获取的数据更新到本地数据库
        5. 更新时间：记录本次同步时间
        
        同步规则：
        - 根据edittime判断数据是否需要更新
        - is_deleted标记用于处理已删除的记录
        - 使用事务确保数据一致性
        
        返回格式：
        {
            'code': 0/500,  # 0表示成功，其他表示失败
            'msg': '处理结果说明',
            'data': [] # 同步的数据列表
        }
        """
        # 初始化数据库连接为 None
        conn = None
        
        # 1. 环境检查
        if ENV != 'local':
            print("[Sync] 只能在本地环境同步数据")
            return json.dumps({
                'code': 400,
                'msg': '只能在本地环境同步数据',
                'data': None
            })

        try:
            print("[Sync] 开始从生产环境同步数据...")
            
            # 2. 准备同步请求
            headers = {
                'X-API-Key': PROD_SERVER['API_KEY'],
                'X-Sync-Time': str(self.last_sync_time)
            }
            
            # 3. 从生产环境获取数据
            sync_url = f"{PROD_SERVER['URL']}/api/roadmap/sync"
            print(f"[Sync] Requesting updates since: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_sync_time))}")
            print(f"[Sync] Target URL: {sync_url}")
            
            response = requests.get(sync_url, headers=headers, timeout=PROD_SERVER['TIMEOUT'])
            
            if response.status_code != 200:
                print(f"[Sync] Failed to get data from production: {response.text}")
                return json.dumps({
                    'code': 500,
                    'msg': f'同步失败: {response.text}',
                    'data': None
                })
            
            updates = response.json()
            if not updates.get('data'):
                print("[Sync] 没有新的更新")
                return json.dumps({
                    'code': 0,
                    'msg': '没有新的更新',
                    'data': None
                })

            print(f"[Sync] Received {len(updates['data'])} updates")
            
            # 4. 处理数据更新
            conn = self.get_db()
            cursor = conn.cursor()
            
            update_count = 0
            delete_count = 0
            
            for item in updates['data']:
                # 检查记录是否存在
                cursor.execute('SELECT id FROM roadmap WHERE id = ?', (item['id'],))
                exists = cursor.fetchone()
                
                # 确保user_id有值
                user_id = item.get('user_id')
                if not user_id:
                    # 如果没有user_id，使用默认用户ID(比如系统用户)
                    user_id = 1  # 假设1是系统用户ID
                    print(f"[Sync] 记录 {item['id']} 没有user_id，使用默认值: {user_id}")
                
                if exists:
                    # 更新现有记录
                    cursor.execute('''
                        UPDATE roadmap 
                        SET name = ?, 
                            description = ?, 
                            status = ?, 
                            color = ?,
                            addtime = ?,
                            edittime = ?,
                            "order" = ?,
                            user_id = ?,
                            is_deleted = ?
                        WHERE id = ?
                    ''', (
                        item['name'],
                        item['description'],
                        item['status'],
                        item.get('color', '#ffffff'),  # 使用默认颜色
                        item['addtime'],
                        item['edittime'],
                        item.get('order', 0),  # 使用默认顺序
                        user_id,
                        item.get('is_deleted', 0),
                        item['id']
                    ))
                else:
                    # 插入新记录
                    cursor.execute('''
                        INSERT INTO roadmap (
                            id, name, description, status, color,
                            addtime, edittime, "order", user_id, is_deleted
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item['id'],
                        item['name'],
                        item['description'],
                        item['status'],
                        item.get('color', '#ffffff'),  # 使用默认颜色
                        item['addtime'],
                        item['edittime'],
                        item.get('order', 0),  # 使用默认顺序
                        user_id,
                        item.get('is_deleted', 0)
                    ))
                
                if item['is_deleted']:
                    delete_count += 1
                else:
                    update_count += 1
            
            # 提交事务
            conn.commit()
            
            # 5. 更新同步时间
            self.last_sync_time = int(time.time())
            
            print(f"[Sync] 同步完成: {update_count} 更新, {delete_count} 删除")
            return json.dumps({
                'code': 0,
                'msg': f'同步成功: {update_count} 更新, {delete_count} 删除',
                'data': updates['data']
            })
            
        except Exception as e:
            print(f"[Sync] Error during sync: {str(e)}")
            if conn:
                conn.rollback()
            return json.dumps({
                'code': 500,
                'msg': f'同步过程出错: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()
    
    def sync_data(self):
        """提供数据同步接口（仅在生产环境可用）"""
        if ENV != 'prod':
            return json.dumps({
                'code': 403,
                'msg': '只能在生产环境提供同步数据',
                'data': None
            })

        try:
            # 验证API密钥
            api_key = request.headers.get('X-API-Key')
            if not api_key or api_key != PROD_SERVER['API_KEY']:
                return json.dumps({
                    'code': 401,
                    'msg': 'API密钥无效',
                    'data': None
                })

            # 获取上次同步时间
            last_sync_time = int(request.headers.get('X-Sync-Time', 0))
            
            # 获取数据库连接
            conn = self.get_db()
            cursor = conn.cursor()
            
            try:
                # 获取所有更新的数据
                cursor.execute('''
                    SELECT r.*, 
                        CASE 
                            WHEN r.edittime > ? THEN 0 
                            ELSE 1 
                        END as is_deleted,
                        COALESCE(r.user_id, 1) as user_id  -- 确保user_id有值
                    FROM roadmap r
                    WHERE r.edittime > ?
                    ORDER BY r.edittime ASC
                ''', (last_sync_time, last_sync_time))
                
                # 转换结果为字典列表
                columns = [col[0] for col in cursor.description]
                updates = []
                for row in cursor.fetchall():
                    item = dict(zip(columns, row))
                    # 确保所有必需字段都有值
                    item['color'] = item.get('color', '#ffffff')
                    item['order'] = item.get('order', 0)
                    item['is_deleted'] = item.get('is_deleted', 0)
                    updates.append(item)
                
                return json.dumps({
                    'code': 0,
                    'msg': '获取成功',
                    'data': updates
                })
                
            finally:
                cursor.close()
                conn.close()
                
        except Exception as e:
            print(f"[Sync] Error providing sync data: {str(e)}")
            return json.dumps({
                'code': 500,
                'msg': f'获取同步数据失败: {str(e)}',
                'data': None
            })

    def auto_sync(self):
        """自动同步函数
        
        在以下情况下触发同步：
        1. 本地环境
        2. 距离上次同步超过5分钟
        """
        if ENV == 'local' and time.time() - self.last_sync_time > Roadmap_SYNC_TIME:  # 5分钟同步一次
            print("[Sync] 自动同步触发")
            return self.sync_from_prod()
        return None

    def get_roadmap(self):
        """获取所有未删除的开发计划"""
        # 在获取数据前先尝试同步
        if ENV == 'local':
            self.auto_sync()
        
        login_result = json.loads(self.check_login())
        if login_result['code'] == 0:
            return login_result
        
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 计算一年前的时间戳
            one_year_ago = int(time.time()) - (365 * 24 * 60 * 60)
            # 只获取未删除的记录
            cursor.execute('''
                SELECT * FROM roadmap 
                WHERE is_deleted = 0  AND edittime > ? AND user_id = ?
                ORDER BY "order" ASC, edittime DESC
            ''', (one_year_ago,session.get('user_id')))
            
            roadmaps = [dict(row) for row in cursor.fetchall()]
            return json.dumps({
                'code': 0,
                'msg': '获取成功',
                'data': roadmaps
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
                0,
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
        """软删除开发计划"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 标记为已删除而不是真正删除
            cursor.execute('''
                UPDATE roadmap 
                SET is_deleted = 1, 
                    edittime = ? 
                WHERE id = ?
            ''', (int(time.time()), roadmap_id))
            
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