"""
服务器管理模块
处理HTTP/HTTPS服务器的配置和管理
"""
import os
import ssl
import logging
import threading
import eventlet
from eventlet import wsgi
from eventlet import listen
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
            
            # 配置eventlet
            eventlet.monkey_patch()
            # 优化wsgi参数
            wsgi.MAX_HEADER_LINE = 65536  # 增加最大请求头大小
            wsgi.MINIMUM_CHUNK_SIZE = 16384  # 优化块大小
            wsgi.MAX_REQUEST_LINE = 16384  # 优化请求行大小

    def setup_ssl(self, ssl_dir: str) -> Tuple[bool, Optional[ssl.SSLContext]]:
        """配置SSL上下文"""
        try:
            # 创建SSL上下文
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # 优化 SSL 配置
            ssl_context.options |= (
                ssl.OP_NO_COMPRESSION |  # 禁用压缩以减少CPU开销
                ssl.OP_NO_RENEGOTIATION |  # 禁用重新协商以提高安全性
                ssl.OP_CIPHER_SERVER_PREFERENCE |  # 使用服务器的密码套件优先级
                ssl.OP_SINGLE_DH_USE |  # 每次连接使用新的DH密钥
                ssl.OP_CIPHER_SERVER_PREFERENCE  # 使用服务器的密码套件优先级
            )
            
            # 设置现代密码套件，按优先级排序
            ssl_context.set_ciphers(
                'ECDHE-ECDSA-AES256-GCM-SHA384:'
                'ECDHE-RSA-AES256-GCM-SHA384:'
                'ECDHE-ECDSA-CHACHA20-POLY1305:'
                'ECDHE-RSA-CHACHA20-POLY1305:'
                'ECDHE-ECDSA-AES128-GCM-SHA256:'
                'ECDHE-RSA-AES128-GCM-SHA256'
            )
            
            # 设置DH参数
            ssl_context.set_ecdh_curve('prime256v1')  # 使用更快的椭圆曲线

            if ENV == 'local':
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                # 本地开发环境使用自签名证书
                logger.info("[SSL] 本地开发环境，使用自签名证书")
                # 确保dev目录存在
                dev_dir = os.path.join(ssl_dir, 'dev')
                if not os.path.exists(dev_dir):
                    os.makedirs(dev_dir)
                    logger.info(f"[SSL] 创建本地开发证书目录: {dev_dir}")
                
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
                    return True, ssl_context
                except Exception as e:
                    logger.error(f"[SSL] 加载本地证书失败: {str(e)}")
                    return False, None
            
            # 生产环境配置
            else:
                logger.info("[SSL] 生产环境，使用正式证书")
                try:
                    ssl_context.load_cert_chain(
                        certfile=SSL_CERT_FILE,
                        keyfile=SSL_KEY_FILE
                    )
                    logger.info("[SSL] 证书加载成功")
                    return True, ssl_context
                except Exception as e:
                    logger.error(f"[SSL] 证书加载失败: {str(e)}")
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
                debug=True,  # HTTP服务器不需要debug模式
                use_reloader=True  # 禁用reloader以避免与HTTPS服务器冲突
            )
        except Exception as e:
            logger.error(f"HTTP服务器启动失败: {str(e)}")

    def _run_socketio_server(self, app: Flask, socketio, **config) -> None:
        """
        运行SocketIO服务器
        
        Args:
            app: Flask应用实例
            socketio: SocketIO实例
            config: 服务器配置参数
        """
        try:
            # 基础配置
            server_config = {
                'host': SERVER_IP,
                'port': PORT,
                'debug': DEBUG,
                'use_reloader': False,  # 禁用reloader提高性能
                'log_output': True,
                'max_connections': 5000,  # 增加最大连接数
                'backlog': 4096,  # 增加等待队列
                'worker_connections': 20000,  # 增加工作连接数
                'keepalive_timeout': 30,  # 减少keepalive超时
                'client_max_body_size': '50M'  # 增加最大请求体大小
            }
            
            # 更新配置
            if config:
                server_config.update(config)

            # SocketIO配置
            socketio_config = {
                'cors_allowed_origins': '*',
                'async_mode': 'eventlet',
                'ping_timeout': 10,
                'ping_interval': 25,
                'max_http_buffer_size': 10e6,
                'manage_session': False,
                'transports': ['websocket'],
                'http_compression': True,
                'websocket_compression': True,
                'always_connect': True,
                'async_handlers': True
            }

            # 如果启用了Cloudflare，添加websocket配置
            if CLOUDFLARE['enabled'] and CLOUDFLARE['websocket']:
                socketio_config.update({
                    'path': CLOUDFLARE['websocket'].get('path', '/socket.io'),
                    'transports': ['websocket']
                })
            # HTTPS模式配置
            # if ENV == 'local' and HTTPS_ENABLED:
            #     # 本地开发环境使用自签名证书
            #     ssl_success, ssl_context = self.setup_ssl(SSL_CERT_DIR)
            #     if ssl_success:
            #         server_config.update({
            #             'port': HTTPS_PORT,
            #             'ssl_context': ssl_context,
            #             'ssl_version': ssl.PROTOCOL_TLSv1_2,  # 使用TLS 1.2
            #             'ciphers': 'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384'  # 高性能密码套件
            #         })
            #     else:
            #         logger.warning("SSL配置失败，回退到HTTP模式")
            #         server_config['port'] = PORT + 1

            logger.info(f"[SocketIO] 服务器配置: {server_config}")
            logger.info(f"[SocketIO] SocketIO配置: {socketio_config}")
            
            # 更新SocketIO配置
            for key, value in socketio_config.items():
                if hasattr(socketio, key):
                    setattr(socketio, key, value)
            
            # 创建更大的eventlet工作线程池
            pool = eventlet.GreenPool(2000)
            
            # 启动服务器
            sock = listen(
                (server_config['host'], server_config['port']), 
                backlog=server_config['backlog']
            )
            
            # 如果是HTTPS模式，包装socket
            if 'ssl_context' in server_config:
                logger.info(f"正在配置HTTPS socket，端口: {server_config['port']}")
                sock = server_config['ssl_context'].wrap_socket(sock, server_side=True)
                logger.info("HTTPS socket配置完成")
            
            protocol = 'https' if 'ssl_context' in server_config else 'http'
            logger.info(f"服务器启动于 {protocol}://{server_config['host']}:{server_config['port']}")
            
            # 使用工作线程池处理请求
            wsgi.server(
                sock,
                app,
                custom_pool=pool,
                log_output=server_config['log_output'],
                max_size=server_config['worker_connections'],
                keepalive=server_config['keepalive_timeout'],
                socket_timeout=30  # 设置socket超时
            )

        except Exception as e:
            logger.error(f"启动SocketIO服务器失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"启动SocketIO服务器失败: {str(e)}")

    def start_server(self, app: Flask, socketio) -> None:
        """启动服务器（HTTP或HTTPS）"""
        try:
            if HTTPS_ENABLED:
                # 获取SSL配置
                ssl_success, ssl_context = self.setup_ssl(SSL_CERT_DIR)
                
                if not ssl_success:
                    logger.error("SSL配置失败，服务器将退出")
                    raise RuntimeError("SSL配置失败")
                
                try:
                    # 配置HTTPS服务器
                    server_config = {
                        'host': SERVER_IP,
                        'port': HTTPS_PORT,
                        'debug': DEBUG,
                        'use_reloader': False,
                        'log_output': True,
                        'max_connections': 5000,
                        'backlog': 4096,
                        'worker_connections': 20000,
                        'keepalive_timeout': 30,
                        'client_max_body_size': '50M',
                        'ssl_context': ssl_context
                    }
                    
                    # 创建HTTPS服务器
                    try:
                        # 先尝试关闭可能占用的端口
                        import socket
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # 启用keepalive
                        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 启用TCP_NODELAY
                        try:
                            s.bind((SERVER_IP, HTTPS_PORT))
                            s.close()
                            
                            # 启动HTTPS服务器
                            logger.info(f"启动HTTPS服务器，端口 {HTTPS_PORT}")
                            self._run_socketio_server(app, socketio, **server_config)
                            
                        except Exception as e:
                            logger.error(f"HTTPS端口 {HTTPS_PORT} 被占用: {str(e)}")
                            s.close()
                            raise RuntimeError(f"HTTPS端口 {HTTPS_PORT} 被占用")
                        
                    except Exception as e:
                        logger.error(f"HTTPS服务器启动失败: {str(e)}")
                        raise RuntimeError("HTTPS服务器启动失败")
                
                except Exception as e:
                    logger.error(f"配置HTTPS服务器失败: {str(e)}")
                    raise RuntimeError("配置HTTPS服务器失败")
            
            else:
                # 仅HTTP模式
                try:
                    # 先尝试关闭可能占用的端口
                    import socket
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # 启用keepalive
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 启用TCP_NODELAY
                    try:
                        s.bind((SERVER_IP, PORT))
                        s.close()
                        
                        # 启动HTTP服务器
                        logger.info(f"启动HTTP服务器，端口 {PORT}")
                        self._run_socketio_server(app, socketio)
                        
                    except Exception as e:
                        logger.error(f"HTTP端口 {PORT} 被占用: {str(e)}")
                        s.close()
                        raise RuntimeError(f"HTTP端口 {PORT} 被占用")
                    
                except Exception as e:
                    logger.error(f"HTTP服务器启动失败: {str(e)}")
                    raise RuntimeError("HTTP服务器启动失败")
            
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