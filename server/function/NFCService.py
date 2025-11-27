import sqlite3
import os
import logging
import time
import json
import traceback
from datetime import datetime
import serial
import serial.tools.list_ports
import re
from utils.response_handler import ResponseHandler, StatusCode
from config.config import ENV
# 导入SSE服务
from function.SSEService import sse_service
if ENV == 'local':
    from ndef import message, record
    from function.NFC_Device import NFC_Device

logger = logging.getLogger(__name__)

class NFCService:
    _instance = None
    _nfc_device = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NFCService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'database', 
                'game.db'
            )
            self.initialized = True
            
    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_nfc_device(self):
        """获取或创建NFC设备实例"""
        try:
            if self._nfc_device is None and ENV == 'local':
                print("[NFC] 创建新的NFC设备实例")
                self._nfc_device = NFC_Device()
            
            # 确保设备已初始化
            if self._nfc_device and not self._nfc_device.initialized:
                print("[NFC] 尝试初始化设备")
                if not self._nfc_device.auto_detect_device():
                    print("[NFC] 设备初始化失败")
                    return None
            else:
                print("[NFC] 设备已初始化") 
            return self._nfc_device
            
        except Exception as e:
            print(f"[NFC] 获取设备实例失败: {str(e)}")
            return None

    def get_nfc_cards(self):
        """获取NFC卡片列表"""
        try:
            print("[NFC] 获取NFC卡片列表")
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 获取最大的card_id
            cursor.execute('SELECT MAX(card_id) FROM NFC_card')
            max_id = cursor.fetchone()[0] or 0
            print(f"[NFC] 当前最大card_id: {max_id}")
            
            # 获取所有卡片数据
            cursor.execute('''
                SELECT 
                    card_id, type, id, value, addtime,
                    status, description, device
                FROM NFC_card
                ORDER BY addtime DESC
            ''')
            
            cards = []
            for row in cursor.fetchall():
                card = {
                    'card_id': row[0],
                    'type': row[1],
                    'id': row[2],
                    'value': row[3],
                    'addtime': row[4],
                    'status': row[5],
                    'description': row[6],
                    'device': row[7]
                }
                print(f"[NFC] 获取到卡片: {card}")
                cards.append(card)
                
            print(f"[NFC] 成功获取 {len(cards)} 张卡片")
            
            return ResponseHandler.success(
                data={
                    'cards': cards,
                    'next_card_id': max_id  # 添加next_card_id字段
                },
                msg="获取NFC卡片列表成功"
            )
            
        except Exception as e:
            print(f"[NFC] 获取卡片列表失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取卡片列表失败: {str(e)}"
            )
        finally:
            conn.close()

    def create_nfc_card(self, data):
        """创建新NFC卡片"""
        try:
            print(f"接收到的NFC卡片创建数据: {data}")
            current_time = int(time.time())
            
            # 验证必填字段
            required_fields = ['type', 'id', 'value']
            for field in required_fields:
                if field not in data:
                    print(f"缺少必填字段: {field}")
                    return ResponseHandler.error(
                        code=StatusCode.PARAM_ERROR,
                        msg=f"缺少必填字段: {field}"
                    )
            
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 获取最大的 card_id
            cursor.execute('SELECT MAX(card_id) FROM NFC_card')
            result = cursor.fetchone()
            next_card_id = 1 if result[0] is None else result[0] + 1
            print(f"生成的新card_id: {next_card_id}")
            
            # 准备插入数据
            insert_data = {
                'card_id': next_card_id,
                'type': data['type'],
                'id': data['id'],
                'value': data['value'],
                'addtime': current_time,
                'status': 'UNLINK',
                'description': data.get('description', ''),
                'device': data.get('device', '')
            }
            print(f"准备插入的数据: {insert_data}")
            
            cursor.execute('''
                INSERT INTO NFC_card (
                    card_id, type, id, value, addtime, 
                    status, description, device
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                insert_data['card_id'],
                insert_data['type'],
                insert_data['id'],
                insert_data['value'],
                insert_data['addtime'],
                insert_data['status'],
                insert_data['description'],
                insert_data['device']
            ))
            
            conn.commit()
            
            # 验证插入是否成功
            cursor.execute('SELECT * FROM NFC_card WHERE card_id = ?', (next_card_id,))
            inserted_data = cursor.fetchone()
            print(f"插入后的数据验证: {dict(inserted_data) if inserted_data else None}")
            
            return ResponseHandler.success(
                data={'card_id': next_card_id},
                msg="创建NFC卡片成功"
            )
            
        except Exception as e:
            print(f"创建NFC卡片失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"创建NFC卡片失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def update_nfc_card(self, card_id, data):
        """更新NFC卡片"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            update_fields = []
            params = []
            
            # 构建更新字段
            if 'status' in data:
                update_fields.append('status = ?')
                params.append(data['status'])
            if 'description' in data:
                update_fields.append('description = ?')
                params.append(data['description'])
            if 'device' in data:
                update_fields.append('device = ?')
                params.append(data['device'])
                
            if not update_fields:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="没有要更新的字段"
                )
                
            params.append(card_id)
            
            cursor.execute(f'''
                UPDATE NFC_card 
                SET {', '.join(update_fields)}
                WHERE card_id = ?
            ''', params)
            
            if cursor.rowcount == 0:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg="卡片不存在"
                )
                
            conn.commit()
            
            return ResponseHandler.success(msg="更新NFC卡片成功")
            
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"更新NFC卡片失败: {str(e)}"
            )
        finally:
            conn.close()

    def delete_nfc_card(self, card_id):
        """删除NFC卡片"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM NFC_card WHERE card_id = ?', (card_id,))
            
            if cursor.rowcount == 0:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg="卡片不存在"
                )
                
            conn.commit()
            
            return ResponseHandler.success(msg="删除NFC卡片成功")
            
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"删除NFC卡片失败: {str(e)}"
            )
        finally:
            conn.close()

    def get_next_card_id(self):
        """获取下一个可用的NFC卡片ID"""
        try:
            print("[NFC] 获取下一个可用卡片ID")
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 获取最大的card_id
            cursor.execute('SELECT MAX(card_id) FROM NFC_card')
            result = cursor.fetchone()
            next_id = 1 if result[0] is None else result[0] + 1
            
            print(f"[NFC] 下一个可用ID: {next_id}")
            return ResponseHandler.success(
                data={'next_id': next_id},
                msg="获取下一个可用卡片ID成功"
            )
            
        except Exception as e:
            print(f"[NFC] 获取下一个卡片ID失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取下一个卡片ID失败: {str(e)}"
            )
        finally:
            conn.close()

    def get_card_status(self, card_id):
        """获取指定NFC卡片的状态"""
        try:
            print(f"[NFC] 获取卡片状态: {card_id}")
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('SELECT status FROM NFC_card WHERE card_id = ?', (card_id,))
            result = cursor.fetchone()
            
            if result:
                print(f"[NFC] 卡片状态: {result['status']}")
                return ResponseHandler.success(
                    data={'status': result['status']},
                    msg="获取卡片状态成功"
                )
            else:
                print(f"[NFC] 卡片不存在: {card_id}")
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg="卡片不存在"
                )
                
        except Exception as e:
            print(f"[NFC] 获取卡片状态失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取卡片状态失败: {str(e)}"
            )
        finally:
            conn.close()

    def get_hardware_status(self):
        """获取NFC硬件设备状态"""
        if ENV == 'prod':
            return ResponseHandler.success(
                msg='NFC功能已关闭',
                data=None
            )
        try:
            print("[NFC] 检查设备状态")
            nfc_device = self.get_nfc_device()
            
            # 自动检测设备
            is_connected = nfc_device.auto_detect_device()
            print(f"[NFC Hardware] 设备连接状态: {'已连接' if is_connected else '未连接'}")
            
            # 获取端口信息
            port_info = ""
            if is_connected and nfc_device.serial_port:
                port_info = nfc_device.serial_port.port
                print(f"[NFC Hardware] 当前使用端口: {port_info}")
            
            # 构建状态信息
            status = {
                'device_connected': is_connected,
                'port': port_info,
                'card_present': False,  # 默认无卡
                'card_id': None  # 添加card_id字段
            }
            
            # 如果设备已连接，检查卡片状态
            if is_connected:
                try:
                    card_id = nfc_device.read_card_id()
                    print(f"[NFC Hardware] 读取到卡片ID: {card_id}")
                    if card_id and isinstance(card_id, str):  # 确保card_id是有效的字符串
                        status['card_present'] = True
                        status['card_id'] = card_id
                        print(f"[NFC Hardware] 卡片状态: 已检测到卡片 (ID: {card_id})")
                    else:
                        print("[NFC Hardware] 卡片状态: 未检测到卡片")
                except Exception as e:
                    print(f"[NFC Hardware] 读取卡片ID失败: {str(e)}")
                    status['card_present'] = False
                    status['card_id'] = None
                
            return ResponseHandler.success(
                data=status,
                msg="获取设备状态成功"
            )
            
        except Exception as e:
            print(f"[NFC Hardware] 获取设备状态失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取设备状态失败: {str(e)}"
            )

    def read_hardware(self):
        """读取NFC实体卡片"""
        if ENV == 'prod':
            return ResponseHandler.success(
                msg='NFC功能已关闭',
                data=None
            )
        print("[NFC] 开始读取卡片数据")
        
        nfc_device = self.get_nfc_device()
        if nfc_device is None:
            return ResponseHandler.error(
                code=StatusCode.DEVICE_ERROR,
                msg='NFC设备未初始化'
            )

        try:
            # 读取卡片数据
            card_data = nfc_device.read_all_card_data()
            if not card_data:
                return ResponseHandler.error(
                    code=StatusCode.DEVICE_ERROR,
                    msg='未检测到卡片或读取失败'
                )
                
            print(f"[NFC] 读取到数据: {card_data}")
            
            # 解析数据
            parsed_data = nfc_device.parse_nfc_data(card_data)
            print(f"[NFC] 解析数据: {parsed_data}")
            if not parsed_data:
                return ResponseHandler.error(
                    code=StatusCode.DEVICE_ERROR,
                    msg='数据解析失败'
                )
                
            return ResponseHandler.success(
                data={
                    'raw_data': card_data.upper(),
                    'url': parsed_data['url'],
                    'params': parsed_data['params'],
                    'raw_ascii': parsed_data['ascii'],
                },
                msg="读取卡片成功"
            )
            
        except Exception as e:
            print(f"[NFC] 读取错误: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.DEVICE_ERROR,
                msg=f'读卡错误: {str(e)}'
            )

    def write_hardware(self, data):
        """写入NFC实体卡片"""
        if ENV == 'prod':
            return ResponseHandler.success(
                msg='NFC功能已关闭',
                data=None
            )
        print("[NFC] 开始写入卡片数据")
        
        nfc_device = self.get_nfc_device()
        if nfc_device is None:
            print("[NFC Write] 无法获取设备实例")
            return ResponseHandler.error(
                code=StatusCode.DEVICE_ERROR,
                msg='NFC设备未初始化'
            )

        if not data or 'data' not in data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg='写入数据不能为空'
            )

        try:
            # 写入前检查卡片状态
            card_id = nfc_device.read_card_id()
            if not card_id:
                return ResponseHandler.error(
                    code=StatusCode.DEVICE_ERROR,
                    msg='未检测到卡片'
                )

            print(f"[NFC] 写入数据: {data}")
            hex_data = nfc_device.format_ascii_to_hex(data['data'])
            
            # 写入数据
            if nfc_device._write_ntag_data(hex_data):
                print(f"[NFC] 写入成功: {hex_data}")
                
                # 写入后立即读取验证
                read_data = nfc_device.read_card_data_by_page()
                if not read_data:
                    return ResponseHandler.error(
                        code=StatusCode.DEVICE_ERROR,
                        msg='写入后验证失败：无法读取数据'
                    )
                    
                # 验证写入的数据
                if hex_data.rstrip('0').upper() in read_data.upper():
                    return ResponseHandler.success(
                        data={
                            'hex_data': hex_data,
                            'verified': True
                        },
                        msg="写入成功"
                    )
                else:
                    return ResponseHandler.error(
                        code=StatusCode.DEVICE_ERROR,
                        msg='写入验证失败：数据不匹配'
                    )
            else:
                print("[NFC] 写入失败")
                return ResponseHandler.error(
                    code=StatusCode.DEVICE_ERROR,
                    msg='写入失败'
                )
        except Exception as e:
            print(f"[NFC] 写入错误: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'写入异常: {str(e)}'
            )

    def handle_nfc_card(self, card_id, player_id):
        """处理NFC卡片扫描"""
        # 导入SSE服务
        from function.SSEService import sse_service
        print("[NFC] ====== 开始处理NFC卡片 ======")
        print(f"[NFC] 卡片ID: {card_id}, 玩家ID: {player_id}")
        
        conn = None
        response = {'code': 0, 'msg': '处理成功', 'data': None}
        room = f'user_{player_id}'

        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 查询卡片信息
            cursor.execute('SELECT * FROM NFC_card WHERE card_id = ?', (card_id,))
            card = cursor.fetchone()
            print(f"[NFC] 查询到的卡片信息: {json.dumps(dict(card) if card else None, ensure_ascii=False)}")
            
            if not card:
                error_msg = '无效的NFC卡片'
                print(f"[NFC] 错误: {error_msg}")
                return {
                    'code': 404,
                    'msg': error_msg,
                    'data': None
                }, 404
                
            card_type = card['type']
            value = card['value']
            print(f"[NFC] 卡片类型: {card_type}, 值: {value}")

            # 任务卡片处理
            if card_type == 'TASK':
                return self._handle_task_card(cursor, conn, value, player_id, room)
                
            # 积分卡片处理
            elif card_type == 'POINTS':
                return self._handle_points_card(cursor, conn, card_id, value, player_id)
                
            # 道具卡片处理
            elif card_type == 'CARD':
                return self._handle_game_card(cursor, conn, value, player_id)
                
            # 勋章卡片处理
            elif card_type == 'MEDAL':
                return self._handle_medal_card(cursor, conn, value, player_id)
                
            else:
                error_msg = f'未知的卡片类型: {card_type}'
                print(f"[NFC] 错误: {error_msg}")
                return json.dumps({
                    'code': 400,
                    'msg': error_msg,
                    'data': None
                }), 400

        except Exception as e:
            error_msg = f'处理失败: {str(e)}'
            print(f"[NFC] 错误: {error_msg}")
            print(f"[NFC] 详细错误信息: ", traceback.format_exc())

            if conn:
                conn.rollback()
                print("[NFC] 数据库事务已回滚")

            self._send_sse_message(room, 'ERROR', error_msg)

            return {
                'code': 500,
                'msg': error_msg,
                'data': None
            }, 500

        finally:
            if conn:
                conn.close()
                print("[NFC] 数据库连接已关闭")

    def _send_sse_message(self, room, msg_type, message, task=None, task_id=None, rewards=None, timestamp=None):
        """统一的SSE消息发送函数
        Args:
            room: 房间ID
            msg_type: 消息类型 ('ERROR', 'SUCCESS', 'INFO', 'COMPLETE', 'CHECK', 'ALREADY_COMPLETED' 等)
            message: 消息内容
            task: 任务信息字典（可选）
            task_id: 任务ID（可选）
            rewards: 奖励信息（可选）
            timestamp: 时间戳（可选）
        """
        print(f"[NFC] 发送SSE消息 - 类型: {msg_type}")
        print(f"[NFC] 消息内容: {message}")
        
        sse_data = {
            'type': msg_type,
            'message': message
        }
        
        if task:
            sse_data['task'] = task
        if task_id:
            sse_data['task_id'] = task_id
        if rewards:
            sse_data['rewards'] = rewards
        if timestamp:
            sse_data['timestamp'] = timestamp
        
        # 导入SSE服务（避免循环导入）
        from function.SSEService import sse_service
        sse_service.broadcast_to_room(room, 'nfc_task_update', sse_data)

    def _format_task_message(self, task, status_msg="", extra_msg=""):
        """格式化任务相关消息
        Args:
            task: 任务信息字典
            status_msg: 状态信息（可选）
            extra_msg: 额外信息（可选）
        """
        message = f'''任务ID：{task["id"]}
        任务名称：{task["name"]}
        任务类型：{task["task_type"]}
        任务描述：{task["description"]}'''

        if status_msg:
            message += f"\n状态：{status_msg}"
        if extra_msg:
            message += f"\n{extra_msg}"
        
        return message

    def _handle_task_card(self, cursor, conn, task_id, player_id, room):
        """处理任务卡片"""
        from function.TaskService import task_service  # 导入任务服务
        
        print(f"[NFC] 开始处理任务卡片 - 任务ID: {task_id}")
        
        try:
            # 验证玩家和任务
            result = task_service.complete_task_api(player_id, task_id)
            
            if result['code'] == 0:
                # 任务完成成功
                self._send_sse_message(
                    room, 
                    'COMPLETE' if not result.get('data', {}).get('need_check') else 'CHECK',
                    "任务提交成功",
                    task=result.get('data', {})
                )
                return result
            else:
                # 任务完成失败
                self._send_sse_message(
                    room,
                    'ERROR',
                    result['msg']
                )
                return result
            
        except Exception as e:
            error_msg = f"处理任务卡片失败: {str(e)}"
            print(f"[NFC] 错误: {error_msg}")
            self._send_sse_message(room, 'ERROR', error_msg)
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=error_msg
            )

    def _handle_points_card(self, cursor, conn, card_id, value, player_id):
        """处理积分卡片"""
        try:
            # 检查卡片是否有效且未使用
            cursor.execute(
                'SELECT * FROM NFC_card WHERE card_id = ? AND status = "active"', 
                (card_id,)
            )
            card = cursor.fetchone()
            
            if not card:
                return json.dumps({
                    'code': 403, 
                    'msg': '无效的积分卡或卡片已被使用',
                    'data': None
                }), 403

            current_time = int(time.time())
            points = int(value)

            # 更新玩家积分
            cursor.execute('''
                UPDATE player_data 
                SET points = points + ? 
                WHERE player_id = ?
            ''', (points, player_id))

            # 记录积分变动
            cursor.execute('''
                INSERT INTO points_record (
                    player_id, number, addtime, remark
                ) VALUES (?, ?, ?, ?)
            ''', (player_id, points, current_time, f'NFC卡片 {card_id}'))

            # 将卡片标记为已使用
            cursor.execute('''
                UPDATE NFC_card 
                SET status = "used", 
                    use_time = ?,
                    player_id = ? 
                WHERE card_id = ?
            ''', (current_time, player_id, card_id))

            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': f'成功使用积分卡，获得 {points} 积分',
                'data': {'points': points}
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"处理积分卡片失败: {str(e)}")
            return json.dumps({
                'code': 500,
                'msg': f'处理积分卡片失败: {str(e)}',
                'data': None
            }), 500

    def _handle_game_card(self, cursor, conn, value, player_id):
        """处理道具卡片"""
        try:
            # 检查道具是否存在
            cursor.execute('SELECT * FROM game_card WHERE id = ?', (value,))
            prop = cursor.fetchone()
            
            if not prop:
                return json.dumps({
                    'code': 404,
                    'msg': '道具不存在',
                    'data': None
                }), 404

            current_time = int(time.time())

            # 检查玩家是否已有该道具
            cursor.execute('''
                SELECT * FROM player_game_card 
                WHERE player_id = ? AND game_card_id = ?
            ''', (player_id, value))
            existing_card = cursor.fetchone()
            
            if existing_card:
                # 更新道具数量
                cursor.execute('''
                    UPDATE player_game_card 
                    SET number = number + 1,
                        timestamp = ?
                    WHERE player_id = ? AND game_card_id = ?
                ''', (current_time, player_id, value))
            else:
                # 添加新道具
                cursor.execute('''
                    INSERT INTO player_game_card (
                        player_id, game_card_id, number, timestamp
                    ) VALUES (?, ?, 1, ?)
                ''', (player_id, value, current_time))

            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': f'成功获得道具：{prop["name"]}',
                'data': {'prop_id': value, 'prop_name': prop['name']}
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"处理道具卡片失败: {str(e)}")
            return json.dumps({
                'code': 500,
                'msg': f'处理道具卡片失败: {str(e)}',
                'data': None
            }), 500

    def _handle_medal_card(self, cursor, conn, value, player_id):
        """处理勋章卡片"""
        try:
            # 检查勋章是否存在
            cursor.execute('SELECT * FROM medal WHERE id = ?', (value,))
            medal = cursor.fetchone()
            
            if not medal:
                return json.dumps({
                    'code': 404,
                    'msg': '勋章不存在',
                    'data': None
                }), 404

            # 检查玩家是否已有该勋章
            cursor.execute('''
                SELECT * FROM player_medal 
                WHERE player_id = ? AND medal_id = ?
            ''', (player_id, value))
            
            if cursor.fetchone():
                return json.dumps({
                    'code': 400,
                    'msg': '已拥有该勋章',
                    'data': None
                }), 400

            # 添加勋章
            current_time = int(time.time())
            cursor.execute('''
                INSERT INTO player_medal (
                    player_id, medal_id, addtime
                ) VALUES (?, ?, ?)
            ''', (player_id, value, current_time))

            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': f'成功获得勋章：{medal["name"]}',
                'data': {'medal_id': value, 'medal_name': medal['name']}
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"处理勋章卡片失败: {str(e)}")
            return json.dumps({
                'code': 500,
                'msg': f'处理勋章卡片失败: {str(e)}',
                'data': None
            }), 500

    def get_nfc_card_info(self, card_id):
        """获取NFC卡片信息"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.*, 
                       CASE 
                           WHEN c.card_type = 'TASK' THEN t.name
                           WHEN c.card_type = 'CARD' THEN gc.name
                           WHEN c.card_type = 'MEDAL' THEN m.name
                           ELSE NULL 
                       END as item_name
                FROM NFC_card c
                LEFT JOIN task t ON c.card_type = 'TASK' AND c.value = t.id
                LEFT JOIN game_card gc ON c.card_type = 'CARD' AND c.value = gc.id
                LEFT JOIN medal m ON c.card_type = 'MEDAL' AND c.value = m.id
                WHERE c.card_id = ?
            ''', (card_id,))
            
            card = cursor.fetchone()
            
            if not card:
                return json.dumps({
                    'code': 404,
                    'msg': '卡片不存在',
                    'data': None
                }), 404

            return json.dumps({
                'code': 0,
                'msg': '获取卡片信息成功',
                'data': dict(card)
            })

        except Exception as e:
            logger.error(f"获取NFC卡片信息失败: {str(e)}")
            return json.dumps({
                'code': 500,
                'msg': f'获取NFC卡片信息失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()

nfc_service = NFCService()
