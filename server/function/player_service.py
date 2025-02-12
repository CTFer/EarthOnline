# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-04 23:29:47
# LastEditTime: 2025-02-05 11:30:49
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class PlayerService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlayerService, cls).__new__(cls)
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

    def get_player(self, player_id):
        """获取角色信息"""
        logger.debug(f"获取角色信息: player_id={player_id}")
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM player_data where player_id=?', (player_id,))
            columns = [description[0] for description in cursor.description]
            character = cursor.fetchone()

            if character:
                player_data = dict(zip(columns, character))
                return json.dumps({
                    'code': 0,
                    'msg': '获取角色信息成功',
                    'data': {
                        'player_id': player_data['player_id'],
                        'stamina': player_data['stamina'],
                        'sex': player_data['sex'],
                        'player_name': player_data['player_name'],
                        'points': player_data['points'],
                        'create_time': player_data['create_time'],
                        'level': player_data['level'],
                        'experience': player_data['experience']
                    }
                })
            else:
                return json.dumps({
                    'code': 1,
                    'msg': '角色不存在',
                    'data': None
                }), 404

        except sqlite3.Error as e:
            print("Database error:", str(e))
            return json.dumps({
                'code': 2,
                'msg': f'数据库错误: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()

    def get_players(self):
        """获取所有玩家"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT *
                FROM player_data 
                ORDER BY player_id ASC
            ''')

            players = [dict(row) for row in cursor.fetchall()]

            return json.dumps({
                "code": 0,
                "msg": "获取玩家列表成功",
                "data": players
            })

        except Exception as e:
            print(f"获取玩家列表出错: {str(e)}")
            return json.dumps({
                "code": 1,
                "msg": f"获取玩家列表失败: {str(e)}",
                "data": None
            }), 500
        finally:
            if conn:
                conn.close()
    def update_player(self, player_id,data):
        """更新玩家信息"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            print(data)
            cursor.execute('''
                UPDATE player_data 
                SET player_name = ?,
                points = ?,
                level = ?
                WHERE player_id = ?
            ''', (data['player_name'], data['points'], data['level'], player_id,))

            conn.commit()
            return json.dumps({"success": True})
        except Exception as e:
            print(f"Error in update_player: {str(e)}")
            return json.dumps({'error': str(e)}), 500
        finally:
            conn.close()

    def delete_player(self, player_id):
        """删除玩家"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 删除玩家相关的任务
            cursor.execute('DELETE FROM player_task WHERE player_id = ?', (player_id,))

            # 删除玩家
            cursor.execute('DELETE FROM player_data WHERE player_id = ?', (player_id,))

            conn.commit()
            return json.dumps({"code": 0, "msg": "删除玩家成功"})
        except Exception as e:
            print(f"Error in delete_player: {str(e)}")
            return json.dumps({'code': 1, 'msg': str(e)}), 500
        finally:
            conn.close()

    def add_player(self, data):
        """添加新玩家"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO player_data (player_name, english_name, level, points, create_time)
                VALUES (?, ?, ?, ?, datetime('now'))
            ''', (data['player_name'], data['english_name'], data['level'], data['points']))

            player_id = cursor.lastrowid
            conn.commit()

            return json.dumps({
                "code": 0,
                "msg": "添加玩家成功",
                "data": {"id": player_id}
            }), 201
        except Exception as e:
            print(f"Error in add_player: {str(e)}")
            return json.dumps({'code': 1, 'msg': str(e)}), 500
        finally:
            conn.close()

player_service = PlayerService() 