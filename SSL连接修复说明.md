# SSL连接修复说明

## 问题描述
停车场客户端在服务器启用SSL后无法连接，出现SSL证书验证失败错误：
```
SSLError(SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1000)'))
```

## 解决方案
已修改客户端代码，添加SSL证书验证跳过功能：

### 1. 修改的文件
- `server/utils/car_park_client.py` - 客户端主程序
- `server/utils/config.json` - 客户端配置文件

### 2. 主要修改内容

#### 2.1 添加SSL警告禁用
```python
import urllib3

def disable_ssl_warnings():
    """禁用SSL警告"""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

#### 2.2 更新所有HTTP请求
所有`requests`调用都添加了`verify=False`参数：
```python
response = requests.get(
    url,
    headers=HEADERS,
    timeout=10,
    verify=CONFIG.get('ssl_verify', False)  # 使用配置文件中的SSL验证设置
)
```

#### 2.3 更新配置文件
在`config.json`中添加了SSL验证配置：
```json
{
    "CONFIG": {
        "review_api_url": "https://1.95.11.164/car_park/review",
        "ssl_verify": false
    }
}
```

### 3. 配置选项说明

#### ssl_verify 参数
- `true`: 启用SSL证书验证（推荐用于生产环境）
- `false`: 跳过SSL证书验证（用于自签名证书或测试环境）

### 4. 使用方法

#### 4.1 更新配置文件
确保客户端的`config.json`文件包含以下配置：
```json
{
    "DEBUG": false,
    "CONFIG": {
        "review_api_url": "https://1.95.11.164/car_park/review",
        "conn_str": "DRIVER={SQL Server};SERVER=localhost;DATABASE=Park_DB;UID=sa;PWD=123",
        "sync_interval": 60,
        "sys_check_interval": 5,
        "max_retries": 3,
        "retry_interval": 5,
        "ssl_verify": false
    },
    "HEADERS": {
        "X-API-KEY": "95279527"
    }
}
```

#### 4.2 重启客户端
修改配置后需要重启停车场客户端程序。

### 5. 安全注意事项

#### 5.1 生产环境建议
- 如果服务器使用有效的SSL证书，建议设置`"ssl_verify": true`
- 如果使用自签名证书，可以设置`"ssl_verify": false`

#### 5.2 证书验证
- 跳过SSL验证会降低安全性，但可以解决证书问题
- 建议在服务器端配置有效的SSL证书

### 6. 故障排除

#### 6.1 检查配置文件
确保`config.json`文件格式正确，URL已更新为HTTPS。

#### 6.2 检查网络连接
确保客户端可以访问服务器的443端口。

#### 6.3 查看日志
客户端会输出详细的连接日志，包括SSL验证状态。

### 7. 测试步骤

1. 更新客户端配置文件
2. 重启客户端程序
3. 查看日志输出，确认连接成功
4. 测试续期功能是否正常

## 修改总结

此次修改解决了SSL证书验证问题，使客户端能够正常连接到启用SSL的服务器。修改保持了向后兼容性，并提供了灵活的配置选项。
