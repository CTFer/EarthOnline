# -*- coding: utf-8 -*-
"""
教师系统独立启动脚本
"""
import os
import sys

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from app import teacher_app

if __name__ == "__main__":
    print("=" * 50)
    print("教师系统启动中...")
    print("=" * 50)
    
    # 初始化数据库
    try:
        from database.init_teacher_db import init_teacher_database
        init_teacher_database()
        print("✓ 数据库初始化完成")
    except Exception as e:
        print(f"✗ 数据库初始化失败: {e}")
    
    print("\n访问地址:")
    print("  - 公共展示: http://localhost:5001/teacher/public/")
    print("  - 教师管理: http://localhost:5001/teacher/admin/login")
    print("  - 学生入口: http://localhost:5001/teacher/student/login")
    print("  - API接口: http://localhost:5001/teacher/api/")
    print("\n默认管理员账户:")
    print("  手机号: admin")
    print("  密码: admin123")
    print("\n按 Ctrl+C 停止服务")
    print("=" * 50)
    
    # 启动应用
    teacher_app.run(
        debug=True,
        host='0.0.0.0',
        port=5001,
        threaded=True
    )
