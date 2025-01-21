from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from functools import wraps
import sqlite3
import os
from api import api_registry
import json
import hashlib  # 添加到文件顶部的导入
from datetime import datetime

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

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
            print(f"Login attempt - User: {username}, Found user: {dict(user) if user else None}")  # 调试日志
            
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
        return jsonify({"data": users})
    except Exception as e:
        print(f"Error in get_users: {str(e)}")
        return jsonify({'error': str(e)}), 500
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
        
        return jsonify({"id": user_id}), 201
    except Exception as e:
        print(f"Error in add_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """获取指定用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user is None:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify(dict(user))
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
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
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除用户相关的任务
        cursor.execute('DELETE FROM tasks WHERE user_id = ?', (user_id,))
        
        # 删除用户
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in delete_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
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
        return jsonify({"data": skills})
    except Exception as e:
        print(f"Error in get_skills: {str(e)}")
        return jsonify({'error': str(e)}), 500
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
        
        return jsonify({"id": skill_id}), 201
    except Exception as e:
        print(f"Error in add_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/skills/<int:skill_id>', methods=['GET'])
@admin_required
def get_skill(skill_id):
    """获取指定技能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, proficiency, description FROM skills WHERE id = ?', (skill_id,))
        skill = cursor.fetchone()
        
        if skill is None:
            return jsonify({'error': 'Skill not found'}), 404
            
        return jsonify(dict(skill))
    except Exception as e:
        print(f"Error in get_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
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
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in update_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
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
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in delete_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks', methods=['GET'])
@admin_required
def get_tasks():
    """获取所有任务"""
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
            FROM tasks
            ORDER BY id
        '''
        print(f"执行SQL: {query}")  # 调试日志
        cursor.execute(query)
        
        # 转换为字典列表
        tasks = []
        for row in cursor.fetchall():
            task = dict(row)
            
            # 确保所有字段都存在，设置默认值
            for column in columns:
                if column not in task or task[column] is None:
                    if column in ['is_enabled', 'repeatable']:
                        task[column] = False
                    elif column in ['points', 'stamina_cost', 'limit_time', 'repeat_time', 
                                  'completion_count', 'task_chain_id', 'parent_task_id']:
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
            
            tasks.append(task)
        
        print(f"获取到 {len(tasks)} 条任务数据")  # 调试日志
        
        response_data = {
            "code": 0,
            "msg": "",
            "count": len(tasks),
            "data": tasks
        }
        return jsonify(response_data)
        
    except Exception as e:
        print(f"获取任务列表出错: {str(e)}")  # 错误日志
        return jsonify({
            "code": 1,
            "msg": f"获取任务列表失败: {str(e)}",
            "count": 0,
            "data": []
        }), 500
    finally:
        if conn:
            conn.close()

@admin_bp.route('/api/tasks', methods=['POST'])
@admin_required
def add_task():
    """添加新任务"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 转换任务奖励为JSON字符串
        task_rewards = json.dumps(data.get('task_rewards', {}))
        
        cursor.execute('''
            INSERT INTO tasks (
                name, description, task_chain_id, parent_task_id,
                task_type, task_status, task_scope, stamina_cost,
                limit_time, repeat_time, is_enabled, repeatable,
                task_rewards, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (
            data['name'],
            data['description'],
            data['task_chain_id'],
            data['parent_task_id'],
            data['task_type'],
            data['task_status'],
            data['task_scope'],
            data['stamina_cost'],
            data['limit_time'],
            data['repeat_time'],
            data['is_enabled'],
            data['repeatable'],
            task_rewards
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({"id": task_id}), 201
    except Exception as e:
        print(f"Error in add_task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@admin_required
def update_task(task_id):
    """更新任务"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 确保 task_rewards 是 JSON 字符串
        if isinstance(data.get('task_rewards'), dict):
            data['task_rewards'] = json.dumps(data['task_rewards'])
        
        cursor.execute('''
            UPDATE tasks 
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
                task_rewards = ?
            WHERE id = ?
        ''', (
            data['name'],
            data['description'],
            data['task_chain_id'],
            data['parent_task_id'],
            data['task_type'],
            data['task_status'],
            data['task_scope'],
            data['stamina_cost'],
            data['limit_time'],
            data['repeat_time'],
            data['is_enabled'],
            data['repeatable'],
            data['task_rewards'],
            task_id
        ))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in update_task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@admin_required
def delete_task(task_id):
    """删除任务"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in delete_task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 添加API文档路由
@admin_bp.route('/api/docs', methods=['GET'])
@admin_required
def get_api_docs():
    """获取API文档"""
    try:
        endpoints = api_registry.get_all_endpoints()
        return jsonify({
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
        return jsonify({'error': str(e)}), 500

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
                pt.points_earned,
                pt.status,
                pt.complete_time,
                pt.comment
            FROM player_task pt 
            LEFT JOIN tasks t ON pt.task_id = t.id 
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
                'points_earned': row[6],
                'status': row[7],
                'complete_time': row[8],
                'comment': row[9]
            })
        
        conn.close()
        
        return jsonify({
            'code': 0,
            'msg': '',
            'count': total,
            'data': tasks
        })
        
    except Exception as e:
        return jsonify({
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
                pt.points_earned,
                pt.status,
                pt.complete_time,
                pt.comment
            FROM player_task pt 
            LEFT JOIN tasks t ON pt.task_id = t.id 
            WHERE pt.id = ?
        ''', (task_id,))
        
        row = cursor.fetchone()
        if row is None:
            return jsonify({
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
            'points_earned': row[6],
            'status': row[7],
            'complete_time': row[8],
            'comment': row[9]
        }
        
        conn.close()
        return jsonify({
            'code': 0,
            'msg': '',
            'data': task
        })
        
    except Exception as e:
        print("Get task error:", str(e))
        return jsonify({
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
                points_earned, status, complete_time, comment
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('player_id'),
            data.get('task_id'),
            data.get('starttime', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            data.get('endtime'),
            data.get('points_earned', 0),
            data.get('status', 'available'),
            data.get('complete_time'),
            data.get('comment')
        ))
        
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            'code': 0,
            'msg': '创建成功',
            'data': {'id': task_id}
        }), 201
        
    except Exception as e:
        return jsonify({
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
                points_earned = ?,
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
            data.get('points_earned'),
            data.get('status'),
            data.get('complete_time'),
            data.get('comment'),
            task_id
        )
        
        print("Update params:", params)  # 调试日志
        cursor.execute(update_query, params)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({
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
                pt.points_earned,
                pt.status,
                pt.complete_time,
                pt.comment
            FROM player_task pt 
            LEFT JOIN tasks t ON pt.task_id = t.id 
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
            'points_earned': row[6],
            'status': row[7],
            'complete_time': row[8],
            'comment': row[9]
        }
        
        conn.close()
        print("Updated data:", updated_data)
        return jsonify({
            'code': 0,
            'msg': '更新成功',
            'data': updated_data
        })
        
    except Exception as e:
        print("Update error:", str(e))  # 错误日志
        return jsonify({
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
        
        return jsonify({
            'code': 0,
            'msg': '删除成功',
            'data': None
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'msg': str(e),
            'data': None
        }), 500

if __name__ == '__main__':
    app.run(debug=True)