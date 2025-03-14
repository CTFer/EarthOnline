# -*- coding: utf-8 -*-
import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from config.private import QYWECHAT_CORP_ID, QYWECHAT_AGENT_ID, QYWECHAT_CORP_SECRET
from Crypto.Cipher import AES
import base64
import json
import random
import string
import struct
import requests
import threading
from utils.response_handler import ResponseHandler, StatusCode
import os
import sqlite3

logger = logging.getLogger(__name__)

class AccessToken:
    """访问令牌类，用于存储和管理access_token"""
    def __init__(self):
        self.access_token = None
        self.expires_time = 0  # 过期时间戳
        self.lock = threading.Lock()  # 用于线程安全

class QYWeChatService:
    """企业微信服务类"""
    
    def __init__(self):
        """初始化企业微信服务"""
        self.corp_id = QYWECHAT_CORP_ID
        self.agent_id = QYWECHAT_AGENT_ID
        self.corp_secret = QYWECHAT_CORP_SECRET
        self.token = "xCmY3kAhUPNFjQjwUboMvii2oJxCNg6K"  # 用于验证URL
        self.encoding_aes_key = "c5GBoCr1nkrowd1AlaqjpUNQL6dcg9ervFSitvToarB"  # 消息加解密密钥
        self._access_token = AccessToken()  # 用于存储access_token
        
    def get_access_token(self):
        """
        获取access_token
        如果access_token已过期，会自动刷新
        :return: access_token
        """
        with self._access_token.lock:
            now = int(time.time())
            
            # 如果access_token还有效且距离过期还有超过5分钟，直接返回
            if (self._access_token.access_token and 
                self._access_token.expires_time - now > 300):  # 留5分钟余量
                return self._access_token.access_token
                
            # 需要刷新access_token
            try:
                url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
                params = {
                    "corpid": self.corp_id,
                    "corpsecret": self.corp_secret
                }
                
                logger.info("[QYWeChat] 开始获取access_token")
                response = requests.get(url, params=params)
                result = response.json()
                
                if "access_token" in result:
                    self._access_token.access_token = result["access_token"]
                    self._access_token.expires_time = now + result["expires_in"]
                    logger.info("[QYWeChat] 成功获取access_token")
                    return self._access_token.access_token
                else:
                    error_code = result.get("errcode", "未知")
                    error_msg = result.get("errmsg", "未知错误")
                    logger.error(f"[QYWeChat] 获取access_token失败: [{error_code}] {error_msg}")
                    raise Exception(f"获取access_token失败: [{error_code}] {error_msg}")
                    
            except Exception as e:
                logger.error(f"[QYWeChat] 获取access_token异常: {str(e)}", exc_info=True)
                raise
                
    def refresh_access_token(self):
        """
        强制刷新access_token
        :return: 新的access_token
        """
        with self._access_token.lock:
            # 清空当前的access_token
            self._access_token.access_token = None
            self._access_token.expires_time = 0
            
            # 重新获取
            return self.get_access_token()

    def send_text_message(self, content, to_user=None, to_party=None, to_tag=None, safe=0):
        """
        发送文本消息
        :param content: 消息内容
        :param to_user: 指定接收消息的成员，成员ID列表（多个接收者用'|'分隔）
        :param to_party: 指定接收消息的部门，部门ID列表（多个接收者用'|'分隔）
        :param to_tag: 指定接收消息的标签，标签ID列表（多个接收者用'|'分隔）
        :param safe: 表示是否是保密消息，0表示可对外分享，1表示不能分享且内容显示水印
        :return: 发送结果
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            data = {
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {
                    "content": content
                },
                "safe": safe
            }
            
            # 设置接收者
            if to_user:
                data["touser"] = to_user
            if to_party:
                data["toparty"] = to_party
            if to_tag:
                data["totag"] = to_tag
                
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 消息发送成功")
                return True, "消息发送成功"
            else:
                error_msg = f"消息发送失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 发送消息异常: {str(e)}", exc_info=True)
            return False, f"发送消息异常: {str(e)}"

    def create_menu(self, menu_data):
        """
        创建应用菜单
        :param menu_data: 菜单数据，格式参考企业微信文档
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}&agentid={self.agent_id}"
            
            response = requests.post(url, json=menu_data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 应用菜单创建成功")
                return True, "应用菜单创建成功"
            else:
                error_msg = f"应用菜单创建失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 创建应用菜单异常: {str(e)}", exc_info=True)
            return False, f"创建应用菜单异常: {str(e)}"

    def get_menu(self):
        """
        获取应用菜单
        :return: 菜单数据
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/menu/get?access_token={access_token}&agentid={self.agent_id}"
            
            response = requests.get(url)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 获取应用菜单成功")
                return True, result.get("button", [])
            else:
                error_msg = f"获取应用菜单失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取应用菜单异常: {str(e)}", exc_info=True)
            return False, f"获取应用菜单异常: {str(e)}"

    def delete_menu(self):
        """
        删除应用菜单
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/menu/delete?access_token={access_token}&agentid={self.agent_id}"
            
            response = requests.get(url)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 应用菜单删除成功")
                return True, "应用菜单删除成功"
            else:
                error_msg = f"应用菜单删除失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 删除应用菜单异常: {str(e)}", exc_info=True)
            return False, f"删除应用菜单异常: {str(e)}"

    def _create_cipher(self):
        """创建新的cipher实例"""
        key = base64.b64decode(self.encoding_aes_key + '=')
        return AES.new(key, AES.MODE_CBC, iv=key[:16])

    def verify_url(self, msg_signature, timestamp, nonce, echostr):
        """
        验证URL有效性
        :param msg_signature: 企业微信加密签名
        :param timestamp: 时间戳
        :param nonce: 随机数
        :param echostr: 加密的随机字符串
        :return: 解密后的echostr或None
        """
        try:
            # 1. 将token、timestamp、nonce、msg_encrypt按字典序排序
            signature_list = [self.token, timestamp, nonce, echostr]
            signature_list.sort()
            
            # 2. 将四个参数拼接成一个字符串进行sha1计算
            temp_str = ''.join(signature_list)
            sign = hashlib.sha1(temp_str.encode('utf-8')).hexdigest()
            
            logger.debug(f"[QYWeChat] URL验证 - 计算签名: {sign}")
            logger.debug(f"[QYWeChat] URL验证 - 接收签名: {msg_signature}")
            
            # 3. 对比签名
            if sign == msg_signature:
                # 4. 解密echostr
                decrypted_str = self._decrypt_message(echostr)
                return decrypted_str
            else:
                logger.warning("[QYWeChat] URL验证失败 - 签名不匹配")
                return None
                
        except Exception as e:
            logger.error(f"[QYWeChat] URL验证异常: {str(e)}", exc_info=True)
            return None

    def _decrypt_message(self, encrypted_msg):
        """
        解密消息
        :param encrypted_msg: 加密后的消息
        :return: 解密后的消息
        """
        try:
            # Base64解码
            encrypted_data = base64.b64decode(encrypted_msg)
            
            # 创建解密器
            cipher = self._create_cipher()
            
            # AES解密
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # 去除补位
            pad = decrypted_data[-1]
            content = decrypted_data[:-pad]
            
            # 获取消息长度
            msg_len = struct.unpack('!I', content[16:20])[0]
            
            # 获取消息内容
            xml_content = content[20:20+msg_len]
            
            # 获取企业ID
            received_corp_id = content[20+msg_len:].decode('utf-8')
            
            # 验证企业ID
            if received_corp_id != self.corp_id:
                raise ValueError("企业ID不匹配")
                
            return xml_content.decode('utf-8')
            
        except Exception as e:
            logger.error(f"[QYWeChat] 消息解密失败: {str(e)}", exc_info=True)
            raise

    def _encrypt_message(self, reply_msg):
        """
        加密消息
        :param reply_msg: 回复的消息
        :return: 加密后的消息
        """
        try:
            # 生成16位随机字符串
            random_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            
            # 生成密文
            text = random_str.encode('utf-8') + struct.pack('!I', len(reply_msg.encode('utf-8'))) + \
                   reply_msg.encode('utf-8') + self.corp_id.encode('utf-8')
            
            # 补位
            pad_num = 32 - (len(text) % 32)
            text += bytes([pad_num] * pad_num)
            
            # 创建加密器
            cipher = self._create_cipher()
            
            # AES加密
            encrypted_text = cipher.encrypt(text)
            
            # Base64编码
            return base64.b64encode(encrypted_text).decode('utf-8')
            
        except Exception as e:
            logger.error(f"[QYWeChat] 消息加密失败: {str(e)}", exc_info=True)
            raise

    def _get_encrypted_response(self, reply_msg, timestamp, nonce):
        """
        获取加密后的响应消息
        :param reply_msg: 回复的消息
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: 加密后的XML
        """
        try:
            # 加密消息
            encrypt = self._encrypt_message(reply_msg)
            
            # 生成签名
            signature_list = [self.token, timestamp, nonce, encrypt]
            signature_list.sort()
            signature = hashlib.sha1(''.join(signature_list).encode('utf-8')).hexdigest()
            
            # 生成加密后的XML
            return f"""<xml>
                <Encrypt><![CDATA[{encrypt}]]></Encrypt>
                <MsgSignature><![CDATA[{signature}]]></MsgSignature>
                <TimeStamp>{timestamp}</TimeStamp>
                <Nonce><![CDATA[{nonce}]]></Nonce>
            </xml>"""
            
        except Exception as e:
            logger.error(f"[QYWeChat] 生成加密响应失败: {str(e)}", exc_info=True)
            raise

    def handle_message(self, xml_data, msg_signature=None, timestamp=None, nonce=None):
        """
        处理企业微信消息和事件
        :param xml_data: 原始XML消息数据
        :param msg_signature: 消息签名
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: 响应消息
        """
        try:
            xml_str = xml_data.decode('utf-8')
            logger.info(f"[QYWeChat] 收到原始消息: {xml_str}")
            
            # 解析XML
            root = ET.fromstring(xml_str)
            
            # 获取加密消息
            encrypted_msg = root.find('Encrypt').text
            logger.debug(f"[QYWeChat] 收到加密消息: {encrypted_msg}")
            
            # 验证消息签名
            signature_list = [self.token, timestamp, nonce, encrypted_msg]
            signature_list.sort()
            calc_signature = hashlib.sha1(''.join(signature_list).encode('utf-8')).hexdigest()
            
            if calc_signature != msg_signature:
                logger.warning("[QYWeChat] 消息签名验证失败")
                return 'success'  # 即使验证失败也返回success，避免企业微信重试
            
            # 解密消息
            decrypted_xml = self._decrypt_message(encrypted_msg)
            logger.debug(f"[QYWeChat] 解密后的消息: {decrypted_xml}")
            
            # 解析解密后的XML
            msg_root = ET.fromstring(decrypted_xml)
            
            # 获取消息基本信息
            msg_type = msg_root.find('MsgType').text
            from_user = msg_root.find('FromUserName').text
            to_user = msg_root.find('ToUserName').text
            create_time = msg_root.find('CreateTime').text
            agent_id = msg_root.find('AgentID').text if msg_root.find('AgentID') is not None else None
            
            logger.info(f"[QYWeChat] 消息类型: {msg_type}")
            logger.info(f"[QYWeChat] 发送者UserID: {from_user}")
            logger.info(f"[QYWeChat] 接收者: {to_user}")
            logger.info(f"[QYWeChat] 消息创建时间: {create_time}")
            logger.info(f"[QYWeChat] 应用ID: {agent_id}")
            
            # 根据消息类型处理
            if msg_type == 'text':
                # 处理文本消息
                content = msg_root.find('Content').text
                msg_id = msg_root.find('MsgId').text
                logger.info(f"[QYWeChat] 收到文本消息 - 内容: {content}, 消息ID: {msg_id}")
                response_content = self._handle_text_message(content)
                
            elif msg_type == 'image':
                # 处理图片消息
                pic_url = msg_root.find('PicUrl').text
                media_id = msg_root.find('MediaId').text
                msg_id = msg_root.find('MsgId').text
                logger.info(f"[QYWeChat] 收到图片消息 - MediaID: {media_id}, 消息ID: {msg_id}")
                response_content = "图片已收到"
                
            elif msg_type == 'voice':
                # 处理语音消息
                media_id = msg_root.find('MediaId').text
                format_type = msg_root.find('Format').text
                msg_id = msg_root.find('MsgId').text
                logger.info(f"[QYWeChat] 收到语音消息 - 格式: {format_type}, MediaID: {media_id}")
                response_content = "语音已收到"
                
            elif msg_type == 'video':
                # 处理视频消息
                media_id = msg_root.find('MediaId').text
                thumb_media_id = msg_root.find('ThumbMediaId').text
                msg_id = msg_root.find('MsgId').text
                logger.info(f"[QYWeChat] 收到视频消息 - MediaID: {media_id}, 视频封面MediaID: {thumb_media_id}")
                response_content = "视频已收到"
                
            elif msg_type == 'location':
                # 处理位置消息
                location_x = msg_root.find('Location_X').text
                location_y = msg_root.find('Location_Y').text
                scale = msg_root.find('Scale').text
                label = msg_root.find('Label').text
                msg_id = msg_root.find('MsgId').text
                logger.info(f"[QYWeChat] 收到位置消息 - 位置: {label}, 经度: {location_y}, 纬度: {location_x}")
                response_content = f"位置已收到：{label}"
                
            elif msg_type == 'link':
                # 处理链接消息
                title = msg_root.find('Title').text
                description = msg_root.find('Description').text
                url = msg_root.find('Url').text
                msg_id = msg_root.find('MsgId').text
                logger.info(f"[QYWeChat] 收到链接消息 - 标题: {title}, URL: {url}")
                response_content = f"链接已收到：{title}"
                
            elif msg_type == 'event':
                # 处理事件消息
                response_content = self._handle_event(msg_root, from_user, to_user)
            else:
                logger.warning(f"[QYWeChat] 未处理的消息类型: {msg_type}")
                return 'success'
            
            # 构建响应XML
            current_timestamp = str(int(time.time()))
            reply_msg = f"""<xml>
                <ToUserName><![CDATA[{from_user}]]></ToUserName>
                <FromUserName><![CDATA[{to_user}]]></FromUserName>
                <CreateTime>{current_timestamp}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{response_content}]]></Content>
                <AgentID>{agent_id}</AgentID>
            </xml>"""
            
            # 加密响应消息
            encrypted_response = self._get_encrypted_response(reply_msg, timestamp, nonce)
            logger.debug(f"[QYWeChat] 返回加密消息: {encrypted_response}")
            
            return encrypted_response
            
        except Exception as e:
            logger.error(f"[QYWeChat] 处理消息失败: {str(e)}", exc_info=True)
            return 'success'  # 即使处理失败也返回success，避免企业微信重试

    def _handle_text_message(self, content):
        """
        处理文本消息
        :param content: 消息内容
        :return: 响应内容
        """
        try:
            # 这里可以根据内容关键词进行自定义回复
            if '你好' in content or 'hello' in content.lower():
                return "你好！很高兴为您服务。"
            elif '帮助' in content or 'help' in content.lower():
                return "您可以：\n1. 发送文本消息\n2. 发送图片或文件\n3. 使用任务卡片功能"
            else:
                return f"您发送的消息是：{content}"
                
        except Exception as e:
            logger.error(f"[QYWeChat] 处理文本消息异常: {str(e)}", exc_info=True)
            return "抱歉，处理消息时出现错误，请稍后再试"

    def _handle_event(self, root, from_user, to_user):
        """
        处理事件消息
        :param root: XML根节点
        :param from_user: 发送者UserID
        :param to_user: 接收者
        :return: 响应消息
        """
        try:
            event = root.find('Event').text.lower()
            logger.info(f"[QYWeChat] 收到事件: {event}")
            
            if event == 'location_select':
                # 处理弹出地理位置选择器的事件
                location = root.find('SendLocationInfo')
                if location is not None:
                    location_x = location.find('Location_X').text  # 纬度
                    location_y = location.find('Location_Y').text  # 经度
                    scale = location.find('Scale').text  # 精度
                    label = location.find('Label').text  # 位置名称
                    poiname = location.find('Poiname').text  # POI名称
                    
                    logger.info(f"[QYWeChat] 用户选择位置 - 位置: {label}, 经度: {location_y}, 纬度: {location_x}, 精度: {scale}, POI: {poiname}")
                    
                    # 这里可以添加位置处理逻辑
                    
            elif event == 'template_card_event':
                # 处理模板卡片事件
                card_type = root.find('CardType').text
                task_id = root.find('TaskId').text
                response_code = root.find('ResponseCode').text
                
                logger.info(f"[QYWeChat] 模板卡片事件 - 类型: {card_type}, 任务ID: {task_id}, 响应码: {response_code}")
                
                # 处理不同类型的模板卡片
                if card_type == 'text_notice':
                    # 处理文本通知类型卡片
                    pass
                elif card_type == 'button_interaction':
                    # 处理按钮交互型卡片
                    pass
                elif card_type == 'vote_interaction':
                    # 处理投票选择型卡片
                    pass
                
                
            elif event == 'sys_photo':
                # 处理系统拍照发图事件
                count = root.find('Count').text
                pic_md5_sum = root.find('PicMd5Sum').text
                logger.info(f"[QYWeChat] 系统拍照发图 - 数量: {count}, 图片MD5: {pic_md5_sum}")
            elif event == 'click':
                event_key = root.find('EventKey').text
                wechat_userid = root.find('FromUserName').text
                
                # 获取玩家信息
                player_info = self.get_player_by_wechat_userid(wechat_userid)
                if player_info.get('code') != 0:
                    return self.reply_text(from_user, "未找到玩家信息")
                    
                player_id = player_info['data']['id']
                task_service = TaskService()
                
                if event_key == 'PLAYER_TASK':
                    # 获取玩家当前任务列表
                    current_tasks = task_service.get_current_tasks(player_id)
                    if current_tasks.get('code') != 0:
                        return self.reply_text(from_user, "获取任务列表失败")
                        
                    tasks = current_tasks.get('data', [])
                    if not tasks:
                        return self.reply_text(from_user, "当前没有进行中的任务")
                        
                    # 发送任务卡片消息
                    for task in tasks:
                        self.send_task_card_message(
                            to_user=wechat_userid,
                            task_data=task,
                            card_type='current_task'
                        )
                        
                elif event_key == 'AVAIL_TASK':
                    # 获取可用任务列表
                    available_tasks = task_service.get_available_tasks(player_id)
                    if available_tasks.get('code') != 0:
                        return self.reply_text(from_user, "获取可用任务失败")
                        
                    tasks = available_tasks.get('data', [])
                    if not tasks:
                        return self.reply_text(from_user, "当前没有可用的任务")
                        
                    # 发送任务卡片消息
                    for task in tasks:
                        self.send_task_card_message(
                            to_user=wechat_userid,
                            task_data=task,
                            card_type='available_task'
                        )
                        
            return 'success'
            
        except Exception as e:
            logger.error(f"[QYWeChat] 处理事件失败: {str(e)}", exc_info=True)
            return 'success'

    def update_template_card(self, response_code, template_card):
        """
        更新模板卡片消息
        :param response_code: 更新模板卡片的response_code
        :param template_card: 模板卡片数据
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/update_template_card?access_token={access_token}"
            
            data = {
                "response_code": response_code,
                "template_card": template_card
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 模板卡片更新成功")
                return True, "模板卡片更新成功"
            else:
                error_msg = f"模板卡片更新失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 更新模板卡片异常: {str(e)}", exc_info=True)
            return False, f"更新模板卡片异常: {str(e)}"

    def send_task_card_message(self, to_user=None, to_party=None, to_tag=None, task_data=None, card_type='task_info'):
        """发送企业微信任务卡片消息"""
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            # 构建任务信息卡片
            data = {
                "touser": to_user,
                "toparty": to_party,
                "totag": to_tag,
                "msgtype": "template_card",
                "agentid": self.agent_id,
                "template_card": {
                    "card_type": "button_interaction",
                    "source": {
                        "icon_url": "https://example.com/icon.png",
                        "desc": "任务系统"
                    },
                    "main_title": {
                        "title": task_data['name'],
                        "desc": "任务详情"
                    },
                    "quote_area": {
                        "type": 1,
                        "quote_text": task_data['description']
                    },
                    "horizontal_content_list": [
                        {
                            "keyname": "任务类型",
                            "value": task_data['task_type'],
                            "type": 1
                        },
                        {
                            "keyname": "体力消耗",
                            "value": str(task_data['stamina_cost']),
                            "type": 1
                        },
                        {
                            "keyname": "时间限制",
                            "value": f"{task_data['limit_time']}小时" if task_data['limit_time'] else "无限制",
                            "type": 1
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": f"https://example.com/task/{task_data['id']}"
                    },
                    "button_list": [
                        {
                            "text": "接受任务",
                            "style": 1,
                            "key": f"accept_task_{task_data['id']}"
                        } if card_type == 'available_task' else {
                            "text": "查看详情",
                            "style": 2,
                            "key": f"view_task_{task_data['id']}"
                        }
                    ]
                }
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 模板卡片消息发送成功")
                return True, "消息发送成功"
            else:
                error_msg = f"消息发送失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f"[QYWeChat] 发送任务卡片消息失败: {str(e)}", exc_info=True)
            return False, f"发送任务卡片消息失败: {str(e)}"

    def upload_file_to_wecom(self, file_path, file_name=None):
        """
        上传文件到企业微信微盘
        :param file_path: 文件本地路径
        :param file_name: 文件名称（可选）
        :return: (success, file_id或错误信息)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_upload?access_token={access_token}"
            
            # 准备文件数据
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name or os.path.basename(file_path), f, 'application/octet-stream')
                }
                
                logger.info(f"[QYWeChat] 开始上传文件: {file_name or os.path.basename(file_path)}")
                response = requests.post(url, files=files)
                result = response.json()
                
                if result.get("errcode") == 0:
                    file_id = result.get("file_id")
                    logger.info(f"[QYWeChat] 文件上传成功，file_id: {file_id}")
                    return True, file_id
                else:
                    error_msg = f"文件上传失败: [{result.get('errcode')}] {result.get('errmsg')}"
                    logger.error(f"[QYWeChat] {error_msg}")
                    return False, error_msg
                    
        except Exception as e:
            logger.error(f"[QYWeChat] 上传文件异常: {str(e)}", exc_info=True)
            return False, f"上传文件异常: {str(e)}"

    def download_file_from_wecom(self, file_id, save_path):
        """
        从企业微信微盘下载文件
        :param file_id: 文件ID
        :param save_path: 保存路径
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_download?access_token={access_token}"
            
            data = {
                "file_id": file_id
            }
            
            logger.info(f"[QYWeChat] 开始下载文件: {file_id}")
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"[QYWeChat] 文件下载成功，保存至: {save_path}")
                return True, "文件下载成功"
            else:
                result = response.json()
                error_msg = f"文件下载失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 下载文件异常: {str(e)}", exc_info=True)
            return False, f"下载文件异常: {str(e)}"

    def create_wecom_file(self, file_id, file_name, parent_id=""):
        """
        在企业微信微盘创建文件
        :param file_id: 文件ID（通过上传接口获取）
        :param file_name: 文件名称
        :param parent_id: 父目录ID（可选）
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_create?access_token={access_token}"
            
            data = {
                "file_id": file_id,
                "file_name": file_name,
                "parent_id": parent_id
            }
            
            logger.info(f"[QYWeChat] 开始创建文件: {file_name}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件创建成功")
                return True, "文件创建成功"
            else:
                error_msg = f"文件创建失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 创建文件异常: {str(e)}", exc_info=True)
            return False, f"创建文件异常: {str(e)}"

    def delete_wecom_file(self, file_id):
        """
        删除企业微信微盘文件
        :param file_id: 文件ID
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_delete?access_token={access_token}"
            
            data = {
                "file_id": file_id
            }
            
            logger.info(f"[QYWeChat] 开始删除文件: {file_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件删除成功")
                return True, "文件删除成功"
            else:
                error_msg = f"文件删除失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 删除文件异常: {str(e)}", exc_info=True)
            return False, f"删除文件异常: {str(e)}"

    def rename_wecom_file(self, file_id, new_name):
        """
        重命名企业微信微盘文件
        :param file_id: 文件ID
        :param new_name: 新文件名
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_rename?access_token={access_token}"
            
            data = {
                "file_id": file_id,
                "new_name": new_name
            }
            
            logger.info(f"[QYWeChat] 开始重命名文件: {file_id} -> {new_name}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件重命名成功")
                return True, "文件重命名成功"
            else:
                error_msg = f"文件重命名失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 重命名文件异常: {str(e)}", exc_info=True)
            return False, f"重命名文件异常: {str(e)}"

    def move_wecom_file(self, file_id, parent_id="", replace=False):
        """
        移动企业微信微盘文件
        :param file_id: 文件ID
        :param parent_id: 目标目录ID
        :param replace: 是否覆盖同名文件
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_move?access_token={access_token}"
            
            data = {
                "file_id": file_id,
                "parent_id": parent_id,
                "replace": replace
            }
            
            logger.info(f"[QYWeChat] 开始移动文件: {file_id} -> {parent_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件移动成功")
                return True, "文件移动成功"
            else:
                error_msg = f"文件移动失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 移动文件异常: {str(e)}", exc_info=True)
            return False, f"移动文件异常: {str(e)}"

    def list_wecom_files(self, parent_id="", sort_type=0, start=0, limit=50):
        """
        获取企业微信微盘文件列表
        :param parent_id: 父目录ID
        :param sort_type: 排序类型（0:名字升序 1:名字降序 2:大小升序 3:大小降序 4:修改时间升序 5:修改时间降序）
        :param start: 起始位置
        :param limit: 拉取数量
        :return: (success, file_list或错误信息)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_list?access_token={access_token}"
            
            data = {
                "parent_id": parent_id,
                "sort_type": sort_type,
                "start": start,
                "limit": limit
            }
            
            logger.info(f"[QYWeChat] 开始获取文件列表: parent_id={parent_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                file_list = result.get("file_list", [])
                logger.info(f"[QYWeChat] 获取文件列表成功，共{len(file_list)}个文件")
                return True, file_list
            else:
                error_msg = f"获取文件列表失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取文件列表异常: {str(e)}", exc_info=True)
            return False, f"获取文件列表异常: {str(e)}"

    def get_player_by_wechat_userid(self, wechat_userid):
        """根据企业微信用户ID获取玩家信息"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM player_data WHERE wechat_userid = ?', (wechat_userid,))
            player = cursor.fetchone()
            if player:
                return ResponseHandler.success(data=dict(player), msg="获取玩家信息成功")
            else:
                return ResponseHandler.error(code=StatusCode.PLAYER_NOT_FOUND, msg="玩家不存在")
        except sqlite3.Error as e:
            logger.error(f"获取玩家信息失败: {str(e)}")
            return ResponseHandler.error(code=StatusCode.SERVER_ERROR, msg="获取玩家信息失败")
        finally:
            conn.close()

# 创建服务实例
qywechat_service = QYWeChatService()
