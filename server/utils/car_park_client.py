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
            "review_api_url": "http://1.95.11.164/car_park/review",
            "conn_str": "DRIVER={SQL Server};SERVER=localhost;DATABASE=Park_DB;UID=sa;PWD=123",
            "sync_interval": 10,  # 同步间隔（分钟）
            "max_retries": 3,     # 最大重试次数
            "retry_interval": 5   # 重试间隔（秒）
        }
        print(f"[调试] 默认配置内容:")
        print(f"[调试] DEBUG = True")
        print(f"[调试] CONFIG = {json.dumps(default_config, ensure_ascii=False, indent=2)}")
        print(f"[调试] HEADERS = {json.dumps({'X-API-Key': '95279527'}, ensure_ascii=False, indent=2)}")
        
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

# 设置日志
logger = setup_logging(DEBUG)

# 记录配置信息
logger.info("=== 加载配置信息 ===")
if DEBUG:
    logger.info(f"调试模式: {DEBUG}")
logger.info(f"API地址: {CONFIG['review_api_url']}")

# SQL Server日期时间转换工具类
class SQLServerDateConverter:
    """SQL Server日期时间转换工具类"""
    
    @staticmethod
    def sqlserver_hex_to_datetime(hex_value):
        """
        将SQL Server的十六进制DateTime表示转换为Python datetime对象
        
        参数:
            hex_value: SQL Server的十六进制日期时间字符串或整数
        
        返回:
            datetime对象
        """
        try:
            # 检查并提取十六进制值
            if isinstance(hex_value, str):
                # 处理CAST表达式
                cast_match = re.search(r'CAST\(0x([0-9A-Fa-f]+)\s+AS\s+DateTime\)', hex_value)
                if cast_match:
                    hex_value = '0x' + cast_match.group(1)
                
                # 确保有0x前缀
                if not hex_value.startswith('0x'):
                    hex_value = '0x' + hex_value
                    
                # 将十六进制字符串转换为整数
                hex_int = int(hex_value, 16)
            else:
                # 如果已经是整数，直接使用
                hex_int = hex_value
            
            # 提取日期部分(高4字节)：1900-01-01以来的天数
            days = hex_int >> 32
            
            # 提取时间部分(低4字节)：以300分之一秒为单位的时间数
            ticks = hex_int & 0xFFFFFFFF
            seconds = ticks / 300.0
            
            # 基准日期：1900-01-01
            base_date = datetime(1900, 1, 1)
            
            # 计算最终日期时间
            result_datetime = base_date + timedelta(days=days, seconds=seconds)
            
            return result_datetime
        except Exception as e:
            logger.error(f"十六进制转日期时间失败: {str(e)}")
            return None
    
    @staticmethod
    def datetime_to_sqlserver_hex(dt):
        """
        将Python datetime对象转换为SQL Server的十六进制DateTime表示
        
        参数:
            dt: datetime对象或符合'%Y-%m-%d %H:%M:%S'格式的字符串
        
        返回:
            (hex_str, hex_int): 十六进制字符串表示和对应的整数值
        """
        try:
            # 如果输入是字符串，转换为datetime对象
            if isinstance(dt, str):
                dt = datetime.strptime(dt, '%Y-%m-%d %H:%M:%S')
            
            # 基准日期：1900-01-01
            base_date = datetime(1900, 1, 1)
            
            # 计算与基准日期的差值
            delta = dt - base_date
            days = delta.days
            
            # 计算当天经过的秒数，并转换为300分之一秒
            seconds_since_midnight = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1000000.0
            ticks = int(seconds_since_midnight * 300)
            
            # 合并天数和时间刻度为一个8字节整数
            hex_int = (days << 32) | ticks
            
            # 转换为十六进制字符串
            hex_str = f"0x{hex_int:016X}"
            
            return (hex_str, hex_int)
        except Exception as e:
            logger.error(f"日期时间转SQL Server格式失败: {str(e)}")
            return (None, None)
    
    @staticmethod
    def format_datetime(dt_value, format='%Y-%m-%d %H:%M:%S'):
        """
        格式化日期时间对象为字符串
        
        参数:
            dt_value: datetime对象或SQL Server十六进制日期时间
            format: 输出格式
        
        返回:
            格式化的日期时间字符串
        """
        try:
            # 如果是十六进制字符串，先转换为datetime
            if isinstance(dt_value, str) and ('0x' in dt_value or 'CAST(' in dt_value):
                dt_value = SQLServerDateConverter.sqlserver_hex_to_datetime(dt_value)
            
            # 格式化为字符串
            if isinstance(dt_value, datetime):
                return dt_value.strftime(format)
            
            # 如果不是可识别的格式，返回原值
            return str(dt_value)
        except Exception as e:
            logger.error(f"日期时间格式化失败: {str(e)}")
            return "格式化错误"


# 创建全局转换器实例，方便其他模块直接导入使用
date_converter = SQLServerDateConverter()


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


class ParkingService:
    """停车场服务主类"""

    def __init__(self):
        self.last_check_time = datetime.now()
        self.review_api_url = CONFIG["review_api_url"]
        self.max_retries = 3  # 最大重试次数
        self.retry_interval = 5  # 重试间隔（秒）

    def check_remote_connection(self) -> bool:
        """
        检查与远程服务器的连接状态
        
        Returns:
            bool: 连接是否正常
        """
        logger.info("[调试] 开始检查远程服务器连接...")
        
        # 检查数据库连接
        try:
            with ParkingDB() as db:
                logger.info("[调试] 数据库连接测试成功")
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
                response = requests.get(
                    self.review_api_url,
                    headers=HEADERS,
                    timeout=10  # 设置超时时间
                )
                if response.status_code == 200:
                    logger.info("[调试] 远程API连接测试成功")
                    return True
                else:
                    logger.warning(f"[调试] 远程API响应异常 - 状态码: {response.status_code}")
                    
            except requests.RequestException as e:
                logger.warning(f"[调试] 远程API连接失败 (尝试 {retry_count + 1}/{self.max_retries}): {str(e)}")
                
            retry_count += 1
            if retry_count < self.max_retries:
                logger.info(f"[调试] 等待 {self.retry_interval} 秒后重试...")
                time.sleep(self.retry_interval)
        
        logger.error("[调试] 远程API连接检查失败，已达到最大重试次数")
        return False


    def get_pending_reviews(self):
        """获取待处理的续期请求"""
        try:
            
            response = requests.get(self.review_api_url, headers=HEADERS)
                        
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
            response = requests.post(self.review_api_url, json=data, headers=HEADERS)
            

            
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

    def process_review(self, review_info):
        """
        处理单个续期请求
        
        Args:
            review_info (dict): 续期请求信息，包含车牌号、车主、续期时长等信息
            
        Returns:
            bool: 处理是否成功
        """
        try:
            # 连接SQL Server数据库
            conn = pyodbc.connect(CONFIG["conn_str"])
            cursor = conn.cursor()

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
                logger.info(f"[调试] 当前车辆 {review_info['car_number']} 在Sys_Park_Plate表中的到期时间: {current_end_time}")
            else:
                logger.warning(f"[调试] 车辆 {review_info['car_number']} 在Sys_Park_Plate表中未找到记录")

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
                new_end_time = current_end_time + relativedelta(months=review_info["parktime"])
                new_end_time = new_end_time.replace(hour=23, minute=59, second=59, microsecond=0)
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

                # 提交事务
                conn.commit()
                logger.info(f"[调试] 数据库事务提交成功")

                # 更新续期状态为完成，传递车牌号
                self.update_review_status(
                    review_id=review_info["id"],
                    status="complete",
                    car_number=review_info["car_number"],
                    error_msg=f"{review_info['parktime']}个月，新的到期时间: {new_end_time}"
                )
            else:
                logger.info("[调试] DEBUG模式：跳过数据库更新操作")

            conn.close()
            logger.info(f"[调试] 处理续期请求成功: {review_info['car_number']}")
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

    def check_reviews(self):
        """检查并处理续期请求"""
        try:
            logger.info("检查续期请求")
            reviews = self.get_pending_reviews()
            for review in reviews:
                logger.info(f"处理续期请求: {review}")
                self.process_review(review)
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
        
        # 设置定时任务，每CONFIG["sync_interval"]分钟检查一次
        schedule.every(CONFIG["sync_interval"]).minutes.do(service.check_reviews)
        logger.info(f"[调试] 定时任务已设置：每{CONFIG['sync_interval']}分钟检查一次续期请求")

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
