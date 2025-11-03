# -*- coding: utf-8 -*-
"""
后台管理路由
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..services.AuthService import AuthService
from ..services.TeacherService import TeacherService
from ..services.ClassService import ClassService
from ..services.StudentService import StudentService
from ..services.MaterialService import MaterialService
from ..services.FileService import FileService
from ..services.NotificationService import NotificationService

admin_bp = Blueprint('teacher_admin', __name__, url_prefix='/admin')

# 初始化服务
auth_service = AuthService()
teacher_service = TeacherService()
class_service = ClassService()
student_service = StudentService()
material_service = MaterialService()
file_service = FileService()
notification_service = NotificationService()

def require_login(f):
    """登录验证装饰器"""
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            return redirect(url_for('teacher.teacher_admin.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """教师登录"""
    if request.method == 'GET':
        return render_template('admin/login.html')
    
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    result = auth_service.teacher_login(username, password)
    
    if result['success']:
        session['teacher_id'] = result['data']['id']
        session['teacher_name'] = result['data']['name']
        return jsonify(result)
    else:
        return jsonify(result), 400

@admin_bp.route('/logout')
def logout():
    """教师登出"""
    session.clear()
    return redirect(url_for('teacher_admin.login'))

@admin_bp.route('/')
@require_login
def dashboard():
    """仪表盘"""
    teacher_id = session['teacher_id']
    
    # 获取仪表盘数据
    dashboard_data = teacher_service.get_dashboard_data(teacher_id)
    notifications = notification_service.get_teacher_notifications(teacher_id)
    
    return render_template('admin/dashboard.html', 
                         dashboard_data=dashboard_data['data'],
                         notifications=notifications['data'])

@admin_bp.route('/classes')
@require_login
def class_manage():
    """班级管理"""
    teacher_id = session['teacher_id']
    
    # 获取班级列表
    classes_result = class_service.get_teacher_classes(teacher_id)
    
    return render_template('admin/class_manage.html', 
                         classes=classes_result['data'])

@admin_bp.route('/classes/create', methods=['POST'])
@require_login
def create_class():
    """创建班级"""
    teacher_id = session['teacher_id']
    data = request.get_json()
    
    result = class_service.create_class(
        teacher_id, 
        data.get('name'), 
        data.get('description', '')
    )
    
    return jsonify(result)

@admin_bp.route('/classes/<int:class_id>', methods=['PUT', 'DELETE'])
@require_login
def class_detail(class_id):
    """班级详情操作"""
    if request.method == 'PUT':
        data = request.get_json()
        result = class_service.update_class(
            class_id, 
            data.get('name'), 
            data.get('description')
        )
        return jsonify(result)
    
    elif request.method == 'DELETE':
        result = class_service.delete_class(class_id)
        return jsonify(result)

@admin_bp.route('/students')
@require_login
def student_manage():
    """学生管理"""
    teacher_id = session['teacher_id']
    
    # 获取学生列表
    students_result = student_service.get_teacher_students(teacher_id)
    
    return render_template('admin/student_manage.html', 
                         students=students_result['data'])

@admin_bp.route('/students/create', methods=['POST'])
@require_login
def create_student():
    """创建学生"""
    teacher_id = session['teacher_id']
    data = request.get_json()
    
    result = student_service.create_student(teacher_id, **data)
    
    return jsonify(result)

@admin_bp.route('/students/<int:student_id>', methods=['PUT', 'DELETE'])
@require_login
def student_detail(student_id):
    """学生详情操作"""
    if request.method == 'PUT':
        data = request.get_json()
        result = student_service.update_student(student_id, **data)
        return jsonify(result)
    
    elif request.method == 'DELETE':
        result = student_service.delete_student(student_id)
        return jsonify(result)

@admin_bp.route('/materials')
@require_login
def material_manage():
    """材料管理"""
    teacher_id = session['teacher_id']
    
    # 获取材料列表
    materials_result = material_service.get_teacher_materials(teacher_id)
    
    return render_template('admin/material_manage.html', 
                         materials=materials_result['data'])

@admin_bp.route('/materials/upload', methods=['POST'])
@require_login
def upload_material():
    """上传材料"""
    teacher_id = session['teacher_id']
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '没有选择文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '没有选择文件'}), 400
    
    # 准备文件数据
    file_data = {
        'filename': file.filename,
        'content': file.read(),
        'content_type': file.content_type
    }
    
    # 保存文件
    file_result = file_service.save_file(teacher_id, file_data)
    if not file_result['success']:
        return jsonify(file_result), 400
    
    # 创建材料记录
    material_data = request.form.to_dict()
    material_data.update({
        'teacher_id': teacher_id,
        'file_name': file.filename,
        'file_path': file_result['data']['file_path'],
        'file_size': file_result['data']['file_size']
    })
    
    result = material_service.create_material(**material_data)
    
    return jsonify(result)

@admin_bp.route('/materials/<int:material_id>', methods=['PUT', 'DELETE'])
@require_login
def material_detail(material_id):
    """材料详情操作"""
    if request.method == 'PUT':
        data = request.get_json()
        result = material_service.update_material(material_id, **data)
        return jsonify(result)
    
    elif request.method == 'DELETE':
        result = material_service.delete_material(material_id)
        return jsonify(result)

@admin_bp.route('/materials/<int:material_id>/distribute', methods=['POST'])
@require_login
def distribute_material(material_id):
    """分发材料"""
    data = request.get_json()
    targets = data.get('targets', [])
    
    result = material_service.distribute_material(material_id, targets)
    
    return jsonify(result)

@admin_bp.route('/profile')
@require_login
def profile():
    """教师资料"""
    teacher_id = session['teacher_id']
    
    # 获取教师信息
    profile_result = teacher_service.get_teacher_profile(teacher_id)
    
    return render_template('admin/profile.html', 
                         profile=profile_result['data'])

@admin_bp.route('/profile/update', methods=['POST'])
@require_login
def update_profile():
    """更新教师资料"""
    teacher_id = session['teacher_id']
    data = request.get_json()
    
    result = teacher_service.update_teacher_profile(teacher_id, data)
    
    return jsonify(result)
