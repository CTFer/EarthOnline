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
    "amount": "Money-1741513682248",  # 交费金额
    "unit": "Text-1741513707328",  # 单元号
    "attachment": "File-1741513763522"  # 附件
}

# 添加心跳检测相关变量
ALERT_SENT = False  # 用于跟踪是否已发送报警


class QYWeChatAuth:
    """企业微信鉴权类"""
    _instances = {}  # 用于存储不同配置的实例
    _lock = threading.Lock()

    def __new__(cls, corp_id=None, agent_id=None, corp_secret=None, token=None,
                encoding_aes_key=None):
        # 如果没有提供参数，使用默认配置
        if all(param is None for param in [corp_id, agent_id, corp_secret, token,
                                           encoding_aes_key]):
            corp_id = CONFIG["corp_id"]
            agent_id = CONFIG["agent_id"]
            corp_secret = CONFIG["corp_secret"]
            token = CONFIG["token"]
            encoding_aes_key = CONFIG["encoding_aes_key"]

        # 创建配置键
        config_key = f"{corp_id}:{agent_id}"

        if config_key not in cls._instances:
            with cls._lock:
                if config_key not in cls._instances:
                    instance = super(QYWeChatAuth, cls).__new__(cls)
                    instance._init_config(
                        corp_id=corp_id,
                        agent_id=agent_id,
                        corp_secret=corp_secret,
                        token=token,
                        encoding_aes_key=encoding_aes_key
                    )
                    cls._instances[config_key] = instance
        return cls._instances[config_key]

    def _init_config(self, corp_id, agent_id, corp_secret, token, encoding_aes_key):
        """初始化配置"""
        if not hasattr(self, 'initialized'):
            self.corp_id = corp_id
            self.agent_id = agent_id
            self.corp_secret = corp_secret
            self.token = token
            self.encoding_aes_key = encoding_aes_key
            self._access_token = None
            self._access_token_expires = 0
            self.initialized = True

            # 记录配置信息
            logger.info(f"[QYWeChatAuth] 初始化企业微信配置:")
            logger.info(f"[QYWeChatAuth] - 企业ID: {self.corp_id}")
            logger.info(f"[QYWeChatAuth] - 应用ID: {self.agent_id}")

    @classmethod
    def get_instance(cls, corp_id=None, agent_id=None, corp_secret=None, token=None, encoding_aes_key=None):
        """获取指定配置的实例"""
        return cls(corp_id, agent_id, corp_secret, token, encoding_aes_key)

    @classmethod
    def clear_instances(cls):
        """清除所有实例（用于测试）"""
        with cls._lock:
            cls._instances.clear()


class QYWeChatService:
    """企业微信服务类"""

    def __init__(self):
        """初始化企业微信服务"""
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
            # 获取access_token
            access_token = self.get_access_token()
            if not access_token:
                logger.error("[QYWeChat] 获取access_token失败")
                return False, {"error": "获取access_token失败"}

            # 构建请求URL
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/gettemplatedetail?access_token={access_token}"

            # 构建请求数据
            data = {
                "template_id": CONFIG["template_id"]
            }

            logger.info(f"[QYWeChat] 获取审批模板 {CONFIG['template_id']} 详情")
            response = requests.post(url, json=data)
            result = response.json()

            if result.get("errcode") == 0:
                template_detail = result.get("template_content", {})
                logger.info(f"[QYWeChat] 获取审批模板详情成功")
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
            # Base64解码
            encrypted_data = base64.b64decode(encrypted_msg)

            # AES解密
            key = base64.b64decode(self.encoding_aes_key + '=')
            cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
            decrypted_data = cipher.decrypt(encrypted_data)

            # 处理PKCS7填充
            pad = decrypted_data[-1]
            if not isinstance(pad, int):
                pad = ord(pad)
            content = decrypted_data[:-pad]

            # 解析数据结构
            random_str = content[:16]
            msg_len = struct.unpack('>I', content[16:20])[0]
            msg_content = content[20:20+msg_len]
            receiveid = content[20+msg_len:].decode('utf-8')

            # 验证企业ID
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

            # 生成密文
            msg_len = struct.pack('!I', len(reply_msg.encode('utf-8')))
            text = random_str.encode(
                'utf-8') + msg_len + reply_msg.encode('utf-8') + self.corp_id.encode('utf-8')

            # 补位
            pad_num = 32 - (len(text) % 32)
            text += bytes([pad_num] * pad_num)

            # 创建加密器
            cipher = self._create_cipher()

            # AES加密
            encrypted_text = cipher.encrypt(text)

            # Base64编码
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

            # 生成签名
            signature = self._generate_signature(timestamp, nonce, echostr)

            if signature.lower() != msg_signature.lower():
                logger.error(f"[Car_Park] URL验证失败：签名不匹配")
                return None

            # 解密echostr
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

            # 添加接收者
            if to_user:
                data["touser"] = to_user
            if to_party:
                data["toparty"] = to_party
            if to_tag:
                data["totag"] = to_tag

            # 确保至少有一个接收者
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
            content = msg_root.find('Content').text
            msg_id = msg_root.find('MsgId').text
            from_user = msg_root.find('FromUserName').text

            logger.info(
                f"[Car_Park] 收到文本消息 - 内容: {content}, 消息ID: {msg_id}, 发送者: {from_user}")

            # 根据内容关键词进行回复
            if '你好' in content or 'hello' in content.lower():
                return "你好！我是停车场管理助手，可以帮您查询车位信息。"
            elif '帮助' in content or 'help' in content.lower():
                return "您可以：\n1. 发送车牌号查询车位信息\n2. 发送\"续费\"了解续费流程\n3. 发送\"价格\"查询停车费用"
            elif '续费' in content:
                return "续费流程：\n1. 点击菜单\"月租车登记\"\n2. 填写车辆信息\n3. 等待物业审批\n4. 审批通过后即可续费成功"
            elif '价格' in content:
                return "停车费用标准：\n1. 业主首车：60元/月\n2. 业主第二车：150元/月\n3. 租户或其他：200元/月"
            else:
                # 检查是否是车牌号查询
                if len(content) >= 6 and any(char.isdigit() for char in content):
                    return self._query_car_info(content)
                return f"收到您的消息：{content}\n如需帮助请回复\"帮助\""

        except Exception as e:
            logger.error(f"[Car_Park] 处理文本消息异常: {str(e)}", exc_info=True)
            return "抱歉，处理消息时出现错误，请稍后再试"

    def _query_car_info(self, car_number):
        """查询车辆信息
        :param car_number: 车牌号
        :return: 查询结果
        """
        try:
            conn = sqlite3.connect("database/car_park.db")
            cursor = conn.cursor()

            cursor.execute('''
            SELECT car_number, owner, car_type, parktime, start_date, end_date 
            FROM car_park 
            WHERE car_number = ? AND status = 1
            ''', (car_number,))

            car_info = cursor.fetchone()
            conn.close()

            if car_info:
                return f"车辆信息：\n车牌号：{car_info[0]}\n车主：{car_info[1]}\n类型：{car_info[2]}\n租期：{car_info[3]}个月\n起始日期：{car_info[4]}\n到期日期：{car_info[5]}"
            else:
                return f"未找到车牌号为 {car_number} 的有效记录"

        except Exception as e:
            logger.error(f"[Car_Park] 查询车辆信息异常: {str(e)}", exc_info=True)
            return "查询车辆信息失败，请稍后重试"

    def _handle_event(self, msg_root):
        """处理事件消息
        :param msg_root: 消息XML根节点
        :return: 响应内容
        """
        try:
            event = msg_root.find('Event').text.lower()
            from_user = msg_root.find('FromUserName').text

            logger.info(f"[Car_Park] 收到事件: {event}, 发送者: {from_user}")

            if event == 'click':
                # 处理菜单点击事件
                event_key = msg_root.find('EventKey').text
                return self._handle_menu_click(event_key, from_user)
            elif event == 'sys_approval_change':
                # 处理审批状态变更事件
                approval_info = msg_root.find('ApprovalInfo')
                if approval_info is not None:
                    sp_no = approval_info.find('SpNo').text
                    sp_status = int(approval_info.find('SpStatus').text)

                    logger.info(
                        f"[Car_Park] _handle_event收到审批状态变更 - 单号: {sp_no}, 状态: {sp_status}")

                    # 如果审批通过，解析并保存数据
                    if sp_status == 2:  # 2表示审批通过
                        # 解析审批数据
                        car_info = parse_approval_data({"SpNo": sp_no})
                        if car_info:
                            # 保存到数据库
                            if save_car_park_info(car_info):
                                return f"_handle_event审批通过：{car_info['car_number']}"
                            else:
                                return f"审批数据保存失败：{car_info['car_number']}"
                return "收到审批状态变更"
            else:
                logger.warning(f"[Car_Park] 未处理的事件类型: {event}")
                return "收到事件"

        except Exception as e:
            logger.error(f"[Car_Park] 处理事件异常: {str(e)}", exc_info=True)
            return "处理事件失败"

    def _handle_menu_click(self, event_key, from_user):
        """处理菜单点击事件
        :param event_key: 菜单key
        :param from_user: 发送者UserID
        :return: 响应内容
        """
        try:
            if event_key == 'QUERY_CAR':
                return "请发送车牌号查询车位信息"
            elif event_key == 'PRICE_INFO':
                return "停车费用标准：\n1. 业主首车：60元/月\n2. 业主第二车：150元/月\n3. 租户或其他：200元/月"
            elif event_key == 'HELP':
                return "帮助信息：\n1. 发送车牌号查询车位信息\n2. 点击'月租车登记'进行续费\n3. 如有问题请联系物业"
            else:
                return "功能开发中，敬请期待"

        except Exception as e:
            logger.error(f"[Car_Park] 处理菜单点击异常: {str(e)}", exc_info=True)
            return "处理菜单点击失败"

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

# 创建鉴权实例
qywechat_auth = QYWeChatAuth()


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
                f"🔨系统报警\n"
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
            
            # 记录请求详情
            logger.info(f"[Car_Park] 收到API请求:")
            logger.info(f"[Car_Park] - Method: {request.method}")
            logger.info(f"[Car_Park] - Headers: {dict(request.headers)}")
            logger.info(f"[Car_Park] - API Key in headers: {api_key}")
            logger.info(f"[Car_Park] - Expected API Key: {expected_key}")
            
            if not api_key:
                logger.warning(f"[Car_Park] 请求中缺少API密钥")
                return ResponseHandler.error(
                    code=StatusCode.UNAUTHORIZED,
                    msg="缺少API密钥"
                )
            if api_key != expected_key:
                logger.warning(f"[Car_Park] API密钥不匹配: {api_key} != {expected_key}")
                return ResponseHandler.error(
                    code=StatusCode.UNAUTHORIZED,
                    msg="无效的API密钥"
                )
            logger.info(f"[Car_Park] API密钥验证成功")
        return f(*args, **kwargs)
    return decorated_function


def parse_approval_data(approval_info: dict) -> dict:
    """
    解析审批数据

    Args:
        approval_info: 审批信息，包含SpNo等信息

    Returns:
        dict: 解析后的数据字典，包含：
            - owner: 车主姓名
            - car_number: 车牌号
            - parktime: 续期时长（月）
            - addtime: 添加时间
            - status: 状态（默认pending）
            - comment: 审批结果信息，通常只有出错才会记录
            - remark: 备注信息
    """
    try:
        # 获取审批模板详情
        success, template_data = qywechat_service.get_template_detail(
            CONFIG["template_id"])
        if not success:
            logger.error("[Car_Park] 获取审批模板详情失败")
            return None

        logger.info(f"[Car_Park] 审批模板数据: {template_data}")

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

        # 遍历控件找到对应的值
        for control in template_data.get("controls", []):
            prop = control.get("property", {})
            control_id = prop.get("id")

            # 根据控件ID解析对应的值
            if control_id == APPROVAL_CONTROL_IDS["car_number"]:
                # 车牌号
                result["car_number"] = control.get("value", {}).get("text", "")

            elif control_id == APPROVAL_CONTROL_IDS["owner"]:
                # 车主姓名
                result["owner"] = control.get("value", {}).get("text", "")

            elif control_id == APPROVAL_CONTROL_IDS["park_time"]:
                # 续期时长（月）
                try:
                    result["parktime"] = int(
                        control.get("value", {}).get("number", 0))
                except (TypeError, ValueError) as e:
                    logger.error(f"[Car_Park] 解析续期时长失败: {str(e)}")
                    result["parktime"] = 0

        # 验证必要字段
        if not result["car_number"]:
            logger.error("[Car_Park] 解析失败：缺少车牌号")
            return None

        if not result["owner"]:
            logger.error("[Car_Park] 解析失败：缺少车主姓名")
            return None

        if result["parktime"] <= 0:
            logger.error("[Car_Park] 解析失败：续期时长无效")
            return None

        # 添加审批单号作为备注
        result["remark"] = f"车辆类型: {approval_info.get('car_type', 'unknown')}；审批单号: {approval_info.get('SpNo', 'unknown')}"
        logger.info(f"[Car_Park] 解析审批数据成功: {result}")
        return result

    except Exception as e:
        logger.error(f"[Car_Park] 解析审批数据失败: {str(e)}", exc_info=True)
        return None


def init_car_park_db():
    """初始化停车场数据库"""
    try:
        conn = sqlite3.connect("database/car_park.db")
        cursor = conn.cursor()

        # 创建car_park表（如果不存在）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS "car_park" (
            "id" INTEGER NOT NULL PRIMARY KEY,
            "owner" TEXT,
            "car_number" TEXT,
            "time" TEXT,
            "addtime" TEXT,
            "status" TEXT,
            "comment" TEXT
        )
        ''')

        conn.commit()
        conn.close()
        logger.info("[Car_Park] 数据库初始化成功")
        return True
    except Exception as e:
        logger.error(f"[Car_Park] 数据库初始化失败: {str(e)}", exc_info=True)
        return False


def save_car_park_info(car_info: dict) -> bool:
    """保存车辆信息到数据库
    :param car_info: 车辆信息字典
    :return: 是否保存成功
    """
    try:
        conn = sqlite3.connect("database/car_park.db")
        cursor = conn.cursor()

        # 插入新记录
        cursor.execute('''
        INSERT INTO car_park (
            owner, car_number, time, addtime, status
        ) VALUES (?, ?, ?, ?, ?)
        ''', (
            car_info["owner"],
            car_info["car_number"],
            str(car_info["parktime"]),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'pending'
        ))

        conn.commit()
        conn.close()
        logger.info(f"[Car_Park] 保存车辆信息成功: {car_info['car_number']}")
        return True

    except Exception as e:
        error_msg = f"保存车辆信息失败: {str(e)}"
        logger.error(f"[Car_Park] {error_msg}", exc_info=True)
        # 发送错误通知到企业微信
        qywechat_service.send_text_message(
            content=f"车辆信息保存失败\n车牌号：{car_info['car_number']}\n车主：{car_info['owner']}\n原因：{error_msg}",
            to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"],
            to_party=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("toparty"),
            to_tag=CONFIG["DEFAULT_MESSAGE_RECEIVER"].get("totag")
        )
        return False


def update_car_park_status(car_number: str, status: str, comment: str = None) -> bool:
    """更新车辆状态
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
        cursor.execute('SELECT owner FROM car_park WHERE car_number = ?', (car_number,))
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
        error_msg = f"更新车辆状态失败: {str(e)}"
        logger.error(f"[Car_Park] {error_msg}", exc_info=True)
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


@car_park_bp.route('/WW_verify_jaYdfovk1ueUNYpb.txt')
def qywechat_verify():
    """企业微信域名验证"""
    return 'jaYdfovk1ueUNYpb'


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
                logger.info("[Car_Park] URL验证成功")
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
            logger.info(f"[Car_Park] 收到消息推送: {xml_data}")

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


@car_park_bp.route('/approval/callback', methods=['GET', 'POST'])
def wechat_approval_callback():
    """企业微信审批回调处理"""
    try:
        # 获取通用参数
        msg_signature = request.args.get('msg_signature')
        timestamp = request.args.get('timestamp')
        nonce = request.args.get('nonce')

        if request.method == 'GET':
            # 处理URL验证请求
            echostr = request.args.get('echostr')
            logger.info(
                f"[Car_Park] 收到URL验证请求: msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")

            # 使用自带的QYWeChatAuth进行验证
            decrypted_str = qywechat_auth.verify_url(
                msg_signature, timestamp, nonce, echostr)
            if decrypted_str:
                logger.info("[Car_Park] URL验证成功")
                logger.info(f"[Car_Park] 解密后的echostr明文: {decrypted_str}")
                response = make_response(decrypted_str)
                response.headers['Content-Type'] = 'text/plain; charset=utf-8'
                response.headers['Cache-Control'] = 'no-cache'
                return response
            else:
                logger.warning("[Car_Park] URL验证失败")
                return "验证失败", 403
        else:
            # 处理POST请求
            xml_data = request.data
            logger.info(f"[Car_Park] 收到审批回调数据: {xml_data.decode('utf-8')}")

            # 解析XML数据
            xml_tree = etree.fromstring(xml_data)
            encrypt_msg = xml_tree.find("Encrypt").text

            # 使用自带的QYWeChatAuth解密消息
            decrypted_msg = qywechat_auth.decrypt_message(encrypt_msg)
            logger.info(f"[Car_Park] 解密后的审批回调消息: {decrypted_msg}")

            # 解析解密后的XML
            event_xml = etree.fromstring(decrypted_msg)

            # 获取事件类型
            if event_xml.find("Event") is not None:
                event_type = event_xml.find("Event").text

                # 处理审批状态变更事件
                if event_type == "sys_approval_change":
                    logger.info("[Car_Park] 收到审批状态变更事件")

                    # 提取审批信息
                    approval_info = {}
                    approval_info_node = event_xml.find("ApprovalInfo")
                    if approval_info_node is not None:
                        for child in approval_info_node:
                            approval_info[child.tag] = child.text

                    logger.info(f"[Car_Park] 审批信息: {approval_info}")

                    # 获取审批单号和状态
                    sp_no = approval_info.get('SpNo')
                    sp_status = int(approval_info.get('SpStatus', 0))

                    # 如果审批通过，解析并保存数据
                    if sp_status == 2:  # 2表示审批通过
                        # 解析审批数据
                        car_info = parse_approval_data(approval_info)
                        if car_info:
                            # 保存到数据库
                            if save_car_park_info(car_info):
                                logger.info(
                                    f"[Car_Park] 车辆信息保存成功: {car_info['car_number']}")
                            else:
                                logger.error(
                                    f"[Car_Park] 车辆信息保存失败: {car_info['car_number']}")

            # 返回成功响应
            return 'success'

    except Exception as e:
        logger.error(f"[Car_Park] 处理企业微信回调失败: {str(e)}", exc_info=True)
        # 即使出错也返回success，避免企业微信重试
        return 'success'


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
# 初始化数据库
# init_car_park_db()
