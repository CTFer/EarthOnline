# -*- coding: utf-8 -*-
from flask import Blueprint, request, make_response
import logging
from utils.response_handler import ResponseHandler, StatusCode, api_response
import xml.etree.ElementTree as ET
from lxml import etree  # 添加此导入
import sqlite3
import hashlib
import time
import requests
import threading
import json
import re
from Crypto.Cipher import AES
import base64
import random
import string
import struct
from config.config import TASK_TYPE, DOMAIN, PROD_SERVER
from datetime import datetime, timedelta
from typing import Tuple, Any, Dict, List, Optional
from functools import wraps
import os

# 创建蓝图
car_park_bp = Blueprint('car_park', __name__)
logger = logging.getLogger(__name__)

CONFIG = {
    "corp_id": "ww0e92b0a70b5f5bb6",
    "agent_id": "1000002",
    "corp_secret": "Y9kpZjWjiC1wYAbNby05bHknAqMoZbbIgs51o02sFEk",
    "token": "oGLIAWAUTkFLKFysSBq",
    "encoding_aes_key": "joQ3dt58VNQzMbpWwa4MoVPUBaHQVPRx1aIYa8Cr2pj",
    "template_id": "C4ZW8NykzpNK7YfW5vS9Swnv1xPJ7wTPxHMKAZmAo",
    "HEARTBEAT_TIMEOUT": timedelta(hours=1),  # 心跳超时时间为1小时
    "HEARTBEAT_CHECK_INTERVAL": 300,  # 心跳检查间隔（秒）
    "HEARTBEAT_FILE": "car_park_last_heartbeat.txt",  # 心跳文件路径
    "DEFAULT_MESSAGE_RECEIVER": {
        "touser": "ShengTieXiaJiuJingGuoMinBan|QianHaoJun"  # 发送给指定成员，多个用|分隔
        # "toparty": "1",  # 如果需要发送给指定部门，取消注释并填写部门ID
        # "totag": "1"     # 如果需要发送给指定标签成员，取消注释并填写标签ID
    }
}

# 审批模板控件ID映射
APPROVAL_CONTROL_IDS = {
    "car_number": "Text-1741513512955",  # 车牌号
    "car_type": "Selector-1742995139638",  # 车辆类型
    "park_time": "Number-1742995306717",  # 时长（月）
    "owner": "Text-1741513613871",  # 车主姓名
    "money": "Money-1741513682248",  # 交费记录金额
    "unit_number": "Text-1741513707328",  # 单元号
}

# 添加心跳检测相关变量
ALERT_SENT = False  # 用于跟踪是否已发送报警

# 添加车辆类型映射
CAR_TYPE_MAP = {
    1: "业主首车",
    2: "外部和租户月租车",
    5: "业主二车"
}
plate_info_map = {
        "owner_first": {
        "name": "业主首车60元/月",
        "key": "option-1742995139638",
        "price": 60
    },
    "owner_second": {
        "name": "业主第二车150元/月",
        "key": "option-1742995139639",
        "price": 150
    },
    "tenant": {
        "name": "租户或其他200元/月",
        "key": "option-1742995166414",
        "price": 200
    }
}


class QYWeChatService:
    """企业微信服务类"""

    def __init__(self):
        self.corp_id = CONFIG["corp_id"]
        self.agent_id = CONFIG["agent_id"]
        self.corp_secret = CONFIG["corp_secret"]
        self.token = CONFIG["token"]
        self.encoding_aes_key = CONFIG["encoding_aes_key"]
        self._access_token = None
        self._access_token_expires = 0
        self._lock = threading.Lock()

    def get_template_detail(self, template_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        获取审批模板详情
        Args:
            template_id (str): 模板ID
        Returns:
            Tuple[bool, Dict[str, Any]]: (是否成功, 模板详情/错误信息)
            - 成功时返回 (True, 模板详情字典)
            - 失败时返回 (False, 包含错误信息的字典)
        """
        try:
            access_token = self.get_access_token()
            if not access_token:
                logger.error("[QYWeChat] 获取access_token失败")
                return False, {"error": "获取access_token失败"}
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/gettemplatedetail?access_token={access_token}"
            data = {
                "template_id": CONFIG["template_id"]
            }
            response = requests.post(url, json=data)
            result = response.json()

            if result.get("errcode") == 0:
                template_detail = result.get("template_content", {})
                return True, template_detail
            else:
                error_msg = f"获取审批模板详情失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, {"error": error_msg}

        except Exception as e:
            error_msg = f"获取审批模板详情异常: {str(e)}"
            logger.error(f"[QYWeChat] {error_msg}", exc_info=True)
            return False, {"error": error_msg}

    def get_access_token(self):
        """获取access_token，如果过期会自动刷新"""
        with self._lock:
            now = int(time.time())
            if self._access_token and now < self._access_token_expires - 300:  # 提前5分钟刷新
                return self._access_token
            try:
                url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
                params = {
                    "corpid": self.corp_id,
                    "corpsecret": self.corp_secret
                }

                response = requests.get(url, params=params)
                result = response.json()

                if "access_token" in result:
                    self._access_token = result["access_token"]
                    self._access_token_expires = now + result["expires_in"]
                    logger.info(
                        f"[Car_Park] 获取access_token成功: {self._access_token}")
                    return self._access_token
                else:
                    logger.error(f"[Car_Park] 获取access_token失败: {result}")
                    return None

            except Exception as e:
                logger.error(f"[Car_Park] 获取access_token异常: {str(e)}")
                return None

    def refresh_access_token(self):
        """强制刷新access_token"""
        with self._lock:
            self._access_token = None
            self._access_token_expires = 0
            return self.get_access_token()

    def _create_cipher(self):
        """创建AES加解密器"""
        key = base64.b64decode(self.encoding_aes_key + '=')
        return AES.new(key, AES.MODE_CBC, iv=key[:16])

    def _generate_signature(self, timestamp, nonce, encrypt=None):
        """生成签名"""
        sign_list = [self.token, timestamp, nonce]
        if encrypt:
            sign_list.append(encrypt)
        sign_list.sort()
        sign_str = ''.join(sign_list)
        return hashlib.sha1(sign_str.encode('utf-8')).hexdigest()

    def decrypt_message(self, encrypted_msg):
        """解密消息"""
        try:
            encrypted_data = base64.b64decode(encrypted_msg)

            key = base64.b64decode(self.encoding_aes_key + '=')
            cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
            decrypted_data = cipher.decrypt(encrypted_data)

            pad = decrypted_data[-1]
            if not isinstance(pad, int):
                pad = ord(pad)
            content = decrypted_data[:-pad]

            random_str = content[:16]
            msg_len = struct.unpack('>I', content[16:20])[0]
            msg_content = content[20:20+msg_len]
            receiveid = content[20+msg_len:].decode('utf-8')
            if receiveid != self.corp_id:
                logger.error(
                    f"[Car_Park] 企业ID不匹配: {receiveid} != {self.corp_id}")
                raise ValueError(f"企业ID不匹配: {receiveid} != {self.corp_id}")

            return msg_content.decode('utf-8')

        except Exception as e:
            logger.error(f"[Car_Park] 消息解密失败: {str(e)}", exc_info=True)
            raise

    def encrypt_message(self, reply_msg):
        """加密消息"""
        try:
            # 生成16位随机字符串
            random_str = ''.join(random.choice(
                string.ascii_letters + string.digits) for _ in range(16))

            msg_len = struct.pack('!I', len(reply_msg.encode('utf-8')))
            text = random_str.encode(
                'utf-8') + msg_len + reply_msg.encode('utf-8') + self.corp_id.encode('utf-8')

            pad_num = 32 - (len(text) % 32)
            text += bytes([pad_num] * pad_num)

            # 创建加密器
            cipher = self._create_cipher()

            encrypted_text = cipher.encrypt(text)
            base64_text = base64.b64encode(encrypted_text).decode('utf-8')

            return base64_text

        except Exception as e:
            logger.error(f"[Car_Park] 消息加密失败: {str(e)}", exc_info=True)
            raise

    def verify_url(self, msg_signature, timestamp, nonce, echostr):
        """验证URL有效性"""
        try:
            # 参数完整性检查
            if not all([msg_signature, timestamp, nonce, echostr]):
                logger.error("[Car_Park] URL验证失败：缺少必要参数")
                return None

            signature = self._generate_signature(timestamp, nonce, echostr)

            if signature.lower() != msg_signature.lower():
                logger.error(f"[Car_Park] URL验证失败：签名不匹配")
                return None

            decrypted_str = self.decrypt_message(echostr)
            return decrypted_str.strip()

        except Exception as e:
            logger.error(f"[Car_Park] URL验证异常: {str(e)}", exc_info=True)
            return None

    def send_text_message(self, content, to_user=None, to_party=None, to_tag=None, safe=0):
        """发送文本消息"""
        try:
            access_token = self.get_access_token()
            if not access_token:
                return False, "获取access_token失败"

            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"

            data = {
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {
                    "content": content
                },
                "safe": safe
            }

            if to_user:
                data["touser"] = to_user
            if to_party:
                data["toparty"] = to_party
            if to_tag:
                data["totag"] = to_tag

            if not any([to_user, to_party, to_tag]):
                logger.warning("[Car_Park] 未指定任何接收者，使用默认接收者配置")
                data["touser"] = CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]
                if "toparty" in CONFIG["DEFAULT_MESSAGE_RECEIVER"]:
                    data["toparty"] = CONFIG["DEFAULT_MESSAGE_RECEIVER"]["toparty"]
                if "totag" in CONFIG["DEFAULT_MESSAGE_RECEIVER"]:
                    data["totag"] = CONFIG["DEFAULT_MESSAGE_RECEIVER"]["totag"]

            response = requests.post(url, json=data)
            result = response.json()

            if result.get("errcode") == 0:
                return True, "消息发送成功"
            else:
                error_msg = f"消息发送失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[Car_Park] {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"发送消息异常: {str(e)}"
            logger.error(f"[Car_Park] {error_msg}")
            return False, error_msg

    def _handle_text_message(self, msg_root):
        """处理文本消息
        :param msg_root: 消息XML根节点
        :return: 响应内容
        """
        try:
            content = msg_root.find('Content').text.strip()  # 清理前后空格
            msg_id = msg_root.find('MsgId').text
            from_user = msg_root.find('FromUserName').text

            logger.info(
                f"[Car_Park] 收到文本消息 - 内容: {content}, 消息ID: {msg_id}, 发送者: {from_user}")
            # 判断是否是车牌号（包含数字且长度大于等于6）
            is_plate = len(content) >= 6 and any(char.isdigit()
                                                 for char in content)
            is_name = len(content) >= 2 and any(char.isalpha()
                                                for char in content)
            # 根据内容关键词进行回复 先判断是否是车牌号或者姓名
            if '价格' in content:
                return "停车费用标准：\n1. 业主首车：60元/月\n2. 业主第二车：150元/月\n3. 租户或其他：200元/月"
            elif '绑定，' in content:
                return self._add_wechat_id(from_user, content, True)
            elif '解绑，' in content:
                return self._add_wechat_id(from_user, content, False)
            # 内容以续期开头
            elif content.startswith('续期：'):
                if from_user not in CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]:
                    return "您无权进行续期操作"
                try:
                    content = content[3:].strip()
                    content = content.replace('，', ',')
                    parts = [part.strip() for part in content.split(',')]

                    if len(parts) != 3:
                        return "格式错误，正确格式：续期：车主，车牌号，月数\n例如：续期：张三，川A12345，1"
                    owner = parts[0]
                    car_number = parts[1]
                    try:
                        month = int(parts[2])
                        if month <= 0:
                            return "续期月数必须大于0"
                    except ValueError:
                        return "月数必须是整数"

                    # 添加续期记录
                    addtime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    car_info = {
                        'owner': owner,
                        'car_number': car_number,
                        'parktime': month,
                        'addtime': addtime,
                        'status': 'pending',
                        'remark': '程序添加'
                    }

                    if save_car_park_info(car_info):
                        return (f"续期申请已提交：\n"
                                f"车主：{owner}\n"
                                f"车牌号：{car_number}\n"
                                f"续期时长：{month}个月\n"
                                f"提交时间：{addtime}")
                    else:
                        return f"续期失败：{car_number}（车辆信息不存在或数据库错误）"
                except Exception as e:
                    logger.error(
                        f"[Car_Park] 处理续期请求异常: {str(e)}", exc_info=True)
                    return "续期处理失败，请检查格式是否正确：续期：车主，车牌号，月数"
            elif content.startswith('备注：'):
                if from_user not in CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]:
                    return "您无权进行备注操作"
                # 移除备注：
                content = content[3:].strip()
                content = content.replace('，', ',')
                parts = [part.strip() for part in content.split(',')]
                if len(parts) != 2:
                    return "格式错误，正确格式：备注：车牌号，备注内容"
                car_number = parts[0]
                return self._add_remark(from_user, content)
            elif content == "统计":
                if from_user not in CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]:
                    return "您无权进行统计操作"
                # 获取统计信息
                message_parts = get_car_park_statistics()
                if isinstance(message_parts, list):
                    # 发送概览信息
                    self.send_text_message(
                        content="\n".join(message_parts[:10]),  # 发送基础统计信息
                        to_user=from_user
                    )

                    # 发送即将到期车辆信息
                    expiring_start = 10
                    expiring_end = message_parts.index(
                        "\n❌ 已过期车辆（30天内）：") if "\n❌ 已过期车辆（30天内）：" in message_parts else len(message_parts)
                    if expiring_end > expiring_start:
                        self.send_text_message(
                            content="\n".join(
                                message_parts[expiring_start:expiring_end]),
                            to_user=from_user
                        )

                    # 发送已过期车辆信息
                    expired_start = expiring_end
                    expired_end = message_parts.index(
                        "\n⛔ 长期过期车辆（超30天）：") if "\n⛔ 长期过期车辆（超30天）：" in message_parts else len(message_parts)
                    if expired_end > expired_start:
                        self.send_text_message(
                            content="\n".join(
                                message_parts[expired_start:expired_end]),
                            to_user=from_user
                        )

                    # 发送长期过期车辆信息
                    if expired_end < len(message_parts):
                        self.send_text_message(
                            content="\n".join(message_parts[expired_end:]),
                            to_user=from_user
                        )

                    return None  # 返回None表示已经通过其他方式发送了消息
                else:
                    return message_parts  # 如果是错误信息，直接返回

            elif content.startswith('审批'):
                if from_user not in CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"] and from_user != "cymg":
                    return "您无权进行审批操作"
                # 提取车牌号和时长 移除审批和分隔符 
                content = content[2:].strip()
                # 移除可能存在的分割符号，替换为半角逗号
                pattern = re.compile(r'[^\u4e00-\u9fa5a-zA-Z0-9 ]')
                content = pattern.sub(',', content)
                # 移除开头结尾的非中英文数字字符
                content = re.sub(r'^[^a-zA-Z0-9\u4e00-\u9fa5]+|[^a-zA-Z0-9\u4e00-\u9fa5]+$', '', content)
                print(content)
                parts = [part.strip() for part in content.split(',')]
                if len(parts) != 2:
                    return "格式错误，正确格式：审批：车牌号，时长"
                car_number = parts[0].upper()
                month = int(parts[1])
                if month <= 0:
                    return "时长必须大于0"
                return self._handle_approval(car_number, month)
            elif is_plate or is_name:
                return self._query_car_info(content, not is_plate)
            else:
                return "点击查看祥和园停车管理公约（试行）\nhttps://docs.qq.com/doc/DWVZVdmptY3R3cFF5#\n您可以：\n1. 直接输入车牌号(不区分大小写)查询车辆信息\n2. 直接输入车主姓名查询车辆信息\n3. 发送\"绑定，车主姓名，车牌号\"绑定车辆月租到期提醒\n4. 发送\"解绑，车主姓名，车牌号\"解绑车辆月租到期提醒\n5. 发送\"续期：车主姓名，车牌号，月数\"续期车辆月租\n6. 发送\"备注：车牌号，备注内容\"添加备注\n7. 发送\"统计\"查看统计信息"

        except Exception as e:
            logger.error(f"[Car_Park] 处理文本消息异常: {str(e)}", exc_info=True)
            return "抱歉，处理消息时出现错误，请稍后再试"

    def _query_car_info(self, query, is_name=False):
        """查询车辆信息
        :param query: 查询内容（车牌号或车主姓名）
        :param is_name: 是否按姓名查询
        :return: 查询结果
        """
        try:
            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()

            if is_name:
                # 按姓名查询，移除数字后缀进行模糊匹配
                base_name = ''.join(
                    char for char in query if not char.isdigit())
                sql = """
                SELECT pp.pName, p.plateNumber, p.beginTime, p.endTime, pp.pAddress,
                       p.plateStandard, pp.pPhone ,p.pRemark  -- 添加联系方式
                FROM Sys_Park_Plate p
                LEFT JOIN Sys_Park_Person pp ON p.personId = pp.id
                WHERE pp.pName LIKE ? OR pp.pName LIKE ?
                ORDER BY pp.pName ASC, p.plateStandard ASC, p.endTime DESC
                """
                cursor.execute(sql, (f"{base_name}%", f"{base_name}_"))
            else:
                # 按车牌号查询 参数中的字母自动变大写
                sql = """
                SELECT pp.pName, p.plateNumber, p.beginTime, p.endTime, pp.pAddress,
                       p.plateStandard, pp.pPhone ,p.pRemark  -- 添加联系方式
                FROM Sys_Park_Plate p
                LEFT JOIN Sys_Park_Person pp ON p.personId = pp.id
                WHERE p.plateNumber = ?
                ORDER BY p.endTime DESC
                """
                cursor.execute(sql, (query.upper(),))

            results = cursor.fetchall()
            conn.close()

            if results:
                response = []
                current_owner = None
                car_count = 0

                for row in results:
                    owner, plate_number, begin_time, end_time, address, plate_standard, phone, remark = row

                    # 处理新车主
                    if current_owner != owner:
                        current_owner = owner
                        car_count = 1
                        if len(response) > 0:
                            response.append("")  # 添加空行分隔不同车主
                    else:
                        car_count += 1

                    # 获取车辆类型描述
                    car_type = CAR_TYPE_MAP.get(plate_standard, "其他车辆")

                    # 计算到期状态
                    end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                    days_left = (end_time - datetime.now()).days
                    if days_left > 30:
                        status = f"正常（剩余{days_left}天）"
                    elif days_left > 0:
                        status = f"即将到期（剩余{days_left}天）"
                    else:
                        status = f"已过期（超期{abs(days_left)}天）"

                    # 构建响应信息
                    car_info = [
                        f"车主：{owner}",
                        f"车辆类型：{car_type}",
                        f"车牌号：{plate_number}",
                        f"到期时间：{end_time.strftime('%Y-%m-%d')}",
                        f"状态：{status}",
                    ]
                    if phone:
                        car_info.append(f"联系方式：{phone}")
                    if remark:
                        car_info.append(f"备注：{remark}")

                    response.append("\n".join(car_info))

                return "\n\n".join(response)
            else:
                if is_name:
                    return f'未找到车主"{query}"的月租车信息'
                return f'车牌号"{query}"不是月租车'

        except Exception as e:
            logger.error(f"[Car_Park] 查询车辆信息异常: {str(e)}", exc_info=True)
            return "查询车辆信息失败，请稍后重试"

    def _add_wechat_id(self, from_user, content, is_add):
        """添加或删除微信ID
        :param from_user: 发送者UserID
        :param content: 绑定信息
        :param is_add: True为绑定，False为解绑
        :return: 响应内容
        """
        try:
            # 解析内容
            action = "绑定" if is_add else "解绑"
            # 移除可能存在的全角逗号，替换为半角逗号
            content = content.replace('，', ',').replace('：', ':')
            # 移除开头的"绑定,"或"解绑,"
            if content.startswith(f"{action},"):
                content = content[len(action + ','):]
            elif content.startswith(f"{action}，"):
                content = content[len(action + '，'):]

            # 分割剩余内容
            parts = [p.strip() for p in content.split(',')]
            if len(parts) != 2:
                return f"格式错误，正确格式：{action}，车主姓名，车牌号"

            # 提取车主和车牌信息
            owner = parts[0].strip()
            car_number = parts[1].strip().upper()  # 车牌号转大写

            # 连接数据库
            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()

            try:
                # 查询车主和车牌是否匹配
                cursor.execute("""
                    SELECT pp.id, pp.pName, pp.wechat_id, p.plateNumber
                    FROM Sys_Park_Person pp
                    JOIN Sys_Park_Plate p ON p.personId = pp.id
                    WHERE pp.pName = ? AND p.plateNumber = ?
                """, (owner, car_number))

                result = cursor.fetchone()

                if not result:
                    return f"未找到匹配的车主和车牌信息：{owner} - {car_number}"

                person_id, db_owner, current_wechat_id, db_car_number = result

                if is_add:
                    # 绑定操作
                    if current_wechat_id:
                        if current_wechat_id == from_user:
                            return "该车主已经绑定过您的微信，无需重复绑定"
                        else:
                            return "该车主已绑定其他微信账号，请先解绑"

                    # 更新wechat_id
                    cursor.execute("""
                        UPDATE Sys_Park_Person
                        SET wechat_id = ?
                        WHERE id = ?
                    """, (from_user, person_id))

                    conn.commit()
                    return f"绑定成功！\n车主：{owner}\n车牌号：{car_number}"
                else:
                    # 解绑操作
                    if not current_wechat_id:
                        return "该车主未绑定微信账号"
                    if current_wechat_id != from_user:
                        return "您无权解绑其他人的微信账号"

                    # 清除wechat_id
                    cursor.execute("""
                        UPDATE Sys_Park_Person
                        SET wechat_id = NULL
                        WHERE id = ?
                    """, (person_id,))

                    conn.commit()
                    return f"解绑成功！\n车主：{owner}\n车牌号：{car_number}"

            finally:
                cursor.close()
                conn.close()

        except Exception as e:
            logger.error(
                f"[Car_Park] {'绑定' if is_add else '解绑'}微信ID异常: {str(e)}", exc_info=True)
            return f"{'绑定' if is_add else '解绑'}失败，请稍后重试"

    def _add_remark(self, from_user, content):
        """添加备注
        :param from_user: 发送者UserID
        :param content: 备注信息
        :return: 响应内容
        """
        # 更新Sys_Park_Plate表的pRemark字段 将content中的车牌号和备注内容分开
        try:
            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()

            # 解析内容
            car_number = content.split(',')[0]
            remark = content.split(',')[1]

            # 更新Sys_Park_Plate表的pRemark字段
            cursor.execute(
                "UPDATE Sys_Park_Plate SET pRemark = ? WHERE plateNumber = ?", (remark, car_number))
            conn.commit()
            return f"备注成功！\n车牌号：{car_number}\n备注：{remark}"
        except Exception as e:
            logger.error(f"[Car_Park] 添加备注异常: {str(e)}", exc_info=True)
            return f"添加备注异常: {str(e)}"

    def _handle_event(self, msg_root):
        """处理事件消息"""
        try:
            # 获取事件类型
            event = msg_root.find('Event').text
            logger.info(
                f"[Car_Park] 收到事件: {event}, 发送者: {msg_root.find('FromUserName').text}")

            if event == 'sys_approval_change':
                # 处理审批状态变更事件
                approval_info = msg_root.find('ApprovalInfo')
                if approval_info is not None:
                    sp_no = approval_info.find('SpNo').text
                    sp_status = int(approval_info.find('SpStatus').text)

                    logger.info(
                        f"[Car_Park] 收到审批状态变更 - 单号: {sp_no}, 状态: {sp_status}")

                    # 如果审批通过，获取详细信息并处理
                    if sp_status == 2:  # 2表示审批通过
                        # 获取审批申请详情
                        access_token = self.get_access_token()
                        if not access_token:
                            logger.error("[Car_Park] 获取access_token失败")
                            return 'success'

                        # 调用获取审批详情接口
                        url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={access_token}"
                        data = {
                            "sp_no": sp_no
                        }

                        try:
                            response = requests.post(url, json=data)
                            if response.status_code == 200:
                                result = response.json()
                                if result.get('errcode') == 0:
                                    # 解析审批数据
                                    approval_data = result.get('info', {})
                                    car_info = parse_approval_data(
                                        approval_data)
                                    if car_info:
                                        # 处理审批通过的逻辑
                                        logger.info(
                                            f"[Car_Park] 审批通过，车辆信息: {car_info}")
                                        # 这里添加处理审批通过后的业务逻辑
                                        if save_car_park_info(car_info):
                                            logger.info("[Car_Park] 车辆信息保存成功")
                                        else:
                                            logger.error("[Car_Park] 车辆信息保存失败")
                                    else:
                                        logger.error("[Car_Park] 审批数据解析失败")
                                else:
                                    logger.error(
                                        f"[Car_Park] 获取审批详情失败: {result}")
                            else:
                                logger.error(
                                    f"[Car_Park] 获取审批详情请求失败: {response.text}")
                        except Exception as e:
                            logger.error(
                                f"[Car_Park] 获取审批详情异常: {str(e)}", exc_info=True)

            return 'success'
        except Exception as e:
            logger.error(f"[Car_Park] 处理事件消息异常: {str(e)}", exc_info=True)
            return 'success'  # 返回success避免企业微信重试
    
    def _handle_approval(self, car_number: str, months: int, from_user: str = None) -> str:
        """
        发起审批请求

        Args:
            car_number (str): 车牌号
            months (int): 续期时长（月）
            from_user (str, optional): 发起请求的用户ID，如果为None则使用默认用户

        Returns:
            str: 处理结果
        """
        try:
            # 使用当前实例的access_token，无需重新创建服务实例
            access_token = self.get_access_token()
            if not access_token:
                logger.error("[Car_Park] 获取访问令牌失败")
                return "获取访问令牌失败"
            
            # 如果未提供from_user，使用默认用户
            if from_user is None:
                from_user = "ShengTieXiaJiuJingGuoMinBan"
                
            # 从数据库查询车辆信息
            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()
            try:
                # 查询车主信息，先查询车辆
                cursor.execute('''
                    SELECT p.personId, p.plateStandard
                    FROM Sys_Park_Plate p
                    WHERE p.plateNumber = ?
                    LIMIT 1
                ''', (car_number,))
                vehicle_result = cursor.fetchone()
                
                if not vehicle_result:
                    logger.error(f"[Car_Park] 车辆不存在: {car_number}")
                    return "车辆不存在"
                    
                person_id = vehicle_result[0]
                plate_standard = vehicle_result[1]
                
                # 将plateStandard映射到车辆类型
                if plate_standard == 1:
                    car_type = "owner_first"  # 业主首车
                elif plate_standard == 5:
                    car_type = "owner_second"  # 业主第二车
                else:
                    car_type = "tenant"  # 租户或其他
                
                # 查询车主姓名和单元号
                cursor.execute('''
                    SELECT pp.pName, pp.pAddress
                    FROM Sys_Park_Person pp
                    WHERE pp.id = ?
                ''', (person_id,))
                person_result = cursor.fetchone()
                
                if not person_result:
                    logger.error(f"[Car_Park] 车主信息不存在，车主ID: {person_id}")
                    return "车主信息不存在"
                    
                owner_name, unit_number = person_result
                
                # 处理单元号可能为None的情况
                if unit_number is None:
                    unit_number = "0-0-0"
            finally:
                cursor.close()
                conn.close()
                
            # 确保车辆类型有效
            if car_type not in plate_info_map:
                logger.warning(f"[Car_Park] 无效的车辆类型: {car_type}，使用默认类型: owner_first")
                car_type = "owner_first"
                
            # 计算金额
            price_per_month = plate_info_map[car_type]["price"]
            total_amount = price_per_month * months
            
            # 准备审批请求数据 - 按照企业微信官方文档格式
            apply_data = {
                "creator_userid": from_user,  # 创建者用户ID
                "template_id": CONFIG["template_id"],  # 审批模板ID
                "use_template_approver": 1,  # 使用审批模板的审批流程
                "approver": [],  # 不指定审批人
                "notifyer": [],  # 不指定抄送人
                "notify_all": 0,  # 不通知所有人
                "apply_data": {
                    "contents": [
                        {
                            "control": "Text",
                            "id": APPROVAL_CONTROL_IDS["car_number"],
                            "title": [{"text": "车牌号", "lang": "zh_CN"}],
                            "value": {"text": car_number}
                        },
                        {
                            "control": "Selector",
                            "id": APPROVAL_CONTROL_IDS["car_type"],
                            "title": [{"text": "车辆类型", "lang": "zh_CN"}],
                            "value": {"selector": {"type": "single", "options": [{"key": plate_info_map[car_type]["key"]}]}}
                        },
                        {
                            "control": "Number",
                            "id": APPROVAL_CONTROL_IDS["park_time"],
                            "title": [{"text": "时长（单位：月）", "lang": "zh_CN"}],
                            "value": {"new_number": months}
                        },
                        {
                            "control": "Text",
                            "id": APPROVAL_CONTROL_IDS["owner"],
                            "title": [{"text": "车主姓名", "lang": "zh_CN"}],
                            "value": {"text": owner_name}
                        },
                        {
                            "control": "Money",
                            "id": APPROVAL_CONTROL_IDS["money"],
                            "title": [{"text": "交费记录金额", "lang": "zh_CN"}],
                            "value": {"new_money": total_amount}
                        },
                        {
                            "control": "Text",
                            "id": APPROVAL_CONTROL_IDS["unit_number"],
                            "title": [{"text": "单元号", "lang": "zh_CN"}],
                            "value": {"text": unit_number}
                        }
                    ]
                },
                "summary_list": [
                    {
                        "summary_info": [{
                            "text": f"车牌号：{car_number}",
                            "lang": "zh_CN"
                        }]
                    },
                    {
                        "summary_info": [{
                            "text": f"车主：{owner_name}",
                            "lang": "zh_CN"
                        }]
                    },
                    {
                        "summary_info": [{
                            "text": f"续期：{months}个月",
                            "lang": "zh_CN"
                        }]
                    }
                ]
            }
            
            # 调用企业微信API发起审批
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/applyevent?access_token={access_token}"
            
            logger.info(f"[Car_Park] 发起审批请求: 车牌号={car_number}, 车主={owner_name}, 时长={months}个月, 金额={total_amount}元")
            # 记录发送的审批数据，便于调试
            logger.debug(f"[Car_Park] 审批数据: {json.dumps(apply_data, ensure_ascii=False)}")
            
            response = requests.post(url, json=apply_data)
            result = response.json()
            
            if result.get("errcode") == 0:
                sp_no = result.get('sp_no')
                logger.info(f"[Car_Park] 审批申请成功: {sp_no}")
                
                # 成功后发送消息通知
                self.send_text_message(
                    content=f"车辆月租审批已发起\n审批单号：{sp_no}\n车牌号：{car_number}\n车主：{owner_name}\n续期时长：{months}个月\n金额：{total_amount}元",
                    to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
                    to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
                    to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
                )
                
                return f"审批申请成功，审批单号: {sp_no}"
            else:
                error_msg = f"审批申请失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[Car_Park] {error_msg}")
                # 记录完整的错误响应内容，便于调试
                logger.debug(f"[Car_Park] 完整错误响应: {json.dumps(result, ensure_ascii=False)}")
                return error_msg
                
        except Exception as e:
            logger.error(f"[Car_Park] 处理审批请求失败: {str(e)}", exc_info=True)
            return f"处理审批请求失败: {str(e)}"

    def handle_message(self, xml_data, msg_signature=None, timestamp=None, nonce=None):
        """处理企业微信消息和事件"""
        try:
            xml_str = xml_data.decode('utf-8')
            root = ET.fromstring(xml_str)
            encrypted_msg = root.find('Encrypt').text

            # 验证消息签名
            signature = self._generate_signature(
                timestamp, nonce, encrypted_msg)
            if signature != msg_signature:
                logger.warning("[Car_Park] 消息签名验证失败")
                return 'success'

            # 解密消息
            decrypted_xml = self.decrypt_message(encrypted_msg)
            msg_root = ET.fromstring(decrypted_xml)

            # 获取消息基本信息
            msg_type = msg_root.find('MsgType').text
            from_user = msg_root.find('FromUserName').text
            to_user = msg_root.find('ToUserName').text

            # 根据消息类型处理
            response_content = "收到消息"
            if msg_type == "text":
                response_content = self._handle_text_message(msg_root)
            elif msg_type == "event":
                response_content = self._handle_event(msg_root)

            # 构建响应XML
            current_timestamp = str(int(time.time()))
            reply_msg = f"""<xml>
                <ToUserName><![CDATA[{from_user}]]></ToUserName>
                <FromUserName><![CDATA[{to_user}]]></FromUserName>
                <CreateTime>{current_timestamp}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{response_content}]]></Content>
                <AgentID>{self.agent_id}</AgentID>
            </xml>"""

            # 加密响应消息
            encrypt = self.encrypt_message(reply_msg)
            signature = self._generate_signature(timestamp, nonce, encrypt)

            return f"""<xml>
                <Encrypt><![CDATA[{encrypt}]]></Encrypt>
                <MsgSignature><![CDATA[{signature}]]></MsgSignature>
                <TimeStamp>{timestamp}</TimeStamp>
                <Nonce><![CDATA[{nonce}]]></Nonce>
            </xml>"""

        except Exception as e:
            logger.error(f"[Car_Park] 处理消息失败: {str(e)}")
            return 'success'


# 创建服务实例
qywechat_service = QYWeChatService()
# 更新心跳时间到文件


def update_heartbeat_time():
    """更新心跳时间到文件"""
    try:
        current_time = datetime.now()
        with open(CONFIG["HEARTBEAT_FILE"], 'w') as f:
            f.write(current_time.strftime('%Y-%m-%d %H:%M:%S'))
        logger.info(f"[Car_Park] 更新心跳时间: {current_time}")
        return True
    except Exception as e:
        logger.error(f"[Car_Park] 更新心跳时间失败: {str(e)}")
        return False

# 从文件获取最后心跳时间


def get_last_heartbeat():
    """从文件获取最后心跳时间"""
    try:
        if not os.path.exists(CONFIG["HEARTBEAT_FILE"]):
            # 如果文件不存在，创建文件并写入当前时间
            update_heartbeat_time()

        with open(CONFIG["HEARTBEAT_FILE"], 'r') as f:
            time_str = f.read().strip()
            return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"[Car_Park] 获取心跳时间失败: {str(e)}")
        # 如果出错，返回当前时间
        return datetime.now()

# 检查客户端心跳状态


def check_client_heartbeat():
    """检查客户端心跳状态"""
    global ALERT_SENT
    current_time = datetime.now()
    last_heartbeat = get_last_heartbeat()
    time_diff = current_time - last_heartbeat

    if time_diff > CONFIG["HEARTBEAT_TIMEOUT"]:
        if not ALERT_SENT:  # 只在第一次超时时发送报警
            # 发送企业微信报警消息
            alert_msg = (
                f"❌系统报警\n"
                f"停车场自动续约客户端可能离线\n"
                f"最后心跳时间: {last_heartbeat.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"已断开时间: {str(time_diff).split('.')[0]}"
            )
            success, _ = qywechat_service.send_text_message(
                content=alert_msg,
                to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
                to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
                to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
            )
            if success:
                logger.warning(f"[Car_Park] 已发送客户端离线报警消息")
                ALERT_SENT = True
            else:
                logger.error(f"[Car_Park] 发送客户端离线报警消息失败")
    elif time_diff <= CONFIG["HEARTBEAT_TIMEOUT"] and ALERT_SENT:
        # 如果客户端恢复，发送恢复通知
        recovery_msg = (
            f"✅ 系统恢复\n"
            f"停车场自动续约客户端已恢复在线\n"
            f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"离线时长: {str(time_diff).split('.')[0]}"
        )
        qywechat_service.send_text_message(
            content=recovery_msg,
            to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
            to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
            to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
        )
        ALERT_SENT = False  # 重置报警状态
        logger.info(f"[Car_Park] 客户端已恢复在线")

# 启动心跳检测线程


def start_heartbeat_check():
    """启动心跳检测线程"""
    # 如果已经启动，则不重复启动
    if hasattr(check_client_heartbeat, 'thread'):
        logger.info("[Car_Park] 心跳检测线程已启动")
        return

    def check_loop():
        while True:
            check_client_heartbeat()
            time.sleep(CONFIG["HEARTBEAT_CHECK_INTERVAL"])

    thread = threading.Thread(target=check_loop, daemon=True)
    thread.start()
    logger.info("[Car_Park] 心跳检测线程已启动")


start_heartbeat_check()


def check_api_key(f):
    """检查API密钥的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 仅对POST请求进行API密钥检查
        if request.method == 'POST':
            api_key = request.headers.get('X-API-KEY')
            expected_key = PROD_SERVER['API_KEY']

            if not api_key:
                logger.warning(f"[Car_Park] 请求中缺少API密钥")
                return ResponseHandler.error(
                    code=StatusCode.UNAUTHORIZED,
                    msg="缺少API密钥"
                )
            if api_key != expected_key:
                logger.warning(
                    f"[Car_Park] API密钥不匹配: {api_key} != {expected_key}")
                return ResponseHandler.error(
                    code=StatusCode.UNAUTHORIZED,
                    msg="无效的API密钥"
                )
            logger.info(f"[Car_Park] API密钥验证成功")
        return f(*args, **kwargs)
    return decorated_function

# 解析审批数据


def parse_approval_data(approval_info: dict) -> dict:
    """
    解析审批数据

    Args:
        approval_info (dict): 审批信息

    Returns:
        dict: 解析后的数据，包含车主、车牌号、续期时长等信息
    """
    try:
        # 初始化结果字典
        result = {
            "owner": "",
            "car_number": "",
            "parktime": 0,
            "addtime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "pending",
            "comment": "",
            "remark": ""
        }

        # 获取申请数据
        apply_data = approval_info.get('apply_data', {})
        if not apply_data:
            logger.error("[Car_Park] 审批数据中缺少apply_data")
            return None

        # 记录原始数据用于调试
        logger.info(f"[Car_Park] 原始数据: {approval_info}")

        # 获取表单控件值
        contents = apply_data.get('contents', [])
        for item in contents:
            # 获取控件ID
            control_id = item.get('id')
            value = item.get('value', {})

            if not control_id or not value:
                continue

            if control_id == APPROVAL_CONTROL_IDS["car_number"]:
                # 车牌号控件
                result["car_number"] = value.get('text', '').strip().upper()
            elif control_id == APPROVAL_CONTROL_IDS["owner"]:
                # 车主姓名控件
                result["owner"] = value.get('text', '').strip()
            elif control_id == APPROVAL_CONTROL_IDS["park_time"]:
                # 续期时长控件
                try:
                    # 注意：新的数据结构中使用new_number字段
                    result["parktime"] = int(float(value.get('new_number', 0)))
                    if result["parktime"] <= 0:
                        logger.error(f"[Car_Park] 续期时长无效: {value}")
                        return None
                except (ValueError, TypeError) as e:
                    logger.error(f"[Car_Park] 续期时长解析失败: {value}, 错误: {str(e)}")
                    return None

        # 验证必要字段
        if not result["car_number"]:
            logger.error("[Car_Park] 未找到车牌号")
            return None
        if not result["owner"]:
            logger.error("[Car_Park] 未找到车主姓名")
            return None
        if result["parktime"] <= 0:
            logger.error("[Car_Park] 续期时长无效")
            return None

        # 添加备注信息
        result["remark"] = (
            f"审批单号: {approval_info.get('sp_no', '')}, "
            f"申请时间: {datetime.fromtimestamp(approval_info.get('apply_time', 0)).strftime('%Y-%m-%d %H:%M:%S')}, "
            f"申请人: {approval_info.get('applyer', {}).get('userid', '')}"
        )

        logger.info(f"[Car_Park] 解析结果: {result}")
        return result

    except Exception as e:
        logger.error(f"[Car_Park] 解析审批数据失败: {str(e)}")
        return None


# 保存车辆信息到数据库


def save_car_park_info(car_info: dict) -> bool:
    """
    :param car_info: 车辆信息字典
    :return: 是否保存成功
    """
    try:
        conn = sqlite3.connect("database/car_park.db")
        cursor = conn.cursor()
        # 检查Sys_Park_Plate数据库中是否存在该车辆信息，存在才添加续期信息
        cursor.execute('SELECT * FROM Sys_Park_Plate WHERE plateNumber = ?',
                       (car_info["car_number"].strip(),))
        result = cursor.fetchone()
        if not result:
            logger.info(f"[Car_Park] 车辆信息不存在: {car_info['car_number']}")
            return False
        remark = car_info.get("remark", "")
        # 插入新记录 清理空格
        cursor.execute('''
        INSERT INTO car_park (
            owner, car_number, time, addtime, status, remark
        ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            car_info["owner"].strip(),
            car_info["car_number"].strip(),
            str(car_info["parktime"]),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'pending',
            remark
        ))

        conn.commit()
        conn.close()
        logger.info(f"[Car_Park] 保存车辆信息成功: {car_info['car_number']}")
        qywechat_service.send_text_message(
            content=f"车辆信息保存成功\n车牌号：{car_info['car_number']}\n车主：{car_info['owner']}\n续期时长：{car_info['parktime']}个月",
            to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
            to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
            to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
        )
        return True

    except Exception as e:
        logger.error(f"[Car_Park] 保存车辆信息失败: {str(e)}", exc_info=True)
        # 发送错误通知到企业微信
        qywechat_service.send_text_message(
            content=f"车辆信息保存失败\n车牌号：{car_info['car_number']}\n车主：{car_info['owner']}\n原因：{str(e)}",
            to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
            to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
            to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
        )
        return False

# 更新车辆状态


def update_car_park_status(car_number: str, status: str, comment: str = None) -> bool:
    """ 
    :param car_number: 车牌号
    :param status: 新状态
    :param comment: 备注信息（可选）
    :return: 是否更新成功
    """
    conn = None
    cursor = None
    try:
        conn = sqlite3.connect("database/car_park.db")
        cursor = conn.cursor()

        # 先获取车主信息
        cursor.execute(
            'SELECT owner FROM car_park WHERE car_number = ?', (car_number,))
        result = cursor.fetchone()
        owner = result[0] if result else "未知"

        if comment:
            cursor.execute('''
            UPDATE car_park 
            SET status = ?, comment = ?
            WHERE car_number = ?
            ''', (status, comment, car_number))
        else:
            cursor.execute('''
            UPDATE car_park 
            SET status = ?
            WHERE car_number = ?
            ''', (status, car_number))

        conn.commit()

        # 如果更新失败，发送企业微信通知
        if status == 'failed':
            message = f"车辆续期失败\n车牌号：{car_number}\n车主：{owner}\n原因：{comment}"
        elif status == 'complete':
            message = f"车辆续期成功\n车牌号：{car_number}\n车主：{owner}\n续期时长：{comment}"

        qywechat_service.send_text_message(
            content=message,
            to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
            to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
            to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
        )

        logger.info(f"[Car_Park] 更新车辆状态成功: {car_number}, status={status}")
        return True

    except Exception as e:
        logger.error(f"[Car_Park] 更新车辆状态失败: {str(e)}", exc_info=True)
        # 发送错误通知到企业微信
        qywechat_service.send_text_message(
            content=f"更新车辆状态失败\n车牌号：{car_number}\n原因：{error_msg}",
            to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
            to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
            to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
        )
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# 获取统计信息 统计车辆总数，即将到期车辆，到期车辆和超期一个月以上的车辆


def get_car_park_statistics():
    """获取停车场统计信息"""
    try:
        conn = sqlite3.connect("database/car_park.db")
        cursor = conn.cursor()
        current_time = datetime.now()

        # 基础统计信息
        stats = {
            "total": 0,          # 总车辆数
            "expiring": 0,       # 即将到期（3天内）
            "expired": 0,        # 已过期（30天内）
            "long_expired": 0,   # 长期过期（超过30天）
            "by_type": {         # 按类型统计
                "owner_first": 0,    # 业主首车
                "owner_second": 0,   # 业主二车
                "tenant": 0,         # 租户车辆
                "other": 0           # 其他
            },
            "expiring_list": [],     # 即将到期车辆列表
            "expired_list": [],      # 已过期车辆列表
            "long_expired_list": []  # 长期过期车辆列表
        }

        # 查询所有车辆信息
        cursor.execute("""
            SELECT 
                p.plateNumber,pp.pName,p.endTime,p.plateStandard,pp.pAddress,pp.pPhone,p.pRemark,pp.wechat_id
            FROM Sys_Park_Plate p
            LEFT JOIN Sys_Park_Person pp ON p.personId = pp.id
            WHERE p.isDel = 0
            ORDER BY p.endTime ASC
        """)

        for row in cursor.fetchall():
            plate_number, owner, end_time, plate_standard, address, phone, remark, wechat_id = row

            # 转换结束时间为datetime对象
            if isinstance(end_time, str):
                end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')

            # 计算剩余天数
            if end_time:
                days_left = (end_time - current_time).days
            else:
                days_left = -999  # 未设置结束时间的情况

            # 更新总数
            stats["total"] += 1

            # 按车辆类型统计
            if plate_standard == 1:
                stats["by_type"]["owner_first"] += 1
            elif plate_standard == 5:
                stats["by_type"]["owner_second"] += 1
            elif plate_standard == 2:
                stats["by_type"]["tenant"] += 1
            else:
                stats["by_type"]["other"] += 1

            # 构建车辆信息
            car_info = {
                "plate_number": plate_number,
                "owner": owner,
                "end_time": end_time.strftime('%Y-%m-%d') if end_time else "未设置",
                "days_left": days_left,
                "type": CAR_TYPE_MAP.get(plate_standard, "其他"),
                "address": address or "未登记",
                "phone": phone or "未登记",
                "has_wechat": bool(wechat_id),
                "remark": remark
            }
            # 按到期状态分类
            if 0 < days_left <= 3:  # 3天内到期
                stats["expiring"] += 1
                stats["expiring_list"].append(car_info)
            elif -30 < days_left <= 0:  # 已过期但不超过30天
                stats["expired"] += 1
                stats["expired_list"].append(car_info)
            elif days_left <= -30:  # 过期超过30天
                stats["long_expired"] += 1
                stats["long_expired_list"].append(car_info)

        cursor.close()
        conn.close()
        # 构建返回消息
        message_parts = [
            "📊 停车场统计信息",
            f"\n总计：{stats['total']}辆",
            f"• 业主首车：{stats['by_type']['owner_first']}辆",
            f"• 业主二车：{stats['by_type']['owner_second']}辆",
            f"• 租户车辆：{stats['by_type']['tenant']}辆",
            f"• 其他车辆：{stats['by_type']['other']}辆",
            f"\n到期情况：",
            f"• 即将到期（3天内）：{stats['expiring']}辆",
            f"• 已过期（30天内）：{stats['expired']}辆",
            f"• 长期过期（超30天）：{stats['long_expired']}辆"
        ]
        # 添加即将到期车辆详情
        if stats["expiring_list"]:
            message_parts.append("\n⚠️ 即将到期车辆：")
            for car in stats["expiring_list"]:
                message_parts.append(
                    f"\n• {car['plate_number']}（{car['days_left']}天）"
                )
        # 添加已过期车辆详情
        if stats["expired_list"]:
            message_parts.append("\n❌ 已过期车辆（30天内）：")
            for car in stats["expired_list"]:
                message_parts.append(
                    f"\n• {car['plate_number']}（{car['days_left']}天）备注：{car['remark']}"
                )
        # 添加长期过期车辆详情
        if stats["long_expired_list"]:
            message_parts.append("\n⛔ 长期过期车辆（超30天）：")
            for car in stats["long_expired_list"]:
                message_parts.append(
                    f"\n• {car['plate_number']}（{car['days_left']}天） 备注：{car['remark']}"
                )

        return "\n".join(message_parts)

    except Exception as e:
        logger.error(f"[Car_Park] 获取统计信息失败: {str(e)}", exc_info=True)
        return f"获取统计信息失败: {str(e)}"


@car_park_bp.route('/qy/access_token', methods=['GET'])
@api_response
def get_qywechat_access_token():
    """获取企业微信access_token"""
    try:
        # 获取access_token
        access_token = qywechat_service.get_access_token()
        return ResponseHandler.success(data={
            'access_token': access_token,
            'expires_in': 7200  # access_token有效期为2小时
        })
    except Exception as e:
        logger.error(f"[Car_Park] 获取access_token失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"获取access_token失败: {str(e)}"
        )


@car_park_bp.route('/qy/access_token/refresh', methods=['POST'])
@api_response
def refresh_qywechat_access_token():
    """强制刷新企业微信access_token"""
    try:
        # 刷新access_token
        access_token = qywechat_service.refresh_access_token()
        return ResponseHandler.success(data={
            'access_token': access_token,
            'expires_in': 7200  # access_token有效期为2小时
        })
    except Exception as e:
        logger.error(f"[Car_Park] 刷新access_token失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"刷新access_token失败: {str(e)}"
        )


@car_park_bp.route('/qy/message/send', methods=['POST'])
@api_response
def send_qywechat_message():
    """发送企业微信消息"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="缺少必要参数: content"
            )

        content = data['content']
        to_user = data.get('touser')
        to_party = data.get('toparty')
        to_tag = data.get('totag')
        safe = data.get('safe', 0)

        success, message = qywechat_service.send_text_message(
            content=content,
            to_user=to_user,
            to_party=to_party,
            to_tag=to_tag,
            safe=safe
        )

        if success:
            return ResponseHandler.success(msg=message)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_MSG_ERROR,
            msg=message
        )

    except Exception as e:
        logger.error(f"[Car_Park] 发送消息失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"发送消息失败: {str(e)}"
        )


@car_park_bp.route('/qy', methods=['GET', 'POST'])
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

        if request.method == 'GET':
            # 验证URL有效性
            echostr = request.args.get('echostr', '')

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


@car_park_bp.route('/review', methods=['GET', 'POST'])
@check_api_key  # 添加API密钥验证
@api_response
def car_park_review():
    """处理车辆续期审核请求"""
    try:
        if request.method == 'GET':
            # 获取待处理的续期请求
            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id, owner, car_number, time, addtime, status, comment
            FROM car_park
            WHERE status = 'pending'
            ORDER BY addtime DESC
            ''')

            reviews = []
            for row in cursor.fetchall():
                reviews.append({
                    'id': row[0],
                    'owner': row[1],
                    'car_number': row[2],
                    'parktime': int(row[3]),
                    'addtime': row[4],
                    'status': row[5],
                    'comment': row[6]
                })

            conn.close()

            # 更新心跳时间（仅在成功获取数据后）
            update_heartbeat_time()
            return ResponseHandler.success(data=reviews)

        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="缺少请求数据"
                )

            # 更新审核状态
            car_number = data.get('car_number')
            status = data.get('status')
            comment = data.get('comment')

            if not all([car_number, status]):
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="缺少必要参数"
                )

            if update_car_park_status(car_number, status, comment):
                # 更新心跳时间（仅在成功更新状态后）
                update_heartbeat_time()
                return ResponseHandler.success(msg="更新状态成功")
            else:
                return ResponseHandler.error(
                    code=StatusCode.SERVER_ERROR,  # 使用SERVER_ERROR替代DB_ERROR
                    msg="更新状态失败"
                )

    except Exception as e:
        error_msg = f"处理续期审核请求失败: {str(e)}"
        logger.error(f"[Car_Park] {error_msg}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=error_msg
        )

# 查询、更新停车场车辆信息


@car_park_bp.route('/car_park', methods=['GET', 'POST'])
@api_response
@check_api_key  # 添加API密钥验证
def car_park_info():
    """查询、更新停车场车辆信息"""
    try:
        if request.method == 'GET':
            # 获取查询参数，用于单独查询
            car_number = request.args.get('car_number')
            owner_name = request.args.get('owner_name')

            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()

            if car_number or owner_name:
                # 单独查询模式
                conditions = []
                params = []
                if car_number:
                    conditions.append("p.plateNumber = ?")
                    params.append(car_number)
                if owner_name:
                    conditions.append("pp.pName LIKE ?")
                    params.append(f"%{owner_name}%")

                query = """
                SELECT pp.pName, p.plateNumber, p.beginTime, p.endTime, p.pRemark
                FROM Sys_Park_Plate p
                LEFT JOIN Sys_Park_Person pp ON p.personId = pp.id
                WHERE """ + " OR ".join(conditions)

                cursor.execute(query, params)
                results = cursor.fetchall()

                if results:
                    car_info = [{
                        "owner": row[0],
                        "car_number": row[1],
                        "begin_time": row[2],
                        "end_time": row[3],
                        "remark": row[4]
                    } for row in results]
                    return ResponseHandler.success(data=car_info)
                else:
                    return ResponseHandler.error(
                        code=StatusCode.NOT_FOUND,
                        msg="未找到相关车辆信息"
                    )
            else:
                # 同步模式：返回所有数据供客户端对比
                # 获取所有人员数据
                cursor.execute("""
                    SELECT id, pName, pSex, departId, pAddress, pPhone, 
                           pParkSpaceCount, pNumber, upload_yun, IDCardNumber, 
                           upload_yun2, personIdStr, address1, address2, address3
                    FROM Sys_Park_Person
                """)
                persons = []
                for row in cursor.fetchall():
                    person = {}
                    for idx, col in enumerate(cursor.description):
                        person[col[0]] = row[idx]
                    persons.append(person)

                # 获取所有车牌数据
                cursor.execute("""
                    SELECT id, personId, plateNumber, plateType, plateParkingSpaceName,
                           beginTime, endTime, createTime, authType, upload_yun,
                           cNumber, pChargeId, pRemark, balance, cardNumber,
                           plateStandard, thirdCount, upload_third, freeTime,
                           createName, plateIdStr, isDel, upload_yun2, parkHourMinutes
                    FROM Sys_Park_Plate
                """)
                plates = []
                for row in cursor.fetchall():
                    plate = {}
                    for idx, col in enumerate(cursor.description):
                        # 处理日期时间字段
                        if isinstance(row[idx], datetime):
                            plate[col[0]] = row[idx].strftime(
                                '%Y-%m-%d %H:%M:%S')
                        else:
                            plate[col[0]] = row[idx]
                    plates.append(plate)

                conn.close()

                # 返回完整数据集
                return ResponseHandler.success(data={
                    "persons": persons,
                    "plates": plates
                })

        elif request.method == 'POST':
            # 接收同步数据
            data = request.get_json()
            if not data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="缺少请求数据"
                )

            persons = data.get('persons', [])
            plates = data.get('plates', [])

            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()

            try:
                # 更新人员数据
                for person in persons:
                    # 检查记录是否存在
                    cursor.execute("""
                        SELECT id FROM Sys_Park_Person WHERE id = ?
                    """, (person['id'],))
                    exists = cursor.fetchone() is not None

                    if exists:
                        # 更新现有记录，但保留Wechat_id字段
                        cursor.execute("""
                            UPDATE Sys_Park_Person 
                            SET pName = ?, pSex = ?, departId = ?, pAddress = ?, 
                                pPhone = ?, pParkSpaceCount = ?, pNumber = ?, 
                                upload_yun = ?, IDCardNumber = ?, upload_yun2 = ?, 
                                personIdStr = ?, address1 = ?, address2 = ?, 
                                address3 = ?
                            WHERE id = ?
                        """, (
                            person['pName'], person['pSex'], person['departId'],
                            person['pAddress'], person['pPhone'], person['pParkSpaceCount'],
                            person['pNumber'], person['upload_yun'], person['IDCardNumber'],
                            person['upload_yun2'], person['personIdStr'], person['address1'],
                            person['address2'], person['address3'], person['id']
                        ))
                    else:
                        # 插入新记录
                        cursor.execute("""
                            INSERT INTO Sys_Park_Person (
                                id, pName, pSex, departId, pAddress, pPhone,
                                pParkSpaceCount, pNumber, upload_yun, IDCardNumber,
                                upload_yun2, personIdStr, address1, address2, address3
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            person['id'], person['pName'], person['pSex'],
                            person['departId'], person['pAddress'], person['pPhone'],
                            person['pParkSpaceCount'], person['pNumber'],
                            person['upload_yun'], person['IDCardNumber'],
                            person['upload_yun2'], person['personIdStr'],
                            person['address1'], person['address2'], person['address3']
                        ))

                # 更新车牌数据
                for plate in plates:
                    # 检查记录是否存在
                    cursor.execute("""
                        SELECT id FROM Sys_Park_Plate WHERE id = ?
                    """, (plate['id'],))
                    exists = cursor.fetchone() is not None

                    if exists:
                        # 更新现有记录
                        cursor.execute("""
                            UPDATE Sys_Park_Plate 
                            SET personId = ?, plateNumber = ?, plateType = ?, 
                                plateParkingSpaceName = ?, beginTime = ?, endTime = ?, 
                                createTime = ?, authType = ?, upload_yun = ?, 
                                cNumber = ?, pChargeId = ?, pRemark = ?, balance = ?, 
                                cardNumber = ?, plateStandard = ?, thirdCount = ?, 
                                upload_third = ?, freeTime = ?, createName = ?, 
                                plateIdStr = ?, isDel = ?, upload_yun2 = ?, 
                                parkHourMinutes = ?
                            WHERE id = ?
                        """, (
                            plate['personId'], plate['plateNumber'], plate['plateType'],
                            plate['plateParkingSpaceName'], plate['beginTime'],
                            plate['endTime'], plate['createTime'], plate['authType'],
                            plate['upload_yun'], plate['cNumber'], plate['pChargeId'],
                            plate['pRemark'], plate['balance'], plate['cardNumber'],
                            plate['plateStandard'], plate['thirdCount'],
                            plate['upload_third'], plate['freeTime'], plate['createName'],
                            plate['plateIdStr'], plate['isDel'], plate['upload_yun2'],
                            plate['parkHourMinutes'], plate['id']
                        ))
                    else:
                        # 插入新记录
                        cursor.execute("""
                            INSERT INTO Sys_Park_Plate (
                                id, personId, plateNumber, plateType, plateParkingSpaceName,
                                beginTime, endTime, createTime, authType, upload_yun,
                                cNumber, pChargeId, pRemark, balance, cardNumber,
                                plateStandard, thirdCount, upload_third, freeTime,
                                createName, plateIdStr, isDel, upload_yun2, parkHourMinutes
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            plate['id'], plate['personId'], plate['plateNumber'],
                            plate['plateType'], plate['plateParkingSpaceName'],
                            plate['beginTime'], plate['endTime'], plate['createTime'],
                            plate['authType'], plate['upload_yun'], plate['cNumber'],
                            plate['pChargeId'], plate['pRemark'], plate['balance'],
                            plate['cardNumber'], plate['plateStandard'],
                            plate['thirdCount'], plate['upload_third'],
                            plate['freeTime'], plate['createName'], plate['plateIdStr'],
                            plate['isDel'], plate['upload_yun2'], plate['parkHourMinutes']
                        ))

                conn.commit()
                logger.info(
                    f"[Car_Park] 同步数据成功 - {len(persons)}个人员, {len(plates)}个车牌")
                # 输出同步车牌的详情
                logger.info(f"[Car_Park] 同步车牌详情: {plates}")
                return ResponseHandler.success(msg="数据同步成功")

            except Exception as e:
                conn.rollback()
                error_msg = f"数据同步失败: {str(e)}"
                logger.error(f"[Car_Park] {error_msg}")
                return ResponseHandler.error(
                    code=StatusCode.SERVER_ERROR,
                    msg=error_msg
                )
            finally:
                conn.close()

    except Exception as e:
        error_msg = f"处理请求失败: {str(e)}"
        logger.error(f"[Car_Park] {error_msg}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=error_msg
        )

# 客户端存活通知


@car_park_bp.route('/client_alive', methods=['GET'])
@api_response
@check_api_key  # 添加API密钥验证
def client_alive():
    """处理客户端存活通知"""
    try:
        # 获取客户端状态信息
        park_system_status = request.args.get('status', 'unknown')
        process_id = request.args.get('process_id', 'unknown')
        memory_usage = request.args.get('memory_usage', 'unknown')
        cpu_usage = request.args.get('cpu_usage', 'unknown')

        # 更新心跳时间
        update_heartbeat_time()

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
            qywechat_service.send_text_message(
                content=error_msg,
                to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]
            )

            return ResponseHandler.success(
                msg="客户端存活通知已接收，系统状态异常",
                data={
                    "status": "warning",
                    "message": "停车场系统状态异常，已发送通知"
                }
            )

        return ResponseHandler.success(
            msg="客户端存活通知已接收",
            data={
                "status": "ok",
                "message": "系统运行正常"
            }
        )

    except Exception as e:
        error_msg = f"处理客户端存活通知失败: {str(e)}"
        logger.error(f"[Car_Park] {error_msg}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=error_msg
        )


def check_expiring_vehicles():
    """检查即将过期和已过期的车辆并发送提醒"""
    try:
        conn = sqlite3.connect("database/car_park.db")
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

            # 处理end_time为空的情况（虽然SQL已经排除，但为了代码健壮性仍保留此检查）
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
            qywechat_service.send_text_message(
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
                    qywechat_service.send_text_message(
                        content="\n".join(message_parts),
                        to_user="ShengTieXiaJiuJingGuoMinBan"
                    )
            # 分批发送已过期的车辆信息
            if admin_expired:
                batch_size = 8  # 每批发送8辆车的信息
                for i in range(0, len(admin_expired), batch_size):
                    batch = admin_expired[i:i + batch_size]
                    message_parts = [f"\n❌ 已过期车辆（第{i//batch_size + 1}批）："]
                    for vehicle in batch:
                        car_info = [
                            f"\n• 车主：{vehicle['owner']}",
                            f"  车牌号：{vehicle['plate_number']}",
                            f"  车辆类型：{vehicle['car_type']}",
                            f"  到期时间：{vehicle['end_time'].strftime('%Y-%m-%d') if vehicle['end_time'] else '未定义'}",
                            f"  已过期：{vehicle['days_diff']}天" if vehicle['days_diff'] is not None else "  到期时间：未定义"
                        ]
                        if vehicle['phone']:
                            car_info.append(f"  联系电话：{vehicle['phone']}")
                        if vehicle['remark']:
                            car_info.append(f"  备注：{vehicle['remark']}")
                        # 将车辆信息合并为一个字符串并添加到message_parts
                        message_parts.append("\n".join(car_info))
                    qywechat_service.send_text_message(
                        content="\n".join(message_parts),
                        to_user="ShengTieXiaJiuJingGuoMinBan"
                    )
                logger.info(f"[Car_Park] 已发送管理员车位状态日报")
        # 为每个已绑定微信的车主发送消息
        for wechat_id, info in owner_vehicles.items():
            message_parts = [f"📢 尊敬的{info['owner']}，以下是您的车位状态提醒："]
            # 添加即将过期的车辆信息
            if info['expiring']:
                message_parts.append("\n⚠️ 即将过期的车辆：")
                for vehicle in info['expiring']:
                    message_parts.append(
                        f"\n• 车牌号：{vehicle['plate_number']}"
                        f"\n  车辆类型：{vehicle['car_type']}"
                        f"\n  到期时间：{vehicle['end_time'].strftime('%Y-%m-%d') if vehicle['end_time'] else '未定义'}"
                        f"\n  剩余天数：{vehicle['days_diff']}天"
                    )

            # 添加已过期的车辆信息
            if info['expired']:
                message_parts.append("\n❌ 已过期的车辆：")
                for vehicle in info['expired']:
                    message_parts.append(
                        f"\n• 车牌号：{vehicle['plate_number']}"
                        f"\n  车辆类型：{vehicle['car_type']}"
                        f"\n  到期时间：{vehicle['end_time'].strftime('%Y-%m-%d') if vehicle['end_time'] else '未定义'}"
                        f"\n  已过期：{vehicle['days_diff']}天" if vehicle['days_diff'] is not None else "  到期时间：未定义"
                    )
            # 发送消息
            message = "\n".join(message_parts)
            qywechat_service.send_text_message(
                content=message, to_user=wechat_id)
            logger.info(f"[Car_Park] 已发送车位状态提醒 - 车主：{info['owner']}")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"[Car_Park] 检查车辆状态异常: {str(e)}", exc_info=True)


def start_expiry_check():
    """启动过期检查定时任务"""
    def check_loop():
        while True:
            # 获取当前时间
            now = datetime.now()
            # 设置下次执行时间为明天凌晨2点
            next_run = (now + timedelta(days=1)).replace(hour=9,
                                                         minute=0, second=0, microsecond=0)
            # 计算等待时间
            wait_seconds = (next_run - now).total_seconds()
            # 休眠到指定时间
            time.sleep(wait_seconds)
            # 执行检查
            check_expiring_vehicles()
    # 创建并启动线程
    thread = threading.Thread(target=check_loop, daemon=True)
    thread.start()
    logger.info("[Car_Park] 车位到期检查定时任务已启动")


# 在文件末尾添加初始化调用
start_expiry_check()
# check_expiring_vehicles()
