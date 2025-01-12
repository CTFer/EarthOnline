from flask import Blueprint, request, jsonify, render_template, session, redirect, url_for, flash
from functools import wraps
import sqlite3
import os
from api import api_registry

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')

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
        
        # 这里简化了验证逻辑，实际应用中应该使用更安全的方式
        if username == 'admin' and password == 'admin123':
            session['is_admin'] = True
            return redirect(url_for('admin.index'))
        else:
            flash('用户名或密码错误')
            
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
        
        cursor.execute('''
            INSERT INTO users (username, password, created_at)
            VALUES (?, ?, datetime('now'))
        ''', (data['username'], data['password']))  # 实际应用中应该对密码进行哈希处理
        
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
            cursor.execute('''
                UPDATE users 
                SET username = ?, password_hash = ?
                WHERE id = ?
            ''', (data['username'], data['password'], user_id))  # 实际应用中应该对密码进行哈希处理
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks')
        tasks = [dict(row) for row in cursor.fetchall()]
        return jsonify({"data": tasks})
    except Exception as e:
        print(f"Error in get_tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks', methods=['POST'])
@admin_required
def add_task():
    """添加新任务"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (name, description, exp_reward, gold_reward, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (data['name'], data['description'], data['exp_reward'], data['gold_reward']))
        
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
        
        cursor.execute('''
            UPDATE tasks 
            SET name = ?, description = ?, exp_reward = ?, gold_reward = ?
            WHERE id = ?
        ''', (data['name'], data['description'], data['exp_reward'], data['gold_reward'], task_id))
        
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

if __name__ == '__main__':
    app.run(debug=True)