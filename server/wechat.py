# -*- coding: utf-8 -*-
from flask import Blueprint, request
import logging
from function.WeChatService import wechat_service
from function.QYWeChatService import qywechat_service
from utils.response_handler import ResponseHandler, StatusCode, api_response
import xml.etree.ElementTree as ET

# 创建蓝图
wechat_bp = Blueprint('wechat', __name__)
logger = logging.getLogger(__name__)


@wechat_bp.route('/MP_verify_KtDy5Swi8adVxGhD.txt')
def mp_verify():
    """微信公众号域名验证"""
    return 'KtDy5Swi8adVxGhD'


@wechat_bp.route('/WW_verify_mMdUEG9xb15zsh7U.txt')
def qywechat_verify():
    """企业微信域名验证"""
    return 'mMdUEG9xb15zsh7U'


@wechat_bp.route('/', methods=['GET', 'POST'])
def wechat():
    """
    微信公众号接入接口
    GET: 验证服务器有效性
    POST: 处理微信消息和事件
    """
    try:
        if request.method == 'GET':
            # 获取参数
            signature = request.args.get('signature', '')
            timestamp = request.args.get('timestamp', '')
            nonce = request.args.get('nonce', '')
            echostr = request.args.get('echostr', '')

            logger.info(
                f"[WeChat] 收到验证请求: signature={signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")

            # 检查参数完整性
            if not all([signature, timestamp, nonce, echostr]):
                logger.error("[WeChat] 缺少必要的请求参数")
                return 'Missing parameters', 400

            # 检查签名
            if wechat_service.check_signature(signature, timestamp, nonce):
                logger.info("[WeChat] 签名验证通过，返回echostr")
                return echostr
            else:
                logger.warning("[WeChat] 签名验证失败")
                return 'Invalid signature', 403

        elif request.method == 'POST':
            # 获取原始消息数据
            xml_data = request.data
            logger.info(f"[WeChat] 收到消息推送: {xml_data}")
            
            # 使用企业微信服务处理加密消息
            # 传入消息签名、时间戳和随机数用于验证和解密
            response = wechat_service.handle_message(xml_data, msg_signature, timestamp, nonce)
            return response

    except Exception as e:
        logger.error(f"[WeChat] 处理请求失败: {str(e)}", exc_info=True)
        return 'Server error', 500


@wechat_bp.route('/access_token', methods=['GET'])
@api_response
def get_wechat_access_token():
    """获取微信access_token"""
    try:
        # 获取access_token
        access_token = wechat_service.get_access_token()
        return ResponseHandler.success(data={
            'access_token': access_token,
            'expires_in': 7200  # access_token有效期为2小时
        })
    except Exception as e:
        logger.error(f"[WeChat] 获取access_token失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"获取access_token失败: {str(e)}"
        )


@wechat_bp.route('/access_token/refresh', methods=['POST'])
@api_response
def refresh_wechat_access_token():
    """强制刷新微信access_token"""
    try:
        # 刷新access_token
        access_token = wechat_service.refresh_access_token()
        return ResponseHandler.success(data={
            'access_token': access_token,
            'expires_in': 7200  # access_token有效期为2小时
        })
    except Exception as e:
        logger.error(f"[WeChat] 刷新access_token失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"刷新access_token失败: {str(e)}"
        )


@wechat_bp.route('/menu/create', methods=['POST'])
@api_response
def create_wechat_menu():
    """创建微信自定义菜单"""
    try:
        success = wechat_service.create_menu()
        if success:
            return ResponseHandler.success(msg="自定义菜单创建成功")
        return ResponseHandler.error(
            code=StatusCode.WECHAT_MENU_ERROR,
            msg="自定义菜单创建失败"
        )
    except Exception as e:
        logger.error(f"[WeChat] 创建自定义菜单失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"创建自定义菜单失败: {str(e)}"
        )


@wechat_bp.route('/qy/access_token', methods=['GET'])
@api_response
def get_qywechat_access_token():
    """获取企业微信access_token"""
    try:
        # 获取access_token
        access_token = qywechat_service.get_access_token()
        return ResponseHandler.success(data={
            'access_token': access_token,
            'expires_in': 7200  # access_token有效期为2小时
        })
    except Exception as e:
        logger.error(f"[QYWeChat] 获取access_token失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"获取access_token失败: {str(e)}"
        )


@wechat_bp.route('/qy/access_token/refresh', methods=['POST'])
@api_response
def refresh_qywechat_access_token():
    """强制刷新企业微信access_token"""
    try:
        # 刷新access_token
        access_token = qywechat_service.refresh_access_token()
        return ResponseHandler.success(data={
            'access_token': access_token,
            'expires_in': 7200  # access_token有效期为2小时
        })
    except Exception as e:
        logger.error(f"[QYWeChat] 刷新access_token失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"刷新access_token失败: {str(e)}"
        )


@wechat_bp.route('/qy/message/send', methods=['POST'])
@api_response
def send_qywechat_message():
    """发送企业微信消息"""
    try:
        data = request.get_json()
        if not data or 'content' not in data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="缺少必要参数: content"
            )

        content = data['content']
        to_user = data.get('touser')
        to_party = data.get('toparty')
        to_tag = data.get('totag')
        safe = data.get('safe', 0)

        success, message = qywechat_service.send_text_message(
            content=content,
            to_user=to_user,
            to_party=to_party,
            to_tag=to_tag,
            safe=safe
        )

        if success:
            return ResponseHandler.success(msg=message)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_MSG_ERROR,
            msg=message
        )

    except Exception as e:
        logger.error(f"[QYWeChat] 发送消息失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"发送消息失败: {str(e)}"
        )


@wechat_bp.route('/qy/app/menu/create', methods=['POST'])
@api_response
def create_wechat_app_menu():
    """创建企业微信应用菜单"""
    menu_data = {
        "button": [
            {
                "name": "任务列表",
                "sub_button": [
                    {
                        "type": "click",
                        "name": "我的任务",
                        "key": "PLAYER_TASK"
                    },
                    {
                        "type": "click",
                        "name": "可用任务",
                        "key": "AVAIL_TASK"
                    }
                ]
            },
            {
                "type": "location_select",
                "name": "发送位置",
                "key": "SEND_LOCATION"
            }
        ]
    }
    success, message = qywechat_service.create_menu(menu_data)
    if success:
        return ResponseHandler.success(data=message, msg="菜单创建成功")
    return ResponseHandler.error(
        code=StatusCode.WECHAT_MENU_ERROR,
        msg=message
    )


@wechat_bp.route('/qy/menu', methods=['POST'])
@api_response
def create_qywechat_menu():
    """创建企业微信应用菜单"""
    try:
        menu_data = request.get_json()
        if not menu_data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="缺少菜单数据"
            )

        success, message = qywechat_service.create_menu(menu_data)
        if success:
            return ResponseHandler.success(msg=message)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_MENU_ERROR,
            msg=message
        )

    except Exception as e:
        logger.error(f"[QYWeChat] 创建菜单失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"创建菜单失败: {str(e)}"
        )


@wechat_bp.route('/qy/menu', methods=['GET'])
@api_response
def get_qywechat_menu():
    """获取企业微信应用菜单"""
    try:
        success, result = qywechat_service.get_menu()
        if success:
            return ResponseHandler.success(data=result)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_MENU_ERROR,
            msg=result
        )

    except Exception as e:
        logger.error(f"[QYWeChat] 获取菜单失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"获取菜单失败: {str(e)}"
        )


@wechat_bp.route('/qy/menu', methods=['DELETE'])
@api_response
def delete_qywechat_menu():
    """删除企业微信应用菜单"""
    try:
        success, message = qywechat_service.delete_menu()
        if success:
            return ResponseHandler.success(msg=message)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_MENU_ERROR,
            msg=message
        )

    except Exception as e:
        logger.error(f"[QYWeChat] 删除菜单失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"删除菜单失败: {str(e)}"
        )


@wechat_bp.route('/qy', methods=['GET', 'POST'])
def qywechat():
    """
    企业微信接入接口
    GET: 验证服务器有效性
    POST: 处理企业微信消息和事件
    """
    try:
        # 获取通用参数
        print(request.args)
        msg_signature = request.args.get('msg_signature', '')
        timestamp = request.args.get('timestamp', '')
        nonce = request.args.get('nonce', '')

        if request.method == 'GET':
            # 验证URL有效性
            echostr = request.args.get('echostr', '')

            logger.info(
                f"[QYWeChat] 收到URL验证请求: msg_signature={msg_signature}, timestamp={timestamp}, nonce={nonce}, echostr={echostr}")

            # 检查参数完整性
            if not all([msg_signature, timestamp, nonce, echostr]):
                logger.error("[QYWeChat] 缺少必要的请求参数")
                return 'Missing parameters', 400

            # 验证URL
            decrypted_str = qywechat_service.verify_url(
                msg_signature, timestamp, nonce, echostr)
            if decrypted_str:
                logger.info("[QYWeChat] URL验证成功")
                return decrypted_str
            else:
                logger.warning("[QYWeChat] URL验证失败")
                return 'Invalid signature', 403

        elif request.method == 'POST':
            # 获取原始消息数据
            xml_data = request.data
            logger.info(f"[QYWeChat] 收到消息推送: {xml_data}")
            
            # 使用企业微信服务处理加密消息
            # 传入消息签名、时间戳和随机数用于验证和解密
            response = qywechat_service.handle_message(xml_data, msg_signature, timestamp, nonce)
            return response

    except Exception as e:
        logger.error(f"[QYWeChat] 处理请求失败: {str(e)}", exc_info=True)
        return 'success'  # 返回success避免企业微信重试


@wechat_bp.route('/qy/template_card/update', methods=['POST'])
@api_response
def update_qywechat_template_card():
    """更新企业微信模板卡片"""
    try:
        data = request.get_json()
        if not data or 'response_code' not in data or 'template_card' not in data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="缺少必要参数"
            )

        success, message = qywechat_service.update_template_card(
            response_code=data['response_code'],
            template_card=data['template_card']
        )

        if success:
            return ResponseHandler.success(msg=message)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=message
        )

    except Exception as e:
        logger.error(f"[QYWeChat] 更新模板卡片失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"更新模板卡片失败: {str(e)}"
        )


@wechat_bp.route('/qy/task/send_card', methods=['POST'])
@api_response
def send_qywechat_task_card():
    """发送企业微信任务卡片消息"""
    try:
        data = request.get_json()
        if not data:
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="缺少请求数据"
            )

        # 验证必要参数
        required_fields = ['task_data']
        for field in required_fields:
            if field not in data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg=f"缺少必要参数: {field}"
                )

        # 获取可选参数
        to_user = data.get('touser')
        to_party = data.get('toparty')
        to_tag = data.get('totag')
        card_type = data.get('card_type', 'task_info')  # 默认为任务信息卡片

        # 发送任务卡片消息
        success, message = qywechat_service.send_task_card_message(
            to_user=to_user,
            to_party=to_party,
            to_tag=to_tag,
            task_data=data['task_data'],
            card_type=card_type
        )

        if success:
            return ResponseHandler.success(msg=message)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_MSG_ERROR,
            msg=message
        )

    except Exception as e:
        logger.error(f"[QYWeChat] 发送任务卡片消息失败: {str(e)}", exc_info=True)
        return ResponseHandler.error(
            code=StatusCode.WECHAT_API_ERROR,
            msg=f"发送任务卡片消息失败: {str(e)}"
        )
