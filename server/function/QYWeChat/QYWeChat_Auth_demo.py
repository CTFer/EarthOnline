# -*- coding: utf-8 -*-
import base64
import hashlib
import logging
import time
import requests
import threading
import random
import string
import struct
import socket
from Crypto.Cipher import AES
import xml.etree.ElementTree as ET
from config.private import (
    QYWECHAT_CORP_ID,
    QYWECHAT_AGENT_ID,
    QYWECHAT_CORP_SECRET,
    QYWECHAT_TOKEN,
    QYWECHAT_ENCODING_AES_KEY
)

logger = logging.getLogger(__name__)


class CryptError(Exception):
    """加解密异常"""

    def __init__(self, error_code, error_msg):
        super().__init__(error_msg)
        self.error_code = error_code
        self.error_msg = error_msg


class QYWeChatCrypt:
    """企业微信加解密实现"""

    def __init__(self, encoding_aes_key: str, token: str, receive_id: str):
        """
        初始化加解密实例

        Args:
            encoding_aes_key: EncodingAESKey
            token: Token
            receive_id: 企业ID/应用ID
        """
        try:
            self.key = base64.b64decode(encoding_aes_key + "=")
            assert len(self.key) == 32
        except Exception as e:
            logger.error(f"[QYWeChat] AES密钥初始化失败: {str(e)}")
            raise CryptError(900001, "AES密钥初始化失败")

        self.token = token
        self.receive_id = receive_id
        self.aes_mode = AES.MODE_CBC

    def _generate_random_str(self, length: int = 16) -> bytes:
        """生成指定长度的随机字符串"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length)).encode()

    def _calculate_signature(self, timestamp: str, nonce: str, encrypt: str) -> str:
        """
        计算签名

        Args:
            timestamp: 时间戳
            nonce: 随机数
            encrypt: 加密后的消息/echostr

        Returns:
            str: 消息签名
        """
        sign_list = [self.token, timestamp, nonce, encrypt]
        sign_list.sort()
        sign_str = ''.join(sign_list).encode()

        sha1 = hashlib.sha1()
        sha1.update(sign_str)
        return sha1.hexdigest()

    def _pkcs7_pad(self, data: bytes) -> bytes:
        """PKCS7填充"""
        block_size = 32
        padding_size = block_size - (len(data) % block_size)
        if padding_size == 0:
            padding_size = block_size
        return data + (chr(padding_size) * padding_size).encode()

    def _pkcs7_unpad(self, data: bytes) -> bytes:
        """PKCS7去填充"""
        pad_size = data[-1]
        if pad_size < 1 or pad_size > 32:
            pad_size = 0
        return data[:-pad_size]

    def encrypt_message(self, reply_msg: str, nonce: str = None, timestamp: str = None) -> str:
        """
        加密回复消息

        Args:
            reply_msg: 回复的消息明文
            nonce: 随机数，可选
            timestamp: 时间戳，可选

        Returns:
            str: 加密后的XML消息

        Raises:
            CryptError: 加密过程中的错误
        """
        try:
            # 生成随机字符串
            random_str = self._generate_random_str()

            # 生成时间戳(如果未提供)
            timestamp = timestamp or str(int(time.time()))

            # 生成随机数(如果未提供)
            nonce = nonce or str(random.randint(0, 9999999999))

            # 拼接明文
            msg_len = len(reply_msg.encode())
            msg_len_bytes = struct.pack(">I", msg_len)  # 网络字节序(big-endian)
            msg_content = random_str + msg_len_bytes + \
                reply_msg.encode() + self.receive_id.encode()

            # PKCS7填充
            padded_msg = self._pkcs7_pad(msg_content)

            # AES加密
            cryptor = AES.new(self.key, self.aes_mode, self.key[:16])
            encrypted = cryptor.encrypt(padded_msg)
            encrypt_msg = base64.b64encode(encrypted).decode()

            # 生成签名
            signature = self._calculate_signature(
                timestamp, nonce, encrypt_msg)

            # 生成返回的XML
            result = f"""
            <xml>
            <Encrypt><![CDATA[{encrypt_msg}]]></Encrypt>
            <MsgSignature><![CDATA[{signature}]]></MsgSignature>
            <TimeStamp>{timestamp}</TimeStamp>
            <Nonce><![CDATA[{nonce}]]></Nonce>
            </xml>"""

            return result

        except Exception as e:
            logger.error(f"[QYWeChat] 消息加密失败: {str(e)}", exc_info=True)
            raise CryptError(900002, f"消息加密失败: {str(e)}")

    def decrypt_message(self, xml_text: str, signature: str, timestamp: str, nonce: str) -> str:
        """
        解密消息

        Args:
            xml_text: 密文消息
            signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数

        Returns:
            str: 解密后的消息明文

        Raises:
            CryptError: 解密过程中的错误
        """
        try:
            # 提取密文
            xml_tree = ET.fromstring(xml_text)
            encrypt_node = xml_tree.find("Encrypt")
            if encrypt_node is None:
                raise CryptError(900003, "消息中没有找到Encrypt节点")
            encrypt_msg = encrypt_node.text

            # 验证签名
            calc_signature = self._calculate_signature(
                timestamp, nonce, encrypt_msg)
            if calc_signature != signature:
                raise CryptError(900004, "消息签名验证失败")

            # Base64解码
            decrypt_msg = base64.b64decode(encrypt_msg)

            # AES解密
            cryptor = AES.new(self.key, self.aes_mode, self.key[:16])
            decrypted = cryptor.decrypt(decrypt_msg)

            # 去除PKCS7填充
            content = self._pkcs7_unpad(decrypted)

            # 验证数据格式
            if len(content) < 20:  # random(16) + msgLen(4)
                raise CryptError(900005, "解密后的消息格式错误")

            # 解析消息
            random_str = content[:16]
            msg_len = struct.unpack(">I", content[16:20])[0]
            msg_content = content[20:20+msg_len]
            receive_id = content[20+msg_len:]

            # 验证corpid
            if receive_id.decode() != self.receive_id:
                raise CryptError(900006, "接收者ID校验失败")

            return msg_content.decode()

        except CryptError:
            raise
        except Exception as e:
            logger.error(f"[QYWeChat] 消息解密失败: {str(e)}", exc_info=True)
            raise CryptError(900007, f"消息解密失败: {str(e)}")

    def verify_url(self, signature: str, timestamp: str, nonce: str, echostr: str) -> str:
        """
        验证回调URL有效性

        Args:
            signature: 签名
            timestamp: 时间戳
            nonce: 随机数
            echostr: 加密的随机字符串

        Returns:
            str: 解密后的echostr

        Raises:
            CryptError: 验证过程中的错误
        """
        try:
            # 验证签名
            calc_signature = self._calculate_signature(
                timestamp, nonce, echostr)
            if calc_signature != signature:
                raise CryptError(900008, "URL验证签名校验失败")

            # 解密echostr
            cryptor = AES.new(self.key, self.aes_mode, self.key[:16])
            decrypted = cryptor.decrypt(base64.b64decode(echostr))

            # 去除PKCS7填充
            content = self._pkcs7_unpad(decrypted)

            # 验证数据格式
            if len(content) < 20:
                raise CryptError(900009, "解密后的echostr格式错误")

            # 解析数据
            msg_len = struct.unpack(">I", content[16:20])[0]
            msg_content = content[20:20+msg_len]
            receive_id = content[20+msg_len:]

            # 验证corpid
            if receive_id.decode() != self.receive_id:
                raise CryptError(900010, "接收者ID校验失败")

            return msg_content.decode()

        except CryptError:
            raise
        except Exception as e:
            logger.error(f"[QYWeChat] URL验证失败: {str(e)}", exc_info=True)
            raise CryptError(900011, f"URL验证失败: {str(e)}")


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
        """初始化企业微信鉴权实例"""
        if not hasattr(self, 'initialized'):
            # 初始化基本配置
            self.corp_id = QYWECHAT_CORP_ID
            self.agent_id = QYWECHAT_AGENT_ID
            self.corp_secret = QYWECHAT_CORP_SECRET
            self.token = QYWECHAT_TOKEN
            self.encoding_aes_key = QYWECHAT_ENCODING_AES_KEY
            self._access_token = None
            self._access_token_expires = 0

            # 初始化加解密实例
            try:
                self.crypt = QYWeChatCrypt(
                    encoding_aes_key=self.encoding_aes_key,
                    token=self.token,
                    receive_id=self.corp_id
                )
                logger.info("[QYWeChat] 加解密实例初始化成功")
            except Exception as e:
                logger.error(f"[QYWeChat] 加解密实例初始化失败: {str(e)}")
                raise

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
                    logger.info(
                        f"[QYWeChat] 获取access_token成功: {self._access_token}")
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

    def verify_url(self, msg_signature, timestamp, nonce, echostr):
        """
        验证URL有效性

        Args:
            msg_signature (str): 企业微信加密签名
            timestamp (str): 时间戳
            nonce (str): 随机数
            echostr (str): 加密的随机字符串

        Returns:
            str: 解密后的echostr明文，验证失败返回None
        """
        try:
            logger.info("[QYWeChat] 开始URL验证")
            logger.info(
                f"[QYWeChat] 参数: msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")

            result = self.crypt.verify_url(
                msg_signature, timestamp, nonce, echostr)
            logger.info(f"[QYWeChat] URL验证成功，解密后的echostr: {result}")
            return result

        except CryptError as e:
            logger.error(f"[QYWeChat] URL验证失败: [{e.error_code}] {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"[QYWeChat] URL验证异常: {str(e)}", exc_info=True)
            return None

    def decrypt_message(self, xml_text, msg_signature, timestamp, nonce):
        """
        解密消息

        Args:
            xml_text (str/bytes): 加密的XML消息
            msg_signature (str): 消息签名
            timestamp (str): 时间戳
            nonce (str): 随机数

        Returns:
            str: 解密后的XML明文，解密失败返回None
        """
        try:
            logger.info("[QYWeChat] 开始解密消息")
            logger.info(f"[QYWeChat] 收到的加密消息: {xml_text}")

            # 确保xml_text是字符串
            if isinstance(xml_text, bytes):
                xml_text = xml_text.decode('utf-8')

            result = self.crypt.decrypt_message(
                xml_text, msg_signature, timestamp, nonce)
            logger.info(f"[QYWeChat] 解密成功，消息内容: {result}")
            return result

        except CryptError as e:
            logger.error(f"[QYWeChat] 消息解密失败: [{e.error_code}] {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"[QYWeChat] 消息解密异常: {str(e)}", exc_info=True)
            return None

    def encrypt_message(self, reply_msg, nonce=None, timestamp=None):
        """
        加密回复消息

        Args:
            reply_msg (str): 回复的消息明文
            nonce (str, optional): 随机数，如果不提供则自动生成
            timestamp (str, optional): 时间戳，如果不提供则使用当前时间

        Returns:
            str: 加密后的XML消息，加密失败返回None
        """
        try:
            logger.info("[QYWeChat] 开始加密回复消息")

            result = self.crypt.encrypt_message(reply_msg, nonce, timestamp)
            logger.info("[QYWeChat] 消息加密成功")
            return result

        except CryptError as e:
            logger.error(f"[QYWeChat] 消息加密失败: [{e.error_code}] {e.error_msg}")
            return None
        except Exception as e:
            logger.error(f"[QYWeChat] 消息加密异常: {str(e)}", exc_info=True)
            return None


# 创建鉴权实例
qywechat_auth = QYWeChatAuth()
