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
                    logger.info(f"[QYWeChatAuth] 获取access_token成功: {self._access_token}")
                    return self._access_token
                else:
                    logger.error(f"[QYWeChatAuth] 获取access_token失败: {result}")
                    return None
                    
            except Exception as e:
                logger.error(f"[QYWeChatAuth] 获取access_token异常: {str(e)}")
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
            # logger.info(f"[QYWeChatAuth] ============ 消息解密开始 ============")
            # logger.info(f"[QYWeChatAuth] 待解密的消息: {encrypted_msg}")
            
            # 1. Base64解码
            encrypted_data = base64.b64decode(encrypted_msg)
            # logger.info(f"[QYWeChatAuth] Base64解码后数据长度: {len(encrypted_data)} 字节")
            # logger.info(f"[QYWeChatAuth] Base64解码后数据(hex): {encrypted_data.hex()}")
            
            # 2. AES解密
            key = base64.b64decode(self.encoding_aes_key + '=')
            cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
            decrypted_data = cipher.decrypt(encrypted_data)
            # logger.info(f"[QYWeChatAuth] AES解密后数据长度: {len(decrypted_data)} 字节")
            # logger.info(f"[QYWeChatAuth] AES解密后数据(hex): {decrypted_data.hex()}")
            
            # 3. 处理PKCS7填充
            pad = decrypted_data[-1]
            if not isinstance(pad, int):
                pad = ord(pad)
            content = decrypted_data[:-pad]
            # logger.info(f"[QYWeChatAuth] 去除PKCS7填充后数据长度: {len(content)} 字节")
            # logger.info(f"[QYWeChatAuth] 去除填充后数据(hex): {content.hex()}")
            
            # 4. 解析数据结构
            # logger.info(f"[QYWeChatAuth] -------- 解密后数据结构解析 --------")
            
            # a) 16字节随机字符串(random)
            random_str = content[:16]
            # logger.info(f"[QYWeChatAuth] [字段1] random (16字节): {random_str.hex()}")
            
            # b) 4字节消息长度(msg_len)
            msg_len = struct.unpack('>I', content[16:20])[0]
            # logger.info(f"[QYWeChatAuth] [字段2] msg_len (4字节): {msg_len}")
            
            # c) 消息内容(msg)
            msg_content = content[20:20+msg_len]
            try:
                msg_text = msg_content.decode('utf-8')
                # logger.info(f"[QYWeChatAuth] [字段3] msg (消息内容): {msg_text}")
            except UnicodeDecodeError:
                logger.info(f"[QYWeChatAuth] [字段3] msg (消息内容,hex): {msg_content.hex()}")
            
            # d) 企业ID(receiveid)
            receiveid = content[20+msg_len:].decode('utf-8')
            # logger.info(f"[QYWeChatAuth] [字段4] receiveid (企业ID): {receiveid}")
            # logger.info(f"[QYWeChatAuth] [字段4] 配置的企业ID: {self.corp_id}")
            # logger.info(f"[QYWeChatAuth] --------------------------------")
            
            # 5. 验证企业ID
            if receiveid != self.corp_id:
                # logger.error(f"[QYWeChatAuth] 企业ID不匹配")
                # logger.error(f"[QYWeChatAuth] - 接收到的企业ID: {receiveid}")
                # logger.error(f"[QYWeChatAuth] - 配置的企业ID: {self.corp_id}")
                logger.error(f"[QYWeChatAuth] ============ 消息解密失败 ============")
                raise ValueError(f"企业ID不匹配: {receiveid} != {self.corp_id}")
            
            # 6. 返回消息内容
            # logger.info(f"[QYWeChatAuth] 解密成功，返回消息内容: {msg_text}")
            # logger.info(f"[QYWeChatAuth] ============ 消息解密结束 ============")
            return msg_text
                
        except Exception as e:
            logger.error(f"[QYWeChatAuth] 消息解密失败: {str(e)}", exc_info=True)
            logger.error(f"[QYWeChatAuth] ============ 消息解密异常结束 ============")
            raise
            
    def encrypt_message(self, reply_msg):
        """加密消息"""
        try:
            # logger.info(f"[QYWeChatAuth] ============ 消息加密开始 ============")
            # logger.info(f"[QYWeChatAuth] 待加密的消息: {reply_msg}")
            
            # 生成16位随机字符串
            random_str = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
            # logger.info(f"[QYWeChatAuth] 生成的随机字符串: {random_str}")
            
            # 生成密文
            msg_len = struct.pack('!I', len(reply_msg.encode('utf-8')))
            text = random_str.encode('utf-8') + msg_len + reply_msg.encode('utf-8') + self.corp_id.encode('utf-8')
            # logger.info(f"[QYWeChatAuth] 拼接后的数据(hex): {text.hex()}")
            
            # 补位
            pad_num = 32 - (len(text) % 32)
            text += bytes([pad_num] * pad_num)
            # logger.info(f"[QYWeChatAuth] PKCS7填充后数据长度: {len(text)} 字节")
            # logger.info(f"[QYWeChatAuth] 填充后数据(hex): {text.hex()}")
            
            # 创建加密器
            cipher = self._create_cipher()
            
            # AES加密
            encrypted_text = cipher.encrypt(text)
            # logger.info(f"[QYWeChatAuth] AES加密后数据长度: {len(encrypted_text)} 字节")
            # logger.info(f"[QYWeChatAuth] AES加密后数据(hex): {encrypted_text.hex()}")
            
            # Base64编码
            base64_text = base64.b64encode(encrypted_text).decode('utf-8')
            # logger.info(f"[QYWeChatAuth] Base64编码后: {base64_text}")
            # logger.info(f"[QYWeChatAuth] ============ 消息加密结束 ============")
            
            return base64_text
            
        except Exception as e:
            logger.error(f"[QYWeChatAuth] 消息加密失败: {str(e)}", exc_info=True)
            logger.error(f"[QYWeChatAuth] ============ 消息加密异常结束 ============")
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
                logger.error("[QYWeChatAuth] URL验证失败：缺少必要参数")
                for param_name, param_value in {
                    'msg_signature': msg_signature,
                    'timestamp': timestamp,
                    'nonce': nonce,
                    'echostr': echostr
                }.items():
                    if not param_value:
                        logger.error(f"[QYWeChatAuth] 缺少参数: {param_name}")
                return None

            # 1. 验证签名
            logger.info(f"[QYWeChatAuth] ============ URL验证开始 ============")
            logger.info(f"[QYWeChatAuth] 接收到的参数:")
            logger.info(f"[QYWeChatAuth] - msg_signature: {msg_signature}")
            logger.info(f"[QYWeChatAuth] - timestamp: {timestamp}")
            logger.info(f"[QYWeChatAuth] - nonce: {nonce}")
            logger.info(f"[QYWeChatAuth] - echostr: {echostr}")
            logger.info(f"[QYWeChatAuth] - token: {self.token}")
            
            # 生成签名
            signature = self._generate_signature(self.token, timestamp, nonce, echostr)
            logger.info(f"[QYWeChatAuth] 签名生成过程:")
            logger.info(f"[QYWeChatAuth] 1. 排序前的数组: ['{self.token}', '{timestamp}', '{nonce}', '{echostr}']")
            sorted_arr = sorted([self.token, timestamp, nonce, echostr])
            logger.info(f"[QYWeChatAuth] 2. 排序后的数组: {sorted_arr}")
            logger.info(f"[QYWeChatAuth] 3. 拼接后的字符串: {''.join(sorted_arr)}")
            logger.info(f"[QYWeChatAuth] 4. 计算得到的签名: {signature}")
            logger.info(f"[QYWeChatAuth] 5. 接收到的签名: {msg_signature}")
            
            if signature.lower() != msg_signature.lower():
                logger.error(f"[QYWeChatAuth] URL验证失败：签名不匹配")
                logger.error(f"[QYWeChatAuth] - 计算签名: {signature}")
                logger.error(f"[QYWeChatAuth] - 接收签名: {msg_signature}")
                return None
            else:
                logger.info(f"[QYWeChatAuth] 签名验证通过")
                
            # 2. 解密echostr
            try:
                logger.info("[QYWeChatAuth] 开始解密echostr...")
                logger.info(f"[QYWeChatAuth] Base64编码的echostr: {echostr}")
                
                # Base64解码
                encrypted_data = base64.b64decode(echostr)
                logger.info(f"[QYWeChatAuth] Base64解码后的数据长度: {len(encrypted_data)} 字节")
                logger.info(f"[QYWeChatAuth] Base64解码后的数据(hex): {encrypted_data.hex()}")
                
                # AES解密
                decrypted_str = self.decrypt_message(echostr)
                if not decrypted_str:
                    logger.error("[QYWeChatAuth] 解密结果为空")
                    return None
                    
                logger.info(f"[QYWeChatAuth] URL验证成功")
                logger.info(f"[QYWeChatAuth] - 解密后的echostr明文: {decrypted_str}")
                logger.info(f"[QYWeChatAuth] ============ URL验证结束 ============")
                
                # 确保返回的是字符串类型
                return str(decrypted_str).strip()
                
            except Exception as e:
                logger.error(f"[QYWeChatAuth] 解密echostr失败: {str(e)}", exc_info=True)
                logger.error(f"[QYWeChatAuth] ============ URL验证异常结束 ============")
                return None
                
        except Exception as e:
            logger.error(f"[QYWeChatAuth] URL验证异常: {str(e)}", exc_info=True)
            logger.error(f"[QYWeChatAuth] ============ URL验证异常结束 ============")
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
            logger.error(f"[QYWeChatAuth] 生成加密响应失败: {str(e)}")
            raise

# 创建鉴权实例
qywechat_auth = QYWeChatAuth()
