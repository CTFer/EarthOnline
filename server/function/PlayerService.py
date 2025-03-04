# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-04 23:29:47
# LastEditTime: 2025-03-04 21:06:52
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import sqlite3
import os
import logging
import json
import time
from typing import Dict, List, Optional
from utils.response_handler import ResponseHandler, StatusCode

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
        return sqlite3.connect(self.db_path)

    def get_player(self, player_id: int) -> Dict:
        """获取玩家信息"""
        logger.debug(f"获取角色信息: player_id={player_id}")
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT *
                FROM player_data 
                WHERE player_id = ?
            ''', (player_id,))

            player = cursor.fetchone()
            if not player:
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="玩家不存在"
                )

            # 将查询结果转换为字典
            columns = [col[0] for col in cursor.description]
            player_dict = dict(zip(columns, player))

            return ResponseHandler.success(
                data=player_dict,
                msg="获取玩家信息成功"
            )

        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取玩家信息失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def get_players(self) -> Dict:
        """获取所有玩家"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('''
                SELECT *
                FROM player_data 
                ORDER BY player_id ASC
            ''')

            # 将查询结果转换为字典列表
            columns = [col[0] for col in cursor.description]
            players = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return ResponseHandler.success(
                data=players,
                msg="获取玩家列表成功"
            )

        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取玩家列表失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def update_player(self, player_id: int, data: Dict) -> Dict:
        """更新玩家信息"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 检查玩家是否存在
            cursor.execute('SELECT 1 FROM player_data WHERE player_id = ?', (player_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="玩家不存在"
                )

            cursor.execute('''
                UPDATE player_data 
                SET player_name = ?,
                    points = ?,
                    level = ?
                WHERE player_id = ?
            ''', (data['player_name'], data['points'], data['level'], player_id))

            conn.commit()

            return ResponseHandler.success(
                msg="更新玩家信息成功"
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"更新玩家信息失败: {str(e)}"
            )
        finally:
            if conn:
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
            return ResponseHandler.success(
                msg="删除玩家成功"
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"删除玩家失败: {str(e)}"
            )
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

            return ResponseHandler.success(
                data={"id": player_id},
                msg="添加玩家成功"
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"添加玩家失败: {str(e)}"
            )
        finally:
            conn.close()

player_service = PlayerService() 