# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-03-27 14:28:35
# LastEditTime: 2025-03-27 23:31:01
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

# -*- coding: utf-8 -*-
import logging
import requests
import time
import json
import sqlite3
import os
from typing import Dict, Any, List, Optional, Tuple

# 数据库路径常量
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAME_DB_PATH = os.path.join(BASE_DIR, "database", "game.db")
from .QYWeChat_Auth import qywechat_auth
from config.private import QYWECHAT_APPROVAL_TEMPLATE_ID  # 导入审批模板ID

logger = logging.getLogger(__name__)

class QYWeChatReview:
    """企业微信审批服务类"""
    
    def __init__(self):
        """初始化企业微信审批服务"""
        self.auth = qywechat_auth
        self.template_id = QYWECHAT_APPROVAL_TEMPLATE_ID  # 使用配置的模板ID
        
    def get_template_list(self) -> Tuple[bool, Any]:
        """
        获取审批模板列表
        :return: (success, data/error_message)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/gettemplatedetail?access_token={access_token}"
            
            logger.info("[QYWeChat] 获取审批模板列表")
            response = requests.get(f"https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaltemplate?access_token={access_token}")
            result = response.json()
            
            if result.get("errcode") == 0:
                templates = result.get("template_list", [])
                logger.info(f"[QYWeChat] 获取审批模板列表成功，共{len(templates)}个模板")
                return True, templates
            else:
                error_msg = f"获取审批模板列表失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取审批模板列表异常: {str(e)}", exc_info=True)
            return False, f"获取审批模板列表异常: {str(e)}"
            
    def get_template_detail(self, template_id: str) -> Tuple[bool, Any]:
        """
        获取审批模板详情
        :param template_id: 模板ID
        :return: (success, data/error_message)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/gettemplatedetail?access_token={access_token}"
            
            data = {
                "template_id": template_id
            }
            
            logger.info(f"[QYWeChat] 获取审批模板 {template_id} 详情")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                template_detail = result.get("template_content")
                logger.info(f"[QYWeChat] 获取审批模板详情成功")
                return True, template_detail
            else:
                error_msg = f"获取审批模板详情失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取审批模板详情异常: {str(e)}", exc_info=True)
            return False, f"获取审批模板详情异常: {str(e)}"
            
    def create_approval(self, creator_userid: str, template_id: str, approver: List[Dict], 
                       task_title: str, task_content: str, task_id: int, 
                       task_url: str = "", notifyer: List[str] = None, 
                       summary_list: List[Dict] = None, apply_data: Dict = None) -> Tuple[bool, Any]:
        """
        创建审批申请
        :param creator_userid: 申请人userid
        :param template_id: 模板ID
        :param approver: 审批人列表 [{"userid": "xxx", "attr": 1}]
        :param task_title: 任务标题
        :param task_content: 任务内容
        :param task_id: 任务ID
        :param task_url: 任务URL (可选)
        :param notifyer: 抄送人列表 (可选)
        :param summary_list: 摘要信息 (可选)
        :param apply_data: 审批内容 (可选，如果提供则优先使用)
        :return: (success, sp_no/error_message)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/applyevent?access_token={access_token}"
            
            # 审批内容
            if apply_data is None:
                apply_data = self.fill_approval_content(task_id, task_title, task_content)
            
            # 摘要信息，严格遵循企业微信API规范
            if summary_list is None:
                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                summary_list = [
                    {
                        "summary_info": [
                            {
                                "text": f"任务：{task_title[:20]}",
                                "lang": "zh_CN"
                            }
                        ]
                    },
                    {
                        "summary_info": [
                            {
                                "text": f"提交时间：{time_str}",
                                "lang": "zh_CN"
                            }
                        ]
                    }
                ]
            
            # 请求数据
            data = {
                "creator_userid": creator_userid,
                "template_id": template_id,
                "use_template_approver": 0,  # 使用自定义审批人
                "approver": approver,
                "notify_type": 1,  # 提交审批通知审批人
                "apply_data": apply_data,
                "summary_list": summary_list
            }
            
            # 添加抄送人
            if notifyer:
                data["notifyer"] = notifyer
            
            # 记录请求数据方便调试
            logger.debug(f"[QYWeChat] 创建审批请求数据: {json.dumps(data, ensure_ascii=False)}")
            
            logger.info(f"[QYWeChat] 创建审批申请: {task_title} (任务ID: {task_id})")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                sp_no = result.get("sp_no")
                logger.info(f"[QYWeChat] 创建审批申请成功，审批单号: {sp_no}")
                return True, sp_no
            else:
                error_msg = f"创建审批申请失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 创建审批申请异常: {str(e)}", exc_info=True)
            return False, f"创建审批申请异常: {str(e)}"
            
    def get_approval_detail(self, sp_no: str) -> Tuple[bool, Any]:
        """
        获取审批申请详情
        :param sp_no: 审批单号
        :return: (success, data/error_message)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={access_token}"
            
            data = {
                "sp_no": sp_no
            }
            
            logger.info(f"[QYWeChat] 获取审批详情: {sp_no}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                approval_detail = result.get("info")
                logger.info(f"[QYWeChat] 获取审批详情成功: {sp_no}")
                return True, approval_detail
            else:
                error_msg = f"获取审批详情失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取审批详情异常: {str(e)}", exc_info=True)
            return False, f"获取审批详情异常: {str(e)}"
    
    def get_user_approval_info(self, userid: str, start_time: int = None, end_time: int = None, cursor: int = 0,
                             size: int = 100, filters: Dict = None) -> Tuple[bool, Any]:
        """
        获取用户审批数据
        :param userid: 用户ID
        :param start_time: 开始时间戳
        :param end_time: 结束时间戳
        :param cursor: 分页游标
        :param size: 分页大小
        :param filters: 过滤条件
        :return: (success, data/error_message)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovalinfo?access_token={access_token}"
            
            if start_time is None:
                start_time = int(time.time()) - 30 * 24 * 3600  # 默认30天前
                
            if end_time is None:
                end_time = int(time.time())
                
            data = {
                "starttime": start_time,
                "endtime": end_time,
                "cursor": cursor,
                "size": size,
                "filters": filters or {}
            }
            
            if userid:
                data["creator"] = userid
            
            logger.info(f"[QYWeChat] 获取用户 {userid} 的审批数据")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                approval_list = result.get("sp_list", [])
                next_cursor = result.get("next_cursor")
                logger.info(f"[QYWeChat] 获取用户审批数据成功，共{len(approval_list)}条记录")
                return True, {"sp_list": approval_list, "next_cursor": next_cursor}
            else:
                error_msg = f"获取用户审批数据失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取用户审批数据异常: {str(e)}", exc_info=True)
            return False, f"获取用户审批数据异常: {str(e)}"
            
    def create_task_approval(self, player_id: int, task_id: int, approvers: List[str], 
                          form_data: Dict = None, wechat_userid: str = None) -> Tuple[bool, Any]:
        """
        创建任务审批 (针对任务提交的封装方法)
        :param player_id: 玩家ID
        :param task_id: 任务ID
        :param approvers: 审批人企业微信用户ID列表
        :param form_data: 审批表单数据 
        :param wechat_userid: 玩家关联的企业微信用户ID
        :return: (success, sp_no/error_message)
        """
        try:
            # 检查必要参数
            if not wechat_userid:
                return False, "缺少企业微信用户ID"
                
            # 从表单数据中获取任务信息
            task_title = form_data.get("task_name", f"任务-{task_id}")
            task_content = form_data.get("task_description", f"任务ID: {task_id}, 玩家ID: {player_id}")
            
            # 任务标题前添加标识
            task_title = f"【任务提交】{task_title}"
            
            # 使用配置的模板ID
            template_id = self.template_id
            if not template_id:
                # 如果没有配置模板ID，尝试获取模板列表
                success, templates = self.get_template_list()
                if not success:
                    return False, f"获取审批模板失败: {templates}"
                    
                # 选择第一个模板
                if not templates:
                    return False, "未找到可用的审批模板"
                    
                template_id = templates[0]["templateid"]
            
            # 构建审批人列表
            approver_list = []
            for approver_id in approvers:
                approver_list.append({
                    "userid": approver_id,
                    "attr": 1  # 1-审批人
                })
            
            # 填充审批内容
            apply_data = self.fill_approval_content(task_id, task_title, task_content, form_data)
            
            # 构建正确格式的摘要信息
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            summary_list = [
                {
                    "summary_info": [
                        {
                            "text": f"任务：{task_title[:20]}",
                            "lang": "zh_CN"
                        }
                    ]
                },
                {
                    "summary_info": [
                        {
                            "text": f"提交时间：{time_str}",
                            "lang": "zh_CN"
                        }
                    ]
                }
            ]
            
            # 创建审批申请
            return self.create_approval(
                creator_userid=wechat_userid,
                template_id=template_id,
                approver=approver_list,
                task_title=task_title,
                task_content=task_content,
                task_id=task_id,
                summary_list=summary_list,
                apply_data=apply_data  # 使用填充好的审批内容
            )
            
        except Exception as e:
            logger.error(f"[QYWeChat] 创建任务审批异常: {str(e)}", exc_info=True)
            return False, f"创建任务审批异常: {str(e)}"
            
    def fill_approval_content(self, task_id: int, task_title: str, task_content: str, form_data: Dict = None) -> Dict:
        """
        填充审批内容
        
        :param task_id: 任务ID
        :param task_title: 任务标题
        :param task_content: 任务内容
        :param form_data: 额外的表单数据 (可选)
        :return: 填充好的审批内容
        """
        try:
            logger.info(f"[QYWeChat] 填充任务审批内容：任务ID:{task_id}, 标题:{task_title}")
            
            # 准备审批内容
            apply_data = {
                "contents": [
                    {
                        "control": "Number",
                        "id": "Number-1743055311516",
                        "value": {
                            "new_number": str(task_id)
                        }
                    },
                    {
                        "control": "Text",
                        "id": "Text-1640339319582",
                        "value": {
                            "text": task_title
                        }
                    },
                    {
                        "control": "Textarea",
                        "id": "Textarea-1640339335659",
                        "value": {
                            "text": task_content
                        }
                    }
                ]
            }
            
            # 如果有额外的文件附件
            if form_data and form_data.get('files'):
                apply_data["contents"].append({
                    "control": "File",
                    "id": "File-1640339381728",
                    "value": {
                        "files": form_data['files']
                    }
                })
            
            logger.info(f"[QYWeChat] 审批内容填充完成，共 {len(apply_data['contents'])} 个控件")
            return apply_data
            
        except Exception as e:
            logger.error(f"[QYWeChat] 填充审批内容异常: {str(e)}", exc_info=True)
            return {
                "contents": [
                    {
                        "control": "Number",
                        "id": "Number-1743055311516",
                        "value": {
                            "new_number": str(task_id)
                        }
                    },
                    {
                        "control": "Text",
                        "id": "Text-1640339319582",
                        "value": {
                            "text": task_title
                        }
                    },
                    {
                        "control": "Textarea",
                        "id": "Textarea-1640339335659",
                        "value": {
                            "text": task_content
                        }
                    }
                ]
            }
            
    def get_task_approval_status(self, sp_no: str) -> Tuple[bool, Dict]:
        """
        获取任务审批状态
        :param sp_no: 审批单号
        :return: (success, status_data/error_message)
        """
        try:
            success, detail = self.get_approval_detail(sp_no)
            if not success:
                return False, detail
                
            # 审批状态: 1-审批中；2-已通过；3-已驳回；4-已撤销；6-通过后撤销；7-已删除；10-已支付
            sp_status = detail.get("sp_status")
            status_dict = {
                1: "审批中",
                2: "已通过",
                3: "已驳回",
                4: "已撤销",
                6: "通过后撤销",
                7: "已删除",
                10: "已支付"
            }
            
            status_info = {
                "sp_no": sp_no,
                "status_code": sp_status,
                "status_text": status_dict.get(sp_status, "未知状态"),
                "apply_time": detail.get("apply_time"),
                "apply_user_id": detail.get("applyer", {}).get("userid"),
                "approval_nodes": []
            }
            
            # 获取审批流程信息
            approval_nodes = detail.get("sp_record", [])
            for node in approval_nodes:
                approvers = node.get("approver", [])
                for approver in approvers:
                    status_info["approval_nodes"].append({
                        "approver_userid": approver.get("userid"),
                        "approver_name": approver.get("name"),
                        "status": approver.get("sp_status"),
                        "speech": approver.get("speech", ""),
                        "time": approver.get("sptime", 0)
                    })
            
            return True, status_info
            
        except Exception as e:
            logger.error(f"[QYWeChat] 获取任务审批状态异常: {str(e)}", exc_info=True)
            return False, f"获取任务审批状态异常: {str(e)}"
    
    def get_default_approvers(self) -> List[str]:
        """
        获取默认审批人列表
        :return: 审批人用户ID列表
        """
        # 在实际应用中，可以从配置或数据库中获取，这里返回示例值
        # 如果项目有管理员用户或特定审批人，应该从数据库中获取
        try:
            # 此处应该实现从数据库中获取管理员或审批人列表的逻辑
            # 例如: SELECT wechat_userid FROM users WHERE role = 'admin'
            
            # 示例：返回一个固定的审批人列表
            # 在实际项目中应该替换为动态获取的逻辑AMoXianSheng
            return ["DuChengLong", "AMoXianSheng"]
        except Exception as e:
            logger.error(f"[QYWeChat] 获取默认审批人列表异常: {str(e)}")
            return []

    def handle_approval_event(self, event_data: Dict) -> Tuple[bool, str]:
        """
        处理企业微信审批状态变更回调事件
        :param event_data: 回调事件数据
        :return: (success, message)
        """
        try:
            # 提取审批单号和新状态
            sp_no = event_data.get("ApprovalInfo", {}).get("SpNo")
            sp_status = event_data.get("ApprovalInfo", {}).get("SpStatus")
            
            if not sp_no or sp_status is None:
                logger.error(f"[QYWeChat] 审批回调事件缺少必要参数: {event_data}")
                return False, "回调事件缺少必要参数"
            
            logger.info(f"[QYWeChat] 收到审批状态变更事件: 单号={sp_no}, 状态={sp_status}")
            
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
                return False, f"未找到审批单号对应的任务: {sp_no}"
            
            task_id = task["id"]
            player_id = task["player_id"]
            
            # 调用TaskService同步审批状态
            from function.TaskService import task_service
            result = task_service.sync_approval_status(task_id, player_id)
            
            logger.info(f"[QYWeChat] 同步审批状态结果: {result}")
            return True, "审批状态同步成功"
            
        except Exception as e:
            logger.error(f"[QYWeChat] 处理审批回调事件异常: {str(e)}", exc_info=True)
            return False, f"处理审批回调事件异常: {str(e)}"

# 创建企业微信审批实例
qywechat_review = QYWeChatReview()
