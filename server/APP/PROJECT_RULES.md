# EarthOnline 项目规则文档

## 1. 项目概述

EarthOnline 是一个基于 Python 开发的 ARG（Alternate Reality Game，平行实境游戏）养成类应用。该项目通过将现实世界与游戏世界相结合，玩家可以通过完成游戏中的任务获得现实世界的奖励。

为了便于模块化开发和管理，项目采用了 Flask 蓝图（Blueprint）机制，在 `server/APP` 目录下存放各个独立的 Web 应用模块，这些模块通过统一的应用集成服务加载到主应用中。

## 2. 目录结构规范

### 2.1 主项目结构

```
server/
├── APP/               # 应用模块目录（所有子应用存放于此）
├── function/          # 核心功能服务目录
├── templates/         # 主应用模板目录
├── static/            # 主应用静态文件目录
├── app.py             # 主应用入口
└── ...                # 其他文件和目录
```

### 2.2 APP 模块结构

每个应用模块必须遵循以下目录结构：

```
APP/
└── 应用名称/
    ├── __init__.py        # Python 包标识文件，必须包含蓝图定义
    ├── app.py             # 应用主模块，包含路由和视图函数
    ├── templates/         # 应用模板目录
    ├── static/            # 应用静态文件目录
    ├── README.md          # 应用说明文档（推荐）
    └── ...                # 其他必要文件和目录（如 services/, models/, utils.py 等）
```

**注意事项：**
- 应用名称应使用小写字母和下划线命名，避免使用中文字符
- 每个应用必须是一个独立的 Python 包（包含 `__init__.py`）
- 模板和静态文件目录是可选的，但建议包含以保持一致性

## 3. 蓝图开发规范

### 3.1 蓝图创建方式

有两种推荐的蓝图创建方式：

#### 方式一：在 `__init__.py` 中创建蓝图

```python
# APP/应用名称/__init__.py
from flask import Blueprint
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建蓝图
应用名称_bp = Blueprint('应用名称', __name__, 
                        template_folder=os.path.join(BASE_DIR, 'templates'),
                        url_prefix='/应用名称')

# 导入视图函数
from . import app

__all__ = ['应用名称_bp']
```

```python
# APP/应用名称/app.py
from . import 应用名称_bp

@应用名称_bp.route('/')
def index():
    return 'Hello from 应用名称!'
```

#### 方式二：使用工厂函数创建蓝图

```python
# APP/应用名称/app.py
from flask import Blueprint
import os

def create_应用名称_blueprint():
    """创建应用蓝图"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    应用名称_bp = Blueprint('应用名称', __name__, 
                          url_prefix='/应用名称',
                          template_folder=os.path.join(current_dir, 'templates'),
                          static_folder=os.path.join(current_dir, 'static'))
    
    @应用名称_bp.route('/')
    def index():
        return 'Hello from 应用名称!'
    
    return 应用名称_bp

# 创建蓝图实例
应用名称_bp = create_应用名称_blueprint()
```

### 3.2 蓝图命名规范

- 蓝图名称（Blueprint 构造函数的第一个参数）：使用有意义的名称，通常与应用名称相同
- 蓝图变量名：统一使用 `应用名称_bp` 的格式
- URL 前缀：与应用名称保持一致，使用小写字母和下划线

### 3.3 路由命名规范

- 路由函数名应使用有意义的英文名称，采用小写字母和下划线分隔
- 避免使用相同的路由函数名，即使在不同的蓝图中
- 对于 API 路由，建议使用 `/api/` 前缀

### 3.4 错误处理

每个应用模块应包含基本的错误处理：

```python
@应用名称_bp.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('error.html', 
                         message='页面不存在',
                         error_code=404), 404

@应用名称_bp.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('error.html', 
                         message='服务器内部错误',
                         error_code=500), 500
```

### 3.5 独立运行模式

每个应用模块应支持独立运行，便于开发和测试：

```python
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(应用名称_bp)
    app.run(debug=True, host='127.0.0.1', port=5000)
```

## 4. 应用集成指南

### 4.1 集成方式

应用模块通过主应用中的 `AppIntegrationService` 服务集成：

1. 在 `server/app.py` 文件中的 `apps_to_integrate` 列表中添加应用配置

```python
apps_to_integrate = [
    # 现有应用配置...
    
    # 新应用配置
    {
        'app_name': '应用描述名称',      # 应用的描述性名称（用于日志）
        'app_path': 'APP/应用名称',      # 应用相对路径
        'module_name': 'app',           # 应用主模块名称（默认为'app'）
        'blueprint_name': '应用名称_bp', # 蓝图变量名
        'url_prefix': '/应用名称'        # URL前缀
    }
]
```

### 4.2 配置参数说明

| 参数名 | 类型 | 默认值 | 说明 |
|-------|------|-------|------|
| app_name | str | 必填 | 应用的描述性名称，用于日志和标识 |
| app_path | str | 必填 | 应用的相对路径或绝对路径 |
| module_name | str | 'app' | 应用的主模块名称 |
| blueprint_name | str | 'bp' | 蓝图对象的变量名 |
| url_prefix | str | None | 蓝图的URL前缀，None表示使用蓝图默认值 |
| template_dir | str | 'templates' | 应用的模板目录名 |
| static_dir | str | 'static' | 应用的静态文件目录名 |

### 4.3 集成检查清单

1. ✅ 应用目录结构符合规范
2. ✅ `__init__.py` 文件已正确创建
3. ✅ 蓝图对象已正确定义并命名
4. ✅ 已在 `apps_to_integrate` 中添加正确的配置
5. ✅ 应用支持独立运行和集成运行两种模式
6. ✅ 包含必要的错误处理
7. ✅ 静态文件和模板目录配置正确

## 5. 最佳实践

### 5.1 代码组织

- 将业务逻辑与路由处理分离，建议使用 services 目录存放业务逻辑
- 对于复杂应用，可使用子蓝图进行功能模块划分
- 使用装饰器统一处理认证、日志等横切关注点

### 5.2 数据库使用

- 每个应用模块应使用自己的数据库或表前缀，避免表名冲突
- 提供数据库初始化脚本，便于快速部署
- 使用数据库连接池或上下文管理器管理数据库连接

### 5.3 日志记录

- 使用主应用提供的日志服务（`log_service`）
- 对于独立运行模式，提供基本的日志配置
- 记录关键操作和错误信息

### 5.4 安全性

- 实现必要的认证和授权机制
- 对用户输入进行验证和过滤
- 密码存储使用安全的哈希算法

### 5.5 性能优化

- 使用缓存减少重复计算和数据库查询
- 优化静态资源加载
- 对于独立运行的应用，考虑使用生产环境服务器（如 Gunicorn、Waitress）

## 6. 示例应用分析

### 6.1 轨迹图模块（route）

- **核心功能**：提供轨迹数据的管理和展示
- **目录结构**：基础的应用结构，包含必要的模板和静态文件
- **特点**：实现了完整的认证机制和数据库操作

### 6.2 教师系统（teacher）

- **核心功能**：教师管理系统
- **目录结构**：更复杂的结构，使用子蓝图组织功能模块
- **特点**：模块化程度高，使用配置文件管理应用设置

### 6.3 停车场管理系统（car_park_new）

- **核心功能**：停车场信息管理
- **目录结构**：包含服务层和工具函数
- **特点**：实现了与企业微信的集成

### 6.4 数据库管理系统（workdata）

- **核心功能**：工作数据管理
- **特点**：专注于数据处理和统计功能

## 7. 故障排除

### 7.1 集成失败

- 检查应用路径是否正确
- 确认蓝图变量名与配置中的 `blueprint_name` 一致
- 查看日志获取具体错误信息
- 验证应用是否可以独立运行

### 7.2 模板加载问题

- 确保模板目录结构正确
- 检查模板引用路径是否使用了正确的相对路径
- 避免不同应用间的模板文件重名

### 7.3 静态资源访问问题

- 确认静态目录配置正确
- 使用蓝图提供的 `url_for('蓝图名.static', filename='资源路径')` 生成静态资源URL

## 8. 版本控制

- 应用模块的代码应遵循主项目的版本控制规范
- 重大变更应在 README.md 中记录
- 推荐使用 Git 分支进行功能开发和测试

---

本规则文档基于 EarthOnline 项目的当前架构设计，如有变更，请及时更新。