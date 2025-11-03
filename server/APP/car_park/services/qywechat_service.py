# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-11-01 11:00:00
# LastEditTime: 2025-11-01 17:04:34
# LastEditors: 一根鱼骨棒
# Description: 企业微信服务类
# Software: VScode
# Copyright 2025 迷舍

import os
import sys
import logging
import base64
import time
import json
import requests
from datetime import datetime, timedelta
from Crypto.Cipher import AES
import hashlib
import random
from typing import Optional, Dict, Any, Union

# 配置常量
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
    },
    "MESSAGE_RETRY_TIMES": 3,  # 消息发送重试次数
    "MESSAGE_RETRY_INTERVAL": 2,  # 重试间隔（秒）
    "ACCESS_TOKEN_CACHE_FILE": "access_token_cache.json",  # Token缓存文件
    "ACCESS_TOKEN_EXPIRE_TIME": 7200  # Token过期时间（秒）
}

# 审批模板控件ID映射
APPROVAL_CONTROL_IDS = {
    "APPLY_USER": "Text-1568693962000",  # 申请人
    "APPLY_DEPARTMENT": "Department-1568693963000",  # 所属部门
    "CAR_NUMBER": "Text-1568693964000",  # 车牌号
    "CAR_TYPE": "Select-1568693965000",  # 车辆类型
    "APPLY_REASON": "Textarea-1568693966000",  # 申请事由
    "MONTH_COUNT": "Number-1568693967000",  # 申请月数
    "START_TIME": "Date-1568693968000",  # 开始时间
    "END_TIME": "Date-1568693969000"  # 结束时间
}

# 车辆类型映射
CAR_TYPE_MAP = {
    1: "业主首车",
    2: "外部和租户月租车",
    5: "业主二车"
}

logger = logging.getLogger(__name__)

class QYWeChatService:
    """企业微信服务类"""
    
    def __init__(self):
        self.access_token = None
        self.access_token_expire_time = 0
        self.cache_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            CONFIG["ACCESS_TOKEN_CACHE_FILE"]
        )
        self._load_cached_token()
    
    def _load_cached_token(self):
        """从缓存文件加载access_token"""
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.access_token_expire_time = data.get('expire_time', 0)
        except Exception as e:
            logger.error(f"[QYWeChat] 加载缓存的access_token失败: {str(e)}")
    
    def _save_cached_token(self):
        """保存access_token到缓存文件"""
        try:
            data = {
                'access_token': self.access_token,
                'expire_time': self.access_token_expire_time
            }
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"[QYWeChat] 保存access_token到缓存失败: {str(e)}")
    
    def get_access_token(self):
        """获取企业微信access_token"""
        current_time = time.time()
        
        # 检查token是否有效
        if self.access_token and self.access_token_expire_time > current_time:
            logger.info(f"[QYWeChat] 使用缓存的access_token，剩余有效期: {int(self.access_token_expire_time - current_time)}秒")
            return self.access_token
        
        # 重新获取token
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CONFIG['corp_id']}&corpsecret={CONFIG['corp_secret']}"
            response = requests.get(url, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                self.access_token = result.get('access_token')
                self.access_token_expire_time = current_time + CONFIG['ACCESS_TOKEN_EXPIRE_TIME'] - 600  # 提前10分钟过期
                self._save_cached_token()
                logger.info(f"[QYWeChat] 成功获取新的access_token，有效期: {CONFIG['ACCESS_TOKEN_EXPIRE_TIME'] - 600}秒")
                return self.access_token
            else:
                logger.error(f"[QYWeChat] 获取access_token失败: {result}")
                return None
        except Exception as e:
            logger.error(f"[QYWeChat] 获取access_token异常: {str(e)}")
            return None
    
    def force_refresh_token(self):
        """强制刷新access_token"""
        self.access_token = None
        self.access_token_expire_time = 0
        return self.get_access_token()
    
    def get_template_detail(self, template_id):
        """获取审批模板详情"""
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/gettemplatedetail?access_token={access_token}"
            data = {
                "template_id": template_id
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"[QYWeChat] 成功获取审批模板详情: {template_id}")
                return result.get('template_info')
            else:
                logger.error(f"[QYWeChat] 获取审批模板详情失败: {result}")
                return None
        except Exception as e:
            logger.error(f"[QYWeChat] 获取审批模板详情异常: {str(e)}")
            return None
    
    def decrypt_message(self, encrypted_msg: str, msg_signature: str, timestamp: str, nonce: str) -> Optional[str]:
        """解密企业微信消息"""
        try:
            # 验证签名
            if not self.verify_url(msg_signature, timestamp, nonce, encrypted_msg):
                logger.error("[QYWeChat] 消息签名验证失败")
                return None
            
            # Base64解码
            aes_key = base64.b64decode(CONFIG["encoding_aes_key"] + '=')
            cryptor = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
            
            # 解密
            plain_text = cryptor.decrypt(base64.b64decode(encrypted_msg))
            
            # 去除PKCS7填充
            pad = plain_text[-1]
            plain_text = plain_text[:-pad]
            
            # 解析消息内容
            xml_len = int(plain_text[16:20].decode())
            xml_content = plain_text[20:20 + xml_len].decode()
            
            return xml_content
        except Exception as e:
            logger.error(f"[QYWeChat] 解密消息失败: {str(e)}")
            return None
    
    def encrypt_message(self, reply_msg: str, timestamp: str, nonce: str) -> Optional[Dict[str, str]]:
        """加密企业微信回复消息"""
        try:
            # 生成随机字符串
            rand_str = ''.join([str(random.randint(0, 9)) for _ in range(16)])
            
            # 计算消息长度
            msg_len = len(reply_msg)
            len_bytes = msg_len.to_bytes(4, 'big')
            
            # 构造要加密的消息
            content = rand_str.encode() + len_bytes + reply_msg.encode() + CONFIG["corp_id"].encode()
            
            # PKCS7填充
            pad_len = 32 - (len(content) % 32)
            content += bytes([pad_len]) * pad_len
            
            # AES加密
            aes_key = base64.b64decode(CONFIG["encoding_aes_key"] + '=')
            cryptor = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
            encrypted = cryptor.encrypt(content)
            
            # Base64编码
            encrypted_base64 = base64.b64encode(encrypted).decode()
            
            # 生成签名
            signature = self._generate_signature(timestamp, nonce, encrypted_base64)
            
            return {
                "msg_signature": signature,
                "timestamp": timestamp,
                "nonce": nonce,
                "encrypt": encrypted_base64
            }
        except Exception as e:
            logger.error(f"[QYWeChat] 加密消息失败: {str(e)}")
            return None
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> bool:
        """验证企业微信URL"""
        try:
            signature = self._generate_signature(timestamp, nonce, echostr)
            return signature == msg_signature
        except Exception as e:
            logger.error(f"[QYWeChat] URL验证失败: {str(e)}")
            return False
    
    def _generate_signature(self, timestamp: str, nonce: str, encrypted: str) -> str:
        """生成签名"""
        params = [CONFIG["token"], timestamp, nonce, encrypted]
        params.sort()
        string = ''.join(params)
        hash_obj = hashlib.sha1(string.encode())
        return hash_obj.hexdigest()
    
    def send_text_message(self, content: str, to_user: str = None, to_party: str = None, to_tag: str = None) -> bool:
        """发送文本消息"""
        access_token = self.get_access_token()
        if not access_token:
            return False
        
        if not any([to_user, to_party, to_tag]):
            to_user = CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        data = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": "text",
            "agentid": CONFIG["agent_id"],
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        # 移除None值
        data = {k: v for k, v in data.items() if v is not None}
        
        # 重试机制
        for retry in range(CONFIG["MESSAGE_RETRY_TIMES"]):
            try:
                response = requests.post(url, json=data, timeout=10)
                result = response.json()
                
                if result.get('errcode') == 0:
                    logger.info(f"[QYWeChat] 消息发送成功，接收者: {to_user}")
                    return True
                else:
                    logger.error(f"[QYWeChat] 消息发送失败 (尝试 {retry + 1}/{CONFIG['MESSAGE_RETRY_TIMES']}): {result}")
                    # 如果是token过期，强制刷新
                    if result.get('errcode') == 40014:
                        self.force_refresh_token()
            except Exception as e:
                logger.error(f"[QYWeChat] 消息发送异常 (尝试 {retry + 1}/{CONFIG['MESSAGE_RETRY_TIMES']}): {str(e)}")
            
            if retry < CONFIG["MESSAGE_RETRY_TIMES"] - 1:
                time.sleep(CONFIG["MESSAGE_RETRY_INTERVAL"])
        
        return False
    
    def _handle_text_message(self, content: str, from_user: str) -> Optional[str]:
        """处理文本消息"""
        content = content.strip()
        
        # 命令处理逻辑
        if content.startswith("修改车牌"):
            return self._handle_modify_plate(content, from_user)
        elif content.startswith("审批"):
            return self._handle_approval(content, from_user)
        elif content.startswith("删除"):
            return self._handle_delete(content, from_user)
        elif content.startswith("绑定"):
            return self._add_wechat_id(content, from_user, 'bind')
        elif content.startswith("解绑"):
            return self._add_wechat_id(content, from_user, 'unbind')
        elif content == "记录查询":
            return self._get_recent_records(from_user)
        else:
            return self._query_car_info(content, from_user)
    
    def _query_car_info(self, query: str, from_user: str) -> str:
        """查询车辆信息"""
        # 这个方法将在views.py中实现，因为需要数据库操作
        return "查询功能暂未实现，请稍后再试"
    
    def _handle_modify_plate(self, content: str, from_user: str) -> str:
        """处理修改车牌"""
        try:
            # 解析输入格式：修改车牌 原车牌号 新车牌号
            parts = content.split(" ")
            if len(parts) != 3:
                return "输入格式错误，请使用：修改车牌 原车牌号 新车牌号"
            
            old_plate = parts[1]
            new_plate = parts[2]
            
            # 这里将在views.py中实现数据库操作
            return f"收到修改车牌请求：{old_plate} -> {new_plate}，请等待审核"
        except Exception as e:
            logger.error(f"[QYWeChat] 处理修改车牌失败: {str(e)}")
            return "处理失败，请稍后再试"
    
    def _add_wechat_id(self, content: str, from_user: str, action: str) -> str:
        """处理微信ID绑定/解绑"""
        try:
            # 解析输入格式：绑定/解绑 姓名 电话
            parts = content.split(" ")
            if len(parts) != 3:
                return f"输入格式错误，请使用：{action} 姓名 电话"
            
            name = parts[1]
            phone = parts[2]
            
            # 这里将在views.py中实现数据库操作
            return f"{action}请求已提交，请等待验证"
        except Exception as e:
            logger.error(f"[QYWeChat] 处理{action}失败: {str(e)}")
            return "处理失败，请稍后再试"

    def handle_message(self, xml_data: bytes, msg_signature: str, timestamp: str, nonce: str) -> str:
        """
        处理企业微信加密消息
        :param xml_data: 原始XML数据
        :param msg_signature: 消息签名
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: 响应XML
        """
        try:
            # 解析XML数据
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_data)
            encrypted_msg = root.find('Encrypt').text
            
            # 解密消息
            decrypted_xml = self.decrypt_message(encrypted_msg, msg_signature, timestamp, nonce)
            if not decrypted_xml:
                logger.error("[QYWeChat] 消息解密失败")
                return '<xml><ToUserName><![CDATA[]]></ToUserName><FromUserName><![CDATA[]]></FromUserName><CreateTime>0</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[解密失败]]></Content></xml>'
            
            # 解析解密后的XML
            decrypted_root = ET.fromstring(decrypted_xml)
            msg_type = decrypted_root.find('MsgType').text
            from_user = decrypted_root.find('FromUserName').text
            
            # 处理不同类型的消息
            response_content = ""
            if msg_type == 'text':
                # 处理文本消息
                content = decrypted_root.find('Content').text
                response_content = self._handle_text_message(content, from_user)
            elif msg_type == 'event':
                # 处理事件消息
                event = decrypted_root.find('Event').text
                if event == 'subscribe':
                    response_content = "欢迎使用停车场管理系统！"
                elif event == 'CLICK':
                    # 处理菜单点击事件
                    event_key = decrypted_root.find('EventKey').text
                    if event_key == 'STATISTICS':
                        response_content = "统计功能暂未实现"
            
            # 构建回复XML
            if response_content:
                to_user = decrypted_root.find('FromUserName').text
                from_user = decrypted_root.find('ToUserName').text
                reply_xml = f"""
                <xml>
                    <ToUserName><![CDATA[{to_user}]]></ToUserName>
                    <FromUserName><![CDATA[{from_user}]]></FromUserName>
                    <CreateTime>{int(time.time())}</CreateTime>
                    <MsgType><![CDATA[text]]></MsgType>
                    <Content><![CDATA[{response_content}]]></Content>
                </xml>
                """
                
                # 加密回复
                encrypted_data = self.encrypt_message(reply_xml, timestamp, nonce)
                if encrypted_data:
                    # 构建加密响应XML
                    encrypt_reply = f"""
                    <xml>
                        <Encrypt><![CDATA[{encrypted_data['encrypt']}]]></Encrypt>
                        <MsgSignature><![CDATA[{encrypted_data['msg_signature']}]]></MsgSignature>
                        <TimeStamp>{encrypted_data['timestamp']}</TimeStamp>
                        <Nonce><![CDATA[{encrypted_data['nonce']}]]></Nonce>
                    </xml>
                    """
                    return encrypt_reply
            
            # 返回空响应
            return '<xml><ToUserName><![CDATA[]]></ToUserName><FromUserName><![CDATA[]]></FromUserName><CreateTime>0</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[]]></Content></xml>'
        except Exception as e:
            logger.error(f"[QYWeChat] 处理消息失败: {str(e)}", exc_info=True)
            return '<xml><ToUserName><![CDATA[]]></ToUserName><FromUserName><![CDATA[]]></FromUserName><CreateTime>0</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[处理失败]]></Content></xml>'

# 懒加载企业微信服务实例
_qywechat_service_instance = None

def get_qywechat_service():
    """获取企业微信服务实例（懒加载模式）"""
    global _qywechat_service_instance
    if _qywechat_service_instance is None:
        _qywechat_service_instance = QYWeChatService()
    return _qywechat_service_instance

# 不自动初始化，只在实际使用时通过get_qywechat_service()获取实例