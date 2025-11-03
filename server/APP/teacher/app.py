# -*- coding: utf-8 -*-
"""
教师系统蓝图创建
"""
import os
from flask import Blueprint, render_template, send_from_directory
try:
    from .config import TeacherConfig
    from .routes import admin_bp, student_bp, public_bp, api_bp
except ImportError:
    # 独立运行时的导入
    from config import TeacherConfig
    from routes import admin_bp, student_bp, public_bp, api_bp

def create_teacher_blueprint():
    """创建教师系统蓝图"""
    # 创建主蓝图，指定模板文件夹
    teacher_bp = Blueprint('teacher', __name__, 
                          url_prefix='/teacher',
                          template_folder='templates',
                          static_folder='static')
    
    # 根路由重定向
    @teacher_bp.route('/')
    def teacher_index():
        from flask import redirect, url_for
        return redirect(url_for('teacher.teacher_admin.login'))
    
    # 注册子蓝图
    teacher_bp.register_blueprint(admin_bp)
    teacher_bp.register_blueprint(student_bp)
    teacher_bp.register_blueprint(public_bp)
    teacher_bp.register_blueprint(api_bp)
    
    # 静态文件路由
    @teacher_bp.route('/static/<path:filename>')
    def teacher_static(filename):
        """教师系统静态文件"""
        static_folder = os.path.join(os.path.dirname(__file__), 'static')
        return send_from_directory(static_folder, filename)
    
    # 文件上传路由
    @teacher_bp.route('/uploads/<path:filename>')
    def teacher_uploads(filename):
        """教师系统上传文件"""
        upload_folder = TeacherConfig.UPLOAD_FOLDER
        return send_from_directory(upload_folder, filename)
    
    # 错误处理
    @teacher_bp.errorhandler(404)
    def not_found(error):
        """404错误处理"""
        return render_template('error.html', 
                             message='页面不存在',
                             error_code=404), 404
    
    @teacher_bp.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        return render_template('error.html', 
                             message='服务器内部错误',
                             error_code=500), 500
    
    # 初始化数据库
    init_database()
    
    return teacher_bp

def init_database():
    """初始化数据库"""
    try:
        try:
            from .database.init_teacher_db import init_teacher_database
        except ImportError:
            from database.init_teacher_db import init_teacher_database
        init_teacher_database()
        print("教师系统数据库初始化完成")
    except Exception as e:
        print(f"教师系统数据库初始化失败: {e}")

# 创建蓝图实例
teacher_bp = create_teacher_blueprint()

if __name__ == '__main__':
    # 独立运行模式
    from flask import Flask
    app = Flask(__name__)
    app.config.from_object(TeacherConfig)
    app.register_blueprint(teacher_bp)
    app.run(debug=True, host='0.0.0.0', port=5001)
