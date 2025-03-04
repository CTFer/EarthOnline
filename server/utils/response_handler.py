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
    
    # 用户相关状态码 (2000-2999)
    USER_NOT_FOUND = 2001      # 用户不存在
    LOGIN_FAILED = 2002        # 登录失败
    TOKEN_EXPIRED = 2003       # Token过期
    
    # GPS相关状态码 (3000-3999)
    GPS_DATA_INVALID = 3001    # GPS数据无效
    GPS_RECORD_NOT_FOUND = 3002 # GPS记录不存在
    
    # NFC相关状态码 (4000-4999)
    NFC_CARD_NOT_FOUND = 4001  # NFC卡片不存在
    NFC_DEVICE_ERROR = 4002    # NFC设备错误

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