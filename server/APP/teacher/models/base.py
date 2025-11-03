# -*- coding: utf-8 -*-
"""
基础模型类
"""
import sqlite3
import os
from typing import Optional, List, Dict, Any
from datetime import datetime

class BaseModel:
    """基础模型类，提供数据库操作的基础方法"""
    
    def __init__(self, db_path: str = None):
        """初始化数据库连接"""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'database', 'teacher.db')
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """执行查询并返回结果"""
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """执行更新操作并返回影响的行数"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """执行插入操作并返回新插入的ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def get_by_id(self, table_name: str, record_id: int) -> Optional[Dict[str, Any]]:
        """根据ID获取单条记录"""
        query = f"SELECT * FROM {table_name} WHERE id = ?"
        results = self.execute_query(query, (record_id,))
        return results[0] if results else None
    
    def get_all(self, table_name: str, where_clause: str = "", params: tuple = ()) -> List[Dict[str, Any]]:
        """获取所有记录"""
        query = f"SELECT * FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        return self.execute_query(query, params)
    
    def delete_by_id(self, table_name: str, record_id: int) -> int:
        """根据ID删除记录"""
        query = f"DELETE FROM {table_name} WHERE id = ?"
        return self.execute_update(query, (record_id,))
    
    def update_by_id(self, table_name: str, record_id: int, data: Dict[str, Any]) -> int:
        """根据ID更新记录"""
        if not data:
            return 0
        
        # 添加更新时间
        data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        query = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        params = list(data.values()) + [record_id]
        
        return self.execute_update(query, tuple(params))
    
    def insert(self, table_name: str, data: Dict[str, Any]) -> int:
        """插入新记录"""
        if not data:
            return 0
        
        # 添加创建时间
        data['create_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data['update_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data.keys()])
        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        return self.execute_insert(query, tuple(data.values()))
