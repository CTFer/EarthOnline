# -*- coding: utf-8 -*-
"""
API接口路由
"""
from flask import Blueprint, request, jsonify, session
from ..services.AuthService import AuthService
from ..services.TeacherService import TeacherService
from ..services.ClassService import ClassService
from ..services.StudentService import StudentService
from ..services.MaterialService import MaterialService
from ..services.FileService import FileService
from ..services.NotificationService import NotificationService

api_bp = Blueprint('teacher_api', __name__, url_prefix='/api')

# 初始化服务
auth_service = AuthService()
teacher_service = TeacherService()
class_service = ClassService()
student_service = StudentService()
material_service = MaterialService()
file_service = FileService()
notification_service = NotificationService()

def require_teacher_login(f):
    """教师登录验证装饰器"""
    def decorated_function(*args, **kwargs):
        if 'teacher_id' not in session:
            return jsonify({'success': False, 'message': '未登录'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_student_login(f):
    """学生登录验证装饰器"""
    def decorated_function(*args, **kwargs):
        if 'student_id' not in session:
            return jsonify({'success': False, 'message': '未登录'}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

# 认证相关API
@api_bp.route('/auth/teacher/login', methods=['POST'])
def teacher_login():
    """教师登录API"""
    data = request.get_json()
    phone = data.get('phone')
    password = data.get('password')
    
    result = auth_service.teacher_login(phone, password)
    
    if result['success']:
        session['teacher_id'] = result['data']['id']
        session['teacher_name'] = result['data']['name']
    
    return jsonify(result)

@api_bp.route('/auth/teacher/register', methods=['POST'])
def teacher_register():
    """教师注册API"""
    data = request.get_json()
    result = auth_service.teacher_register(**data)
    return jsonify(result)

@api_bp.route('/auth/student/verify', methods=['POST'])
def student_verify():
    """学生验证API"""
    data = request.get_json()
    class_code = data.get('class_code')
    student_name = data.get('student_name')
    
    result = auth_service.student_verify(class_code, student_name)
    
    if result['success']:
        session['student_id'] = result['data']['id']
        session['student_name'] = result['data']['name']
        session['class_name'] = result['data']['class_name']
    
    return jsonify(result)

# 教师端API
@api_bp.route('/teacher/dashboard')
@require_teacher_login
def teacher_dashboard():
    """教师仪表盘API"""
    teacher_id = session['teacher_id']
    result = teacher_service.get_dashboard_data(teacher_id)
    return jsonify(result)

@api_bp.route('/teacher/profile')
@require_teacher_login
def teacher_profile():
    """教师资料API"""
    teacher_id = session['teacher_id']
    result = teacher_service.get_teacher_profile(teacher_id)
    return jsonify(result)

@api_bp.route('/teacher/profile', methods=['PUT'])
@require_teacher_login
def update_teacher_profile():
    """更新教师资料API"""
    teacher_id = session['teacher_id']
    data = request.get_json()
    result = teacher_service.update_teacher_profile(teacher_id, data)
    return jsonify(result)

# 班级管理API
@api_bp.route('/classes', methods=['GET', 'POST'])
@require_teacher_login
def classes_api():
    """班级管理API"""
    teacher_id = session['teacher_id']
    
    if request.method == 'GET':
        result = class_service.get_teacher_classes(teacher_id)
        if result['success']:
            return jsonify({
                'code': 0,
                'data': result['data'],
                'count': len(result['data']),
                'msg': '获取成功'
            })
        else:
            return jsonify({
                'code': 1,
                'data': [],
                'count': 0,
                'msg': result['message']
            })
    
    elif request.method == 'POST':
        data = request.get_json()
        result = class_service.create_class(teacher_id, **data)
        return jsonify(result)

@api_bp.route('/classes/<int:class_id>', methods=['GET', 'PUT', 'DELETE'])
@require_teacher_login
def class_detail_api(class_id):
    """班级详情API"""
    if request.method == 'GET':
        result = class_service.get_class_detail(class_id)
        return jsonify(result)
    
    elif request.method == 'PUT':
        data = request.get_json()
        result = class_service.update_class(class_id, **data)
        return jsonify(result)
    
    elif request.method == 'DELETE':
        result = class_service.delete_class(class_id)
        return jsonify(result)

# 学生管理API
@api_bp.route('/students', methods=['GET', 'POST'])
@require_teacher_login
def students_api():
    """学生管理API"""
    teacher_id = session['teacher_id']
    
    if request.method == 'GET':
        result = student_service.get_teacher_students(teacher_id)
        if result['success']:
            return jsonify({
                'code': 0,
                'data': result['data'],
                'count': len(result['data']),
                'msg': '获取成功'
            })
        else:
            return jsonify({
                'code': 1,
                'data': [],
                'count': 0,
                'msg': result['message']
            })
    
    elif request.method == 'POST':
        data = request.get_json()
        result = student_service.create_student(teacher_id, **data)
        return jsonify(result)

@api_bp.route('/students/<int:student_id>', methods=['GET', 'PUT', 'DELETE'])
@require_teacher_login
def student_detail_api(student_id):
    """学生详情API"""
    if request.method == 'GET':
        result = student_service.get_student_detail(student_id)
        return jsonify(result)
    
    elif request.method == 'PUT':
        data = request.get_json()
        result = student_service.update_student(student_id, **data)
        return jsonify(result)
    
    elif request.method == 'DELETE':
        result = student_service.delete_student(student_id)
        return jsonify(result)

# 材料管理API
@api_bp.route('/materials', methods=['GET', 'POST'])
@require_teacher_login
def materials_api():
    """材料管理API"""
    teacher_id = session['teacher_id']
    
    if request.method == 'GET':
        result = material_service.get_teacher_materials(teacher_id)
        if result['success']:
            return jsonify({
                'code': 0,
                'data': result['data'],
                'count': len(result['data']),
                'msg': '获取成功'
            })
        else:
            return jsonify({
                'code': 1,
                'data': [],
                'count': 0,
                'msg': result['message']
            })
    
    elif request.method == 'POST':
        data = request.get_json()
        result = material_service.create_material(teacher_id, **data)
        return jsonify(result)

@api_bp.route('/materials/<int:material_id>', methods=['GET', 'PUT', 'DELETE'])
@require_teacher_login
def material_detail_api(material_id):
    """材料详情API"""
    if request.method == 'GET':
        result = material_service.get_material_detail(material_id)
        return jsonify(result)
    
    elif request.method == 'PUT':
        data = request.get_json()
        result = material_service.update_material(material_id, **data)
        return jsonify(result)
    
    elif request.method == 'DELETE':
        result = material_service.delete_material(material_id)
        return jsonify(result)

@api_bp.route('/materials/<int:material_id>/distribute', methods=['POST'])
@require_teacher_login
def distribute_material_api(material_id):
    """分发材料API"""
    data = request.get_json()
    targets = data.get('targets', [])
    result = material_service.distribute_material(material_id, targets)
    return jsonify(result)

# 学生端API
@api_bp.route('/student/materials')
@require_student_login
def student_materials():
    """学生材料API"""
    student_id = session['student_id']
    result = material_service.get_student_materials(student_id)
    return jsonify(result)

@api_bp.route('/student/completion/<int:material_id>', methods=['POST'])
@require_student_login
def update_completion(material_id):
    """更新完成状态API"""
    student_id = session['student_id']
    data = request.get_json()
    
    status = data.get('status', 0)
    progress = data.get('progress', 0)
    last_position = data.get('last_position', 0)
    
    result = material_service.update_completion_status(
        material_id, student_id, status, progress, last_position
    )
    
    return jsonify(result)

# 文件上传API
@api_bp.route('/upload', methods=['POST'])
@require_teacher_login
def upload_file():
    """文件上传API"""
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
    
    result = file_service.save_file(teacher_id, file_data)
    return jsonify(result)

# 通知API
@api_bp.route('/notifications')
@require_teacher_login
def notifications():
    """通知API"""
    teacher_id = session['teacher_id']
    result = notification_service.get_teacher_notifications(teacher_id)
    return jsonify(result)

@api_bp.route('/dashboard')
@require_teacher_login
def dashboard():
    """仪表盘API"""
    teacher_id = session['teacher_id']
    result = notification_service.get_dashboard_summary(teacher_id)
    return jsonify(result)
