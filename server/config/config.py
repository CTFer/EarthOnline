# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-05 11:53:10
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import os

# 服务器配置
SERVER_IP = '0.0.0.0'
DOMAIN = 'duonline.top'
DOMAIN_IP = '1.95.11.164'
PORT = 8000
# 环境配置 本地开发环境 local 生产环境 prod 生产环境中NFC读写卡功能关闭
ENV = 'local'


# SSL配置目录
SSL_CERT_DIR = os.path.join(os.path.dirname(
    os.path.dirname(__file__)), 'config', 'ssl')
SSL_DEV_DIR = os.path.join(SSL_CERT_DIR, 'dev')  # 本地开发证书目录

# 本地开发HTTPS配置
LOCAL_SSL = {
    'enabled': True,  # 本地是否启用SSL
    'cert_required': False,  # 本地开发是否强制要求证书
    'adhoc': True,  # 使用临时自签名证书
    'cert_dir': SSL_DEV_DIR,  # 本地证书目录
    'cert_file': os.path.join(SSL_DEV_DIR, 'cert.pem'),  # 本地证书文件
    'key_file': os.path.join(SSL_DEV_DIR, 'key.pem')  # 本地私钥文件
}

# HTTPS配置
HTTPS_ENABLED = False  # 是否启用HTTPS
HTTPS_PORT = 443     # HTTPS端口号

# 根据环境选择证书路径
if ENV == 'local':
    SSL_CERT_FILE = LOCAL_SSL['cert_file']
    SSL_KEY_FILE = LOCAL_SSL['key_file']
else:
    # 生产环境使用 Cloudflare 证书
    SSL_CERT_FILE = os.path.join(
        SSL_CERT_DIR, 'cloudfare.pem')  # Cloudflare 证书
    SSL_KEY_FILE = os.path.join(SSL_CERT_DIR, 'domain.key')      # 私钥

# ACME验证目录（用于Let's Encrypt证书续期）
ACME_CHALLENGE_DIR = os.path.join('static', '.well-known', 'acme-challenge')

# Cloudflare配置
CLOUDFLARE = {
    'enabled': True,  # 启用Cloudflare
    'flexible_ssl': True,  # 使用Flexible SSL模式
    'proxy_fix': True,  # 启用代理修复
    'websocket': {
        'enabled': True,
        'path': '/socket.io',
        'ping_interval': 25000,
        'ping_timeout': 20000,
        'max_http_buffer_size': 1e8,
        'transports': ['websocket', 'polling'],
        'async_mode': 'eventlet',
        'logger': True,
        'engineio_logger': True,
        'always_connect': True
    },
    'headers': {
        'X-Forwarded-For': 1,
        'X-Forwarded-Proto': 1,
        'X-Forwarded-Host': 1,
        'X-Forwarded-Port': 1,
        'X-Forwarded-Prefix': 1,
        'X-Real-IP': 1
    },
    'domain_only_ssl': True  # 只对域名访问启用SSL重定向
}

# 数据库配置
DATABASE_PATH = 'database/game.db'

# 调试模式
DEBUG = True

# GPS更新精度阈值 int值
GPS_ACCURACY = 3

# GPS更新间隔 时间 秒
GPS_DURATION = 60
# GPS数据处理相关配置
GPS_CONFIG = {
    'AUTO_OPTIMIZE': True,           # 是否自动优化
    'MAX_DATA_NUMBER': 1000,         # 单次请求最大返回数据量
    'SAMPLING_THRESHOLD': 1000,      # 触发优化的数据量阈值
    'MIN_DISTANCE': 0.0001,          # 最小距离阈值（经纬度）
    'TIME_INTERVAL': 30,             # 最小时间间隔（秒）
    'SPEED_THRESHOLD': 5,            # 速度变化阈值（m/s）
    'ACCURACY_THRESHOLD': 10,        # 精度变化阈值（米）
    'MAX_OPTIMIZATION_LEVEL': 5      # 最大优化级别
}

WAITRESS_CONFIG = {
    'THREADS': 4,               # 处理请求的线程数
    'CONNECTION_LIMIT': 1000,   # 最大并发连接数
    'TIMEOUT': 30,      # 连接超时时间（秒）
    'CLEANUP_INTERVAL': 30,     # 清理间隔（秒）
    'IDENT': 'Game Server'      # 服务器标识
}

# 生产环境配置 用于同步数据库
PROD_SERVER = {
    'URL': f'https://{DOMAIN_IP}' if HTTPS_ENABLED else f'http://{DOMAIN_IP}',  # 使用IP地址
    'API_KEY': '95279527',    # API认证密钥 用于同步数据库
    'TIMEOUT': 5,             # 请求超时时间（秒）
    'RETRY': 3,              # 失败重试次数
    'SSL_VERIFY': False,     # 禁用SSL验证，因为使用IP访问
    'HEADERS': {             # 标准请求头
        'Content-Type': 'application/json',
        'X-Sync-From': 'local',
        'Host': DOMAIN       # 添加Host头以支持SSL
    }
}
# 同步时间 秒
Roadmap_SYNC_TIME = 300

# 需要同步的接口列表
SYNC_ENDPOINTS = [
    '/api/roadmap/add',
    '/api/roadmap/<id>',  # PUT/DELETE
]
# 定义任务类型
TASK_TYPE = {
    'DAILY': '每日任务',
    'MAIN': '主线任务',
    'BRANCH': '支线任务',
    'SPECIAL': '特殊任务',
}
# 任务池中的任务状态
TASK_STATUS = {
    'ACCEPT': '已接受',  # 任务已被接受
    'LOCKED': '未解锁',  # 任务未解锁
    'AVAIL': '可接受',  # 任务可接受
    'COMPLETED': '已完成',  # 任务已完成
}
# 玩家任务状态
CURRENT_TASK_STATUS = {
    'IN_PROGRESS': '进行中',  # 任务进行中
    'CHECK': '待检查',  # 玩家提交等待管理员检查
    'REJECT': '已驳回',  # 管理员驳回
    'UNFINISH': '未完成',  # 超时未完成
    'ABANDONED': '已放弃',  # 玩家主动放弃
    'COMPLETED': '已完成',  # 任务已完成
}

# 安全配置
SECURITY = {
    'open': False,
    'rate_limit': {
        'enabled': True if ENV == 'prod' else False,  # 生产环境启用速率限制
        'limit': 500,  # 每个IP每分钟最大请求数
        'window': 60   # 时间窗口（秒）
    },
    'headers': {
        'X-Frame-Options': 'SAMEORIGIN',
        'X-Content-Type-Options': 'nosniff',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    },
    'blocked_ips': [
        '0.0.0.0/8',          # 本地网络
        '10.0.0.0/8',         # 私有网络
        '127.0.0.0/8',        # 环回地址
        '169.254.0.0/16',     # 链路本地
        '172.16.0.0/12',      # 私有网络
        '192.168.0.0/16',     # 私有网络
        '224.0.0.0/4',        # 多播
        '240.0.0.0/4'         # 保留地址
    ],
    'white_ips': [
        "183.47.100.66",
        "183.47.102.153",
        "157.148.55.111",
        "157.148.41.225",
        "120.233.17.190",
        "120.241.149.189",
        "42.194.252.200",
        "42.194.252.76",
        "101.91.40.24",
        "101.226.141.58",
        "210.22.244.32",
        "140.206.161.227",
        "117.135.156.58",
        "117.185.253.167",
        "81.69.54.213", "81.69.87.29", "43.135.106.227", "43.135.106.8"  # 企业微信API
    ],
    'allowed_file_types': [
        '.jpg', '.jpeg', '.png', '.gif', '.ico',
        '.css', '.js', '.map',
        '.html', '.htm',
        '.woff', '.woff2', '.ttf', '.eot', '.svg',
        '.pdf', '.txt'
    ]
}
