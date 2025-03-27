# -*- coding: utf-8 -*-
import eventlet
eventlet.monkey_patch()

# 正确导入wsgi模块
from eventlet import wsgi
from eventlet import listen

# 配置wsgi参数
wsgi.MAX_HEADER_LINE = 65536  # 增加最大请求头大小
wsgi.MINIMUM_CHUNK_SIZE = 16384  # 优化块大小
wsgi.MAX_REQUEST_LINE = 16384  # 优化请求行大小

import traceback
import uuid
import json
import sys
from functools import wraps
import time as time_module
import threading
from datetime import datetime, time, timedelta
import os
import sqlite3
import logging
from flask import Flask, request, redirect, send_from_directory, make_response, render_template, jsonify, session
from config.config import (
    SERVER_IP, 
    PORT, 
    DEBUG, 
    WAITRESS_CONFIG, 
    ENV,
    PROD_SERVER,  # 添加这行
    SSL_CERT_DIR,
    SSL_KEY_FILE,
    HTTPS_PORT,
    HTTPS_ENABLED,
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    CLOUDFLARE,
    SECURITY,
    DOMAIN
)

# 首先导入服务器管理服务
from function.ServerService import server_service  # 导入服务器管理服务
from utils.LogService import log_service  # 导入日志服务

# 创建 Flask 应用实例
app = Flask(__name__, static_folder='static')

# 立即应用服务器配置
app = server_service.configure_app(app)
logger = log_service.setup_logging(DEBUG)

# 导入其他依赖
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from admin import admin_bp
from shop import shop_bp  # 确保在同一目录下
from function.PlayerService import player_service
from function.TaskService import task_service
from function.GPSService import gps_service
from function.RoadmapService import roadmap_service
from function.WeChatService import wechat_service
from function.SchedulerService import scheduler_service  # 导入调度器服务
from function.WebSocketService import websocket_service
from config.private import AMAP_SECURITY_JS_CODE, WECHAT_TOKEN, WECHAT_ENCODING_AES_KEY, WECHAT_APP_ID
import requests
from function.NotificationService import notification_service
from function.MedalService import medal_service
from function.GameCardService import game_card_service
from utils.response_handler import ResponseHandler, StatusCode, api_response
from wechat import wechat_bp  # 导入微信蓝图
from function.SecurityService import security_service
from function.RateLimitService import rate_limit_service
from lxml import etree

# 初始化 Flask 应用设置
logger.info(f"Flask应用初始化完成，Session配置: {app.config.get('SESSION_COOKIE_NAME')}, {app.config.get('SESSION_COOKIE_DOMAIN')}, {app.config.get('SESSION_COOKIE_SECURE')}")

# 注册蓝图
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(shop_bp)
app.register_blueprint(wechat_bp, url_prefix='/wechat')

# 初始化WebSocket服务
websocket_service.init_app(app)

# 配置 SocketIO
socketio = websocket_service.socketio

# 初始化日志服务的WebSocket
log_service.init_websocket(websocket_service)

# 为所有现有路由添加日志装饰器
app.view_functions = {
    endpoint: log_service.log_request(func)
    for endpoint, func in app.view_functions.items()
}

# 添加模板目录配置
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

# 注意：不再需要重复定义WebSocket事件处理器，因为它们已经在WebSocketService中定义
# 以下是其他API路由

# 添加玩家登录路由
@app.route('/api/player/login', methods=['POST'])
def player_login():
    """玩家登录"""
    try:
        data = request.get_json()
        return player_service.login(data.get('player_id'), data.get('password'))
    except Exception as e:
        logger.error(f"登录失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.LOGIN_FAILED,
            msg=f"登录失败: {str(e)}"
        )

@app.route('/api/player/logout', methods=['POST'])
def player_logout():
    """玩家登出"""
    return player_service.logout()
@app.route('/api/player/check_login', methods=['GET'])
def check_login():
    """检查玩家登录状态"""
    response = player_service.check_login()
    if response:
        return ResponseHandler.success(
            code=StatusCode.SUCCESS,
            msg="已登录",
            data={
                "is_player": True,
                "player_id": response
            }
        )
    else:
        return ResponseHandler.error(
            code=StatusCode.UNAUTHORIZED,
            msg="未登录"
        )

# 修改需要认证的路由，添加 @player_required 装饰器
@app.route('/api/player/<int:player_id>', methods=['GET'])
@api_response
def get_player_api(player_id):
    """获取角色信息"""
    return player_service.get_player(player_id)

@app.route('/api/get_players', methods=['GET'])
@api_response
def get_players():
    """获取所有玩家"""
    return player_service.get_players()

@app.route('/api/tasks/available/<int:player_id>', methods=['GET'])
@api_response
def get_available_tasks(player_id):
    """获取可用任务列表"""
    return task_service.get_available_tasks(player_id)

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
@api_response
def get_task_by_id(task_id):
    """获取任务详情"""
    return task_service.get_task_by_id(task_id)

# 添加获取玩家当前任务的API
@app.route('/api/tasks/current_detail/<int:task_id>', methods=['GET'])
def get_current_task_by_id(task_id):
    """获取当前任务详情"""
    return task_service.get_current_task_by_id(task_id)

@app.route('/api/tasks/current/<int:player_id>', methods=['GET'])
@api_response
def get_current_tasks(player_id):
    """获取用户当前未过期的任务列表"""
    return task_service.get_current_tasks(player_id)

@app.route('/api/tasks/accept', methods=['POST'])
@player_service.player_required
@api_response
def accept_task():
    """接受任务接口"""
    try:
        data = request.get_json()
        logger.info(f"[TaskAPI] 收到接受任务请求: {data}")
        
        # 验证请求数据
        if not data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg='无效的请求数据'
            )
            
        # 检查必要字段
        required_fields = ['player_id', 'task_id']
        for field in required_fields:
            if field not in data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg=f'缺少必要参数: {field}'
                )
        
        # 调用任务服务
        logger.debug(f"[TaskAPI] 开始处理任务接受请求 - 玩家ID: {data['player_id']}, 任务ID: {data['task_id']}")
        result = task_service.accept_task(data['player_id'], data['task_id'])
        logger.info(f"[TaskAPI] 任务接受处理完成: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"[TaskAPI] 处理任务接受请求时发生错误: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=f'处理任务请求失败: {str(e)}'
        )

@app.route('/api/tasks/abandon', methods=['POST'])
@player_service.player_required
@api_response
def abandon_task():
    """放弃任务接口"""
    try:
        data = request.get_json()
        logger.info(f"[TaskAPI] 收到放弃任务请求: {data}")
        
        # 验证请求数据
        if not data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg='无效的请求数据'
            )
            
        # 检查必要字段
        required_fields = ['player_id', 'task_id']
        for field in required_fields:
            if field not in data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg=f'缺少必要参数: {field}'
                )
        
        # 调用任务服务
        logger.debug(f"[TaskAPI] 开始处理任务放弃请求 - 玩家ID: {data['player_id']}, 任务ID: {data['task_id']}")
        result = task_service.abandon_task(data['player_id'], data['task_id'])
        logger.info(f"[TaskAPI] 任务放弃处理完成: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"[TaskAPI] 处理任务放弃请求时发生错误: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=f'处理任务请求失败: {str(e)}'
        )

@app.route('/api/tasks/submit', methods=['POST'])
@player_service.player_required
@api_response
def submit_task_api():
    """提交任务接口"""
    try:
        data = request.get_json()
        logger.info(f"[TaskAPI] 收到提交任务请求: {data}")

        # 检查必要字段
        required_fields = ['player_id', 'task_id']
        for field in required_fields:
            if field not in data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg=f'缺少必要参数: {field}'
                )
        
        # 调用任务服务
        logger.debug(f"[TaskAPI] 开始处理任务提交请求 - 玩家ID: {data['player_id']}, 任务ID: {data['task_id']}")
        result = task_service.submit_task(data['player_id'], data['task_id'])
        logger.info(f"[TaskAPI] 任务提交处理完成: {result}")
        return result

    except Exception as e:
        logger.error(f"[TaskAPI] 处理任务提交请求时发生错误: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=f'处理任务请求失败: {str(e)}'
        )

@app.route('/api/tasks/complete', methods=['POST'])
@player_service.player_required
@api_response
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

        # 使用日志服务获取过滤后的日志
        filtered_logs = log_service.get_request_logs(method_filter, path_filter)

        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()

        # 生成请求记录HTML
        logs_html = ''
        for log in filtered_logs:
            logs_html += log_service.format_log_entry(log)

        # 替换模板中的占位符
        html = template.replace('{{request_logs}}', logs_html)
        return html

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}", 500

@app.route('/')
@app.route('/shop')
def spa_index():
    """单页应用入口"""
    return render_template('/client/base.html')

# API路由 - 获取模板片段
@app.route('/api/templates/<template_name>')
def get_template(template_name):
    """获取模板片段
    
    Args:
        template_name: 模板名称，如 home, shop 等
    """
    try:
        # 安全检查：确保template_name不包含目录遍历
        if '..' in template_name or template_name.startswith('/'):
            return "非法的模板名称", 400
            
        template_path = os.path.join(TEMPLATE_DIR, f'client/{template_name}.html')
        if not os.path.exists(template_path):
            return "模板不存在", 404
            
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取模板失败: {str(e)}")
        return "模板加载失败", 500

@app.route('/clear-logs', methods=['POST'])
def clear_logs():
    """清除所有请求日志"""
    log_service.clear_logs()
    return redirect('/')

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
    """提供静态文件访问"""
    try:
        # 对于 .well-known 路径的请求，使用专门的处理
        if path.startswith('.well-known/acme-challenge/'):
            token = path.split('/')[-1]
            return acme_challenge(token)
        return send_from_directory('static', path)
    except Exception as e:
        logger.error(f"Error serving static file: {str(e)}")
        return jsonify(ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=f"服务器错误: {str(e)}"
        ))

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
        
        # 获取必要参数（不区分大小写）
        card_id = data.get('CARD_ID') or data.get('card_id')
        player_id = data.get('PLAYER_ID') or data.get('player_id')
        device = data.get('DEVICE') or data.get('device', 'unknown')
        timestamp = data.get('TIMESTAMP') or data.get('timestamp')
        value = data.get('VALUE') or data.get('value')
        card_type = data.get('TYPE') or data.get('type')

        # 参数验证
        if not card_id or not player_id:
            error_msg = '缺少必要参数: CARD_ID 或 PLAYER_ID'
            print(f"[NFC API Debug] 错误: {error_msg}")
            print(f"[NFC API Debug] 收到的数据: card_id={card_id}, player_id={player_id}")
            return json.dumps({
                'code': 400,
                'msg': error_msg,
                'data': None
            }), 400

        print(f"[NFC API Debug] 卡片ID: {card_id}")
        print(f"[NFC API Debug] 玩家ID: {player_id}")
        print(f"[NFC API Debug] 设备: {device}")
        print(f"[NFC API Debug] 时间戳: {timestamp}")
        print(f"[NFC API Debug] 值: {value}")
        print(f"[NFC API Debug] 类型: {card_type}")

        # 调用 NFC 服务处理
        from function.NFCService import nfc_service
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

@app.route('/api/gps/sync', methods=['GET'])
@api_response
def sync_gps_records():
    """提供GPS数据同步接口"""
    try:
        limit = request.args.get('limit', 1000, type=int)
        return gps_service.get_latest_gps_records(limit)
    except Exception as e:
        logger.error(f"[GPS] 同步GPS记录失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.GPS_SYNC_FAILED,
            msg=f'同步GPS记录失败: {str(e)}'
        )

@app.route('/api/gps', methods=['POST'])
@api_response
def add_gps():
    """添加GPS记录,针对macroDroid"""
    try:
        data = json.loads(request.data)
        print(f"[GPS] 获取到数据: {data}") 
        location = data.get('location', '')
        player_id = data.get('player_id')
        
        # 分割经纬度数据
        try:
            latitude, longitude = map(float, location.split(','))
        except (ValueError, AttributeError):
            return ResponseHandler.error(
                code=StatusCode.GPS_DATA_INVALID,
                msg='无效的位置数据格式'
            )
            
        # 将WGS84坐标转换为GCJ02坐标（高德地图坐标系）
        try:
            longitude, latitude = gps_service.wgs84_to_gcj02(longitude, latitude)
            print(f"[GPS] 坐标转换结果 - 经度: {longitude}, 纬度: {latitude}")
        except Exception as e:
            print(f"[GPS] 坐标转换失败: {str(e)}")
            # 即使转换失败也继续使用原始坐标
            pass

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
        response_data = gps_service.add_gps(gps_data)
        print(f"[GPS] 添加GPS记录结果: {response_data}")
        
        # 只有在新增GPS记录时才发送 WebSocket 通知
        if (response_data['code'] == 0 and 
            response_data['msg'] == '添加GPS记录成功' and 
            player_id):
            # 添加完整的GPS数据到推送数据中
            socket_data = {
                'x': longitude,
                'y': latitude,
                'player_id': player_id,
                'device': gps_data['device'],
                'remark': gps_data['remark'],
                'speed': gps_data['speed'],
                'battery': data.get('battery', 0),
                'timestamp': timestamp,
                'accuracy': gps_data['accuracy'],
                'id': response_data['data']['id']  # 添加记录ID
            }
            
            print(f"[GPS] 发送新GPS点位更新通知: {socket_data}")
            socketio.emit('gps_update', socket_data, room=f'user_{player_id}')
        else:
            # 更新时间的情况
            socket_data = {
                'speed': gps_data['speed'],
                'battery': data.get('battery', 0),
                'timestamp': timestamp,
                'accuracy': gps_data['accuracy'],
                'id': response_data['data']['id']  # 添加记录ID
            }
            print(f"[GPS] 仅更新时间，发送电量、速度、更新时间：{socket_data}")
            socketio.emit('gps_update', socket_data, room=f'user_{player_id}')
        return response_data

    except Exception as e:
        logger.error(f"处理GPS数据失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.GPS_DATA_INVALID,
            msg=f'处理GPS数据失败: {str(e)}'
        )

@app.route('/api/gps/<int:gps_id>', methods=['GET'])
def get_gps(gps_id):
    """获取单个GPS记录"""
    return gps_service.get_gps(gps_id)

@app.route('/api/gps/player/<int:player_id>', methods=['GET'])
def get_player_gps(player_id):
    """获取玩家GPS记录"""
    return gps_service.get_player_gps(player_id)

@app.route('/api/gps/<int:gps_id>', methods=['PUT'])
@player_service.player_required
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
    """装饰器：同步数据库操作到生产环境"""
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
                    
                    # 使用配置的请求头
                    prod_headers = {
                        **PROD_SERVER['HEADERS'],
                        'X-API-Key': PROD_SERVER['API_KEY']
                    }
                    
                    # 使用配置的SSL验证
                    ssl_config = {
                        'verify': PROD_SERVER['SSL_VERIFY'],
                        'timeout': PROD_SERVER['TIMEOUT']
                    }
                    
                    print(f"[Sync] Syncing {request.method} {request.path} to production")
                    print(f"[Sync] Target URL: {prod_url}")
                    print(f"[Sync] Headers: {prod_headers}")
                    
                    # 发送同步请求
                    sync_response = None
                    if request.method == 'POST':
                        sync_response = requests.post(
                            prod_url, 
                            json=request.get_json(), 
                            headers=prod_headers,
                            **ssl_config
                        )
                    elif request.method == 'PUT':
                        sync_response = requests.put(
                            prod_url, 
                            json=request.get_json(), 
                            headers=prod_headers,
                            **ssl_config
                        )
                    elif request.method == 'DELETE':
                        sync_response = requests.delete(
                            prod_url, 
                            headers=prod_headers,
                            **ssl_config
                        )
                    
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

# 在生产环境添加批量同步数据接口
@app.route('/api/roadmap/batch_sync', methods=['POST'])
def batch_sync_roadmap_data():
    """批量同步数据接口（仅在生产环境可用）"""
    data = request.get_json()
    return roadmap_service.batch_sync(data.get('updates', []))


# 通知相关接口
@app.route('/api/notifications', methods=['GET'])
@api_response
def get_notifications():
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
            
        return ResponseHandler.success(data=notifications)
    except Exception as e:
        return ResponseHandler.error(
            code=StatusCode.NOTIFICATION_NOT_FOUND,
            msg=str(e)
        )

@app.route('/api/notifications/<int:notification_id>', methods=['GET'])
@api_response
def get_notification(notification_id):
    """获取单个通知"""
    try:
        notification = notification_service.get_notification(notification_id)
        
        if not notification:
            return ResponseHandler.error(
                code=StatusCode.NOTIFICATION_NOT_FOUND,
                msg='通知不存在'
            )
        
        return ResponseHandler.success(data=notification)
    except Exception as e:
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=str(e)
        )

@app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
@api_response
def mark_notification_as_read(notification_id):
    """标记通知为已读"""
    try:
        success = notification_service.mark_as_read(notification_id)
        
        if success:
            return ResponseHandler.success(msg='标记成功')
        return ResponseHandler.error(
            code=StatusCode.NOTIFICATION_READ_ERROR,
            msg='标记失败'
        )
    except Exception as e:
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=str(e)
        )

@app.route('/api/notifications/unread/count', methods=['GET'])
@api_response
def get_unread_notifications_count():
    """获取未读通知数量"""
    try:
        target_type = request.args.get('target_type', 'all')
        target_id = request.args.get('target_id', type=int)
        
        count = notification_service.get_unread_count(
            target_type=target_type,
            target_id=target_id
        )
        
        return ResponseHandler.success(data=count)
    except Exception as e:
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=str(e)
        )

# WebSocket通知事件
@socketio.on('notification:read')
def handle_notification_read(data):
    """处理通知已读事件"""
    try:
        notification_id = data.get('notification_id')
        if not notification_id:
            return
        
        notification_service.mark_as_read(notification_id)
        
        # 广播通知状态更新
        emit('notification:update', {
            'id': notification_id,
            'is_read': True
        }, broadcast=True)
    except Exception as e:
        Logger.error('WebSocket', f'处理通知已读事件失败: {str(e)}')

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

@app.route('/reminder')
def reminder():
    """提词器页面"""
    return render_template('client/reminder.html')

@app.route('/api/amap/security-config')
def get_amap_security_config():
    """获取高德地图安全配置"""
    return jsonify({
        'securityJsCode': AMAP_SECURITY_JS_CODE
    })

# 勋章 词云相关接口
@app.route('/api/player/<int:player_id>/wordcloud', methods=['GET'])
def get_wordcloud(player_id):
    """获取词云数据 - 展示中的勋章"""
    return medal_service.get_wordcloud_medals(player_id)

# 获取勋章列表
@app.route('/api/medals', methods=['GET'])
@api_response
def get_medals():
    """获取勋章列表"""
    return medal_service.get_medals()

# 获取勋章详情
@app.route('/api/medals/<int:medal_id>', methods=['GET'])
@api_response
def get_medal(medal_id):
    """获取勋章详情"""
    return medal_service.get_medal(medal_id)
    
# GameCard相关接口
@app.route('/api/game_cards', methods=['GET'])
@api_response
def get_game_cards():
    """获取道具卡列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    return game_card_service.get_game_cards(page=page, limit=limit)

@app.route('/api/game_cards/<int:game_card_id>', methods=['GET'])
@api_response
def get_game_card(game_card_id):
    """获取单个道具卡信息"""
    return game_card_service.get_game_card(game_card_id)

@app.route('/api/task/approval/status', methods=['GET'])
@player_service.player_required
@api_response
def get_task_approval_status():
    """获取任务审批状态"""
    try:
        task_id = request.args.get('task_id')
        player_id = request.args.get('player_id')
        
        if not task_id or not player_id:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg='缺少必要参数: task_id 或 player_id'
            )
            
        # 转换为整数类型
        try:
            task_id = int(task_id)
            player_id = int(player_id)
        except ValueError:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg='参数类型错误: task_id 和 player_id 必须为整数'
            )
            
        logger.info(f"[TaskApprovalAPI] 获取任务审批状态 - 玩家ID: {player_id}, 任务ID: {task_id}")
        result = task_service.get_task_approval_status(task_id, player_id)
        return result
        
    except Exception as e:
        logger.error(f"[TaskApprovalAPI] 获取任务审批状态失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=f'获取任务审批状态失败: {str(e)}'
        )

@app.route('/api/task/approval/sync', methods=['POST'])
@player_service.player_required
@api_response
def sync_task_approval_status():
    """同步任务审批状态"""
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg='请求数据为空'
            )
            
        # 检查必要参数
        required_fields = ['task_id', 'player_id']
        for field in required_fields:
            if field not in data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg=f'缺少必要参数: {field}'
                )
                
        task_id = data['task_id']
        player_id = data['player_id']
        
        logger.info(f"[TaskApprovalAPI] 同步任务审批状态 - 玩家ID: {player_id}, 任务ID: {task_id}")
        result = task_service.sync_approval_status(task_id, player_id)
        return result
        
    except Exception as e:
        logger.error(f"[TaskApprovalAPI] 同步任务审批状态失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=f'同步任务审批状态失败: {str(e)}'
        )

@app.route('/api/test_session', methods=['GET'])
@api_response
def test_session():
    """测试 session 是否正常工作"""
    from flask import current_app
    # 设置测试值
    if 'test_count' not in session:
        session['test_count'] = 1
    else:
        session['test_count'] += 1
    session.modified = True
    
    # 收集状态信息
    return {
        'session_data': dict(session),
        'is_logged_in': bool(session.get('is_player', False)),
        'request_info': {
            'remote_addr': request.remote_addr,
            'host': request.host,
            'cookies': {k: v for k, v in request.cookies.items()},
            'user_agent': request.headers.get('User-Agent', ''),
            'method': request.method,
            'path': request.path
        },
        'session_config': {
            'cookie_name': current_app.config.get('SESSION_COOKIE_NAME'),
            'cookie_domain': current_app.config.get('SESSION_COOKIE_DOMAIN'),
            'cookie_secure': current_app.config.get('SESSION_COOKIE_SECURE'),
            'cookie_httponly': current_app.config.get('SESSION_COOKIE_HTTPONLY'),
            'cookie_samesite': current_app.config.get('SESSION_COOKIE_SAMESITE'),
            'permanent_lifetime': str(current_app.config.get('PERMANENT_SESSION_LIFETIME'))
        }
    }

@app.route('/debug_session', methods=['GET'])
def debug_session():
    """查看和修复当前 session"""
    # 当前 session 状态
    current_session = dict(session)
    
    # 请求信息
    request_info = {
        'remote_addr': request.remote_addr,
        'host': request.host,
        'user_agent': request.headers.get('User-Agent'),
        'referrer': request.referrer,
        'cookies': {k: v for k, v in request.cookies.items()}
    }
    
    # Flask 配置信息
    config_info = {
        'SESSION_COOKIE_DOMAIN': app.config.get('SESSION_COOKIE_DOMAIN'),
        'SESSION_COOKIE_SECURE': app.config.get('SESSION_COOKIE_SECURE'),
        'SESSION_COOKIE_HTTPONLY': app.config.get('SESSION_COOKIE_HTTPONLY'),
        'SESSION_COOKIE_SAMESITE': app.config.get('SESSION_COOKIE_SAMESITE'),
        'SESSION_COOKIE_PATH': app.config.get('SESSION_COOKIE_PATH'),
        'SECRET_KEY_SET': bool(app.secret_key)
    }
    
    # 创建简单的 HTML 页面
    html = f"""
    <html>
    <head><title>Session Debug</title></head>
    <body>
        <h2>当前 Session:</h2>
        <pre>{json.dumps(current_session, indent=4)}</pre>
        
        <h2>请求信息:</h2>
        <pre>{json.dumps(request_info, indent=4)}</pre>
        
        <h2>配置信息:</h2>
        <pre>{json.dumps(config_info, indent=4)}</pre>
        
        <h2>操作:</h2>
        <form method="post" action="/set_test_session">
            <button type="submit">设置测试 Session</button>
        </form>
        <form method="post" action="/clear_session">
            <button type="submit">清除 Session</button>
        </form>
    </body>
    </html>
    """
    
    return html

@app.route('/set_test_session', methods=['POST'])
def set_test_session():
    """设置测试 session 数据"""
    session['test_value'] = 'test_' + str(time_module.time())
    session.modified = True
    return redirect('/debug_session')

@app.route('/clear_session', methods=['POST'])
def clear_session():
    """清除 session 数据"""
    session.clear()
    return redirect('/debug_session')

@app.errorhandler(Exception)
def handle_error(e):
    """全局错误处理器"""
    error_id = str(uuid.uuid4())
    logger.error(f"未捕获的异常 [{error_id}]: {str(e)}", exc_info=True)
    
    error_response = {
        'code': StatusCode.SERVER_ERROR,
        'msg': f"服务器错误 (ID: {error_id})",
        'error': {
            'type': e.__class__.__name__,
            'message': str(e),
            'id': error_id
        }
    }
    
    if DEBUG:
        error_response['error']['traceback'] = traceback.format_exc()
    
    return jsonify(error_response), 500

@app.route('/.well-known/acme-challenge/<token>')
def acme_challenge(token):
    """处理 Let's Encrypt ACME 验证请求"""
    try:
        # 使用绝对路径
        acme_path = os.path.join(project_root, 'static', '.well-known', 'acme-challenge', token)
        logger.info(f"查找ACME验证文件: {acme_path}")
        
        if os.path.exists(acme_path):
            with open(acme_path, 'r') as f:
                content = f.read().strip()
            logger.info(f"成功读取ACME验证文件内容: {content}")
            return content, 200, {'Content-Type': 'text/plain'}
        else:
            logger.error(f"找不到ACME验证文件: {acme_path}")
            # 列出目录内容以帮助调试
            challenge_dir = os.path.join(project_root, 'static', '.well-known', 'acme-challenge')
            if os.path.exists(challenge_dir):
                files = os.listdir(challenge_dir)
                logger.info(f"验证目录中的文件: {files}")
            return 'Not Found', 404
    except Exception as e:
        logger.error(f"处理ACME验证请求时出错: {str(e)}", exc_info=True)
        return 'Internal Server Error', 500

# 在全局错误处理之前添加
@app.errorhandler(404)
def handle_404(e):
    """处理404错误"""
    return security_service.handle_404(e)

# 添加 HTTP 请求前置处理器
@app.before_request
def before_request():
    """请求预处理"""
    # 添加 session 调试信息
    if '/api/' in request.path and request.method != 'OPTIONS':
        logger.debug(f"请求: {request.path}, IP: {request.remote_addr}, Session: {dict(session)}")
    
    # 速率限制检查
    if SECURITY['rate_limit']['enabled'] and not request.path.startswith(('/static/', '/.well-known/')):
        limiter_result = rate_limit_service.handle_rate_limit(request)
        if limiter_result is not None:  # 确保返回不是 None
            return limiter_result
    
    # 安全检查
    security_result = security_service.security_check()
    if security_result is not None:  # 确保返回不是 None
        return security_result
    
    # 所有检查都通过，不返回任何内容，继续处理请求

# 添加 HTTP 请求后置处理器
@app.after_request
def after_request(response):
    """响应后处理"""
    # 添加安全响应头
    response = security_service.add_security_headers(response)
    return response

@app.route('/test/nfc')
def nfc_test():
    """NFC测试页面"""
    return render_template('nfc.html')


if __name__ == '__main__':
    logger.info("开始初始化服务器...")
    
    try:
        # 启动调度器服务
        scheduler_service.start()
        logger.info("调度器服务启动成功")
    except Exception as e:
        logger.error(f"调度器服务启动失败: {str(e)}", exc_info=True)
        sys.exit(1)
    
    logger.info(f"服务器配置 - IP: {SERVER_IP}, 端口: {'%d(HTTPS)' % HTTPS_PORT if HTTPS_ENABLED else '%d(HTTP)' % PORT}, 调试模式: {DEBUG}")
    
    try:
        # 使用 ServerService 启动服务器，它会应用所有配置
        socketio = SocketIO(app, cors_allowed_origins="*")
        server_service.start_server(app, socketio)
        
    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭服务器...")
    except Exception as e:
        logger.error(f"服务器启动失败: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        try:
            # 停止服务
            scheduler_service.stop()
            server_service.stop()
            logger.info("服务器关闭完成")
        except Exception as e:
            logger.error(f"服务器关闭时发生错误: {str(e)}", exc_info=True)
        sys.exit(0)
