# -*- coding: utf-8 -*-
import pyodbc
from datetime import datetime, timedelta
import schedule
import time
import requests
import json
import logging
from dateutil.relativedelta import relativedelta
import sys
import os
import re
import psutil
import subprocess
import win32com.client
import win32process
import win32con
import win32gui
import urllib3


def disable_ssl_warnings():
    """禁用SSL警告"""
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def load_config():
    """
    加载配置文件

    Returns:
        tuple: (DEBUG, CONFIG, HEADERS)
    """
    try:
        # 获取可执行文件所在目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的可执行文件
            base_dir = os.path.dirname(sys.executable)
            print(f"[调试] 运行模式: 打包后的可执行文件")
            print(f"[调试] 程序目录: {base_dir}")
        else:
            # 如果是开发环境
            base_dir = os.path.dirname(os.path.abspath(__file__))
            print(f"[调试] 运行模式: 开发环境")
            print(f"[调试] 程序目录: {base_dir}")

        config_path = os.path.join(base_dir, 'config.json')
        print(f"[调试] 配置文件路径: {config_path}")

        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            print(f"[调试] 配置文件不存在: {config_path}")
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        else:
            print(f"[调试] 配置文件存在，准备读取")

        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        return (
            config_data.get("DEBUG", False),
            config_data.get("CONFIG", {}),
            config_data.get("HEADERS", {})
        )
    except Exception as e:
        print(f"[调试] 加载配置文件失败: {str(e)}")
        print("[调试] 使用默认配置")
        # 返回默认配置
        default_config = {
            "review_api_url": "https://1.95.11.164/car_park/review",
            "conn_str": "DRIVER={SQL Server};SERVER=localhost;DATABASE=Park_DB;UID=sa;PWD=123",
            "sync_interval": 10,  # 同步间隔（分钟）
            "sys_check_interval": 5,  # 系统检查间隔（分钟）
            "max_retries": 3,     # 最大重试次数
            "retry_interval": 5,  # 重试间隔（秒）
            "ssl_verify": False   # SSL证书验证，False表示跳过验证
        }
        print(f"[调试] 默认配置内容:")
        print(f"[调试] DEBUG = True")
        print(
            f"[调试] CONFIG = {json.dumps(default_config, ensure_ascii=False, indent=2)}")
        print(
            f"[调试] HEADERS = {json.dumps({'X-API-Key': '95279527'}, ensure_ascii=False, indent=2)}")

        return (
            True,  # 默认调试模式
            default_config,
            {
                "X-API-Key": "95279527"
            }
        )


def setup_logging(debug_mode):
    """
    设置日志配置

    Args:
        debug_mode (bool): 是否为调试模式
    """
    # 获取日志目录
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_file = os.path.join(log_dir, 'parking_service.log')

    # 配置日志
    logging.basicConfig(
            level=logging.DEBUG if debug_mode else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    return logging.getLogger('ParkingService')


# 加载配置
DEBUG, CONFIG, HEADERS = load_config()

# 禁用SSL警告
disable_ssl_warnings()

# 设置日志
logger = setup_logging(DEBUG)

# 记录配置信息
logger.info("=== 加载配置信息 ===")
if DEBUG:
    logger.info(f"调试模式: {DEBUG}")
logger.info(f"API地址: {CONFIG['review_api_url']}")


class ParkingDB:
    def __init__(self):
        """初始化数据库连接"""
        # 数据库连接配置
        self.conn_str = (CONFIG["conn_str"])

    def __enter__(self):
        """使用 with 语句进入上下文时建立连接和游标"""
        try:
            self.conn = pyodbc.connect(self.conn_str)
            self.cursor = self.conn.cursor()
            return self
        except pyodbc.Error as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """使用 with 语句退出上下文时关闭游标和连接"""
        if hasattr(self, 'cursor') and self.cursor:
            self.cursor.close()
        if hasattr(self, 'conn') and self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

    def get_current_end_time(self, plate_number):
        """获取当前车辆的包月结束时间"""
        try:
            query_sql = """
            SELECT endTime
            FROM Sys_Park_Plate
            WHERE plateNumber = ?
            """
            self.cursor.execute(query_sql, plate_number)
            row = self.cursor.fetchone()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"查询车辆包月结束时间失败: {str(e)}")
            return None

    def update_monthly_parking(self, plate_number, owner_name, months):
        """更新车辆包月信息"""
        try:
            # 获取当前结束时间
            current_end_time = self.get_current_end_time(plate_number)

            # 计算新的结束时间
            if current_end_time:
                new_end_time = current_end_time + relativedelta(months=months)
            else:
                # 如果是新车，从当前时间开始计算
                new_end_time = datetime.now() + relativedelta(months=months)
                current_end_time = datetime.now()

            # 更新车辆信息
            update_sql = """
            UPDATE Sys_Park_Plate 
            SET endTime = ?,
                upload_yun = 0,
                upload_yun2 = 0
            WHERE plateNumber = ?
            """
            self.cursor.execute(update_sql, (new_end_time, plate_number))

            # 记录操作日志
            log_sql = """
            INSERT INTO Sys_Park_PlateOperationRecords 
            (personName, plateNumber, OpType, OpTime, OpName, OpContent)
            VALUES (?, ?, 3, GETDATE(), ?, ?)
            """
            op_content = f"续约{months}个月,到期时间延长至{new_end_time}"
            self.cursor.execute(
                log_sql, (owner_name, plate_number, "自动续约系统", op_content))

            logger.info(f"车辆 {plate_number} 续约成功: {op_content}")
            return True
        except Exception as e:
            logger.error(f"更新车辆包月信息失败: {str(e)}")
            return False


class ParkSystemMonitor:
    """停车场系统监控类"""

    def __init__(self):
        self.process_name = "高清车牌识别收费系统V9.9.exe"
        self.process_path = r"D:\Program Files (x86)\ParkSystem\高清车牌识别收费系统V9.9.exe"
        self.process = None
        self.last_status = None
        self.restart_count = 0
        self.max_restarts = 3  # 最大重启次数
        self.restart_interval = 300  # 重启间隔（秒）
        self.last_restart_time = None

    def get_process_info(self):
        """获取进程信息"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
                if proc.info['name'] == self.process_name:
                    return {
                        'status': 'running',
                        'process_id': proc.info['pid'],
                        'memory_usage': f"{proc.info['memory_info'].rss / 1024 / 1024:.1f}MB",
                        'cpu_usage': f"{proc.info['cpu_percent']}%"
                    }
            return {
                'status': 'stopped',
                'process_id': None,
                'memory_usage': '0MB',
                'cpu_usage': '0%'
            }
        except Exception as e:
            logger.error(f"[Car_Park] 获取进程信息失败: {str(e)}")
            return {
                'status': 'error',
                'process_id': None,
                'memory_usage': 'unknown',
                'cpu_usage': 'unknown'
            }

    def start_process(self):
        """启动停车场系统进程"""
        try:
            # 检查是否已经在运行
            if self.is_process_running():
                logger.info("[Car_Park] 停车场系统已在运行")
                return True

            # 检查重启限制
            if self.restart_count >= self.max_restarts:
                if self.last_restart_time and (datetime.now() - self.last_restart_time).total_seconds() < self.restart_interval:
                    logger.warning("[Car_Park] 达到最大重启次数限制，等待冷却时间")
                    return False
                else:
                    # 重置重启计数
                    self.restart_count = 0

            # 启动进程
            subprocess.Popen(self.process_path)
            logger.info("[Car_Park] 启动停车场系统")

            # 更新重启信息
            self.restart_count += 1
            self.last_restart_time = datetime.now()
            return True

        except Exception as e:
            logger.error(f"[Car_Park] 启动停车场系统失败: {str(e)}")
            return False

    def is_process_running(self):
        """检查进程是否在运行"""
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] == self.process_name:
                    return True
            return False
        except Exception as e:
            logger.error(f"[Car_Park] 检查进程状态失败: {str(e)}")
            return False

    def check_and_restart(self):
        """检查并在需要时重启进程"""
        try:
            process_info = self.get_process_info()
            current_status = process_info['status']

            # 状态发生变化时记录日志
            if current_status != self.last_status:
                if current_status == 'running':
                    logger.info("[Car_Park] 停车场系统已启动运行")
                else:
                    logger.warning("[Car_Park] 停车场系统已停止运行")
                self.last_status = current_status

            # 如果进程不在运行，尝试重启
            if current_status != 'running':
                logger.warning("[Car_Park] 检测到停车场系统未运行，尝试重启")
                if self.start_process():
                    logger.info("[Car_Park] 停车场系统重启成功")
                else:
                    logger.error("[Car_Park] 停车场系统重启失败")

            return process_info

        except Exception as e:
            logger.error(f"[Car_Park] 检查和重启进程失败: {str(e)}")
            return {
                'status': 'error',
                'process_id': None,
                'memory_usage': 'unknown',
                'cpu_usage': 'unknown'
            }


class ParkingService:
    """停车场服务主类"""

    def __init__(self):
        self.last_check_time = datetime.now()
        self.review_api_url = CONFIG["review_api_url"]
        self.max_retries = CONFIG.get("max_retries", 3)  # 最大重试次数
        self.retry_interval = CONFIG.get("retry_interval", 5)  # 重试间隔（秒）
        self.park_system = ParkSystemMonitor()  # 添加系统监控实例

    def check_remote_connection(self) -> bool:
        """
        检查与远程服务器的连接状态

        Returns:
            bool: 连接是否正常
        """

        # 检查停车场系统状态
        process_info = self.park_system.check_and_restart()

        # 检查数据库连接
        try:
            with ParkingDB() as db:
                if DEBUG:
                    # 在调试模式下，测试查询操作
                    test_result = db.get_current_end_time("川AAB1234")
                    logger.info(f"[调试] 数据库查询测试结果: {test_result}")
        except Exception as e:
            logger.error(f"[调试] 数据库连接失败: {str(e)}")
            return False

        # 检查远程API连接
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                # 发送心跳包，包含停车场系统状态
                response = requests.get(
                    self.review_api_url.replace('/review', '/client_alive'),
                    params=process_info,
                    headers=HEADERS,
                    timeout=10,
                    verify=CONFIG.get('ssl_verify', False)  # 使用配置文件中的SSL验证设置
                )
                if response.status_code == 200:
                    logger.info(f"[调试] 远程API连接成功")
                    return True
                else:
                    logger.warning(
                        f"[调试] 远程API响应异常 - 状态码: {response.status_code}")

            except requests.RequestException as e:
                logger.warning(
                    f"[调试] 远程API连接失败 (尝试 {retry_count + 1}/{self.max_retries}): {str(e)}")

            retry_count += 1
            if retry_count < self.max_retries:
                logger.info(f"[调试] 等待 {self.retry_interval} 秒后重试...")
                time.sleep(self.retry_interval)

        logger.error("[调试] 远程API连接检查失败，已达到最大重试次数")
        return False

    def get_pending_reviews(self):
        """获取待处理的续期请求"""
        try:

            response = requests.get(self.review_api_url, headers=HEADERS, verify=CONFIG.get('ssl_verify', False))

            if response.status_code == 200:
                result = response.json()
                if result.get("code") == 0:
                    return result.get("data", [])
            return []
        except Exception as e:
            logger.error(f"获取续期请求异常: {str(e)}")
            return []

    def update_review_status(self, review_id, status, error_msg=None, car_number=None):
        """更新续期请求状态

        Args:
            review_id: 续期请求ID
            status: 状态（complete/failed）
            error_msg: 错误信息（可选）
            car_number: 车牌号（可选）
        """
        try:
            data = {
                "car_number": car_number,
                "status": status,
                "comment": error_msg
            }

            # 使用全局配置中的HEADERS
            response = requests.post(
                self.review_api_url, json=data, headers=HEADERS, verify=CONFIG.get('ssl_verify', False))

            # 检查响应状态
            if response.status_code == 401:
                logger.error(f"[调试] API密钥验证失败")
                logger.error(f"[调试] - 发送的Headers: {HEADERS}")
                logger.error(f"[调试] - 响应内容: {response.text}")
                return False

            return response.status_code == 200
        except Exception as e:
            logger.error(f"更新续期状态异常: {str(e)}")
            return False

    def _process_plate_change(self, review_info, conn, cursor):
        """
        处理车牌修改请求
        
        Args:
            review_info (dict): 修改请求信息
            conn: 数据库连接
            cursor: 数据库游标
            
        Returns:
            bool: 处理是否成功
        """
        try:
            old_plate = review_info["car_number"]
            new_plate = review_info.get("remark", "")  # 新车牌在remark字段中
            
            if not new_plate:
                logger.error(f"[调试] 车牌修改失败：缺少新车牌信息")
                return False
            
            logger.info(f"[调试] 开始处理车牌修改：{old_plate} -> {new_plate}")
            
            # 检查原车牌是否存在
            cursor.execute("""
                SELECT TOP 1 id, plateNumber, endTime, personId
                FROM Sys_Park_Plate
                WHERE plateNumber = ?
                ORDER BY endTime DESC
            """, old_plate)
            
            plate_row = cursor.fetchone()
            if not plate_row:
                logger.error(f"[调试] 原车牌 {old_plate} 不存在")
                return False
            
            plate_id, current_plate, end_time, person_id = plate_row
            
            # 检查新车牌是否已存在
            cursor.execute("""
                SELECT TOP 1 plateNumber
                FROM Sys_Park_Plate
                WHERE plateNumber = ?
            """, new_plate)
            
            if cursor.fetchone():
                logger.error(f"[调试] 新车牌 {new_plate} 已存在")
                return False
            
            if not DEBUG:
                try:
                    # 更新车牌号
                    cursor.execute("""
                        UPDATE Sys_Park_Plate 
                        SET plateNumber = ?,
                            upload_yun = 0,
                            upload_yun2 = 0
                        WHERE id = ?
                    """, (new_plate, plate_id))
                    
                    # 更新相关的Sys_Park_PlateCharge记录
                    cursor.execute("""
                        UPDATE Sys_Park_PlateCharge 
                        SET plateNumber = ?
                        WHERE plateNumber = ?
                    """, (new_plate, old_plate))
                    
                    # 更新状态为完成
                    if self.update_review_status(
                        review_id=review_info["id"],
                        status="changed",
                        car_number=old_plate,
                        error_msg=f"车牌由{old_plate}改为{new_plate}"
                    ):
                        conn.commit()
                        logger.info(f"[调试] 车牌修改成功：{old_plate} -> {new_plate}")
                        return True
                    else:
                        conn.rollback()
                        logger.error(f"[调试] 更新修改状态失败，回滚数据库操作")
                        return False
                        
                except Exception as e:
                    if conn:
                        conn.rollback()
                    logger.error(f"[调试] 车牌修改数据库操作异常，回滚事务: {str(e)}")
                    return False
            else:
                logger.info(f"[调试] DEBUG模式：跳过车牌修改数据库操作")
                return True
                
        except Exception as e:
            logger.error(f"[调试] 处理车牌修改请求失败: {str(e)}")
            return False

    def process_review(self, review_info):
        """
        处理单个续期请求

        Args:
            review_info (dict): 续期请求信息，包含车牌号、车主、续期时长等信息

        Returns:
            bool: 处理是否成功
        """
        conn = None
        cursor = None
        try:
            # 连接SQL Server数据库
            conn = pyodbc.connect(CONFIG["conn_str"])
            cursor = conn.cursor()

            # 检查是否为车牌修改请求
            if review_info.get("status") == "change":
                return self._process_plate_change(review_info, conn, cursor)

            # 获取Sys_Park_Plate中的当前记录
            cursor.execute("""
                SELECT TOP 1 plateNumber, endTime
                FROM Sys_Park_Plate
                WHERE plateNumber = ?
                ORDER BY endTime DESC
            """, review_info["car_number"])

            plate_row = cursor.fetchone()
            current_end_time = None

            if plate_row:
                current_end_time = plate_row[1]
                logger.info(
                    f"[调试] 当前车辆 {review_info['car_number']} 在Sys_Park_Plate表中的到期时间: {current_end_time}")
            else:
                logger.warning(
                    f"[调试] 车辆 {review_info['car_number']} 在Sys_Park_Plate表中未找到记录")

            # 获取Sys_Park_PlateCharge中的最新记录的所有字段
            cursor.execute("""
                SELECT TOP 1 
                    id, personName, personPhone, personAddress, pParkSpaceCount,
                    plateParkingSpaceName, plateNumber, authType, beginTime, endTime,
                    createTime, createName, receiveMoney, factMoney, upload_yun,
                    chargeType, personId, remark, yunPayChannel, yunPayTime,
                    yunOrderNumber, orderNumber, payCount, payUnit, upload_third,
                    upload_yun2, plateIdStr, personIdStr
                FROM Sys_Park_PlateCharge
                WHERE plateNumber = ?
                ORDER BY id DESC
            """, review_info["car_number"])

            charge_row = cursor.fetchone()
            charge_data = {}

            if charge_row:
                # 将查询结果转换为字典
                columns = [column[0] for column in cursor.description]
                charge_data = dict(zip(columns, charge_row))

            # 计算新的结束时间
            if current_end_time:
                # 注意：SQL Server的datetime格式为 YYYY-MM-DD HH:mm:ss.000
                new_end_time = current_end_time + \
                    relativedelta(months=review_info["parktime"])
                new_end_time = new_end_time.replace(
                    hour=23, minute=59, second=59, microsecond=0)
            else:
                # 如果是新车，从当前时间开始计算
                current_end_time = datetime.now()
                new_end_time = (current_end_time + relativedelta(months=review_info["parktime"])).replace(
                    hour=23, minute=59, second=59, microsecond=0
                )

            logger.info(f"[调试] 续期信息:")
            logger.info(f"[调试] - 车牌号: {review_info['car_number']}")
            logger.info(f"[调试] - 车主: {review_info['owner']}")
            logger.info(f"[调试] - 续期时长: {review_info['parktime']}个月")
            logger.info(f"[调试] - 当前到期时间: {current_end_time}")
            logger.info(f"[调试] - 新的到期时间: {new_end_time}")

            if not DEBUG:
                try:
                    # 1. 更新Sys_Park_Plate表
                    cursor.execute("""
                        UPDATE Sys_Park_Plate 
                        SET endTime = ?,
                            upload_yun = 0,
                            upload_yun2 = 0
                        WHERE plateNumber = ?
                    """, (new_end_time, review_info["car_number"]))

                    # 2. 插入新的Sys_Park_PlateCharge记录
                    insert_sql = """
                        INSERT INTO Sys_Park_PlateCharge 
                        (personName, personPhone, personAddress, pParkSpaceCount,
                        plateParkingSpaceName, plateNumber, authType, beginTime, endTime,
                        createTime, createName, receiveMoney, factMoney, upload_yun,
                        chargeType, personId, remark, yunPayChannel, yunPayTime,
                        yunOrderNumber, orderNumber, payCount, payUnit, upload_third,
                        upload_yun2, plateIdStr, personIdStr)
                        VALUES 
                        (?, ?, ?, ?, ?, ?, ?, ?, ?,
                         GETDATE(), ?, ?, ?, ?, ?, ?, ?, ?, ?,
                         ?, ?, ?, ?, ?, ?, ?, ?)
                    """

                    # 生成订单号
                    order_number = f"M{datetime.now().strftime('%Y%m%d%H%M%S')}"

                    # 准备插入数据，优先使用历史数据，必要时更新
                    insert_data = (
                        review_info["owner"],                          # personName
                        charge_data.get("personPhone", ""),           # personPhone
                        charge_data.get("personAddress", ""),         # personAddress
                        charge_data.get("pParkSpaceCount", 1),       # pParkSpaceCount
                        charge_data.get("plateParkingSpaceName", ""), # plateParkingSpaceName
                        review_info["car_number"],                    # plateNumber
                        charge_data.get("authType", 1),              # authType
                        current_end_time,                            # beginTime
                        new_end_time,                                # endTime
                        "自动续约系统",                              # createName
                        charge_data.get("receiveMoney", 0.0),        # receiveMoney
                        charge_data.get("factMoney", 0.0),           # factMoney
                        0,                                           # upload_yun
                        charge_data.get("chargeType", 1),            # chargeType
                        charge_data.get("personId", None),           # personId
                        f"自动续约{review_info['parktime']}个月",     # remark
                        charge_data.get("yunPayChannel", ""),        # yunPayChannel
                        None,                                        # yunPayTime
                        "",                                          # yunOrderNumber
                        order_number,                                # orderNumber
                        review_info["parktime"],                     # payCount
                        "月",                                        # payUnit
                        charge_data.get("upload_third", None),       # upload_third
                        0,                                           # upload_yun2
                        charge_data.get("plateIdStr", ""),           # plateIdStr
                        charge_data.get("personIdStr", "")           # personIdStr
                    )

                    cursor.execute(insert_sql, insert_data)

                    # 更新续期状态为完成，传递车牌号
                    if self.update_review_status(
                        review_id=review_info["id"],
                        status="complete",
                        car_number=review_info["car_number"],
                        error_msg=f"{review_info['parktime']}个月，新的到期时间: {new_end_time}"
                    ):
                        # 只有在更新状态成功后才提交事务
                        conn.commit()
                        logger.info(f"[调试] 数据库事务提交成功")
                        return True
                    else:
                        # 如果更新状态失败，回滚事务
                        conn.rollback()
                        logger.error(f"[调试] 更新续期状态失败，回滚数据库操作")
                        return False

                except Exception as e:
                    # 发生任何异常都回滚事务
                    if conn:
                        conn.rollback()
                    logger.error(f"[调试] 数据库操作异常，回滚事务: {str(e)}")
                    return False
            else:
                logger.info("[调试] DEBUG模式：跳过数据库更新操作")
                return True

        except Exception as e:
            error_msg = f"处理续期请求失败: {str(e)}"
            logger.error(f"[调试] {error_msg}")
            if not DEBUG:
                # 更新续期状态为失败，传递车牌号
                self.update_review_status(
                    review_id=review_info["id"],
                    status="failed",
                    error_msg=error_msg,
                    car_number=review_info["car_number"]
                )
            return False
        finally:
            # 确保关闭数据库连接
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def sync_parking_data(self) -> bool:
        """同步停车场数据到服务器"""
        conn = None
        cursor = None
        try:
            logger.info("[调试] 开始同步停车场数据...")

            # 连接SQL Server数据库
            conn = pyodbc.connect(CONFIG["conn_str"])
            cursor = conn.cursor()

            # 获取本地数据 - 根据实际表结构修改查询
            cursor.execute("""
                SELECT id, pName, pSex, departId, pAddress, pPhone, 
                       pParkSpaceCount, pNumber, upload_yun, IDCardNumber, 
                       upload_yun2, personIdStr, address1, address2, address3
                FROM Sys_Park_Person
            """)
            local_persons = []
            for row in cursor.fetchall():
                person = {}
                for idx, col in enumerate(cursor.description):
                    value = row[idx]
                    # 处理Decimal类型
                    if str(type(value)).find('Decimal') > -1:
                        person[col[0]] = float(value)
                    else:
                        person[col[0]] = value
                local_persons.append(person)

            cursor.execute("""
                SELECT id, personId, plateNumber, plateType, plateParkingSpaceName,
                       beginTime, endTime, createTime, authType, upload_yun,
                       cNumber, pChargeId, pRemark, balance, cardNumber,
                       plateStandard, thirdCount, upload_third, freeTime,
                       createName, plateIdStr, isDel, upload_yun2, parkHourMinutes
                FROM Sys_Park_Plate
            """)
            local_plates = []
            for row in cursor.fetchall():
                plate = {}
                for idx, col in enumerate(cursor.description):
                    value = row[idx]
                    # 处理日期时间字段
                    if isinstance(value, datetime):
                        plate[col[0]] = value.strftime('%Y-%m-%d %H:%M:%S')
                    # 处理Decimal类型（money字段）
                    elif str(type(value)).find('Decimal') > -1:
                        plate[col[0]] = float(value)
                    else:
                        plate[col[0]] = value
                local_plates.append(plate)

            # 获取服务器端数据
            car_park_url = CONFIG["review_api_url"].replace("/review", "/car_park")
            response = requests.get(
                car_park_url,
                headers=HEADERS,
                timeout=30,
                verify=CONFIG.get('ssl_verify', False)
            )

            if response.status_code != 200:
                logger.error(f"[调试] 获取服务器数据失败: {response.text}")
                return False

            server_data = response.json().get('data', {})
            server_persons = {p['id']: p for p in server_data.get('persons', [])}
            server_plates = {p['id']: p for p in server_data.get('plates', [])}

            # 对比数据，找出需要更新的记录
            persons_to_update = []
            plates_to_update = []

            # 对比人员数据
            for person in local_persons:
                server_person = server_persons.get(person['id'])
                if not server_person or self._is_record_different(person, server_person):
                    persons_to_update.append(person)

            # 对比车牌数据
            for plate in local_plates:
                server_plate = server_plates.get(plate['id'])
                if server_plate:
                    # 检查远端pRemark字段是否不为空，如果不为空则更新到本地
                    if server_plate.get('pRemark'):
                        try:
                            cursor.execute("""
                                UPDATE Sys_Park_Plate 
                                SET pRemark = ?
                                WHERE id = ?
                            """, (server_plate['pRemark'], plate['id']))
                            logger.info(f"[调试] 更新车牌 {plate['plateNumber']} 的pRemark字段为: {server_plate['pRemark']}")
                            # 同步更新本地数据
                            plate['pRemark'] = server_plate['pRemark']
                        except Exception as e:
                            logger.error(f"[调试] 更新车牌 {plate['plateNumber']} 的pRemark字段失败: {str(e)}")
                
                # 继续检查其他字段的差异
                if not server_plate or self._is_record_different(plate, server_plate):
                    plates_to_update.append(plate)

            # 提交pRemark更新
            try:
                conn.commit()
                logger.info("[调试] pRemark字段更新已提交")
            except Exception as e:
                logger.error(f"[调试] 提交pRemark更新失败: {str(e)}")
                conn.rollback()

            # 如果有差异，发送更新数据到服务器
            if persons_to_update or plates_to_update:
                logger.info(f"[调试] 发现数据差异 - {len(persons_to_update)}个人员, {len(plates_to_update)}个车牌需要更新")
                # 输出姓名列表
                person_names = [p['pName'] for p in persons_to_update]
                logger.info(f"[调试] 人员姓名列表: {person_names}")
                # 输出车牌列表
                plate_numbers = [p['plateNumber'] for p in plates_to_update]
                logger.info(f"[调试] 车牌列表: {plate_numbers}")

                # 确保所有日期时间字段都已转换为字符串
                for plate in plates_to_update:
                    for key in ['beginTime', 'endTime', 'createTime']:
                        if isinstance(plate.get(key), datetime):
                            plate[key] = plate[key].strftime('%Y-%m-%d %H:%M:%S')
                    # 确保金额字段为浮点数
                    if 'balance' in plate and str(type(plate['balance'])).find('Decimal') > -1:
                        plate['balance'] = float(plate['balance'])

                sync_data = {
                    "persons": persons_to_update,
                    "plates": plates_to_update
                }

                response = requests.post(
                    car_park_url,
                    json=sync_data,
                    headers=HEADERS,
                    timeout=30,
                    verify=CONFIG.get('ssl_verify', False)
                )

                if response.status_code == 200:
                    logger.info("[调试] 数据差异同步成功")
                    return True
                else:
                    logger.error(f"[调试] 数据差异同步失败: {response.text}")
                    return False
            else:
                logger.info("[调试] 数据无差异，无需同步")
                return True

        except Exception as e:
            logger.error(f"[调试] 同步停车场数据异常: {str(e)}")
            return False
        finally:
            # 确保在所有操作完成后关闭游标和连接
            if cursor:
                try:
                    cursor.close()
                except Exception as e:
                    logger.error(f"[调试] 关闭游标失败: {str(e)}")
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"[调试] 关闭数据库连接失败: {str(e)}")

    def _is_record_different(self, local_record: dict, server_record: dict) -> bool:
        """比较两条记录是否有差异"""
        try:
            # 转换日期时间字段为字符串进行比较
            local_copy = local_record.copy()
            server_copy = server_record.copy()

            for field in ['beginTime', 'endTime', 'createTime']:
                if field in local_copy and isinstance(local_copy[field], datetime):
                    local_copy[field] = local_copy[field].strftime(
                        '%Y-%m-%d %H:%M:%S')
                if field in server_copy and isinstance(server_copy[field], datetime):
                    server_copy[field] = server_copy[field].strftime(
                        '%Y-%m-%d %H:%M:%S')

            return local_copy != server_copy
        except Exception as e:
            logger.error(f"[调试] 比较记录差异异常: {str(e)}")
            return True  # 如果比较出错，认为有差异

    def check_reviews(self):
        """检查并处理续期请求"""
        try:
            logger.info("检查续期请求")
            # 检查check_remote_connection状态
            if not self.check_remote_connection():
                logger.error("[调试] 无法连接到远端服务器，服务启动失败")
                return
            reviews = self.get_pending_reviews()
            has_updates = False
            for review in reviews:
                logger.info(f"处理续期请求: {review}")
                if self.process_review(review):
                    has_updates = True

            # 如果有更新，同步数据到服务器
            if has_updates:
                logger.info("[调试] 续期处理完成，开始同步数据...")
                self.sync_parking_data()

        except Exception as e:
            logger.error(f"检查续期请求异常: {str(e)}")


def run_service():
    """运行服务"""
    try:
        service = ParkingService()

        # 检查与远端服务器的连接
        if not service.check_remote_connection():
            logger.error("[调试] 无法连接到远端服务器，服务启动失败")
            if DEBUG:
                logger.info("[调试] DEBUG模式：继续运行以进行测试")
            else:
                return

        service.sync_parking_data()
        logger.info("同步停车场数据完成")

        # 设置定时任务
        schedule.every(CONFIG["sync_interval"]).minutes.do(
            service.check_reviews)
        schedule.every(CONFIG["sys_check_interval"]).minutes.do(
            service.check_remote_connection)  # 每5分钟检查一次连接和进程状态

        logger.info(f"[调试] 定时任务已设置：")
        logger.info(f"[调试] - 每{CONFIG['sync_interval']}分钟检查一次续期请求")
        logger.info(f"[调试] - 每{CONFIG['sys_check_interval']}分钟检查一次系统状态")
        logger.info("[调试] 停车场自动续约服务已启动...")

        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except Exception as e:
                    logger.error(f"[调试] 服务运行异常: {str(e)}")
                    if DEBUG:
                        logger.info("[调试] DEBUG模式：继续运行以进行测试")
                        time.sleep(60)  # 发生异常时等待1分钟后继续
                    else:
                        # 非调试模式下，检查连接状态
                        if not service.check_remote_connection():
                            logger.error("[调试] 服务异常且无法连接到远端服务器，即将退出")
                            break
                        time.sleep(60)  # 等待1分钟后继续

    except Exception as e:
        logger.error(f"[调试] 服务启动失败: {str(e)}")
        if not DEBUG:
            raise  # 非调试模式下抛出异常


if __name__ == "__main__":
    if DEBUG:
        logger.info("=== DEBUG模式启动 ===")
        # 测试数据库连接
        service = ParkingService()
        if service.check_remote_connection():
            logger.info("远程连接测试成功")
            # 测试查询车辆
            with ParkingDB() as db:
                test_plate = "川AAB1234"
                result = db.get_current_end_time(test_plate)
                logger.info(f"测试查询车辆 {test_plate} 结果: {result}")
    else:
            logger.warning("远程连接测试失败")

    run_service()
