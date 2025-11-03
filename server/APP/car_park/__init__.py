# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-11-01 11:00:00
# LastEditTime: 2025-11-01 19:32:51
# LastEditors: 一根鱼骨棒
# Description: 停车场管理应用 - 新版
# Software: VScode
# Copyright 2025 迷舍

import os
import sys

# 添加服务器根目录到Python路径，确保能导入utils等模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from flask import Blueprint

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建新的蓝图，指定templates文件夹路径
car_park_new_bp = Blueprint('car_park_new', __name__, 
                           template_folder=os.path.join(BASE_DIR, 'templates'),
                           url_prefix='/car_park_new')  # 注意：URL前缀不包含尾部斜杠，Flask会自动处理

# 导入视图函数
from . import app

__all__ = ['car_park_new_bp']