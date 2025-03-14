"""
WebSocket服务模块
处理WebSocket连接和实时通信
"""
import logging
from flask_socketio import SocketIO, emit, join_room, leave_room
from typing import Dict, Any, Optional
from config.config import CLOUDFLARE, ENV, DOMAIN
import time

logger = logging.getLogger(__name__)

class WebSocketService:
    """WebSocket服务类"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(WebSocketService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """初始化WebSocket服务"""
        if not hasattr(self, 'initialized'):
            # 优化的WebSocket配置
            socketio_config = {
                'cors_allowed_origins': '*',
                'async_mode': 'eventlet',
                'ping_timeout': 10,  # 减少ping超时时间
                'ping_interval': 25,  # 适当增加ping间隔
                'max_http_buffer_size': 10e6,  # 限制缓冲区大小为10MB
                'manage_session': False,  # 禁用会话管理以提高性能
                'transports': ['websocket'],  # 只使用websocket传输
                'always_connect': True,  # 保持连接
                'async_handlers': True,  # 异步处理
                'message_queue_maxsize': 10000,  # 消息队列最大大小
                'engineio_logger': False  # 关闭引擎日志
            }
            
            logger.info("[WebSocket] 开始初始化WebSocket服务")
            logger.info(f"[WebSocket] 使用配置: {socketio_config}")
            
            self.socketio = SocketIO(**socketio_config)
            self.initialized = True
            logger.info("[WebSocket] WebSocket服务初始化完成")
            
    def init_app(self, app):
        """将WebSocket服务与Flask应用关联"""
        self.socketio.init_app(app)
        
    def _register_handlers(self) -> None:
        """注册WebSocket事件处理器"""
        @self.socketio.on('connect')
        def handle_connect():
            """处理WebSocket连接"""
            client_info = {
                'sid': request.sid,
                'remote_addr': request.remote_addr,
                'headers': dict(request.headers),
                'transport': request.args.get('transport', 'unknown'),
                'protocol': request.args.get('protocol', 'unknown')
            }
            logger.info(f"[WebSocket] 客户端连接成功: {client_info}")
            emit('connected', {'status': 'success', 'client_info': client_info})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """处理WebSocket断开连接"""
            logger.info(f"[WebSocket] 客户端断开连接: {request.sid}")

        @self.socketio.on_error()
        def handle_error(e):
            """处理WebSocket错误"""
            error_info = {
                'sid': request.sid if hasattr(request, 'sid') else 'unknown',
                'error': str(e),
                'event': request.event.get('message', 'unknown') if hasattr(request, 'event') else 'unknown'
            }
            logger.error(f"[WebSocket] 发生错误: {error_info}", exc_info=True)

        @self.socketio.on('subscribe_tasks')
        def handle_task_subscription(data: Dict[str, Any]):
            """处理任务订阅"""
            try:
                logger.info(f"[WebSocket] 收到订阅请求: {data}")
                player_id = data.get('player_id')
                if player_id:
                    room = f'user_{player_id}'
                    join_room(room)
                    logger.info(f"[WebSocket] 用户 {player_id} 加入房间: {room}")
                    # 发送确认消息
                    emit('subscription_confirmed', {
                        'status': 'success',
                        'room': room,
                        'timestamp': time.time()
                    }, room=room)
                else:
                    logger.warning(f"[WebSocket] 警告: 收到无玩家ID的订阅请求")
            except Exception as e:
                logger.error(f"[WebSocket] 处理任务订阅失败: {str(e)}", exc_info=True)

        @self.socketio.on('ping')
        def handle_ping():
            """处理ping消息"""
            logger.debug(f"[WebSocket] 收到ping: {request.sid}")
            emit('pong', {'timestamp': time.time()})

    def emit(self, event, data, room=None):
        """发送WebSocket事件"""
        try:
            self.socketio.emit(event, data, room=room)
        except Exception as e:
            logger.error(f"[WebSocket] 发送事件失败: {str(e)}")

    def broadcast_task_update(self, player_id: int, task_data: Dict[str, Any]) -> None:
        """向指定用户广播任务更新"""
        try:
            logger.info(f"[WebSocket] 广播任务更新: player_id={player_id}, task_data={task_data}")
            self.emit('task_update', task_data, room=f'user_{player_id}')
        except Exception as e:
            logger.error(f"[WebSocket] 广播任务更新失败: {str(e)}", exc_info=True)

    def broadcast_gps_update(self, player_id: int, gps_data: Dict[str, Any]) -> None:
        """向指定用户广播GPS更新"""
        try:
            logger.info(f"[WebSocket] 广播GPS更新: player_id={player_id}, gps_data={gps_data}")
            self.emit('gps_update', gps_data, room=f'user_{player_id}')
        except Exception as e:
            logger.error(f"[WebSocket] 广播GPS更新失败: {str(e)}", exc_info=True)

    def broadcast_log_update(self, logs: list, latest: Dict[str, Any]) -> None:
        """广播日志更新"""
        return
        try:
            logger.debug(f"[WebSocket] 广播日志更新: latest={latest}")
            self.emit('log_update', {
                'logs': logs,
                'latest': latest,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.error(f"[WebSocket] 广播日志更新失败: {str(e)}", exc_info=True)

    def broadcast_nfc_update(self, player_id: int, data: Dict[str, Any]) -> None:
        """向指定用户广播NFC更新"""
        try:
            self.emit('nfc_task_update', data, room=f'user_{player_id}')
        except Exception as e:
            logger.error(f"[WebSocket] 广播NFC更新失败: {str(e)}", exc_info=True)

    def run(self, app, host: str, port: int, **kwargs) -> None:
        """运行WebSocket服务器"""
        try:
            if self.socketio:
                logger.info(f"[WebSocket] 启动WebSocket服务器: host={host}, port={port}, kwargs={kwargs}")
                self.socketio.run(app, host=host, port=port, **kwargs)
            else:
                logger.error("[WebSocket] SocketIO未初始化")
        except Exception as e:
            logger.error(f"[WebSocket] 运行服务器失败: {str(e)}", exc_info=True)
            raise

# 创建WebSocket服务实例
websocket_service = WebSocketService() 