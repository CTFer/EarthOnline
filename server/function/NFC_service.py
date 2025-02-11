import sqlite3
from flask import jsonify
import os
import logging
import time
import json
import traceback
from flask_socketio import emit
from datetime import datetime
import serial
import serial.tools.list_ports
from ndef import message, record, UriRecord, TextRecord, message_encoder
import re


logger = logging.getLogger(__name__)

class NFCService:
    _instance = None
    
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
            self.serial_port = None
            self.initialized = False
  
    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def handle_nfc_card(self, card_id, player_id, socketio):
        """处理NFC卡片扫描"""
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
                return self._handle_task_card(cursor, conn, value, player_id, socketio, room)
                
            # 积分卡片处理
            elif card_type == 'POINTS':
                return self._handle_points_card(cursor, conn, card_id, value, player_id)
                
            # 道具卡片处理
            elif card_type == 'CARD':
                return self._handle_prop_card(cursor, conn, value, player_id)
                
            # 勋章卡片处理
            elif card_type == 'MEDAL':
                return self._handle_medal_card(cursor, conn, value, player_id)
                
            else:
                error_msg = f'未知的卡片类型: {card_type}'
                print(f"[NFC] 错误: {error_msg}")
                return jsonify({
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

            socketio.emit('nfc_task_update', {
                'type': 'ERROR',
                'message': error_msg
            }, room=room)

            return {
                'code': 500,
                'msg': error_msg,
                'data': None
            }, 500

        finally:
            if conn:
                conn.close()
                print("[NFC] 数据库连接已关闭")

    def _send_socket_message(self, socketio, room, msg_type, message, task=None, task_id=None, rewards=None, timestamp=None):
        """统一的Socket消息发送函数
        Args:
            socketio: SocketIO实例
            room: 房间ID
            msg_type: 消息类型 ('ERROR', 'SUCCESS', 'INFO', 'COMPLETE', 'CHECK', 'ALREADY_COMPLETED' 等)
            message: 消息内容
            task: 任务信息字典（可选）
            task_id: 任务ID（可选）
            rewards: 奖励信息（可选）
            timestamp: 时间戳（可选）
        """
        print(f"[NFC] 发送Socket消息 - 类型: {msg_type}")
        print(f"[NFC] 消息内容: {message}")
        
        socket_data = {
            'type': msg_type,
            'message': message
        }
        
        if task:
            socket_data['task'] = task
        if task_id:
            socket_data['task_id'] = task_id
        if rewards:
            socket_data['rewards'] = rewards
        if timestamp:
            socket_data['timestamp'] = timestamp
        
        socketio.emit('nfc_task_update', socket_data, room=room)

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

    def _handle_task_card(self, cursor, conn, task_id, player_id, socketio, room):
        """处理任务卡片"""
        print(f"[NFC] 开始处理任务卡片 - 任务ID: {task_id}")
        
        # 首先验证玩家ID是否有效
        cursor.execute('SELECT player_id FROM player_data WHERE player_id = ?', (player_id,))
        player = cursor.fetchone()
        if not player:
            error_msg = f'无效的玩家ID: {player_id}'
            print(f"[NFC] 错误: {error_msg}")
            self._send_socket_message(socketio, room, 'ERROR', error_msg, task_id=task_id)
            return {
                'code': 404,
                'msg': error_msg,
                'data': None
            }, 404
        
        # 查询任务信息
        cursor.execute('''
            SELECT id, name, description, task_type, need_check, 
                   is_enabled, limit_time, task_rewards as rewards
            FROM task 
            WHERE id = ?
        ''', (task_id,))
        task = cursor.fetchone()
        print(f"[NFC] 查询到的任务信息: {json.dumps(dict(task) if task else None, ensure_ascii=False)}")

        if not task:
            error_msg = f'任务不存在 (ID: {task_id})'
            print(f"[NFC] 错误: {error_msg}")
            self._send_socket_message(socketio, room, 'ERROR', error_msg, task_id=task_id)
            return {
                'code': 404,
                'msg': error_msg,
                'data': None
            }, 404

        if not task['is_enabled']:
            error_msg = f'任务未启用 (ID: {task_id})'
            print(f"[NFC] 错误: {error_msg}")
            self._send_socket_message(socketio, room, 'ERROR', error_msg, task_id=task_id)
            return {
                'code': 403,
                'msg': error_msg,
                'data': None
            }, 403

        # 查询玩家任务状态
        cursor.execute('''
            SELECT pt.*, t.name as task_name, t.description, t.task_type
            FROM player_task pt
            JOIN task t ON pt.task_id = t.id
            WHERE pt.player_id = ? AND pt.task_id = ? 
            ORDER BY pt.starttime DESC LIMIT 1
        ''', (player_id, task_id))
        task_info = cursor.fetchone()
        
        print(f"[NFC] 查询到的玩家任务状态: {json.dumps(dict(task_info) if task_info else None, ensure_ascii=False)}")
        
        if not task_info:
            message = self._format_task_message(
                task,
                "未接受",
                "请先在任务面板接受该任务"
            )
            print(f"[NFC] 错误: 任务未接受")
            self._send_socket_message(socketio, room, 'ERROR', message, task=dict(task))
            return {
                'code': 403, 
                'msg': '未接受该任务',
                'data': None
            }, 403

        status = task_info['status']
        task_info = dict(task_info)

        # 检查任务是否已完成
        if status == 'COMPLETED':
            complete_time = datetime.fromtimestamp(task_info["complete_time"]).strftime("%Y-%m-%d %H:%M:%S") if task_info.get("complete_time") else "未知"
            message = self._format_task_message(
                task,
                "已完成",
                f"完成时间：{complete_time}"
            )
            print(f"[NFC] 任务已经完成: {task['name']}")
            self._send_socket_message(socketio, room, 'ALREADY_COMPLETED', message, task=task_info)
            return {
                'code': 0,
                'msg': '任务已经完成',
                'data': task_info
            }, 200

        # 检查任务是否在进行中
        if status == 'IN_PROGRESS':
            # 如果是自动完成的任务
            if task['need_check'] == 0:
                try:
                    success, message, rewards_summary = self._complete_task(
                        cursor, player_id, task_id, task_info, int(time.time()))
                    
                    if success:
                        conn.commit()
                        self._send_socket_message(
                            socketio, room, 'COMPLETE', message, 
                            task=task_info, rewards=rewards_summary, 
                            timestamp=int(time.time())
                        )
                        return {
                            'code': 0,
                            'msg': message,
                            'data': task_info
                        }, 200
                except Exception as e:
                    conn.rollback()
                    raise
            else:
                # 提交检查
                cursor.execute('''
                    UPDATE player_task
                    SET status = 'CHECK'
                    WHERE player_id = ? AND task_id = ?
                ''', (player_id, task_id))
                conn.commit()
                print(f"[NFC] 任务已提交检查: {task['name']}")
                self._send_socket_message(socketio, room, 'CHECK', message, task=task_info)
                return {
                    'code': 0,
                    'msg': '任务已提交检查',
                    'data': task_info
                }, 200

        return {
            'code': 400,
            'msg': f'无效的任务状态: {status}',
            'data': task_info
        }, 400

    def _complete_task(self, cursor, player_id, task_id, task_info, current_time):
        """完成任务并发放奖励"""
        rewards_summary = {
            'points': 0,
            'exp': 0,
            'cards': [],
            'medals': []
        }

        # 获取任务奖励信息
        cursor.execute('SELECT task_rewards FROM task WHERE id = ?', (task_id,))
        rewards = json.loads(cursor.fetchone()['task_rewards'])

        # 1. 处理积分奖励
        if rewards.get('points', 0) > 0:
            cursor.execute('''
                UPDATE player_data 
                SET points = points + ? 
                WHERE player_id = ?
            ''', (rewards['points'], player_id))
            rewards_summary['points'] = rewards['points']

        # 2. 处理经验奖励
        if rewards.get('exp', 0) > 0:
            cursor.execute('SELECT experience FROM player_data WHERE player_id = ?', (player_id,))
            current_exp = cursor.fetchone()['experience']
            new_exp = current_exp + rewards['exp']
            
            cursor.execute('''
                UPDATE player_data 
                SET experience = ? 
                WHERE player_id = ?
            ''', (new_exp, player_id))
            
            cursor.execute('''
                INSERT INTO exp_record (player_id, number, addtime, total)
                VALUES (?, ?, ?, ?)
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
                cursor.execute('''
                    UPDATE player_game_card 
                    SET number = number + 1,
                        timestamp = ?
                    WHERE player_id = ? AND game_card_id = ?
                ''', (current_time, player_id, card_id))
            else:
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

        # 更新任务状态为已完成
        cursor.execute('''
            UPDATE player_task
            SET status = 'COMPLETED', 
                complete_time = ? 
            WHERE player_id = ? AND task_id = ?
        ''', (current_time, player_id, task_id))

        return True, "任务完成，奖励已发放", rewards_summary

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
                return jsonify({
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
            return jsonify({
                'code': 0,
                'msg': f'成功使用积分卡，获得 {points} 积分',
                'data': {'points': points}
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"处理积分卡片失败: {str(e)}")
            return jsonify({
                'code': 500,
                'msg': f'处理积分卡片失败: {str(e)}',
                'data': None
            }), 500

    def _handle_prop_card(self, cursor, conn, value, player_id):
        """处理道具卡片"""
        try:
            # 检查道具是否存在
            cursor.execute('SELECT * FROM game_card WHERE id = ?', (value,))
            prop = cursor.fetchone()
            
            if not prop:
                return jsonify({
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
            return jsonify({
                'code': 0,
                'msg': f'成功获得道具：{prop["name"]}',
                'data': {'prop_id': value, 'prop_name': prop['name']}
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"处理道具卡片失败: {str(e)}")
            return jsonify({
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
                return jsonify({
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
                return jsonify({
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
            return jsonify({
                'code': 0,
                'msg': f'成功获得勋章：{medal["name"]}',
                'data': {'medal_id': value, 'medal_name': medal['name']}
            })

        except Exception as e:
            conn.rollback()
            logger.error(f"处理勋章卡片失败: {str(e)}")
            return jsonify({
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
                return jsonify({
                    'code': 404,
                    'msg': '卡片不存在',
                    'data': None
                }), 404

            return jsonify({
                'code': 0,
                'msg': '获取卡片信息成功',
                'data': dict(card)
            })

        except Exception as e:
            logger.error(f"获取NFC卡片信息失败: {str(e)}")
            return jsonify({
                'code': 500,
                'msg': f'获取NFC卡片信息失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()




nfc_service = NFCService()
