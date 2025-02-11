<!--
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-12 16:39:10
 * @LastEditTime: 2025-02-06 13:52:47
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
-->
# EarthOnline 

全程AI为主开发、基于 Python + Flask 构建的真人养成游戏，提供完整的游戏功能支持和管理系统。

## 🚀 特性

- 完整的用户认证系统
- 角色管理与数据持久化
- 实时任务系统
- 技能树系统
- 管理后台界面
- WebSocket 实时通信
- RESTful API 接口
- 自动化的数据备份

## 🛠 技术栈

- **后端框架:** Python + Flask
- **数据库:** SQLite
- **实时通信:** Socket.IO
- **文档:** Swagger/OpenAPI
- **代码规范:** Black + PEP 8
- **版本控制:** Git

## 📁 项目结构

```
EarthOnline/
├── server/                    # 后端服务器
│   ├── static/               # 静态资源
│   │   ├── css/             # CSS样式文件
│   │   └── js/              # JavaScript文件
│   ├── templates/           # HTML模板
│   ├── database/            # 数据库相关
│   │   ├── migrations/      # 数据库迁移
│   │   └── models/         # 数据模型
│   ├── utils/              # 工具函数
│   ├── admin.py            # 管理后台
│   ├── api.py              # API接口
│   ├── config.py           # 配置文件
│   └── app.py              # 应用入口
│
└── earthonline/            # 前端项目
    ├── css/                # CSS样式
    │   ├── index.css      # 主样式文件
    │   └── swiper-bundle.min.css  # Swiper样式
    ├── js/                 # JavaScript文件
    │   ├── config.js      # 配置文件
    │   ├── game.js        # 游戏逻辑
    │   ├── live2d.min.js  # Live2D核心
    │   └── live2d-config.js  # Live2D配置
    ├── models/            # Live2D模型
    │   └── boy/          # 男孩模型
    │       ├── boy.model3.json
    │       └── textures/
    └── index.html         # 主页面
```

主要文件说明：

1. server/app.py: 后端主程序，处理API请求
2. earthonline/js/game.js: 前端游戏逻辑
3. earthonline/js/config.js: 前端配置文件
4. earthonline/css/index.css: 主要样式文件
5. earthonline/index.html: 主页面

技术栈：

- 后端：Python + Flask
- 前端：HTML5 + CSS3 + JavaScript
- UI框架：Layui
- 动画：Live2D
- 数据库：SQLite


## 💾 数据库设计

### 核心表结构
- **users:** 用户账户信息
- **player_data:** 玩家游戏数据
- **tasks:** 任务配置
- **skills:** 技能定义
- **skill_relations:** 技能树关系
- **player_task:** 玩家任务进度

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip
- SQLite 3

### 1. 安装依赖
```bash
cd server
pip install -r requirements.txt
```

### 2. 初始化数据库
```bash
cd database
sqlite3 game.db < game.sql
```

### 3. 启动服务
```bash
python app.py
```

## 📚 API 文档

### 玩家接口
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /api/character | 获取角色信息 |
| GET | /api/tasks/available | 获取可用任务 |
| POST | /api/tasks/{id}/accept | 接受任务 |

### 管理接口
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | /admin/api/users | 获取用户列表 |
| POST | /admin/api/users | 创建用户 |
| GET | /admin/api/tasks | 获取任务列表 |
| POST | /admin/api/tasks | 创建任务 |

> 📘 完整 API 文档请访问: `/admin/api/docs`

## 💻 开发指南

### 代码规范
- 使用 Black 格式化 Python 代码
- 遵循 PEP 8 Python 代码规范
- 所有函数必须包含类型注解
- 关键函数必须包含文档字符串

### Git 提交规范
```
feat: 新功能
fix: 修复问题
docs: 文档更新
style: 代码格式
refactor: 代码重构
test: 测试相关
chore: 构建过程或辅助工具的变动
```

## 📄 许可证

本项目采用 GPL 3.0 协议 - 详见 [LICENSE](LICENSE) 文件

## 👥 团队

- **一根鱼骨棒** - *项目负责人* - [775639471@qq.com](mailto:775639471@qq.com)
- Copyright © 2025 迷舍

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## 📞 联系我们

- 项目主页: [GitHub](https://github.com/yourusername/earthonline)
- 问题反馈: [Issues](https://github.com/yourusername/earthonline/issues)
- 邮件联系: 775639471@qq.com
