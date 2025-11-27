# -*- coding: utf-8 -*-
import os
import sqlite3
import hashlib

# 数据库路径
DB_PATH = os.path.join('d:\code\EarthOnline\server\database', 'user.db')

print(f"用户数据库路径: {DB_PATH}")
print("初始化用户数据库...")

# 确保数据库目录存在
db_dir = os.path.dirname(DB_PATH)
os.makedirs(db_dir, exist_ok=True)

# 连接数据库
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS user (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT,
        remark TEXT,
        created_at TEXT
    )
    ''')
    
    # 检查是否已有用户
    cursor.execute("SELECT COUNT(*) FROM user")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        # 创建管理员用户，密码使用MD5加密
        admin_username = 'emanon'
        admin_password = '325299'
        # 计算密码的MD5哈希
        md5_hash = hashlib.md5(admin_password.encode()).hexdigest()
        
        # 插入管理员用户
        cursor.execute(
            "INSERT INTO user (username, password, role, remark, created_at) VALUES (?, ?, ?, ?, datetime('now'))",
            (admin_username, md5_hash, 'admin', '系统管理员',)
        )
        
        print(f"\n管理员用户创建成功！")
        print(f"用户名: {admin_username}")
        print(f"密码: {admin_password}")
        print(f"密码哈希(MD5): {md5_hash}")
    else:
        print("\n用户表中已有用户记录，跳过管理员创建")
        # 显示现有用户
        cursor.execute("SELECT id, username, role FROM user")
        users = cursor.fetchall()
        print("\n现有用户列表:")
        for user in users:
            print(f"  ID: {user[0]}, 用户名: {user[1]}, 角色: {user[2]}")
    
    # 提交更改
    conn.commit()
    print("\n用户数据库初始化完成！")
    
    # 显示表结构
    print("\n用户表结构:")
    cursor.execute("PRAGMA table_info(user)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
        
finally:
    # 关闭连接
    conn.close()
    print("\n数据库连接已关闭")