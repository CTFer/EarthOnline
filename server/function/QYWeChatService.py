# -*- coding: utf-8 -*-
import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from config.private import QYWECHAT_CORP_ID, QYWECHAT_AGENT_ID
from config.config import TASK_TYPE,DOMAIN
import json
import requests
import threading
from utils.response_handler import ResponseHandler, StatusCode
from function.PlayerService import player_service
from function.TaskService import task_service
from function.GPSService import gps_service
from function.QYWeChat.QYWeChat_Auth import qywechat_auth
from function.QYWeChat.QYWeChat_Send import qywechat_send
import sqlite3
import os

# 数据库路径常量
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME_DB_PATH = os.path.join(BASE_DIR, "database", "game.db")

logger = logging.getLogger(__name__)

class QYWeChatService:
    """企业微信服务类"""
    
    def __init__(self):
        """初始化企业微信服务"""
        self.corp_id = QYWECHAT_CORP_ID
        self.agent_id = QYWECHAT_AGENT_ID
        self.auth = qywechat_auth
        self.send = qywechat_send
        
    def get_access_token(self):
        """获取access_token"""
        return self.auth.get_access_token()
                
    def refresh_access_token(self):
        """强制刷新access_token"""
        return self.auth.refresh_access_token()

    def verify_url(self, msg_signature, timestamp, nonce, echostr):
        """验证URL有效性"""
        return self.auth.verify_url(msg_signature, timestamp, nonce, echostr)

    def send_text_message(self, content, to_user=None, to_party=None, to_tag=None, safe=0):
        """发送文本消息"""
        return self.send.send_text(content, to_user, to_party, to_tag, safe)

    def create_menu(self, menu_data):
        """创建应用菜单"""
        try:
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 创建应用菜单异常: {str(e)}")
            return False, f"创建应用菜单异常: {str(e)}"

    def get_menu(self):
        """获取应用菜单"""
        try:
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 获取应用菜单异常: {str(e)}")
            return False, f"获取应用菜单异常: {str(e)}"

    def delete_menu(self):
        """删除应用菜单"""
        try:
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 删除应用菜单异常: {str(e)}")
            return False, f"删除应用菜单异常: {str(e)}"

    def handle_message(self, xml_data, msg_signature=None, timestamp=None, nonce=None):
        """处理企业微信消息和事件"""
        try:
            xml_str = xml_data.decode('utf-8')
            # logger.info(f"[QYWeChat] 收到原始消息: {xml_str}")
            
            # 解析XML
            root = ET.fromstring(xml_str)
            
            # 获取加密消息
            encrypted_msg = root.find('Encrypt').text
            # logger.debug(f"[QYWeChat] 收到加密消息: {encrypted_msg}")
            
            # 验证消息签名
            signature_list = [self.auth.token, timestamp, nonce, encrypted_msg]
            signature_list.sort()
            calc_signature = hashlib.sha1(''.join(signature_list).encode('utf-8')).hexdigest()
            
            if calc_signature != msg_signature:
                logger.warning("[QYWeChat] 消息签名验证失败")
                return 'success'  # 即使验证失败也返回success，避免企业微信重试
            
            # 解密消息
            decrypted_xml = self.auth.decrypt_message(encrypted_msg)
            # logger.debug(f"[QYWeChat] 解密后的消息: {decrypted_xml}")
            
            # 解析解密后的XML
            msg_root = ET.fromstring(decrypted_xml)
            
            # 获取消息基本信息
            msg_type = msg_root.find('MsgType').text
            from_user = msg_root.find('FromUserName').text
            to_user = msg_root.find('ToUserName').text
            create_time = msg_root.find('CreateTime').text
            agent_id = msg_root.find('AgentID').text if msg_root.find('AgentID') is not None else None
            
            logger.info(f"[QYWeChat] 消息类型: {msg_type}")
            logger.info(f"[QYWeChat] 发送者UserID: {from_user}")
            logger.info(f"[QYWeChat] 接收者: {to_user}")
            logger.info(f"[QYWeChat] 消息创建时间: {create_time}")
            logger.info(f"[QYWeChat] 应用ID: {agent_id}")
            
            # 根据消息类型处理
            if msg_type == 'text':
                # 处理文本消息
                content = msg_root.find('Content').text
                msg_id = msg_root.find('MsgId').text
                logger.info(f"[QYWeChat] 收到文本消息 - 内容: {content}, 消息ID: {msg_id}")
                response_content = self._handle_text_message(content)
            elif msg_type == 'location':
                # 处理位置消息
                response_content = self._handle_location_message(msg_root, from_user)
            elif msg_type == 'event':
                # 处理事件消息
                response_content = self._handle_event(msg_root, from_user, to_user)
            else:
                logger.warning(f"[QYWeChat] 未处理的消息类型: {msg_type}")
                return 'success'
            
            # 构建响应XML
            current_timestamp = str(int(time.time()))
            reply_msg = f"""<xml>
                <ToUserName><![CDATA[{from_user}]]></ToUserName>
                <FromUserName><![CDATA[{to_user}]]></FromUserName>
                <CreateTime>{current_timestamp}</CreateTime>
                <MsgType><![CDATA[text]]></MsgType>
                <Content><![CDATA[{response_content}]]></Content>
                <AgentID>{agent_id}</AgentID>
            </xml>"""
            
            # 加密响应消息
            encrypted_response = self._get_encrypted_response(reply_msg, timestamp, nonce)
            # logger.debug(f"[QYWeChat] 返回加密消息: {encrypted_response}")
            
            return encrypted_response
            
        except Exception as e:
            logger.error(f"[QYWeChat] 处理消息失败: {str(e)}")
            return 'success'  # 即使处理失败也返回success，避免企业微信重试

    def _handle_text_message(self, content):
        """处理文本消息"""
        try:
            # 这里可以根据内容关键词进行自定义回复
            if '你好' in content or 'hello' in content.lower():
                return "你好！很高兴为您服务。"
            elif '帮助' in content or 'help' in content.lower():
                return "您可以：\n1. 发送文本消息\n2. 发送图片或文件\n3. 使用任务卡片功能"
            else:
                return f"您发送的消息是：{content}"
                
        except Exception as e:
            logger.error(f"[QYWeChat] 处理文本消息异常: {str(e)}")
            return "抱歉，处理消息时出现错误，请稍后再试"

    def _handle_location_message(self, msg_root, from_user):
        """处理位置消息"""
        try:
            # 获取位置信息
            location_x = float(msg_root.find('Location_X').text)  # 纬度
            location_y = float(msg_root.find('Location_Y').text)  # 经度
            scale = float(msg_root.find('Scale').text)  # 精度
            label = msg_root.find('Label').text  # 位置名称
            create_time = int(msg_root.find('CreateTime').text)  # 消息创建时间
            
            logger.info(f"[QYWeChat] 收到位置消息 - 位置: {label}, 经度: {location_y}, 纬度: {location_x}, 精度: {scale}")
            
            # 获取玩家信息
            player_info = player_service.get_player_by_wechat_userid(from_user)
            logger.debug(f"[QYWeChat] 获取到玩家信息: {player_info}")
            
            if player_info.get('code') != 0:
                error_msg = f"未找到玩家信息: {player_info.get('msg', '未知错误')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return error_msg
                
            player_id = player_info['data']['player_id']
            
            # 构建GPS数据
            gps_data = {
                'x': location_y,  # 经度
                'y': location_x,  # 纬度
                'player_id': player_id,
                'device': from_user,  # 记录发送者UserID
                'remark': label,  # 位置名称
                'accuracy': scale,  # 精度
                'addtime': create_time  # 消息创建时间
            }
            
            logger.debug(f"[QYWeChat] 准备添加GPS记录: {gps_data}")
            
            # 调用GPS服务添加记录
            from function.GPSService import gps_service
            result = gps_service.add_gps(gps_data)
            
            if result.get('code') == 0:
                success_msg = f"{result.get('msg')}: {label}"
                logger.info(f"[QYWeChat] {success_msg}")
                return success_msg
            else:
                error_msg = f"记录位置信息失败: {result.get('msg', '未知错误')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return error_msg
                
        except Exception as e:
            error_msg = f"处理位置信息时出现错误: {str(e)}"
            logger.error(f"[QYWeChat] {error_msg}", exc_info=True)
            return error_msg

    def _handle_event(self, root, from_user, to_user):
        """处理事件消息"""
        try:
            event = root.find('Event').text.lower()
            logger.info(f"[QYWeChat] 收到事件: {event}")
            
            if event == 'location_select':
                # 处理弹出地理位置选择器的事件
                location = root.find('SendLocationInfo')
                if location is not None:
                    location_x = float(location.find('Location_X').text)  # 纬度
                    location_y = float(location.find('Location_Y').text)  # 经度
                    scale = float(location.find('Scale').text)  # 精度
                    label = location.find('Label').text  # 位置名称
                    poiname = location.find('Poiname').text  # POI名称
                    create_time = int(root.find('CreateTime').text)  # 消息创建时间
                    
                    logger.info(f"[QYWeChat] 用户选择位置 - 位置: {label}, 经度: {location_y}, 纬度: {location_x}, 精度: {scale}, POI: {poiname}")
                    
                    # 获取玩家信息
                    player_info = player_service.get_player_by_wechat_userid(from_user)
                    logger.debug(f"[QYWeChat] 获取到玩家信息: {player_info}")
                    
                    if player_info.get('code') != 0:
                        error_msg = f"未找到玩家信息: {player_info.get('msg', '未知错误')}"
                        logger.error(f"[QYWeChat] {error_msg}")
                        return error_msg
                        
                    player_id = player_info['data']['player_id']
                    
                    # 构建GPS数据
                    gps_data = {
                        'x': location_y,  # 经度
                        'y': location_x,  # 纬度
                        'player_id': player_id,
                        'device': from_user,  # 记录发送者UserID
                        'remark': f"{label} {poiname}".strip(),  # 位置名称和POI
                        'accuracy': scale,  # 精度
                        'addtime': create_time  # 消息创建时间
                    }
                    
                    logger.debug(f"[QYWeChat] 准备添加GPS记录: {gps_data}")
                    
                    result = gps_service.add_gps(gps_data)
                    
                    if result.get('code') == 0:
                        success_msg = f"{result.get('msg')}: {label}"
                        logger.info(f"[QYWeChat] {success_msg}")
                        return success_msg
                    else:
                        error_msg = f"记录位置信息失败: {result.get('msg', '未知错误')}"
                        logger.error(f"[QYWeChat] {error_msg}")
                        return error_msg
            elif event == 'click':
                event_key = root.find('EventKey').text
                wechat_userid = root.find('FromUserName').text
                
                # 获取玩家信息
                player_info = player_service.get_player_by_wechat_userid(wechat_userid)
                if player_info.get('code') != 0:
                    return self.send.send_text(to_user=from_user, content="未找到玩家信息")
                    
                player_id = player_info['data']['player_id']
                
                if event_key == 'PLAYER_TASK':
                    # 处理当前任务列表
                    return self._handle_current_tasks(player_id, wechat_userid, from_user)
                elif event_key == 'AVAIL_TASK':
                    # 处理可用任务列表
                    return self._handle_available_tasks(player_id, wechat_userid, from_user)
            elif event == 'sys_approval_change':
                # 处理审批状态变更事件
                approval_info = root.find('ApprovalInfo')
                if approval_info is not None:
                    sp_no = approval_info.find('SpNo').text  # 审批单号
                    sp_status = int(approval_info.find('SpStatus').text)  # 审批状态
                    
                    logger.info(f"[QYWeChat] 收到审批状态变更 - 单号: {sp_no}, 状态: {sp_status}")
                    
                    # 查询数据库，找到对应的任务
                    conn = sqlite3.connect(GAME_DB_PATH)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT id, player_id
                        FROM player_task
                        WHERE review_id = ?
                    ''', (sp_no,))
                    
                    task = cursor.fetchone()
                    conn.close()
                    
                    if not task:
                        logger.warning(f"[QYWeChat] 未找到审批单号对应的任务: {sp_no}")
                        return 'success'
                    
                    task_id = task["id"]
                    player_id = task["player_id"]
                    
                    # 调用TaskService同步审批状态
                    from function.TaskService import task_service
                    result = task_service.sync_approval_status(task_id, player_id)
                    
                    logger.info(f"[QYWeChat] 同步审批状态结果: {result}")
                    
            return 'success'
            
        except Exception as e:
            logger.error(f"[QYWeChat] 处理事件失败: {str(e)}")
            return 'success'

    def _handle_current_tasks(self, player_id, wechat_userid, from_user):
        """处理当前任务列表"""
        # 获取玩家当前任务列表
        current_tasks = task_service.get_current_tasks(player_id)
        if current_tasks.get('code') != 0:
            return self.send.send_text(to_user=from_user, content="获取任务列表失败")
            
        current_tasks_list = current_tasks.get('data', [])
        if not current_tasks_list:
            return self.send.send_text(to_user=from_user, content="当前没有进行中的任务")

        # 每6个任务一组发送卡片
        for i in range(0, len(current_tasks_list), 6):
            batch_tasks = current_tasks_list[i:i+6]
            template_card = {
                "card_type": "button_interaction",
                    "source": {
                    "icon_url": f"https://{DOMAIN}/static/img/favicon.svg",
                        "desc": "任务系统",
                    "desc_color": 0
                    },
                    "main_title": {
                    "title": "进行中的任务",
                    "desc": f"第{i//6 + 1}页 | 共{(len(current_tasks_list)-1)//6 + 1}页"
                },
                "task_id": f"current_task_list_{int(time.time())}_{i//6}",
                "horizontal_content_list": [],
                    "card_action": {
                        "type": 1,
                    "url": f"https://{DOMAIN}/task/current"
                },
                "button_list": []
            }

            # 添加任务到水平内容列表
            for task in batch_tasks:
                task_type_cn = TASK_TYPE.get(task['task_type'], task['task_type'])
                template_card['horizontal_content_list'].append({
                    "keyname": task_type_cn,
                    "value": task['name'],
                    "type": 1,
                    "url": f"https://{DOMAIN}/task/{task['id']}/detail"
                })

                # 为每个任务添加操作按钮
                template_card['button_list'].extend([
                    {
                        "text": f"完成 #{task['id']}",
                        "style": 1,
                        "type": 0,
                        "key": f"complete_{task['id']}"
                    },
                    {
                        "text": f"放弃 #{task['id']}",
                        "style": 2,
                        "type": 0,
                        "key": f"abandon_{task['id']}"
                    }
                ])

            # 确保按钮不超过6个
            if len(template_card['button_list']) > 6:
                template_card['button_list'] = template_card['button_list'][:6]

            # 发送当前任务卡片
            success, msg = self.send.send_template_card(
                template_card=template_card,
                to_user=wechat_userid
            )
            if not success:
                logger.error(f"[QYWeChat] 发送当前任务卡片失败: {msg}")
                return self.send.send_text(to_user=from_user, content="发送任务信息失败")

        return 'success'

    def _handle_available_tasks(self, player_id, wechat_userid, from_user):
        """处理可用任务列表"""
        # 获取可用任务列表
        available_tasks = task_service.get_available_tasks(player_id)
        if available_tasks.get('code') != 0:
            return self.send.send_text(to_user=from_user, content="获取可用任务失败")
            
        available_tasks_list = available_tasks.get('data', [])
        if not available_tasks_list:
            return self.send.send_text(to_user=from_user, content="当前没有可接受的任务")

        # 每6个任务一组发送卡片
        for i in range(0, len(available_tasks_list), 6):
            batch_tasks = available_tasks_list[i:i+6]
            template_card = {
                "card_type": "button_interaction",
                "source": {
                    "icon_url": f"https://{DOMAIN}/static/img/favicon.svg",
                    "desc": "任务系统",
                    "desc_color": 0
                },
                "main_title": {
                    "title": "可接受的任务",
                    "desc": f"第{i//6 + 1}页 | 共{(len(available_tasks_list)-1)//6 + 1}页"
                },
                "task_id": f"avail_task_list_{int(time.time())}_{i//6}",
                "horizontal_content_list": [],
                "card_action": {
                    "type": 1,
                    "url": f"https://{DOMAIN}/task/available"
                },
                "button_list": []
            }

            # 添加任务到水平内容列表
            for task in batch_tasks:
                task_type_cn = TASK_TYPE.get(task['task_type'], task['task_type'])
                template_card['horizontal_content_list'].append({
                    "keyname": task_type_cn,
                    "value": task['name'],
                    "type": 1,
                    "url": f"https://{DOMAIN}/task/{task['id']}/detail"
                })

                # 为每个任务添加接受按钮
                template_card['button_list'].append({
                    "text": f"接受 #{task['id']}",
                    "style": 1,
                    "type": 0,
                    "key": f"accept_{task['id']}"
                })

            # 确保按钮不超过6个
            if len(template_card['button_list']) > 6:
                template_card['button_list'] = template_card['button_list'][:6]

            # 发送可用任务卡片
            success, msg = self.send.send_template_card(
                template_card=template_card,
                to_user=wechat_userid
            )
            if not success:
                logger.error(f"[QYWeChat] 发送可用任务卡片失败: {msg}")
                return self.send.send_text(to_user=from_user, content="发送任务信息失败")

        return 'success'

    def _get_encrypted_response(self, reply_msg, timestamp, nonce):
        """获取加密后的响应消息"""
        try:
            # 加密消息
            encrypt = self.auth.encrypt_message(reply_msg)
            
            # 生成签名
            signature_list = [self.auth.token, timestamp, nonce, encrypt]
            signature_list.sort()
            signature = hashlib.sha1(''.join(signature_list).encode('utf-8')).hexdigest()
            
            # 生成加密后的XML
            return f"""<xml>
                <Encrypt><![CDATA[{encrypt}]]></Encrypt>
                <MsgSignature><![CDATA[{signature}]]></MsgSignature>
                <TimeStamp>{timestamp}</TimeStamp>
                <Nonce><![CDATA[{nonce}]]></Nonce>
            </xml>"""
                
        except Exception as e:
            logger.error(f"[QYWeChat] 生成加密响应失败: {str(e)}")
            raise

# 创建服务实例
qywechat_service = QYWeChatService()
