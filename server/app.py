# -*- coding: utf-8 -*-
import eventlet
eventlet.monkey_patch()

import traceback
import uuid
import json
from functools import wraps
import time as time_module
import threading
import schedule
from datetime import datetime, time, timedelta
from admin import admin_bp
import os
import sqlite3
import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from flask import Flask, request, redirect, send_from_directory, make_response, render_template
from shop import shop_bp  # 确保在同一目录下
from function.PlayerService import player_service
from function.TaskService import task_service
from function.GPSService import gps_service
from function.RoadmapService import roadmap_service
from config import (
    SERVER_IP, 
    PORT, 
    DEBUG, 
    WAITRESS_CONFIG, 
    ENV,
    PROD_SERVER  # 添加这行
)
import requests
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)
app = Flask(__name__, static_folder='static')
CORS(app)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')

app.secret_key = '00000000000000000000000000000000'  # 设置session密钥
app.register_blueprint(admin_bp, url_prefix='/admin')

# 注册商店蓝图
app.register_blueprint(shop_bp)

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


def assign_daily_tasks():
    """分配每日任务并处理过期任务"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取当天的7点和22点时间戳
        today = datetime.now().date()
        start_time = datetime.combine(today, time(7, 0))  # 早上7点
        end_time = datetime.combine(today, time(22, 0))   # 晚上10点
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())
        current_time = int(datetime.now().timestamp())
        
        # 更新过期任务状态为UNFINISH
        cursor.execute('''
            UPDATE player_task 
            SET status = 'UNFINISH'
            WHERE status = 'IN_PROGRESS' 
            AND endtime < ? 
            AND endtime != 0
        ''', (current_time,))

        # 获取所有启用的每日任务
        cursor.execute('''
            SELECT id, task_scope 
            FROM task 
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

# 为所有现有路由添加日志装饰器
app.view_functions = {
    endpoint: log_request(func)
    for endpoint, func in app.view_functions.items()
}
# 添加模板目录配置
TEMPLATE_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), 'templates')
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

@app.route('/api/player/<int:player_id>', methods=['GET'])
def get_player_api(player_id):
    """获取角色信息"""
    print(player_id)    
    return player_service.get_player(player_id)


@app.route('/api/get_players', methods=['GET'])
def get_players():
    """获取所有玩家"""
    return player_service.get_players()

@app.route('/api/tasks/available/<int:player_id>', methods=['GET'])
def get_available_tasks(player_id):
    """获取可用任务列表"""
    return task_service.get_available_tasks(player_id)

# 添加获取玩家当前任务的API


@app.route('/api/tasks/current/<int:player_id>', methods=['GET'])
def get_current_tasks(player_id):
    """获取用户当前未过期的任务列表"""
    return task_service.get_current_tasks(player_id)


@app.route('/api/tasks/accept', methods=['POST'])
def accept_task():
    data = request.get_json()
    return task_service.accept_task(data['player_id'], data['task_id'])

@app.route('/api/tasks/abandon', methods=['POST'])
def abandon_task():
    data = request.get_json()
    return task_service.abandon_task(data['player_id'], data['task_id'])

@app.route('/api/tasks/complete', methods=['POST'])
def complete_task_api():
    data = request.get_json()
    return task_service.complete_task_api(data['player_id'], data['task_id'])




@app.route('/record')
def record():
    """显示后端请求记录的首页"""
    try:
        template_path = os.path.join(TEMPLATE_DIR, 'record.html')

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


@app.route('/')
def index():
    """客户端首页"""
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

    return json.dumps(filtered_logs)


# 如果需要自定义静态文件路由


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


@app.route('/api/nfc_post', methods=['POST'])
def handle_nfc_card():
    try:
        print("\n[NFC API] ====== 开始处理NFC卡片请求 ======")
        
        # 获取请求数据（支持 JSON 和 Form 格式）
        if request.is_json:
            data = request.json
            print(f"[NFC API Debug] 接收到JSON数据: {json.dumps(data, ensure_ascii=False)}")
        else:
            data = request.form.to_dict()
            print(f"[NFC API Debug] 接收到Form数据: {json.dumps(data, ensure_ascii=False)}")
        
        # 获取必要参数
        card_id = data.get('card_id')
        player_id = data.get('player_id')

        # 参数验证
        if not card_id or not player_id:
            error_msg = '缺少必要参数: card_id 或 player_id'
            print(f"[NFC API Debug] 错误: {error_msg}")
            return json.dumps({
                'code': 400,
                'msg': error_msg,
                'data': None
            }), 400

        print(f"[NFC API Debug] 卡片ID: {card_id}")
        print(f"[NFC API Debug] 玩家ID: {player_id}")

        # 调用 NFC 服务处理
        from function.NFC_service import NFCService
        nfc_service = NFCService()
        response, status_code = nfc_service.handle_nfc_card(card_id, player_id, socketio)

        print(f"[NFC API Debug] 处理结果: {json.dumps(response, ensure_ascii=False)}")
        print("[NFC API] ====== NFC卡片请求处理完成 ======\n")
        
        return response, status_code

    except Exception as e:
        error_msg = f'API处理失败: {str(e)}'
        print(f"[NFC API] 错误: {error_msg}")
        print(f"[NFC API] 详细错误信息: ", traceback.format_exc())

        if 'player_id' in locals():
            socketio.emit('nfc_task_update', {
                'type': 'ERROR',
                'message': error_msg
            }, room=f'user_{player_id}')

        return json.dumps({
            'code': 500,
            'msg': error_msg,
            'data': None
        }), 500

@app.route('/api/gps', methods=['POST'])
def add_gps():
    """添加GPS记录"""
    try:
        data = json.loads(request.data)
        print(f"[GPS] 获取到数据: {data}") 
        location = data.get('location', '')
        player_id = data.get('player_id')
        
        # 分割经纬度数据
        try:
            latitude, longitude = map(float, location.split(','))
        except (ValueError, AttributeError):
            return json.dumps({
                'code': 400,
                'msg': '无效的位置数据格式',
                'data': None
            }), 400

        # 处理时间戳
        try:
            timestamp_str = data.get('timestamp')
            if timestamp_str:
                # 将时间字符串转换为时间戳
                timestamp = int(datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').timestamp())
            else:
                timestamp = int(time_module.time())
        except ValueError:
            timestamp = int(time_module.time())
            logger.warning(f"无效的时间戳格式: {timestamp_str}, 使用当前时间")

        # 构建标准格式的GPS数据
        gps_data = {
            'x': longitude,        # 经度
            'y': latitude,         # 纬度
            'player_id': player_id,
            'device': data.get('device', 'unknown'),
            'remark': data.get('timestamp', ''),  # 原始时间字符串
            'accuracy': float(data.get('accuracy', 0)),  # GPS精度
            'speed': float(data.get('speed', 0)),    # 速度
            'device_time': timestamp  # 设备采集时间
        }
        print(f"[GPS] 添加GPS记录: {gps_data}")

        # 调用 GPS 服务添加记录
        result = gps_service.add_gps(gps_data)
        print(f"[GPS] 添加GPS记录结果: {result}")
        response_data = json.loads(result)
        
        # 只有在新增GPS记录时才发送 WebSocket 通知
        if (response_data['code'] == 0 and 
            response_data['msg'] == '添加GPS记录成功' and 
            player_id):
            # 添加速度和时间信息到推送数据中
            socket_data = {
                'x': longitude,
                'y': latitude,
                'player_id': player_id,
                'device': gps_data['device'],
                'remark': gps_data['remark'],
                'speed': gps_data['speed'],
                'battery': data.get('battery', 0),
                'timestamp': timestamp,
                'accuracy': gps_data['accuracy']
            }
            
            print(f"[GPS] 发送新GPS点位更新通知: {socket_data}")
        else:
            socket_data = {
                'speed': gps_data['speed'],
                'battery': data.get('battery', 0),
                'timestamp': timestamp,
                'accuracy': gps_data['accuracy']
            }
            print(f"[GPS] 仅更新时间，发送电量、速度、更新时间：{socket_data}")
        socketio.emit('gps_update', socket_data, room=f'user_{player_id}')    
        return result

    except Exception as e:
        logger.error(f"处理GPS数据失败: {str(e)}")
        return json.dumps({
            'code': 500,
            'msg': f'处理GPS数据失败: {str(e)}',
            'data': None
        }), 500

@app.route('/api/gps/<int:gps_id>', methods=['GET'])
def get_gps(gps_id):
    """获取单个GPS记录"""
    return gps_service.get_gps(gps_id)

@app.route('/api/gps/player/<int:player_id>', methods=['GET'])
def get_player_gps(player_id):
    """获取玩家GPS记录"""
    return gps_service.get_player_gps(player_id)

@app.route('/api/gps/<int:gps_id>', methods=['PUT'])
def update_gps(gps_id):
    """更新GPS记录"""
    data = request.get_json()
    return gps_service.update_gps(gps_id, data)


# 开发计划相关接口
@app.route('/api/roadmap/login', methods=['POST'])
def roadmap_login():
    """开发计划登录"""
    data = request.get_json()
    return roadmap_service.roadmap_login(data)
@app.route('/api/roadmap/check_login', methods=['GET'])
def roadmap_check_login():
    """开发计划检查登录"""
    return roadmap_service.check_login()
@app.route('/api/roadmap/logout', methods=['GET'])
def roadmap_logout():
    """开发计划登出"""
    return roadmap_service.roadmap_logout()
@app.route('/roadmap')
def roadmap():
    """开发计划首页"""
    return render_template('client/roadmap.html')
@app.route('/api/roadmap', methods=['GET'])
def get_roadmap():
    """获取开发计划"""
    return roadmap_service.get_roadmap()

def sync_to_prod(methods=['POST', 'PUT', 'DELETE']):
    """
    装饰器：同步数据库操作到生产环境
    :param methods: 需要同步的HTTP方法列表
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 获取原始响应
            original_response = f(*args, **kwargs)
            
            # 只在本地环境且请求方法在指定列表中时同步
            if ENV == 'local' and request.method in methods:
                try:
                    # 构建同步请求
                    prod_url = f"{PROD_SERVER['URL']}{request.path}"
                    prod_headers = {
                        'Content-Type': 'application/json',
                        'X-Sync-From': 'local',
                        'X-API-Key': PROD_SERVER['API_KEY']
                    }
                    
                    print(f"[Sync] Syncing {request.method} {request.path} to production")
                    print(f"[Sync] Target URL: {prod_url}")
                    
                    # 发送同步请求
                    sync_response = None
                    if request.method == 'POST':
                        sync_response = requests.post(prod_url, json=request.get_json(), headers=prod_headers)
                    elif request.method == 'PUT':
                        sync_response = requests.put(prod_url, json=request.get_json(), headers=prod_headers)
                    elif request.method == 'DELETE':
                        sync_response = requests.delete(prod_url, headers=prod_headers)
                    
                    print(f"[Sync] Sync completed with status code: {sync_response.status_code}")
                    if sync_response.status_code != 200:
                        print(f"[Sync] Error response: {sync_response.text}")
                except Exception as e:
                    print(f"[Sync] Error syncing to production: {str(e)}")
                    # 同步失败不影响本地操作
                    pass
            
            # 始终返回原始响应
            return original_response
        return wrapper
    return decorator

# 在需要同步的路由上使用装饰器
@app.route('/api/roadmap/add', methods=['POST'])
@sync_to_prod()
def add_roadmap():
    """添加开发计划"""
    data = request.get_json()
    return roadmap_service.add_roadmap(data)

@app.route('/api/roadmap/<int:roadmap_id>', methods=['PUT'])
@sync_to_prod()
def update_roadmap(roadmap_id):
    """更新开发计划"""
    data = request.get_json()
    return roadmap_service.update_roadmap(roadmap_id, data)

@app.route('/api/roadmap/<int:roadmap_id>', methods=['DELETE'])
@sync_to_prod()
def delete_roadmap(roadmap_id):
    """删除开发计划"""
    return roadmap_service.delete_roadmap(roadmap_id)
@app.route('/api/roadmap/get_sync', methods=['GET'])
def sync_roadmap():
    """手动触发同步_仅本地环境可用"""
    return roadmap_service.sync_from_prod()

# 在生产环境添加同步数据接口
@app.route('/api/roadmap/sync', methods=['GET'])
def sync_roadmap_data():
    """提供数据同步接口（仅在生产环境可用）"""
    return roadmap_service.sync_data()
# 添加NFC接口测试页面路由


@app.route('/nfc_test')
def nfc_test():
    return render_template('nfc_test.html')

def complete_task(cursor, player_id, task_id, task_info, current_time):
    """
    完成任务并处理奖励
    
    Args:
        cursor: 数据库游标
        player_id: 玩家ID
        task_id: 任务ID
        task_info: 任务信息字典
        current_time: 当前时间戳
    
    Returns:
        tuple: (success, message, rewards_summary)
        - success: 布尔值，表示是否成功
        - message: 字符串，处理结果消息
        - rewards_summary: 字典，奖励处理摘要
    """
    try:
        # 1. 更新任务状态
        cursor.execute('''
            UPDATE player_task 
            SET status = 'COMPLETE', 
                complete_time = ?
            WHERE player_id = ? AND task_id = ?
        ''', (current_time, player_id, task_id))
        
        rewards = task_info.get('rewards', {})
        rewards_summary = {
            'points': 0,
            'exp': 0,
            'cards': [],
            'medals': []
        }
        
        # 2. 处理积分和经验奖励
        if rewards.get('points', 0) > 0:
            # 获取当前积分
            cursor.execute('SELECT points FROM player_data WHERE player_id = ?', (player_id,))
            current_points = cursor.fetchone()['points']
            new_points = current_points + rewards['points']
            
            # 更新玩家积分
            cursor.execute('''
                UPDATE player_data 
                SET points = ? 
                WHERE player_id = ?
            ''', (new_points, player_id))
            
            # 记录积分变动
            cursor.execute('''
                INSERT INTO points_record (
                    player_id, number, addtime, total
                ) VALUES (?, ?, ?, ?)
            ''', (player_id, rewards['points'], current_time, new_points))
            
            rewards_summary['points'] = rewards['points']
        
        if rewards.get('exp', 0) > 0:
            # 获取当前经验
            cursor.execute('SELECT experience FROM player_data WHERE player_id = ?', (player_id,))
            current_exp = cursor.fetchone()['experience']
            new_exp = current_exp + rewards['exp']
            
            # 更新玩家经验
            cursor.execute('''
                UPDATE player_data 
                SET experience = ? 
                WHERE player_id = ?
            ''', (new_exp, player_id))
            
            # 记录经验变动
            cursor.execute('''
                INSERT INTO exp_record (
                    player_id, number, addtime, total
                ) VALUES (?, ?, ?, ?)
            ''', (player_id, rewards['exp'], current_time, new_exp))
            
            rewards_summary['exp'] = rewards['exp']
        
        # 3. 处理卡片奖励
        for card in rewards.get('cards', []):
            card_id = card.get('id')
            if not card_id:
                continue
                
            cursor.execute('''
                SELECT * FROM player_game_card 
                WHERE player_id = ? AND game_card_id = ?
            ''', (player_id, card_id))
            existing_card = cursor.fetchone()
            
            if existing_card:
                # 更新卡片数量
                cursor.execute('''
                    UPDATE player_game_card 
                    SET number = number + 1,
                        timestamp = ?
                    WHERE player_id = ? AND game_card_id = ?
                ''', (current_time, player_id, card_id))
            else:
                # 添加新卡片
                cursor.execute('''
                    INSERT INTO player_game_card (
                        player_id, game_card_id, number, timestamp
                    ) VALUES (?, ?, 1, ?)
                ''', (player_id, card_id, current_time))
            
            rewards_summary['cards'].append(card_id)
        
        # 4. 处理勋章奖励
        for medal in rewards.get('medals', []):
            medal_id = medal.get('id')
            if not medal_id:
                continue
                
            cursor.execute('''
                SELECT * FROM player_medal 
                WHERE player_id = ? AND medal_id = ?
            ''', (player_id, medal_id))
            
            if not cursor.fetchone():
                cursor.execute('''
                    INSERT INTO player_medal (
                        player_id, medal_id, addtime
                    ) VALUES (?, ?, ?)
                ''', (player_id, medal_id, current_time))
                
                rewards_summary['medals'].append(medal_id)
        
        return True, "任务完成，奖励已发放", rewards_summary
        
    except Exception as e:
        print(f"完成任务时出错: {str(e)}")
        raise

def setup_logging():
    """配置日志系统"""
    log_level = logging.DEBUG if DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('server.log')
        ]
    )
    return logging.getLogger(__name__)

    # 在应用启动时调用
if __name__ == '__main__':
    logger = setup_logging()
    logger.info("Starting server initialization...")
    
    try:
        start_scheduler()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}", exc_info=True)
    
    logger.info(f"Server configuration - IP: {SERVER_IP}, Port: {PORT}, Debug: {DEBUG}")
    
    try:
        if DEBUG:
            # 开发环境：使用 eventlet（支持热重载和WebSocket）
            logger.info("Starting development server with eventlet...")
            socketio.run(
            app,
                host=SERVER_IP,
                port=PORT,
            debug=True,
            use_reloader=True,
            log_output=True
        )
        else:
            # 生产环境：使用 waitress
            from waitress import serve
            from paste.translogger import TransLogger
            
            logger.info("Starting production server with waitress...")
            # 使用 TransLogger 记录访问日志
            app_logged = TransLogger(app)
            
            # 配置 waitress
            serve(
                app_logged,
                host=SERVER_IP,
                port=PORT,
                threads=WAITRESS_CONFIG['THREADS'],               
                connection_limit=WAITRESS_CONFIG['CONNECTION_LIMIT'],   
                channel_timeout=WAITRESS_CONFIG['TIMEOUT'],      
                cleanup_interval=WAITRESS_CONFIG['CLEANUP_INTERVAL'],     
                ident=WAITRESS_CONFIG['IDENT']      
            )
            
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}", exc_info=True)
        raise



