# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-12 20:04:48
# LastEditTime: 2025-03-04 21:44:23
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import os
import time
import sqlite3
from typing import Dict, List, Optional, Union
from utils.response_handler import ResponseHandler, StatusCode

class GameCardService:
    '''
    道具卡服务
    定义道具卡片的获取和管理
    '''
    def __init__(self):
        """初始化道具卡服务"""
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'game.db')
    
    def get_db_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_game_cards(self, page: int = 1, limit: int = 20) -> Dict:
        """
        获取道具卡列表
        :param page: 页码
        :param limit: 每页数量
        :return: 包含道具卡列表和总数的字典
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 计算偏移量
            offset = (page - 1) * limit
            
            # 获取总数
            cursor.execute('SELECT COUNT(*) FROM game_card')
            total = cursor.fetchone()[0]
            
            # 获取分页数据
            cursor.execute('''
                SELECT *
                FROM game_card 
                ORDER BY id DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            game_cards = [dict(row) for row in cursor.fetchall()]
            
            return ResponseHandler.success(data={
                'items': game_cards,
                'total': total
            }, msg='获取道具卡列表成功')
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.INTERNAL_ERROR.value,
                msg=f'获取道具卡列表失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def get_game_card(self, game_card_id: int) -> Dict:
        """
        获取单个道具卡信息
        :param game_card_id: 道具卡ID
        :return: 道具卡信息字典
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, en_name, description, method, addtime, icon
                FROM game_card 
                WHERE id = ?
            ''', (game_card_id,))
            
            row = cursor.fetchone()
            if not row:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND.value,
                    msg='道具卡不存在'
                )
            
            return ResponseHandler.success(
                data=dict(row),
                msg='获取道具卡信息成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.INTERNAL_ERROR.value,
                msg=f'获取道具卡信息失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def create_game_card(self, data: Dict) -> Dict:
        """
        创建新道具卡
        :param data: 道具卡数据字典
        :return: 创建结果
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            current_time = int(time.time())
            
            cursor.execute('''
                INSERT INTO game_card (name, en_name, description, method, addtime, icon)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('en_name'),
                data.get('description'),
                data.get('method'),
                current_time,
                data.get('icon')
            ))
            
            game_card_id = cursor.lastrowid
            conn.commit()
            
            return ResponseHandler.success(
                data={'id': game_card_id},
                msg='创建道具卡成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.INTERNAL_ERROR.value,
                msg=f'创建道具卡失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def update_game_card(self, game_card_id: int, data: Dict) -> Dict:
        """
        更新道具卡信息
        :param game_card_id: 道具卡ID
        :param data: 更新数据字典
        :return: 更新结果
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            update_data = {
                'name': data.get('name'),
                'en_name': data.get('en_name'),
                'description': data.get('description'),
                'method': data.get('method'),
                'icon': data.get('icon')
            }
            
            cursor.execute('''
                UPDATE game_card
                SET name = ?,
                    en_name = ?,
                    description = ?,
                    method = ?,
                    icon = ?
                WHERE id = ?
            ''', (
                update_data['name'],
                update_data['en_name'],
                update_data['description'],
                update_data['method'],
                update_data['icon'],
                game_card_id
            ))
            
            if cursor.rowcount == 0:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND.value,
                    msg='未找到要更新的道具卡'
                )
            
            conn.commit()
            
            # 获取更新后的数据
            cursor.execute('SELECT * FROM game_card WHERE id = ?', (game_card_id,))
            updated_game_card = cursor.fetchone()
            
            return ResponseHandler.success(
                data=dict(updated_game_card),
                msg='更新道具卡成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.INTERNAL_ERROR.value,
                msg=f'更新道具卡失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def delete_game_card(self, game_card_id: int) -> Dict:
        """
        删除道具卡
        :param game_card_id: 道具卡ID
        :return: 删除结果
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM game_card WHERE id = ?', (game_card_id,))
            conn.commit()
            
            return ResponseHandler.success(msg='删除道具卡成功')
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.INTERNAL_ERROR.value,
                msg=f'删除道具卡失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def get_icon_list(self) -> Dict:
        """获取图标列表"""
        try:
            icons = []
            icon_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'game_card')
            for filename in os.listdir(icon_dir):
                if filename.endswith(('.png', '.svg', '.jpg', '.jpeg', '.gif')):
                    icons.append(filename)
            return ResponseHandler.success(
                data=icons,
                msg='获取图标列表成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.INTERNAL_ERROR.value,
                msg=f'获取图标列表失败: {str(e)}'
            )

# 创建全局实例
game_card_service = GameCardService()
