# -*- coding: utf-8 -*-
"""
SSE服务模块
提供Server-Sent Events功能，用于推送周期任务提醒
使用主应用的SSE服务，而非独立实现
"""
import time
import threading
import json
from flask import Response

# 导入主应用的SSE服务
try:
    from function.SSEService import sse_service as main_sse_service
    USE_MAIN_SSE_SERVICE = True
    print("[Roadmap SSE] 已导入主应用SSE服务")
except ImportError:
    USE_MAIN_SSE_SERVICE = False
    print("[Roadmap SSE] 无法导入主应用SSE服务，使用独立实现")

class RoadmapSSEService:
    def __init__(self):
        self.is_running = False
        self.check_interval = 86400  # 每天检查一次周期任务
        self.roadmap_service = None
        # 添加客户端连接管理
        self.clients = []
        self.clients_lock = threading.Lock()
        
    def set_roadmap_service(self, roadmap_service):
        """设置roadmap服务实例"""
        self.roadmap_service = roadmap_service
        
    def start(self):
        """启动SSE服务"""
        if self.is_running:
            return
        
        self.is_running = True
        # 启动周期任务检查线程
        self.check_thread = threading.Thread(target=self.check_cycle_tasks_loop)
        self.check_thread.daemon = True
        self.check_thread.start()
        print("[Roadmap SSE] 已启动周期任务检查线程")
        
    def stop(self):
        """停止SSE服务"""
        self.is_running = False
        self.check_thread.join(timeout=1)
        print("[Roadmap SSE] 已停止")
        
    def register_client(self):
        """注册新客户端，提供完整的SSE连接实现"""
        from flask import stream_with_context
        
        # 创建客户端对象
        client = {
            'id': f'client_{time.time()}',
            'created_at': time.time(),
            'messages': []
        }
        
        # 添加客户端到连接列表
        with self.clients_lock:
            self.clients.append(client)
        
        @stream_with_context
        def client_generator():
            try:
                # 立即发送连接成功事件，不等待任何初始化操作
                yield "event: connected\ndata: {\"type\": \"connected\", \"message\": \"Roadmap SSE连接已建立\"}\n\n"
                
                # 保持连接，定期发送心跳
                heartbeat_count = 0
                last_heartbeat_time = time.time()
                
                while self.is_running:
                    current_time = time.time()
                    
                    # 检查是否有新消息 - 尽量减少锁竞争
                    messages_to_send = []
                    with self.clients_lock:
                        if client['messages']:
                            # 获取所有消息并清空队列
                            messages_to_send = client['messages']
                            client['messages'] = []
                    
                    # 发送所有消息
                    for message in messages_to_send:
                        yield message
                    
                    # 每3秒发送一次心跳，平衡可靠性和性能
                    if current_time - last_heartbeat_time >= 3:
                        # 发送简洁的心跳消息，减少数据大小
                        yield f"event: ping\ndata: {{\"timestamp\": {current_time}}}\n\n"
                        heartbeat_count += 1
                        last_heartbeat_time = current_time
                    
                    # 短暂休眠，减少CPU占用
                    time.sleep(0.1)  # 保持高频检查，但只在需要时发送心跳
            except GeneratorExit:
                # 客户端断开连接，移除客户端
                with self.clients_lock:
                    if client in self.clients:
                        self.clients.remove(client)
                print(f"[Roadmap SSE] 客户端断开连接: {client['id']}")
            except Exception as e:
                # 客户端连接异常，移除客户端
                with self.clients_lock:
                    if client in self.clients:
                        self.clients.remove(client)
                print(f"[Roadmap SSE] 客户端连接异常: {str(e)}")
        
        # 创建SSE响应，设置正确的响应头
        response = Response(
            client_generator(), 
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache, no-store',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Allow-Headers': 'Origin, X-Requested-With, Content-Type, Accept',
                'X-Content-Type-Options': 'nosniff',  # 防止浏览器嗅探
                'Content-Encoding': 'identity'  # 禁用压缩
            }
        )
        
        # 立即返回响应，不等待任何异步操作
        return response
        
    def check_cycle_tasks_loop(self):
        """周期任务检查循环"""
        while self.is_running:
            try:
                self.check_cycle_tasks()
            except Exception as e:
                print(f"[Roadmap SSE] 检查周期任务失败: {str(e)}")
            time.sleep(self.check_interval)
            
    def check_cycle_tasks(self):
        """检查周期任务并推送提醒"""
        if not self.roadmap_service:
            return
            
        # 获取当前时间戳
        current_time = int(time.time())
        
        # 获取过期的周期任务
        conn = None
        try:
            conn = self.roadmap_service.get_db()
            cursor = conn.cursor()
            
            # 查询所有过期的周期任务
            cursor.execute('''
                SELECT * FROM roadmap 
                WHERE is_cycle_task = 1 
                AND next_reminder_time <= ? 
                AND status != 'COMPLETED' 
                AND is_deleted = 0
            ''', (current_time,))
            
            tasks = [dict(row) for row in cursor.fetchall()]
            
            if tasks:
                print(f"[Roadmap SSE] 发现 {len(tasks)} 个过期周期任务")
                # 推送提醒
                self.push_reminders(tasks)
                
                # 将过期任务状态从PLANNED更新为WORKING
                cursor.execute('''
                    UPDATE roadmap 
                    SET status = 'WORKING',
                        edittime = ?
                    WHERE is_cycle_task = 1 
                    AND next_reminder_time <= ? 
                    AND status = 'PLANNED' 
                    AND is_deleted = 0
                ''', (current_time, current_time))
                conn.commit()
                
        except Exception as e:
            print(f"[Roadmap SSE] 检查周期任务失败: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
                
    def push_reminders(self, tasks):
        """推送周期任务提醒"""
        for task in tasks:
            event_data = {
                'type': 'cycle_task_reminder',
                'task': {
                    'id': task['id'],
                    'name': task['name'],
                    'status': task['status'],
                    'next_reminder_time': task['next_reminder_time'],
                    'cycle_duration': task['cycle_duration']
                }
            }
            
            # 格式化SSE消息
            message = f"data: {json.dumps(event_data)}\n\n"
            
            # 使用主应用的SSE服务推送消息
            if USE_MAIN_SSE_SERVICE:
                # 主应用的SSE服务支持broadcast_to_room方法
                try:
                    print(f"[Roadmap SSE] 使用主应用SSE服务推送提醒: {task['name']}")
                    main_sse_service.broadcast_to_room('roadmap_room', 'cycle_task_reminder', event_data['task'])
                except Exception as e:
                    print(f"[Roadmap SSE] 使用主应用SSE服务推送失败: {str(e)}")
                    # 降级到本地推送
                    self._push_local_message(message)
            else:
                # 直接使用本地SSE服务推送消息
                print(f"[Roadmap SSE] 本地推送提醒: {task['name']}")
                self._push_local_message(message)
    
    def _push_local_message(self, message):
        """本地推送消息到所有连接的客户端"""
        with self.clients_lock:
            for client in self.clients:
                client['messages'].append(message)
                print(f"[Roadmap SSE] 消息已添加到客户端队列: {client['id']}")

# 创建SSE服务实例
sse_service = RoadmapSSEService()