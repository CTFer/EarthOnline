# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-11-01 11:00:00
# LastEditTime: 2025-11-02 15:53:05
# LastEditors: 一根鱼骨棒
# Description: 停车场管理应用路由主入口 - 新版
# Software: VScode
# Copyright 2025 迷舍

import os
import sys
import logging
import hashlib
from datetime import datetime
from flask import render_template, jsonify, request, make_response, session, redirect, url_for

# 获取当前文件所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加服务器根目录到Python路径，确保能导入utils等模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))))

from utils.response_handler import ResponseHandler, StatusCode

# 从__init__.py导入蓝图
from . import car_park_new_bp
from .services.qywechat_service import get_qywechat_service
from .utils import (
    get_monthly_cars,
    _query_car_info,
    get_db_connection,
    get_car_park_statistics,
    update_heartbeat_time,
    check_api_key,
    save_car_park_info,
    parse_approval_data,
    get_car_park_records,
    get_car_park_record,
    add_car_park_record,
    update_car_park_record,
    delete_car_park_record
)

logger = logging.getLogger(__name__)

# 确保默认管理员用户存在
def ensure_admin_user():
    """确保默认管理员用户存在于数据库中"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 创建user表（如果不存在）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            remark TEXT
        )
        ''')
        
        # 计算密码的MD5哈希
        md5_hash = hashlib.md5('325299'.encode()).hexdigest()
        
        # 检查用户是否已存在
        cursor.execute("SELECT * FROM user WHERE user = ?", ('emanon',))
        user = cursor.fetchone()
        
        if not user:
            # 创建默认管理员用户
            cursor.execute(
                "INSERT INTO user (user, password, remark) VALUES (?, ?, ?)",
                ('emanon', md5_hash, '默认管理员')
            )
            conn.commit()
            print("默认管理员用户已创建: emanon/325299")
    except Exception as e:
        print(f"创建默认管理员用户失败: {e}")
    finally:
        conn.close()

# 初始化时确保管理员用户存在
try:
    ensure_admin_user()
except Exception as e:
    print(f"初始化管理员用户时出错: {e}")

# 认证相关函数
def login_required(f):
    """登录检查装饰器 - 用于需要完整权限的路由"""
    def decorator(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('car_park_new.login'))
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

def is_logged_in():
    """检查用户是否已登录"""
    return 'user' in session

def authenticate(username, password):
    """验证用户"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 计算密码的MD5哈希
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        cursor.execute("SELECT * FROM user WHERE user = ? AND password = ?", (username, md5_hash))
        user = cursor.fetchone()
        return user is not None
    finally:
        conn.close()

def filter_car_data(cars, is_admin=False):
    """根据用户权限过滤车辆数据
    is_admin=True: 返回完整信息
    is_admin=False: 只返回车牌号、车辆类型、到期时间、剩余天数
    """
    if is_admin:
        return cars
    
    # 过滤数据，只保留必要字段
    filtered_cars = []
    for car in cars:
        filtered_cars.append({
            'plateNumber': car.get('plateNumber'),
            'plateStandard': car.get('plateStandard'),
            'endTime': car.get('endTime'),
            'remaining_days': car.get('remaining_days'),
            'status': car.get('status')
        })
    return filtered_cars


def get_qywechat():
    """获取企业微信服务实例"""
    return get_qywechat_service()


# 登录页面
@car_park_new_bp.route('/emanon', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if authenticate(username, password):
            session['user'] = username
            return redirect(url_for('car_park_new.index'))  # 登录成功后跳转到首页
        else:
            return render_template('car_park/login.html', error='用户名或密码错误')
    
    return render_template('car_park/login.html')

# 登出
@car_park_new_bp.route('/logout')
def logout():
    """登出"""
    session.pop('user', None)
    return redirect(url_for('car_park_new.index'))

@car_park_new_bp.route('/')
@car_park_new_bp.route('')
def index():
    """首页"""
    # 检查登录状态
    is_admin = is_logged_in()
    username = session.get('user', '')
    
    try:
        # 查询月租车数据
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now()
        
        query = """
        SELECT 
            p.plateNumber AS car_number,
            pp.pName AS owner,
            p.endTime AS expire_time,
            p.plateStandard AS car_type_name,
            pp.pPhone AS phone,
            pp.pAddress AS address,
            p.pRemark AS remark,
            CASE
                WHEN p.endTime < ? THEN 'expired'
                WHEN (julianday(p.endTime) - julianday(DATE('now'))) <= 30 THEN 'expiring'
                ELSE 'normal'
            END AS status,
            CAST(julianday(p.endTime) - julianday(DATE('now')) AS INTEGER) AS remaining_days
        FROM Sys_Park_Plate p
        JOIN Sys_Park_Person pp ON p.personId = pp.id
        WHERE p.isDel = 0
        ORDER BY p.id DESC
        """
        
        cursor.execute(query, (current_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        # 获取列名
        columns = [desc[0] for desc in cursor.description]
        
        # 将结果转换为字典列表
        cars = []
        for row in cursor.fetchall():
            cars.append(dict(zip(columns, row)))
        conn.close()
        
        # 统计信息
        total_cars = len(cars)
        expired_cars = sum(1 for car in cars if car['status'] == 'expired')
        expiring_cars = sum(1 for car in cars if car['status'] == 'expiring')
        normal_cars = total_cars - expired_cars - expiring_cars
        
        # 车辆类型映射 - 与utils.py中保持一致
        car_type_map = {
            1: '业主首车',
            2: '外部和租户月租车',
            5: '业主二车'
        }
        
        # 处理车辆类型和统一字段名
        processed_cars = []
        for car in cars:
            processed_car = car.copy()
            # 转换车辆类型为中文
            processed_car['car_type_name'] = car_type_map.get(processed_car.get('car_type_name'), processed_car.get('car_type_name', ''))
            # 确保有expire_time_display字段
            processed_car['expire_time_display'] = processed_car.get('expire_time')
            processed_cars.append(processed_car)
        cars = processed_cars
        
        # 根据登录状态过滤数据
        if not is_admin:
            filtered_cars = []
            for car in cars:
                filtered_car = {
                    'car_number': car['car_number'],
                    'car_type_name': car['car_type_name'],
                    'expire_time_display': car['expire_time_display'],
                    'remaining_days': car['remaining_days'],
                    'status': car['status']
                }
                filtered_cars.append(filtered_car)
            cars = filtered_cars
        
    except Exception as e:
        logger.error(f"获取首页数据失败: {str(e)}")
        cars = []
        total_cars = 0
        expired_cars = 0
        expiring_cars = 0
        normal_cars = 0
    
    # 渲染首页模板
    return render_template('car_park/index.html', 
                           cars=cars,
                           total_cars=total_cars,
                           expired_cars=expired_cars,
                           expiring_cars=expiring_cars,
                           normal_cars=normal_cars,
                           is_admin=is_admin,
                           username=username)


@car_park_new_bp.route('/api/cars', methods=['GET'])
def api_cars():
    """获取月租车数据的API接口，根据登录状态返回不同数据"""
    try:
        # 检查登录状态
        is_admin = is_logged_in()
        
        # 查询月租车数据
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now()
        
        query = """
        SELECT 
            p.plateNumber AS car_number,
            pp.pName AS owner,
            p.plateStandard AS car_type_name,
            p.endTime AS expire_time,
            pp.pPhone AS phone,
            pp.pAddress AS address,
            p.pRemark AS remark,
            CASE
                WHEN p.endTime < ? THEN 'expired'
                WHEN (julianday(p.endTime) - julianday(DATE('now'))) <= 30 THEN 'expiring'
                ELSE 'normal'
            END AS status,
            p.endTime AS expire_time_display,
            CAST(julianday(p.endTime) - julianday(DATE('now')) AS INTEGER) AS remaining_days
        FROM Sys_Park_Plate p
        JOIN Sys_Park_Person pp ON p.personId = pp.id
        WHERE p.isDel = 0
        ORDER BY p.id DESC
        """
        
        cursor.execute(query, (current_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        # 获取列名
        columns = [desc[0] for desc in cursor.description]
        
        # 将结果转换为字典列表
        cars = []
        for row in cursor.fetchall():
            cars.append(dict(zip(columns, row)))
        
        # 车辆类型映射 - 与utils.py中保持一致
        car_type_map = {
            1: '业主首车',
            2: '外部和租户月租车',
            5: '业主二车'
        }
        
        # 处理车辆类型
        processed_cars = []
        for car in cars:
            processed_car = car.copy()
            # 转换车辆类型为中文
            processed_car['car_type_name'] = car_type_map.get(processed_car.get('car_type_name'), processed_car.get('car_type_name', ''))
            processed_cars.append(processed_car)
        
        # 根据登录状态过滤数据
        filtered_cars = []
        for car in processed_cars:
            if is_admin:
                # 管理员可以看到所有字段
                filtered_cars.append(car)
            else:
                # 非管理员只看到车牌号、车辆类型、到期时间、剩余天数和状态
                filtered_car = {
                    'car_number': car['car_number'],
                    'car_type_name': car['car_type_name'],
                    'expire_time_display': car['expire_time_display'],
                    'remaining_days': car['remaining_days'],
                    'status': car['status']
                }
                filtered_cars.append(filtered_car)
        
        conn.close()
        
        return jsonify({
            'status': 'success',
            'data': filtered_cars,
            'count': len(filtered_cars),
            'is_admin': is_admin
        })
    except Exception as e:
        logger.error(f"获取月租车数据失败: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f'获取数据失败: {str(e)}'
        })


@car_park_new_bp.route('/qy', methods=['GET', 'POST'])
def qywechat():
    """
    企业微信接入接口
    GET: 验证服务器有效性
    POST: 处理企业微信消息和事件
    """
    try:
        # 获取通用参数
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')
        echostr = request.args.get('echostr', '')
        
        # 获取企业微信服务实例
        qywechat_service = get_qywechat_service()
        
        if request.method == 'GET':
            # 验证URL有效性
            logger.info(
                f"[Car_Park] 收到URL验证请求: msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")

            # 验证URL
            decrypted_str = qywechat_service.verify_url(
                msg_signature, timestamp, nonce, echostr)
            if decrypted_str:
                logger.info(f"[Car_Park] 解密后的echostr明文: {decrypted_str}")
                # 设置正确的响应头
                response = make_response(decrypted_str)
                response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                response.headers['Cache-Control'] = 'no-cache'
                return response
            else:
                logger.warning("[Car_Park] URL验证失败")
                return 'Invalid signature', 403

        elif request.method == 'POST':
            # 获取原始消息数据
            xml_data = request.data
            # 使用企业微信服务处理加密消息
            response = qywechat_service.handle_message(
                xml_data, msg_signature, timestamp, nonce)
            # 设置正确的响应头
            resp = make_response(response)
            resp.headers['Content-Type'] = 'application/xml; charset=utf-8'
            resp.headers['Cache-Control'] = 'no-cache'
            return resp

    except Exception as e:
        logger.error(f"[Car_Park] 处理请求失败: {str(e)}", exc_info=True)
        return 'success'  # 返回success避免企业微信重试


@car_park_new_bp.route('/qy/access_token')
def get_qy_access_token():
    """获取企业微信access_token"""
    access_token = get_qywechat().get_access_token()
    if access_token:
        return ResponseHandler.success(
            msg="获取access_token成功",
            data={"access_token": access_token}
        )
    else:
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="获取access_token失败"
        )


@car_park_new_bp.route('/qy/access_token/refresh')
def refresh_qy_access_token():
    """强制刷新企业微信access_token"""
    access_token = get_qywechat().force_refresh_token()
    if access_token:
        return ResponseHandler.success(
            msg="刷新access_token成功",
            data={"access_token": access_token}
        )
    else:
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="刷新access_token失败"
        )


@car_park_new_bp.route('/qy/message/send', methods=['POST'])
def send_qy_message():
    """发送企业微信消息"""
    try:
        data = request.json
        content = data.get('content')
        to_user = data.get('to_user')
        
        if not content:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="消息内容不能为空"
            )
        
        success = get_qywechat().send_text_message(content, to_user)
        if success:
            return ResponseHandler.success(msg="消息发送成功")
        else:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg="消息发送失败"
            )
    except Exception as e:
        logger.error(f"[Car_Park] 发送消息失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="发送消息异常"
        )

# ====== car_park表CRUD API路由 ======

@car_park_new_bp.route('/api/car_park', methods=['GET'])
def api_get_car_park_records():
    """获取所有续期记录"""
    try:
        is_admin = is_logged_in()
        
        # 未登录用户不能访问续期记录
        if not is_admin:
            return ResponseHandler.error(
                code=StatusCode.UNAUTHORIZED,
                msg="请先登录"
            )
        
        records = get_car_park_records()
        return ResponseHandler.success(
            data={
                'records': records,
                'total': len(records)
            }
        )
    except Exception as e:
        logger.error(f"[Car_Park] 获取续期记录失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="获取续期记录失败"
        )

@car_park_new_bp.route('/api/car_park/<int:record_id>', methods=['GET'])
def api_get_car_park_record(record_id):
    """获取单个续期记录"""
    try:
        is_admin = is_logged_in()
        
        # 未登录用户不能访问续期记录
        if not is_admin:
            return ResponseHandler.error(
                code=StatusCode.UNAUTHORIZED,
                msg="请先登录"
            )
        
        record = get_car_park_record(record_id)
        if record:
            return ResponseHandler.success(data=record)
        else:
            return ResponseHandler.error(
                code=StatusCode.NOT_FOUND,
                msg="续期记录不存在"
            )
    except Exception as e:
        logger.error(f"[Car_Park] 获取续期记录失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="获取续期记录失败"
        )

@car_park_new_bp.route('/api/car_park', methods=['POST'])
@login_required
def api_add_car_park_record():
    """添加续期记录 - 需要登录"""
    try:
        data = request.json
        if not data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="请求数据不能为空"
            )
        
        success = add_car_park_record(data)
        if success:
            return ResponseHandler.success(msg="添加续期记录成功")
        else:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg="添加续期记录失败"
            )
    except Exception as e:
        logger.error(f"[Car_Park] 添加续期记录失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="添加续期记录异常"
        )

@car_park_new_bp.route('/api/car_park/<int:record_id>', methods=['PUT'])
@login_required
def api_update_car_park_record(record_id):
    """更新续期记录 - 需要登录"""
    try:
        data = request.json
        if not data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="请求数据不能为空"
            )
        
        success = update_car_park_record(record_id, data)
        if success:
            return ResponseHandler.success(msg="更新续期记录成功")
        else:
            return ResponseHandler.error(
                code=StatusCode.NOT_FOUND,
                msg="续期记录不存在或更新失败"
            )
    except Exception as e:
        logger.error(f"[Car_Park] 更新续期记录失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="更新续期记录异常"
        )

@car_park_new_bp.route('/api/car_park/<int:record_id>', methods=['DELETE'])
@login_required
def api_delete_car_park_record(record_id):
    """删除续期记录 - 需要登录"""
    try:
        success = delete_car_park_record(record_id)
        if success:
            return ResponseHandler.success(msg="删除续期记录成功")
        else:
            return ResponseHandler.error(
                code=StatusCode.NOT_FOUND,
                msg="续期记录不存在"
            )
    except Exception as e:
        logger.error(f"[Car_Park] 删除续期记录失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="删除续期记录异常"
        )


@car_park_new_bp.route('/review', methods=['POST'])
@login_required
def handle_review():
    """车辆续期审核请求 - 需要登录"""
    try:
        data = request.json
        car_number = data.get('car_number')
        owner_name = data.get('owner_name')
        car_type = data.get('car_type', 1)
        month_count = data.get('month_count', 1)
        
        if not all([car_number, owner_name]):
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="参数不完整"
            )
        
        # 这里可以实现审核请求逻辑
        # 例如调用企业微信审批API创建审批单
        
        return ResponseHandler.success(
            msg="审核请求已提交",
            data={
                "car_number": car_number,
                "owner_name": owner_name,
                "month_count": month_count,
                "status": "pending"
            }
        )
        
    except Exception as e:
        logger.error(f"[Car_Park] 处理审核请求失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="处理审核请求异常"
        )


@car_park_new_bp.route('/car_park', methods=['GET', 'POST'])
def car_park_api():
    """查询/更新停车场车辆信息"""
    try:
        if request.method == 'GET':
            # 查询车辆信息
            car_number = request.args.get('car_number')
            owner_name = request.args.get('owner_name')
            sync_all = request.args.get('sync_all', 'false').lower() == 'true'
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if sync_all:
                # 获取所有车辆信息
                cursor.execute("""
                    SELECT 
                        p.id, p.plateNumber, p.plateStandard, p.endTime, p.pRemark, p.isDel,
                        pp.pName, pp.pPhone, pp.pAddress
                    FROM Sys_Park_Plate p
                    JOIN Sys_Park_Person pp ON p.personId = pp.id
                """)
                cars = []
                for row in cursor.fetchall():
                    cars.append({
                        'id': row['id'],
                        'plateNumber': row['plateNumber'],
                        'plateStandard': row['plateStandard'],
                        'endTime': row['endTime'],
                        'pRemark': row['pRemark'],
                        'isDel': row['isDel'],
                        'pName': row['pName'],
                        'pPhone': row['pPhone'],
                        'pAddress': row['pAddress']
                    })
                
                conn.close()
                return ResponseHandler.success(
                    msg="获取全部车辆信息成功",
                    data=cars,
                    count=len(cars)
                )
            
            elif car_number:
                # 按车牌号查询
                cursor.execute("""
                    SELECT 
                        p.id, p.plateNumber, p.plateStandard, p.endTime, p.pRemark,
                        pp.pName, pp.pPhone, pp.pAddress
                    FROM Sys_Park_Plate p
                    JOIN Sys_Park_Person pp ON p.personId = pp.id
                    WHERE p.isDel = 0 AND p.plateNumber = ?
                """, (car_number,))
                
                row = cursor.fetchone()
                conn.close()
                
                if row:
                    return ResponseHandler.success(
                        msg="查询成功",
                        data={
                            'id': row['id'],
                            'plateNumber': row['plateNumber'],
                            'plateStandard': row['plateStandard'],
                            'endTime': row['endTime'],
                            'pRemark': row['pRemark'],
                            'pName': row['pName'],
                            'pPhone': row['pPhone'],
                            'pAddress': row['pAddress']
                        }
                    )
                else:
                    return ResponseHandler.error(
                        code=StatusCode.NOT_FOUND,
                        msg="未找到车辆信息"
                    )
            
            elif owner_name:
                # 按车主姓名查询
                cursor.execute("""
                    SELECT 
                        p.id, p.plateNumber, p.plateStandard, p.endTime, p.pRemark,
                        pp.pName, pp.pPhone, pp.pAddress
                    FROM Sys_Park_Plate p
                    JOIN Sys_Park_Person pp ON p.personId = pp.id
                    WHERE p.isDel = 0 AND pp.pName LIKE ?
                """, (f"%{owner_name}%",))
                
                cars = []
                for row in cursor.fetchall():
                    cars.append({
                        'id': row['id'],
                        'plateNumber': row['plateNumber'],
                        'plateStandard': row['plateStandard'],
                        'endTime': row['endTime'],
                        'pRemark': row['pRemark'],
                        'pName': row['pName'],
                        'pPhone': row['pPhone'],
                        'pAddress': row['pAddress']
                    })
                
                conn.close()
                
                if cars:
                    return ResponseHandler.success(
                        msg="查询成功",
                        data=cars,
                        count=len(cars)
                    )
                else:
                    return ResponseHandler.error(
                        code=StatusCode.NOT_FOUND,
                        msg="未找到车辆信息"
                    )
            
            else:
                # 获取统计信息
                stats = get_car_park_statistics()
                return ResponseHandler.success(
                    msg="获取统计信息成功",
                    data=stats
                )
        
        elif request.method == 'POST':
            # 同步数据
            data = request.json
            if not data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="数据不能为空"
                )
            
            conn = get_db_connection()
            cursor = conn.cursor()
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 处理人员数据
            if 'persons' in data:
                for person in data['persons']:
                    # 尝试更新，不存在则插入
                    cursor.execute("""
                        INSERT OR REPLACE INTO Sys_Park_Person (id, pName, pPhone, pAddress)
                        VALUES (?, ?, ?, ?)
                    """, (person['id'], person['pName'], person['pPhone'], person['pAddress']))
            
            # 处理车牌数据
            if 'plates' in data:
                for plate in data['plates']:
                    # 尝试更新，不存在则插入
                    cursor.execute("""
                        INSERT OR REPLACE INTO Sys_Park_Plate 
                        (id, personId, plateNumber, plateStandard, endTime, pRemark, isDel, createTime, updateTime)
                        VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT createTime FROM Sys_Park_Plate WHERE id = ?), ?), ?)
                    """, (
                        plate['id'], plate['personId'], plate['plateNumber'], 
                        plate['plateStandard'], plate['endTime'], plate['pRemark'], 
                        plate['isDel'], plate['id'], current_time, current_time
                    ))
            
            conn.commit()
            conn.close()
            
            return ResponseHandler.success(
                msg="数据同步成功",
                data={
                    'persons_count': len(data.get('persons', [])),
                    'plates_count': len(data.get('plates', []))
                }
            )
            
    except Exception as e:
        logger.error(f"[Car_Park] 处理车辆信息失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg="处理车辆信息异常"
        )


@car_park_new_bp.route('/client_alive', methods=['GET'])
@check_api_key  # 添加API密钥验证
def client_alive():
    """处理客户端存活通知"""
    try:
        # 获取客户端状态信息
        park_system_status = request.args.get('status', 'unknown')
        process_id = request.args.get('process_id', 'unknown')
        memory_usage = request.args.get('memory_usage', 'unknown')
        cpu_usage = request.args.get('cpu_usage', 'unknown')

        # 记录客户端状态
        logger.info(f"[Car_Park] 收到客户端存活通知:")
        logger.info(f"[Car_Park] - 停车场系统状态: {park_system_status}")
        logger.info(f"[Car_Park] - 进程ID: {process_id}")
        logger.info(f"[Car_Park] - 内存使用: {memory_usage}")
        logger.info(f"[Car_Park] - CPU使用: {cpu_usage}")

        # 如果停车场系统异常，发送通知
        if park_system_status != 'running':
            error_msg = (
                f"⚠️ 停车场系统异常\n"
                f"状态：{park_system_status}\n"
                f"进程ID：{process_id}\n"
                f"内存使用：{memory_usage}\n"
                f"CPU使用：{cpu_usage}\n"
                f"时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            get_qywechat().send_text_message(
                content=error_msg,
                to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]
            )

            return ResponseHandler.success(
                msg="客户端存活通知已接收，系统状态异常",
                data={
                    "status": "warning",
                    "message": "停车场系统状态异常，已发送通知",
                    "code": 0  # 添加code字段，确保客户端能正确识别响应
                }
            )

        # 更新心跳时间
        update_heartbeat_time()

        return ResponseHandler.success(
            msg="客户端存活通知已接收",
            data={
                "status": "ok",
                "message": "系统运行正常",
                "code": 0  # 添加code字段，确保客户端能正确识别响应
            }
        )

    except Exception as e:
        error_msg = f"处理客户端存活通知失败: {str(e)}"
        logger.error(f"[Car_Park] {error_msg}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=error_msg,
            data={
                "status": "error",
                "message": str(e),
                "code": StatusCode.SERVER_ERROR
            }
        )


@car_park_new_bp.route('/refresh')
def refresh_data():
    """刷新数据页面"""
    return render_template('car_park/refresh.html')