"""
服务器管理模块
处理HTTP/HTTPS服务器的配置和管理
"""
import os
import ssl
import logging
import threading
import eventlet
from flask import Flask, send_from_directory
from flask_cors import CORS
from typing import Optional, Tuple
from config.config import (
    SERVER_IP,
    PORT,
    DEBUG,
    HTTPS_PORT,
    HTTPS_ENABLED,
    ENV,
    LOCAL_SSL,
    SSL_CERT_DIR,
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    DOMAIN,
    CLOUDFLARE
)

logger = logging.getLogger(__name__)

class ServerService:
    """服务器管理类"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ServerService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """初始化服务器管理服务"""
        if not hasattr(self, 'initialized'):
            self.http_thread = None
            self.is_running = False
            self.initialized = True
            
    def setup_ssl(self, ssl_dir: str) -> Tuple[bool, Optional[ssl.SSLContext]]:
        """
        配置SSL上下文
        
        Args:
            ssl_dir: SSL证书目录路径
            
        Returns:
            Tuple[bool, Optional[ssl.SSLContext]]: (是否成功, SSL上下文)
        """
        try:
            # 确保证书目录存在
            if not os.path.exists(ssl_dir):
                os.makedirs(ssl_dir)
                logger.info(f"创建SSL目录: {ssl_dir}")

            # 本地开发环境使用自签名证书
            if ENV == 'local':
                logger.info("[SSL] 本地开发环境，使用自签名证书")
                # 确保dev目录存在
                dev_dir = os.path.join(ssl_dir, 'dev')
                if not os.path.exists(dev_dir):
                    os.makedirs(dev_dir)
                    logger.info(f"[SSL] 创建本地开发证书目录: {dev_dir}")

                # 创建SSL上下文
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                # 禁用证书验证
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # 如果需要自签名证书
                if LOCAL_SSL['adhoc']:
                    try:
                        from OpenSSL import crypto
                        # 创建自签名证书
                        key = crypto.PKey()
                        key.generate_key(crypto.TYPE_RSA, 2048)
                        
                        cert = crypto.X509()
                        cert.get_subject().CN = "localhost"
                        cert.set_serial_number(1000)
                        cert.gmtime_adj_notBefore(0)
                        cert.gmtime_adj_notAfter(365*24*60*60)  # 1年有效期
                        cert.set_issuer(cert.get_subject())
                        cert.set_pubkey(key)
                        cert.sign(key, 'sha256')
                        
                        # 保存证书和私钥到dev目录
                        cert_file = os.path.join(dev_dir, 'cert.pem')
                        key_file = os.path.join(dev_dir, 'key.pem')
                        
                        with open(cert_file, "wb") as f:
                            f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
                        with open(key_file, "wb") as f:
                            f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, key))
                            
                        logger.info("[SSL] 已生成本地开发用的自签名证书")
                        
                        # 使用新生成的证书和私钥
                        ssl_context.load_cert_chain(
                            certfile=cert_file,
                            keyfile=key_file
                        )
                        logger.info("[SSL] 本地证书加载成功")
                        return True, ssl_context
                        
                    except ImportError:
                        # 直接安装pyOpenSSL
                        try:
                            os.system("pip install pyOpenSSL")
                            from OpenSSL import crypto
                            # 重试证书生成
                            return self.setup_ssl(ssl_dir)
                        except Exception as e:
                            logger.error(f"[SSL] 安装pyOpenSSL失败: {str(e)}")
                            return False, None
                    except Exception as e:
                        logger.error(f"[SSL] 生成自签名证书失败: {str(e)}")
                        return False, None
                
                # 如果不需要自签名证书，使用已有的证书
                try:
                    ssl_context.load_cert_chain(
                        certfile=LOCAL_SSL['cert_file'],
                        keyfile=LOCAL_SSL['key_file']
                    )
                    logger.info("[SSL] 本地证书加载成功")
                except Exception as e:
                    logger.error(f"[SSL] 加载本地证书失败: {str(e)}")
                    return False, None
                
                return True, ssl_context
            
            # 生产环境使用Cloudflare证书
            else:
                logger.info("[SSL] 生产环境，使用Cloudflare证书")
                
                # 检查证书文件是否存在
                if not os.path.exists(SSL_CERT_FILE) or not os.path.exists(SSL_KEY_FILE):
                    logger.error("[SSL] Cloudflare证书文件不存在")
                    logger.error(f"[SSL] cloudfare.pem: {os.path.exists(SSL_CERT_FILE)}")
                    logger.error(f"[SSL] domain.key: {os.path.exists(SSL_KEY_FILE)}")
                    return False, None

                # 创建SSL上下文
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                
                # 配置SSL选项
                ssl_context.options |= ssl.OP_NO_SSLv2
                ssl_context.options |= ssl.OP_NO_SSLv3
                ssl_context.options |= ssl.OP_NO_TLSv1
                ssl_context.options |= ssl.OP_NO_TLSv1_1
                ssl_context.options |= ssl.OP_CIPHER_SERVER_PREFERENCE
                
                # 设置密码套件
                ssl_context.set_ciphers('ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384')
                
                # 加载证书
                try:
                    ssl_context.load_cert_chain(
                        certfile=SSL_CERT_FILE,  # 使用Cloudflare证书
                        keyfile=SSL_KEY_FILE,    # 使用私钥
                        password=None
                    )
                    logger.info("[SSL] Cloudflare证书加载成功")
                    
                    # 验证证书和私钥是否匹配
                    try:
                        ssl_context.get_ca_certs()
                        logger.info("[SSL] 证书和私钥匹配验证成功")
                    except ssl.SSLError as e:
                        logger.error(f"[SSL] 证书和私钥不匹配: {str(e)}")
                        return False, None
                        
                    return True, ssl_context
                    
                except Exception as e:
                    logger.error(f"[SSL] 加载Cloudflare证书失败: {str(e)}")
                    return False, None
            
        except Exception as e:
            logger.error(f"[SSL] SSL配置失败: {str(e)}")
            return False, None

    def run_http_server(self, app: Flask) -> None:
        """
        运行HTTP服务器
        
        Args:
            app: Flask应用实例
        """
        try:
            # 创建一个新的Flask应用实例，只用于HTTP
            http_app = Flask(__name__, static_folder='static')
            CORS(http_app)
            
            # 只注册需要HTTP访问的路由
            @http_app.route('/.well-known/acme-challenge/<path:path>')
            def acme_challenge(path):
                """Let's Encrypt验证接口"""
                try:
                    challenge_dir = os.path.join(app.static_folder, '.well-known', 'acme-challenge')
                    return send_from_directory(challenge_dir, path)
                except Exception as e:
                    logger.error(f"ACME challenge失败: {str(e)}")
                    return str(e), 404

            # 启动HTTP服务器
            logger.info(f"启动HTTP服务器，端口 {PORT}")
            http_app.run(
                host=SERVER_IP,
                port=PORT,
                debug=False,  # HTTP服务器不需要debug模式
                use_reloader=False  # 禁用reloader以避免与HTTPS服务器冲突
            )
        except Exception as e:
            logger.error(f"HTTP服务器启动失败: {str(e)}")

    def _run_socketio_server(self, app: Flask, socketio) -> None:
        """
        运行SocketIO服务器
        
        Args:
            app: Flask应用实例
            socketio: SocketIO实例
        """
        try:
            # 基础配置
            server_config = {
                'host': SERVER_IP,
                'port': PORT,
                'debug': DEBUG,
                'use_reloader': False,
                'log_output': True if ENV == 'local' else False
            }

            # HTTPS模式配置
            if ENV == 'local' and HTTPS_ENABLED:
                # 本地开发环境使用自签名证书
                ssl_success, ssl_context = self.setup_ssl(SSL_CERT_DIR)
                if ssl_success:
                    server_config.update({
                        'port': HTTPS_PORT,  # 使用HTTPS端口
                        'ssl_context': ssl_context
                    })
                else:
                    # 如果SSL配置失败，回退到HTTP
                    logger.warning("SSL配置失败，回退到HTTP模式")
                    server_config['port'] = PORT + 1  # 使用不同的端口避免冲突

            logger.info(f"[SocketIO] 服务器配置: {server_config}")
            
            # 启动服务器
            socketio.run(app, **server_config)

        except Exception as e:
            logger.error(f"启动SocketIO服务器失败: {str(e)}")
            raise

    def start_server(self, app: Flask, socketio) -> None:
        """
        启动服务器（HTTP和/或HTTPS）
        
        Args:
            app: Flask应用实例
            socketio: SocketIO实例
        """
        try:
            if HTTPS_ENABLED:
                # 在新线程中启动HTTP服务器
                self.http_thread = threading.Thread(target=self.run_http_server, args=(app,))
                self.http_thread.daemon = True
                self.http_thread.start()
                logger.info("HTTP服务器线程已启动")

                # 主线程运行HTTPS服务器
                ssl_success, ssl_context = self.setup_ssl(SSL_CERT_DIR)
                
                if ssl_success:
                    try:
                        # 创建socket并包装SSL
                        sock = eventlet.listen((SERVER_IP, HTTPS_PORT))
                        ssl_sock = ssl_context.wrap_socket(sock, server_side=True)
                        
                        logger.info(f"启动HTTPS服务器，端口 {HTTPS_PORT}")
                        eventlet.wsgi.server(ssl_sock, app)
                    except Exception as e:
                        logger.error(f"HTTPS服务器启动失败，回退到HTTP模式: {str(e)}")
                        self._run_socketio_server(app, socketio)
                else:
                    logger.info("回退到仅HTTP模式...")
                    self._run_socketio_server(app, socketio)
            else:
                # 仅启动HTTP服务器
                self._run_socketio_server(app, socketio)
                
        except Exception as e:
            logger.error(f"服务器启动失败: {str(e)}")
            raise

    def stop(self) -> None:
        """停止服务器"""
        if self.http_thread and self.http_thread.is_alive():
            # 在这里可以添加清理代码
            logger.info("正在停止HTTP服务器...")
            
        logger.info("服务器已停止")

# 创建服务器管理实例
server_service = ServerService() 