# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-11-01 11:00:00
# LastEditTime: 2025-11-01 19:59:53
# LastEditors: 一根鱼骨棒
# Description: 停车场管理功能函数 - 新版
# Software: VScode
# Copyright 2025 迷舍

import os
import re
import sys
import time
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Tuple, Any, Dict, List, Optional, Union
import threading
from functools import wraps

# 获取当前文件所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加服务器根目录到Python路径，确保能导入utils等模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))))

from flask import request, jsonify
from utils.response_handler import ResponseHandler, StatusCode
from .services.qywechat_service import CAR_TYPE_MAP, CONFIG, get_qywechat_service

logger = logging.getLogger(__name__)

# 缓存
recent_records_cache = {}
recent_records_expire = {}

# 心跳时间
last_heartbeat_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# API密钥
API_KEY = "car_park_api_key_2025"  # API密钥，生产环境请使用环境变量或配置文件

# 最近续期记录缓存
recent_records_cache = {}
recent_records_expire = {}


# 数据库工具函数
# 数据库路径 - 使用相对路径指向APP/car_park/database目录下的数据库
# DB_PATH = os.path.join(BASE_DIR, 'database', 'car_park.db')
# 数据库路径 - 指向server/database目录下的数据库
# 获取server目录的绝对路径
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(SERVER_DIR, 'database', 'car_park.db')

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def check_api_key(func):
    """API密钥验证装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        api_key = request.args.get('api_key') or request.headers.get('X-API-Key')
        if api_key != API_KEY:
            logger.warning(f"[Car_Park] API密钥验证失败: {api_key}")
            return ResponseHandler.error(
                code=StatusCode.UNAUTHORIZED,
                msg="API密钥错误",
                data={"status": "error", "message": "Unauthorized access"}
            )
        return func(*args, **kwargs)
    return wrapper

def _normalize_input(text: str) -> str:
    """标准化输入文本"""
    # 移除所有空格和特殊字符，只保留中文、字母、数字
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
    return text.strip().upper()  # 车牌号统一转大写

def _check_permission(wechat_id: str) -> bool:
    """检查微信用户权限"""
    # 这里可以实现更复杂的权限检查逻辑
    admin_users = ['admin1', 'admin2', CONFIG['DEFAULT_MESSAGE_RECEIVER']['touser']]
    return wechat_id in admin_users

def update_heartbeat_time():
    """更新心跳时间"""
    try:
        heartbeat_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))),
            CONFIG["HEARTBEAT_FILE"]
        )
        with open(heartbeat_file, 'w') as f:
            f.write(str(time.time()))
        logger.info("[Car_Park] 心跳时间已更新")
    except Exception as e:
        logger.error(f"[Car_Park] 更新心跳时间失败: {str(e)}")

def check_client_heartbeat():
    """检查客户端心跳状态"""
    try:
        heartbeat_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(BASE_DIR))),
            CONFIG["HEARTBEAT_FILE"]
        )
        if not os.path.exists(heartbeat_file):
            return False
        
        with open(heartbeat_file, 'r') as f:
            last_heartbeat = float(f.read().strip())
        
        current_time = time.time()
        return current_time - last_heartbeat <= CONFIG["HEARTBEAT_TIMEOUT"].total_seconds()
    except Exception as e:
        logger.error(f"[Car_Park] 检查客户端心跳状态失败: {str(e)}")
        return False


def _query_car_info(query: str, from_user: str) -> str:
    """查询车辆信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        normalized_query = _normalize_input(query)
        
        # 尝试按车牌号查询
        cursor.execute("""
            SELECT 
                p.plateNumber, 
                pp.pName, 
                p.endTime, 
                p.plateStandard, 
                pp.pPhone, 
                pp.pAddress
            FROM Sys_Park_Plate p
            JOIN Sys_Park_Person pp ON p.personId = pp.id
            WHERE p.isDel = 0 AND REPLACE(p.plateNumber, ' ', '') = ?
        """, (normalized_query,))
        
        result = cursor.fetchone()
        
        if not result:
            # 尝试按车主姓名查询
            cursor.execute("""
                SELECT 
                    p.plateNumber, 
                    pp.pName, 
                    p.endTime, 
                    p.plateStandard, 
                    pp.pPhone, 
                    pp.pAddress
                FROM Sys_Park_Plate p
                JOIN Sys_Park_Person pp ON p.personId = pp.id
                WHERE p.isDel = 0 AND pp.pName LIKE ?
            """, (f"%{query}%",))
            
            results = cursor.fetchall()
            if results:
                if len(results) == 1:
                    result = results[0]
                else:
                    # 多个结果
                    response = ["查询到多个车辆信息："]
                    for i, r in enumerate(results, 1):
                        response.append(f"\n{i}. 车牌号：{r['plateNumber']}")
                        response.append(f"   车主：{r['pName']}")
                        if r['endTime']:
                            expire_dt = datetime.strptime(r['endTime'], '%Y-%m-%d %H:%M:%S')
                            days_diff = (expire_dt - datetime.now()).days
                            response.append(f"   到期时间：{expire_dt.strftime('%Y-%m-%d')}")
                            response.append(f"   剩余天数：{days_diff}天")
                    conn.close()
                    return "".join(response)
            
            if not result:
                conn.close()
                return f"未找到车辆信息: {query}"
        
        # 格式化单个查询结果
        car_type = CAR_TYPE_MAP.get(result['plateStandard'], "其他车辆")
        response = [
            f"车牌号：{result['plateNumber']}",
            f"车主：{result['pName']}",
            f"车辆类型：{car_type}"
        ]
        
        if result['endTime']:
            expire_dt = datetime.strptime(result['endTime'], '%Y-%m-%d %H:%M:%S')
            days_diff = (expire_dt - datetime.now()).days
            response.append(f"到期时间：{expire_dt.strftime('%Y-%m-%d')}")
            response.append(f"剩余天数：{days_diff}天")
            if days_diff < 0:
                response.append("⚠️ 已过期，请及时续期")
            elif days_diff <= 7:
                response.append("⚠️ 即将过期，请及时续期")
        
        if result['pPhone']:
            response.append(f"联系电话：{result['pPhone']}")
        if result['pAddress']:
            response.append(f"地址：{result['pAddress']}")
        
        conn.close()
        return "\n".join(response)
        
    except Exception as e:
        logger.error(f"[Car_Park] 查询车辆信息失败: {str(e)}")
        return "查询失败，请稍后再试"

def _add_wechat_id(content: str, from_user: str, action: str) -> str:
    """处理微信ID绑定/解绑"""
    try:
        parts = content.split(" ")
        if len(parts) != 3:
            return f"输入格式错误，请使用：{action} 姓名 电话"
        
        name = parts[1]
        phone = parts[2]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查找用户
        cursor.execute("""
            SELECT id, pName, pPhone, wechat_id 
            FROM Sys_Park_Person 
            WHERE pName = ? AND pPhone = ?
        """, (name, phone))
        
        person = cursor.fetchone()
        if not person:
            conn.close()
            return f"未找到用户：{name} {phone}"
        
        if action == 'bind':
            # 检查是否已绑定
            if person['wechat_id']:
                if person['wechat_id'] == from_user:
                    return "您已绑定此账号"
                else:
                    return "该账号已被其他微信绑定，请联系管理员"
            
            # 绑定微信ID
            cursor.execute("""
                UPDATE Sys_Park_Person 
                SET wechat_id = ? 
                WHERE id = ?
            """, (from_user, person['id']))
            conn.commit()
            conn.close()
            return f"绑定成功！欢迎您，{name}！"
        
        elif action == 'unbind':
            # 检查绑定关系
            if person['wechat_id'] != from_user:
                conn.close()
                return "您没有权限解绑此账号"
            
            # 解绑微信ID
            cursor.execute("""
                UPDATE Sys_Park_Person 
                SET wechat_id = NULL 
                WHERE id = ?
            """, (person['id'],))
            conn.commit()
            conn.close()
            return f"解绑成功！"
        
    except Exception as e:
        logger.error(f"[Car_Park] 处理{action}失败: {str(e)}")
        return "处理失败，请稍后再试"

def _handle_event(xml_data: Dict[str, Any]) -> Optional[str]:
    """处理企业微信事件"""
    try:
        event_type = xml_data.get('Event')
        if event_type == 'open_approval_change':
            # 处理审批状态变更事件
            approval_info = xml_data.get('ApprovalInfo')
            if not approval_info:
                logger.warning("[Car_Park] 审批事件数据不完整")
                return None
            
            # 解析审批数据
            approval_data = parse_approval_data(approval_info)
            
            # 如果审批通过，保存车辆信息
            if approval_data.get('sp_status') == 1:
                save_result = save_car_park_info(approval_data)
                if save_result:
                    logger.info(f"[Car_Park] 审批通过，车辆信息已保存: {approval_data.get('car_number')}")
                else:
                    logger.error(f"[Car_Park] 审批通过，但保存车辆信息失败")
    
    except Exception as e:
        logger.error(f"[Car_Park] 处理事件失败: {str(e)}")
    
    return None

def _add_remark(content: str, from_user: str) -> str:
    """添加车辆备注"""
    try:
        # 解析输入格式：备注 车牌号 备注内容
        parts = content.split(" ")
        if len(parts) < 3:
            return "输入格式错误，请使用：备注 车牌号 备注内容"
        
        plate_number = parts[1]
        remark = " ".join(parts[2:])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 更新备注
        cursor.execute("""
            UPDATE Sys_Park_Plate 
            SET pRemark = ? 
            WHERE plateNumber = ?
        """, (remark, plate_number))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            return f"备注添加成功：车牌号 {plate_number}"
        else:
            conn.close()
            return f"未找到车辆：{plate_number}"
    
    except Exception as e:
        logger.error(f"[Car_Park] 添加备注失败: {str(e)}")
        return "添加备注失败，请稍后再试"

def _delete_car_info(content: str, from_user: str) -> str:
    """删除车辆信息"""
    try:
        # 检查权限
        if not _check_permission(from_user):
            return "您没有权限执行此操作"
        
        # 解析车牌号
        parts = content.split(" ")
        if len(parts) != 2:
            return "输入格式错误，请使用：删除 车牌号"
        
        plate_number = parts[1]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 软删除
        cursor.execute("""
            UPDATE Sys_Park_Plate 
            SET isDel = 1 
            WHERE plateNumber = ?
        """, (plate_number,))
        
        if cursor.rowcount > 0:
            conn.commit()
            conn.close()
            logger.info(f"[Car_Park] 车辆信息已删除: {plate_number} by {from_user}")
            return f"车辆信息已删除：{plate_number}"
        else:
            conn.close()
            return f"未找到车辆：{plate_number}"
    
    except Exception as e:
        logger.error(f"[Car_Park] 删除车辆信息失败: {str(e)}")
        return "删除失败，请稍后再试"

def _get_recent_records(from_user: str) -> str:
    """获取最近续期记录"""
    try:
        # 检查缓存
        current_time = time.time()
        if from_user in recent_records_cache and recent_records_expire.get(from_user, 0) > current_time:
            return recent_records_cache[from_user]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询最近30天的续期记录
        cursor.execute("""
            SELECT 
                p.plateNumber, 
                pp.pName, 
                p.endTime, 
                p.createTime 
            FROM Sys_Park_Plate p
            JOIN Sys_Park_Person pp ON p.personId = pp.id
            WHERE p.isDel = 0 AND p.createTime > datetime('now', '-30 day')
            ORDER BY p.createTime DESC
            LIMIT 20
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return "最近30天内没有续期记录"
        
        # 格式化结果
        response = ["📋 最近续期记录（30天内）："]
        for row in results:
            create_dt = datetime.strptime(row['createTime'], '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(row['endTime'], '%Y-%m-%d %H:%M:%S') if row['endTime'] else None
            
            response.append(f"\n• 车牌号：{row['plateNumber']}")
            response.append(f"  车主：{row['pName']}")
            response.append(f"  续期时间：{create_dt.strftime('%Y-%m-%d')}")
            if end_dt:
                response.append(f"  到期时间：{end_dt.strftime('%Y-%m-%d')}")
        
        response_text = "".join(response)
        
        # 缓存结果
        recent_records_cache[from_user] = response_text
        recent_records_expire[from_user] = current_time + 300  # 缓存5分钟
        
        return response_text
        
    except Exception as e:
        logger.error(f"[Car_Park] 获取最近记录失败: {str(e)}")
        return "获取记录失败，请稍后再试"


def update_car_park_status(car_id: int, status: int) -> bool:
    """更新车辆状态"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE Sys_Park_Plate 
            SET status = ? 
            WHERE id = ?
        """, (status, car_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"[Car_Park] 更新车辆状态失败: {str(e)}")
        return False


def get_car_park_statistics() -> Dict[str, int]:
    """获取停车场统计信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 统计总车辆数
        cursor.execute("""
            SELECT COUNT(*) as total 
            FROM Sys_Park_Plate 
            WHERE isDel = 0
        """)
        total = cursor.fetchone()['total']
        
        # 统计已过期车辆数
        cursor.execute("""
            SELECT COUNT(*) as expired 
            FROM Sys_Park_Plate 
            WHERE isDel = 0 AND endTime < ?
        """, (current_time,))
        expired = cursor.fetchone()['expired']
        
        # 统计即将过期车辆数（30天内）
        cursor.execute("""
            SELECT COUNT(*) as expiring 
            FROM Sys_Park_Plate 
            WHERE isDel = 0 AND endTime >= ? AND endTime <= datetime(?, '+30 day')
        """, (current_time, current_time))
        expiring = cursor.fetchone()['expiring']
        
        # 统计正常车辆数
        normal = total - expired - expiring
        
        conn.close()
        
        return {
            'total': total,
            'expired': expired,
            'expiring': expiring,
            'normal': normal
        }
        
    except Exception as e:
        logger.error(f"[Car_Park] 获取统计信息失败: {str(e)}")
        return {
            'total': 0,
            'expired': 0,
            'expiring': 0,
            'normal': 0
        }


def check_expiring_vehicles():
    """检查即将过期和已过期的车辆并发送提醒"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        logger.info("[Car_Park] 开始检查即将过期和已过期的车辆")
        current_time = datetime.now()
        expiry_check_time = current_time + timedelta(days=3)
        expired_limit_time = current_time - timedelta(days=31)  # 31天前的时间

        # 查询所有需要提醒的车辆（包括即将过期和已过期的）
        cursor.execute("""
            SELECT 
                pp.pName, 
                pp.wechat_id, 
                p.plateNumber, 
                p.endTime,
                p.plateStandard, 
                pp.pAddress, 
                pp.pPhone,
                p.pRemark,
                CASE 
                    WHEN p.endTime > ? THEN '即将过期'
                    ELSE '已过期'
                END as status
            FROM Sys_Park_Plate p
            JOIN Sys_Park_Person pp ON p.personId = pp.id
            WHERE (
                -- 即将过期的车辆（3天内）
                (p.endTime <= ? AND p.endTime > ?)
                OR
                -- 已过期的车辆（31天内）
                (p.endTime <= ? AND p.endTime > ?)
            )
            ORDER BY p.endTime ASC
        """, (
            current_time.strftime('%Y-%m-%d %H:%M:%S'),
            expiry_check_time.strftime('%Y-%m-%d %H:%M:%S'),
            current_time.strftime('%Y-%m-%d %H:%M:%S'),
            current_time.strftime('%Y-%m-%d %H:%M:%S'),
            expired_limit_time.strftime('%Y-%m-%d %H:%M:%S')
        ))

        results = cursor.fetchall()
        logger.info(f"[Car_Park] 检查到 {len(results)} 辆车辆")
        # 按车主分组发送消息
        owner_vehicles = {}
        # 管理员通知列表
        admin_expiring = []
        admin_expired = []

        for row in results:
            owner, wechat_id, plate_number, end_time, plate_standard, address, phone, remark, status = row

            # 处理end_time为空的情况
            if end_time is None:
                end_time_dt = None
                days_diff = None
            else:
                end_time_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                days_diff = (end_time_dt - current_time).days

            # 获取车辆类型描述
            car_type = CAR_TYPE_MAP.get(plate_standard, "其他车辆")

            # 构建车辆信息
            vehicle_info = {
                'owner': owner,
                'plate_number': plate_number,
                'car_type': car_type,
                'end_time': end_time_dt,
                'days_diff': abs(days_diff) if days_diff is not None else None,
                'address': address,
                'phone': phone,
                'remark': remark
            }

            # 添加到管理员通知列表
            if status == '即将过期':
                admin_expiring.append(vehicle_info)
            else:
                admin_expired.append(vehicle_info)

            # 如果有微信ID，添加到用户通知列表
            if wechat_id:
                if wechat_id not in owner_vehicles:
                    owner_vehicles[wechat_id] = {
                        'owner': owner,
                        'expiring': [],
                        'expired': []
                    }

                if status == '即将过期':
                    owner_vehicles[wechat_id]['expiring'].append(vehicle_info)
                else:
                    owner_vehicles[wechat_id]['expired'].append(vehicle_info)
        
        logger.info(
            f"[Car_Park] 管理员通知列表：即将过期 {len(admin_expiring)} 辆，已过期 {len(admin_expired)} 辆")
        
        # 发送管理员通知（分批发送）
        if admin_expiring or admin_expired:
            # 发送标题和统计信息
            admin_stats = [
                "📊 车位到期状态日报",
                f"\n📈 统计信息（{current_time.strftime('%Y-%m-%d')}）："
                f"\n• 总计：{len(admin_expiring) + len(admin_expired)}辆"
                f"\n• 即将过期（3天内）：{len(admin_expiring)}辆"
                f"\n• 已过期（31天内）：{len(admin_expired)}辆"
            ]
            get_qywechat_service().send_text_message(
                content="\n".join(admin_stats),
                to_user="ShengTieXiaJiuJingGuoMinBan"
            )
            
            # 分批发送即将过期的车辆信息
            if admin_expiring:
                batch_size = 8  # 每批发送8辆车的信息
                for i in range(0, len(admin_expiring), batch_size):
                    batch = admin_expiring[i:i + batch_size]
                    message_parts = [f"\n⚠️ 即将过期车辆（第{i//batch_size + 1}批）："]
                    for vehicle in batch:
                        # 构建车辆信息字符串
                        car_info = [
                            f"\n• 车主：{vehicle['owner']}",
                            f"  车牌号：{vehicle['plate_number']}",
                            f"  车辆类型：{vehicle['car_type']}",
                            f"  到期时间：{vehicle['end_time'].strftime('%Y-%m-%d') if vehicle['end_time'] else '未定义'}",
                            f"  剩余天数：{vehicle['days_diff']}天"
                        ]
                        if vehicle['phone']:
                            car_info.append(f"  联系电话：{vehicle['phone']}")
                        if vehicle['remark']:
                            car_info.append(f"  备注：{vehicle['remark']}")
                        # 将车辆信息合并为一个字符串并添加到message_parts
                        message_parts.append("\n".join(car_info))
                    get_qywechat_service().send_text_message(
                        content="".join(message_parts),
                        to_user="ShengTieXiaJiuJingGuoMinBan"
                    )
            
            # 分批发送已过期的车辆信息
            if admin_expired:
                batch_size = 8
                for i in range(0, len(admin_expired), batch_size):
                    batch = admin_expired[i:i + batch_size]
                    message_parts = [f"\n❌ 已过期车辆（第{i//batch_size + 1}批）："]
                    for vehicle in batch:
                        car_info = [
                            f"\n• 车主：{vehicle['owner']}",
                            f"  车牌号：{vehicle['plate_number']}",
                            f"  车辆类型：{vehicle['car_type']}",
                            f"  到期时间：{vehicle['end_time'].strftime('%Y-%m-%d') if vehicle['end_time'] else '未定义'}",
                            f"  过期天数：{vehicle['days_diff']}天"
                        ]
                        if vehicle['phone']:
                            car_info.append(f"  联系电话：{vehicle['phone']}")
                        if vehicle['remark']:
                            car_info.append(f"  备注：{vehicle['remark']}")
                        message_parts.append("\n".join(car_info))
                    get_qywechat_service().send_text_message(
                        content="".join(message_parts),
                        to_user="ShengTieXiaJiuJingGuoMinBan"
                    )
        
        # 发送用户通知
        for wechat_id, vehicles in owner_vehicles.items():
            message_parts = [f"📢 您好，{vehicles['owner']}！"]
            
            if vehicles['expiring']:
                message_parts.append("\n\n⚠️ 您有以下车辆即将过期：")
                for v in vehicles['expiring']:
                    message_parts.append(f"\n• 车牌号：{v['plate_number']}")
                    message_parts.append(f"  到期时间：{v['end_time'].strftime('%Y-%m-%d')}")
                    message_parts.append(f"  剩余天数：{v['days_diff']}天")
            
            if vehicles['expired']:
                message_parts.append("\n\n❌ 您有以下车辆已过期：")
                for v in vehicles['expired']:
                    message_parts.append(f"\n• 车牌号：{v['plate_number']}")
                    message_parts.append(f"  到期时间：{v['end_time'].strftime('%Y-%m-%d')}")
                    message_parts.append(f"  过期天数：{v['days_diff']}天")
            
            message_parts.append("\n\n请及时办理续期手续，谢谢！")
            
            get_qywechat_service().send_text_message(
                content="".join(message_parts),
                to_user=wechat_id
            )
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"[Car_Park] 检查过期车辆失败: {str(e)}")
        return False


def start_expiry_check():
    """启动过期检查定时任务"""
    def check_task():
        while True:
            check_expiring_vehicles()
            time.sleep(86400)  # 每天执行一次
    
    # 启动后台线程
    thread = threading.Thread(target=check_task, daemon=True)
    thread.start()
    logger.info("[Car_Park] 过期检查定时任务已启动")


def update_heartbeat_time():
    """更新心跳时间"""
    global last_heartbeat_time
    last_heartbeat_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    logger.info(f"[Car_Park] 心跳时间已更新: {last_heartbeat_time}")


# 启动过期检查任务 注意：过期检查任务不再自动启动，需要在app.py中手动触发
# start_expiry_check()

def get_monthly_cars():
    """获取所有月租车及其到期时间信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        current_time = datetime.now()
        
        # 查询所有月租车信息，包括车主信息
        cursor.execute("""
            SELECT 
                p.plateNumber AS car_number,
                pp.pName AS owner,
                p.endTime AS expire_time,
                p.plateStandard AS car_type,
                p.pRemark AS remark,
                pp.pPhone AS phone,
                pp.pAddress AS address
            FROM Sys_Park_Plate p
            JOIN Sys_Park_Person pp ON p.personId = pp.id
            WHERE p.isDel = 0
            ORDER BY 
                CASE 
                    WHEN p.endTime < ? THEN 0  -- 已过期的排前面
                    ELSE 1
                END,
                p.endTime ASC
        """, (current_time.strftime('%Y-%m-%d %H:%M:%S'),))
        
        results = cursor.fetchall()
        cars = []
        
        for row in results:
            car = dict(row)
            # 计算剩余天数
            if car['expire_time']:
                expire_dt = datetime.strptime(car['expire_time'], '%Y-%m-%d %H:%M:%S')
                days_diff = (expire_dt - current_time).days
                car['remaining_days'] = days_diff
                car['status'] = 'expired' if days_diff < 0 else 'expiring' if days_diff <= 30 else 'normal'
                car['expire_time_display'] = expire_dt.strftime('%Y-%m-%d')
            else:
                car['remaining_days'] = None
                car['status'] = 'unknown'
                car['expire_time_display'] = '未设置'
            
            # 添加车辆类型描述
            car['car_type_name'] = CAR_TYPE_MAP.get(car['car_type'], "其他车辆")
            
            cars.append(car)
        
        conn.close()
        return cars
    
    except Exception as e:
        logger.error(f"获取月租车信息失败: {str(e)}", exc_info=True)
        return []

def parse_approval_data(approval_info: Dict[str, Any]) -> Dict[str, Any]:
    """解析审批数据"""
    try:
        # 提取审批基本信息
        sp_no = approval_info.get('SpNo')  # 审批单号
        sp_status = int(approval_info.get('SpStatus', 0))  # 审批状态
        apply_user = approval_info.get('ApplyUserName')  # 申请人
        apply_time = approval_info.get('ApplyTime')  # 申请时间
        
        # 提取审批表单数据
        form_data = approval_info.get('FormData', {})
        form_items = form_data.get('item', []) if isinstance(form_data.get('item'), list) else [form_data.get('item')]
        
        # 构建字段映射
        field_map = {}
        for item in form_items:
            if isinstance(item, dict) and item.get('name'):
                field_map[item.get('name')] = item.get('value')
        
        # 提取车辆信息
        car_number = field_map.get('车牌号', '')
        car_type = field_map.get('车辆类型', '')
        start_time = field_map.get('开始时间', '')
        end_time = field_map.get('结束时间', '')
        apply_reason = field_map.get('申请事由', '')
        
        # 转换车辆类型
        car_type_map = {
            '业主首车': 1,
            '外部和租户月租车': 2,
            '业主二车': 5
        }
        car_type_code = car_type_map.get(car_type, 1)
        
        return {
            'sp_no': sp_no,
            'sp_status': sp_status,
            'apply_user': apply_user,
            'apply_time': apply_time,
            'car_number': car_number,
            'car_type': car_type_code,
            'car_type_name': car_type,
            'start_time': start_time,
            'end_time': end_time,
            'apply_reason': apply_reason
        }
    except Exception as e:
        logger.error(f"[Car_Park] 解析审批数据失败: {str(e)}")
        return {}

def save_car_park_info(approval_data: Dict[str, Any]) -> bool:
    """保存车辆信息"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取车辆信息
        car_number = approval_data.get('car_number')
        car_type = approval_data.get('car_type')
        end_time = approval_data.get('end_time')
        
        # 检查车辆是否已存在
        cursor.execute("""
            SELECT id FROM Sys_Park_Plate 
            WHERE plateNumber = ? AND isDel = 0
        """, (car_number,))
        existing_car = cursor.fetchone()
        
        if existing_car:
            # 更新车辆信息
            cursor.execute("""
                UPDATE Sys_Park_Plate 
                SET endTime = ?, plateStandard = ? 
                WHERE id = ?
            """, (end_time, car_type, existing_car['id']))
        else:
            # 这里需要添加创建新车辆的逻辑，可能需要先创建车主信息
            # 简化处理，实际应用中需要更完整的逻辑
            pass
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"[Car_Park] 保存车辆信息失败: {str(e)}")
        return False

# ====== car_park表CRUD操作函数 ======

def get_car_park_records() -> List[Dict[str, Any]]:
    """获取所有续期记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM car_park 
            ORDER BY id DESC
        """)
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"[Car_Park] 获取续期记录失败: {str(e)}")
        return []

def get_car_park_record(record_id: int) -> Optional[Dict[str, Any]]:
    """获取单个续期记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM car_park 
            WHERE id = ?
        """, (record_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return dict(result)
        return None
    except Exception as e:
        logger.error(f"[Car_Park] 获取续期记录失败: {str(e)}")
        return None

def add_car_park_record(record_data: Dict[str, Any]) -> bool:
    """添加续期记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最大id，生成新id
        cursor.execute("SELECT MAX(id) as max_id FROM car_park")
        max_id = cursor.fetchone()['max_id'] or 0
        new_id = max_id + 1
        
        # 插入记录
        cursor.execute("""
            INSERT INTO car_park (id, owner, car_number, time, addtime, status, comment, remark)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_id,
            record_data.get('owner', ''),
            record_data.get('car_number', ''),
            record_data.get('time', ''),
            record_data.get('addtime', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            record_data.get('status', 'pending'),
            record_data.get('comment', ''),
            record_data.get('remark', '')
        ))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"[Car_Park] 添加续期记录失败: {str(e)}")
        return False

def update_car_park_record(record_id: int, update_data: Dict[str, Any]) -> bool:
    """更新续期记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建更新语句
        fields = []
        values = []
        
        for key, value in update_data.items():
            fields.append(f"{key} = ?")
            values.append(value)
        
        if fields:
            values.append(record_id)
            query = f"UPDATE car_park SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"[Car_Park] 更新续期记录失败: {str(e)}")
        return False

def delete_car_park_record(record_id: int) -> bool:
    """删除续期记录"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM car_park 
            WHERE id = ?
        """, (record_id,))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"[Car_Park] 删除续期记录失败: {str(e)}")
        return False

