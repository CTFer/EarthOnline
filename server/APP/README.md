# APP模块整合说明

## 概述

本项目已成功将教师系统和轨迹图模块整合到APP目录下，并作为蓝图引入到主程序中。

## 目录结构

```
server/APP/
├── route/                    # 轨迹图模块
│   ├── app.py               # 轨迹图蓝图
│   ├── templates/           # 轨迹图模板
│   ├── static/              # 轨迹图静态文件
│   └── data.sqlite3         # 轨迹图数据库
├── teacher/                 # 教师系统模块
│   ├── app.py               # 教师系统蓝图
│   ├── config.py            # 教师系统配置
│   ├── database/            # 教师系统数据库
│   ├── models/               # 数据模型
│   ├── routes/              # 路由模块
│   ├── services/            # 业务服务
│   ├── templates/           # 教师系统模板
│   └── static/              # 教师系统静态文件
└── README.md                # 本说明文档
```

## 模块功能

### 1. 轨迹图模块 (route)

**功能**: 提供轨迹图展示和管理功能

**访问地址**:
- 首页: `http://localhost:5000/route/`
- 城市列表: `http://localhost:5000/route/getCityList`
- 城市坐标: `http://localhost:5000/route/getCity`
- 路线数据: `http://localhost:5000/route/getRoute`
- 添加路线: `http://localhost:5000/route/add`
- 路线列表: `http://localhost:5000/route/list`

**主要特性**:
- 支持城市坐标管理
- 支持路线轨迹记录
- 提供RESTful API接口
- 使用SQLite数据库存储

### 2. 教师系统模块 (teacher)

**功能**: 提供完整的教师管理系统

**访问地址**:
- 教师管理: `http://localhost:5000/teacher/admin/login`
- 学生入口: `http://localhost:5000/teacher/student/login`
- 公共展示: `http://localhost:5000/teacher/public/`
- API接口: `http://localhost:5000/teacher/api/`

**主要特性**:
- 教师账户管理
- 学生信息管理
- 班级管理
- 教学材料管理
- 作业布置和批改
- 活动管理
- 课程管理
- 文件上传和管理

## 技术实现

### 蓝图架构

所有模块都使用Flask蓝图(Blueprint)架构，确保模块化和可维护性：

```python
# 轨迹图蓝图
route_bp = Blueprint('route', __name__, 
                    template_folder="templates", 
                    static_folder="static",
                    url_prefix='/route')

# 教师系统蓝图
teacher_bp = Blueprint('teacher', __name__, 
                      template_folder='templates',
                      static_folder='static',
                      url_prefix='/teacher')
```

### 数据库设计

**轨迹图数据库**:
- 使用SQLite数据库
- 包含城市表和路线表
- 支持坐标存储和查询

**教师系统数据库**:
- 使用SQLite数据库
- 包含用户、班级、学生、材料等多个表
- 支持完整的教学管理功能

### 主程序集成

在主程序`app.py`中，通过以下方式集成APP模块：

```python
# 集成轨迹图模块
from APP.route.app import route_bp
app.register_blueprint(route_bp)

# 集成教师系统
from teacher_integration import integrate_teacher_system
integrate_teacher_system(app)

# 集成APP目录下的教师系统
from teacher.app import teacher_bp as app_teacher_bp
app.register_blueprint(app_teacher_bp)
```

## 部署说明

### 环境要求

- Python 3.7+
- Flask 2.0+
- SQLite3

### 启动步骤

1. 确保所有依赖已安装
2. 运行主程序: `python app.py`
3. 访问相应模块的URL地址

### 测试验证

运行测试脚本验证整合是否成功：

```bash
python test_app_integration.py
```

## 开发指南

### 添加新模块

1. 在APP目录下创建新的模块目录
2. 创建蓝图文件，定义路由和功能
3. 在主程序中注册蓝图
4. 更新测试脚本

### 模块间通信

- 使用数据库进行数据共享
- 通过API接口进行模块间通信
- 避免直接的文件系统依赖

### 配置管理

- 每个模块都有自己的配置文件
- 使用相对路径确保可移植性
- 统一错误处理和日志记录

## 注意事项

1. **路径管理**: 所有路径都使用相对路径，确保在不同环境下正常工作
2. **数据库连接**: 每个模块管理自己的数据库连接，避免冲突
3. **静态文件**: 每个模块的静态文件独立管理
4. **模板继承**: 可以创建基础模板供各模块继承使用

## 更新日志

- 2025-01-10: 完成APP模块整合
- 2025-01-10: 轨迹图模块蓝图化
- 2025-01-10: 教师系统迁移到APP目录
- 2025-01-10: 主程序集成完成
- 2025-01-10: 测试验证通过

## 联系方式

如有问题，请联系开发团队。
