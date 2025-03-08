# -*- coding: utf-8 -*-
import hashlib
import logging
import time
import requests
import threading
from config.private import QYWECHAT_CORP_ID, QYWECHAT_AGENT_ID, QYWECHAT_CORP_SECRET
from Crypto.Cipher import AES
import base64
import struct
import random
import string

logger = logging.getLogger(__name__)

class QYWeChatAuth:
    """企业微信鉴权类"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(QYWeChatAuth, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.corp_id = QYWECHAT_CORP_ID
            self.agent_id = QYWECHAT_AGENT_ID
            self.corp_secret = QYWECHAT_CORP_SECRET
            self.token = "xCmY3kAhUPNFjQjwUboMvii2oJxCNg6K"  # 用于验证URL
            self.encoding_aes_key = "c5GBoCr1nkrowd1AlaqjpUNQL6dcg9ervFSitvToarB"  # 消息加解密密钥
            self._access_token = None
            self._access_token_expires = 0
            self.initialized = True
            
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
                    return self._access_token
                else:
                    logger.error(f"[QYWeChat] 获取access_token失败: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"[QYWeChat] 获取access_token异常: {str(e)}")
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

    def _generate_signature(self, token, timestamp, nonce, encrypt):
        """
        生成签名
        :param token: 配置的Token
        :param timestamp: 时间戳
        :param nonce: 随机字符串
        :param encrypt: 加密的消息体
        :return: 签名字符串
        """
        sign_list = [token, timestamp, nonce]
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
            msg_content = content[20:20+msg_len]
            
            # 获取企业ID
            received_corp_id = content[20+msg_len:].decode('utf-8')
            
            # 验证企业ID
            if received_corp_id != self.corp_id:
                raise ValueError("企业ID不匹配")
                
            return msg_content.decode('utf-8')
            
        except Exception as e:
            logger.error(f"[QYWeChat] 消息解密失败: {str(e)}")
            raise
            
    def encrypt_message(self, reply_msg):
        """加密消息"""
        try:
            # 生成16位随机字符串
            random_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            
            # 生成密文
            msg_len = struct.pack('!I', len(reply_msg.encode('utf-8')))
            text = random_str.encode('utf-8') + msg_len + reply_msg.encode('utf-8') + self.corp_id.encode('utf-8')
            
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
            logger.error(f"[QYWeChat] 消息加密失败: {str(e)}")
            raise
            
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
            # 1. 验证签名
            signature = self._generate_signature(self.token, timestamp, nonce, echostr)
            if signature != msg_signature:
                logger.error("[QYWeChat] URL验证失败：签名不匹配")
                logger.debug(f"计算的签名: {signature}")
                logger.debug(f"接收的签名: {msg_signature}")
                return None
                
            # 2. 解密echostr
            decrypted_str = self.decrypt_message(echostr)
            logger.info("[QYWeChat] URL验证成功")
            return decrypted_str
            
        except Exception as e:
            logger.error(f"[QYWeChat] URL验证异常: {str(e)}")
            return None

    def get_encrypted_response(self, reply_msg, timestamp, nonce):
        """
        获取加密后的响应消息
        :param reply_msg: 回复的消息
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: 加密后的XML
        """
        try:
            # 1. 加密消息
            encrypt = self.encrypt_message(reply_msg)
            
            # 2. 生成签名
            signature = self._generate_signature(self.token, timestamp, nonce, encrypt)
            
            # 3. 生成加密后的XML
            return f"""<xml>
                <Encrypt><![CDATA[{encrypt}]]></Encrypt>
                <MsgSignature><![CDATA[{signature}]]></MsgSignature>
                <TimeStamp>{timestamp}</TimeStamp>
                <Nonce><![CDATA[{nonce}]]></Nonce>
            </xml>"""
            
        except Exception as e:
            logger.error(f"[QYWeChat] 生成加密响应失败: {str(e)}")
            raise

# 创建鉴权实例
qywechat_auth = QYWeChatAuth()
