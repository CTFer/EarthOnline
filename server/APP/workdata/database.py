# -*- coding: utf-8 -*-

"""
数据库操作工具类
支持SQLite数据库的动态连接和CRUD操作
"""
import os
import sqlite3
import json
from typing import Dict, List, Any, Tuple, Optional

class SQLiteDatabase:
    """SQLite数据库操作类"""
    
    def __init__(self, db_path: str):
        """初始化数据库连接
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """建立数据库连接"""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
        
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # 启用外键约束
        self.conn.execute("PRAGMA foreign_keys = ON")
        # 设置返回字典格式的结果
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
    
    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        """上下文管理器进入"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.close()
    
    def get_tables(self) -> List[str]:
        """获取数据库中的所有表格
        
        Returns:
            表格名列表
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = self.cursor.fetchall()
        # 过滤系统表
        return [table[0] for table in tables if not table[0].startswith('sqlite_')]
    
    def get_table_structure(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表格结构
        
        Args:
            table_name: 表格名称
        
        Returns:
            表格结构信息列表
        """
        self.cursor.execute(f"PRAGMA table_info({table_name});")
        columns = self.cursor.fetchall()
        
        structure = []
        for col in columns:
            structure.append({
                'cid': col[0],
                'name': col[1],
                'type': col[2],
                'notnull': bool(col[3]),
                'dflt_value': col[4],
                'pk': bool(col[5])
            })
        
        return structure
    
    def get_primary_key(self, table_name: str) -> Optional[str]:
        """获取表格的主键字段名
        
        Args:
            table_name: 表格名称
        
        Returns:
            主键字段名，如果没有返回None
        """
        structure = self.get_table_structure(table_name)
        for col in structure:
            if col['pk']:
                return col['name']
        return None
    
    def get_table_data(self, table_name: str, page: int = 1, limit: int = 20, 
                      keyword: str = None, order_by: str = None, 
                      order_dir: str = 'ASC') -> Dict[str, Any]:
        """获取表格数据，支持分页和搜索
        
        Args:
            table_name: 表格名称
            page: 页码，从1开始
            limit: 每页记录数
            keyword: 搜索关键词
            order_by: 排序字段
            order_dir: 排序方向，'ASC'或'DESC'
        
        Returns:
            包含数据和分页信息的字典
        """
        # 验证排序方向
        if order_dir not in ['ASC', 'DESC']:
            order_dir = 'ASC'
        
        # 构建基础查询
        base_query = f"SELECT * FROM {table_name}"
        count_query = f"SELECT COUNT(*) FROM {table_name}"
        params = []
        
        # 添加搜索条件
        where_clause = ""
        if keyword:
            # 获取表格结构
            structure = self.get_table_structure(table_name)
            search_conditions = []
            
            for col in structure:
                # 只对TEXT类型的字段进行模糊搜索
                if col['type'].upper() in ['TEXT', 'VARCHAR', 'CHAR']:
                    search_conditions.append(f"{col['name']} LIKE ?")
                    params.append(f"%{keyword}%")
            
            if search_conditions:
                where_clause = " WHERE " + " OR ".join(search_conditions)
        
        # 添加排序
        order_clause = ""
        if order_by:
            # 验证排序字段是否存在
            structure = self.get_table_structure(table_name)
            valid_columns = [col['name'] for col in structure]
            if order_by in valid_columns:
                order_clause = f" ORDER BY {order_by} {order_dir}"
        elif self.get_primary_key(table_name):
            # 如果没有指定排序字段，默认按主键排序
            order_clause = f" ORDER BY {self.get_primary_key(table_name)} {order_dir}"
        
        # 获取总数
        self.cursor.execute(count_query + where_clause, params)
        total = self.cursor.fetchone()[0]
        
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 执行查询
        self.cursor.execute(base_query + where_clause + order_clause + " LIMIT ? OFFSET ?", 
                          params + [limit, offset])
        rows = self.cursor.fetchall()
        
        # 转换为字典列表
        data = []
        for row in rows:
            data.append(dict(row))
        
        # 计算总页数
        total_pages = (total + limit - 1) // limit
        
        return {
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': total_pages,
            'data': data
        }
    
    def insert_data(self, table_name: str, data: Dict[str, Any]) -> int:
        """插入数据
        
        Args:
            table_name: 表格名称
            data: 要插入的数据字典
        
        Returns:
            插入的记录ID
        """
        # 获取表格结构，验证字段
        structure = self.get_table_structure(table_name)
        valid_columns = [col['name'] for col in structure]
        
        # 过滤有效字段
        valid_data = {k: v for k, v in data.items() if k in valid_columns}
        
        if not valid_data:
            raise ValueError("没有有效的字段可以插入")
        
        # 构建SQL语句
        columns = ', '.join(valid_data.keys())
        placeholders = ', '.join(['?'] * len(valid_data))
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        # 执行插入
        self.cursor.execute(sql, list(valid_data.values()))
        self.conn.commit()
        
        return self.cursor.lastrowid
    
    def update_data(self, table_name: str, pk_value: Any, data: Dict[str, Any]) -> int:
        """更新数据
        
        Args:
            table_name: 表格名称
            pk_value: 主键值
            data: 要更新的数据字典
        
        Returns:
            更新的记录数
        """
        # 获取主键字段
        pk_field = self.get_primary_key(table_name)
        if not pk_field:
            raise ValueError("表格没有主键，无法更新")
        
        # 获取表格结构，验证字段
        structure = self.get_table_structure(table_name)
        valid_columns = [col['name'] for col in structure if col['name'] != pk_field]
        
        # 过滤有效字段
        valid_data = {k: v for k, v in data.items() if k in valid_columns}
        
        if not valid_data:
            raise ValueError("没有有效的字段可以更新")
        
        # 构建SQL语句
        set_clause = ', '.join([f"{k} = ?" for k in valid_data.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE {pk_field} = ?"
        
        # 执行更新
        params = list(valid_data.values()) + [pk_value]
        self.cursor.execute(sql, params)
        self.conn.commit()
        
        return self.cursor.rowcount
    
    def delete_data(self, table_name: str, pk_value: Any) -> int:
        """删除数据
        
        Args:
            table_name: 表格名称
            pk_value: 主键值
        
        Returns:
            删除的记录数
        """
        # 获取主键字段
        pk_field = self.get_primary_key(table_name)
        if not pk_field:
            raise ValueError("表格没有主键，无法删除")
        
        # 构建SQL语句
        sql = f"DELETE FROM {table_name} WHERE {pk_field} = ?"
        
        # 执行删除
        self.cursor.execute(sql, [pk_value])
        self.conn.commit()
        
        return self.cursor.rowcount
    
    def execute_query(self, query: str, params: List[Any] = None) -> List[Dict[str, Any]]:
        """执行自定义查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
        
        Returns:
            查询结果列表
        """
        self.cursor.execute(query, params or [])
        rows = self.cursor.fetchall()
        
        # 转换为字典列表
        data = []
        for row in rows:
            data.append(dict(row))
        
        return data

# 数据库管理类
class DatabaseManager:
    """数据库管理器，用于管理多个数据库"""
    
    @staticmethod
    def get_database_list(database_dir: str = 'd:/code/EarthOnline/server/APP/workdata/database') -> List[str]:
        """获取数据库目录中的所有SQLite数据库文件
        
        Args:
            database_dir: 数据库目录路径
        
        Returns:
            数据库文件名列表
        """
        if not os.path.exists(database_dir):
            return []
        
        db_files = []
        for file in os.listdir(database_dir):
            if file.endswith('.db') or file.endswith('.sqlite3'):
                db_files.append(file)
        
        return sorted(db_files)
    
    @staticmethod
    def get_database_path(db_name: str, database_dir: str = 'd:/code/EarthOnline/server/APP/workdata/database') -> str:
        """获取数据库文件的完整路径
        
        Args:
            db_name: 数据库文件名
            database_dir: 数据库目录路径
        
        Returns:
            数据库文件的完整路径
        """
        return os.path.join(database_dir, db_name)
    
    @staticmethod
    def validate_database(db_name: str, database_dir: str = 'd:/code/EarthOnline/server/APP/workdata/database') -> bool:
        """验证数据库文件是否存在且是有效的SQLite文件
        
        Args:
            db_name: 数据库文件名
            database_dir: 数据库目录路径
        
        Returns:
            是否有效
        """
        db_path = DatabaseManager.get_database_path(db_name, database_dir)
        
        if not os.path.exists(db_path):
            return False
        
        # 检查文件是否为SQLite文件
        try:
            with sqlite3.connect(db_path) as conn:
                conn.execute("SELECT sqlite_version()")
                return True
        except:
            return False
    
    @staticmethod
    def create_database(db_name: str, database_dir: str = 'd:/code/EarthOnline/server/APP/workdata/database') -> bool:
        """创建新的SQLite数据库文件
        
        Args:
            db_name: 数据库文件名
            database_dir: 数据库目录路径
        
        Returns:
            是否创建成功
        """
        # 确保目录存在
        os.makedirs(database_dir, exist_ok=True)
        
        db_path = DatabaseManager.get_database_path(db_name, database_dir)
        
        # 如果文件已存在，返回False
        if os.path.exists(db_path):
            return False
        
        try:
            # 创建空数据库
            conn = sqlite3.connect(db_path)
            conn.close()
            return True
        except:
            return False