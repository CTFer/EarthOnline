#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SSE服务测试脚本
用于验证SSE服务的功能是否正常工作
"""

import requests
import json
import time
from sseclient import SSEClient

# 服务器URL
BASE_URL = 'http://localhost:5000'
SSE_URL = f'{BASE_URL}/api/sse/connect'
TEST_PLAYER_ID = 1


def test_sse_connection():
    """测试SSE连接"""
    print("开始测试SSE连接...")
    
    try:
        # 创建SSE客户端
        messages = SSEClient(SSE_URL)
        print(f"已连接到SSE服务: {SSE_URL}")
        
        # 监听消息
        message_count = 0
        start_time = time.time()
        
        print("等待接收消息... (按Ctrl+C停止)")
        print("=" * 50)
        
        for msg in messages:
            if msg.data:
                try:
                    # 解析消息数据
                    data = json.loads(msg.data)
                    print(f"[{time.strftime('%H:%M:%S')}] 收到事件: {msg.event if msg.event else 'message'}")
                    print(f"  数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
                    print("-" * 50)
                    
                    message_count += 1
                    
                    # 测试30秒后自动退出
                    if time.time() - start_time > 30:
                        print("测试时间已到，退出测试")
                        break
                        
                except json.JSONDecodeError:
                    print(f"[{time.strftime('%H:%M:%S')}] 收到非JSON数据: {msg.data}")
                    print("-" * 50)
                    
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
    finally:
        print(f"\n测试结束，共接收 {message_count} 条消息")


def test_sse_api():
    """测试SSE相关API"""
    print("\n测试SSE相关API...")
    
    # 测试获取连接状态
    try:
        response = requests.get(f'{BASE_URL}/api/sse/status')
        if response.status_code == 200:
            print(f"连接状态API: 成功")
            print(f"  状态: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        else:
            print(f"连接状态API: 失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"连接状态API: 错误 - {str(e)}")
    
    # 测试向指定玩家发送消息
    try:
        test_data = {
            'player_id': TEST_PLAYER_ID,
            'event': 'test_event',
            'data': {
                'message': '这是一条测试消息',
                'timestamp': time.time()
            }
        }
        response = requests.post(f'{BASE_URL}/api/sse/send_to_player', json=test_data)
        if response.status_code == 200:
            print(f"发送消息API: 成功")
            print(f"  响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
        else:
            print(f"发送消息API: 失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"发送消息API: 错误 - {str(e)}")


if __name__ == '__main__':
    print("EarthOnline SSE服务测试脚本")
    print("=" * 50)
    
    try:
        # 首先测试API
        test_sse_api()
        
        # 然后测试实际的SSE连接
        test_sse_connection()
        
    except ImportError:
        print("错误: 缺少依赖包 'sseclient'")
        print("请运行: pip install sseclient-py")
    except Exception as e:
        print(f"发生未预期的错误: {str(e)}")