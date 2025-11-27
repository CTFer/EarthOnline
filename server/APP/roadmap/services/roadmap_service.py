# -*- coding: utf-8 -*-
"""
Roadmap服务模块
提供计划管理相关的服务功能
"""
import sqlite3
import time
import json
import os
from flask import session, request
import hashlib
import requests
# 从主应用导入配置
from config.config import PROD_SERVER, ENV, Roadmap_SYNC_TIME

class RoadmapService:
    def __init__(self):
        # 调整数据库路径，使其相对于当前文件
        self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
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
                session.clear()  # 清除旧的session
                session['user_id'] = user['id']
                session['username'] = user['username']
                session.permanent = True  # 设置session为永久性
                session.modified = True   # 确保session被保存
                
                print(f"[Roadmap] 登录成功 - 设置用户: {username} (ID: {user['id']}) 的 session")
                print(f"[Roadmap] 当前 session: {dict(session)}")  # 打印当前session内容
                
                return json.dumps({
                    'code': 0,
                    'msg': '登录成功',
                    'data': {
                        'username': user['username'],
                        'user_id': user['id']
                    }
                })
            else:
                print(f"[Roadmap] 登录失败 - 用户: {username} 的凭证无效")
                return json.dumps({'code': 1, 'msg': '用户名或密码错误'})
                
        except Exception as e:
            print(f"[Roadmap] 登录失败: {str(e)}")
            return json.dumps({'code': 1, 'msg': f'登录失败: {str(e)}'})
        finally:
            if 'conn' in locals():
                conn.close()

    def roadmap_logout(self):
        """开发计划登出"""
        try:
            username = session.get('username')
            print(f"[Roadmap] 登出用户: {username}")
            session.clear()
            return json.dumps({
                'code': 0,
                'msg': '登出成功',
                'data': None
            })
        except Exception as e:
            print(f"[Roadmap] 登出失败: {str(e)}")
            return json.dumps({
                'code': 1,
                'msg': f'登出失败: {str(e)}',
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
                    'code': 0,  # 修改为0，表示成功
                    'msg': 'API密钥验证通过',
                    'data': {
                        'username': 'emanon',
                        'user_id': 1  # 默认用户ID
                    }
                })
            
            # 检查session登录
            user_id = session.get('user_id')
            username = session.get('username')
            
            print(f"[Roadmap] 检查 session - user_id: {user_id}, username: {username}")
            print(f"[Roadmap] 当前 session 数据: {dict(session)}")
            
            if not username or not user_id:
                print("[Roadmap] 会话认证失败 - 缺少 user_id 或 username")
                return json.dumps({
                    'code': 1,  # 1 表示未登录
                    'msg': '未登录',
                    'data': None
                })
            
            print(f"[Roadmap] 会话认证成功 - 用户: {username}")
            return json.dumps({
                'code': 0,  # 修改为0，表示成功
                'msg': '已登录',
                'data': {
                    'username': username,
                    'user_id': user_id
                }
            })
        except Exception as e:
            print(f"[Roadmap] 登录检查失败: {str(e)}")
            return json.dumps({
                'code': 1,
                'msg': f'登录检查失败: {str(e)}',
                'data': None
            })

    def sync_from_prod(self):
        """从生产环境同步数据到本地，并将本地独有数据同步到生产环境
        
        同步策略：
        1. 获取本地和生产环境的数据
        2. 比较edittime时间戳
        3. 本地较新的同步到生产环境
        4. 生产环境较新的同步到本地
        """
        conn = None
        try:
            print("[Sync] 开始双向增量同步...")
            
            # 准备同步请求头
            headers = {
                **PROD_SERVER['HEADERS'],  # 使用配置的标准头
                'X-API-Key': PROD_SERVER['API_KEY'],
                'X-Sync-Time': str(self.last_sync_time)
            }
            
            # 1. 从生产环境获取增量更新
            sync_url = f"{PROD_SERVER['URL']}/api/roadmap/sync"
            print(f"[Sync] 从生产环境获取增量更新 - 上次同步时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_sync_time))}")
            
            # 添加SSL验证配置
            ssl_config = {
                'verify': PROD_SERVER['SSL_VERIFY'],
                'timeout': PROD_SERVER['TIMEOUT']
            }
            
            response = requests.get(sync_url, headers=headers, **ssl_config)
            if response.status_code != 200:
                raise Exception(f"获取生产环境数据失败: HTTP {response.status_code}")
            
            prod_updates = response.json().get('data', [])
            print(f"[Sync] 收到 {len(prod_updates)} 条生产环境更新")
            
            # 2. 获取数据库连接
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 3. 处理从生产环境获取的更新
            stats = {'from_prod': 0, 'to_prod': 0}
            
            for item in prod_updates:
                cursor.execute('SELECT edittime FROM roadmap WHERE id = ?', (item['id'],))
                local_record = cursor.fetchone()
                
                if not local_record or local_record['edittime'] < item['edittime']:
                    # 更新本地记录
                    if local_record:
                        cursor.execute('''
                            UPDATE roadmap 
                            SET name = ?, description = ?, status = ?, 
                                color = ?, addtime = ?, edittime = ?,
                                "order" = ?, user_id = ?, is_deleted = ?
                            WHERE id = ?
                        ''', (
                            item['name'], item['description'], item['status'],
                            item.get('color', '#ffffff'), item['addtime'], item['edittime'],
                            item.get('order', 0), item.get('user_id', 1), item.get('is_deleted', 0),
                            item['id']
                        ))
                        print(f"[Sync] 更新本地记录 {item['id']}: 生产环境时间 {item['edittime']} > 本地时间 {local_record['edittime']}")
                    else:
                        cursor.execute('''
                            INSERT INTO roadmap (id, name, description, status, color,
                                addtime, edittime, "order", user_id, is_deleted)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            item['id'], item['name'], item['description'], item['status'],
                            item.get('color', '#ffffff'), item['addtime'], item['edittime'],
                            item.get('order', 0), item.get('user_id', 1), item.get('is_deleted', 0)
                        ))
                        print(f"[Sync] 插入新记录 {item['id']}")
                    stats['from_prod'] += 1
            
            # 4. 获取本地需要同步到生产环境的更新
            cursor.execute('''
                SELECT * FROM roadmap 
                WHERE edittime > ?
                ORDER BY edittime ASC
            ''', (self.last_sync_time,))
            
            local_updates = []
            for row in cursor.fetchall():
                item = dict(row)
                # 如果这条记录不在生产环境的更新列表中
                if not any(p['id'] == item['id'] and p['edittime'] >= item['edittime'] for p in prod_updates):
                    local_updates.append(item)
            
            # 5. 将本地更新同步到生产环境
            if local_updates:
                print(f"[Sync] 发现 {len(local_updates)} 条本地更新需要同步到生产环境")
                
                sync_url = f"{PROD_SERVER['URL']}/api/roadmap/batch_sync"
                response = requests.post(
                    sync_url,
                    headers=headers,
                    json={'updates': local_updates},
                    **ssl_config
                )
                
                if response.status_code != 200:
                    raise Exception(f"同步到生产环境失败: HTTP {response.status_code}")
                    
                result = response.json()
                if result.get('code') == 0:
                    stats['to_prod'] = len(local_updates)
                    print(f"[Sync] 成功同步 {stats['to_prod']} 条记录到生产环境")
                else:
                    raise Exception(f"同步到生产环境失败: {result.get('msg')}")
            
            # 6. 提交事务并更新同步时间
            conn.commit()
            self.last_sync_time = int(time.time())
            
            print(f"[Sync] 双向增量同步完成:")
            print(f"从生产环境同步: {stats['from_prod']} 条")
            print(f"同步到生产环境: {stats['to_prod']} 条")
            
            return json.dumps({
                'code': 0,
                'msg': '双向增量同步成功',
                'data': {
                    'stats': stats,
                    'from_prod': prod_updates,
                    'to_prod': local_updates
                }
            })
            
        except Exception as e:
            print(f"[Sync] 同步失败: {str(e)}")
            if conn:
                conn.rollback()
            return json.dumps({
                'code': 500,
                'msg': f'同步失败: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()

    def sync_data(self):
        """提供数据同步接口（仅在生产环境可用）"""
        conn = None
        # 记录请求信息，用于调试
        print("\n[Sync] ==== 收到同步请求 ====")
        print(f"[Sync] 远程地址: {request.remote_addr}")
        print(f"[Sync] 请求方法: {request.method}")
        print(f"[Sync] 请求路径: {request.path}")
        print(f"[Sync] 请求头: {dict(request.headers)}")
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
                print(f"[Sync] API密钥验证失败: 收到 {api_key}, 期望 {PROD_SERVER['API_KEY']}")
                return json.dumps({
                    'code': 401,
                    'msg': 'API密钥无效',
                    'data': None
                })

            # 获取上次同步时间
            last_sync_time = int(request.headers.get('X-Sync-Time', 0))
            print(f"[Sync] 收到同步请求，上次同步时间: {last_sync_time}")
            
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
        conn = None
        if ENV == 'local':
            sync_result = self.auto_sync()
            print(f"[Roadmap] 同步结果: {sync_result}")
        
        # 检查登录状态
        login_result = json.loads(self.check_login())
        print(f"[Roadmap] 登录检查结果: {login_result}")
        
        if login_result['code'] != 0:  # 修改为检查code不等于0
            print("[Roadmap] 用户未登录，返回登录检查结果")
            return json.dumps(login_result)
        
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 计算一年前的时间戳
            one_year_ago = int(time.time()) - (365 * 24 * 60 * 60)
            
            # 获取用户ID（从登录结果中获取）
            user_id = login_result['data']['user_id']
            print(f"[Roadmap] 获取用户 {user_id} 的开发计划")
            
            # 只获取未删除的记录
            cursor.execute('''
                SELECT * FROM roadmap 
                WHERE is_deleted = 0 AND edittime > ? AND user_id = ?
                ORDER BY "order" ASC, edittime DESC
            ''', (one_year_ago, user_id))
            
            roadmaps = [dict(row) for row in cursor.fetchall()]
            print(f"[Roadmap] 获取到 {len(roadmaps)} 条记录")
            
            return json.dumps({
                'code': 0,
                'msg': '获取成功',
                'data': roadmaps
            })
        except Exception as e:
            print(f"[Roadmap] 获取开发计划失败: {str(e)}")
            return json.dumps({
                'code': 1,
                'msg': f'获取失败: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()

    def add_roadmap(self, data):
        """添加开发计划"""
        conn = None
        try:
            # 检查登录状态
            login_result = json.loads(self.check_login())
            if login_result['code'] != 0:  # 修改判断条件
                print("[Roadmap] 用户未登录")
                return login_result
            
            # 获取数据库连接
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 获取当前最大order值
            cursor.execute('SELECT MAX("order") FROM roadmap')
            max_order = cursor.fetchone()[0] or 0
            
            current_time = int(time.time())
            
            # 获取用户ID（从登录结果中获取）
            user_id = login_result['data']['user_id']
            print(f"[Roadmap] 添加开发计划 - 用户: {user_id}")
            
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
                user_id
            ))
            
            new_id = cursor.lastrowid
            conn.commit()
            
            print(f"[Roadmap] 添加成功 - ID: {new_id}")
            return json.dumps({
                'code': 0,
                'msg': '添加成功',
                'data': new_id
            })
            
        except Exception as e:
            print(f"[Roadmap] 添加开发计划失败: {str(e)}")
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
        conn = None
        try:
            # 检查登录状态
            login_result = json.loads(self.check_login())
            if login_result['code'] != 0:  # 修改判断条件
                print("[Roadmap] 用户未登录")
                return login_result
            
            # 获取数据库连接
            conn = self.get_db()
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            # 构建更新字段
            update_fields = []
            params = []
            
            # 处理各个字段的更新
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
                print(f"[Roadmap] Updating order to: {data['order']}")
                update_fields.append('"order" = ?')
                params.append(int(data['order']))  # 确保order是整数
                
            # 添加更新时间
            update_fields.append('edittime = ?')
            params.append(current_time)
            
            # 添加ID到参数列表
            params.append(roadmap_id)
            
            # 构建并执行更新查询
            query = f'''
                UPDATE roadmap 
                SET {', '.join(update_fields)}
                WHERE id = ?
            '''
            
            print(f"[Roadmap] Executing update query: {query}")
            print(f"[Roadmap] Query parameters: {params}")
            
            cursor.execute(query, params)
            
            if cursor.rowcount == 0:
                print(f"[Roadmap] No rows updated for ID: {roadmap_id}")
                return json.dumps({
                    'code': 404,
                    'msg': '任务不存在或无权限更新',
                    'data': None
                })
            
            conn.commit()
            print(f"[Roadmap] Successfully updated task {roadmap_id}")
            
            return json.dumps({
                'code': 0,
                'msg': '更新成功',
                'data': None
            })
            
        except Exception as e:
            print(f"[Roadmap] Error updating task: {str(e)}")
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

    def batch_sync(self, updates):
        """处理批量同步请求（仅在生产环境可用）
        
        Args:
            updates: 要同步的数据列表
        """
        if ENV != 'prod':
            return json.dumps({
                'code': 403,
                'msg': '只能在生产环境使用批量同步',
                'data': None
            })
        
        conn = None
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            updated_count = 0
            for item in updates:
                # 检查记录是否存在并比较时间戳
                cursor.execute('SELECT edittime FROM roadmap WHERE id = ?', (item['id'],))
                existing = cursor.fetchone()
                
                if existing and existing['edittime'] >= item['edittime']:
                    print(f"[Sync] 跳过记录 {item['id']}: 本地时间 {existing['edittime']} >= 同步时间 {item['edittime']}")
                    continue
                
                if existing:
                    cursor.execute('''
                        UPDATE roadmap 
                        SET name = ?, description = ?, status = ?, 
                            color = ?, addtime = ?, edittime = ?,
                            "order" = ?, user_id = ?, is_deleted = ?
                        WHERE id = ?
                    ''', (
                        item['name'], item['description'], item['status'],
                        item.get('color', '#ffffff'), item['addtime'], item['edittime'],
                        item.get('order', 0), item.get('user_id', 1), item.get('is_deleted', 0),
                        item['id']
                    ))
                    print(f"[Sync] 更新记录 {item['id']}")
                else:
                    cursor.execute('''
                        INSERT INTO roadmap (id, name, description, status, color,
                            addtime, edittime, "order", user_id, is_deleted)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item['id'], item['name'], item['description'], item['status'],
                        item.get('color', '#ffffff'), item['addtime'], item['edittime'],
                        item.get('order', 0), item.get('user_id', 1), item.get('is_deleted', 0)
                    ))
                    print(f"[Sync] 插入新记录 {item['id']}")
                
                updated_count += 1
            
            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': '批量同步成功',
                'data': {'updated': updated_count}
            })
            
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[Sync] 批量同步失败: {str(e)}")
            return json.dumps({
                'code': 500,
                'msg': f'批量同步失败: {str(e)}',
                'data': None
            })
        finally:
            if conn:
                conn.close()

# 创建服务实例
roadmap_service = RoadmapService()