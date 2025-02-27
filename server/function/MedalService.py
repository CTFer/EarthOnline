# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-12 20:04:48
# LastEditTime: 2025-02-27 13:20:49
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import os
import time
import sqlite3
from typing import Dict, List, Optional, Union

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
            cursor.execute('SELECT COUNT(*) FROM medals')
            total = cursor.fetchone()[0]
            
            # 获取分页数据
            cursor.execute('''
                SELECT id, name, description, addtime, icon, conditions
                FROM medals 
                ORDER BY id DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            
            medals = [dict(row) for row in cursor.fetchall()]
            
            return {
                'code': 0,
                'msg': '',
                'count': total,
                'data': medals
            }
        except Exception as e:
            return {
                'code': 500,
                'msg': str(e),
                'count': 0,
                'data': []
            }
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
                FROM medals 
                WHERE id = ?
            ''', (medal_id,))
            
            row = cursor.fetchone()
            if not row:
                return {
                    'code': 404,
                    'msg': '勋章不存在',
                    'data': None
                }
            
            return {
                'code': 0,
                'msg': '',
                'data': dict(row)
            }
        except Exception as e:
            return {
                'code': 500,
                'msg': str(e),
                'data': None
            }
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
                INSERT INTO medals (name, description, addtime, icon, conditions)
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
            
            return {
                'code': 0,
                'msg': '创建成功',
                'data': {'id': medal_id}
            }
        except Exception as e:
            return {
                'code': 500,
                'msg': str(e),
                'data': None
            }
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
                UPDATE medals
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
                return {
                    'code': 404,
                    'msg': '未找到要更新的勋章',
                    'data': None
                }
            
            conn.commit()
            
            # 获取更新后的数据
            cursor.execute('SELECT * FROM medals WHERE id = ?', (medal_id,))
            updated_medal = cursor.fetchone()
            
            return {
                'code': 0,
                'msg': '更新成功',
                'data': dict(updated_medal) if updated_medal else None
            }
        except Exception as e:
            return {
                'code': 500,
                'msg': str(e),
                'data': None
            }
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
            
            cursor.execute('DELETE FROM medals WHERE id = ?', (medal_id,))
            conn.commit()
            
            return {
                'code': 0,
                'msg': '删除成功',
                'data': None
            }
        except Exception as e:
            return {
                'code': 500,
                'msg': str(e),
                'data': None
            }
        finally:
            if conn:
                conn.close()
    
    def get_icon_list(self) -> List[str]:
        """获取图标列表"""
        icons = []
        icon_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'img', 'medal')
        for filename in os.listdir(icon_dir):
            if filename.endswith(('.png', '.svg', '.jpg', '.jpeg', '.gif')):
                icons.append(filename)
        return icons

    def get_wordcloud_medals(self) -> Dict:
        """
        获取用于词云显示的勋章数据
        :return: 包含勋章名称列表的字典
        """
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # 联合查询获取正在展示的勋章名称
            cursor.execute('''
                SELECT m.name, pm.level
                FROM player_medal pm
                JOIN medals m ON pm.medal_id = m.id
                WHERE pm.show = 1
            ''')
            
            # 获取所有勋章名称
            medals = [(row['name'], row['level']) for row in cursor.fetchall()]
            
            return {
                'code': 0,
                'msg': '获取成功',
                'data': medals
            }
        except Exception as e:
            return {
                'code': 500,
                'msg': str(e),
                'data': None
            }
        finally:
            if conn:
                conn.close()

# 创建全局实例
medal_service = MedalService()
