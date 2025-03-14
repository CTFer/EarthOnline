"""
统一响应处理模块
包含状态码定义和统一的响应格式处理
"""
from flask import jsonify
from typing import Any, Optional, Union, Dict
import logging

logger = logging.getLogger(__name__)

class StatusCode:
    """状态码定义"""
    # 基础状态码 (0-999)
    SUCCESS = 0           # 成功
    FAIL = 1             # 一般性失败
    PARAM_ERROR = 400    # 参数错误
    UNAUTHORIZED = 401   # 未授权
    FORBIDDEN = 403      # 禁止访问
    NOT_FOUND = 404      # 资源不存在
    METHOD_NOT_ALLOWED = 405  # 方法不允许
    CONFLICT = 409       # 资源冲突
    SERVER_ERROR = 500   # 服务器错误
    SERVICE_UNAVAILABLE = 503  # 服务不可用
    
    # 认证相关状态码 (1000-1099)
    LOGIN_FAILED = 1000       # 登录失败
    TOKEN_EXPIRED = 1001      # Token过期
    TOKEN_INVALID = 1002      # Token无效
    SESSION_EXPIRED = 1003    # 会话过期
    INVALID_CREDENTIALS = 1004 # 无效的凭证
    ACCOUNT_LOCKED = 1005     # 账户被锁定
    ACCOUNT_DISABLED = 1006   # 账户被禁用
    PASSWORD_EXPIRED = 1007   # 密码过期
    
    # 用户相关状态码 (1100-1199)
    USER_NOT_FOUND = 1100     # 用户不存在
    USER_EXISTS = 1101        # 用户已存在
    USER_INACTIVE = 1102      # 用户未激活
    USER_BANNED = 1103        # 用户被封禁
    USER_DELETE_FAILED = 1104 # 删除用户失败
    USER_UPDATE_FAILED = 1105 # 更新用户失败
    USER_CREATE_FAILED = 1106 # 创建用户失败
    
    # 玩家相关状态码 (1200-1299)
    PLAYER_NOT_FOUND = 1200    # 玩家不存在
    PLAYER_EXISTS = 1201       # 玩家已存在
    PLAYER_BANNED = 1202       # 玩家被封禁
    PLAYER_LEVEL_LOW = 1203    # 玩家等级不足
    PLAYER_POINTS_LOW = 1204   # 玩家积分不足
    PLAYER_STAMINA_LOW = 1205  # 玩家体力不足
    PLAYER_INVENTORY_FULL = 1206 # 玩家背包已满
    
    # 任务相关状态码 (1300-1399)
    TASK_NOT_FOUND = 1300      # 任务不存在
    TASK_EXPIRED = 1301        # 任务已过期
    TASK_COMPLETED = 1302      # 任务已完成
    TASK_IN_PROGRESS = 1303    # 任务进行中
    TASK_NOT_AVAILABLE = 1304  # 任务不可用
    TASK_ACCEPT_FAILED = 1305  # 接受任务失败
    TASK_ABANDON_FAILED = 1306 # 放弃任务失败
    TASK_COMPLETE_FAILED = 1307 # 完成任务失败
    TASK_REWARD_FAILED = 1308  # 任务奖励发放失败
    
    # 道具相关状态码 (1400-1499)
    ITEM_NOT_FOUND = 1400      # 道具不存在
    ITEM_EXPIRED = 1401        # 道具已过期
    ITEM_USED = 1402          # 道具已使用
    ITEM_NOT_ENOUGH = 1403    # 道具数量不足
    ITEM_USE_FAILED = 1404    # 使用道具失败
    ITEM_CREATE_FAILED = 1405  # 创建道具失败
    ITEM_DELETE_FAILED = 1406  # 删除道具失败
    
    # 勋章相关状态码 (1500-1599)
    MEDAL_NOT_FOUND = 1500     # 勋章不存在
    MEDAL_ALREADY_OWNED = 1501 # 已拥有该勋章
    MEDAL_NOT_AVAILABLE = 1502 # 勋章不可获取
    MEDAL_CONDITION_NOT_MET = 1503 # 获取条件未满足
    MEDAL_GRANT_FAILED = 1504  # 授予勋章失败
    
    # NFC相关状态码 (1600-1699)
    NFC_CARD_NOT_FOUND = 1600  # NFC卡片不存在
    NFC_CARD_USED = 1601      # NFC卡片已使用
    NFC_CARD_INVALID = 1602   # NFC卡片无效
    NFC_DEVICE_ERROR = 1603   # NFC设备错误
    NFC_READ_ERROR = 1604     # 读取NFC失败
    NFC_WRITE_ERROR = 1605    # 写入NFC失败
    NFC_NOT_SUPPORTED = 1606  # 不支持NFC功能
    
    # 数据库相关状态码 (1700-1799)
    DB_CONNECTION_ERROR = 1700 # 数据库连接错误
    DB_QUERY_ERROR = 1701     # 数据库查询错误
    DB_UPDATE_ERROR = 1702    # 数据库更新错误
    DB_DELETE_ERROR = 1703    # 数据库删除错误
    DB_INSERT_ERROR = 1704    # 数据库插入错误
    DB_TRANSACTION_ERROR = 1705 # 事务处理错误
    
    # 文件相关状态码 (1800-1899)
    FILE_NOT_FOUND = 1800     # 文件不存在
    FILE_UPLOAD_FAILED = 1801 # 文件上传失败
    FILE_DELETE_FAILED = 1802 # 文件删除失败
    FILE_TOO_LARGE = 1803    # 文件太大
    FILE_TYPE_ERROR = 1804   # 文件类型错误
    
    # 通知相关状态码 (1900-1999)
    NOTIFICATION_NOT_FOUND = 1900 # 通知不存在
    NOTIFICATION_SEND_FAILED = 1901 # 发送通知失败
    NOTIFICATION_READ_ERROR = 1902 # 标记通知已读失败
    NOTIFICATION_DELETE_ERROR = 1903 # 删除通知失败
    
    # 系统相关状态码 (2000-2099)
    SYSTEM_MAINTENANCE = 2000  # 系统维护中
    SYSTEM_BUSY = 2001        # 系统繁忙
    SYSTEM_TIMEOUT = 2002     # 系统超时
    SYSTEM_CONFIG_ERROR = 2003 # 系统配置错误
    SYSTEM_VERSION_ERROR = 2004 # 系统版本错误

    @staticmethod
    def get_message(code: int) -> str:
        """获取状态码对应的默认消息"""
        messages = {
            # 基础状态码消息
            StatusCode.SUCCESS: "操作成功",
            StatusCode.FAIL: "操作失败",
            StatusCode.PARAM_ERROR: "参数错误",
            StatusCode.UNAUTHORIZED: "未授权",
            StatusCode.FORBIDDEN: "禁止访问",
            StatusCode.NOT_FOUND: "资源不存在",
            StatusCode.METHOD_NOT_ALLOWED: "不支持的请求方法",
            StatusCode.SERVER_ERROR: "服务器错误",
            
            # 任务相关状态码消息
            StatusCode.TASK_NOT_FOUND: "任务不存在",
            StatusCode.TASK_EXPIRED: "任务已过期",
            StatusCode.TASK_COMPLETED: "任务已完成",
            StatusCode.TASK_IN_PROGRESS: "任务进行中",
            StatusCode.TASK_NOT_AVAILABLE: "任务不可用",
            StatusCode.TASK_ACCEPT_FAILED: "接受任务失败",
            StatusCode.TASK_ABANDON_FAILED: "放弃任务失败",
            StatusCode.TASK_COMPLETE_FAILED: "完成任务失败",
            
            # 用户相关状态码消息
            StatusCode.USER_NOT_FOUND: "用户不存在",
            StatusCode.USER_EXISTS: "用户已存在",
            StatusCode.LOGIN_FAILED: "登录失败",
            StatusCode.ACCOUNT_DISABLED: "账户已禁用",
            StatusCode.ACCOUNT_LOCKED: "账户已锁定",
            
            # 数据库相关状态码消息
            StatusCode.DB_CONNECTION_ERROR: "数据库连接错误",
            StatusCode.DB_QUERY_ERROR: "数据库查询错误",
            StatusCode.DB_UPDATE_ERROR: "数据库更新错误"
        }
        return messages.get(code, "未知错误")

class ResponseHandler:
    """统一响应处理类"""
    
    @staticmethod
    def success(data: Any = None, msg: str = "success") -> Dict:
        """
        成功响应
        :param data: 响应数据
        :param msg: 响应消息
        :return: 统一格式的响应字典
        """
        return {
            "code": StatusCode.SUCCESS,
            "msg": msg,
            "data": data
        }
    
    @staticmethod
    def error(
        code: int = StatusCode.FAIL,
        msg: str = "操作失败",
        data: Any = None
    ) -> Dict:
        """
        错误响应
        :param code: 错误码
        :param msg: 错误消息
        :param data: 错误数据
        :return: 统一格式的响应字典
        """
        return {
            "code": code,
            "msg": msg,
            "data": data
        }
    
    @staticmethod
    def response(
        success: bool = True,
        data: Any = None,
        msg: str = None,
        code: int = None
    ) -> Dict:
        """
        通用响应
        :param success: 是否成功
        :param data: 响应数据
        :param msg: 响应消息
        :param code: 状态码
        :return: 统一格式的响应字典
        """
        if success:
            return ResponseHandler.success(data=data, msg=msg or "success")
        else:
            return ResponseHandler.error(
                code=code or StatusCode.FAIL,
                msg=msg or "操作失败",
                data=data
            )

def api_response(func):
    """
    API响应装饰器
    自动处理异常并包装响应
    """
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # 如果返回的已经是字典格式且包含code字段，直接返回
            if isinstance(result, dict) and "code" in result:
                return jsonify(result)
            # 否则包装为成功响应
            return jsonify(ResponseHandler.success(data=result))
        except Exception as e:
            logger.exception(f"API异常: {str(e)}")
            return jsonify(ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"服务器错误: {str(e)}"
            ))
    wrapper.__name__ = func.__name__
    return wrapper 