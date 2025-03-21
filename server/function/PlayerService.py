# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-04 23:29:47
# LastEditTime: 2025-03-21 22:59:05
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import sqlite3
import os
import logging
import json
import time
import hashlib
from typing import Dict, List, Optional
from flask import session, request
from utils.response_handler import ResponseHandler, StatusCode
from config.config import DEBUG
from functools import wraps

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

    def encrypt_password(self, password):
        """使用MD5加密密码"""
        if not password:
            raise ValueError("密码不能为空")
        return hashlib.md5(password.encode('utf-8')).hexdigest()

    def login(self, player_id, password):
        """玩家登录"""
        logger.info(f"尝试登录玩家ID: {player_id}")
        conn = None
        try:
            if not player_id or not password:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="玩家ID和密码不能为空"
                )
                
            # 验证玩家ID和密码
            conn = self.get_db()
            cursor = conn.cursor()

            # 获取玩家信息
            cursor.execute('''
                SELECT player_id, player_name, password, level, points, create_time
                FROM player_data 
                WHERE player_id = ?
            ''', (player_id,))

            player = cursor.fetchone()
            
            if not player:
                logger.warning(f"玩家不存在: {player_id}")
                return ResponseHandler.error(
                    code=StatusCode.USER_NOT_FOUND,
                    msg="玩家不存在"
                )
                            
            # 直接比较加密后的密码字符串
            if player[2] == password:  # 前端已经用相同的方式加密
                # 设置session
                session['is_player'] = True
                session['player_id'] = player[0]
                session['player_name'] = player[1]
                session['level'] = player[3]
                session['points'] = player[4]
                
                logger.info(f"玩家 {player[1]} 登录成功")
                return ResponseHandler.success(
                    data={
                        "player_id": player[0],
                        "player_name": player[1],
                        "level": player[3],
                        "points": player[4]
                    },
                    msg="登录成功"
                )
            else:
                logger.warning(f"密码错误: {player_id}")
                return ResponseHandler.error(
                    code=StatusCode.PASSWORD_ERROR,
                    msg="密码错误"
                )

        except Exception as e:
            logger.error(f"登录失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"登录失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def logout(self):
        """玩家登出"""
        try:
            player_name = session.get('player_name')
            logger.info(f"玩家 {player_name} 正在登出")
            
            # 清除session
            session.pop('is_player', None)
            session.pop('player_id', None)
            session.pop('player_name', None)
            session.pop('level', None)
            session.pop('points', None)
            
            logger.info(f"玩家 {player_name} 登出成功")
            return ResponseHandler.success(msg="登出成功")
        except Exception as e:
            logger.error(f"登出过程发生错误: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"登出失败: {str(e)}"
            )

    def check_login(self):
        """检查玩家登录状态"""
        logger.info(f"检查玩家登录状态: {session.get('is_player', False)}")
        if session.get('is_player', False):
            return session.get('player_id')
        else:
            return False

    def player_required(self, f):
        """玩家认证装饰器"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session.get('is_player'):
                logger.warning(f"未授权访问: {request.path}")
                return ResponseHandler.error(
                    code=StatusCode.UNAUTHORIZED,
                    msg="需要玩家登录"
                )
            return f(*args, **kwargs)
        return decorated_function

    def get_player_by_wechat_userid(self, wechat_userid):
        """根据企业微信用户ID获取玩家信息"""
        try:
            if DEBUG:
                wechat_userid = 'duyucheng'
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM player_data WHERE wechat_userid = ?', (wechat_userid,))
            player = cursor.fetchone()
            if player:
                # 获取列名并将查询结果转换为字典
                columns = [col[0] for col in cursor.description]
                player_dict = dict(zip(columns, player))
                return ResponseHandler.success(data=player_dict, msg="获取玩家信息成功")
            else:
                return ResponseHandler.error(code=StatusCode.PLAYER_NOT_FOUND, msg="玩家不存在")
        except sqlite3.Error as e:
            logger.error(f"获取玩家信息失败: {str(e)}")
            return ResponseHandler.error(code=StatusCode.SERVER_ERROR, msg="获取玩家信息失败")
        finally:
            conn.close()
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