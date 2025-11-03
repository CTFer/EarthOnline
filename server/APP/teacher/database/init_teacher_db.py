# -*- coding: utf-8 -*-
"""
教师系统数据库初始化脚本
"""
import sqlite3
import os
import hashlib
from datetime import datetime

def init_teacher_database():
    """初始化教师系统数据库"""
    db_path = os.path.join(os.path.dirname(__file__), 'teacher.db')
    
    # 确保数据库目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 检查并升级现有数据库
        upgrade_database(cursor)
        # 创建教师用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_user (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                phone VARCHAR(20) UNIQUE,
                password VARCHAR(64) NOT NULL,
                name VARCHAR(50) NOT NULL,
                avatar VARCHAR(200),
                introduction TEXT,
                education TEXT,
                experience TEXT,
                specialties TEXT,
                philosophy TEXT,
                status TINYINT DEFAULT 1,
                last_login DATETIME,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建班级表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_class (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                class_code VARCHAR(20) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                status TINYINT DEFAULT 1,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teacher_user(id)
            )
        ''')
        
        # 创建学生表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_student (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                name VARCHAR(50) NOT NULL,
                student_no VARCHAR(50),
                phone VARCHAR(20),
                parent_name VARCHAR(50),
                parent_phone VARCHAR(20),
                notes TEXT,
                status TINYINT DEFAULT 1,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teacher_user(id)
            )
        ''')
        
        # 创建学生班级关联表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_student_class (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                class_id INTEGER NOT NULL,
                join_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TINYINT DEFAULT 1,
                FOREIGN KEY (student_id) REFERENCES teacher_student(id),
                FOREIGN KEY (class_id) REFERENCES teacher_class(id),
                UNIQUE(student_id, class_id)
            )
        ''')
        
        # 创建材料表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_material (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                type VARCHAR(10) NOT NULL,
                file_name VARCHAR(200) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_url VARCHAR(500),
                file_size BIGINT,
                file_duration INTEGER,
                description TEXT,
                deadline DATETIME,
                is_public TINYINT DEFAULT 0,
                status TINYINT DEFAULT 1,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teacher_user(id)
            )
        ''')
        
        # 创建材料分发表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_material_target (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                target_type VARCHAR(10) NOT NULL,
                target_id INTEGER NOT NULL,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES teacher_material(id)
            )
        ''')
        
        # 创建完成状态表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_completion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL,
                student_id INTEGER NOT NULL,
                status TINYINT DEFAULT 0,
                progress INTEGER DEFAULT 0,
                last_position INTEGER DEFAULT 0,
                complete_time DATETIME,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (material_id) REFERENCES teacher_material(id),
                FOREIGN KEY (student_id) REFERENCES teacher_student(id),
                UNIQUE(material_id, student_id)
            )
        ''')
        
        # 创建活动表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT,
                start_time DATETIME NOT NULL,
                end_time DATETIME NOT NULL,
                location VARCHAR(200),
                location_type VARCHAR(10) DEFAULT 'offline',
                max_participants INTEGER,
                current_participants INTEGER DEFAULT 0,
                registration_required TINYINT DEFAULT 0,
                status TINYINT DEFAULT 1,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teacher_user(id)
            )
        ''')
        
        # 创建课程表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_course (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                name VARCHAR(200) NOT NULL,
                description TEXT,
                target_age VARCHAR(50),
                difficulty VARCHAR(20),
                duration INTEGER,
                price DECIMAL(10,2),
                is_online TINYINT DEFAULT 0,
                status TINYINT DEFAULT 1,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                update_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teacher_user(id)
            )
        ''')
        
        # 创建文件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS teacher_file (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                teacher_id INTEGER NOT NULL,
                original_name VARCHAR(200) NOT NULL,
                stored_name VARCHAR(200) NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                file_url VARCHAR(500),
                file_size BIGINT NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                mime_type VARCHAR(100) NOT NULL,
                hash_md5 VARCHAR(32),
                status TINYINT DEFAULT 1,
                create_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teacher_user(id)
            )
        ''')
        
        # 创建索引
        create_indexes(cursor)
        
        # 创建默认管理员账户
        create_default_admin(cursor)
        
        conn.commit()
        print("教师系统数据库初始化完成")
        
    except Exception as e:
        print(f"数据库初始化失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_indexes(cursor):
    """创建数据库索引"""
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_teacher_user_username ON teacher_user(username)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_user_phone ON teacher_user(phone)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_user_status ON teacher_user(status)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_class_teacher_id ON teacher_class(teacher_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_class_code ON teacher_class(class_code)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_class_status ON teacher_class(status)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_student_teacher_id ON teacher_student(teacher_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_student_name ON teacher_student(name)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_student_status ON teacher_student(status)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_student_class_student_id ON teacher_student_class(student_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_student_class_class_id ON teacher_student_class(class_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_student_class_unique ON teacher_student_class(student_id, class_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_material_teacher_id ON teacher_material(teacher_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_material_type ON teacher_material(type)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_material_deadline ON teacher_material(deadline)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_material_status ON teacher_material(status)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_material_target_material_id ON teacher_material_target(material_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_material_target_type_id ON teacher_material_target(target_type, target_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_completion_material_id ON teacher_completion(material_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_completion_student_id ON teacher_completion(student_id)",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_teacher_completion_unique ON teacher_completion(material_id, student_id)",
        "CREATE INDEX IF NOT EXISTS idx_teacher_completion_status ON teacher_completion(status)"
    ]
    
    for index_sql in indexes:
        cursor.execute(index_sql)

def upgrade_database(cursor):
    """升级现有数据库结构"""
    try:
        # 检查是否存在username列
        cursor.execute("PRAGMA table_info(teacher_user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'username' not in columns:
            print("检测到旧版本数据库，正在升级...")
            
            # 添加username列
            cursor.execute("ALTER TABLE teacher_user ADD COLUMN username VARCHAR(50)")
            
            # 为现有用户生成用户名（基于手机号）
            cursor.execute("SELECT id, phone FROM teacher_user WHERE phone IS NOT NULL")
            users = cursor.fetchall()
            
            for user_id, phone in users:
                if phone:
                    # 使用手机号作为用户名
                    cursor.execute("UPDATE teacher_user SET username = ? WHERE id = ?", (phone, user_id))
            
            # 为没有手机号的用户设置默认用户名
            cursor.execute("UPDATE teacher_user SET username = 'user_' || id WHERE username IS NULL")
            
            # 设置username为NOT NULL
            cursor.execute("UPDATE teacher_user SET username = 'user_' || id WHERE username IS NULL")
            
            print("数据库升级完成")
            
    except Exception as e:
        print(f"数据库升级失败: {e}")

def create_default_admin(cursor):
    """创建默认管理员账户"""
    # 检查是否已存在管理员
    cursor.execute("SELECT COUNT(*) FROM teacher_user WHERE username = 'admin'")
    if cursor.fetchone()[0] > 0:
        return
    
    # 创建默认管理员
    default_password = hashlib.md5('admin123'.encode()).hexdigest()
    cursor.execute('''
        INSERT INTO teacher_user (username, phone, password, name, introduction, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', '13800138000', default_password, '系统管理员', '默认管理员账户，请及时修改密码', 1))

if __name__ == "__main__":
    init_teacher_database()
