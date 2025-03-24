# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-12 20:04:48
# LastEditTime: 2025-03-21 20:12:32
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import os
import time
import sqlite3
from typing import Dict, List, Optional, Union
from utils.response_handler import ResponseHandler, StatusCode

class MedalService:
    '''
    勋章服务
    定义勋章的获取和管理
    '''
    def __init__(self):
        """初始化勋章服务"""
        self.db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'game.db')
    
    def get_db_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_medals(self, page: int = 1, limit: int = 20) -> Dict:
        """
        获取勋章列表
        :param page: 页码
        :param limit: 每页数量
        :return: 包含勋章列表和总数的字典
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 计算偏移量
            offset = (page - 1) * limit
            
            # 获取总数
            cursor.execute('SELECT COUNT(*) FROM medal')
            total = cursor.fetchone()[0]
            
            # 获取分页数据
            cursor.execute('''
                SELECT id, name, description, addtime, icon, conditions
                FROM medal 
                ORDER BY id DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            medals = [dict(row) for row in cursor.fetchall()]
            
            return ResponseHandler.success(
                data={
                    'items': medals,
                    'total': total
                },
                msg='获取勋章列表成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'获取勋章列表失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def get_medal(self, medal_id: int) -> Dict:
        """
        获取单个勋章信息
        :param medal_id: 勋章ID
        :return: 勋章信息字典
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, name, description, addtime, icon, conditions
                FROM medal 
                WHERE id = ?
            ''', (medal_id,))
            
            row = cursor.fetchone()
            if not row:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg='勋章不存在'
                )
            
            return ResponseHandler.success(
                data=dict(row),
                msg='获取勋章信息成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'获取勋章信息失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def create_medal(self, data: Dict) -> Dict:
        """
        创建新勋章
        :param data: 勋章数据字典
        :return: 创建结果
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            current_time = int(time.time())
            
            cursor.execute('''
                INSERT INTO medal (name, description, addtime, icon, conditions)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                data.get('name'),
                data.get('description'),
                current_time,
                data.get('icon'),
                data.get('conditions')
            ))
            
            medal_id = cursor.lastrowid
            conn.commit()
            
            return ResponseHandler.success(
                data={'id': medal_id},
                msg='创建勋章成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'创建勋章失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def update_medal(self, medal_id: int, data: Dict) -> Dict:
        """
        更新勋章信息
        :param medal_id: 勋章ID
        :param data: 更新数据字典
        :return: 更新结果
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            update_data = {
                'name': data.get('name'),
                'description': data.get('description'),
                'icon': data.get('icon'),
                'conditions': data.get('conditions')
            }
            
            cursor.execute('''
                UPDATE medal
                SET name = ?,
                    description = ?,
                    icon = ?,
                    conditions = ?
                WHERE id = ?
            ''', (
                update_data['name'],
                update_data['description'],
                update_data['icon'],
                update_data['conditions'],
                medal_id
            ))
            
            if cursor.rowcount == 0:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg='未找到要更新的勋章'
                )
            
            conn.commit()
            
            # 获取更新后的数据
            cursor.execute('SELECT * FROM medal WHERE id = ?', (medal_id,))
            updated_medal = cursor.fetchone()
            
            return ResponseHandler.success(
                data=dict(updated_medal) if updated_medal else None,
                msg='更新勋章成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'更新勋章失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def delete_medal(self, medal_id: int) -> Dict:
        """
        删除勋章
        :param medal_id: 勋章ID
        :return: 删除结果
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM medal WHERE id = ?', (medal_id,))
            
            if cursor.rowcount == 0:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg='未找到要删除的勋章'
                )
            
            conn.commit()
            
            return ResponseHandler.success(
                msg='删除勋章成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'删除勋章失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()
    
    def get_icon_list(self) -> Dict:
        """获取图标列表"""
        try:
            icons = []
            icon_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'medal')
            for filename in os.listdir(icon_dir):
                if filename.endswith(('.png', '.svg', '.jpg', '.jpeg', '.gif')):
                    icons.append(filename)
            return ResponseHandler.success(
                data=icons,
                msg='获取图标列表成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'获取图标列表失败: {str(e)}'
            )

    def get_wordcloud_medals(self, player_id: int) -> Dict:
        """
        获取用于词云显示的勋章数据
        :param player_id: 玩家ID
        :return: 包含勋章名称列表的字典
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 联合查询获取正在展示的勋章名称
            cursor.execute('''
                SELECT m.name, pm.level
                FROM player_medal pm
                JOIN medal m ON pm.medal_id = m.id
                WHERE pm.show = 1 AND pm.player_id = ?
            ''', (player_id,))
            
            # 获取所有勋章名称
            medals = [(row['name'], row['level']) for row in cursor.fetchall()]
            
            return ResponseHandler.success(
                data=medals,
                msg='获取词云勋章数据成功'
            )
        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f'获取词云勋章数据失败: {str(e)}'
            )
        finally:
            if conn:
                conn.close()

# 创建全局实例
medal_service = MedalService()
