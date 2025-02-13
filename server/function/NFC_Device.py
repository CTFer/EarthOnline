import sqlite3
import os
import logging
import time
import json
import traceback
from datetime import datetime
import serial
import serial.tools.list_ports
from ndef import message, record, UriRecord, TextRecord, message_encoder
import re
import nfc


logger = logging.getLogger(__name__)

class NFC_Device:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NFC_Device, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'database', 
                'game.db'
            )
            self.serial_port = None
            self.initialized = False
            self.last_device_check = 0
            self.device_check_interval = 2  # 设备检查间隔(秒)
            
    def init_nfc_reader(self, port=None, baudrate=115200):
        """初始化NFC读卡器"""
        try:
            # 如果已经初始化且串口正常，直接返回
            if self.initialized and self.serial_port and self.serial_port.is_open:
                return True
            
            # 如果串口存在但未打开，尝试关闭并重新打开
            if self.serial_port:
                try:
                    if self.serial_port.is_open:
                        self.serial_port.close()
                except:
                    pass
                self.serial_port = None
            
            # 等待设备释放
            time.sleep(1)
            detected_ports = []
            
            # 如果没有指定端口，尝试查找可用的串口
            if not port:
                ports = list(serial.tools.list_ports.comports())
                for p in ports:
                    detected_ports.append((p.device, p.description))
                    if 'USB' in p.description:  # 假设NFC读卡器是USB设备
                        port = p.device
                        print(f"\n[NFC] 找到可能的设备:")
                        print(f"  - 端口: {p.device}")
                        print(f"  - 描述: {p.description}")
                        print(f"  - 硬件ID: {p.hwid}")
                        print(f"  - VID:PID: {p.vid}:{p.pid}")
                        print(f"  - 制造商: {p.manufacturer}")
                        print(f"  - 产品: {p.product}")
                        break
                    
            print("\n[NFC] 检测到的所有端口和设备:")
            for dev, desc in detected_ports:
                print(f"  - 端口: {dev}, 设备描述: {desc}")
            
            if not port:
                print("[NFC] 未找到可用的串口设备")
                return False
            
            print(f"\n[NFC] 尝试打开串口: {port}")
            print(f"[NFC] 波特率: {baudrate}")
            
            # 初始化串口
            try:
                self.serial_port = serial.Serial(
                    port=port,
                    baudrate=baudrate,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    bytesize=serial.EIGHTBITS,
                    timeout=1
                )
                
                if self.serial_port.is_open:
                    print("\n[NFC] 串口连接状态:")
                    print(f"  - 端口: {self.serial_port.port}")
                    print(f"  - 波特率: {self.serial_port.baudrate}")
                    print(f"  - 字节大小: {self.serial_port.bytesize}")
                    print(f"  - 停止位: {self.serial_port.stopbits}")
                    print(f"  - 奇偶校验: {self.serial_port.parity}")
                    print(f"  - 超时设置: {self.serial_port.timeout}秒")
                    
                    # 清空缓冲区
                    self.serial_port.reset_input_buffer()
                    self.serial_port.reset_output_buffer()
                    
                    # 发送唤醒指令
                    print("\n[NFC] 发送唤醒指令...")
                    wakeup_cmd = bytes.fromhex('55 55 00 00 00 00 00 00 00 00 00 00 00 00 00 00 FF 03 FD D4 14 01 17 00')
                    self.serial_port.write(wakeup_cmd)
                    time.sleep(0.1)
                    
                    if self.serial_port.in_waiting:
                        response = self.serial_port.read(self.serial_port.in_waiting)
                        print(f"[NFC] 唤醒响应: {response.hex()}")
                        if response and 'd5' in response.hex():
                            print("[NFC] 设备唤醒成功")
                            self.initialized = True
                            return True
                        else:
                            print("[NFC] 设备响应无效")
                    else:
                        print("[NFC] 设备无响应")
                    
                    self.serial_port.close()
                    print("[NFC] 关闭串口连接")
                    self.initialized = False
                    return False
                    
            except serial.SerialException as e:
                print(f"[NFC] 串口错误: {str(e)}")
                if "Permission" in str(e):
                    print("[NFC] 端口可能被其他程序占用")
                return False
            
        except Exception as e:
            print(f"[NFC] 初始化失败: {str(e)}")
            traceback.print_exc()
            self.initialized = False
            return False

    def try_command(self, cmd):
        """尝试发送命令并等待响应"""
        try:
            self.serial_port.write(cmd)
            self.serial_port.flush()
            time.sleep(0.2)
            
            if self.serial_port.in_waiting:
                response = self.serial_port.read(self.serial_port.in_waiting)
                return True
            return False
            
        except Exception as e:
            print(f"[NFC] 命令执行失败: {str(e)}")
            return False

    def read_card_id(self):
        """读取卡片ID"""
        if not self.initialized or not self.serial_port:
            print("[NFC] 设备未初始化")
            return None
        
        try:
            self.serial_port.reset_input_buffer()
            # InListPassiveTarget 命令
            cmd = bytes.fromhex('00 00 FF 04 FC D4 4A 01 00 E1 00')
            self.serial_port.write(cmd)
            time.sleep(0.1)
            
            response = self.serial_port.read_all()
            if not response:
                print("[NFC] 未收到响应")
                return None
            
            print(f"[NFC] 读取卡片ID响应: {response.hex()}")
            hex_data = response.hex().lower()
            
            # 检查响应中是否包含d54b（成功响应标识）
            if 'd54b' not in hex_data:
                print("[NFC] 响应中未找到有效的卡片ID")
                return None
            
            # 提取卡片信息
            card_info = hex_data[hex_data.find('d54b')+4:]
            if len(card_info) >= 8:
                card_id = card_info.upper()
                print(f"[NFC] 成功读取卡片ID: {card_id}")
                return card_id
            
            print("[NFC] 卡片信息长度不足")
            return None
            
        except Exception as e:
            print(f"[NFC] 读取卡片ID错误: {str(e)}")
            return None

    def read_card_data(self, block_number=0):
        """读取NTAG215数据"""
        if not self.initialized or not self.serial_port:
            return None
            
        try:
            # 预先构建命令,避免重复计算
            cmd_body = bytes.fromhex(f'D4 40 01 30 {block_number:02x}')
            cmd = self._build_command(cmd_body)
            
            # 直接写入不等待
            self.serial_port.write(cmd)
            
            # 使用更短的等待时间
            time.sleep(0.05)
            
            # 一次性读取所有数据
            data_response = self.serial_port.read_all()
            if data_response and 'd541' in data_response.hex():
                data_start = data_response.hex().find('d541') + 6
                if len(data_response.hex()) >= data_start + 32:
                    return data_response.hex()[data_start:data_start+8].upper()
            return None
            
        except Exception as e:
            print(f"[NFC] 读取错误: {str(e)}")
            return None

    def write_card_data(self, page, data):
        """写入单页数据到NTAG215并验证
        Args:
            page: 页码 (0-129)
            data: 8字节的十六进制数据
        Returns:
            bool: 写入并验证成功返回True
        """
        try:
            if not self.initialized or not self.serial_port:
                print("[NFC] 设备未初始化")
                return False
                
            # 构造写入命令 (NTAG215 Write Command: A2)
            cmd_body = bytes.fromhex(f'D4 40 01 A2 {page:02x} {data}')
            cmd = self._build_command(cmd_body)
            print(f"\n[NFC] === 页 {page} 写入操作 ===")
            print(f"预期数据: {data}")
            print(f"写入命令: {cmd.hex()}")
            
            max_retries = 3
            for retry in range(max_retries):
                # 发送命令前清空缓冲区
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                
                # 发送写入命令
                self.serial_port.write(cmd)
                time.sleep(0.02)  # 等待写入完成
                
                # 读取写入响应
                response = self.serial_port.read_all()
                print(f"写入响应: {response.hex() if response else 'None'}")
                
                # 检查写入响应 (D5 41 00 表示成功)
                if response and 'd541' in response.hex().lower():
                    # 验证写入的数据
                    time.sleep(0.02)  # 等待数据稳定
                    read_data = self.read_card_data(page)
                    
                    if read_data:
                        print(f"读取数据: {read_data}")
                        # 比较预期数据和实际数据
                        if read_data.upper() == data.upper():
                            print(f"数据验证: [成功] 预期={data} 实际={read_data}")
                            print(f"[NFC] 页 {page} 写入成功，验证通过")
                            return True
                        else:
                            print(f"数据验证: [失败]")
                            print(f"  预期数据: {data}")
                            print(f"  实际数据: {read_data}")
                            print(f"  差异位置: ", end='')
                            for i in range(min(len(data), len(read_data))):
                                if data[i].upper() != read_data[i].upper():
                                    print(f"位置{i}[{data[i]}!={read_data[i]}] ", end='')
                            print()
                            
                            if retry < max_retries - 1:
                                print(f"正在重试 ({retry + 1}/{max_retries})...")
                                time.sleep(0.05)  # 重试前等待
                                continue
                    else:
                        print(f"数据验证: [失败] 无法读取数据")
                        if retry < max_retries - 1:
                            print(f"正在重试 ({retry + 1}/{max_retries})...")
                            time.sleep(0.05)
                            continue
                else:
                    print(f"写入响应: [失败] 未收到正确的响应")
                    if retry < max_retries - 1:
                        print(f"正在重试 ({retry + 1}/{max_retries})...")
                        time.sleep(0.05)
                        continue
                    
            print(f"[NFC] 页 {page} 写入失败，重试次数达到上限")
            return False
            
        except Exception as e:
            print(f"[NFC] 写入页 {page} 错误: {str(e)}")
            return False

    def write_card_data_old(self, block_number, data):
        """写入NTAG215数据旧版本 会出现多写入字符的情况"""
        if not self.initialized or not self.serial_port:
            return False
            
        try:
            if len(data) != 8:
                print(f"[NFC] 数据长度错误: {len(data)}, 应为8")
                return False
            
            # 预先构建命令
            cmd_body = bytes.fromhex(f'D4 40 01 A2 {block_number:02x} {data}')
            cmd = self._build_command(cmd_body)
            
            # 直接写入不等待
            self.serial_port.write(cmd)
            
            # 使用更短的等待时间
            time.sleep(0.05)
            
            # 快速检查响应
            response = self.serial_port.read_all()
            return bool(response and 'd541' in response.hex())
            
        except Exception as e:
            print(f"[NFC] 写入错误: {str(e)}")
            return False

    def _build_command(self, cmd_body):
        """构建完整的命令"""
        cmd_len = len(cmd_body)
        lcs = (0x100 - cmd_len) & 0xFF
        dcs = (0x100 - sum(cmd_body) & 0xFF) & 0xFF
        return bytes.fromhex('00 00 FF') + bytes([cmd_len, lcs]) + cmd_body + bytes([dcs, 0x00])

    def test_device(self):
        """测试设备功能"""
        if not self.initialized:
            if not self.init_nfc_reader():
                print("[NFC] 初始化失败")
                return
            
        print("[NFC] 等待读卡...")
        last_card_id = None
        card_present = False
        
        try:
            card_id = self.read_card_id()
            
            if card_id:
                if not card_present or card_id != last_card_id:
                    print(f"[NFC] 检测到卡片: {card_id}")
                    # 尝试分页读取，如果失败则使用一次性读取
                    data = self.read_card_data_by_page()
                    if not data:
                        data = self.read_all_card_data()
                    if data:
                        print(f"[NFC] 读取数据: {data}")
                        
                    last_card_id = card_id
                    card_present = True
        
            else:
                if card_present:
                    print("[NFC] 卡片已移除")
                    card_present = False
                    last_card_id = None
                    
            time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n[NFC] 停止读卡")
        except Exception as e:
            print(f"[NFC] 错误: {str(e)}")

    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def generate_header(self, data_length, identifier):
        """生成NDEF消息头部
        Args:
            data_length: 数据长度
            identifier: 标识符
        Returns:
            str: 头部的hex字符串
        """
        # 1. 固定起始字节
        start_byte = "03"
        
        # 2. 长度字节
        length_byte = format(data_length, '02X')
        
        # 3. 固定标识
        fixed_id = "9205"
        
        # 4. 长度标识符
        
        # 5. 固定前缀
        prefix = "77312F3130"
        
        # 组合头部
        header = f"{start_byte}{length_byte}{fixed_id}{identifier}{prefix}"
        return header

    def get_length_identifier(self, total_length):
        """根据总长度计算标识符
        Args:
            total_length: 数据总长度
        Returns:
            str: 两字符的标识符
        """
        # 标识符值 = 总长度 - 45
        identifier_value = total_length - 45
        identifier = format(identifier_value, '02X')
        
        print(f"\n标识符计算:")
        print(f"数据总长度: {total_length}")
        print(f"标识符计算: {total_length} - 45 = {identifier_value}")
        print(f"标识符(HEX): {identifier}")
        
        return identifier

    def calculate_ndef_length(self, url_data):
        """计算NDEF消息长度
        Args:
            url_data: URL字符串(已处理分号)
        Returns:
            int: 总长度
        """
        # 固定部分
        package_info = "android.com:pkgcom.wakdev.nfctasks"
        fixed_extra_bytes = 11  # T + 0F + 13 + FE + 00 + 00 + 00000
        
        # 计算总长度
        total_length = (
            len(url_data) +     # URL长度(含分号)
            len(package_info) + # 包名长度
            fixed_extra_bytes   # 固定的额外11字节
        )
        
        print(f"\n长度计算详情:")
        print(f"URL(含分号): '{url_data}' ({len(url_data)} 字节)")
        print(f"包名: '{package_info}' ({len(package_info)} 字节)")
        print(f"固定额外字节: {fixed_extra_bytes} 字节")
        print(f"  - 控制字符(T0F13): 3 字节")
        print(f"  - 结束标记(FE0000): 3 字节")
        print(f"  - 填充(00000): 5 字节")
        print(f"总长度: {total_length} (0x{format(total_length, '02X')}) 字节")
        
        return total_length

    def format_ascii_to_hex(self, url_data):
        """将用户提供的URL转换为NDEF格式的hex数据"""
        try:
            print(f"[NFC] 格式化URL: {url_data}")
            # 1. 确保URL以分号结束
            if not url_data.endswith(';'):
                url_data = url_data + ';'
            
            # 2. 移除URL中可能已存在的包名部分
            if "android.com:pkgcom.wakdev.nfctasks" in url_data:
                url_data = url_data.replace("Tandroid.com:pkgcom.wakdev.nfctasks", "")
            
            # 3. 计算总长度
            ndef_length = self.calculate_ndef_length(url_data)
            length_byte = format(ndef_length, '02X')
            
            # 4. 根据长度获取标识符
            identifier = self.get_length_identifier(ndef_length)
            
            # 5. 生成头部
            header = self.generate_header(ndef_length, identifier)
            
            # 6. 构造数据部分
            hex_parts = []
            hex_parts.append(url_data.encode('utf-8').hex().upper())
            hex_parts.append("540F13")  # 完整的控制字符
            hex_parts.append("616E64726F69642E636F6D3A706B67636F6D2E77616B6465762E6E66637461736B73")
            hex_parts.append("FE0000")
            hex_parts.append("00" * 10)
            
            # 7. 合并所有数据
            final_hex = header + ''.join(hex_parts)
            print(f"计算长度: {ndef_length}")
            print(f"最终数据: {final_hex}")
            
            return final_hex
            
        except Exception as e:
            print(f"格式转换错误: {str(e)}")
            traceback.print_exc()
            return None

    def read_all_card_data(self, start_page=4, end_page=129):
        """读取NTAG215所有数据
        Args:
            start_page: 起始页码 (默认4)
            end_page: 结束页码 (默认129)
        Returns:
            str: 十六进制数据字符串
        """
        try:
            if not self.initialized or not self.serial_port:
                print("[NFC] 设备未初始化")
                return None
                
            # 检查卡片
            if not self.read_card_id():
                print("[NFC] 未检测到卡片")
                return None
                
            print("[NFC] 开始读取数据...")
            all_data = []
            
            # 逐页读取数据
            for page in range(start_page, end_page):
                # 清空缓冲区
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                
                # 读取单页数据
                page_data = self.read_card_data(page)
                if not page_data:
                    print(f"[NFC] 读取页 {page} 失败")
                    break
                    
                print(f"[NFC] 页 {page}: {page_data}")
                all_data.append(page_data)
                
                # 检查是否遇到结束标记 (FE)
                if 'FE' in page_data:
                    # 找到FE的位置
                    fe_pos = page_data.find('FE')
                    # 保留FE及之前的数据
                    all_data[-1] = page_data[:fe_pos + 2]
                    break
                    
                time.sleep(0.01)  # 短暂延时确保稳定性
                
            if not all_data:
                print("[NFC] 未读取到有效数据")
                return None
                
            # 合并所有数据
            complete_data = ''.join(all_data)
            print(f"\n[NFC] 完整数据: {complete_data}")
            return complete_data
            
        except Exception as e:
            print(f"[NFC] 读取数据错误: {str(e)}")
            return None

    def _wait_for_card(self):
        """等待卡片并初始化串口读卡器"""
        try:
            # 确保串口已初始化
            if not self.initialized:
                if not self.init_nfc_reader():
                    print("[NFC] 无法初始化读卡器")
                    return False
                    
            # 等待卡片
            while True:
                card_id = self.read_card_id()
                if card_id:
                    print(f"[NFC] 检测到卡片: {card_id}")
                    return True
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n[NFC] 操作被用户中断")
            return False
        except Exception as e:
            print(f"[NFC] 等待卡片错误: {str(e)}")
            return False

    def _process_card_data(self, data_blocks):
        """处理读取到的卡片数据"""
        if not data_blocks:
            return None
        
        complete_data = ''.join(data_blocks)
        print(f"[NFC] 完整数据: {complete_data}")
        
        # 处理结束标记和填充
        if 'FE' in complete_data:
            fe_pos = complete_data.find('FE')
            complete_data = complete_data[:fe_pos+2]
            
            # 添加填充
            if len(complete_data) % 8 != 0:
                padding = 8 - (len(complete_data) % 8)
                complete_data += '00' * padding
            
        return complete_data

    def _wait_for_card_nfcpy(self):
        """使用python-nfc等待卡片并初始化读卡器"""
        try:
            print("[NFC] 使用python-nfc等待卡片...")
            
            # 断开串口连接
            if self.serial_port and self.serial_port.is_open:
                print("[NFC] 关闭串口连接...")
                self.serial_port.close()
                self.serial_port = None
                self.initialized = False
                time.sleep(1)
            
            clf = None  # 确保clf在try块外定义
            try:
                # 尝试初始化NFC读卡器
                for retry in range(3):
                    try:
                        print(f"[NFC] 尝试初始化NFC读卡器 {retry + 1}/3")
                        clf = nfc.ContactlessFrontend('usb')
                        if clf:
                            print("[NFC] NFC读卡器初始化成功")
                            break
                    except Exception as e:
                        print(f"[NFC] 初始化尝试失败: {str(e)}")
                        if clf:
                            clf.close()
                            clf = None
                        time.sleep(1)
                
                if not clf:
                    print("[NFC] 无法初始化NFC读卡器，切换到串口模式")
                    return None, None
                
                # 等待并检测卡片
                target = clf.sense(nfc.clf.RemoteTarget('106A'))
                if not target:
                    print("[NFC] 未检测到卡片")
                    clf.close()
                    return None, None
                
                # 连接卡片
                tag = nfc.tag.activate(clf, target)
                if not tag:
                    print("[NFC] 无法连接卡片")
                    clf.close()
                    return None, None
                
                print(f"[NFC] 已连接卡片: {tag}")
                return clf, tag
                
            except Exception as e:
                print(f"[NFC] python-nfc设备访问错误: {str(e)}")
                if clf:
                    clf.close()
                return None, None
                
        except ImportError:
            print("[NFC] python-nfc库未安装，请使用pip install nfcpy安装")
            return None, None
        except KeyboardInterrupt:
            print("\n[NFC] 操作被用户中断")
            return None, None
        except Exception as e:
            print(f"[NFC] python-nfc初始化错误: {str(e)}")
            traceback.print_exc()
            return None, None

    def _read_classic_data(self):
        """读取Mifare Classic数据，优先使用python-nfc"""
        try:
            # 尝试使用python-nfc
            clf, tag = self._wait_for_card_nfcpy()
            if clf and tag:
                try:
                    print("[NFC] 使用python-nfc读取Classic数据...")
                    all_data = []
                    
                    # 读取前4个扇区的数据
                    for sector in range(4):
                        sector_data = []
                        start_block = sector * 4
                        
                        # 读取扇区的前3个块
                        for block in range(3):
                            block_num = start_block + block
                            try:
                                data = tag.read(block_num)
                                if data:
                                    hex_data = data.hex().upper()
                                    sector_data.append(hex_data)
                                    print(f"[NFC] 块{block_num}读取成功: {hex_data}")
                                else:
                                    print(f"[NFC] 块{block_num}读取失败")
                                    continue
                            except Exception as e:
                                print(f"[NFC] 读取块{block_num}错误: {str(e)}")
                                continue
                            
                        if sector_data:
                            sector_hex = ''.join(sector_data)
                            all_data.append(sector_hex)
                            
                            # 检查结束标记
                            if 'FE' in sector_hex:
                                break
                                
                    return self._process_card_data(all_data)
                    
                finally:
                    clf.close()
                    time.sleep(1)  # 等待设备释放
                    
            # 如果python-nfc失败，使用串口方式
            print("[NFC] 准备切换到串口方式...")
            
            # 确保完全重置设备状态
            if self.serial_port and self.serial_port.is_open:
                print("[NFC] 关闭现有串口连接...")
                self.serial_port.close()
                self.serial_port = None
            self.initialized = False
            time.sleep(2)  # 增加等待时间
            
            # 重试串口初始化
            for retry in range(3):  # 最多重试3次
                print(f"[NFC] 尝试初始化串口 {retry + 1}/3")
                if self.init_nfc_reader():
                    print("[NFC] 串口初始化成功")
                    break
                time.sleep(1)
            else:
                print("[NFC] 串口初始化失败")
                return None
            
            # 等待卡片
            if not self._wait_for_card():
                return None
            
            # 读取前4个扇区的数据
            all_data = []
            for sector in range(4):
                sector_data = []
                start_block = sector * 4
                
                # 读取扇区的前3个块
                for block in range(3):
                    block_num = start_block + block
                    data = self.read_classic_block(block_num)
                    if data:
                        sector_data.append(data)
                        print(f"[NFC] 块{block_num}读取成功: {data}")
                    else:
                        print(f"[NFC] 块{block_num}读取失败")
                        continue
                    
                if sector_data:
                    sector_hex = ''.join(sector_data)
                    all_data.append(sector_hex)
                    
                    # 检查结束标记
                    if 'FE' in sector_hex:
                        break
                    
            return self._process_card_data(all_data)
            
        except Exception as e:
            print(f"[NFC] Classic读取错误: {str(e)}")
            traceback.print_exc()
            return None
        finally:
            # 确保设备状态正确
            if not self.initialized:
                print("[NFC] 最终检查设备状态...")
                time.sleep(2)
                for retry in range(3):
                    if self.init_nfc_reader():
                        print("[NFC] 设备恢复成功")
                        break
                    time.sleep(1)
                else:
                    print("[NFC] 设备恢复失败")

    def _read_ntag_data(self, start_page=4, end_page=129):
        """使用串口读取NTAG215数据"""
        try:
            if not self._wait_for_card():
                return None
            
            # 读取数据页
            all_data = []
            found_end = False
            
            for page in range(start_page, end_page, 4):
                if found_end:
                    break
                
                self.serial_port.reset_input_buffer()
                cmd_body = bytes.fromhex(f'D4 40 01 30 {page:02x} 04')
                cmd = self._build_command(cmd_body)
                
                self.serial_port.write(cmd)
                time.sleep(0.1)
                
                response = self.serial_port.read_all()
                if not response:
                    continue
                
                hex_data = response.hex()
                if 'd541' not in hex_data:
                    continue
                
                data_start = hex_data.find('d541') + 6
                data = hex_data[data_start:].upper()
                
                if 'FE' in data:
                    fe_pos = data.find('FE')
                    data = data[:fe_pos+2]
                    found_end = True
                    
                    total_len = len(''.join(all_data)) + len(data)
                    padding_needed = 8 - (total_len % 8) if total_len % 8 != 0 else 0
                    if padding_needed > 0:
                        data += '00' * padding_needed
                    
                all_data.append(data)
                time.sleep(0.05)
                
            return self._process_card_data(all_data)
            
        except Exception as e:
            print(f"[NFC] NTAG读取错误: {str(e)}")
            traceback.print_exc()
            return None

    def read_classic_block(self, block):
        """读取Classic卡片数据块"""
        if not self.initialized or not self.serial_port:
            return None
        
        try:
            self.serial_port.reset_input_buffer()
            cmd_body = bytes.fromhex(f'D4 40 01 30 {block:02x}')
            cmd = self._build_command(cmd_body)
            
            print(f"[NFC] 发送读取命令: {cmd.hex()}")
            self.serial_port.write(cmd)
            time.sleep(0.1)
            
            response = self.serial_port.read_all()
            if not response:
                return None
            
            hex_data = response.hex().lower()
            if 'd541' not in hex_data:
                return None
            
            data_start = hex_data.find('d541') + 6
            if len(hex_data) >= data_start + 32:
                block_data = hex_data[data_start:data_start+32].upper()
                print(f"[NFC] 块{block}数据: {block_data}")
                return block_data
            
            return None
            
        except Exception as e:
            print(f"[NFC] 读取数据块错误: {str(e)}")
            return None

    def read_card_data_by_page(self):
        """分页读取卡片数据"""
        if not self.initialized or not self.serial_port:
            print("[NFC] 设备未初始化")
            return None
        
        try:
            if not self.read_card_id():
                print("[NFC] 未检测到卡片")
                return None
            
            print("[NFC] 开始分页读取...")
            all_data = []
            found_end = False
            
            for page in range(4, 130):
                if found_end:
                    break
                    
                data = self.read_card_data(page)
                if not data:
                    break
                    
                # 检查是否包含结束标志FE
                if 'FE' in data:
                    fe_pos = data.find('FE')
                    data = data[:fe_pos+2]  # 包含FE
                    found_end = True
                    
                    # 计算需要的填充量
                    total_len = len(''.join(all_data)) + len(data)
                    padding_needed = 8 - (total_len % 8) if total_len % 8 != 0 else 0
                    if padding_needed > 0:
                        data += '00' * padding_needed
                        
                all_data.append(data)
                
            if not all_data:
                print("[NFC] 读取失败")
                return None
                
            complete_data = ''.join(all_data)
            print("[NFC] 读取完成")
            return complete_data
            
        except Exception as e:
            print(f"[NFC] 分页读取错误: {str(e)}")
            return None

    def write_data_to_card(self, data, is_ascii=True):
        """自动识别卡片类型并写入数据"""
        if not self.initialized:
            if not self.init_nfc_reader():
                print("[NFC] 初始化失败")
                return False
        
        try:
            print("[NFC] 等待放置卡片...")
            while not self.read_card_id():
                time.sleep(0.05)
            
            # 识别卡片类型
            card_type = self.read_card_type()
            if not card_type:
                print("[NFC] 无法识别卡片类型")
                return False
            
            print(f"[NFC] 检测到卡片类型: {card_type}")
            
            # 准备数据
            if is_ascii:
                hex_data = self.format_ascii_to_hex(data)
                if not hex_data:
                    print("[NFC] 数据格式化失败")
                    return False
            else:
                hex_data = data.upper()
            
            # 根据卡片类型选择写入方式
            if card_type == 'NTAG215':
                return self._write_ntag_data(hex_data)
            elif card_type == 'MIFARE_CLASSIC_1K':
                return self._write_classic_data(hex_data)
            else:
                print("[NFC] 不支持的卡片类型")
                return False
            
        except Exception as e:
            print(f"[NFC] 写入错误: {str(e)}")
            return False

    def _write_ntag_data(self, hex_data):
        """写入数据到NTAG卡片"""
        try:
            # 初始检查卡片
            card_id = self.read_card_id()
            if not card_id:
                print("[NFC] 未检测到卡片")
                return False
                
            print(f"[NFC] 开始写入NTAG215数据...")
            
            # 计算需要写入的页数
            data_len = len(hex_data)
            pages = (data_len + 7) // 8
            
            # 分页写入数据
            for page in range(pages):
                start = page * 8
                end = min(start + 8, data_len)
                page_data = hex_data[start:end].ljust(8, '0')
                
                # 写入单页数据
                if not self.write_card_data(page + 4, page_data):
                    print(f"[NFC] 写入页 {page + 4} 失败")
                    return False
                    
                time.sleep(0.05)
            
            print("[NFC] 验证完整数据...")
            # 读取完整数据进行验证
            read_data = ""
            for page in range(pages):
                page_data = self.read_card_data(page + 4)
                if not page_data:
                    print(f"[NFC] 读取页 {page + 4} 失败")
                    return False
                read_data += page_data
                
            # 移除末尾的填充零
            written_data = hex_data.rstrip('0')
            read_data = read_data.rstrip('0')
            
            print("\n[NFC] 数据对比:")
            print(f"预期数据: {written_data}")
            print(f"实际数据: {read_data}")
            
            if written_data == read_data:
                print("[NFC] 数据验证成功")
                return True
            else:
                print("[NFC] 数据验证失败")
                print("差异位置:")
                for i, (w, r) in enumerate(zip(written_data, read_data)):
                    if w != r:
                        print(f"位置 {i}: 预期={w} 实际={r}")
                return False
                
        except Exception as e:
            print(f"[NFC] 写入NTAG数据错误: {str(e)}")
            return False

    def _write_ntag_data_old(self, hex_data):
        """写入NTAG215数据"""
        try:
            # 初始检查卡片，只检查一次
            card_id = self.read_card_id()
            if not card_id:
                print("[NFC] 未检测到卡片")
                return False
            
            print(f"[NFC] 开始写入NTAG215数据...")
            
            # 计算需要写入的页数 (每页8字节)
            data_len = len(hex_data)
            pages = (data_len + 7) // 8  # 每页8字节，向上取整
            
            # 一次性准备所有数据
            all_pages_data = []
            for page in range(pages):
                start = page * 8
                end = min(start + 8, data_len)
                page_data = hex_data[start:end].ljust(8, '0')
                all_pages_data.append(page_data)
            
            # 连续快速写入所有数据
            for page, page_data in enumerate(all_pages_data):
                # 使用write_card_data写入单页
                if not self.write_card_data(page + 4, page_data):  # 从第4页开始写入
                    print(f"[NFC] 写入页 {page + 4} 失败")
                    return False
                
                # 最小化延时
                time.sleep(0.05)
            
            print("[NFC] 验证数据...")
            written_data = hex_data.rstrip('0')
            read_data = self.read_all_card_data()
            
            if not read_data or written_data not in read_data:
                print("[NFC] 数据验证失败")
                return False            
            # 写入完成后等待数据稳定
            time.sleep(0.05)
            
            print("[NFC] 写入完成")
            return True
            
        except Exception as e:
            print(f"[NFC] 写入NTAG数据错误: {str(e)}")
            return False

    def _write_classic_data(self, hex_data):
        """写入Mifare Classic数据"""
        try:
            print("[NFC] 开始写入Classic数据...")
            
            # 计算需要的扇区数
            data_len = len(hex_data)
            bytes_per_sector = 48  # 3个块，每块16字节
            sectors_needed = (data_len + 31) // 32  # 向上取整
            
            # 分割数据
            chunks = []
            for i in range(0, data_len, 32):
                chunk = hex_data[i:i+32]
                if len(chunk) < 32:
                    chunk = chunk.ljust(32, '0')
                chunks.append(chunk)
            
            # 写入数据
            for sector in range(min(sectors_needed, 4)):  # 限制在前4个扇区
                if not self.read_card_id():
                    print("[NFC] 卡片已移除")
                    return False
                    
                sector_chunks = chunks[sector*3:(sector+1)*3]
                if not sector_chunks:
                    break
                    
                # 补齐3个块
                while len(sector_chunks) < 3:
                    sector_chunks.append('00' * 16)
                    
                if not self.write_classic_sector(sector, sector_chunks):
                    print(f"[NFC] 扇区{sector}写入失败")
                    return False
                    
                time.sleep(0.1)
            
            print("[NFC] 验证数据...")
            written_data = hex_data.rstrip('0')
            read_data = self._read_classic_data()
            
            if not read_data or written_data not in read_data:
                print("[NFC] 数据验证失败")
                return False
            
            print("[NFC] 写入完成")
            return True
            
        except Exception as e:
            print(f"[NFC] Classic写入错误: {str(e)}")
            return False

    def format_to_hex_test(self, data):
        """测试格式化HEX数据"""
        hex_data = self.format_ascii_to_hex(data)
        print(f"写入的HEX数据: {hex_data}")
        print(f"写入的HEX数据长度: {len(hex_data)}")

    def decode_hex_data(self, full_hex, debug_color=True):
        """解码十六进制数据，支持多种编码方式和染色调试
        Args:
            full_hex: 完整的十六进制数据字符串
            debug_color: 是否启用染色调试
        """
        try:
            print("\n" + "="*50)
            print("数据解码分析:")
            print("="*50)
            
            # 原始数据展示
            print("\n[原始HEX数据]")
            if debug_color:
                try:
                    # 染色显示不同部分
                    colored_hex = (
                        f"\033[94m{full_hex[:8]}\033[0m"  # NDEF头部(蓝色)
                        f"\033[92m{full_hex[8:12]}\033[0m"  # 标识符(绿色)
                        f"\033[93m{full_hex[12:20]}\033[0m"  # w1/10前缀(黄色)
                        f"\033[97m{full_hex[20:-14]}\033[0m"  # URL数据(白色)
                        f"\033[91m{full_hex[-14:-6]}\033[0m"  # 结束标记(红色)
                        f"\033[90m{full_hex[-6:]}\033[0m"  # 填充(灰色)
                    )
                    print(colored_hex)
                except Exception as e:
                    print(full_hex)
                    print(f"染色显示错误: {str(e)}")
            else:
                print(full_hex)
                
            print("\n[数据长度]")
            print(f"总长度: {len(full_hex)//2} 字节")
            
            # 尝试多种编码解码
            encodings = ['ascii', 'utf-8']
            decoded_data = None
            
            for encoding in encodings:
                try:
                    # 确保hex字符串是有效的
                    clean_hex = ''.join(c for c in full_hex if c.isalnum())
                    if len(clean_hex) % 2 != 0:
                        clean_hex = clean_hex[:-1]  # 确保长度为偶数
                        
                    decoded = bytes.fromhex(clean_hex).decode(encoding, errors='ignore')
                    # 移除空字符和控制字符
                    cleaned = ''.join(char for char in decoded if ord(char) >= 32)
                    if cleaned:
                        print(f"{encoding:10}: {cleaned}")
                        if not decoded_data:
                            decoded_data = cleaned
                except Exception as e:
                    print(f"{encoding:10}: 解码失败 - {str(e)}")

            print("\n" + "="*50)
            return {
                'data': {
                    'decoded_data': decoded_data if decoded_data else "解码失败"
                }
            }
            
        except Exception as e:
            print(f"整体解码过程出错: {str(e)}")
            traceback.print_exc()
            return {
                'code': -1,
                'msg': f'解码错误: {str(e)}',
                'data': None
            }

    def decode_hex_data_test(self, full_hex):
        """测试解码HEX数据"""
        return self.decode_hex_data(full_hex, debug_color=True)

    def read_card_type(self):
        """读取卡片类型"""
        if not self.initialized or not self.serial_port:
            if not self.init_nfc_reader():
                print("[NFC] 初始化失败")
                return None
        
        try:
            self.serial_port.reset_input_buffer()
            # InListPassiveTarget 命令
            cmd = bytes.fromhex('00 00 FF 04 FC D4 4A 01 00 E1 00')
            self.serial_port.write(cmd)
            time.sleep(0.1)
            
            response = self.serial_port.read_all()
            if not response:
                return None
            
            hex_data = response.hex().lower()
            print(f"[NFC] 完整响应: {hex_data}")
            
            if 'd54b' not in hex_data:
                return None
            
            # 提取完整响应数据，跳过d54b
            response_data = hex_data[hex_data.find('d54b')+4:]
            
            if len(response_data) < 16:  # 确保数据长度足够
                return None
            
            # 正确提取ATQA和SAK
            # ATQA在第3-4字节位置 (跳过前两个字节)
            atqa = response_data[4:8]
            # SAK在ATQA后的第4个字节
            sak = response_data[8:10]
            
            print(f"[NFC] 解析卡片信息 - ATQA: {atqa}, SAK: {sak}, 原始数据: {response_data}")
            
            # NTAG215: ATQA=0x0044, SAK=0x00
            if atqa == '0044' and sak == '00':
                return 'NTAG215'
            # Mifare Classic 1K: ATQA=0x0004, SAK=0x08
            elif atqa == '0004' and sak == '08':
                return 'MIFARE_CLASSIC_1K'
            
            # 备用判断逻辑
            if '0044' in response_data[4:8]:
                return 'NTAG215'
            elif '0004' in response_data[4:8]:
                return 'MIFARE_CLASSIC_1K'
            
            return None
            
        except Exception as e:
            print(f"[NFC] 读取卡片类型错误: {str(e)}")
            traceback.print_exc()
            return None

    def authenticate_sector(self, sector, key_type='A', key='FFFFFFFFFFFF'):
        """验证扇区
        Args:
            sector: 扇区号(0-15)
            key_type: 密钥类型('A' or 'B')
            key: 6字节密钥(hex string)
        Returns:
            bool: 验证成功返回True
        """
        if not self.initialized or not self.serial_port:
            return False
        
        try:
            # 对于未加密卡片，直接返回True
            return True
            
            # 以下是加密卡片的认证逻辑，暂时不使用
            """
            # 计算块地址(每个扇区4个块)
            block = sector * 4
            
            # 构建认证命令
            key_cmd = 'A0' if key_type == 'A' else 'B0'
            cmd_body = bytes.fromhex(f'D4 40 01 {key_cmd} {block:02x} {key}')
            cmd = self._build_command(cmd_body)
            
            self.serial_port.write(cmd)
            time.sleep(0.1)
            
            response = self.serial_port.read_all()
            return bool(response and 'd541' in response.hex())
            """
            
        except Exception as e:
            print(f"[NFC] 扇区认证错误: {str(e)}")
            return False

    def read_classic_sector(self, sector, key='FFFFFFFFFFFF', key_type='A'):
        """读取整个扇区数据
        Args:
            sector: 扇区号(0-15)
            key: 密钥(默认FFFFFFFFFFFF)
            key_type: 密钥类型(A/B)
        Returns:
            list: 包含4个数据块的列表
        """
        if not self.authenticate_sector(sector, key_type, key):
            print(f"[NFC] 扇区{sector}认证失败")
            return None
        
        try:
            blocks = []
            start_block = sector * 4
            for i in range(4):
                block_data = self.read_classic_block(start_block + i)
                if not block_data:
                    return None
                blocks.append(block_data)
            return blocks
            
        except Exception as e:
            print(f"[NFC] 读取扇区错误: {str(e)}")
            return None

    def write_classic_sector(self, sector, data_blocks, key='FFFFFFFFFFFF', key_type='A'):
        """写入整个扇区数据
        Args:
            sector: 扇区号(0-15)
            data_blocks: 3个数据块的列表(不包括尾块)
            key: 密钥
            key_type: 密钥类型(A/B)
        Returns:
            bool: 写入成功返回True
        """
        if not self.authenticate_sector(sector, key_type, key):
            print(f"[NFC] 扇区{sector}认证失败")
            return False
        
        try:
            start_block = sector * 4
            for i in range(3):  # 只写入前3个数据块，不写尾块
                if not self.write_classic_block(start_block + i, data_blocks[i]):
                    return False
            return True
            
        except Exception as e:
            print(f"[NFC] 写入扇区错误: {str(e)}")
            return False

    def auto_detect_device(self):
        """自动检测并连接NFC设备"""
        current_time = time.time()
        
        # 控制检查频率
        if current_time - self.last_device_check < self.device_check_interval:
            return self.initialized
            
        self.last_device_check = current_time
        print("[NFC] 开始自动检测设备...")
        
        try:
            # 如果已连接，检查设备是否仍然可用
            if self.initialized and self.serial_port and self.serial_port.is_open:
                try:
                    # 发送获取固件版本命令测试设备是否响应
                    test_cmd = bytes.fromhex('00 00 FF 02 FE D4 02 2A 00')
                    self.serial_port.write(test_cmd)
                    time.sleep(0.1)
                    
                    if self.serial_port.in_waiting:
                        response = self.serial_port.read(self.serial_port.in_waiting)
                        if response:  # 收到任何响应都认为设备在线
                            return True
                            
                    print("[NFC] 设备无响应")
                    self.initialized = False
                    
                except serial.SerialException as e:
                    print(f"[NFC] 串口通信错误: {str(e)}")
                    self.initialized = False
                    if self.serial_port and self.serial_port.is_open:
                        self.serial_port.close()
                    
            # 查找可用的USB串口设备
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                if 'USB' in p.description:  # 假设NFC读卡器是USB设备
                    print(f"[NFC] 发现USB设备: {p.description} ({p.device})")
                    if self.init_nfc_reader(port=p.device):
                        print(f"[NFC] 成功连接到设备: {p.device}")
                        return True
                        
            if not ports:
                print("[NFC] 未找到USB设备")
            return False
            
        except Exception as e:
            print(f"[NFC] 自动检测设备失败: {str(e)}")
            return False

    def get_device_status(self):
        """获取设备状态信息"""
        # 首先尝试自动检测设备
        self.auto_detect_device()
        
        status = {
            'connected': False,
            'port': None,
            'card_present': False,
            'card_id': None,
            'error': None
        }
        
        try:
            status['connected'] = self.initialized and self.serial_port and self.serial_port.is_open
            
            if status['connected']:
                status['port'] = self.serial_port.port
                
                # 检查卡片
                card_id = self.read_card_id()
                if card_id:
                    status['card_present'] = True
                    status['card_id'] = card_id
                    
        except Exception as e:
            status['error'] = str(e)
            print(f"[NFC] 获取状态失败: {str(e)}")
            
        return status

    def parse_nfc_data(self, hex_data):
        """解析NFC数据，处理特定的干扰字符
        Args:
            hex_data: 十六进制字符串
        Returns:
            dict: 解析后的数据字典
        """
        try:
            # 转换为ASCII字符串
            ascii_data = bytes.fromhex(hex_data).decode('ascii', errors='ignore')
            print(f"[NFC] 原始ASCII数据: {ascii_data}")
            
            # 提取基本结构：http开头的URL
            full_match = re.search(r'(http:[^|]+)', ascii_data)
            if not full_match:
                print("[NFC] 未找到有效URL格式")
                return None
            
            # 提取并清理URL
            base_url = full_match.group(1)
            print(f"[NFC] 清理后的URL: {base_url}")
            # 提取参数部分：从|后面开始，到T或;T之前的内容
            params_match = re.search(r'\|(.*?)(?=;?T[a-z]|$)', ascii_data)
            if params_match:
                params_str = params_match.group(1)
                print(f"[NFC] 找到参数字符串: {params_str}")
            else:
                print("[NFC] 未找到参数")
                print(f"[NFC] 尝试查找 '|' 位置: {ascii_data.find('|')}")
            print(f"[NFC] 原始参数字符串: {params_str}")
            
            # 清理并解析参数
            # 移除所有控制字符和可能的干扰
            clean_params_str = re.sub(r'[\x00-\x1F\x7F-\xFF]', '', params_str)
            clean_params_str = re.sub(r'\s+', '', clean_params_str)  # 移除所有空白字符
            
            # 解析参数对
            params = {}
            param_pairs = clean_params_str.split(';')
            for pair in param_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:  # 确保键值都不为空
                        params[key] = value
            
            print(f"[NFC] 解析后的参数: {params}")
            
            return {
                'url': base_url,
                'params': params,
                'ascii': ascii_data
            }
            
        except Exception as e:
            print(f"[NFC] 解析数据错误: {str(e)}")
            return None

def main():
    """主函数"""
    print("NFC读卡器测试程序")
    print("确保PCR532软件已关闭且设备已连接到COM7")
    
    nfc_device = NFC_Device()
    
    while True:
        print("\n请选择操作:")
        print("1. 读取卡片")
        print("2. 写入ASCII数据")
        print("3. 写入HEX数据")
        print("4. ASCII转HEX数据")
        print("5. 解码HEX数据")
        print("6. 读取卡片类型")
        print("7. 列出nfcpy可连接的设备")
        print("8. 退出")
        
        choice = input("请输入选项 (1-8): ")
        
        if choice == '1':
            nfc_device.test_device()
        elif choice == '2':
            data = input("请输入要写入的ASCII数据: ")
            nfc_device.write_data_to_card(data, is_ascii=True)
        elif choice == '3':
            data = input("请输入要写入的HEX数据: ")
            nfc_device.write_data_to_card(data, is_ascii=False)
        elif choice == '4':
            data = input("请输入要测试编码的ASCII数据: ")
            nfc_device.format_to_hex_test(data)
        elif choice == '5':
            data = input("请输入要解码的HEX数据: ")
            nfc_device.decode_hex_data_test(data)
        elif choice == '6':
            card_type = nfc_device.read_card_type()
            if card_type:
                print(f"[NFC] 检测到卡片类型: {card_type}")
            else:
                print("[NFC] 无法识别卡片类型")
        elif choice == '7':
            '''列出nfcpy可连接的设备'''
            try:
                device = nfc_device.init_nfc_reader()
            except Exception as e:
                print(f"Error listing devices: {str(e)}")
        elif choice == '8':
            print("程序退出")
            break
        else:
            print("无效选项，请重试")

if __name__ == "__main__":
    main()

