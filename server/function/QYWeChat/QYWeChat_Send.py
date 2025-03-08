# -*- coding: utf-8 -*-
import json
import logging
import requests
import os
from config.private import QYWECHAT_CORP_ID, QYWECHAT_AGENT_ID
from .QYWeChat_Auth import qywechat_auth

logger = logging.getLogger(__name__)

class QYWeChatSend:
    """企业微信消息发送类"""
    
    def __init__(self):
        """初始化企业微信消息发送服务"""
        self.corp_id = QYWECHAT_CORP_ID
        self.agent_id = QYWECHAT_AGENT_ID
        self.auth = qywechat_auth

    def _send_message(self, message_data):
        """统一的消息发送方法"""
        try:
            access_token = self.auth.get_access_token()
            if not access_token:
                return False, "获取access_token失败"
                
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
            response = requests.post(url, json=message_data)
            result = response.json()
            
            if result.get("errcode") == 0:
                return True, "消息发送成功"
            else:
                error_msg = f"消息发送失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 发送消息异常: {str(e)}")
            return False, f"发送消息异常: {str(e)}"

    def send_text(self, content, to_user=None, to_party=None, to_tag=None, safe=0):
        """发送文本消息"""
        message_data = {
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {
                "content": content
            },
            "safe": safe
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_image(self, media_id, to_user=None, to_party=None, to_tag=None, safe=0):
        """发送图片消息"""
        message_data = {
            "msgtype": "image",
            "agentid": self.agent_id,
            "image": {
                "media_id": media_id
            },
            "safe": safe
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_voice(self, media_id, to_user=None, to_party=None, to_tag=None):
        """发送语音消息"""
        message_data = {
            "msgtype": "voice",
            "agentid": self.agent_id,
            "voice": {
                "media_id": media_id
            }
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_video(self, media_id, title=None, description=None, to_user=None, to_party=None, to_tag=None, safe=0):
        """发送视频消息"""
        message_data = {
            "msgtype": "video",
            "agentid": self.agent_id,
            "video": {
                "media_id": media_id,
                "title": title,
                "description": description
            },
            "safe": safe
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_file(self, media_id, to_user=None, to_party=None, to_tag=None, safe=0):
        """发送文件消息"""
        message_data = {
            "msgtype": "file",
            "agentid": self.agent_id,
            "file": {
                "media_id": media_id
            },
            "safe": safe
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_textcard(self, title, description, url, btntxt=None, to_user=None, to_party=None, to_tag=None):
        """发送文本卡片消息"""
        message_data = {
            "msgtype": "textcard",
            "agentid": self.agent_id,
            "textcard": {
                "title": title,
                "description": description,
                "url": url,
                "btntxt": btntxt or "详情"
            }
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_news(self, articles, to_user=None, to_party=None, to_tag=None):
        """发送图文消息"""
        message_data = {
            "msgtype": "news",
            "agentid": self.agent_id,
            "news": {
                "articles": articles
            }
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_mpnews(self, articles, to_user=None, to_party=None, to_tag=None, safe=0):
        """发送图文消息（mpnews）"""
        message_data = {
            "msgtype": "mpnews",
            "agentid": self.agent_id,
            "mpnews": {
                "articles": articles
            },
            "safe": safe
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_markdown(self, content, to_user=None, to_party=None, to_tag=None):
        """发送markdown消息"""
        message_data = {
            "msgtype": "markdown",
            "agentid": self.agent_id,
            "markdown": {
                "content": content
            }
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_template_card(self, template_card, to_user=None, to_party=None, to_tag=None):
        """发送模板卡片消息"""
        message_data = {
            "msgtype": "template_card",
            "agentid": self.agent_id,
            "template_card": template_card
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_miniprogram_notice(self, appid, page, title, description, emphasis_first_item=False, content_item=None, to_user=None, to_party=None, to_tag=None):
        """发送小程序通知消息"""
        message_data = {
            "msgtype": "miniprogram_notice",
            "agentid": self.agent_id,
            "miniprogram_notice": {
                "appid": appid,
                "page": page,
                "title": title,
                "description": description,
                "emphasis_first_item": emphasis_first_item,
                "content_item": content_item or []
            }
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def send_interactive_taskcard(self, task_id, title, description, url, task_buttons, to_user=None, to_party=None, to_tag=None):
        """发送任务卡片消息"""
        message_data = {
            "msgtype": "interactive_taskcard",
            "agentid": self.agent_id,
            "interactive_taskcard": {
                "title": title,
                "description": description,
                "url": url,
                "task_id": task_id,
                "btn": task_buttons
            }
        }
        
        if to_user:
            message_data["touser"] = to_user
        if to_party:
            message_data["toparty"] = to_party
        if to_tag:
            message_data["totag"] = to_tag
            
        return self._send_message(message_data)

    def update_taskcard(self, userids, agentid, task_id, clicked_key, replace_name=None):
        """更新任务卡片消息按钮"""
        try:
            access_token = self.auth.get_access_token()
            if not access_token:
                return False, "获取access_token失败"
                
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/update_taskcard?access_token={access_token}"
            
            data = {
                "userids": userids,
                "agentid": agentid,
                "task_id": task_id,
                "clicked_key": clicked_key
            }
            
            if replace_name:
                data["replace_name"] = replace_name
                
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                return True, "任务卡片更新成功"
            else:
                error_msg = f"任务卡片更新失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 更新任务卡片异常: {str(e)}")
            return False, f"更新任务卡片异常: {str(e)}"

    def upload_media(self, media_type, media_file):
        """上传临时素材"""
        try:
            access_token = self.auth.get_access_token()
            if not access_token:
                return False, "获取access_token失败"
                
            url = f"https://qyapi.weixin.qq.com/cgi-bin/media/upload?access_token={access_token}&type={media_type}"
            
            with open(media_file, 'rb') as f:
                files = {
                    'media': f
                }
                response = requests.post(url, files=files)
                result = response.json()
                
                if result.get("errcode") == 0:
                    return True, result.get("media_id")
                else:
                    error_msg = f"上传素材失败: [{result.get('errcode')}] {result.get('errmsg')}"
                    logger.error(f"[QYWeChat] {error_msg}")
                    return False, error_msg
                    
        except Exception as e:
            logger.error(f"[QYWeChat] 上传素材异常: {str(e)}")
            return False, f"上传素材异常: {str(e)}"

    def recall_message(self, msgid):
        """撤回应用消息"""
        try:
            access_token = self.auth.get_access_token()
            if not access_token:
                return False, "获取access_token失败"
                
            url = f"https://qyapi.weixin.qq.com/cgi-bin/message/recall?access_token={access_token}"
            
            data = {
                "msgid": msgid
            }
            
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                return True, "消息撤回成功"
            else:
                error_msg = f"消息撤回失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 撤回消息异常: {str(e)}")
            return False, f"撤回消息异常: {str(e)}"

# 创建消息发送实例
qywechat_send = QYWeChatSend()
