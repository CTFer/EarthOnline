# -*- coding: utf-8 -*-
import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from config.private import QYWECHAT_CORP_ID, QYWECHAT_AGENT_ID, QYWECHAT_CORP_SECRET
from Crypto.Cipher import AES
import base64
import json
import random
import string
import struct
import requests
import threading
from utils.response_handler import ResponseHandler, StatusCode
import os

logger = logging.getLogger(__name__)

class AccessToken:
    """访问令牌类，用于存储和管理access_token"""
    def __init__(self):
        self.access_token = None
        self.expires_time = 0  # 过期时间戳
        self.lock = threading.Lock()  # 用于线程安全

class QYWeChatService:
    """企业微信服务类"""
    
    def __init__(self):
        """初始化企业微信服务"""
        self.corp_id = QYWECHAT_CORP_ID
        self.agent_id = QYWECHAT_AGENT_ID
        self.corp_secret = QYWECHAT_CORP_SECRET
        self._access_token = AccessToken()  # 用于存储access_token
        
    def get_access_token(self):
        """
        获取access_token
        如果access_token已过期，会自动刷新
        :return: access_token
        """
        with self._access_token.lock:
            now = int(time.time())
            
            # 如果access_token还有效且距离过期还有超过5分钟，直接返回
            if (self._access_token.access_token and 
                self._access_token.expires_time - now > 300):  # 留5分钟余量
                return self._access_token.access_token
                
            # 需要刷新access_token
            try:
                url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
                params = {
                    "corpid": self.corp_id,
                    "corpsecret": self.corp_secret
                }
                
                logger.info("[QYWeChat] 开始获取access_token")
                response = requests.get(url, params=params)
                result = response.json()
                
                if "access_token" in result:
                    self._access_token.access_token = result["access_token"]
                    self._access_token.expires_time = now + result["expires_in"]
                    logger.info("[QYWeChat] 成功获取access_token")
                    return self._access_token.access_token
                else:
                    error_code = result.get("errcode", "未知")
                    error_msg = result.get("errmsg", "未知错误")
                    logger.error(f"[QYWeChat] 获取access_token失败: [{error_code}] {error_msg}")
                    raise Exception(f"获取access_token失败: [{error_code}] {error_msg}")
                    
            except Exception as e:
                logger.error(f"[QYWeChat] 获取access_token异常: {str(e)}", exc_info=True)
                raise
                
    def refresh_access_token(self):
        """
        强制刷新access_token
        :return: 新的access_token
        """
        with self._access_token.lock:
            # 清空当前的access_token
            self._access_token.access_token = None
            self._access_token.expires_time = 0
            
            # 重新获取
            return self.get_access_token()

    def send_text_message(self, content, to_user=None, to_party=None, to_tag=None, safe=0):
        """
        发送文本消息
        :param content: 消息内容
        :param to_user: 指定接收消息的成员，成员ID列表（多个接收者用'|'分隔）
        :param to_party: 指定接收消息的部门，部门ID列表（多个接收者用'|'分隔）
        :param to_tag: 指定接收消息的标签，标签ID列表（多个接收者用'|'分隔）
        :param safe: 表示是否是保密消息，0表示可对外分享，1表示不能分享且内容显示水印
        :return: 发送结果
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            data = {
                "msgtype": "text",
                "agentid": self.agent_id,
                "text": {
                    "content": content
                },
                "safe": safe
            }
            
            # 设置接收者
            if to_user:
                data["touser"] = to_user
            if to_party:
                data["toparty"] = to_party
            if to_tag:
                data["totag"] = to_tag
                
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 消息发送成功")
                return True, "消息发送成功"
            else:
                error_msg = f"消息发送失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 发送消息异常: {str(e)}", exc_info=True)
            return False, f"发送消息异常: {str(e)}"

    def create_menu(self, menu_data):
        """
        创建应用菜单
        :param menu_data: 菜单数据，格式参考企业微信文档
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/menu/create?access_token={access_token}&agentid={self.agent_id}"
            
            response = requests.post(url, json=menu_data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 应用菜单创建成功")
                return True, "应用菜单创建成功"
            else:
                error_msg = f"应用菜单创建失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 创建应用菜单异常: {str(e)}", exc_info=True)
            return False, f"创建应用菜单异常: {str(e)}"

    def get_menu(self):
        """
        获取应用菜单
        :return: 菜单数据
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/menu/get?access_token={access_token}&agentid={self.agent_id}"
            
            response = requests.get(url)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 获取应用菜单成功")
                return True, result.get("button", [])
            else:
                error_msg = f"获取应用菜单失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取应用菜单异常: {str(e)}", exc_info=True)
            return False, f"获取应用菜单异常: {str(e)}"

    def delete_menu(self):
        """
        删除应用菜单
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/menu/delete?access_token={access_token}&agentid={self.agent_id}"
            
            response = requests.get(url)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 应用菜单删除成功")
                return True, "应用菜单删除成功"
            else:
                error_msg = f"应用菜单删除失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 删除应用菜单异常: {str(e)}", exc_info=True)
            return False, f"删除应用菜单异常: {str(e)}"

    def handle_message(self, xml_data, msg_signature=None, timestamp=None, nonce=None):
        """
        处理企业微信消息和事件
        :param xml_data: 原始XML消息数据
        :param msg_signature: 消息签名
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: 响应消息
        """
        try:
            xml_str = xml_data.decode('utf-8')
            logger.info(f"[QYWeChat] 收到原始消息: {xml_str}")
            
            # 解析XML
            root = ET.fromstring(xml_str)
            
            # 获取消息基本信息
            msg_type = root.find('MsgType').text
            from_user = root.find('FromUserName').text
            to_user = root.find('ToUserName').text
            create_time = root.find('CreateTime').text
            agent_id = root.find('AgentID').text if root.find('AgentID') is not None else None
            
            logger.info(f"[QYWeChat] 消息类型: {msg_type}")
            logger.info(f"[QYWeChat] 发送者UserID: {from_user}")
            logger.info(f"[QYWeChat] 接收者: {to_user}")
            logger.info(f"[QYWeChat] 消息创建时间: {create_time}")
            logger.info(f"[QYWeChat] 应用ID: {agent_id}")
            
            # 根据消息类型处理
            if msg_type == 'event':
                return self._handle_event(root, from_user, to_user)
            else:
                logger.warning(f"[QYWeChat] 未处理的消息类型: {msg_type}")
                return 'success'
                
        except Exception as e:
            logger.error(f"[QYWeChat] 处理消息失败: {str(e)}", exc_info=True)
            return 'success'  # 即使处理失败也返回success，避免企业微信重试

    def _handle_event(self, root, from_user, to_user):
        """
        处理事件消息
        :param root: XML根节点
        :param from_user: 发送者UserID
        :param to_user: 接收者
        :return: 响应消息
        """
        try:
            event = root.find('Event').text.lower()
            logger.info(f"[QYWeChat] 收到事件: {event}")
            
            if event == 'location_select':
                # 处理弹出地理位置选择器的事件
                location = root.find('SendLocationInfo')
                if location is not None:
                    location_x = location.find('Location_X').text  # 纬度
                    location_y = location.find('Location_Y').text  # 经度
                    scale = location.find('Scale').text  # 精度
                    label = location.find('Label').text  # 位置名称
                    poiname = location.find('Poiname').text  # POI名称
                    
                    logger.info(f"[QYWeChat] 用户选择位置 - 位置: {label}, 经度: {location_y}, 纬度: {location_x}, 精度: {scale}, POI: {poiname}")
                    
                    # 这里可以添加位置处理逻辑
                    
            elif event == 'template_card_event':
                # 处理模板卡片事件
                card_type = root.find('CardType').text
                task_id = root.find('TaskId').text
                response_code = root.find('ResponseCode').text
                
                logger.info(f"[QYWeChat] 模板卡片事件 - 类型: {card_type}, 任务ID: {task_id}, 响应码: {response_code}")
                
                # 处理不同类型的模板卡片
                if card_type == 'text_notice':
                    # 处理文本通知类型卡片
                    pass
                elif card_type == 'button_interaction':
                    # 处理按钮交互型卡片
                    pass
                elif card_type == 'vote_interaction':
                    # 处理投票选择型卡片
                    pass
                
                
            elif event == 'sys_photo':
                # 处理系统拍照发图事件
                count = root.find('Count').text
                pic_md5_sum = root.find('PicMd5Sum').text
                logger.info(f"[QYWeChat] 系统拍照发图 - 数量: {count}, 图片MD5: {pic_md5_sum}")
                
            return 'success'
            
        except Exception as e:
            logger.error(f"[QYWeChat] 处理事件失败: {str(e)}", exc_info=True)
            return 'success'

    def update_template_card(self, response_code, template_card):
        """
        更新模板卡片消息
        :param response_code: 更新模板卡片的response_code
        :param template_card: 模板卡片数据
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/update_template_card?access_token={access_token}"
            
            data = {
                "response_code": response_code,
                "template_card": template_card
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 模板卡片更新成功")
                return True, "模板卡片更新成功"
            else:
                error_msg = f"模板卡片更新失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 更新模板卡片异常: {str(e)}", exc_info=True)
            return False, f"更新模板卡片异常: {str(e)}"

    def send_task_card_message(self, to_user=None, to_party=None, to_tag=None, task_data=None, card_type='task_info'):
        """
        发送任务相关的模板卡片消息
        :param to_user: 指定接收消息的成员
        :param to_party: 指定接收消息的部门
        :param to_tag: 指定接收消息的标签
        :param task_data: 任务数据
        :param card_type: 卡片类型(task_info: 任务信息, current_task: 当前任务)
        :return: (success, message)
        """
        try:
            from function.TaskService import task_service
            
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            
            # 构建基础消息数据
            data = {
                "touser": to_user,
                "toparty": to_party,
                "totag": to_tag,
                "msgtype": "template_card",
                "agentid": self.agent_id,
                "enable_id_trans": 0,
                "enable_duplicate_check": 1,
                "duplicate_check_interval": 1800
            }
            
            if card_type == 'task_info':
                # 获取任务详情
                task_info = task_service.get_task_by_id(task_data['task_id'])
                if task_info.get('code') != 0:
                    raise Exception(task_info.get('msg', '获取任务信息失败'))
                    
                task = task_info['data']
                
                # 构建任务信息卡片
                data["template_card"] = {
                    "card_type": "text_notice",
                    "source": {
                        "icon_url": task.get('icon', ''),
                        "desc": "任务系统",
                        "desc_color": 1
                    },
                    "main_title": {
                        "title": task['name'],
                        "desc": f"任务类型：{task['task_type']}"
                    },
                    "emphasis_content": {
                        "title": task.get('points', 0),
                        "desc": "任务积分"
                    },
                    "sub_title_text": task['description'],
                    "horizontal_content_list": [
                        {
                            "keyname": "体力消耗",
                            "value": str(task.get('stamina_cost', 0)),
                            "type": 1
                        },
                        {
                            "keyname": "时间限制",
                            "value": f"{task.get('limit_time', 0)}小时",
                            "type": 1
                        }
                    ],
                    "jump_list": [
                        {
                            "type": 1,
                            "title": "查看详情",
                            "url": f"https://example.com/task/{task['id']}"
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": f"https://example.com/task/{task['id']}"
                    }
                }
            
            elif card_type == 'current_task':
                # 获取当前任务详情
                current_task = task_service.get_current_task_by_id(task_data['task_id'])
                if current_task.get('code') != 0:
                    raise Exception(current_task.get('msg', '获取当前任务信息失败'))
                    
                task = current_task['data']
                
                # 计算剩余时间
                remaining_time = ""
                if task.get('endtime'):
                    current_time = int(time.time())
                    remaining_seconds = task['endtime'] - current_time
                    if remaining_seconds > 0:
                        remaining_hours = remaining_seconds // 3600
                        remaining_minutes = (remaining_seconds % 3600) // 60
                        remaining_time = f"{remaining_hours}小时{remaining_minutes}分钟"
                    else:
                        remaining_time = "已超时"
                
                # 构建当前任务卡片
                data["template_card"] = {
                    "card_type": "button_interaction",
                    "source": {
                        "icon_url": task.get('icon', ''),
                        "desc": "进行中的任务",
                        "desc_color": 1
                    },
                    "main_title": {
                        "title": task['name'],
                        "desc": f"状态：{task['status']}"
                    },
                    "sub_title_text": task['description'],
                    "horizontal_content_list": [
                        {
                            "keyname": "开始时间",
                            "value": time.strftime("%Y-%m-%d %H:%M", time.localtime(task['starttime'])),
                            "type": 1
                        },
                        {
                            "keyname": "剩余时间",
                            "value": remaining_time,
                            "type": 1
                        }
                    ],
                    "jump_list": [
                        {
                            "type": 1,
                            "title": "查看详情",
                            "url": f"https://example.com/task/{task['id']}"
                        }
                    ],
                    "card_action": {
                        "type": 1,
                        "url": f"https://example.com/task/{task['id']}"
                    },
                    "button_selection": {
                        "question_key": "task_action",
                        "title": "任务操作",
                        "option_list": [
                            {
                                "id": "complete",
                                "text": "完成任务"
                            },
                            {
                                "id": "abandon",
                                "text": "放弃任务"
                            }
                        ]
                    }
                }
            
            # 发送消息
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info("[QYWeChat] 模板卡片消息发送成功")
                return True, "消息发送成功"
            else:
                error_msg = f"消息发送失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 发送模板卡片消息异常: {str(e)}", exc_info=True)
            return False, f"发送消息异常: {str(e)}"

    def upload_file_to_wecom(self, file_path, file_name=None):
        """
        上传文件到企业微信微盘
        :param file_path: 文件本地路径
        :param file_name: 文件名称（可选）
        :return: (success, file_id或错误信息)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_upload?access_token={access_token}"
            
            # 准备文件数据
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name or os.path.basename(file_path), f, 'application/octet-stream')
                }
                
                logger.info(f"[QYWeChat] 开始上传文件: {file_name or os.path.basename(file_path)}")
                response = requests.post(url, files=files)
                result = response.json()
                
                if result.get("errcode") == 0:
                    file_id = result.get("file_id")
                    logger.info(f"[QYWeChat] 文件上传成功，file_id: {file_id}")
                    return True, file_id
                else:
                    error_msg = f"文件上传失败: [{result.get('errcode')}] {result.get('errmsg')}"
                    logger.error(f"[QYWeChat] {error_msg}")
                    return False, error_msg
                    
        except Exception as e:
            logger.error(f"[QYWeChat] 上传文件异常: {str(e)}", exc_info=True)
            return False, f"上传文件异常: {str(e)}"

    def download_file_from_wecom(self, file_id, save_path):
        """
        从企业微信微盘下载文件
        :param file_id: 文件ID
        :param save_path: 保存路径
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_download?access_token={access_token}"
            
            data = {
                "file_id": file_id
            }
            
            logger.info(f"[QYWeChat] 开始下载文件: {file_id}")
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"[QYWeChat] 文件下载成功，保存至: {save_path}")
                return True, "文件下载成功"
            else:
                result = response.json()
                error_msg = f"文件下载失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 下载文件异常: {str(e)}", exc_info=True)
            return False, f"下载文件异常: {str(e)}"

    def create_wecom_file(self, file_id, file_name, parent_id=""):
        """
        在企业微信微盘创建文件
        :param file_id: 文件ID（通过上传接口获取）
        :param file_name: 文件名称
        :param parent_id: 父目录ID（可选）
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_create?access_token={access_token}"
            
            data = {
                "file_id": file_id,
                "file_name": file_name,
                "parent_id": parent_id
            }
            
            logger.info(f"[QYWeChat] 开始创建文件: {file_name}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件创建成功")
                return True, "文件创建成功"
            else:
                error_msg = f"文件创建失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 创建文件异常: {str(e)}", exc_info=True)
            return False, f"创建文件异常: {str(e)}"

    def delete_wecom_file(self, file_id):
        """
        删除企业微信微盘文件
        :param file_id: 文件ID
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_delete?access_token={access_token}"
            
            data = {
                "file_id": file_id
            }
            
            logger.info(f"[QYWeChat] 开始删除文件: {file_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件删除成功")
                return True, "文件删除成功"
            else:
                error_msg = f"文件删除失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 删除文件异常: {str(e)}", exc_info=True)
            return False, f"删除文件异常: {str(e)}"

    def rename_wecom_file(self, file_id, new_name):
        """
        重命名企业微信微盘文件
        :param file_id: 文件ID
        :param new_name: 新文件名
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_rename?access_token={access_token}"
            
            data = {
                "file_id": file_id,
                "new_name": new_name
            }
            
            logger.info(f"[QYWeChat] 开始重命名文件: {file_id} -> {new_name}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件重命名成功")
                return True, "文件重命名成功"
            else:
                error_msg = f"文件重命名失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 重命名文件异常: {str(e)}", exc_info=True)
            return False, f"重命名文件异常: {str(e)}"

    def move_wecom_file(self, file_id, parent_id="", replace=False):
        """
        移动企业微信微盘文件
        :param file_id: 文件ID
        :param parent_id: 目标目录ID
        :param replace: 是否覆盖同名文件
        :return: (success, message)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_move?access_token={access_token}"
            
            data = {
                "file_id": file_id,
                "parent_id": parent_id,
                "replace": replace
            }
            
            logger.info(f"[QYWeChat] 开始移动文件: {file_id} -> {parent_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 文件移动成功")
                return True, "文件移动成功"
            else:
                error_msg = f"文件移动失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 移动文件异常: {str(e)}", exc_info=True)
            return False, f"移动文件异常: {str(e)}"

    def list_wecom_files(self, parent_id="", sort_type=0, start=0, limit=50):
        """
        获取企业微信微盘文件列表
        :param parent_id: 父目录ID
        :param sort_type: 排序类型（0:名字升序 1:名字降序 2:大小升序 3:大小降序 4:修改时间升序 5:修改时间降序）
        :param start: 起始位置
        :param limit: 拉取数量
        :return: (success, file_list或错误信息)
        """
        try:
            access_token = self.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_list?access_token={access_token}"
            
            data = {
                "parent_id": parent_id,
                "sort_type": sort_type,
                "start": start,
                "limit": limit
            }
            
            logger.info(f"[QYWeChat] 开始获取文件列表: parent_id={parent_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                file_list = result.get("file_list", [])
                logger.info(f"[QYWeChat] 获取文件列表成功，共{len(file_list)}个文件")
                return True, file_list
            else:
                error_msg = f"获取文件列表失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取文件列表异常: {str(e)}", exc_info=True)
            return False, f"获取文件列表异常: {str(e)}"

# 创建服务实例
qywechat_service = QYWeChatService()
