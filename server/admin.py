from flask import Blueprint, request, render_template, session, redirect, url_for, flash, current_app, jsonify
from functools import wraps
import sqlite3
import os
from api import api_registry
import json
import hashlib  # 添加到文件顶部的导入
from datetime import datetime
import time
from function.PlayerService import player_service
from flask_socketio import SocketIO
from config import ENV
if ENV == 'local':
    from function.NFC_Device import NFC_Device
from function.admin_service import admin_service
import threading
from function.NotificationService import notification_service

# 创建蓝图
admin_bp = Blueprint('admin', __name__)
socketio = SocketIO()
nfc_device = None

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')

# 添加密码加密函数


def encrypt_password(password):
    """使用MD5加密密码"""
    return hashlib.md5(password.encode('utf-8')).hexdigest()

# 管理员认证装饰器


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# 路由处理
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 获取用户信息，包括密码字段
            cursor.execute('''
                SELECT id, username, password, created_at 
                FROM users 
                WHERE username = ?
            ''', (username,))

            user = cursor.fetchone()
            # 调试日志
            print(
                f"Login attempt - User: {username}, Found user: {dict(user) if user else None}")

            if user and user['password'] == encrypt_password(password):
                session['is_admin'] = True
                session['user_id'] = user['id']  # 保存用户ID到session
                session['username'] = user['username']  # 保存用户名到session
                print(f"Login successful for user: {username}")  # 调试日志
                return redirect(url_for('admin.index'))
            else:
                print(f"Login failed for user: {username}")  # 调试日志
                flash('用户名或密码错误')

        except Exception as e:
            print(f"Login error: {str(e)}")
            flash('登录过程中发生错误')
        finally:
            conn.close()

    return render_template('admin_login.html')


@admin_bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_required
def index():
    return render_template('admin.html')


@admin_bp.route('/api/players', methods=['GET'])
def get_players():
    """获取所有玩家"""
    return player_service.get_players()


@admin_bp.route('/api/players/<int:player_id>', methods=['POST'])
@admin_required
def update_player(player_id):
    """更新玩家信息"""
    data = request.get_json()
    return player_service.update_player(player_id, data)


@admin_bp.route('/api/players/<int:player_id>', methods=['DELETE'])
@admin_required
def delete_player(player_id):
    """删除玩家"""
    return player_service.delete_player(player_id)


@admin_bp.route('/api/players/<int:player_id>', methods=['GET'])
@admin_required
def get_player(player_id):
    """获得单个玩家信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM player_data WHERE player_id = ?', (player_id,))
        player = cursor.fetchone()

        if player is None:
            return json.dumps({'error': 'User not found'}), 404

        return json.dumps(dict(player))
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/addplayer', methods=['POST'])
@admin_required
def add_player():
    """添加新玩家"""
    data = request.get_json()
    return player_service.add_player(data)


# API路由


@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """获取所有用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at FROM users')
        users = [dict(row) for row in cursor.fetchall()]
        return json.dumps({"data": users})
    except Exception as e:
        print(f"Error in get_users: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/adduser', methods=['POST'])
@admin_required
def add_user():
    """添加新用户"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        # 对密码进行MD5加密
        encrypted_password = encrypt_password(data['password'])

        cursor.execute('''
            INSERT INTO users (username, password, created_at)
            VALUES (?, ?, datetime('now'))
        ''', (data['username'], encrypted_password))

        user_id = cursor.lastrowid
        conn.commit()

        return json.dumps({"id": user_id}), 201
    except Exception as e:
        print(f"Error in add_user: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """获取指定用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()

        if user is None:
            return json.dumps({'error': 'User not found'}), 404

        return json.dumps(dict(user))
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """更新用户信息"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        if data.get('password'):
            # 如果更新包含密码，进行MD5加密
            encrypted_password = encrypt_password(data['password'])
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
        return json.dumps({"success": True})
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()


        # 删除用户
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))

        conn.commit()
        return json.dumps({"success": True})
    except Exception as e:
        print(f"Error in delete_user: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/skills', methods=['GET'])
@admin_required
def get_skills():
    """获取所有技能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, proficiency, description FROM skills')
        skills = [dict(row) for row in cursor.fetchall()]
        return json.dumps({"data": skills})
    except Exception as e:
        print(f"Error in get_skills: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/skills', methods=['POST'])
@admin_required
def add_skill():
    """添加新技能"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO skills (name, proficiency, description)
            VALUES (?, ?, ?)
        ''', (data['name'], data['proficiency'], data.get('description', '')))

        skill_id = cursor.lastrowid
        conn.commit()

        return json.dumps({"id": skill_id}), 201
    except Exception as e:
        print(f"Error in add_skill: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/skills/<int:skill_id>', methods=['GET'])
@admin_required
def get_skill(skill_id):
    """获取指定技能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, name, proficiency, description FROM skills WHERE id = ?', (skill_id,))
        skill = cursor.fetchone()

        if skill is None:
            return json.dumps({'error': 'Skill not found'}), 404

        return json.dumps(dict(skill))
    except Exception as e:
        print(f"Error in get_skill: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/skills/<int:skill_id>', methods=['PUT'])
@admin_required
def update_skill(skill_id):
    """更新技能"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE skills 
            SET name = ?, proficiency = ?, description = ?
            WHERE id = ?
        ''', (data['name'], data['proficiency'], data.get('description', ''), skill_id))

        conn.commit()
        return json.dumps({"success": True})
    except Exception as e:
        print(f"Error in update_skill: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/skills/<int:skill_id>', methods=['DELETE'])
@admin_required
def delete_skill(skill_id):
    """删除技能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 首先删除相关的技能关系
        cursor.execute('DELETE FROM skill_relations WHERE parent_skill_id = ? OR child_skill_id = ?',
                       (skill_id, skill_id))

        # 然后删除技能
        cursor.execute('DELETE FROM skills WHERE id = ?', (skill_id,))

        conn.commit()
        return json.dumps({"success": True})
    except Exception as e:
        print(f"Error in delete_skill: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()


@admin_bp.route('/api/tasks', methods=['GET'])
@admin_required
def get_tasks():
    """获取任务列表，支持分页"""
    try:
        # 获取分页参数
        page = request.args.get('page', type=int)
        limit = request.args.get('limit', type=int)
        
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取总记录数
        cursor.execute("SELECT COUNT(*) as total FROM task")
        total = cursor.fetchone()['total']

        # 构建基础查询
        base_query = '''
            SELECT id, name, description, task_type, task_status, 
                   task_chain_id, parent_task_id, task_scope, stamina_cost,
                   limit_time, repeat_time, is_enabled, repeatable, task_rewards
            FROM task
        '''

        # 根据是否有分页参数决定查询方式
        if page is not None and limit is not None:
            offset = (page - 1) * limit
            query = base_query + ' LIMIT ? OFFSET ?'
            cursor.execute(query, (limit, offset))
        else:
            cursor.execute(base_query)

        tasks = []
        for row in cursor.fetchall():
            task = dict(row)
            # 处理task_rewards JSON字符串
            if task['task_rewards'] and isinstance(task['task_rewards'], str):
                try:
                    task['task_rewards'] = json.loads(task['task_rewards'])
                except json.JSONDecodeError:
                    task['task_rewards'] = {}
            
            tasks.append(task)

        response_data = {
            "code": 0,
            "msg": "",
            "count": total,
            "data": tasks
        }
        return json.dumps(response_data)

    except Exception as e:
        print(f"获取任务列表出错: {str(e)}")
        return json.dumps({
            "code": 1,
            "msg": f"获取任务列表失败: {str(e)}",
            "count": 0,
            "data": []
        }), 500
    finally:
        if conn:
            conn.close()

@admin_bp.route('/api/tasks/<int:task_id>', methods=['GET'])
@admin_required
def get_task(task_id):
    """获取单个任务信息"""
    conn = None
    try:
        print("开始获取任务列表...")  # 调试日志
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 获取表结构
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"表中所有字段: {columns}")  # 调试日志

        # 获取所有任务
        query = f'''
            SELECT {", ".join(columns)}
            FROM task
            where id={task_id}
            ORDER BY id

        '''
        print(f"执行SQL: {query}")  # 调试日志
        cursor.execute(query)

        # 转换为字典列表
        tasks = []
        task=dict(cursor.fetchone())
        # 确保所有字段都存在，设置默认值
        for column in columns:
            if column not in task or task[column] is None:
                if column in ['is_enabled', 'repeatable']:
                    task[column] = False
                elif column in ['points', 'stamina_cost', 'limit_time','repeat_time',
                                'completion_count', 'task_chain_id','parent_task_id']:
                    task[column] = 0
                elif column == 'task_rewards':
                    task[column] = {}
                elif column == 'task_status':
                    task[column] = 'INACTIVE'
                else:
                    task[column] = None
        # 类型转换
        task['is_enabled'] = bool(task['is_enabled'])
        task['repeatable'] = bool(task['repeatable'])
        # 解析 task_rewards JSON 字符串
        if task['task_rewards'] and isinstance(task['task_rewards'], str):
            try:
                task['task_rewards'] = json.loads(task['task_rewards'])
            except json.JSONDecodeError:
                task['task_rewards'] = {}
        elif task['task_rewards'] is None:
            task['task_rewards'] = {}


        response_data = {
            "code": 0,
            "msg": "获取任务成功",
            "data": task
        }
        print(response_data)
        return json.dumps(response_data)

    except Exception as e:
        print(f"获取任务列表出错: {str(e)}")  # 错误日志
        return json.dumps({
            "code": 1,
            "msg": f"获取任务列表失败: {str(e)}",
            "data": []
        }), 500
    finally:
        if conn:
            conn.close()

# 添加任务状态常量
TASK_STATUS = {
    'LOCKED': '未解锁',
    'AVAIL': '可接受',
    'ACCEPT': '已接受',
    'COMPLETED': '已完成'
}

@admin_bp.route('/api/tasks', methods=['POST'])
@admin_required
def add_task():
    """添加新任务"""
    try:
        data = request.get_json()
        print(f"Received task data: {data}")  # 调试日志
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 处理任务奖励数据
        task_rewards = {
            'points_rewards': [],
            'card_rewards': [],
            'medal_rewards': [],
            'real_rewards': []
        }

        # 处理数值奖励（经验值和积分）
        if 'points_rewards' in data.get('task_rewards', {}):
            task_rewards['points_rewards'] = [
                {
                    'type': reward.get('type', 'exp'),
                    'number': int(reward.get('number', 0))
                }
                for reward in data['task_rewards']['points_rewards']
                if reward.get('number') is not None
            ]

        # 处理卡片奖励
        if 'card_rewards' in data.get('task_rewards', {}):
            task_rewards['card_rewards'] = [
                {
                    'id': int(reward.get('id', 0)),
                    'number': int(reward.get('number', 0))
                }
                for reward in data['task_rewards']['card_rewards']
                if reward.get('id') is not None and reward.get('number') is not None
            ]

        # 处理成就奖励
        if 'medal_rewards' in data.get('task_rewards', {}):
            task_rewards['medal_rewards'] = [
                {
                    'id': int(reward.get('id', 0)),
                    'number': 1  # 成就奖励默认数量为1
                }
                for reward in data['task_rewards']['medal_rewards']
                if reward.get('id') is not None
            ]

        # 处理实物奖励
        if 'real_rewards' in data.get('task_rewards', {}):
            task_rewards['real_rewards'] = [
                {
                    'name': reward.get('name', ''),
                    'number': int(reward.get('number', 0))
                }
                for reward in data['task_rewards']['real_rewards']
                if reward.get('name') and reward.get('number') is not None
            ]

        cursor.execute('''
            INSERT INTO tasks (
                name, description, task_chain_id, parent_task_id,
                task_type, task_status, task_scope, stamina_cost,
                limit_time, repeat_time, is_enabled, repeatable,
                need_check, task_rewards, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (
            data['name'],
            data.get('description', ''),
            int(data.get('task_chain_id', 0)),
            int(data.get('parent_task_id', 0)),
            data['task_type'],
            data.get('task_status', 'LOCKED'),  # 默认状态为未解锁
            int(data.get('task_scope', 0)),
            int(data.get('stamina_cost', 0)),
            int(data.get('limit_time', 0)),
            int(data.get('repeat_time', 1)),
            int(data.get('is_enabled', 0)),
            int(data.get('repeatable', 0)),
            int(data.get('need_check', 0)),
            json.dumps(task_rewards)
        ))

        task_id = cursor.lastrowid
        conn.commit()

        return json.dumps({
            "code": 0,
            "msg": "添加任务成功",
            "data": {"id": task_id}
        })

    except Exception as e:
        print(f"添加任务出错: {str(e)}")  # 错误日志
        return json.dumps({
            "code": 500,
            "msg": f"添加任务失败: {str(e)}",
            "data": None
        }), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@admin_required
def update_task(task_id):
    """更新任务"""
    try:
        data = request.get_json()
        print(f"Updating task {task_id} with data: {data}")  # 调试日志
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 处理任务奖励数据（与添加任务相同的逻辑）
        task_rewards = {
            'points_rewards': [],
            'card_rewards': [],
            'medal_rewards': [],
            'real_rewards': []
        }

        # 处理各类奖励（与添加任务相同的逻辑）
        if 'task_rewards' in data:
            if 'points_rewards' in data['task_rewards']:
                task_rewards['points_rewards'] = [
                    {
                        'type': reward.get('type', 'exp'),
                        'number': int(reward.get('number', 0))
                    }
                    for reward in data['task_rewards']['points_rewards']
                ]

            if 'card_rewards' in data['task_rewards']:
                task_rewards['card_rewards'] = [
                    {
                        'id': int(reward.get('id', 0)),
                        'number': int(reward.get('number', 0))
                    }
                    for reward in data['task_rewards']['card_rewards']
                ]

            if 'medal_rewards' in data['task_rewards']:
                task_rewards['medal_rewards'] = [
                    {
                        'id': int(reward.get('id', 0)),
                        'number': 1  # 成就奖励默认数量为1
                    }
                    for reward in data['task_rewards']['medal_rewards']
                ]

            if 'real_rewards' in data['task_rewards']:
                task_rewards['real_rewards'] = [
                    {
                        'name': reward.get('name', ''),
                        'number': int(reward.get('number', 0))
                    }
                    for reward in data['task_rewards']['real_rewards']
                ]

        cursor.execute('''
            UPDATE task 
            SET name = ?, 
                description = ?, 
                task_chain_id = ?,
                parent_task_id = ?,
                task_type = ?,
                task_status = ?,
                task_scope = ?,
                stamina_cost = ?,
                limit_time = ?,
                repeat_time = ?,
                is_enabled = ?,
                repeatable = ?,
                need_check = ?,
                task_rewards = ?
            WHERE id = ?
        ''', (
            data['name'],
            data.get('description', ''),
            int(data.get('task_chain_id', 0)),
            int(data.get('parent_task_id', 0)),
            data['task_type'],
            data.get('task_status', 'LOCKED'),  # 保持一致的默认状态
            int(data.get('task_scope', 0)),
            int(data.get('stamina_cost', 0)),
            int(data.get('limit_time', 0)),
            int(data.get('repeat_time', 1)),
            int(data.get('is_enabled', 0)),
            int(data.get('repeatable', 0)),
            int(data.get('need_check', 0)),
            json.dumps(task_rewards),
            task_id
        ))

        conn.commit()

        # 获取更新后的任务数据
        cursor.execute('SELECT * FROM task WHERE id = ?', (task_id,))
        updated_task = cursor.fetchone()

        return json.dumps({
            "code": 0,
            "msg": "更新任务成功",
            "data": dict(updated_task) if updated_task else None
        })

    except Exception as e:
        print(f"更新任务出错: {str(e)}")  # 错误日志
        return json.dumps({
            "code": 500,
            "msg": f"更新任务失败: {str(e)}",
            "data": None
        }), 500
    finally:
        if conn:
            conn.close()


@admin_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@admin_required
def delete_task(task_id):
    """删除任务"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM task WHERE id = ?', (task_id,))
        conn.commit()
        return json.dumps({"success": True})
    except Exception as e:
        print(f"Error in delete_task: {str(e)}")
        return json.dumps({'error': str(e)}), 500
    finally:
        conn.close()

# 添加API文档路由


@admin_bp.route('/api/docs', methods=['GET'])
@admin_required
def get_api_docs():
    """获取API文档"""
    try:
        endpoints = api_registry.get_all_endpoints()
        return json.dumps({
            "data": [
                {
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "description": endpoint.description,
                    "auth_required": endpoint.auth_required,
                    "parameters": endpoint.parameters,
                    "response": endpoint.response
                }
                for endpoint in endpoints
            ]
        })
    except Exception as e:
        print(f"Error in get_api_docs: {str(e)}")
        return json.dumps({'error': str(e)}), 500

# 添加任务管理页面路由


@admin_bp.route('/tasks')
@admin_required
def task_manage():
    """任务管理页面"""
    return render_template('task_manage.html')

# 任务管理页面路由


@admin_bp.route('/player_tasks')
@admin_required
def player_task_manage():
    """用户任务管理页面"""
    return render_template('player_task_manage.html')

# Player Task API路由


@admin_bp.route('/api/player_tasks', methods=['GET'])
@admin_required
def get_player_tasks():
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        # 计算偏移量
        offset = (page - 1) * limit

        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取总数
        cursor.execute('SELECT COUNT(*) FROM player_task')
        total = cursor.fetchone()[0]

        # 获取分页数据
        cursor.execute('''
            SELECT 
                pt.id,
                pt.player_id,
                pt.task_id,
                t.name as task_name,
                pt.starttime,
                pt.endtime,

                pt.status,
                pt.complete_time,
                pt.comment
            FROM player_task pt 
            LEFT JOIN task t ON pt.task_id = t.id 
            ORDER BY pt.id DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row[0],
                'player_id': row[1],
                'task_id': row[2],
                'task_name': row[3],
                'starttime': row[4],
                'endtime': row[5],

                'status': row[6],
                'complete_time': row[7],
                'comment': row[8]
            })

        conn.close()

        return json.dumps({
            'code': 0,
            'msg': '',
            'count': total,
            'data': tasks
        })

    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'count': 0,
            'data': []
        }), 500


@admin_bp.route('/api/player_tasks/<int:task_id>', methods=['GET'])
@admin_required
def get_player_task(task_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 明确指定字段顺序
        cursor.execute('''
            SELECT 
                pt.id,
                pt.player_id,
                pt.task_id,
                t.name as task_name,
                pt.starttime,
                pt.endtime,

                pt.status,
                pt.complete_time,
                pt.comment
            FROM player_task pt 
            LEFT JOIN task t ON pt.task_id = t.id 
            WHERE pt.id = ?
        ''', (task_id,))

        row = cursor.fetchone()
        if row is None:
            return json.dumps({
                'code': 404,
                'msg': '任务不存在',
                'data': None
            }), 404

        # 使用字典构造确保字段顺序
        task = {
            'id': row[0],
            'player_id': row[1],
            'task_id': row[2],
            'task_name': row[3],
            'starttime': row[4],
            'endtime': row[5],

            'status': row[6],
            'complete_time': row[7],
            'comment': row[8]
        }

        conn.close()
        return json.dumps({
            'code': 0,
            'msg': '',
            'data': task
        })

    except Exception as e:
        print("Get task error:", str(e))
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500


@admin_bp.route('/api/player_tasks', methods=['POST'])
@admin_required
def create_player_task():
    try:
        data = request.get_json()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO player_task (
                player_id, task_id, starttime, endtime,
                status, complete_time, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('player_id'),
            data.get('task_id'),
            data.get('starttime', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('endtime'),
            data.get('status', 'available'),
            data.get('complete_time'),
            data.get('comment')
        ))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return json.dumps({
            'code': 0,
            'msg': '创建成功',
            'data': {'id': task_id}
        }), 201

    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500


@admin_bp.route('/api/player_tasks/<int:task_id>', methods=['PUT'])
@admin_required
def update_player_task(task_id):
    try:
        data = request.get_json()
        print("Received update data:", data)  # 调试日志

        conn = get_db_connection()
        cursor = conn.cursor()

        # 明确指定更新字段的顺序
        update_query = '''
            UPDATE player_task
            SET player_id = ?,
                task_id = ?,
                starttime = ?,
                endtime = ?,
                status = ?,
                complete_time = ?,
                comment = ?
            WHERE id = ?
        '''

        # 确保参数顺序与SQL字段顺序一致
        params = (
            data.get('player_id'),
            data.get('task_id'),
            data.get('starttime'),
            data.get('endtime'),
            data.get('status'),
            data.get('complete_time'),
            data.get('comment'),
            task_id
        )

        print("Update params:", params)  # 调试日志
        cursor.execute(update_query, params)

        if cursor.rowcount == 0:
            conn.close()
            return json.dumps({
                'code': 404,
                'msg': '未找到要更新的记录',
                'data': None
            }), 404

        conn.commit()

        # 获取更新后的数据，使用相同的字段顺序
        cursor.execute('''
            SELECT 
                pt.id,
                pt.player_id,
                pt.task_id,
                t.name as task_name,
                pt.starttime,
                pt.endtime,
                pt.status,
                pt.complete_time,
                pt.comment
            FROM player_task pt 
            LEFT JOIN task t ON pt.task_id = t.id 
            WHERE pt.id = ?
        ''', (task_id,))

        row = cursor.fetchone()
        print("Updated row:", row[9])
        updated_data = {
            'id': row[0],
            'player_id': row[1],
            'task_id': row[2],
            'task_name': row[3],
            'starttime': row[4],
            'endtime': row[5],
            'status': row[6],
            'complete_time': row[7],
            'comment': row[8]
        }

        conn.close()
        print("Updated data:", updated_data)
        return json.dumps({
            'code': 0,
            'msg': '更新成功',
            'data': updated_data
        })

    except Exception as e:
        print("Update error:", str(e))  # 错误日志
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500


@admin_bp.route('/api/player_tasks/<int:task_id>', methods=['DELETE'])
@admin_required
def delete_player_task(task_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM player_task WHERE id=?', (task_id,))
        conn.commit()
        conn.close()
        print(f"Deleted task with id: {task_id}")
        return json.dumps({
            'code': 0,
            'msg': '删除成功',
            'data': None
        })

    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

# 勋章管理API路由
@admin_bp.route('/api/medals', methods=['GET'])
@admin_required
def get_medals():
    try:
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)

        # 计算偏移量
        offset = (page - 1) * limit

        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取总数
        cursor.execute('SELECT COUNT(*) FROM medals')
        total = cursor.fetchone()[0]

        # 获取分页数据
        cursor.execute('''
            SELECT 
                id,
                name,
                description,
                addtime,
                icon,
                conditions
            FROM medals 
            ORDER BY id DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))

        medals = []
        for row in cursor.fetchall():
            medals.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'addtime': row[3],
                'icon': row[4],
                'conditions': row[5]
            })

        conn.close()

        return json.dumps({
            'code': 0,
            'msg': '',
            'count': total,
            'data': medals
        })

    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'count': 0,
            'data': []
        }), 500

@admin_bp.route('/api/medals/<int:medal_id>', methods=['GET'])
@admin_required
def get_medal(medal_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT 
                id,
                name,
                description,
                addtime,
                icon,
                conditions
            FROM medals 
            WHERE id = ?
        ''', (medal_id,))

        row = cursor.fetchone()
        if row is None:
            return json.dumps({
                'code': 404,
                'msg': '勋章不存在',
                'data': None
            }), 404

        medal = {
            'id': row[0],
            'name': row[1],
            'description': row[2],
            'addtime': row[3],
            'icon': row[4],
            'conditions': row[5]
        }

        conn.close()
        return json.dumps({
            'code': 0,
            'msg': '',
            'data': medal
        })

    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

@admin_bp.route('/api/medals', methods=['POST'])
@admin_required
def create_medal():
    try:
        data = request.get_json()
        current_time = int(time.time())

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO medals (
                name, description, addtime, icon, conditions
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('name'),
            data.get('description'),
            current_time,
            data.get('icon'),
            data.get('conditions')
        ))

        medal_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return json.dumps({
            'code': 0,
            'msg': '创建成功',
            'data': {'id': medal_id}
        }), 201

    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

@admin_bp.route('/api/medals/<int:medal_id>', methods=['PUT'])
@admin_required
def update_medal(medal_id):
    try:
        data = request.get_json()
        print(f"Received medal update data: {data}")  # 添加调试信息

        conn = get_db_connection()
        cursor = conn.cursor()

        # 先获取当前数据
        cursor.execute('SELECT * FROM medals WHERE id = ?', (medal_id,))
        current_medal = cursor.fetchone()
        print(f"Current medal data: {dict(current_medal) if current_medal else None}")  # 添加调试信息

        update_data = {
            'name': data.get('name'),
            'description': data.get('description'),
            'icon': data.get('icon'),
            'conditions': data.get('conditions')
        }
        print(f"Update data to be applied: {update_data}")  # 添加调试信息

        cursor.execute('''
            UPDATE medals
            SET name = ?,
                description = ?,
                icon = ?,
                conditions = ?
            WHERE id = ?
        ''', (
            update_data['name'],
            update_data['description'],
            update_data['icon'],
            update_data['conditions'],
            medal_id
        ))

        if cursor.rowcount == 0:
            print(f"No rows updated for medal_id: {medal_id}")  # 添加调试信息
            conn.close()
            return json.dumps({
                'code': 404,
                'msg': '未找到要更新的勋章',
                'data': None
            }), 404

        conn.commit()
        
        # 获取更新后的数据
        cursor.execute('SELECT * FROM medals WHERE id = ?', (medal_id,))
        updated_medal = cursor.fetchone()
        print(f"Updated medal data: {dict(updated_medal)}")  # 添加调试信息
        
        conn.close()

        return json.dumps({
            'code': 0,
            'msg': '更新成功',
            'data': dict(updated_medal) if updated_medal else None
        })

    except Exception as e:
        print(f"Error updating medal: {str(e)}")  # 添加调试信息
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

@admin_bp.route('/api/medals/<int:medal_id>', methods=['DELETE'])
@admin_required
def delete_medal(medal_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM medals WHERE id = ?', (medal_id,))
        conn.commit()
        conn.close()

        return json.dumps({
            'code': 0,
            'msg': '删除成功',
            'data': None
        })

    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

# NFC卡管理相关路由
@admin_bp.route('/api/nfc/cards', methods=['GET'])
@admin_required
def get_nfc_cards():
    try:
        print("[NFC] 获取NFC卡片列表")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最大的card_id
        cursor.execute('SELECT MAX(card_id) FROM NFC_card')
        max_id = cursor.fetchone()[0] or 0
        print(f"[NFC] 当前最大card_id: {max_id}")
        
        # 获取所有卡片数据
        cursor.execute('''
            SELECT 
                card_id, type, id, value, addtime,
                status, description, device
            FROM NFC_card
            ORDER BY addtime DESC
        ''')
        
        cards = []
        for row in cursor.fetchall():
            card = {
                'card_id': row[0],
                'type': row[1],
                'id': row[2],
                'value': row[3],
                'addtime': row[4],
                'status': row[5],
                'description': row[6],
                'device': row[7]
            }
            print(f"[NFC] 获取到卡片: {card}")
            cards.append(card)
            
        conn.close()
        print(f"[NFC] 成功获取 {len(cards)} 张卡片")
        
        return json.dumps({
            'code': 0,
            'msg': '',
            'data': {
                'cards': cards,
                'next_card_id': max_id  # 添加next_card_id字段
            }
        })
        
    except Exception as e:
        print(f"[NFC] 获取卡片列表失败: {str(e)}")
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

@admin_bp.route('/api/nfc/cards', methods=['POST'])
@admin_required
def create_nfc_card():
    try:
        data = request.get_json()
        print(f"接收到的NFC卡片创建数据: {data}")
        current_time = int(time.time())
        
        # 验证必填字段
        required_fields = ['type', 'id', 'value']
        for field in required_fields:
            if field not in data:
                print(f"缺少必填字段: {field}")
                return json.dumps({
                    'code': 400,
                    'msg': f'缺少必填字段: {field}',
                    'data': None
                }), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最大的 card_id
        cursor.execute('SELECT MAX(card_id) FROM NFC_card')
        result = cursor.fetchone()
        next_card_id = 1 if result[0] is None else result[0] + 1
        print(f"生成的新card_id: {next_card_id}")
        
        # 准备插入数据
        insert_data = {
            'card_id': next_card_id,
            'type': data['type'],
            'id': data['id'],
            'value': data['value'],
            'addtime': current_time,
            'status': 'UNLINK',
            'description': data.get('description', ''),  # 确保获取description字段
            'device': data.get('device', '')
        }
        print(f"准备插入的数据: {insert_data}")
        
        cursor.execute('''
            INSERT INTO NFC_card (
                card_id, type, id, value, addtime, 
                status, description, device
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            insert_data['card_id'],
            insert_data['type'],
            insert_data['id'],
            insert_data['value'],
            insert_data['addtime'],
            insert_data['status'],
            insert_data['description'],
            insert_data['device']
        ))
        
        conn.commit()
        
        # 验证插入是否成功
        cursor.execute('SELECT * FROM NFC_card WHERE card_id = ?', (next_card_id,))
        inserted_data = cursor.fetchone()
        print(f"插入后的数据验证: {dict(inserted_data) if inserted_data else None}")
        
        conn.close()
        
        return json.dumps({
            'code': 0,
            'msg': '创建成功',
            'data': {'card_id': next_card_id}
        }), 201
        
    except Exception as e:
        print(f"创建NFC卡片失败: {str(e)}")
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

@admin_bp.route('/api/nfc/cards/<int:card_id>', methods=['PUT'])
@admin_required
def update_nfc_card(card_id):
    try:
        data = request.get_json()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_fields = []
        params = []
        
        # 构建更新字段
        if 'status' in data:
            update_fields.append('status = ?')
            params.append(data['status'])
        if 'description' in data:
            update_fields.append('description = ?')
            params.append(data['description'])
        if 'device' in data:
            update_fields.append('device = ?')
            params.append(data['device'])
            
        if not update_fields:
            return json.dumps({
                'code': 400,
                'msg': '没有要更新的字段',
                'data': None
            }), 400
            
        params.append(card_id)
        
        cursor.execute(f'''
            UPDATE NFC_card 
            SET {', '.join(update_fields)}
            WHERE card_id = ?
        ''', params)
        
        if cursor.rowcount == 0:
            return json.dumps({
                'code': 404,
                'msg': '卡片不存在',
                'data': None
            }), 404
            
        conn.commit()
        conn.close()
        
        return json.dumps({
            'code': 0,
            'msg': '更新成功',
            'data': None
        })
        
    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

@admin_bp.route('/api/nfc/cards/<int:card_id>', methods=['DELETE'])
@admin_required
def delete_nfc_card(card_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM NFC_card WHERE card_id = ?', (card_id,))
        
        if cursor.rowcount == 0:
            return json.dumps({
                'code': 404,
                'msg': '卡片不存在',
                'data': None
            }), 404
            
        conn.commit()
        conn.close()
        
        return json.dumps({
            'code': 0,
            'msg': '删除成功',
            'data': None
        })
        
    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

# NFC硬件设备相关路由
@admin_bp.route('/api/nfc/hardware/status')
@admin_required
def get_nfc_hardware_status():
    """获取NFC硬件设备状态"""
    if ENV == 'prod':
        return json.dumps({
            'code': 0,
            'msg': 'NFC功能已关闭',
            'data': None
        })
    try:
        print("[NFC] 检查设备状态")
        nfc_device = get_nfc_device()
        
        # 自动检测设备
        is_connected = nfc_device.auto_detect_device()
        print(f"[NFC Hardware] 设备连接状态: {'已连接' if is_connected else '未连接'}")
        
        # 获取端口信息
        port_info = ""
        if is_connected and nfc_device.serial_port:
            port_info = nfc_device.serial_port.port
            print(f"[NFC Hardware] 当前使用端口: {port_info}")
        
        # 构建状态信息
        status = {
            'device_connected': is_connected,
            'port': port_info,
            'card_present': False,  # 默认无卡
            'card_id': None  # 添加card_id字段
        }
        
        # 如果设备已连接，检查卡片状态
        if is_connected:
            try:
                card_id = nfc_device.read_card_id()
                print(f"[NFC Hardware] 读取到卡片ID: {card_id}")
                if card_id and isinstance(card_id, str):  # 确保card_id是有效的字符串
                    status['card_present'] = True
                    status['card_id'] = card_id
                    print(f"[NFC Hardware] 卡片状态: 已检测到卡片 (ID: {card_id})")
                else:
                    print("[NFC Hardware] 卡片状态: 未检测到卡片")
            except Exception as e:
                print(f"[NFC Hardware] 读取卡片ID失败: {str(e)}")
                status['card_present'] = False
                status['card_id'] = None
            
        return json.dumps({
            'code': 0,
            'msg': 'success',
            'data': status
        })
        
    except Exception as e:
        print(f"[NFC Hardware] 获取设备状态失败: {str(e)}")
        return json.dumps({
            'code': 500,
            'msg': f'获取设备状态失败: {str(e)}',
            'data': None
        }), 500

@admin_bp.route('/api/nfc/hardware/read', methods=['POST'])
@admin_required
def read_nfc_hardware():
    """读取NFC实体卡片"""
    if ENV == 'prod':
        return json.dumps({
            'code': 0,
            'msg': 'NFC功能已关闭',
            'data': None
        })
    print("[NFC] 开始读取卡片数据")
    
    nfc_device = get_nfc_device()
    if nfc_device is None:
        return json.dumps({
            'code': -1,
            'msg': 'NFC设备未初始化'
        })

    try:
        # 读取卡片数据
        card_data = nfc_device.read_all_card_data()
        if not card_data:
            return json.dumps({
                'code': -1,
                'msg': '未检测到卡片或读取失败'
            })
            
        print(f"[NFC] 读取到数据: {card_data}")
        
        # 解析数据
        parsed_data = nfc_device.parse_nfc_data(card_data)
        print(f"[NFC] 解析数据: {parsed_data}")
        if not parsed_data:
            return json.dumps({
                'code': -1,
                'msg': '数据解析失败'
            })
            
        return json.dumps({
            'code': 0,
            'msg': 'success',
            'data': {
                'raw_data': card_data.upper(),
                'url': parsed_data['url'],
                'params': parsed_data['params'],
                'raw_ascii': parsed_data['ascii'],
            }
        })
        
    except Exception as e:
        print(f"[NFC] 读取错误: {str(e)}")
        return json.dumps({
            'code': -1,
            'msg': f'读卡错误: {str(e)}'
        })


def get_nfc_device():
    """获取或创建NFC设备实例"""
    global nfc_device
    
    try:
        if nfc_device is None:
            print("[NFC] 创建新的NFC设备实例")
            nfc_device = NFC_Device()
        
        # 确保设备已初始化
        if not nfc_device.initialized:
            print("[NFC] 尝试初始化设备")
            if not nfc_device.auto_detect_device():
                print("[NFC] 设备初始化失败")
                return None
        else:
            print("[NFC] 设备已初始化") 
        return nfc_device
        
    except Exception as e:
        print(f"[NFC] 获取设备实例失败: {str(e)}")
        return None

@admin_bp.route('/api/nfc/hardware/write', methods=['POST'])
@admin_required
def write_nfc_hardware():
    """写入NFC实体卡片"""
    if ENV == 'prod':
        return json.dumps({
            'code': 0,
            'msg': 'NFC功能已关闭',
            'data': None
        })
    print("[NFC] 开始写入卡片数据")
    
    nfc_device = get_nfc_device()
    if nfc_device is None:
        print("[NFC Write] 无法获取设备实例")
        return json.dumps({
            'code': -1,
            'msg': 'NFC设备未初始化'
        })

    data = request.json
    if not data or 'data' not in data:
        return json.dumps({
            'code': -1,
            'msg': '写入数据不能为空'
        })

    try:
        # 写入前检查卡片状态
        card_id = nfc_device.read_card_id()
        if not card_id:
            return json.dumps({
                'code': -1,
                'msg': '未检测到卡片'
            })

        print(f"[NFC] 写入数据: {data}")
        hex_data = nfc_device.format_ascii_to_hex(data['data'])
        
        # 写入数据
        if nfc_device._write_ntag_data(hex_data):
            print(f"[NFC] 写入成功: {hex_data}")
            
            # 写入后立即读取验证
            read_data = nfc_device.read_card_data_by_page()
            if not read_data:
                return json.dumps({
                    'code': -1,
                    'msg': '写入后验证失败：无法读取数据'
                })
                
            # 验证写入的数据
            if hex_data.rstrip('0').upper() in read_data.upper():
                return json.dumps({
                    'code': 0,
                    'msg': '写入成功',
                    'data': {
                        'hex_data': hex_data,
                        'verified': True
                    }
                })
            else:
                return json.dumps({
                    'code': -1,
                    'msg': '写入验证失败：数据不匹配'
                })
        else:
            print("[NFC] 写入失败")
            return json.dumps({
                'code': -1,
                'msg': '写入失败'
            })
    except Exception as e:
        print(f"[NFC] 写入错误: {str(e)}")
        return json.dumps({
            'code': 500,
            'msg': f'写入异常: {str(e)}',
            'data': None
        }), 500

@admin_bp.route('/api/game_cards', methods=['GET'])
@admin_required
def get_game_cards():
    """获取所有道具卡"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, description, en_name, created_at
            FROM game_card
            ORDER BY id ASC
        ''')
        
        cards = []
        for row in cursor.fetchall():
            cards.append({
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'en_name': row['en_name'],
                'created_at': row['created_at']
            })
            
        conn.close()
        return json.dumps({
            'code': 0,
            'msg': '',
            'data': cards
        })
        
    except Exception as e:
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500


@admin_bp.route('/api/nfc/next_card_id', methods=['GET'])
@admin_required
def get_next_card_id():
    """获取下一个可用的NFC卡片ID"""
    try:
        print("[NFC] 获取下一个可用卡片ID")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最大的card_id
        cursor.execute('SELECT MAX(card_id) FROM NFC_card')
        result = cursor.fetchone()
        next_id = 1 if result[0] is None else result[0] + 1
        
        print(f"[NFC] 下一个可用ID: {next_id}")
        return json.dumps({
            'code': 0,
            'msg': '获取成功',
            'data': {'next_id': next_id}
        })
        
    except Exception as e:
        print(f"[NFC] 获取下一个卡片ID失败: {str(e)}")
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500
    finally:
        conn.close()

@admin_bp.route('/api/nfc/card_status/<int:card_id>', methods=['GET'])
@admin_required
def get_card_status(card_id):
    """获取指定NFC卡片的状态"""
    try:
        print(f"[NFC] 获取卡片状态: {card_id}")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT status FROM NFC_card WHERE card_id = ?', (card_id,))
        result = cursor.fetchone()
        
        if result:
            print(f"[NFC] 卡片状态: {result['status']}")
            return json.dumps({
                'code': 0,
                'msg': '获取成功',
                'data': {'status': result['status']}
            })
        else:
            print(f"[NFC] 卡片不存在: {card_id}")
            return json.dumps({
                'code': 404,
                'msg': '卡片不存在',
                'data': None
            }), 404
            
    except Exception as e:
        print(f"[NFC] 获取卡片状态失败: {str(e)}")
        return json.dumps({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500
    finally:
        conn.close()

# 通知管理接口
@admin_bp.route('/api/notifications', methods=['GET'])
@admin_required
def admin_get_notifications():
    """获取通知列表"""
    try:
        target_type = request.args.get('target_type', 'all')
        target_id = request.args.get('target_id', type=int)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        notifications = notification_service.get_notifications(
            target_type=target_type,
            target_id=target_id,
            limit=limit,
            offset=offset
        )
        return json.dumps({
            'code': 0,
            'msg': 'success',
            'data': notifications
        })
    except Exception as e:
        return json.dumps({
            'code': 1,
            'msg': str(e)
        })

@admin_bp.route('/api/notifications', methods=['POST'])
@admin_required
def admin_create_notification():
    """创建新通知"""
    try:
        data = request.get_json()
        required_fields = ['title', 'content', 'type']
        for field in required_fields:
            if field not in data:
                return json.dumps({
                    'code': 1,
                    'msg': f'缺少必要字段: {field}'
                })
        
        with get_db_connection() as conn:
            notification = notification_service.add_notification(data)
            
            # 通过WebSocket广播新通知
            socketio.emit('notification:new', notification, broadcast=True)
            
            return json.dumps({
                'code': 0,
                'msg': 'success',
                'data': notification
            })
    except Exception as e:
        return json.dumps({
            'code': 1,
            'msg': str(e)
        })

@admin_bp.route('/api/notifications/<int:notification_id>', methods=['PUT'])
@admin_required
def admin_update_notification(notification_id):
    """更新通知"""
    try:
        data = request.get_json()
        with get_db_connection() as conn:
            notification = notification_service.update_notification(notification_id, data)
            
            # 通过WebSocket广播通知更新
            socketio.emit('notification:update', notification, broadcast=True)
            
            return json.dumps({
                'code': 0,
                'msg': 'success',
                'data': notification
            })
    except Exception as e:
        return jsonify({
            'code': 1,
            'msg': str(e)
        })

@admin_bp.route('/api/notifications/<int:notification_id>', methods=['DELETE'])
@admin_required
def admin_delete_notification(notification_id):
    """删除通知"""
    try:
        success = notification_service.delete_notification(notification_id)
            
        if success:
            # 通过WebSocket广播通知删除
            socketio.emit('notification:delete', {'id': notification_id}, broadcast=True)
            
            return jsonify({
                'code': 0,
                'msg': 'success'
            })
        else:
            return jsonify({
                'code': 1,
                'msg': '删除失败'
            })
    except Exception as e:
        return jsonify({
            'code': 1,
            'msg': str(e)
        })

@admin_bp.route('/api/notifications/cleanup', methods=['POST'])
@admin_required
def admin_cleanup_notifications():
    """清理过期通知"""
    try:
        count = notification_service.cleanup_expired_notifications()
            
        return json.dumps({
            'code': 0,
            'msg': 'success',
            'data': {
                'cleaned_count': count
            }
        })
    except Exception as e:
        return json.dumps({
            'code': 1,
            'msg': str(e)
        })

if __name__ == '__main__':
    socketio.run(app, debug=True)
