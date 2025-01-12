# -*- coding: utf-8 -*-


# Author: 一根鱼骨棒 Email 775639471@qq.com

# Date: 2025-01-07 14:02:42

# LastEditTime: 2025-01-12 23:01:02

# LastEditors: 一根鱼骨棒

# Description: 本开源代码使用GPL 3.0协议

# Software: VScode

# Copyright 2025 迷舍


from flask import Flask, jsonify, request, redirect, send_from_directory, make_response
from flask_cors import CORS
import sqlite3
import os
from admin import admin_bp
from flask_socketio import SocketIO, emit, join_room, leave_room
from datetime import datetime, time, timedelta
import schedule
import threading
import time as time_module
from functools import wraps
import json
import uuid


app = Flask(__name__, static_folder='static')
CORS(app)  # 启用CORS支持跨域请求


# 数据库路径

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')


app.secret_key = '00000000000000000000000000000000'  # 设置session密钥
app.register_blueprint(admin_bp, url_prefix='/admin')


# 初始化Flask-SocketIO
socketio = SocketIO(app,
                    cors_allowed_origins="*",
                    ping_timeout=5,
                    ping_interval=2
                    )


# 添加请求记录列表
request_logs = []
MAX_LOGS = 100  # 最多保存100条记录

# 记录请求的装饰器


def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 获取请求信息
        log_entry = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'method': request.method,
            'path': request.path,
            'args': dict(request.args),
            'form': dict(request.form),
            'headers': {k: v for k, v in request.headers.items()},
            'remote_addr': request.remote_addr,
            'request_data': request.get_json() if request.is_json else None
        }

        # 执行原始函数并捕获响应
        response = f(*args, **kwargs)

        # 添加响应信息
        try:
            # 处理不同类型的响应
            if isinstance(response, tuple):
                response_data, status_code = response
            else:
                response_data = response
                status_code = 200

            # 处理Response对象
            if hasattr(response_data, 'get_json'):
                response_data = response_data.get_json()
            elif hasattr(response_data, 'response'):
                response_data = response_data.response[0].decode('utf-8')
                try:
                    response_data = json.loads(response_data)
                except:
                    pass

            log_entry['response'] = {
                'status_code': status_code,
                'data': response_data
            }
        except Exception as e:
            log_entry['response'] = {
                'error': str(e),
                'status_code': 500
            }

        # 添加新记录并保持最大长度
        request_logs.insert(0, log_entry)
        if len(request_logs) > MAX_LOGS:
            request_logs.pop()

        # 通过WebSocket发送更新
        socketio.emit('log_update', {
            'logs': request_logs,
            'latest': log_entry
        })

        return response

    return decorated_function


def get_db_connection():
    """创建数据库连接"""

    try:

        # 确保数据库目录存在

        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        # 创建连接

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row

        print(f"Successfully connected to database at {DB_PATH}")  # 调试输出
        return conn

    except Exception as e:

        print(f"Database connection error: {str(e)}")  # 调试输出
        raise


@app.route('/api/player', methods=['GET'])
def get_player():
    """获取角色信息"""

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        # 从player_data表获取角色信息

        cursor.execute('''

            SELECT * FROM player_data where id=1
        ''')

        # 获取列名

        columns = [description[0] for description in cursor.description]

        # 获取结果并转换为字典
        character = cursor.fetchone()

        if character:
            player_data = dict(zip(columns, character))

            return jsonify({

                'id': player_data['id'],

                'user_id': player_data['user_id'],

                'stamina': player_data['stamina'],

                'strength': player_data['strength'],

                'intelligence': player_data['intelligence'],

                'player_name': player_data['player_name'],

                'create_time': player_data['create_time'],

                'level': player_data['level'],

                'experience': player_data['experience']

            })
        else:

            return jsonify({'error': 'Character not found'}), 404

    except sqlite3.Error as e:

        print("Database error:", str(e))  # 调试输出

        return jsonify({'error': str(e)}), 500

    finally:

        conn.close()


@app.route('/api/tasks/available/<int:user_id>', methods=['GET'])
def get_available_tasks(user_id):
    """获取可用任务列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 从tasks表获取可用任务，区分每日任务和普通任务
        # 添加user_id限制：task_scope=0表示所有玩家可见，或task_scope等于指定玩家ID
        cursor.execute('''
            SELECT 
                t.id,
                t.name,
                t.description,
                t.points,
                t.stamina_cost,
                t.task_rewards,
                t.task_type,
                t.task_status,
                t.limit_time
            FROM tasks t
            WHERE t.is_enabled = 1 
            AND (t.task_scope = 0 OR t.task_scope = ?)
            AND t.id NOT IN (
                SELECT task_id 
                FROM player_task 
                WHERE user_id = ? 
            )
        ''', (user_id, user_id))

        tasks = []
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        for row in rows:
            task_dict = dict(zip(columns, row))
            tasks.append(task_dict)

        return jsonify(tasks)

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 添加获取玩家当前任务的API


@app.route('/api/tasks/current/<int:user_id>', methods=['GET'])
def get_current_tasks(user_id):
    """获取用户当前未过期的任务列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取当前时间戳
        current_timestamp = int(datetime.now().timestamp())

        # 获取未过期的任务
        cursor.execute('''
            SELECT 
                pt.id,
                t.name,
                t.description,
                t.points,
                t.stamina_cost,
                pt.starttime,
                pt.points_earned,
                pt.status,
                t.task_type,
                pt.endtime
            FROM player_task pt
            JOIN tasks t ON pt.task_id = t.id
            WHERE pt.user_id = ? 
            AND pt.endtime > ?
            ORDER BY pt.starttime DESC
        ''', (user_id, current_timestamp))

        tasks = []
        for row in cursor.fetchall():
            tasks.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'points': row[3],
                'stamina_cost': row[4],
                'starttime': row[5],
                'points_earned': row[6],
                'status': row[7],
                'task_type': row[8],
                'endtime': row[9]
            })

        return jsonify(tasks)

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/tasks/<int:task_id>/accept', methods=['POST', 'OPTIONS'])
def accept_task(task_id):
    """接受任务"""
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    conn = None
    try:
        # 打印请求数据以便调试
        print("Request Data:", request.get_json())
        
        # 获取请求数据
        data = request.get_json()
        if not data or 'user_id' not in data:
            print("Missing user_id in request:", data)
            return jsonify({'error': 'Missing user_id'}), 400
            
        user_id = data['user_id']
        current_timestamp = int(datetime.now().timestamp())
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务是否存在且可接受
        cursor.execute('''
            SELECT task_status, limit_time 
            FROM tasks 
            WHERE id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task[0] != 'AVAILABLE':
            return jsonify({'error': 'Task is not available'}), 400

        # 计算结束时间
        endtime = current_timestamp + task[1] if task[1] else None

        # 将任务添加到player_task表
        cursor.execute('''
            INSERT INTO player_task (
                task_id,
                user_id,
                starttime,
                endtime,
                status,
                points_earned
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            task_id,
            user_id,
            current_timestamp,
            endtime,
            'IN_PROGRESS',
            0
        ))

        # 更新任务状态
        cursor.execute('''
            UPDATE tasks 
            SET task_status = 'IN_PROGRESS'
            WHERE id = ?
        ''', (task_id,))

        conn.commit()
        
        # 添加CORS头部到响应
        response = jsonify({
            'message': 'Task accepted successfully',
            'starttime': current_timestamp,
            'endtime': endtime
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error accepting task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/tasks/<int:task_id>/abandon', methods=['POST', 'OPTIONS'])
def abandon_task(task_id):
    """放弃任务"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    conn = None
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'Missing user_id'}), 400

        user_id = data['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务状态
        cursor.execute('''
            SELECT task_status 
            FROM tasks 
            WHERE id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task[0] != 'IN_PROGRESS':
            return jsonify({'error': 'Task is not in progress'}), 400

        # 更新任务状态
        cursor.execute('''
            UPDATE tasks 
            SET task_status = 'ABANDONED'
            WHERE id = ?
        ''', (task_id,))

        conn.commit()
        
        response = jsonify({'message': 'Task abandoned successfully'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error abandoning task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/tasks/<int:task_id>/complete', methods=['POST', 'OPTIONS'])
def complete_task(task_id):
    """完成任务"""
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    conn = None
    try:
        data = request.get_json()
        if not data or 'user_id' not in data:
            return jsonify({'error': 'Missing user_id'}), 400

        user_id = data['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务状态
        cursor.execute('''
            SELECT task_status, task_rewards
            FROM tasks 
            WHERE id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        if task[0] != 'IN_PROGRESS':
            return jsonify({'error': 'Task is not in progress'}), 400

        # 更新任务状态
        cursor.execute('''
            UPDATE tasks 
            SET task_status = 'COMPLETED'
            WHERE id = ?
        ''', (task_id,))

        conn.commit()
        
        response = jsonify({
            'message': 'Task completed successfully',
            'rewards': task[1]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error completing task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/tasks/nfc_post', methods=['POST'])
def nfc_task_post():
    """处理NFC任务提交"""
    conn = None  # 初始化连接变量
    try:
        data = request.values  # 使用request.values获取form-data数据

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # 验证必要字段
        required_fields = ['id', 'character', 'device']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务状态
        cursor.execute('''
            SELECT id, name, description, is_enabled 
            FROM tasks 
            WHERE id = ? AND is_enabled = 1
        ''', (data['id'],))

        task = cursor.fetchone()

        if not task:
            return jsonify({'error': 'Task not found or not enabled'}), 404

        # 记录NFC打卡数据
        # cursor.execute('''
        #     INSERT INTO nfc_records (
        #         task_id,
        #         character_id,
        #         device_type,
        #         add_time
        #     ) VALUES (?, ?, ?, ?)
        # ''', (
        #     data['id'],
        #     data['character'],
        #     data['device'],
        #     data['addtime']
        # ))

        conn.commit()

        # 构建推送消息
        task_data = {
            'task_id': task[0],
            'task_name': task[1],
            'task_description': task[2],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 通过WebSocket发送任务通知
        socketio.emit('nfc_task_update', task_data)

        return jsonify({
            'message': 'NFC task recorded successfully',
            'task': task_data
        })

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        if conn:
            conn.rollback()  # 发生错误时回滚事务
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        print(f"Error: {str(e)}")
        if conn:
            conn.rollback()  # 发生错误时回滚事务
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:  # 只在连接存在时关闭
            conn.close()


def assign_daily_tasks():
    """每天早上7点分配每日任务"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取当天的7点和22点时间戳
        today = datetime.now().date()
        start_time = datetime.combine(today, time(7, 0))  # 早上7点
        end_time = datetime.combine(today, time(22, 0))   # 晚上10点
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        # 获取所有启用的每日任务
        cursor.execute('''
            SELECT id, task_scope 
            FROM tasks 
            WHERE is_enabled = 1 AND task_type = 'DAILY'
        ''')
        daily_tasks = cursor.fetchall()

        # 获取所有玩家ID
        cursor.execute('SELECT user_id FROM player_data')
        all_players = [row[0] for row in cursor.fetchall()]

        # 为每个任务分配玩家
        for task_id, task_scope in daily_tasks:
            if task_scope == 0:  # 所有玩家都可见的任务
                players = all_players
            else:  # 特定玩家的任务
                players = [task_scope]

            # 为符合条件的玩家添加任务
            for player_id in players:
                # 检查玩家是否已有该任务
                cursor.execute('''
                    SELECT id FROM player_task 
                    WHERE user_id = ? AND task_id = ? 
                    AND starttime = ?
                ''', (player_id, task_id, start_timestamp))

                if not cursor.fetchone():  # 如果玩家还没有这个任务
                    cursor.execute('''
                        INSERT INTO player_task 
                        (user_id, task_id, starttime, endtime, status) 
                        VALUES (?, ?, ?, ?, 'available')
                    ''', (player_id, task_id, start_timestamp, end_timestamp))

        conn.commit()
        print(f"Daily tasks assigned successfully at {datetime.now()}")

    except sqlite3.Error as e:
        print(f"Database error in assign_daily_tasks: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def run_scheduler():
    """运行调度器"""
    schedule.every().day.at("07:00").do(assign_daily_tasks)

    while True:
        schedule.run_pending()
        time_module.sleep(60)  # 每分钟检查一次

# 在应用启动时启动调度器


def start_scheduler():
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True  # 设置为守护线程
    scheduler_thread.start()


# 添加模板目录配置
TEMPLATE_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'templates')


@app.route('/')
def index():
    """显示后端请求记录的首页"""
    try:
        template_path = os.path.join(TEMPLATE_DIR, 'index.html')

        # 获取过滤参数
        method_filter = request.args.get('method', '').upper()
        path_filter = request.args.get('path', '')

        # 过滤日志
        filtered_logs = request_logs
        if method_filter:
            filtered_logs = [
                log for log in filtered_logs if log['method'] == method_filter]
        if path_filter:
            filtered_logs = [
                log for log in filtered_logs if path_filter in log['path']]

        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # 生成请求记录HTML
        logs_html = ''
        for log in filtered_logs:
            logs_html += f"""
                <div class="request-log">
                    <div class="timestamp">{log['timestamp']}</div>
                    <div>
                        <span class="method {log['method']}">{log['method']}</span>
                        <span class="path">{log['path']}</span>
                        <span class="ip">from {log['remote_addr']}</span>
                    </div>
                    <pre>{json.dumps(log, indent=2, ensure_ascii=False)}</pre>
                </div>
            """

        # 替换模板中的占位符
        html = template.replace('{{request_logs}}', logs_html)
        return html

    except Exception as e:
        print(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500
# 添加清除日志的路由


@app.route('/clear-logs', methods=['POST'])
def clear_logs():
    """清除所有请求日志"""
    global request_logs
    request_logs = []
    return redirect('/')


# 为所有现有路由添加日志装饰器
app.view_functions = {
    endpoint: log_request(func)
    for endpoint, func in app.view_functions.items()
}


# 添加初始数据加载路由
@app.route('/api/logs')
def get_logs():
    """获取初始日志数据"""
    method_filter = request.args.get('method', '').upper()
    path_filter = request.args.get('path', '')

    filtered_logs = request_logs
    if method_filter:
        filtered_logs = [
            log for log in filtered_logs if log['method'] == method_filter]
    if path_filter:
        filtered_logs = [
            log for log in filtered_logs if path_filter in log['path']]

    return jsonify(filtered_logs)

# WebSocket连接处理


@socketio.on('connect')
def handle_connect():
    """处理WebSocket连接"""
    print("Client connected")
    emit('connected', {'status': 'success'})

@socketio.on('subscribe_tasks')
def handle_task_subscription(data):
    """处理任务订阅"""
    user_id = data.get('user_id')
    if user_id:
        # 将客户端加入以用户ID命名的房间
        join_room(f'user_{user_id}')
        print(f"User {user_id} subscribed to task updates")

def broadcast_task_update(user_id, task_data):
    """向指定用户广播任务更新"""
    socketio.emit('task_update', task_data, room=f'user_{user_id}')

# 如果需要自定义静态文件路由
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)
    # 在应用启动时调用
if __name__ == '__main__':
    start_scheduler()
    # assign_daily_tasks() 测试使用
    socketio.run(app, debug=True, host='192.168.1.12', port=5000)


