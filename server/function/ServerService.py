"""
服务器管理模块
处理HTTP/HTTPS服务器的配置和管理
"""
import os
import ssl
import logging
import threading
import socket
import eventlet
from datetime import datetime, time,timedelta
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
    SSL_CERT_DIR,
    SSL_CERT_FILE,
    SSL_KEY_FILE,
    DOMAIN
)

logger = logging.getLogger(__name__)

def acme_challenge(app, path):
    """
    Let's Encrypt验证接口
    处理ACME挑战验证请求
    
    Args:
        app: Flask应用实例
        path: ACME挑战令牌路径
        
    Returns:
        文件内容或错误响应
    """
    try:
        # 确保静态目录存在
        if not hasattr(app, 'static_folder') or not app.static_folder:
            logger.error("ACME challenge失败: 应用实例没有static_folder属性")
            return "静态目录配置错误", 500
            
        # 构建ACME挑战目录路径
        challenge_dir = os.path.join(app.static_folder, '.well-known', 'acme-challenge')
        
        # 确保ACME挑战目录存在
        if not os.path.exists(challenge_dir):
            try:
                os.makedirs(challenge_dir)
                logger.info(f"创建ACME挑战目录: {challenge_dir}")
            except Exception as e:
                logger.error(f"创建ACME挑战目录失败: {str(e)}")
                return f"创建验证目录失败: {str(e)}", 500
        
        # 检查文件是否存在
        challenge_file = os.path.join(challenge_dir, path)
        if not os.path.exists(challenge_file):
            logger.error(f"ACME挑战文件不存在: {challenge_file}")
            return "验证文件不存在", 404
        
        # 读取并返回验证文件
        return send_from_directory(challenge_dir, path)
    except Exception as e:
        logger.error(f"ACME challenge处理失败: {str(e)}")
        return f"验证失败: {str(e)}", 500

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
            self.initialized = True
            self.http_server = None
            self.https_server = None
            self.server_thread = None
            
            # 配置日志
            self.logger = logging.getLogger(__name__)
            
            # 初始化服务器状态
            self.running = False
            self.ssl_context = None
            
            # 配置eventlet
            eventlet.monkey_patch()
            # 优化wsgi参数
            wsgi.MAX_HEADER_LINE = 65536  # 增加最大请求头大小
            wsgi.MINIMUM_CHUNK_SIZE = 16384  # 优化块大小
            wsgi.MAX_REQUEST_LINE = 16384  # 优化请求行大小

    def configure_app(self, app):
        """配置 Flask 应用"""
        # 设置 secret_key
        app.secret_key = '8b8d3a9e2e7c4f5e9d3a8b7c6d5e4f3a'  # 固定 secret_key
        
        # 清除任何现有配置
        for key in list(app.config.keys()):
            if key.startswith('SESSION_'):
                app.config.pop(key, None)
        
        # 设置基本配置
        app.config.update(
            # Session 配置
            SESSION_COOKIE_NAME="earthonline_session",  # 自定义 cookie 名称
            SESSION_COOKIE_DOMAIN=None,       # 确保在 IP 地址下也能工作
            SESSION_COOKIE_SECURE=False,      # 确保在 HTTP 下也能工作
            SESSION_COOKIE_HTTPONLY=True,     # 防止 JavaScript 访问
            SESSION_COOKIE_SAMESITE=None,     # 允许跨站请求
            SESSION_COOKIE_PATH='/',          # 应用于所有路径
            SESSION_TYPE='filesystem',        # 使用文件系统存储 session
            SESSION_PERMANENT=True,           # 使会话持久化
            SESSION_COOKIE_PARTITIONED=False, # Flask 2.3.0+ 需要这个配置项
            PERMANENT_SESSION_LIFETIME=timedelta(days=7),  # session 有效期7天
            SESSION_REFRESH_EACH_REQUEST=True,# 每次请求都刷新 session
            SESSION_USE_SIGNER=False,         # 不使用签名器
            
            # 应用配置
            MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 最大请求体大小50MB
            JSONIFY_PRETTYPRINT_REGULAR=False,    # 禁用JSON美化
            JSON_SORT_KEYS=False,                 # 禁用JSON键排序
            PROPAGATE_EXCEPTIONS=True,            # 传播异常
            TRAP_HTTP_EXCEPTIONS=True,            # 捕获HTTP异常
            TRAP_BAD_REQUEST_ERRORS=True,         # 捕获错误请求
            PREFERRED_URL_SCHEME='http'           # 默认为 HTTP 协议
        )
        
        # 配置 CORS - 确保支持 cookies
        CORS(app, 
            supports_credentials=True,   # 确保凭据支持
            origins="*",                # 允许所有来源
            allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            max_age=3600               # 预检请求缓存1小时
        )
        
    
        # 打印配置信息
        self.logger.info(f"[Server] 配置应用完成，Session配置: SESSION_COOKIE_NAME={app.config.get('SESSION_COOKIE_NAME')}, SESSION_COOKIE_DOMAIN={app.config.get('SESSION_COOKIE_DOMAIN')}, SESSION_COOKIE_SECURE={app.config.get('SESSION_COOKIE_SECURE')}, SESSION_COOKIE_SAMESITE={app.config.get('SESSION_COOKIE_SAMESITE')}, SESSION_COOKIE_PARTITIONED={app.config.get('SESSION_COOKIE_PARTITIONED')}")
        
        return app

    def setup_ssl(self, ssl_dir: str) -> Tuple[bool, Optional[ssl.SSLContext]]:
        """配置SSL上下文 - 简化版"""
        try:
            # 创建SSL上下文
            ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            
            # 基础SSL安全配置
            ssl_context.options |= (
                ssl.OP_NO_COMPRESSION |  # 禁用压缩以减少CPU开销
                ssl.OP_NO_RENEGOTIATION   # 禁用重新协商以提高安全性
            )
            
            # 设置安全的密码套件
            ssl_context.set_ciphers('DEFAULT@SECLEVEL=2')
            
            if ENV == 'local':
                # 本地环境配置
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                logger.info("[SSL] 本地开发环境，使用简化SSL配置")
                
                # 使用配置文件中指定的本地证书路径
                cert_file = SSL_CERT_FILE
                key_file = SSL_KEY_FILE
                
                # 确保证书目录存在
                cert_dir = os.path.dirname(cert_file)
                if not os.path.exists(cert_dir):
                    os.makedirs(cert_dir)
                    logger.info(f"[SSL] 创建证书目录: {cert_dir}")
                
                # 如果本地证书不存在，生成简单的自签名证书
                if not (os.path.exists(cert_file) and os.path.exists(key_file)):
                    logger.info("[SSL] 本地证书不存在，生成自签名证书")
                    try:
                        # 使用Python标准库生成简单证书
                        from cryptography import x509
                        from cryptography.x509.oid import NameOID
                        from cryptography.hazmat.primitives import hashes
                        from cryptography.hazmat.primitives.asymmetric import rsa
                        from cryptography.hazmat.primitives import serialization
                        from cryptography.hazmat.backends import default_backend
                        import datetime
                        
                        # 生成私钥
                        private_key = rsa.generate_private_key(
                            public_exponent=65537,
                            key_size=2048,
                            backend=default_backend()
                        )
                        
                        # 生成证书
                        subject = issuer = x509.Name([
                            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
                        ])
                        cert = x509.CertificateBuilder().subject_name(
                            subject
                        ).issuer_name(
                            issuer
                        ).public_key(
                            private_key.public_key()
                        ).serial_number(
                            x509.random_serial_number()
                        ).not_valid_before(
                            datetime.datetime.utcnow()
                        ).not_valid_after(
                            datetime.datetime.utcnow() + datetime.timedelta(days=365)
                        ).add_extension(
                            x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
                            critical=False,
                        ).sign(private_key, hashes.SHA256(), default_backend())
                        
                        # 保存证书和私钥
                        with open(cert_file, 'wb') as f:
                            f.write(cert.public_bytes(serialization.Encoding.PEM))
                        with open(key_file, 'wb') as f:
                            f.write(private_key.private_bytes(
                                encoding=serialization.Encoding.PEM,
                                format=serialization.PrivateFormat.TraditionalOpenSSL,
                                encryption_algorithm=serialization.NoEncryption()
                            ))
                            
                        logger.info(f"[SSL] 已生成本地自签名证书: {cert_file}")
                    except Exception as e:
                        logger.warning(f"[SSL] 生成自签名证书失败，将使用简单配置: {str(e)}")
            
            # 加载证书（生产环境和本地环境共用）
            try:
                ssl_context.load_cert_chain(
                    certfile=SSL_CERT_FILE,
                    keyfile=SSL_KEY_FILE
                )
                logger.info(f"[SSL] 证书加载成功: {SSL_CERT_FILE}")
                return True, ssl_context
            except Exception as e:
                logger.error(f"[SSL] 证书加载失败: {str(e)}")
                return False, None
                
        except Exception as e:
            logger.error(f"[SSL] SSL配置失败: {str(e)}")
            return False, None

    def run_http_server(self, app: Flask, ssl_context=None) -> None:
        """
        运行HTTP/HTTPS服务器，优化SSE长连接处理
        
        Args:
            app: Flask应用实例
            ssl_context: SSL上下文对象，如果启用HTTPS
        """
        try:
            # 使用eventlet的wsgi服务器启动，避免重复启动问题
            # 确保在传入的app上注册ACME挑战路由（如果需要）
            if not hasattr(app, '_acme_route_registered'):
                @app.route('/.well-known/acme-challenge/<path:path>')
                def http_acme_challenge(path):
                    """Let's Encrypt验证接口，调用模块级别的acme_challenge函数"""
                    return acme_challenge(app, path)
                app._acme_route_registered = True

            # 根据是否启用HTTPS选择端口
            port = HTTPS_PORT if HTTPS_ENABLED else PORT
            
            # 创建工作线程池，优化SSE连接处理
            pool = eventlet.GreenPool(2000)  # 适合处理大量SSE长连接
            
            # 创建socket，增加backlog以支持更多并发连接
            sock = listen(
                (SERVER_IP, port),
                backlog=4096  # 增加backlog以支持更多连接请求
            )
            
            # 设置socket选项以优化长连接性能
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # 启用keepalive
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 启用TCP_NODELAY
            
            # 如果提供了SSL上下文，应用它到socket
            if ssl_context and HTTPS_ENABLED:
                sock = ssl_context.wrap_socket(sock, server_side=True)
                logger.info("SSL配置完成")
            
            protocol = 'https' if HTTPS_ENABLED else 'http'
            logger.info(f"服务器启动于 {protocol}://{SERVER_IP}:{port}")
            logger.info(f"SSE优化配置：工作线程池大小=2000，backlog=4096，保持连接超时=30秒")
            
            # 使用eventlet的wsgi.server启动服务器，优化SSE长连接处理
            wsgi.server(
                sock,
                app,
                custom_pool=pool,  # 使用自定义线程池
                log_output=True,
                socket_timeout=30,
                keepalive=30,  # 设置keepalive以避免连接过早断开
                max_size=20000  # 增加最大连接数
            )
        except Exception as e:
            logger.error(f"服务器启动失败: {str(e)}", exc_info=True)
            raise RuntimeError(f"服务器启动失败: {str(e)}")

    # 注意：SSE不需要单独的服务器实现，直接使用标准HTTP长连接即可
    # 移除了_run_sse_server方法，统一使用run_http_server方法，因为SSE基于标准HTTP协议

    def start_server(self, app: Flask) -> None:
        """启动服务器（HTTP或HTTPS），使用SSE模式"""
        try:
            # 配置应用
            app = self.configure_app(app)
            self.logger.info(f"[Server] 应用配置完成，Session配置：{app.config.get('SESSION_COOKIE_DOMAIN')}, {app.config.get('SESSION_COOKIE_SECURE')}")
            
            # 准备服务器配置
            server_config = {
                'host': SERVER_IP,
                'port': HTTPS_PORT if HTTPS_ENABLED else PORT,
                'debug': DEBUG,
                'use_reloader': False,
                'log_output': True,
                'max_connections': 5000,
                'backlog': 4096,
                'worker_connections': 20000,
                'keepalive_timeout': 30,
                'client_max_body_size': '50M'
            }
            
            # 如果启用HTTPS，获取SSL配置
            if HTTPS_ENABLED:
                ssl_success, ssl_context = self.setup_ssl(SSL_CERT_DIR)
                
                if not ssl_success:
                    logger.error("SSL配置失败，服务器将退出")
                    raise RuntimeError("SSL配置失败")
                
                # 添加SSL上下文到服务器配置
                server_config['ssl_context'] = ssl_context
                logger.info(f"[Server] HTTPS配置完成，端口: {HTTPS_PORT}")
            else:
                logger.info(f"[Server] HTTP配置完成，端口: {PORT}")
            
            # 检查端口是否被占用
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)  # 启用keepalive
            s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # 启用TCP_NODELAY
            try:
                s.bind((SERVER_IP, server_config['port']))
                s.close()
                
                # 启动服务器 - 使用SSE模式
                protocol = 'HTTPS' if HTTPS_ENABLED else 'HTTP'
                logger.info(f"启动{protocol}服务器，端口 {server_config['port']}")
                logger.info("使用HTTP服务器启动（SSE基于标准HTTP协议）")
                
                # SSE基于标准HTTP协议，直接使用run_http_server方法即可
                # 获取SSL上下文（如果启用了HTTPS）
                ssl_context = server_config.get('ssl_context') if HTTPS_ENABLED else None
                self.run_http_server(app, ssl_context=ssl_context)
                
            except Exception as e:
                logger.error(f"端口 {server_config['port']} 被占用: {str(e)}")
                s.close()
                raise RuntimeError(f"端口 {server_config['port']} 被占用")
                
        except Exception as e:
            logger.error(f"服务器启动失败: {str(e)}")
            raise

    def stop(self) -> None:
        """停止服务器"""
        # 由于使用eventlet的wsgi.server()，不需要单独的线程管理
        logger.info("正在停止服务器...")
        logger.info("服务器已停止")

# 创建服务器管理实例
server_service = ServerService()