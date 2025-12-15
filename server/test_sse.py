#!/usr/bin/env python3
"""
测试SSE连接脚本
"""
import sys
import time
import requests
from urllib3.exceptions import InsecureRequestWarning

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

def test_sse_connection():
    """测试SSE连接"""
    url = 'https://127.0.0.1:8443/roadmap/api/sse'
    
    print(f"开始测试SSE连接: {url}")
    print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    start_time = time.time()
    
    try:
        # 使用stream=True保持连接打开
        response = requests.get(url, stream=True, verify=False)
        
        print(f"连接状态: {response.status_code}")
        print(f"连接建立时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"连接耗时: {time.time() - start_time:.2f} 秒")
        print(f"响应头: {dict(response.headers)}")
        print("\n开始接收SSE事件...")
        
        # 读取SSE事件
        event_count = 0
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                print(f"[{time.strftime('%H:%M:%S')}] {decoded_line}")
                event_count += 1
                
                # 收到3个事件后退出，避免无限等待
                if event_count >= 3:
                    break
                    
                # 5秒后退出，避免无限等待
                if time.time() - start_time > 5:
                    break
                    
    except Exception as e:
        print(f"连接失败: {e}")
        print(f"错误发生时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"错误耗时: {time.time() - start_time:.2f} 秒")
    
    print(f"\n测试结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总耗时: {time.time() - start_time:.2f} 秒")

if __name__ == '__main__':
    test_sse_connection()
