# -*- coding: utf-8 -*-
"""
Roadmap模块主应用文件
包含蓝图定义和路由配置
"""
import json
from flask import Blueprint, request, render_template, redirect, url_for, flash

# 导入本模块的服务
from .services import roadmap_service

# 创建蓝图
roadmap_bp = Blueprint(
    'roadmap',  # 蓝图名称
    __name__,  # 模块名称
    url_prefix='/roadmap',  # URL前缀
    template_folder='templates',  # 模板目录
    static_folder='static'  # 静态文件目录
)

# 视图路由
@roadmap_bp.route('/')
def index():
    """Roadmap模块主页"""
    return render_template('roadmap.html')

# API路由
@roadmap_bp.route('/api/check_login', methods=['GET'])
def check_login():
    """检查登录状态"""
    return roadmap_service.check_login()

@roadmap_bp.route('/api/login', methods=['POST'])
def login():
    """登录接口"""
    try:
        data = request.get_json()
        return roadmap_service.roadmap_login(data)
    except json.JSONDecodeError:
        return json.dumps({'code': 400, 'msg': '无效的JSON数据'})

@roadmap_bp.route('/api/logout', methods=['GET'])
def logout():
    """登出接口"""
    return roadmap_service.roadmap_logout()

@roadmap_bp.route('/api', methods=['GET'])
def get_roadmaps():
    """获取开发计划列表"""
    return roadmap_service.get_roadmap()

@roadmap_bp.route('/api', methods=['POST'])
def add_roadmap():
    """添加开发计划"""
    try:
        data = request.get_json()
        return roadmap_service.add_roadmap(data)
    except json.JSONDecodeError:
        return json.dumps({'code': 400, 'msg': '无效的JSON数据'})

@roadmap_bp.route('/api/<int:roadmap_id>', methods=['PUT'])
def update_roadmap(roadmap_id):
    """更新开发计划"""
    try:
        data = request.get_json()
        return roadmap_service.update_roadmap(roadmap_id, data)
    except json.JSONDecodeError:
        return json.dumps({'code': 400, 'msg': '无效的JSON数据'})

@roadmap_bp.route('/api/<int:roadmap_id>', methods=['DELETE'])
def delete_roadmap(roadmap_id):
    """删除开发计划"""
    return roadmap_service.delete_roadmap(roadmap_id)

# 同步相关接口
@roadmap_bp.route('/api/sync', methods=['GET'])
def sync_data():
    """提供同步数据（仅生产环境）"""
    return roadmap_service.sync_data()

@roadmap_bp.route('/api/sync', methods=['POST'])
def perform_sync():
    """执行同步操作（从生产环境拉取数据）"""
    # 检查登录状态
    login_status = json.loads(roadmap_service.check_login())
    if login_status['code'] != 0:
        return json.dumps(login_status)
    
    return roadmap_service.sync_from_prod()

@roadmap_bp.route('/api/batch_sync', methods=['POST'])
def batch_sync_data():
    """批量同步数据（仅生产环境）"""
    try:
        data = request.get_json()
        updates = data.get('updates', [])
        return roadmap_service.batch_sync(updates)
    except json.JSONDecodeError:
        return json.dumps({'code': 400, 'msg': '无效的JSON数据'})

# 暴露蓝图以便主应用导入
def get_blueprint():
    return roadmap_bp