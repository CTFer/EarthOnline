# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-05 11:53:10
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import os

# 服务器配置
SERVER_IP = '192.168.5.18'
DOMAIN = 'duonline.top'
DOMAIN_IP = '1.95.11.164'
PORT = 80
# HTTPS配置
HTTPS_ENABLED = True
SSL_CERT_PATH = os.path.join(os.path.dirname(__file__), 'cert.pem')  # SSL证书路径
SSL_KEY_PATH = os.path.join(os.path.dirname(__file__), 'private.key')   # SSL私钥路径
HTTPS_PORT = 443  # HTTPS端口号
# 环境配置 本地开发环境 local 生产环境 prod 生产环境中NFC读写卡功能关闭
ENV = 'local'
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
    'THREADS' : 4,               # 处理请求的线程数
    'CONNECTION_LIMIT' : 1000,   # 最大并发连接数
    'TIMEOUT' : 30,      # 连接超时时间（秒）
    'CLEANUP_INTERVAL': 30,     # 清理间隔（秒）
    'IDENT' : 'Game Server'      # 服务器标识
}

# 生产环境配置 用于同步数据库
PROD_SERVER = {
    'URL': DOMAIN,  # 生产环境服务器地址
    'API_KEY': '95279527',    # API认证密钥 用于同步数据库
    'TIMEOUT': 5,                      # 请求超时时间（秒）
    'RETRY': 3                         # 失败重试次数
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