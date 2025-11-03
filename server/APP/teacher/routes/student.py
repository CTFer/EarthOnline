# -*- coding: utf-8 -*-
"""
学生端路由
"""
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for
from ..services.AuthService import AuthService
from ..services.MaterialService import MaterialService
from ..services.ClassService import ClassService

student_bp = Blueprint('teacher_student', __name__, url_prefix='/student')

# 初始化服务
auth_service = AuthService()
material_service = MaterialService()
class_service = ClassService()

@student_bp.route('/login', methods=['GET', 'POST'])
def login():
    """学生登录验证"""
    if request.method == 'GET':
        return render_template('student/login.html')
    
    data = request.get_json()
    class_code = data.get('class_code')
    student_name = data.get('student_name')
    
    result = auth_service.student_verify(class_code, student_name)
    
    if result['success']:
        session['student_id'] = result['data']['id']
        session['student_name'] = result['data']['name']
        session['class_name'] = result['data']['class_name']
        return jsonify(result)
    else:
        return jsonify(result), 400

@student_bp.route('/logout')
def logout():
    """学生登出"""
    session.clear()
    return redirect(url_for('teacher_student.login'))

@student_bp.route('/')
def homework_list():
    """作业列表"""
    if 'student_id' not in session:
        return redirect(url_for('teacher_student.login'))
    
    student_id = session['student_id']
    
    # 获取学生作业列表
    materials_result = material_service.get_student_materials(student_id)
    
    return render_template('student/homework_list.html', 
                         materials=materials_result['data'])

@student_bp.route('/homework/<int:material_id>')
def homework_detail(material_id):
    """作业详情"""
    if 'student_id' not in session:
        return redirect(url_for('teacher_student.login'))
    
    student_id = session['student_id']
    
    # 获取材料详情
    material_result = material_service.get_material_detail(material_id)
    if not material_result['success']:
        return render_template('student/error.html', 
                             message=material_result['message'])
    
    material = material_result['data']['material']
    
    # 获取完成状态
    completion = material_service.completion_model.get_by_material_and_student(
        material_id, student_id
    )
    
    return render_template('student/homework_detail.html', 
                         material=material,
                         completion=completion)

@student_bp.route('/homework/<int:material_id>/complete', methods=['POST'])
def mark_complete(material_id):
    """标记作业完成"""
    if 'student_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    student_id = session['student_id']
    
    result = material_service.update_completion_status(
        material_id, student_id, 1, 100
    )
    
    return jsonify(result)

@student_bp.route('/homework/<int:material_id>/progress', methods=['POST'])
def update_progress(material_id):
    """更新学习进度"""
    if 'student_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    student_id = session['student_id']
    data = request.get_json()
    
    progress = data.get('progress', 0)
    last_position = data.get('last_position', 0)
    
    result = material_service.update_completion_status(
        material_id, student_id, 0, progress, last_position
    )
    
    return jsonify(result)

@student_bp.route('/media/<int:material_id>')
def media_player(material_id):
    """媒体播放器"""
    if 'student_id' not in session:
        return redirect(url_for('teacher_student.login'))
    
    student_id = session['student_id']
    
    # 获取材料详情
    material_result = material_service.get_material_detail(material_id)
    if not material_result['success']:
        return render_template('student/error.html', 
                             message=material_result['message'])
    
    material = material_result['data']['material']
    
    # 获取完成状态
    completion = material_service.completion_model.get_by_material_and_student(
        material_id, student_id
    )
    
    return render_template('student/media_player.html', 
                         material=material,
                         completion=completion)

@student_bp.route('/api/materials')
def api_materials():
    """获取学生材料API"""
    if 'student_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    student_id = session['student_id']
    result = material_service.get_student_materials(student_id)
    
    return jsonify(result)

@student_bp.route('/api/completion/<int:material_id>', methods=['POST'])
def api_update_completion(material_id):
    """更新完成状态API"""
    if 'student_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    student_id = session['student_id']
    data = request.get_json()
    
    status = data.get('status', 0)
    progress = data.get('progress', 0)
    last_position = data.get('last_position', 0)
    
    result = material_service.update_completion_status(
        material_id, student_id, status, progress, last_position
    )
    
    return jsonify(result)
