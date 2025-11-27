"""
SSE(Server-Sent Events)服务模块
处理服务器到客户端的单向实时通信
"""
import logging
import time
import threading
from flask import Response, request, stream_with_context
from typing import Dict, Any, Optional, Set, List
from collections import defaultdict
from config.config import  ENV, DOMAIN

logger = logging.getLogger(__name__)

class SSEService:
    """SSE服务类"""
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SSEService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """初始化SSE服务"""
        with self._lock:
            if not hasattr(self, 'initialized'):
                # 客户端连接管理
                self.connections = defaultdict(set)  # {player_id: set(connections)}
                self.connection_info = {}  # {conn_id: {player_id, created_at, last_activity}}
                self.connection_counter = 0
                
                # 房间管理（模拟WebSocket的房间功能）
                self.rooms = defaultdict(set)  # {room: set(player_ids)}
                
                # 线程安全锁
                self.connection_lock = threading.RLock()
                self.rooms_lock = threading.RLock()
                
                self.initialized = True
                logger.info("[SSE] SSE服务初始化完成")
                
    def init_app(self, app):
        """将SSE服务与Flask应用关联"""
        self.app = app
        # 注册SSE相关的路由
        self._register_routes()
        logger.info("[SSE] SSE服务与Flask应用关联完成")
        
    def _register_routes(self):
        """注册SSE相关的路由"""
        @self.app.route('/api/sse/connect', methods=['GET'])
        def sse_connect():
            """建立SSE连接"""
            player_id = request.args.get('player_id')
            if not player_id:
                return {'error': 'player_id is required'}, 400
            
            logger.info(f"[SSE] 客户端连接请求: player_id={player_id}")
            
            @stream_with_context
            def event_stream():
                conn_id = self._add_connection(player_id)
                
                try:
                    # 立即发送连接成功事件，包含更详细的连接信息
                    yield self._format_event('connected', {'conn_id': conn_id, 'player_id': player_id, 'timestamp': time.time()})
                    
                    # 保持连接
                    heartbeat_interval = 5  # 保持5秒心跳间隔
                    ping_count = 0
                    
                    while True:
                        # 更新连接活动时间
                        self.update_connection_activity(conn_id)
                        
                        # 定期发送心跳
                        yield self._format_event('ping', {'timestamp': time.time(), 'count': ping_count})
                        ping_count += 1
                        time.sleep(0.1)  # 减少延迟，提高响应速度
                        
                        # 检查是否已经过了心跳间隔
                        if ping_count % 50 == 0:  # 大约每5秒发送一次心跳（0.1秒*50）
                            yield self._format_event('ping', {'timestamp': time.time(), 'count': ping_count // 50})
                        
                        # 检查连接是否超时
                        if self._is_connection_inactive(conn_id, timeout=120):
                            yield self._format_event('timeout', {'message': 'Connection timeout'})
                            break
                            
                except GeneratorExit:
                    # 客户端断开连接
                    self._remove_connection(conn_id)
                    logger.info(f"[SSE] 客户端断开连接: player_id={player_id}, conn_id={conn_id}")
                except Exception as e:
                    # 处理其他异常并发送错误事件
                    logger.error(f"[SSE] 连接异常: player_id={player_id}, error={str(e)}", exc_info=True)
                    try:
                        yield self._format_event('error', {'message': str(e)})
                    except:
                        pass
                    finally:
                        self._remove_connection(conn_id)
            
            # 设置SSE响应头，增加跨域支持
            return Response(
                event_stream(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache, no-store',
                    'Connection': 'keep-alive',
                    'X-Accel-Buffering': 'no',
                    'Access-Control-Allow-Origin': '*'  # 支持跨域
                }
            )
            
    def _format_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """格式化SSE事件"""
        import json
        event_str = f"event: {event_type}\n"
        event_str += f"data: {json.dumps(data)}\n\n"
        return event_str
        
    def _add_connection(self, player_id: str) -> str:
        """添加新的连接"""
        with self.connection_lock:
            conn_id = f"conn_{self.connection_counter}"
            self.connection_counter += 1
            
            # 添加到连接管理
            self.connections[player_id].add(conn_id)
            self.connection_info[conn_id] = {
                'player_id': player_id,
                'created_at': time.time(),
                'last_activity': time.time()
            }
            
            logger.info(f"[SSE] 新连接添加: player_id={player_id}, conn_id={conn_id}")
            return conn_id
            
    def _remove_connection(self, conn_id: str) -> None:
        """移除连接"""
        with self.connection_lock:
            if conn_id in self.connection_info:
                player_id = self.connection_info[conn_id]['player_id']
                
                # 从连接集合中移除
                if player_id in self.connections:
                    self.connections[player_id].discard(conn_id)
                    # 如果没有连接了，删除player_id键
                    if not self.connections[player_id]:
                        del self.connections[player_id]
                
                # 删除连接信息
                del self.connection_info[conn_id]
                
                # 从所有房间中移除
                self._remove_from_rooms(player_id)
                
                logger.info(f"[SSE] 连接移除: conn_id={conn_id}, player_id={player_id}")
                
    def _remove_from_rooms(self, player_id: str) -> None:
        """从所有房间中移除玩家"""
        with self.rooms_lock:
            for room, players in list(self.rooms.items()):
                if player_id in players:
                    players.remove(player_id)
                    if not players:
                        del self.rooms[room]
                        
    def _is_connection_inactive(self, conn_id: str, timeout: int = 120) -> bool:
        """检查连接是否不活跃"""
        with self.connection_lock:
            if conn_id not in self.connection_info:
                return True
            
            last_activity = self.connection_info[conn_id]['last_activity']
            inactive_time = time.time() - last_activity
            if inactive_time > timeout:
                logger.info(f"[SSE] 连接超时: conn_id={conn_id}, inactive_time={inactive_time}s")
            return inactive_time > timeout
            
    def join_room(self, player_id: str, room: str) -> None:
        """将玩家加入房间"""
        with self.rooms_lock:
            self.rooms[room].add(player_id)
            logger.info(f"[SSE] 玩家加入房间: player_id={player_id}, room={room}")
            
    def leave_room(self, player_id: str, room: str) -> None:
        """将玩家离开房间"""
        with self.rooms_lock:
            if room in self.rooms:
                self.rooms[room].discard(player_id)
                if not self.rooms[room]:
                    del self.rooms[room]
                logger.info(f"[SSE] 玩家离开房间: player_id={player_id}, room={room}")
                
    def broadcast_task_update(self, player_id: int, task_data: Dict[str, Any]) -> str:
        """向指定用户广播任务更新
        返回格式化的SSE事件数据
        """
        try:
            player_id_str = str(player_id)
            logger.info(f"[SSE] 准备任务更新: player_id={player_id}, task_data={task_data}")
            
            # 更新相关连接的活动时间
            with self.connection_lock:
                if player_id_str in self.connections:
                    for conn_id in self.connections[player_id_str]:
                        self.update_connection_activity(conn_id)
            
            return self._format_event('task_update', task_data)
            
        except Exception as e:
            logger.error(f"[SSE] 任务更新失败: {str(e)}", exc_info=True)
            return None
            
    def broadcast_gps_update(self, player_id: int, gps_data: Dict[str, Any]) -> None:
        """向指定用户广播GPS更新"""
        try:
            player_id_str = str(player_id)
            logger.info(f"[SSE] 准备GPS更新: player_id={player_id}, gps_data={gps_data}")
            
            return self._format_event('gps_update', gps_data)
            
        except Exception as e:
            logger.error(f"[SSE] GPS更新失败: {str(e)}", exc_info=True)
            
    def broadcast_nfc_update(self, player_id: int, data: Dict[str, Any]) -> None:
        """向指定用户广播NFC更新"""
        try:
            player_id_str = str(player_id)
            logger.info(f"[SSE] 准备NFC更新: player_id={player_id}, data={data}")
            
            return self._format_event('nfc_task_update', data)
            
        except Exception as e:
            logger.error(f"[SSE] NFC更新失败: {str(e)}", exc_info=True)
            
    def broadcast_notification_update(self, notification_data):
        """广播通知状态更新"""
        try:
            self._broadcast_event('notification:update', notification_data)
        except Exception as e:
            logger.error(f"[SSE] 通知更新失败: {str(e)}", exc_info=True)
            
    def broadcast_to_room(self, room: str, event_type: str, data: Dict[str, Any]) -> None:
        """向指定房间广播事件"""
        try:
            logger.info(f"[SSE] 准备房间广播: room={room}, event={event_type}")
            event_data = self._format_event(event_type, data)
            
            # 在实际使用中，这里会将事件数据存储，然后由各个连接的事件流发送
            
            with self.rooms_lock:
                if room in self.rooms:
                    for player_id in self.rooms[room]:
                        logger.info(f"[SSE] 房间广播到玩家: player_id={player_id}, room={room}")
                        
        except Exception as e:
            logger.error(f"[SSE] 房间广播失败: {str(e)}", exc_info=True)
            
    def get_connection_count(self, player_id: str = None) -> int:
        """获取连接数量"""
        with self.connection_lock:
            if player_id:
                return len(self.connections.get(player_id, set()))
            else:
                # 计算总连接数
                return sum(len(conns) for conns in self.connections.values())
                
    def get_room_player_count(self, room: str) -> int:
        """获取房间内的玩家数量"""
        with self.rooms_lock:
            return len(self.rooms.get(room, set()))
            
    def update_connection_activity(self, conn_id: str) -> None:
        """更新连接活动时间"""
        with self.connection_lock:
            if conn_id in self.connection_info:
                self.connection_info[conn_id]['last_activity'] = time.time()
                # 可选：记录活动更新日志，用于调试
                # logger.debug(f"[SSE] 更新连接活动: conn_id={conn_id}")
                
# 创建SSE服务实例
sse_service = SSEService()