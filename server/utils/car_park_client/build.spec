/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-03-28 16:08:44
 * @LastEditTime: 2025-11-09 12:58:34
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None

# 获取当前目录
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
spec_dir = os.path.dirname(SPEC)  # PyInstaller提供的SPEC变量

# 创建必要的目录结构
dist_dir = os.path.join(current_dir, 'dist', 'parking_service')
log_dir = os.path.join(dist_dir, 'logs')
Path(log_dir).mkdir(parents=True, exist_ok=True)

# 创建禁用快速编辑模式的代码文件
disable_quick_edit_code = '''
import ctypes

def disable_quick_edit():
    """禁用控制台的快速编辑模式，防止程序假死"""
    try:
        # 定义Windows API常量
        ENABLE_QUICK_EDIT_MODE = 0x0040
        ENABLE_EXTENDED_FLAGS = 0x0080
        STD_INPUT_HANDLE = -10

        # 获取控制台句柄
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(STD_INPUT_HANDLE)
        
        # 获取当前控制台模式
        mode = ctypes.c_ulong()
        kernel32.GetConsoleMode(handle, ctypes.byref(mode))
        
        # 清除快速编辑模式位
        mode.value &= ~ENABLE_QUICK_EDIT_MODE
        # 设置扩展标志位
        mode.value |= ENABLE_EXTENDED_FLAGS
        
        # 设置新的控制台模式
        kernel32.SetConsoleMode(handle, mode)
        print("[Car_Park] 已禁用控制台快速编辑模式")
        
    except Exception as e:
        print(f"[Car_Park] 禁用快速编辑模式失败: {str(e)}")

# 程序启动时禁用快速编辑模式
disable_quick_edit()
'''

disable_quick_edit_path = os.path.join(current_dir, 'disable_quick_edit.py')
with open(disable_quick_edit_path, 'w', encoding='utf-8') as f:
    f.write(disable_quick_edit_code)

# 图标文件路径
icon_path = os.path.join(current_dir, '256.ico')
if not os.path.exists(icon_path):
    icon_path = os.path.join(spec_dir, '256.ico')

# 配置文件
config_file = os.path.join(current_dir, 'config.json')
if not os.path.exists(config_file):
    config_file = os.path.join(spec_dir, 'config.json')

# 如果配置文件不存在，创建默认配置
if not os.path.exists(config_file):
    import json
    default_config = {
        "DEBUG": True,  # 调试模式默认开启，方便排查问题
        "CONFIG": {
            "review_api_url": "http://1.95.11.164/car_park/review",
            "conn_str": "DRIVER={SQL Server};SERVER=localhost;DATABASE=Park_DB;UID=sa;PWD=123",
            "sync_interval": 10,  # 同步间隔（分钟）
            "max_retries": 3,     # 最大重试次数
            "retry_interval": 5   # 重试间隔（秒）
        },
        "HEADERS": {
            "X-API-Key": "95279527"
        }
    }
    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=4, ensure_ascii=False)

# 添加数据文件
datas = [
    (disable_quick_edit_path, '.'),  # 添加禁用快速编辑模式的脚本
]

# 添加配置文件
if os.path.exists(config_file):
    datas.append((config_file, '.'))

# 添加图标文件
if os.path.exists(icon_path):
    datas.append((icon_path, '.'))

# 主程序分析
a = Analysis(
    [os.path.join(spec_dir, 'car_park_client.py'), disable_quick_edit_path],  # 添加禁用快速编辑模式的脚本
    pathex=[current_dir, spec_dir],  # 添加搜索路径
    binaries=[],
    datas=datas,
    hiddenimports=[
        # 基础依赖
        'datetime',
        'json',
        'logging',
        'os',
        're',
        'sys',
        'time',
        'ctypes',  # 添加ctypes依赖
        
        # 第三方库
        'pyodbc',           # SQL Server数据库连接
        'requests',         # HTTP请求
        'schedule',         # 定时任务
        'dateutil.relativedelta',  # 日期计算
        'urllib3',          # requests的依赖库
        
        # 标准库子模块
        'logging.handlers', # 日志处理器
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

# 打包
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# 创建主执行文件
exe = EXE(
    pyz,
    a.scripts,
    [],  # 不包含其他文件
    exclude_binaries=True,  # 排除二进制文件
    name='parking_service',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=True,  # 禁用Windows错误跟踪窗口
    target_arch=None,  # 使用当前系统架构
    codesign_identity=None,  # 不进行代码签名
    entitlements_file=None,  # 不使用授权文件
    icon=icon_path if os.path.exists(icon_path) else None,
)

# 创建分发目录，包含所有依赖和配置
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='parking_service',
)

# 打包后的目录结构说明
"""
dist/
  parking_service/
    parking_service.exe  # 主程序
    config.json         # 配置文件
    256.ico            # 图标文件（如果存在）
    disable_quick_edit.py  # 禁用快速编辑模式的脚本
    logs/              # 日志目录
    python*.dll        # Python运行时
    其他依赖文件...

注意事项：
1. 运行前确保config.json中的配置正确
2. 数据库连接字符串需要根据实际环境修改
3. 日志文件会保存在logs目录下
4. 确保程序有足够的文件读写权限
5. 默认开启调试模式，可在config.json中修改
6. 已禁用控制台快速编辑模式，防止程序假死
"""
