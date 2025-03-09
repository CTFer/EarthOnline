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
    SERVER_ERROR = 500   # 服务器错误
    
    # 业务相关状态码 (1000-1999)
    TASK_NOT_FOUND = 1001      # 任务不存在
    TASK_EXPIRED = 1002        # 任务已过期
    TASK_COMPLETED = 1003      # 任务已完成
    TASK_IN_PROGRESS = 1004    # 任务进行中
    TASK_NOT_AVAILABLE = 1005  # 任务不可用
    TASK_ACCEPT_FAILED = 1006  # 接受任务失败
    TASK_ABANDON_FAILED = 1007 # 放弃任务失败
    TASK_COMPLETE_FAILED = 1008 # 完成任务失败
    
    # 用户相关状态码 (2000-2999)
    USER_NOT_FOUND = 2001      # 用户不存在
    LOGIN_FAILED = 2002        # 登录失败
    TOKEN_EXPIRED = 2003       # Token过期
    PLAYER_NOT_FOUND = 2004    # 玩家不存在
    PLAYER_POINTS_NOT_ENOUGH = 2005  # 玩家积分不足
    PLAYER_LEVEL_NOT_ENOUGH = 2006   # 玩家等级不足
    PLAYER_BANNED = 2007            # 玩家被封禁
    
    # GPS相关状态码 (3000-3999)
    GPS_DATA_INVALID = 3001     # GPS数据无效
    GPS_RECORD_NOT_FOUND = 3002 # GPS记录不存在
    GPS_PERMISSION_DENIED = 3003 # GPS权限被拒绝
    GPS_SIGNAL_WEAK = 3004      # GPS信号弱
    GPS_SYNC_FAILED = 3005      # GPS同步失败
    
    # NFC相关状态码 (4000-4999)
    NFC_CARD_NOT_FOUND = 4001   # NFC卡片不存在
    NFC_DEVICE_ERROR = 4002     # NFC设备错误
    NFC_READ_ERROR = 4003       # NFC读取错误
    NFC_WRITE_ERROR = 4004      # NFC写入错误
    NFC_PERMISSION_DENIED = 4005 # NFC权限被拒绝
    
    # 商店相关状态码 (5000-5999)
    SHOP_ITEM_NOT_FOUND = 5001  # 商品不存在
    SHOP_ITEM_SOLD_OUT = 5002   # 商品已售罄
    SHOP_ITEM_EXPIRED = 5003    # 商品已过期
    SHOP_PURCHASE_FAILED = 5004  # 购买失败
    SHOP_ITEM_DISABLED = 5005   # 商品已下架
    
    # 微信相关状态码 (6000-6999)
    WECHAT_ERROR = 6001         # 微信通用错误
    WECHAT_AUTH_FAILED = 6002   # 微信认证失败
    WECHAT_API_ERROR = 6003     # 微信API调用错误
    WECHAT_MENU_ERROR = 6004    # 微信菜单操作错误
    WECHAT_MSG_ERROR = 6005     # 微信消息发送错误
    
    # 通知相关状态码 (7000-7999)
    NOTIFICATION_NOT_FOUND = 7001 # 通知不存在
    NOTIFICATION_SEND_FAILED = 7002 # 发送通知失败
    NOTIFICATION_READ_ERROR = 7003  # 标记通知已读失败
    
    # 勋章相关状态码 (8000-8999)
    MEDAL_NOT_FOUND = 8001      # 勋章不存在
    MEDAL_ALREADY_OWNED = 8002  # 已拥有该勋章
    MEDAL_CONDITION_NOT_MET = 8003 # 勋章获取条件未满足
    
    # 道具卡相关状态码 (9000-9999)
    GAME_CARD_NOT_FOUND = 9001  # 道具卡不存在
    GAME_CARD_USED = 9002       # 道具卡已使用
    GAME_CARD_EXPIRED = 9003    # 道具卡已过期
    GAME_CARD_INVALID = 9004    # 道具卡无效

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