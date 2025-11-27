# Let's Encrypt 证书管理工具

本工具提供了在Windows Server 2012 R2环境下自动申请、续签和管理Let's Encrypt SSL证书的功能，特别针对nginx 1.8.1进行了优化。

## 功能特性

- ✅ 自动申请Let's Encrypt SSL证书（使用webroot验证方式）
- ✅ 自动续签即将到期的证书
- ✅ 自动部署证书到nginx配置
- ✅ 自动重启nginx服务以应用新证书
- ✅ 定期检查证书状态
- ✅ 命令行界面，支持多种操作
- ✅ 可配置为系统启动时自动运行

## 目录结构

```
d:\code\EarthOnline\server\utils\
├── CertificateService.py     # 核心证书管理服务类
├── certificate_manager.py    # 命令行管理工具
├── certificate_config.json   # 配置文件（使用时需创建）
└── certificate_config.json.example  # 配置文件示例
```

## 前置条件

1. **安装Python**：Windows Server 2012 R2上需安装Python 3.6或更高版本
2. **安装Certbot**：通过pip安装certbot
   ```
   pip install certbot
   ```
3. **nginx已安装**：确保nginx 1.8.1已正确安装并运行
4. **域名已解析**：确保您的域名已正确解析到服务器IP地址
5. **80端口开放**：确保服务器的80端口已开放，用于Let's Encrypt验证

## 快速开始

### 1. 配置域名和邮箱

首先，配置您的域名和联系邮箱：

```cmd
cd d:\code\EarthOnline\server\utils
python certificate_manager.py configure --domain duonline.top --email 775639471@qq.com
```

### 2. 申请新证书

配置完成后，申请新证书：

```cmd
python certificate_manager.py request
```

### 3. 检查证书状态

```cmd
python certificate_manager.py check
```

### 4. 设置自动运行

创建启动脚本并配置为开机自启动：

```cmd
python certificate_manager.py install-service
```

## 详细配置

您可以通过编辑`certificate_config.json`文件进行更详细的配置：

1. 复制示例配置文件：

```cmd
copy certificate_config.json.example certificate_config.json
```

2. 编辑配置文件，修改以下参数：

| 参数 | 说明 | 默认值 |
|------|------|--------|
| domain | 主域名 | example.com |
| domains | 域名列表（包括主域名和子域名） | ["example.com", "www.example.com"] |
| email | Let's Encrypt通知邮箱 | admin@example.com |
| webroot_path | Webroot路径，用于ACME验证 | C:/www/server/static |
| nginx_config_path | nginx配置文件路径 | C:/nginx/conf/nginx.conf |
| nginx_service_name | nginx服务名称 | nginx |
| cert_dir | 证书存储目录 | C:/www/server/config/ssl |
| certbot_path | certbot可执行文件路径 | certbot |
| renew_days_before_expiry | 到期前多少天开始续期 | 30 |
| check_interval_hours | 检查证书状态的时间间隔（小时） | 24 |
| auto_restart_nginx | 证书更新后是否自动重启nginx | true |

## 使用说明

### 命令行工具

```
用法: python certificate_manager.py [命令] [选项]

可用命令:
  configure      配置证书服务
  request        申请新证书
  renew          续签现有证书
  check          检查证书状态
  install-service  安装为Windows服务
  start          启动证书服务
```

### 配置命令示例

```cmd
# 配置域名和邮箱
python certificate_manager.py configure --domain yourdomain.com --email youremail@example.com

# 自定义nginx配置路径
python certificate_manager.py configure --nginx-config "D:/nginx/conf/nginx.conf"

# 禁用自动重启nginx
python certificate_manager.py configure --no-auto-restart
```

### 服务运行

证书服务可以通过以下两种方式运行：

1. **手动启动**：
   ```cmd
   python certificate_manager.py start
   ```

2. **作为Windows服务**：
   - 首先运行 `install-service` 命令创建启动脚本
   - 然后按照提示将脚本添加到Windows任务计划程序

## ACME挑战验证

本工具使用HTTP-01验证方式申请证书，请确保：

1. nginx配置中已正确配置了`.well-known/acme-challenge/`路径
2. 80端口已开放，且可以从互联网访问
3. Webroot路径正确指向您网站的静态文件目录

## 故障排除

### 常见问题

1. **证书申请失败，提示"无法连接到验证URL"**
   - 检查80端口是否开放
   - 确认域名已正确解析到服务器IP
   - 验证nginx配置中的`.well-known/acme-challenge/`路径是否正确

2. **nginx重启失败**
   - 检查nginx服务名称是否正确
   - 确认当前用户有重启服务的权限
   - 可以通过`--no-auto-restart`选项禁用自动重启

3. **找不到certbot命令**
   - 确认certbot已正确安装：`pip install certbot`
   - 或者在配置文件中指定certbot的完整路径

### 日志文件

证书服务的日志文件位于：
- 操作日志：`d:\code\EarthOnline\logs\certificate_manager.log`
- 服务日志：`d:\code\EarthOnline\logs\certificate_service.log`

## 注意事项

1. **定期检查**：建议定期运行`check`命令，确保证书正常
2. **备份配置**：请备份您的`certificate_config.json`文件
3. **续费周期**：Let's Encrypt证书默认有效期为90天，请确保自动续期功能正常工作
4. **权限要求**：运行证书管理工具需要有修改nginx配置和重启nginx服务的权限

## 许可证

本工具基于MIT许可证开源。