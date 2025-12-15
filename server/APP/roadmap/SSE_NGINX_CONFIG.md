# Nginx SSE配置建议

## 问题分析
当使用Nginx作为反向代理时，SSE长连接可能会遇到504 Gateway Time-out错误。这是因为Nginx默认的超时设置较短，无法适应SSE长连接的特性。

## 优化配置

### 基础配置
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    # SSL配置...
    
    # SSE优化配置
    location /roadmap/api/sse {
        # 关闭代理缓冲，允许SSE实时传输
        proxy_buffering off;
        
        # 关闭分块传输编码，避免SSE数据被错误处理
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        chunked_transfer_encoding off;
        
        # 延长超时时间，适应SSE长连接
        proxy_read_timeout 3600s;       # 代理读取超时
        proxy_send_timeout 3600s;       # 代理发送超时
        proxy_connect_timeout 60s;      # 代理连接超时
        
        # 长连接保持时间
        keepalive_timeout 3600s;         # 客户端连接保持时间
        
        # 客户端请求超时
        client_max_body_size 10M;        # 客户端请求体最大值
        client_body_timeout 60s;         # 客户端发送请求体超时
        client_header_timeout 60s;       # 客户端发送请求头超时
        
        # 确保正确传递请求头
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 后端服务器地址
        proxy_pass http://backend_server;
    }
    
    # 其他配置...
}
```

### 完整的http块配置
```nginx
http {
    # 其他http配置...
    
    # 全局超时配置
    keepalive_requests 10000;           # 单个连接最大请求数
    keepalive_timeout 3600s;           # 长连接保持时间
    
    # 客户端配置
    client_body_timeout 60s;           # 客户端发送请求体超时
    client_header_timeout 60s;         # 客户端发送请求头超时
    client_max_body_size 10M;          # 客户端请求体最大值
    
    # 代理配置
    proxy_connect_timeout 60s;          # 代理连接超时
    proxy_read_timeout 3600s;           # 代理读取超时
    proxy_send_timeout 3600s;           # 代理发送超时
    
    # 启用HTTP/2支持
    http2_max_concurrent_streams 1000;   # HTTP/2最大并发流
    
    # 其他配置...
}
```

## 关键配置说明

1. **proxy_buffering off**
   - 关闭代理缓冲，确保SSE数据实时传输到客户端
   - 避免Nginx缓冲完整响应后才发送给客户端

2. **proxy_http_version 1.1**
   - 使用HTTP 1.1，支持长连接
   - 避免HTTP 1.0的短连接限制

3. **Connection ''**
   - 清空Connection头，让Nginx使用Keep-Alive
   - 避免连接被意外关闭

4. **proxy_read_timeout 3600s**
   - 延长代理读取超时时间到1小时
   - 适应SSE长连接特性

5. **keepalive_timeout 3600s**
   - 延长客户端连接保持时间到1小时
   - 减少频繁重连的开销

## 测试建议

1. 应用配置后，重启Nginx：
   ```bash
   sudo systemctl restart nginx
   ```

2. 检查Nginx配置语法：
   ```bash
   sudo nginx -t
   ```

3. 监控Nginx日志，查看是否还有504错误：
   ```bash
   tail -f /var/log/nginx/error.log
   ```

## 注意事项

- 确保后端服务器也正确配置了SSE支持
- 考虑使用HTTP/2，提高SSE连接效率
- 监控服务器资源使用，避免过多长连接导致资源耗尽
- 根据实际业务需求调整超时时间，平衡可靠性和资源消耗

## 参考文档

- [Nginx Proxy Module Documentation](http://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Server-Sent Events: Using Nginx](https://www.nginx.com/blog/server-sent-events-nginx/)
- [MDN: Using server-sent events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)