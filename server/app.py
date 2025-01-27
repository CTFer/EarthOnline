# -*- coding: utf-8 -*-
import eventlet
eventlet.monkey_patch()  # 必须在其他导入之前执行

from flask import Flask, jsonify, request, redirect, send_from_directory, make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import os
from admin import admin_bp
from datetime import datetime, time, timedelta
import schedule
import threading
import time as time_module
from functools import wraps
import json
import uuid

app = Flask(__name__, static_folder='static')
CORS(app)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')

app.secret_key = '00000000000000000000000000000000'  # 设置session密钥
app.register_blueprint(admin_bp, url_prefix='/admin')

# 修改 SocketIO 配置
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,
    engineio_logger=False,
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


@app.route('/api/player/<int:player_id>', methods=['GET'])
def get_player(player_id):
    """获取角色信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM player_data where id=?', (player_id,))
        columns = [description[0] for description in cursor.description]
        character = cursor.fetchone()

        if character:
            player_data = dict(zip(columns, character))
            return jsonify({
                'code': 0,
                'msg': '获取角色信息成功',
                'data': {
                    'id': player_data['id'],
                    'player_id': player_data['player_id'],
                    'stamina': player_data['stamina'],
                    'strength': player_data['strength'],
                    'player_name': player_data['player_name'],
                    'create_time': player_data['create_time'],
                    'level': player_data['level'],
                    'experience': player_data['experience']
                }
            })
        else:
            return jsonify({
                'code': 1,
                'msg': '角色不存在',
                'data': None
            }), 404

    except sqlite3.Error as e:
        print("Database error:", str(e))
        return jsonify({
            'code': 2,
            'msg': f'数据库错误: {str(e)}',
            'data': None
        }), 500
    finally:
        conn.close()

@app.route('/api/get_players', methods=['GET'])
def get_players():
    """获取所有玩家"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT player_id, player_name 
            FROM player_data 
            ORDER BY player_id ASC
        ''')
        
        players = [dict(id=row[0], name=row[1]) for row in cursor.fetchall()]
        
        return jsonify({
            "code": 0,
            "msg": "获取玩家列表成功",
            "data": players
        })
        
    except Exception as e:
        print(f"获取玩家列表出错: {str(e)}")
        return jsonify({
            "code": 1,
            "msg": f"获取玩家列表失败: {str(e)}",
            "data": None
        }), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/tasks/available/<int:player_id>', methods=['GET'])
def get_available_tasks(player_id):
    """获取可用任务列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                t.id, t.name, t.description, t.points, t.stamina_cost,
                t.task_rewards, t.task_type, t.task_status, t.limit_time, t.icon
            FROM tasks t
            WHERE t.is_enabled = 1 
            AND (t.task_scope = 0 OR t.task_scope = ?)
            AND t.id NOT IN (
                SELECT task_id FROM player_task WHERE player_id = ?
            )
        ''', (player_id, player_id))

        tasks = []
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        for row in rows:
            task_dict = dict(zip(columns, row))
            tasks.append(task_dict)

        return jsonify({
            'code': 0,
            'msg': '获取可用任务成功',
            'data': tasks
        })

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return jsonify({
            'code': 1,
            'msg': f'获取任务失败: {str(e)}',
            'data': None
        }), 500
    finally:
        conn.close()

# 添加获取玩家当前任务的API


@app.route('/api/tasks/current/<int:player_id>', methods=['GET'])
def get_current_tasks(player_id):
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
                pt.endtime,
                t.icon
            FROM player_task pt
            JOIN tasks t ON pt.task_id = t.id
            WHERE pt.player_id = ? 
            AND (pt.endtime > ? or pt.endtime is null)
            ORDER BY pt.starttime DESC
        ''', (player_id, current_timestamp))

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
                'endtime': row[9],
                'icon': row[10]
            })

        return jsonify({
            'code': 0,
            'msg': '获取当前任务成功',
            'data': tasks
        })

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return jsonify({
            'code': 1,
            'msg': f'获取当前任务失败: {str(e)}',
            'data': None
        }), 500
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
        print("Request Data:", request.get_json())
        
        data = request.get_json()
        if not data or 'player_id' not in data:
            print("Missing player_id in request:", data)
            return jsonify({
                'code': 1,
                'msg': '缺少玩家ID',
                'data': None
            }), 400
            
        player_id = data['player_id']
        current_timestamp = int(datetime.now().timestamp())
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务信息和前置任务
        cursor.execute('''
            SELECT t.task_status, t.limit_time, t.parent_task_id, t.name,
                   pt.name as parent_name
            FROM tasks t
            LEFT JOIN tasks pt ON t.parent_task_id = pt.id
            WHERE t.id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        task_status, limit_time, parent_task_id, task_name, parent_name = task

        if task_status != 'AVAILABLE':
            return jsonify({'error': 'Task is not available'}), 400

        # 如果有前置任务，检查前置任务完成状态
        if parent_task_id:
            cursor.execute('''
                SELECT status 
                FROM player_task 
                WHERE task_id = ? AND player_id = ?
                ORDER BY starttime DESC 
                LIMIT 1
            ''', (parent_task_id, player_id))
            
            parent_task_status = cursor.fetchone()
            
            if not parent_task_status:
                return jsonify({
                    'msg': f'需要先完成前置任务: {parent_name}',
                    'code': 'PREREQUISITE_NOT_STARTED'
                }), 400
            
            if parent_task_status[0] != 'COMPLETED':
                return jsonify({
                    'msg': f'需要先完成前置任务: {parent_name}',
                    'code': 'PREREQUISITE_NOT_COMPLETED'
                }), 400

        # 检查玩家是否已接受此任务
        cursor.execute('''
            SELECT status 
            FROM player_task 
            WHERE task_id = ? AND player_id = ? AND status != 'ABANDONED'
            ORDER BY starttime DESC 
            LIMIT 1
        ''', (task_id, player_id))
        
        existing_task = cursor.fetchone()
        if existing_task:
            return jsonify({
                'msg': f'已接受任务: {task_name}',
                'code': 'TASK_ALREADY_ACCEPTED'
            }), 400

        # 计算结束时间
        endtime = current_timestamp + limit_time if limit_time else None

        # 将任务添加到player_task表
        cursor.execute('''
            INSERT INTO player_task (
                task_id,
                player_id,
                starttime,
                endtime,
                status,
                points_earned
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            task_id,
            player_id,
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
        
        response = jsonify({
            'code': 0,
            'msg': '任务接受成功',
            'data': {
                'starttime': current_timestamp,
                'endtime': endtime,
                'task_name': task_name
            }
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error accepting task: {str(e)}")
        return jsonify({
            'code': 2,
            'msg': f'接受任务失败: {str(e)}',
            'data': None
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/tasks/<int:task_id>/abandon', methods=['POST'])
def abandon_task(task_id):
    """放弃任务"""
    conn = None
    try:
        data = request.get_json()
        if not data or 'player_id' not in data:
            return jsonify({
                'code': 1,
                'msg': '缺少玩家ID',
                'data': None
            }), 400

        player_id = data['player_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务状态
        cursor.execute('''
            SELECT task_status, name 
            FROM tasks 
            WHERE id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        if not task:
            return jsonify({
                'code': 2,
                'msg': '任务不存在',
                'data': None
            }), 404

        if task[0] != 'IN_PROGRESS':
            return jsonify({
                'code': 3,
                'msg': '任务不在进行中状态',
                'data': None
            }), 400

        # 更新任务状态
        cursor.execute('''
            UPDATE tasks 
            SET task_status = 'ABANDONED'
            WHERE id = ?
        ''', (task_id,))

        conn.commit()
        
        return jsonify({
            'code': 0,
            'msg': f'已放弃任务: {task[1]}',
            'data': None
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'code': 4,
            'msg': f'放弃任务失败: {str(e)}',
            'data': None
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """完成任务"""
    conn = None
    try:
        data = request.get_json()
        if not data or 'player_id' not in data:
            return jsonify({
                'code': 1,
                'msg': '缺少玩家ID',
                'data': None
            }), 400

        player_id = data['player_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务状态
        cursor.execute('''
            SELECT task_status, task_rewards, name, points
            FROM tasks 
            WHERE id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        if not task:
            return jsonify({
                'code': 2,
                'msg': '任务不存在',
                'data': None
            }), 404

        if task[0] != 'IN_PROGRESS':
            return jsonify({
                'code': 3,
                'msg': '任务不在进行中状态',
                'data': None
            }), 400

        # 更新任务状态
        cursor.execute('''
            UPDATE tasks 
            SET task_status = 'COMPLETED'
            WHERE id = ?
        ''', (task_id,))

        conn.commit()
        
        return jsonify({
            'code': 0,
            'msg': f'任务完成: {task[2]}',
            'data': {
                'rewards': task[1],
                'points': task[3],
                'task_name': task[2]
            }
        })

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({
            'code': 4,
            'msg': f'完成任务失败: {str(e)}',
            'data': None
        }), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/tasks/nfc_post', methods=['POST'])
def nfc_task_post():
    """处理NFC任务提交"""
    conn = None
    try:
        print("\n[NFC] ====== 开始处理NFC任务提交 ======")
        data = request.values  # 使用request.values获取form-data数据
        print(f"[NFC] 接收到的原始数据: {data}")

        # 验证数据
        if not data:
            print("[NFC] 错误: 未提供数据")
            socketio.emit('nfc_task_update', {
                'type': 'ERROR',
                'message': '未提供任务数据'
            }, broadcast=True)  # 广播错误消息
            return jsonify({'error': 'No data provided'}), 400

        # 验证必要字段
        required_fields = ['id', 'player', 'device']
        if not all(field in data for field in required_fields):
            print(f"[NFC] 错误: 缺少必要字段. 收到的字段: {list(data.keys())}")
            socketio.emit('nfc_task_update', {
                'type': 'ERROR',
                'message': '缺少必要字段'
            }, broadcast=True)
            return jsonify({'error': 'Missing required fields'}), 400

        task_id = int(data['id'])
        player_id = data['player']
        room = f'user_{player_id}'
        print(f"[NFC] 任务ID: {task_id}, 玩家ID: {player_id}, 房间: {room}")

        # 如果是身份识别卡
        if task_id == 0:
            print("[NFC] 处理身份识别卡")
            update_data = {
                'type': 'IDENTITY',
                'player_id': player_id,
                'message': '身份识别成功'
            }
            print(f"[NFC] 发送身份识别更新: {update_data}")
            socketio.emit('nfc_task_update', update_data, room=room)
            return jsonify({'success': True})

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务是否存在且启用
        cursor.execute('''
            SELECT id, name, description, is_enabled, task_type, task_rewards, points 
            FROM tasks 
            WHERE id = ?
        ''', (task_id,))

        task = cursor.fetchone()
        if not task:
            socketio.emit('nfc_task_update', {
                'type': 'ERROR',
                'message': '任务不存在',
                'task_id': task_id
            }, room=room)
            return jsonify({'success': True})
        
        # 构建基础任务信息
        task_info = {
            'id': task[0],
            'name': task[1],
            'description': task[2],
            'task_type': task[4],
            'rewards': task[5],
            'points': task[6]
        }

        # 根据不同状态返回不同的消息
        if task[3] == 0:  # is_enabled = 0
            socketio.emit('nfc_task_update', {
                'type': 'ERROR',
                'message': '该任务未启用',
                'task': task_info
            }, room=room)
            return jsonify({'success': True})

        # 检查任务状态
        print(f"[NFC] 检查玩家 {player_id} 的任务状态")
        cursor.execute('''
            SELECT status, comment 
            FROM player_task 
            WHERE task_id = ? AND player_id = ?
        ''', (task_id, player_id))

        task_status = cursor.fetchone()
        print(f"[NFC] 当前任务状态: {task_status}")

        # 根据任务状态处理
        if not task_status:
            # 任务不存在，创建新任务
            print(f"[NFC] 为玩家 {player_id} 创建新任务")
            current_timestamp = int(datetime.now().timestamp())
            cursor.execute('''
                INSERT INTO player_task (
                    task_id, player_id, starttime, status, points_earned
                ) VALUES (?, ?, ?, 'IN_PROGRESS', 0)
            ''', (task_id, player_id, current_timestamp))
            
            conn.commit()
            update_data = {
                'type': 'NEW_TASK',
                'message': '任务已接受',
                'task': {
                    'id': task_id,
                    'name': task[1],
                    'description': task[2],
                    'task_type': task[4],
                    'timestamp': current_timestamp
                }
            }
            print(f"[NFC] 发送新任务通知: {update_data}")
            socketio.emit('nfc_task_update', update_data, room=room)
            return jsonify({'success': True})

        # 处理现有任务状态
        status = task_status[0]
        print(f"[NFC] 处理任务状态: {status}")
        
        update_data = None
        if status == 'IN_PROGRESS':
            current_timestamp = int(datetime.now().timestamp())
            cursor.execute('''
                UPDATE player_task 
                SET status = 'COMPLETED', 
                    complete_time = ? 
                WHERE task_id = ? AND player_id = ?
            ''', (current_timestamp, task_id, player_id))
            
            conn.commit()
            update_data = {
                'type': 'COMPLETE',
                'message': '任务完成！',
                'task': task_info,
                'timestamp': current_timestamp
            }
        elif status == 'COMPLETED':
            update_data = {
                'type': 'ALREADY_COMPLETED',
                'message': '该任务已完成',
                'task': task_info
            }
        elif status == 'REJECT':
            update_data = {
                'type': 'REJECTED',
                'message': f'任务被驳回: {task_status[1] or "无驳回原因"}'
            }
        elif status == 'CHECK':
            update_data = {
                'type': 'CHECKING',
                'message': '任务正在审核中'
            }
        else:
            update_data = {
                'type': 'ERROR',
                'message': '任务状态未知'
            }

        # 发送更新通知
        if update_data:
            print(f"[NFC] 发送任务状态更新: {update_data}")
            socketio.emit('nfc_task_update', update_data, room=room)

        print("[NFC] ====== NFC任务处理完成 ======\n")
        return jsonify({'success': True})

    except Exception as e:
        print(f"[NFC] ====== 发生错误 ======")
        print(f"[NFC] 错误信息: {str(e)}")
        if conn:
            conn.rollback()
        
        # 发送错误通知
        error_data = {
            'type': 'ERROR',
            'message': f'处理任务时出错: {str(e)}'
        }
        print(f"[NFC] 发送错误通知: {error_data}")
        if 'player_id' in locals():
            socketio.emit('nfc_task_update', error_data, room=f'user_{player_id}')
        else:
            socketio.emit('nfc_task_update', error_data, broadcast=True)
            
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
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
        cursor.execute('SELECT player_id FROM player_data')
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
                    WHERE player_id = ? AND task_id = ? 
                    AND starttime >= ? AND starttime < ?
                ''', (player_id, task_id, start_timestamp, end_timestamp))

                if not cursor.fetchone():  # 如果玩家在今天还没有这个任务
                    cursor.execute('''
                        INSERT INTO player_task 
                        (player_id, task_id, starttime, endtime, status) 
                        VALUES (?, ?, ?, ?, 'IN_PROGRESS')
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


def check_daily_tasks():
    """在程序启动时检查今日任务分配情况"""
    current_hour = datetime.now().hour
    if current_hour >= 7:  # 如果当前时间已过早上7点
        assign_daily_tasks()  # 执行一次任务分配检查


def run_scheduler():
    """运行调度器"""
    schedule.every().day.at("07:00").do(assign_daily_tasks)

    while True:
        schedule.run_pending()
        time_module.sleep(60)  # 每分钟检查一次

# 在应用启动时启动调度器


def start_scheduler():
    check_daily_tasks()  # 启动时检查今日任务
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
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
    print(f"[WebSocket] Received subscription request: {data}")
    player_id = data.get('player_id')
    if player_id:
        room = f'user_{player_id}'
        join_room(room)
        print(f"[WebSocket] User {player_id} joined room: {room}")
        # 发送确认消息
        emit('subscription_confirmed', {
            'status': 'success',
            'room': room
        }, room=room)
    else:
        print(f"[WebSocket] Warning: Received subscribe_tasks without player_id")

def broadcast_task_update(player_id, task_data):
    """向指定用户广播任务更新"""
    socketio.emit('task_update', task_data, room=f'user_{player_id}')

# 如果需要自定义静态文件路由
@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)
    # 在应用启动时调用
if __name__ == '__main__':
    start_scheduler()
    print("Server started")
    try:
        # 使用 eventlet 启动服务器
        socketio.run(
            app,
            # host='192.168.5.18',  # 监听所有网络接口
            host='192.168.1.4',  # 监听所有网络接口
            port=5000,
            debug=True,
            use_reloader=True,
            log_output=True
        )
    except Exception as e:
        print(f"Error starting server: {str(e)}")
        # 如果 eventlet 启动失败，回退到开发服务器
        print("Falling back to development server...")
        app.run(debug=True)


