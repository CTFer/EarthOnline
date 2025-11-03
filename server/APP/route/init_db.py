# -*- coding: utf-8 -*-
import os
import sqlite3
import hashlib

# 获取数据库路径
db_path = os.path.join(os.path.dirname(__file__), 'data.sqlite3')

print(f"数据库路径: {db_path}")
print("检查数据库结构...")

# 连接数据库
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # 检查现有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print(f"现有表: {[table[0] for table in tables]}")
    
    # 检查表结构
    for table in tables:
        print(f"\n表 {table[0]} 的结构:")
        cursor.execute(f"PRAGMA table_info({table[0]});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]}: {col[2]}")
    
    # 检查是否有id列在route表中
    cursor.execute("PRAGMA table_info(route);")
    route_columns = cursor.fetchall()
    has_id_column = any(col[1] == 'id' for col in route_columns)
    
    print(f"\nRoute表有id列: {has_id_column}")
    
    # 如果没有id列，添加id列
    if not has_id_column:
        print("向route表添加id列...")
        # 注意：在SQLite中，不能直接在已有表的中间添加主键列，需要重建表
        # 1. 创建新表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS route_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            method TEXT,
            start TEXT,
            end TEXT,
            start_x REAL,
            start_y REAL,
            end_x REAL,
            end_y REAL,
            remark TEXT,
            muti INTEGER
        )
        ''')
        # 2. 复制数据
        cursor.execute('''
        INSERT INTO route_new (date, method, start, end, start_x, start_y, end_x, end_y, remark, muti)
        SELECT date, method, start, end, start_x, start_y, end_x, end_y, remark, muti FROM route
        ''')
        # 3. 删除旧表
        cursor.execute('DROP TABLE route')
        # 4. 重命名新表
        cursor.execute('ALTER TABLE route_new RENAME TO route')
        print("已添加id列到route表")
    
    # 创建user表
    print("\n创建或更新user表...")
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT UNIQUE,
        password TEXT,
        remark TEXT
    )
    ''')
    
    # 创建默认管理员用户（密码使用MD5加密）
    admin_username = 'emanon'
    admin_password = '325299'
    # 计算MD5哈希
    md5_hash = hashlib.md5(admin_password.encode()).hexdigest()
    
    # 检查用户是否存在
    cursor.execute("SELECT * FROM user WHERE user = ?", (admin_username,))
    existing_user = cursor.fetchone()
    
    if existing_user:
        print(f"用户 {admin_username} 已存在")
    else:
        # 插入新用户
        cursor.execute(
            "INSERT INTO user (user, password, remark) VALUES (?, ?, ?)",
            (admin_username, md5_hash, '默认管理员')
        )
        print(f"已创建管理员用户: {admin_username}, 密码: {admin_password} (已加密)")
    
    # 提交更改
    conn.commit()
    print("\n数据库操作完成")
    
finally:
    # 关闭连接
    cursor.close()
    conn.close()