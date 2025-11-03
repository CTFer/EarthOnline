# -*- coding: utf-8 -*-
"""
公共展示路由
"""
from flask import Blueprint, render_template, request, jsonify
from ..services.TeacherService import TeacherService
from ..services.MaterialService import MaterialService
from ..models.activity import TeacherActivity
from ..models.course import TeacherCourse

public_bp = Blueprint('teacher_public', __name__, url_prefix='/public')

# 初始化服务
teacher_service = TeacherService()
material_service = MaterialService()
activity_model = TeacherActivity()
course_model = TeacherCourse()

@public_bp.route('/')
def index():
    """首页"""
    return render_template('public/index.html')

@public_bp.route('/teacher/<int:teacher_id>')
def teacher_info(teacher_id):
    """教师信息页"""
    # 获取教师信息
    teacher_result = teacher_service.get_teacher_profile(teacher_id)
    if not teacher_result['success']:
        return render_template('public/error.html', 
                             message=teacher_result['message'])
    
    teacher = teacher_result['data']
    
    # 获取教师的公开材料
    public_materials = material_service.material_model.get_public_materials()
    teacher_materials = [m for m in public_materials if m['teacher_id'] == teacher_id]
    
    return render_template('public/teacher_info.html', 
                         teacher=teacher,
                         materials=teacher_materials)

@public_bp.route('/activities')
def activities():
    """活动页"""
    # 获取公开活动
    activities = activity_model.get_public_activities()
    
    return render_template('public/activities.html', 
                         activities=activities)

@public_bp.route('/courses')
def courses():
    """课程页"""
    # 获取公开课程
    courses = course_model.get_public_courses()
    
    return render_template('public/courses.html', 
                         courses=courses)

@public_bp.route('/resources')
def resources():
    """公开资源页"""
    # 获取公开材料
    materials = material_service.material_model.get_public_materials()
    
    # 按类型分组
    video_materials = [m for m in materials if m['type'] == 'video']
    audio_materials = [m for m in materials if m['type'] == 'audio']
    doc_materials = [m for m in materials if m['type'] == 'doc']
    
    return render_template('public/resources.html', 
                         video_materials=video_materials,
                         audio_materials=audio_materials,
                         doc_materials=doc_materials)

@public_bp.route('/api/teachers')
def api_teachers():
    """获取教师列表API"""
    # 获取所有活跃教师
    teachers = teacher_service.user_model.get_active_users()
    
    # 移除敏感信息
    for teacher in teachers:
        if 'password' in teacher:
            del teacher['password']
    
    return jsonify({
        'success': True,
        'data': teachers
    })

@public_bp.route('/api/activities')
def api_activities():
    """获取活动列表API"""
    activities = activity_model.get_public_activities()
    
    return jsonify({
        'success': True,
        'data': activities
    })

@public_bp.route('/api/courses')
def api_courses():
    """获取课程列表API"""
    courses = course_model.get_public_courses()
    
    return jsonify({
        'success': True,
        'data': courses
    })

@public_bp.route('/api/materials')
def api_materials():
    """获取公开材料API"""
    materials = material_service.material_model.get_public_materials()
    
    return jsonify({
        'success': True,
        'data': materials
    })

@public_bp.route('/api/materials/search')
def api_search_materials():
    """搜索材料API"""
    keyword = request.args.get('keyword', '')
    material_type = request.args.get('type', '')
    
    # 构建查询条件
    where_conditions = ["is_public = 1", "status = 1"]
    params = []
    
    if keyword:
        where_conditions.append("title LIKE ?")
        params.append(f"%{keyword}%")
    
    if material_type:
        where_conditions.append("type = ?")
        params.append(material_type)
    
    where_clause = " AND ".join(where_conditions)
    
    materials = material_service.material_model.get_all(
        "teacher_material", where_clause, tuple(params)
    )
    
    return jsonify({
        'success': True,
        'data': materials
    })
