#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 一根鱼骨棒
@Date: 2025-02-17 15:40:00
@LastEditors: 一根鱼骨棒
@Description: 通知服务
"""
import sqlite3
import os
import logging
import time
import json
import traceback
from datetime import datetime
from typing import List, Dict, Optional, Union

logger = logging.getLogger(__name__)

class NotificationService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'database', 
                'game.db'
            )
            self.initialized = False
            self.conn = None
            self.init_db()

    def init_db(self):
        """初始化数据库连接"""
        try:
            # 确保数据库目录存在
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # 创建连接
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            
            # 创建通知表
            self.create_tables()
            
            self.initialized = True
            logger.info('通知服务数据库初始化成功')
            
        except Exception as e:
            logger.error(f'通知服务数据库初始化失败: {str(e)}')
            raise

    def create_tables(self):
        """创建必要的数据表"""
        try:
            cursor = self.conn.cursor()
            
            # 创建通知表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    type TEXT NOT NULL,
                    target_type TEXT DEFAULT 'all',
                    target_id INTEGER,
                    is_read INTEGER DEFAULT 0,
                    create_time INTEGER NOT NULL,
                    update_time INTEGER NOT NULL,
                    expire_time INTEGER,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            self.conn.commit()
            logger.info('通知表创建成功')
            
        except Exception as e:
            logger.error(f'创建通知表失败: {str(e)}')
            raise

    def get_db_connection(self):
        """获取数据库连接"""
        if not self.initialized:
            self.init_db()
        return self.conn

    def get_notifications(self, target_type='all', target_id=None, limit=50, offset=0):
        """获取通知列表"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM notification 
                WHERE status = 'active' 
                AND (target_type = ? OR target_type = 'all')
            '''
            params = [target_type]
            
            if target_id:
                query += ' AND (target_id = ? OR target_id IS NULL)'
                params.append(target_id)
                
            query += ' ORDER BY create_time DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            notifications = [dict(row) for row in cursor.fetchall()]
            
            return notifications
            
        except Exception as e:
            logger.error(f'获取通知列表失败: {str(e)}')
            raise

    def get_notification(self, notification_id):
        """获取单个通知"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM notification WHERE id = ?', (notification_id,))
            notification = cursor.fetchone()
            
            return dict(notification) if notification else None
            
        except Exception as e:
            logger.error(f'获取通知失败: {str(e)}')
            raise

    def add_notification(self, data):
        """添加新通知"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            cursor.execute('''
                INSERT INTO notification (
                    title, content, type, target_type, target_id,
                    create_time, update_time, expire_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['title'],
                data['content'],
                data['type'],
                data.get('target_type', 'all'),
                data.get('target_id'),
                current_time,
                current_time,
                data.get('expire_time')
            ))
            
            notification_id = cursor.lastrowid
            conn.commit()
            
            # 获取新创建的通知
            cursor.execute('SELECT * FROM notification WHERE id = ?', (notification_id,))
            notification = cursor.fetchone()
            
            return dict(notification)
            
        except Exception as e:
            logger.error(f'添加通知失败: {str(e)}')
            raise

    def update_notification(self, notification_id, data):
        """更新通知"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            update_fields = []
            params = []
            
            if 'title' in data:
                update_fields.append('title = ?')
                params.append(data['title'])
            if 'content' in data:
                update_fields.append('content = ?')
                params.append(data['content'])
            if 'type' in data:
                update_fields.append('type = ?')
                params.append(data['type'])
            if 'target_type' in data:
                update_fields.append('target_type = ?')
                params.append(data['target_type'])
            if 'target_id' in data:
                update_fields.append('target_id = ?')
                params.append(data['target_id'])
            if 'expire_time' in data:
                update_fields.append('expire_time = ?')
                params.append(data['expire_time'])
                
            update_fields.append('update_time = ?')
            params.append(int(time.time()))
            
            params.append(notification_id)
            
            query = f'''
                UPDATE notification 
                SET {', '.join(update_fields)}
                WHERE id = ?
            '''
            
            cursor.execute(query, params)
            conn.commit()
            
            # 获取更新后的通知
            cursor.execute('SELECT * FROM notification WHERE id = ?', (notification_id,))
            notification = cursor.fetchone()
            
            return dict(notification) if notification else None
            
        except Exception as e:
            logger.error(f'更新通知失败: {str(e)}')
            raise

    def delete_notification(self, notification_id):
        """删除通知"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE notification 
                SET status = 'deleted', update_time = ? 
                WHERE id = ?
            ''', (int(time.time()), notification_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f'删除通知失败: {str(e)}')
            raise

    def mark_as_read(self, notification_id):
        """标记通知为已读"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE notification 
                SET is_read = 1, update_time = ? 
                WHERE id = ?
            ''', (int(time.time()), notification_id))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f'标记通知已读失败: {str(e)}')
            raise

    def cleanup_expired_notifications(self):
        """清理过期通知"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            current_time = int(time.time())
            
            cursor.execute('''
                UPDATE notification 
                SET status = 'expired', update_time = ? 
                WHERE expire_time IS NOT NULL 
                AND expire_time < ? 
                AND status = 'active'
            ''', (current_time, current_time))
            
            conn.commit()
            return cursor.rowcount
            
        except Exception as e:
            logger.error(f'清理过期通知失败: {str(e)}')
            raise

# 创建全局实例
notification_service = NotificationService()
