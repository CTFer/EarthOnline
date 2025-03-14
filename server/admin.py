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
from config.config import ENV
from utils.response_handler import ResponseHandler, StatusCode, api_response  # 添加这行导入
import logging
if ENV == 'local':
    from function.NFC_Device import NFC_Device
from function.AdminService import admin_service
import threading
from function.NotificationService import notification_service
from function.MedalService import medal_service
from function.TaskService import task_service
from function.SkillService import skill_service
from function.NFCService import nfc_service
from function.GameCardService import game_card_service

# 配置日志
logger = logging.getLogger(__name__)

# 创建蓝图
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
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


def setup_logging():
    """设置日志配置"""
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

setup_logging()

# 路由处理
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash("用户名和密码不能为空")
            return render_template('admin_login.html')

        result = admin_service.login(username, password)
        if result['code'] == 0:
            logger.info(f"管理员 {username} 登录成功")
            next_url = request.args.get('next') or url_for('admin.index')
            return redirect(next_url)
        else:
            logger.warning(f"管理员 {username} 登录失败: {result['msg']}")
            flash(result['msg'])

    return render_template('admin_login.html')


@admin_bp.route('/logout')
def logout():
    """管理员登出"""
    username = session.get('username')
    result = admin_service.logout()
    logger.info(f"管理员 {username} 登出")
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@admin_service.admin_required
def index():
    """管理后台首页"""
    return render_template('admin.html')


@admin_bp.route('/api/players', methods=['GET'])
@admin_service.admin_required
@api_response
def get_players():
    """获取所有玩家"""
    logger.info("获取玩家列表")
    return player_service.get_players()


@admin_bp.route('/api/players/<int:player_id>', methods=['POST'])
@admin_service.admin_required
@api_response
def update_player(player_id):
    """更新玩家信息"""
    data = request.get_json()
    logger.info(f"更新玩家信息: {player_id}")
    return player_service.update_player(player_id, data)


@admin_bp.route('/api/players/<int:player_id>', methods=['DELETE'])
@admin_service.admin_required
@api_response
def delete_player(player_id):
    """删除玩家"""
    logger.info(f"删除玩家: {player_id}")
    return player_service.delete_player(player_id)


@admin_bp.route('/api/players/<int:player_id>', methods=['GET'])
@admin_service.admin_required
@api_response
def get_player(player_id):
    """获取单个玩家信息"""
    logger.info(f"获取玩家信息: {player_id}")
    return player_service.get_player(player_id)


@admin_bp.route('/api/addplayer', methods=['POST'])
@admin_service.admin_required
@api_response
def add_player():
    """添加新玩家"""
    data = request.get_json()
    logger.info("添加新玩家")
    return player_service.add_player(data)


# API路由
@admin_bp.route('/api/users', methods=['GET'])
@admin_service.admin_required
@api_response
def get_users():
    """获取所有用户"""
    logger.info("获取用户列表")
    return admin_service.get_users()


@admin_bp.route('/api/adduser', methods=['POST'])
@admin_service.admin_required
@api_response
def add_user():
    """添加新用户"""
    data = request.get_json()
    logger.info("添加新用户")
    return admin_service.add_user(data)


@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
@admin_service.admin_required
@api_response
def get_user(user_id):
    """获取指定用户"""
    logger.info(f"获取用户信息: {user_id}")
    return admin_service.get_user(user_id)


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_service.admin_required
@api_response
def update_user(user_id):
    """更新用户信息"""
    data = request.get_json()
    logger.info(f"更新用户信息: {user_id}")
    return admin_service.update_user(user_id, data)


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_service.admin_required
@api_response
def delete_user(user_id):
    """删除用户"""
    logger.info(f"删除用户: {user_id}")
    return admin_service.delete_user(user_id)


@admin_bp.route('/api/skills', methods=['GET'])
@admin_service.admin_required
@api_response
def get_skills():
    """获取所有技能"""
    return skill_service.get_skills()


@admin_bp.route('/api/skills', methods=['POST'])
@admin_service.admin_required
@api_response
def add_skill():
    """添加新技能"""
    data = request.get_json()
    return skill_service.add_skill(data)


@admin_bp.route('/api/skills/<int:skill_id>', methods=['GET'])
@admin_service.admin_required
@api_response
def get_skill(skill_id):
    """获取指定技能"""
    return skill_service.get_skill(skill_id)


@admin_bp.route('/api/skills/<int:skill_id>', methods=['PUT'])
@admin_service.admin_required
@api_response
def update_skill(skill_id):
    """更新技能"""
    data = request.get_json()
    return skill_service.update_skill(skill_id, data)


@admin_bp.route('/api/skills/<int:skill_id>', methods=['DELETE'])
@admin_service.admin_required
@api_response
def delete_skill(skill_id):
    """删除技能"""
    return skill_service.delete_skill(skill_id)


@admin_bp.route('/api/tasks', methods=['GET'])
@admin_service.admin_required
@api_response
def get_tasks():
    """获取任务列表"""
    page = request.args.get('page', type=int)
    limit = request.args.get('limit', type=int)
    return task_service.get_tasks(page=page, limit=limit)

@admin_bp.route('/api/tasks/<int:task_id>', methods=['GET'])
@admin_service.admin_required
@api_response
def get_task(task_id):
    """获取单个任务信息"""
    return task_service.get_task(task_id)

@admin_bp.route('/api/tasks', methods=['POST'])
@admin_service.admin_required
@api_response
def add_task():
    """添加新任务"""
    data = request.get_json()
    return task_service.add_task(data)

@admin_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@admin_service.admin_required
@api_response
def update_task(task_id):
    """更新任务"""
    data = request.get_json()
    return task_service.update_task(task_id, data)

@admin_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@admin_service.admin_required
@api_response
def delete_task(task_id):
    """删除任务"""
    return task_service.delete_task(task_id)

# 添加任务管理页面路由


@admin_bp.route('/tasks')
@admin_service.admin_required
def task_manage():
    """任务管理页面"""
    return render_template('task_manage.html')

# 任务管理页面路由


@admin_bp.route('/player_tasks')
@admin_service.admin_required
def player_task_manage():
    """用户任务管理页面"""
    return render_template('player_task_manage.html')

# Player Task API路由


@admin_bp.route('/api/player_tasks', methods=['GET'])
@admin_service.admin_required
@api_response
def get_player_tasks():
    """获取玩家任务列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    return task_service.get_player_tasks(page=page, limit=limit)

@admin_bp.route('/api/player_tasks/<int:task_id>', methods=['GET'])
@admin_service.admin_required
@api_response
def get_player_task(task_id):
    """获取单个玩家任务信息"""
    return task_service.get_player_task(task_id)

@admin_bp.route('/api/player_tasks', methods=['POST'])
@admin_service.admin_required
@api_response
def create_player_task():
    """创建玩家任务"""
    data = request.get_json()
    return task_service.create_player_task(data)

@admin_bp.route('/api/player_tasks/<int:task_id>', methods=['PUT'])
@admin_service.admin_required
@api_response
def update_player_task(task_id):
    """更新玩家任务"""
    data = request.get_json()
    return task_service.update_player_task(task_id, data)

@admin_bp.route('/api/player_tasks/<int:task_id>', methods=['DELETE'])
@admin_service.admin_required
@api_response
def delete_player_task(task_id):
    """删除玩家任务"""
    return task_service.delete_player_task(task_id)

# 勋章管理API路由
@admin_bp.route('/api/medals', methods=['GET'])
@admin_service.admin_required
def get_medals():
    """获取勋章列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    return jsonify(medal_service.get_medals(page, limit))

@admin_bp.route('/api/medals/<int:medal_id>', methods=['GET'])
@admin_service.admin_required
def get_medal(medal_id):
    """获取单个勋章信息"""
    return jsonify(medal_service.get_medal(medal_id))

@admin_bp.route('/api/medals', methods=['POST'])
@admin_service.admin_required
def create_medal():
    """创建新勋章"""
    data = request.get_json()
    return jsonify(medal_service.create_medal(data))

@admin_bp.route('/api/medals/<int:medal_id>', methods=['PUT'])
@admin_service.admin_required
def update_medal(medal_id):
    """更新勋章信息"""
    data = request.get_json()
    return jsonify(medal_service.update_medal(medal_id, data))

@admin_bp.route('/api/medals/<int:medal_id>', methods=['DELETE'])
@admin_service.admin_required
def delete_medal(medal_id):
    """删除勋章"""
    return jsonify(medal_service.delete_medal(medal_id))

@admin_bp.route('/api/medal_img', methods=['GET'])
@admin_service.admin_required
def medal_img():
    """返回勋章图标列表"""
    icons = medal_service.get_icon_list()
    return jsonify({
        'code': 0,
        'msg': '',
        'data': icons
    })

# NFC卡管理相关路由
@admin_bp.route('/api/nfc/cards', methods=['GET'])
@admin_service.admin_required
@api_response
def get_nfc_cards():
    """获取NFC卡片列表"""
    return nfc_service.get_nfc_cards()

@admin_bp.route('/api/nfc/cards', methods=['POST'])
@admin_service.admin_required
@api_response
def create_nfc_card():
    """创建新NFC卡片"""
    data = request.get_json()
    return nfc_service.create_nfc_card(data)

@admin_bp.route('/api/nfc/cards/<int:card_id>', methods=['PUT'])
@admin_service.admin_required
@api_response
def update_nfc_card(card_id):
    """更新NFC卡片"""
    data = request.get_json()
    return nfc_service.update_nfc_card(card_id, data)

@admin_bp.route('/api/nfc/cards/<int:card_id>', methods=['DELETE'])
@admin_service.admin_required
@api_response
def delete_nfc_card(card_id):
    """删除NFC卡片"""
    return nfc_service.delete_nfc_card(card_id)

@admin_bp.route('/api/nfc/next_card_id', methods=['GET'])
@admin_service.admin_required
@api_response
def get_next_card_id():
    """获取下一个可用的NFC卡片ID"""
    return nfc_service.get_next_card_id()

@admin_bp.route('/api/nfc/card_status/<int:card_id>', methods=['GET'])
@admin_service.admin_required
@api_response
def get_card_status(card_id):
    """获取指定NFC卡片的状态"""
    return nfc_service.get_card_status(card_id)

# NFC硬件设备相关路由
@admin_bp.route('/api/nfc/hardware/status')
@admin_service.admin_required
@api_response
def get_nfc_hardware_status():
    """获取NFC硬件设备状态"""
    return nfc_service.get_hardware_status()

@admin_bp.route('/api/nfc/hardware/read', methods=['POST'])
@admin_service.admin_required
@api_response
def read_nfc_hardware():
    """读取NFC实体卡片"""
    return nfc_service.read_hardware()

@admin_bp.route('/api/nfc/hardware/write', methods=['POST'])
@admin_service.admin_required
@api_response
def write_nfc_hardware():
    """写入NFC实体卡片"""
    data = request.get_json()
    return nfc_service.write_hardware(data)

@admin_bp.route('/api/game_cards', methods=['GET'])
@admin_service.admin_required
@api_response
def get_game_cards():
    """获取所有道具卡"""
    return game_card_service.get_game_cards()

# 通知管理接口
@admin_bp.route('/api/notifications', methods=['GET'])
@admin_service.admin_required
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
@admin_service.admin_required
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
@admin_service.admin_required
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
@admin_service.admin_required
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
@admin_service.admin_required
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

@admin_bp.before_request
def before_request():
    """请求预处理：检查认证状态"""
    # 检查是否需要登录（除了登录页面）
    if request.endpoint != 'admin.login' and not session.get('is_admin'):
        return ResponseHandler.redirect(url_for('admin.login'))
    return None

if __name__ == '__main__':
    socketio.run(app, debug=True)
