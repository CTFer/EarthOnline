# -*- coding: utf-8 -*-
import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from config.private import WECHAT_TOKEN, WECHAT_ENCODING_AES_KEY, WECHAT_APP_ID, WECHAT_APP_SECRET
from Crypto.Cipher import AES
import base64
import json
import random
import string
import struct
import requests
import threading
from utils.response_handler import ResponseHandler, StatusCode

logger = logging.getLogger(__name__)

class AccessToken:
    """访问令牌类，用于存储和管理access_token"""
    def __init__(self):
        self.access_token = None
        self.expires_time = 0  # 过期时间戳
        self.lock = threading.Lock()  # 用于线程安全

class WeChatService:
    """微信公众号服务类"""
    
    def __init__(self):
        """初始化微信服务"""
        self.token = WECHAT_TOKEN
        self.encoding_aes_key = WECHAT_ENCODING_AES_KEY + '='  # 补齐等号
        self.app_id = WECHAT_APP_ID
        self.app_secret = WECHAT_APP_SECRET
        self._access_token = AccessToken()  # 用于存储access_token
        
    def _create_cipher(self):
        """创建新的cipher实例"""
        return AES.new(
            base64.b64decode(self.encoding_aes_key),
            AES.MODE_CBC,
            iv=base64.b64decode(self.encoding_aes_key)[:16]
        )

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
                url = "https://api.weixin.qq.com/cgi-bin/token"
                params = {
                    "grant_type": "client_credential",
                    "appid": self.app_id,
                    "secret": self.app_secret
                }
                
                logger.info("[WeChat] 开始获取access_token")
                response = requests.get(url, params=params)
                result = response.json()
                
                if "access_token" in result:
                    self._access_token.access_token = result["access_token"]
                    self._access_token.expires_time = now + result["expires_in"]
                    logger.info("[WeChat] 成功获取access_token")
                    return self._access_token.access_token
                else:
                    error_code = result.get("errcode", "未知")
                    error_msg = result.get("errmsg", "未知错误")
                    logger.error(f"[WeChat] 获取access_token失败: [{error_code}] {error_msg}")
                    
                    if error_code == 40164:
                        logger.error("[WeChat] IP地址不在白名单中，请在微信公众平台配置IP白名单")
                    elif error_code == 40001:
                        logger.error("[WeChat] AppSecret错误或不属于该公众号")
                    elif error_code == 40013:
                        logger.error("[WeChat] AppID无效")
                    
                    raise Exception(f"获取access_token失败: [{error_code}] {error_msg}")
                    
            except Exception as e:
                logger.error(f"[WeChat] 获取access_token异常: {str(e)}", exc_info=True)
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

    def check_signature(self, signature, timestamp, nonce):
        """
        验证微信签名
        :param signature: 微信加密签名
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: bool 签名是否正确
        """
        try:
            # 1. 将token、timestamp、nonce三个参数进行字典序排序
            temp = [self.token, timestamp, nonce]
            temp.sort()

            # 2. 将三个参数字符串拼接成一个字符串进行sha1加密
            temp_str = ''.join(temp)
            sign = hashlib.sha1(temp_str.encode('utf-8')).hexdigest()
            
            # 3. 开启调试日志
            logger.debug(f"[WeChat] 本地签名计算: token={self.token}, timestamp={timestamp}, nonce={nonce}")
            logger.debug(f"[WeChat] 本地计算的签名: {sign}")
            logger.debug(f"[WeChat] 微信传入的签名: {signature}")
            
            # 4. 将加密后的字符串与signature对比
            return sign == signature
            
        except Exception as e:
            logger.error(f"[WeChat] 签名验证失败: {str(e)}", exc_info=True)
            return False

    def _decrypt_message(self, encrypted_msg):
        """
        解密消息
        :param encrypted_msg: 加密后的消息
        :return: 解密后的XML字符串
        """
        try:
            # Base64解码
            encrypted_data = base64.b64decode(encrypted_msg)
            
            # 创建新的cipher用于解密
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
            
            # 获取AppID
            received_app_id = content[20+msg_len:].decode('utf-8')
            
            # 验证AppID
            if received_app_id != self.app_id:
                raise ValueError("AppID不匹配")
                
            return xml_content.decode('utf-8')
            
        except Exception as e:
            logger.error(f"[WeChat] 消息解密失败: {str(e)}", exc_info=True)
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
                   reply_msg.encode('utf-8') + self.app_id.encode('utf-8')
            
            # 补位
            pad_num = 32 - (len(text) % 32)
            text += bytes([pad_num] * pad_num)
            
            # 创建新的cipher用于加密
            cipher = self._create_cipher()
            
            # AES加密
            encrypted_text = cipher.encrypt(text)
            
            # Base64编码
            return base64.b64encode(encrypted_text).decode('utf-8')
            
        except Exception as e:
            logger.error(f"[WeChat] 消息加密失败: {str(e)}", exc_info=True)
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
            logger.error(f"[WeChat] 生成加密响应失败: {str(e)}", exc_info=True)
            raise
            
    def handle_message(self, xml_data, msg_signature=None, timestamp=None, nonce=None, encrypt_type=None):
        """
        处理微信消息
        :param xml_data: 原始XML消息数据
        :param msg_signature: 消息签名（加密模式下使用）
        :param timestamp: 时间戳
        :param nonce: 随机数
        :param encrypt_type: 加密类型（aes或为空）
        :return: 响应消息
        """
        try:
            # 输出当前access_token
            try:
                current_token = self.get_access_token()
                logger.info(f"[WeChat] 当前access_token: {current_token}")
            except Exception as e:
                logger.error(f"[WeChat] 获取access_token失败: {str(e)}")

            xml_str = xml_data.decode('utf-8')
            logger.info(f"[WeChat] 收到原始消息: {xml_str}")
            
            # 解析XML
            root = ET.fromstring(xml_str)
            
            # 处理加密消息
            if encrypt_type == 'aes':
                # 获取加密消息
                encrypted_msg = root.find('Encrypt').text
                logger.debug(f"[WeChat] 收到加密消息: {encrypted_msg}")
                
                # 验证消息签名
                signature_list = [self.token, timestamp, nonce, encrypted_msg]
                signature_list.sort()
                calc_signature = hashlib.sha1(''.join(signature_list).encode('utf-8')).hexdigest()
                
                if calc_signature != msg_signature:
                    logger.warning("[WeChat] 消息签名验证失败")
                    return 'Invalid signature', 403
                
                # 解密消息
                xml_str = self._decrypt_message(encrypted_msg)
                logger.debug(f"[WeChat] 解密后的消息: {xml_str}")
                root = ET.fromstring(xml_str)
            
            # 获取消息基本信息
            msg_type = root.find('MsgType').text
            from_user = root.find('FromUserName').text
            to_user = root.find('ToUserName').text
            create_time = root.find('CreateTime').text
            
            logger.info(f"[WeChat] 消息类型: {msg_type}")
            logger.info(f"[WeChat] 发送者OpenID: {from_user}")
            logger.info(f"[WeChat] 接收者: {to_user}")
            logger.info(f"[WeChat] 消息创建时间: {create_time}")
            
            # 根据消息类型处理
            if msg_type == 'text':
                # 处理文本消息
                content = root.find('Content').text
                msg_id = root.find('MsgId').text
                logger.info(f"[WeChat] 收到文本消息 - 内容: {content}, 消息ID: {msg_id}")
                response_content = self._handle_text_message(content)
                
            elif msg_type == 'image':
                # 处理图片消息
                pic_url = root.find('PicUrl').text
                media_id = root.find('MediaId').text
                msg_id = root.find('MsgId').text
                logger.info(f"[WeChat] 收到图片消息 - 图片URL: {pic_url}, MediaID: {media_id}, 消息ID: {msg_id}")
                response_content = "图片已收到"
                
            elif msg_type == 'voice':
                # 处理语音消息
                media_id = root.find('MediaId').text
                format_type = root.find('Format').text
                msg_id = root.find('MsgId').text
                recognition = root.find('Recognition')
                if recognition is not None:
                    logger.info(f"[WeChat] 收到语音消息 - 格式: {format_type}, MediaID: {media_id}, 语音识别结果: {recognition.text}")
                else:
                    logger.info(f"[WeChat] 收到语音消息 - 格式: {format_type}, MediaID: {media_id}")
                response_content = "语音已收到"
                
            elif msg_type == 'video':
                # 处理视频消息
                media_id = root.find('MediaId').text
                thumb_media_id = root.find('ThumbMediaId').text
                msg_id = root.find('MsgId').text
                logger.info(f"[WeChat] 收到视频消息 - MediaID: {media_id}, 视频封面MediaID: {thumb_media_id}, 消息ID: {msg_id}")
                response_content = "视频已收到"
                
            elif msg_type == 'location':
                # 处理位置消息
                location_x = root.find('Location_X').text
                location_y = root.find('Location_Y').text
                scale = root.find('Scale').text
                label = root.find('Label').text
                msg_id = root.find('MsgId').text
                logger.info(f"[WeChat] 收到位置消息 - 位置: {label}, 经度: {location_y}, 纬度: {location_x}, 精度: {scale}, 消息ID: {msg_id}")
                response_content = f"位置已收到：{label}"
                
            elif msg_type == 'link':
                # 处理链接消息
                title = root.find('Title').text
                description = root.find('Description').text
                url = root.find('Url').text
                msg_id = root.find('MsgId').text
                logger.info(f"[WeChat] 收到链接消息 - 标题: {title}, 描述: {description}, URL: {url}, 消息ID: {msg_id}")
                response_content = f"链接已收到：{title}"
                
            elif msg_type == 'event':
                # 处理事件消息
                event = root.find('Event').text
                logger.info(f"[WeChat] 收到事件推送 - 事件类型: {event}")
                response_content = self._handle_event_message(event, root)
                
            else:
                logger.warning(f"[WeChat] 收到未知类型消息: {msg_type}")
                response_content = "收到消息"
            
            # 构建响应XML
            current_timestamp = int(time.time())
            reply_msg = f"""<xml>
                <ToUserName><![CDATA[{from_user}]]></ToUserName>
                <FromUserName><![CDATA[{to_user}]]></FromUserName>
                <CreateTime>{current_timestamp}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{response_content}]]></Content>
            </xml>"""
            
            # 如果是加密模式，需要加密响应消息
            if encrypt_type == 'aes':
                reply_msg = self._get_encrypted_response(reply_msg, timestamp, nonce)
            
            logger.debug(f"[WeChat] 返回消息: {reply_msg}")
            return reply_msg
            
        except Exception as e:
            logger.error(f"[WeChat] 处理消息失败: {str(e)}", exc_info=True)
            return ''
            
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
                return "您可以：\n1. 点击菜单查看功能\n2. 发送位置信息\n3. 查询积分信息"
            else:
                return f"您发送的消息是：{content}\n请点击下方菜单使用功能。"
        except Exception as e:
            logger.error(f"[WeChat] 处理文本消息异常: {str(e)}", exc_info=True)
            return "抱歉，处理消息时出现错误，请稍后再试"
            
    def _handle_event_message(self, event, root):
        """
        处理事件消息
        :param event: 事件类型
        :param root: XML根节点
        :return: 响应内容
        """
        try:
            event = event.lower()
            if event == 'subscribe':
                # 处理关注事件
                event_key = root.find('EventKey')
                ticket = root.find('Ticket')
                if event_key is not None and ticket is not None:
                    # 通过扫描带参数二维码关注
                    scene_value = event_key.text.replace('qrscene_', '')
                    logger.info(f"[WeChat] 用户通过带参二维码关注 - 场景值: {scene_value}, Ticket: {ticket.text}")
                    return f"感谢关注！您是通过二维码({scene_value})关注的。\n请点击下方菜单使用我们的服务。"
                else:
                    logger.info("[WeChat] 用户直接关注")
                    return "感谢您的关注！\n请点击下方菜单使用我们的服务。"
                    
            elif event == 'unsubscribe':
                # 处理取消关注事件
                logger.info("[WeChat] 用户取消关注")
                return ""
                
            elif event == 'scan':
                # 处理已关注用户扫描二维码事件
                scene_value = root.find('EventKey').text
                ticket = root.find('Ticket').text
                logger.info(f"[WeChat] 已关注用户扫描二维码 - 场景值: {scene_value}, Ticket: {ticket}")
                return f"您扫描的场景值是：{scene_value}"
                
            elif event == 'location':
                # 处理上报地理位置事件
                latitude = root.find('Latitude').text
                longitude = root.find('Longitude').text
                precision = root.find('Precision').text
                logger.info(f"[WeChat] 收到位置上报 - 纬度: {latitude}, 经度: {longitude}, 精度: {precision}")
                return ""  # 位置上报事件不需要回复
                
            elif event == 'click':
                # 处理菜单点击事件
                event_key = root.find('EventKey').text
                logger.info(f"[WeChat] 收到菜单点击事件 - EventKey: {event_key}")
                return self._handle_menu_click(event_key)
                
            elif event == 'view':
                # 处理菜单跳转链接事件
                event_key = root.find('EventKey').text
                logger.info(f"[WeChat] 收到菜单跳转事件 - URL: {event_key}")
                return ""  # 跳转链接不需要回复
                
            elif event == 'location_select':
                # 处理弹出地理位置选择器事件
                location = root.find('SendLocationInfo')
                if location is not None:
                    location_x = location.find('Location_X').text  # 纬度
                    location_y = location.find('Location_Y').text  # 经度
                    scale = location.find('Scale').text  # 精度
                    label = location.find('Label').text  # 位置名称
                    logger.info(f"[WeChat] 用户选择位置 - 位置: {label}, 经度: {location_y}, 纬度: {location_x}, 精度: {scale}")
                    return f"您选择的位置是：\n位置：{label}\n经度：{location_y}\n纬度：{location_x}\n精度：{scale}"
                logger.warning("[WeChat] 未能获取位置信息")
                return "未能获取到位置信息"
                
            else:
                logger.warning(f"[WeChat] 收到未知事件类型: {event}")
                return "感谢您的互动！"
                
        except Exception as e:
            logger.error(f"[WeChat] 处理事件消息异常: {str(e)}", exc_info=True)
            return "抱歉，处理消息时出现错误，请稍后再试"

    def _handle_menu_click(self, event_key):
        """
        处理菜单点击事件
        :param event_key: 菜单key值
        :return: 响应内容
        """
        try:
            if event_key == 'get_points':
                # 获取用户积分信息（默认player_id=1）
                from function.PlayerService import player_service
                player_data = player_service.get_player(1)
                
                if isinstance(player_data, dict) and 'data' in player_data:
                    player = player_data['data']
                    return f"您的积分信息：\n当前积分：{player.get('points', 0)}\n等级：{player.get('level', 1)}"
                else:
                    return "抱歉，获取积分信息失败，请稍后再试"
                    
            elif event_key == 'send_location':
                return "请发送您的位置信息"
            else:
                return f"您点击了未知菜单：{event_key}"
                
        except Exception as e:
            logger.error(f"[WeChat] 处理菜单点击事件异常: {str(e)}", exc_info=True)
            return "抱歉，服务器处理请求时出现错误，请稍后再试"

    def create_menu(self):
        """
        创建自定义菜单
        """
        try:
            # 获取access_token
            access_token = self.get_access_token()
            
            # 菜单配置
            menu_data = {
                "button": [
                    {
                        "name": "位置服务",
                        "type": "location_select",
                        "key": "send_location"
                    },
                    {
                        "name": "我的积分",
                        "type": "click",
                        "key": "get_points"
                    }
                ]
            }
            
            # 调用微信接口创建菜单
            url = f"https://api.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}"
            response = requests.post(url, json=menu_data)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info("[WeChat] 自定义菜单创建成功")
                return True
            else:
                logger.error(f"[WeChat] 自定义菜单创建失败: {result}")
                return False
                
        except Exception as e:
            logger.error(f"[WeChat] 创建自定义菜单异常: {str(e)}", exc_info=True)
            return False

# 创建服务实例
wechat_service = WeChatService()
