# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-02-01 08:25:40
# LastEditTime: 2025-02-01 10:48:04
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import serial
import time
import json
from serial.tools import list_ports

class NFCReader:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self._last_error = None
        
    def get_device_status(self):
        """获取设备详细状态"""
        status = {
            'connected': False,
            'card_present': False,
            'device_info': {
                'port': self.port,
                'baudrate': self.baudrate,
                'available_ports': [],
                'error': None
            },
            'last_error': self._last_error
        }
        
        try:
            # 获取所有可用串口
            available_ports = list_ports.comports()
            status['device_info']['available_ports'] = [
                {
                    'device': port.device,
                    'description': port.description,
                    'manufacturer': port.manufacturer,
                    'pid': port.pid,
                    'vid': port.vid
                }
                for port in available_ports
            ]
            
            # 如果未连接，尝试连接
            if not self.serial or not self.serial.is_open:
                self.serial = serial.Serial(
                    port=self.port,
                    baudrate=self.baudrate,
                    timeout=1
                )
            
            status['connected'] = self.serial.is_open
            
            if status['connected']:
                # 发送查询卡片存在的命令
                self.serial.write(b'CHECK\n')
                response = self.serial.readline().decode().strip()
                status['card_present'] = response == 'CARD_PRESENT'
                
                # 获取设备信息
                self.serial.write(b'INFO\n')
                info_response = self.serial.readline().decode().strip()
                try:
                    device_info = json.loads(info_response)
                    status['device_info'].update(device_info)
                except json.JSONDecodeError:
                    status['device_info']['firmware_info'] = info_response
                
                # 更新设备状态
                status['device_info'].update({
                    'port_open': self.serial.is_open,
                    'dsr': self.serial.dsr,
                    'cts': self.serial.cts,
                    'ri': self.serial.ri,
                    'cd': self.serial.cd
                })
                
        except serial.SerialException as e:
            self._last_error = str(e)
            status['device_info']['error'] = str(e)
        except Exception as e:
            self._last_error = str(e)
            status['device_info']['error'] = str(e)
            
        return status

# 创建全局NFC读写器实例
nfc_reader = NFCReader()

def get_device_status():
    """获取NFC设备状态的全局函数"""
    return nfc_reader.get_device_status()

def read_card():
    """读取NFC卡片数据的全局函数"""
    try:
        if not nfc_reader.serial or not nfc_reader.serial.is_open:
            return {'success': False, 'error': '设备未连接'}
            
        # 发送读取命令
        nfc_reader.serial.write(b'READ\n')
        response = nfc_reader.serial.readline().decode().strip()
        
        if not response:
            return {'success': False, 'error': '读取超时'}
            
        try:
            data = json.loads(response)
            return {'success': True, 'data': data}
        except json.JSONDecodeError:
            return {'success': False, 'error': '数据格式错误'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}

def write_card(data):
    """写入NFC卡片数据的全局函数"""
    try:
        if not nfc_reader.serial or not nfc_reader.serial.is_open:
            return {'success': False, 'error': '设备未连接'}
            
        # 发送写入命令
        command = f"WRITE {json.dumps(data)}\n"
        nfc_reader.serial.write(command.encode())
        
        response = nfc_reader.serial.readline().decode().strip()
        if response == "OK":
            return {'success': True}
        else:
            return {'success': False, 'error': f'写入失败: {response}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)} 