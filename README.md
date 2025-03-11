<!--
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-12 16:39:10
 * @LastEditTime: 2025-03-09 23:25:11
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
-->
# EarthOnline

这是一个基于 Python 开发的ARG养成类平行实境游戏，通过将现实世界与游戏世界相结合，玩家可以通过完成游戏中的任务获得现实世界的奖励。系统使用 NFC 卡片作为玩家与系统之间的交互媒介，实现身份识别和任务管理。

## 🎮 游戏特性

- **任务系统**
  - 主线任务：推动游戏剧情发展的核心任务
  - 支线任务：丰富游戏内容的额外任务
  - 日常任务：每日可重复完成的任务
  - 实时任务状态更新
  - 任务进度追踪
  - 任务奖励系统

- **玩家系统**
  - 完整的用户认证系统
  - 角色管理与数据持久化
  - 玩家状态实时更新
  - 经验值和等级系统
  - 成就系统

- **交互系统**
  - NFC 卡片识别
  - 实时位置追踪
  - 实时通知系统
  - 词云展示
  - Live2D 角色展示

- **管理系统**
  - 完整的管理后台
  - 数据统计和分析
  - 任务管理
  - 用户管理
  - 系统配置

## 🛠 技术栈

### 后端技术

- **核心框架:** Python Flask
- **数据库:** SQLite3
- **实时通信:** Socket.IO
- **API 文档:** Swagger/OpenAPI
- **代码规范:** Black + PEP 8
- **版本控制:** Git

### 前端技术

- **核心框架:**
  - HTML5 + CSS3 + JavaScript
  - Layui UI 框架
- **动画效果:**
  - Live2D
  - CSS3 Animations
- **地图服务:**
  - 高德地图
  - ECharts
- **其他组件:**
  - Swiper 轮播
  - Layer 弹层组件
  - WordCloud 词云

## 📁 项目结构

```text
server/
├── static/                 # 静态资源目录
│   ├── js/                # JavaScript 文件
│   │   ├── client/        # 客户端代码
│   │   │   ├── core/      # 核心模块
│   │   │   ├── service/   # 服务模块
│   │   │   └── utils/     # 工具模块
│   ├── css/               # 样式文件
│   └── img/               # 图片资源
├── templates/             # 模板文件
├── database/             # 数据库文件
├── function/             # 业务功能模块
├── test/                 # 测试文件
└── app.py               # 应用入口
```

### 核心模块说明

- **core/**
  - `api.js`: API 请求封装
  - `eventBus.js`: 事件总线
  - `store.js`: 状态管理
  - `errorHandler.js`: 错误处理

- **service/**
  - `taskService.js`: 任务服务
  - `playerService.js`: 玩家服务
  - `uiService.js`: UI 服务
  - `audioService.js`: 音频服务
  - `mapService.js`: 地图服务
  - `live2dService.js`: Live2D 服务
  - `wordcloudService.js`: 词云服务

- **function/**
  - `TaskService.py`: 任务业务逻辑
  - `PlayerService.py`: 玩家业务逻辑
  - `NFCService.py`: NFC 服务

## 🚀 开发指南

### 环境要求

- Python 3.8+
- Node.js 14+
- SQLite3

### 安装步骤

1.克隆项目

```bash
git clone https://github.com/yourusername/earthonline.git
cd earthonline
```

2.新增配置
在config目录下新建private.py文件，存放了高德地图的KEY

```python
AMAP_SECURITY_JS_CODE = "您的安全密钥"  # 您的安全密钥

```

3.安装依赖

```bash
pip install -r requirements.txt
```

4.初始化数据库

```bash
python init_db.py
```

5.启动服务

```bash
python app.py
```

### 配套接口数据格式

#### NFCTOOLS 数据

```text
[ HTTP POST ]
Request: http://{DEV_SERVER}/api/tasks/nfc_post
POST parameters :
名称: card_id / 值: 1(int类型 填入 )
名称: type / 值: TASK(NFC卡类型)
名称: player_id / 值: 0(int类型 按照NFC卡片设计)
名称: id / 值: 1(int类型 )
名称: value / 值: 0(int类型 )
名称: timastamp / 值: 170000000(时间戳)
名称: device / 值: {SERIAL}(字符串)

```

#### GPS数据格式

```json
{"location":"{last_loc_latlong}","accruacy":"{last_loc_accuracy}","speed":"{last_loc_speed_kmh}","timestamp":"{last_loc_age_timestamp}","player_id":"1","device":"{device_name}"}

```

location：x，y 纬度，精度数据
accruacy：int类型，GPS定位精度
speed：小数，单位公里/小时
player_id:当前数据对应的玩家ID
device：当前数据的采集设备
timestamp：设备采集数据的时间 格式 yyyy-MM-dd HH:mm:ss macroDroid数据格式

### 代码规范

- 使用 Black 格式化 Python 代码
- 遵循 PEP 8 Python 代码规范
- 所有函数必须包含类型注解
- 关键函数必须包含文档字符串
- 注释和调试信息使用中文

### Git 提交规范

```text
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
- 邮件联系: [775639471@qq.com](mailto:775639471@qq.com)
