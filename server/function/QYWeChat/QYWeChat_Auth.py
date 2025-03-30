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
    _instances = {}  # 用于存储不同配置的实例
    _lock = threading.Lock()
    
    def __new__(cls, corp_id=None, agent_id=None, corp_secret=None, token=None, encoding_aes_key=None):
        # 如果没有提供参数，使用默认配置
        if all(param is None for param in [corp_id, agent_id, corp_secret, token, encoding_aes_key]):
            corp_id = QYWECHAT_CORP_ID
            agent_id = QYWECHAT_AGENT_ID
            corp_secret = QYWECHAT_CORP_SECRET
            token = QYWECHAT_TOKEN
            encoding_aes_key = QYWECHAT_ENCODING_AES_KEY
            
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
            logger.info(f"[QYWeChatAuth] - Token: {'已配置' if self.token else '未配置'}")
            logger.info(f"[QYWeChatAuth] - EncodingAESKey: {'已配置' if self.encoding_aes_key else '未配置'}")
            
    @classmethod
    def get_instance(cls, corp_id=None, agent_id=None, corp_secret=None, token=None, encoding_aes_key=None):
        """获取指定配置的实例"""
        return cls(corp_id, agent_id, corp_secret, token, encoding_aes_key)
    
    @classmethod
    def clear_instances(cls):
        """清除所有实例（用于测试）"""
        with cls._lock:
            cls._instances.clear()
            
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
            # 1. Base64解码
            encrypted_data = base64.b64decode(encrypted_msg)
            
            # 2. AES解密
            key = base64.b64decode(self.encoding_aes_key + '=')
            cipher = AES.new(key, AES.MODE_CBC, iv=key[:16])
            decrypted_data = cipher.decrypt(encrypted_data)
            
            # 3. 处理PKCS7填充
            pad = decrypted_data[-1]
            if not isinstance(pad, int):
                pad = ord(pad)
            content = decrypted_data[:-pad]
            
            # 4. 解析数据结构
            random_str = content[:16]
            msg_len = struct.unpack('>I', content[16:20])[0]
            msg_content = content[20:20+msg_len]
            receiveid = content[20+msg_len:].decode('utf-8')
            
            # 5. 验证企业ID
            if receiveid != self.corp_id:
                logger.error(f"[QYWeChatAuth] 企业ID不匹配: {receiveid} != {self.corp_id}")
                raise ValueError(f"企业ID不匹配: {receiveid} != {self.corp_id}")
            
            # 6. 返回消息内容
            return msg_content.decode('utf-8')
                
        except Exception as e:
            logger.error(f"[QYWeChatAuth] 消息解密失败: {str(e)}", exc_info=True)
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
            base64_text = base64.b64encode(encrypted_text).decode('utf-8')
            
            return base64_text
            
        except Exception as e:
            logger.error(f"[QYWeChatAuth] 消息加密失败: {str(e)}", exc_info=True)
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
