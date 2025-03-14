# -*- coding: utf-8 -*-
import hashlib
import logging
import time
import requests
import threading
from config.private import (
    QYWECHAT_CORP_ID, 
    QYWECHAT_AGENT_ID, 
    QYWECHAT_CORP_SECRET,
    QYWECHAT_TOKEN,
    QYWECHAT_ENCODING_AES_KEY
)
from Crypto.Cipher import AES
import base64
import struct
import random
import string
from functools import lru_cache

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
            self.token = QYWECHAT_TOKEN  # 从配置文件读取
            self.encoding_aes_key = QYWECHAT_ENCODING_AES_KEY  # 从配置文件读取
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
                    logger.info(f"[QYWeChat] 获取access_token成功: {self._access_token}")
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

    @lru_cache(maxsize=1000)
    def _generate_signature(self, token, timestamp, nonce, encrypt):
        """使用缓存优化签名生成"""
        sign_list = [token, timestamp, nonce]
        if encrypt:
            sign_list.append(encrypt)
        sign_list.sort()
        sign_str = ''.join(sign_list)
        return hashlib.sha1(sign_str.encode('utf-8')).hexdigest()
        
    def decrypt_message(self, encrypted_msg):
        """解密消息
        解密后的格式：random(16B) + msg_len(4B) + msg + receiveid
        返回msg字段的明文内容
        """
        try:
            # 1. Base64解码
            encrypted_data = base64.b64decode(encrypted_msg)
            logger.info(f"[QYWeChat] ============ 解密过程开始 ============")
            logger.info(f"[QYWeChat] Base64解码后数据长度: {len(encrypted_data)} 字节")
            
            # 2. AES解密
            key = base64.b64decode(self.encoding_aes_key + '=')
            cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
            decrypted_data = cipher.decrypt(encrypted_data)
            logger.info(f"[QYWeChat] AES解密后数据长度: {len(decrypted_data)} 字节")
            
            # 3. 处理PKCS7填充
            pad = decrypted_data[-1]
            if not isinstance(pad, int):
                pad = ord(pad)
            content = decrypted_data[:-pad]
            logger.info(f"[QYWeChat] 去除PKCS7填充后数据长度: {len(content)} 字节")
            
            # 4. 解析数据结构
            logger.info(f"[QYWeChat] -------- 解密后数据结构 --------")
            
            # a) 16字节随机字符串(random)
            random_str = content[:16]
            logger.info(f"[QYWeChat] [字段1] random (16字节): {random_str.hex()}")
            
            # b) 4字节消息长度(msg_len)
            msg_len = struct.unpack('>I', content[16:20])[0]
            logger.info(f"[QYWeChat] [字段2] msg_len (4字节): {msg_len}")
            
            # c) 消息内容(msg)
            msg_content = content[20:20+msg_len]
            try:
                msg_text = msg_content.decode('utf-8')
                logger.info(f"[QYWeChat] [字段3] msg (消息内容): {msg_text}")
            except UnicodeDecodeError:
                logger.info(f"[QYWeChat] [字段3] msg (消息内容,hex): {msg_content.hex()}")
            
            # d) 企业ID(receiveid)
            receiveid = content[20+msg_len:].decode('utf-8')
            logger.info(f"[QYWeChat] [字段4] receiveid (企业ID): {receiveid}")
            logger.info(f"[QYWeChat] --------------------------------")
            
            # 5. 验证企业ID
            if receiveid != self.corp_id:
                logger.error(f"[QYWeChat] 企业ID不匹配: 接收到 {receiveid}，期望 {self.corp_id}")
                raise ValueError(f"企业ID不匹配: {receiveid} != {self.corp_id}")
            
            # 6. 直接返回消息内容(msg字段)，不做任何额外处理
            logger.info(f"[QYWeChat] 解密成功，返回消息内容: {msg_text}")
            logger.info(f"[QYWeChat] ============ 解密过程结束 ============")
            return msg_text
                
        except Exception as e:
            logger.error(f"[QYWeChat] 消息解密失败: {str(e)}", exc_info=True)
            logger.info(f"[QYWeChat] ============ 解密过程异常结束 ============")
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
        :return: 解密后的echostr明文
        """
        try:
            # 参数完整性检查
            if not all([msg_signature, timestamp, nonce, echostr]):
                logger.error("[QYWeChat] URL验证失败：缺少必要参数")
                return None

            # 1. 验证签名
            signature = self._generate_signature(self.token, timestamp, nonce, echostr)
            logger.info(f"[QYWeChat] URL验证 - 接收参数:")
            logger.info(f"[QYWeChat] - msg_signature: {msg_signature}")
            logger.info(f"[QYWeChat] - timestamp: {timestamp}")
            logger.info(f"[QYWeChat] - nonce: {nonce}")
            logger.info(f"[QYWeChat] - echostr: {echostr}")
            logger.info(f"[QYWeChat] - 计算得到的签名: {signature}")
            
            if signature.lower() != msg_signature.lower():
                logger.error(f"[QYWeChat] URL验证失败：签名不匹配 (计算值: {signature}, 接收值: {msg_signature})")
                return None
                
            # 2. 解密echostr
            try:
                logger.info("[QYWeChat] 开始解密echostr...")
                decrypted_str = self.decrypt_message(echostr)
                if not decrypted_str:
                    logger.error("[QYWeChat] 解密结果为空")
                    return None
                    
                logger.info(f"[QYWeChat] URL验证成功，解密后的echostr明文: {decrypted_str}")
                # 确保返回的是字符串类型
                return str(decrypted_str).strip()
                
            except Exception as e:
                logger.error(f"[QYWeChat] 解密echostr失败: {str(e)}", exc_info=True)
                return None
                
        except Exception as e:
            logger.error(f"[QYWeChat] URL验证异常: {str(e)}", exc_info=True)
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
