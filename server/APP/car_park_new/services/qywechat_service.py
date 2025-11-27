# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-11-01 11:00:00
# LastEditTime: 2025-11-01 17:04:34
# LastEditors: 一根鱼骨棒
# Description: 企业微信服务类
# Software: VScode
# Copyright 2025 迷舍

import os
import sys
import logging
import base64
import time
import json
import requests
from datetime import datetime, timedelta
from Crypto.Cipher import AES
import hashlib
import random
from typing import Optional, Dict, Any, Union

# 配置常量
CONFIG = {
    "corp_id": "ww0e92b0a70b5f5bb6",
    "agent_id": "1000002",
    "corp_secret": "Y9kpZjWjiC1wYAbNby05bHknAqMoZbbIgs51o02sFEk",
    "token": "oGLIAWAUTkFLKFysSBq",
    "encoding_aes_key": "joQ3dt58VNQzMbpWwa4MoVPUBaHQVPRx1aIYa8Cr2pj",
    "template_id": "C4ZW8NykzpNK7YfW5vS9Swnv1xPJ7wTPxHMKAZmAo",
    "HEARTBEAT_TIMEOUT": timedelta(hours=1),  # 心跳超时时间为1小时
    "HEARTBEAT_CHECK_INTERVAL": 300,  # 心跳检查间隔（秒）
    "HEARTBEAT_FILE": "car_park_last_heartbeat.txt",  # 心跳文件路径
    "DEFAULT_MESSAGE_RECEIVER": {
        "touser": "ShengTieXiaJiuJingGuoMinBan|QianHaoJun"  # 发送给指定成员，多个用|分隔
    },
    "MESSAGE_RETRY_TIMES": 3,  # 消息发送重试次数
    "MESSAGE_RETRY_INTERVAL": 2,  # 重试间隔（秒）
    "ACCESS_TOKEN_CACHE_FILE": "access_token_cache.json",  # Token缓存文件
    "ACCESS_TOKEN_EXPIRE_TIME": 7200  # Token过期时间（秒）
}

# 审批模板控件ID映射
APPROVAL_CONTROL_IDS = {
    "APPLY_USER": "Text-1568693962000",  # 申请人
    "APPLY_DEPARTMENT": "Department-1568693963000",  # 所属部门
    "CAR_NUMBER": "Text-1568693964000",  # 车牌号
    "CAR_TYPE": "Select-1568693965000",  # 车辆类型
    "APPLY_REASON": "Textarea-1568693966000",  # 申请事由
    "MONTH_COUNT": "Number-1568693967000",  # 申请月数
    "START_TIME": "Date-1568693968000",  # 开始时间
    "END_TIME": "Date-1568693969000"  # 结束时间
}

# 车辆类型映射
CAR_TYPE_MAP = {
    1: "业主首车",
    2: "外部和租户月租车",
    5: "业主二车"
}

logger = logging.getLogger(__name__)

# 最近续期记录缓存
recent_records_cache = {}
recent_records_expire = {}

class QYWeChatService:
    """企业微信服务类"""
    
    def __init__(self):
        self.access_token = None
        self.access_token_expire_time = 0
        self.cache_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            CONFIG["ACCESS_TOKEN_CACHE_FILE"]
        )
        self._load_cached_token()
    
    def _load_cached_token(self):
        """从缓存文件加载access_token"""
        try:
            if os.path.exists(self.cache_file_path):
                with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.access_token = data.get('access_token')
                    self.access_token_expire_time = data.get('expire_time', 0)
        except Exception as e:
            logger.error(f"[QYWeChat] 加载缓存的access_token失败: {str(e)}")
    
    def _save_cached_token(self):
        """保存access_token到缓存文件"""
        try:
            data = {
                'access_token': self.access_token,
                'expire_time': self.access_token_expire_time
            }
            with open(self.cache_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"[QYWeChat] 保存access_token到缓存失败: {str(e)}")
    
    def get_access_token(self):
        """获取企业微信access_token"""
        current_time = time.time()
        
        # 检查token是否有效
        if self.access_token and self.access_token_expire_time > current_time:
            logger.info(f"[QYWeChat] 使用缓存的access_token，剩余有效期: {int(self.access_token_expire_time - current_time)}秒")
            return self.access_token
        
        # 重新获取token
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CONFIG['corp_id']}&corpsecret={CONFIG['corp_secret']}"
            response = requests.get(url, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                self.access_token = result.get('access_token')
                self.access_token_expire_time = current_time + CONFIG['ACCESS_TOKEN_EXPIRE_TIME'] - 600  # 提前10分钟过期
                self._save_cached_token()
                logger.info(f"[QYWeChat] 成功获取新的access_token，有效期: {CONFIG['ACCESS_TOKEN_EXPIRE_TIME'] - 600}秒")
                return self.access_token
            else:
                logger.error(f"[QYWeChat] 获取access_token失败: {result}")
                return None
        except Exception as e:
            logger.error(f"[QYWeChat] 获取access_token异常: {str(e)}")
            return None
    
    def force_refresh_token(self):
        """强制刷新access_token"""
        self.access_token = None
        self.access_token_expire_time = 0
        return self.get_access_token()
    
    def get_template_detail(self, template_id):
        """获取审批模板详情"""
        access_token = self.get_access_token()
        if not access_token:
            return None
        
        try:
            url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/gettemplatedetail?access_token={access_token}"
            data = {
                "template_id": template_id
            }
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get('errcode') == 0:
                logger.info(f"[QYWeChat] 成功获取审批模板详情: {template_id}")
                return result.get('template_info')
            else:
                logger.error(f"[QYWeChat] 获取审批模板详情失败: {result}")
                return None
        except Exception as e:
            logger.error(f"[QYWeChat] 获取审批模板详情异常: {str(e)}")
            return None
    
    def decrypt_message(self, encrypted_msg: str, msg_signature: str, timestamp: str, nonce: str) -> Optional[str]:
        """解密企业微信消息"""
        try:
            # 验证签名
            if not self.verify_url(msg_signature, timestamp, nonce, encrypted_msg):
                logger.error("[QYWeChat] 消息签名验证失败")
                return None
            
            # Base64解码
            aes_key = base64.b64decode(CONFIG["encoding_aes_key"] + '=')
            cryptor = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
            
            # 解密
            plain_text = cryptor.decrypt(base64.b64decode(encrypted_msg))
            
            # 去除PKCS7填充
            pad = plain_text[-1]
            plain_text = plain_text[:-pad]
            
            # 解析消息内容
            xml_len = int(plain_text[16:20].decode())
            xml_content = plain_text[20:20 + xml_len].decode()
            
            return xml_content
        except Exception as e:
            logger.error(f"[QYWeChat] 解密消息失败: {str(e)}")
            return None
    
    def encrypt_message(self, reply_msg: str, timestamp: str, nonce: str) -> Optional[Dict[str, str]]:
        """加密企业微信回复消息"""
        try:
            # 生成随机字符串
            rand_str = ''.join([str(random.randint(0, 9)) for _ in range(16)])
            
            # 计算消息长度
            msg_len = len(reply_msg)
            len_bytes = msg_len.to_bytes(4, 'big')
            
            # 构造要加密的消息
            content = rand_str.encode() + len_bytes + reply_msg.encode() + CONFIG["corp_id"].encode()
            
            # PKCS7填充
            pad_len = 32 - (len(content) % 32)
            content += bytes([pad_len]) * pad_len
            
            # AES加密
            aes_key = base64.b64decode(CONFIG["encoding_aes_key"] + '=')
            cryptor = AES.new(aes_key, AES.MODE_CBC, aes_key[:16])
            encrypted = cryptor.encrypt(content)
            
            # Base64编码
            encrypted_base64 = base64.b64encode(encrypted).decode()
            
            # 生成签名
            signature = self._generate_signature(timestamp, nonce, encrypted_base64)
            
            return {
                "msg_signature": signature,
                "timestamp": timestamp,
                "nonce": nonce,
                "encrypt": encrypted_base64
            }
        except Exception as e:
            logger.error(f"[QYWeChat] 加密消息失败: {str(e)}")
            return None
    
    def verify_url(self, msg_signature: str, timestamp: str, nonce: str, echostr: str) -> bool:
        """验证企业微信URL"""
        try:
            signature = self._generate_signature(timestamp, nonce, echostr)
            return signature == msg_signature
        except Exception as e:
            logger.error(f"[QYWeChat] URL验证失败: {str(e)}")
            return False
    
    def _generate_signature(self, timestamp: str, nonce: str, encrypted: str) -> str:
        """生成签名"""
        params = [CONFIG["token"], timestamp, nonce, encrypted]
        params.sort()
        string = ''.join(params)
        hash_obj = hashlib.sha1(string.encode())
        return hash_obj.hexdigest()
    
    def send_text_message(self, content: str, to_user: str = None, to_party: str = None, to_tag: str = None) -> bool:
        """发送文本消息"""
        access_token = self.get_access_token()
        if not access_token:
            return False
        
        if not any([to_user, to_party, to_tag]):
            to_user = CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={access_token}"
        data = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": "text",
            "agentid": CONFIG["agent_id"],
            "text": {
                "content": content
            },
            "safe": 0
        }
        
        # 移除None值
        data = {k: v for k, v in data.items() if v is not None}
        
        # 重试机制
        for retry in range(CONFIG["MESSAGE_RETRY_TIMES"]):
            try:
                response = requests.post(url, json=data, timeout=10)
                result = response.json()
                
                if result.get('errcode') == 0:
                    logger.info(f"[QYWeChat] 消息发送成功，接收者: {to_user}")
                    return True
                else:
                    logger.error(f"[QYWeChat] 消息发送失败 (尝试 {retry + 1}/{CONFIG['MESSAGE_RETRY_TIMES']}): {result}")
                    # 如果是token过期，强制刷新
                    if result.get('errcode') == 40014:
                        self.force_refresh_token()
            except Exception as e:
                logger.error(f"[QYWeChat] 消息发送异常 (尝试 {retry + 1}/{CONFIG['MESSAGE_RETRY_TIMES']}): {str(e)}")
            
            if retry < CONFIG["MESSAGE_RETRY_TIMES"] - 1:
                time.sleep(CONFIG["MESSAGE_RETRY_INTERVAL"])
        
        return False
    
    def _handle_text_message(self, msg_root) -> Optional[str]:
        """处理文本消息
        :param msg_root: 消息XML根节点
        :return: 响应内容
        """
        try:
            content = msg_root.find('Content').text
            msg_id = msg_root.find('MsgId').text
            from_user = msg_root.find('FromUserName').text

            logger.info(f"[Car_Park] 收到文本消息 - 内容: {content}, 消息ID: {msg_id}, 发送者: {from_user}")
            
            # 使用_normalize_input处理输入内容
            normalized_content, parts = self._normalize_input(content)

            # 处理特殊查询
            if content.startswith('价格'):
                # 返回停车场价格信息
                price_info = "停车场收费标准：\n" \
                            "- 首小时：5元\n" \
                            "- 超过1小时后，每小时3元\n" \
                            "- 每天最高收费：50元\n" \
                            "- 月租：300元/月\n" \
                            "- 季租：800元/季\n" \
                            "- 年租：3000元/年"
                return price_info
            elif content.startswith('统计'):
                # 检查权限
                if not self._check_permission(from_user, '统计'):
                    return "您没有权限执行统计操作"
                    
                # 返回停车统计信息
                try:
                    from ..utils import get_db_connection
                    
                    with get_db_connection() as conn:
                        with conn.cursor() as cursor:
                            # 查询总车辆数
                            cursor.execute("SELECT COUNT(*) FROM Sys_Park_Plate")
                            total_cars = cursor.fetchone()[0]
                            
                            # 查询今日新增车辆数
                            cursor.execute("SELECT COUNT(*) FROM Sys_Park_Plate WHERE CreateDate >= DATE('now')")
                            today_new_cars = cursor.fetchone()[0]
                            
                            # 查询即将到期车辆数
                            cursor.execute("SELECT COUNT(*) FROM Sys_Park_Plate WHERE EndDate <= DATE('now', '+7 days') AND EndDate >= DATE('now')")
                            expiring_soon = cursor.fetchone()[0]
                            
                            # 构建统计信息
                            stats_info = f"停车场统计信息：\n" \
                                       f"- 总车辆数：{total_cars}\n" \
                                       f"- 今日新增：{today_new_cars}\n" \
                                       f"- 即将到期（7天内）：{expiring_soon}"
                            
                            # 分段发送消息（如果超过企业微信限制）
                            max_length = 2000
                            if len(stats_info) <= max_length:
                                return stats_info
                            else:
                                # 分段发送
                                parts = []
                                for i in range(0, len(stats_info), max_length):
                                    parts.append(stats_info[i:i+max_length])
                                
                                # 只返回第一段，实际应用可能需要异步发送其他段
                                return parts[0]
                                
                except Exception as e:
                    logger.error(f"[Car_Park] 统计操作失败: {str(e)}", exc_info=True)
                    return "统计操作失败，请稍后再试"

            # 命令处理逻辑
            if content.startswith("修改车牌"):
                return self._handle_modify_plate(normalized_content, from_user)
            elif content.startswith("审批"):
                return self._handle_approval(normalized_content, from_user)
            elif content.startswith("删除"):
                return self._handle_delete(normalized_content, from_user)
            elif content.startswith("备注"):
                if not self._check_permission(from_user, '备注'):
                    return "您无权进行备注操作"
                return self._add_remark(normalized_content, from_user)
            elif content.startswith("绑定"):
                return self._add_wechat_id(normalized_content, from_user, 'bind')
            elif content.startswith("解绑"):
                return self._add_wechat_id(normalized_content, from_user, 'unbind')
            elif content == "记录查询":
                return self._get_recent_records(from_user)
            else:
                return self._query_car_info(content, from_user)
        except Exception as e:
            logger.error(f"[Car_Park] 处理文本消息异常: {str(e)}", exc_info=True)
            return "处理消息失败，请稍后再试"
    
    def _handle_approval(self, content: str, from_user: str) -> str:
        """处理审批相关操作"""
        try:
            # 简单的审批功能响应
            return "审批功能请通过企业微信工作台进行操作，系统将自动处理审批结果。"
        except Exception as e:
            logger.error(f"[QYWeChat] 处理审批失败: {str(e)}")
            return "处理失败，请稍后再试"
    
    def _check_permission(self, from_user: str, operation: str) -> bool:
        """
        检查用户是否有权限执行特定操作

        Args:
            from_user: 用户ID
            operation: 操作类型（'续期', '备注', '审批', '删除', '统计'）

        Returns:
            bool: 是否有权限
        """
        # 管理员用户拥有所有权限
        if from_user in CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"]:
            return True
        return False

    def _normalize_input(self, content: str) -> tuple:
        """
        统一处理输入内容，过滤空格，统一分隔符，转换车牌为大写

        Args:
            content: 输入内容

        Returns:
            tuple: (处理后的内容, 分割后的部分列表)
        """
        try:
            # 清理前后空格
            content = content.strip()
            
            # 定义命令关键词的基础部分（不包含分隔符）
            commands = ['续期', '备注', '审批', '删除', '绑定', '解绑','记录', '修改']
            
            # 移除命令关键词和其后的任意非中文、字母、数字分隔符
            for cmd in commands:
                if content.startswith(cmd):
                    # 使用正则表达式匹配命令后的任意非中文、字母、数字字符
                    pattern = f"^{cmd}[^a-zA-Z0-9\u4e00-\u9fa5]+"
                    content = re.sub(pattern, '', content).strip()
                    break
            
            # 统一替换任意非中文、字母、数字字符为英文逗号
            pattern = re.compile(r'[^a-zA-Z0-9\u4e00-\u9fa5]+')
            content = pattern.sub(',', content)
            
            # 移除开头结尾的逗号
            content = re.sub(r'^,+|,+$', '', content)
            
            # 分割内容
            parts = [part.strip() for part in content.split(',') if part.strip()]
            
            # 将所有可能的车牌号转换为大写
            for i, part in enumerate(parts):
                # 判断是否为车牌号（包含数字且长度大于等于6）
                if len(part) >= 6 and any(char.isdigit() for char in part):
                    parts[i] = part.upper()
                
            return content, parts
        except Exception as e:
            logger.error(f"[Car_Park] 输入内容处理异常: {str(e)}", exc_info=True)
            return content, []

    def _handle_delete(self, content: str, from_user: str) -> str:
        """删除车辆信息"""
        try:
            from ..utils import get_db_connection
            
            # 检查权限
            if not self._check_permission(from_user, '删除'):
                return "您没有权限执行此操作"
            
            # 解析车牌号
            parts = content.split(" ")
            if len(parts) != 2:
                return "输入格式错误，请使用：删除 车牌号"
            
            plate_number = parts[1]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 软删除
            cursor.execute("""
                UPDATE Sys_Park_Plate 
                SET isDel = 1 
                WHERE plateNumber = ?
            """, (plate_number,))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logger.info(f"[QYWeChat] 车辆信息已删除: {plate_number} by {from_user}")
                return f"车辆信息已删除：{plate_number}"
            else:
                conn.close()
                return f"未找到车辆：{plate_number}"
        
        except Exception as e:
            logger.error(f"[QYWeChat] 删除车辆信息失败: {str(e)}")
            return "删除失败，请稍后再试"
    
    def _add_remark(self, content: str, from_user: str) -> str:
        """添加车辆备注"""
        try:
            from ..utils import get_db_connection
            
            # 解析输入格式：备注 车牌号 备注内容
            parts = content.split(" ")
            if len(parts) < 3:
                return "输入格式错误，请使用：备注 车牌号 备注内容"
            
            plate_number = parts[1]
            remark = " ".join(parts[2:])
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 更新备注
            cursor.execute("""
                UPDATE Sys_Park_Plate 
                SET pRemark = ? 
                WHERE plateNumber = ?
            """, (remark, plate_number))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                return f"备注添加成功：车牌号 {plate_number}"
            else:
                conn.close()
                return f"未找到车辆：{plate_number}"
        
        except Exception as e:
            logger.error(f"[QYWeChat] 添加备注失败: {str(e)}")
            return "添加备注失败，请稍后再试"
    
    def _get_recent_records(self, from_user: str) -> str:
        """获取最近续期记录"""
        try:
            from ..utils import get_db_connection
            
            # 检查缓存
            current_time = time.time()
            cache_key = f"recent_records_{from_user}"
            if cache_key in recent_records_cache and recent_records_expire.get(cache_key, 0) > current_time:
                return recent_records_cache[cache_key]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 查询最近30天的续期记录
            cursor.execute("""
                SELECT 
                    p.plateNumber, 
                    pp.pName, 
                    p.endTime, 
                    p.createTime 
                FROM Sys_Park_Plate p
                JOIN Sys_Park_Person pp ON p.personId = pp.id
                WHERE p.isDel = 0 AND p.createTime > datetime('now', '-30 day')
                ORDER BY p.createTime DESC
                LIMIT 20
            """)
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return "最近30天内没有续期记录"
            
            # 格式化结果
            response = ["📋 最近续期记录（30天内）："]
            for row in results:
                create_dt = datetime.strptime(row['createTime'], '%Y-%m-%d %H:%M:%S')
                end_dt = datetime.strptime(row['endTime'], '%Y-%m-%d %H:%M:%S') if row['endTime'] else None
                
                response.append(f"\n• 车牌号：{row['plateNumber']}")
                response.append(f"  车主：{row['pName']}")
                response.append(f"  续期时间：{create_dt.strftime('%Y-%m-%d')}")
                if end_dt:
                    response.append(f"  到期时间：{end_dt.strftime('%Y-%m-%d')}")
            
            response_text = "".join(response)
            
            # 缓存结果
            recent_records_cache[cache_key] = response_text
            recent_records_expire[cache_key] = current_time + 300  # 缓存5分钟
            
            return response_text
            
        except Exception as e:
            logger.error(f"[QYWeChat] 获取最近记录失败: {str(e)}")
            return "获取记录失败，请稍后再试"
    
    def _query_car_info(self, query: str, from_user: str) -> str:
        """查询车辆信息"""
        try:
            from ..utils import get_db_connection, _normalize_input
            conn = get_db_connection()
            cursor = conn.cursor()
            normalized_query = _normalize_input(query)
            
            # 尝试按车牌号查询
            cursor.execute("""
                SELECT 
                    p.plateNumber, 
                    pp.pName, 
                    p.endTime, 
                    p.plateStandard, 
                    pp.pPhone, 
                    pp.pAddress
                FROM Sys_Park_Plate p
                JOIN Sys_Park_Person pp ON p.personId = pp.id
                WHERE p.isDel = 0 AND REPLACE(p.plateNumber, ' ', '') = ?
            """, (normalized_query,))
            
            result = cursor.fetchone()
            
            if not result:
                # 尝试按车主姓名查询
                cursor.execute("""
                    SELECT 
                        p.plateNumber, 
                        pp.pName, 
                        p.endTime, 
                        p.plateStandard, 
                        pp.pPhone, 
                        pp.pAddress
                    FROM Sys_Park_Plate p
                    JOIN Sys_Park_Person pp ON p.personId = pp.id
                    WHERE p.isDel = 0 AND pp.pName LIKE ?
                """, (f"%{query}%",))
                
                results = cursor.fetchall()
                if results:
                    if len(results) == 1:
                        result = results[0]
                    else:
                        # 多个结果
                        response = ["查询到多个车辆信息："]
                        for i, r in enumerate(results, 1):
                            response.append(f"\n{i}. 车牌号：{r['plateNumber']}")
                            response.append(f"   车主：{r['pName']}")
                            if r['endTime']:
                                expire_dt = datetime.strptime(r['endTime'], '%Y-%m-%d %H:%M:%S')
                                days_diff = (expire_dt - datetime.now()).days
                                response.append(f"   到期时间：{expire_dt.strftime('%Y-%m-%d')}")
                                response.append(f"   剩余天数：{days_diff}天")
                        conn.close()
                        return "".join(response)
                
                if not result:
                    conn.close()
                    return f"未找到车辆信息: {query}"
            
            # 格式化单个查询结果
            car_type = CAR_TYPE_MAP.get(result['plateStandard'], "其他车辆")
            response = [
                f"车牌号：{result['plateNumber']}",
                f"车主：{result['pName']}",
                f"车辆类型：{car_type}"
            ]
            
            if result['endTime']:
                expire_dt = datetime.strptime(result['endTime'], '%Y-%m-%d %H:%M:%S')
                days_diff = (expire_dt - datetime.now()).days
                response.append(f"到期时间：{expire_dt.strftime('%Y-%m-%d')}")
                response.append(f"剩余天数：{days_diff}天")
                if days_diff < 0:
                    response.append("⚠️ 已过期，请及时续期")
                elif days_diff <= 7:
                    response.append("⚠️ 即将过期，请及时续期")
            
            if result['pPhone']:
                response.append(f"联系电话：{result['pPhone']}")
            if result['pAddress']:
                response.append(f"地址：{result['pAddress']}")
            
            conn.close()
            return "\n".join(response)
            
        except Exception as e:
            logger.error(f"[QYWeChat] 查询车辆信息失败: {str(e)}")
            return "查询失败，请稍后再试"
    
    def _handle_modify_plate(self, content: str, from_user: str) -> str:
        """处理修改车牌"""
        try:
            from ..utils import get_db_connection, _normalize_input
            
            # 解析输入格式：修改车牌 原车牌号 新车牌号
            parts = content.split(" ")
            if len(parts) != 3:
                return "输入格式错误，请使用：修改车牌 原车牌号 新车牌号"
            
            old_plate = parts[1]
            new_plate = parts[2]
            normalized_old = _normalize_input(old_plate)
            normalized_new = _normalize_input(new_plate)
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 检查原车牌号是否存在
            cursor.execute("""
                SELECT id, plateNumber 
                FROM Sys_Park_Plate 
                WHERE isDel = 0 AND REPLACE(plateNumber, ' ', '') = ?
            """, (normalized_old,))
            old_car = cursor.fetchone()
            
            if not old_car:
                conn.close()
                return f"未找到原车牌号：{old_plate}"
            
            # 检查新车牌号是否已存在
            cursor.execute("""
                SELECT id, plateNumber 
                FROM Sys_Park_Plate 
                WHERE isDel = 0 AND REPLACE(plateNumber, ' ', '') = ?
            """, (normalized_new,))
            new_car = cursor.fetchone()
            
            if new_car:
                conn.close()
                return f"新车牌号 {new_plate} 已存在，请更换其他车牌号"
            
            # 更新车牌号
            cursor.execute("""
                UPDATE Sys_Park_Plate 
                SET plateNumber = ? 
                WHERE id = ?
            """, (new_plate, old_car['id']))
            
            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logger.info(f"[QYWeChat] 车牌号修改成功: {old_plate} -> {new_plate} by {from_user}")
                return f"车牌号修改成功：{old_plate} -> {new_plate}"
            else:
                conn.close()
                return "修改失败，请稍后再试"
        except Exception as e:
            logger.error(f"[QYWeChat] 处理修改车牌失败: {str(e)}")
            return "处理失败，请稍后再试"
    
    def _add_wechat_id(self, content: str, from_user: str, action: str) -> str:
        """处理微信ID绑定/解绑"""
        try:
            from ..utils import get_db_connection
            
            parts = content.split(" ")
            if len(parts) != 3:
                return f"输入格式错误，请使用：{action} 姓名 电话"
            
            name = parts[1]
            phone = parts[2]
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 查找用户
            cursor.execute("""
                SELECT id, pName, pPhone, wechat_id 
                FROM Sys_Park_Person 
                WHERE pName = ? AND pPhone = ?
            """, (name, phone))
            
            person = cursor.fetchone()
            if not person:
                conn.close()
                return f"未找到用户：{name} {phone}"
            
            if action == 'bind':
                # 检查是否已绑定
                if person['wechat_id']:
                    if person['wechat_id'] == from_user:
                        return "您已绑定此账号"
                    else:
                        return "该账号已被其他微信绑定，请联系管理员"
                
                # 绑定微信ID
                cursor.execute("""
                    UPDATE Sys_Park_Person 
                    SET wechat_id = ? 
                    WHERE id = ?
                """, (from_user, person['id']))
                conn.commit()
                conn.close()
                return f"绑定成功！欢迎您，{name}！"
            
            elif action == 'unbind':
                # 检查绑定关系
                if person['wechat_id'] != from_user:
                    conn.close()
                    return "您没有权限解绑此账号"
                
                # 解绑微信ID
                cursor.execute("""
                    UPDATE Sys_Park_Person 
                    SET wechat_id = NULL 
                    WHERE id = ?
                """, (person['id'],))
                conn.commit()
                conn.close()
                return f"解绑成功！"
            
        except Exception as e:
            logger.error(f"[QYWeChat] 处理{action}失败: {str(e)}")
            return "处理失败，请稍后再试"

    def handle_message(self, xml_data: bytes, msg_signature: str, timestamp: str, nonce: str) -> str:
        """
        处理企业微信加密消息
        :param xml_data: 原始XML数据
        :param msg_signature: 消息签名
        :param timestamp: 时间戳
        :param nonce: 随机数
        :return: 响应XML
        """
        try:
            # 解析XML数据
            from xml.etree import ElementTree as ET
            root = ET.fromstring(xml_data)
            encrypted_msg = root.find('Encrypt').text
            
            # 解密消息
            decrypted_xml = self.decrypt_message(encrypted_msg, msg_signature, timestamp, nonce)
            if not decrypted_xml:
                logger.error("[QYWeChat] 消息解密失败")
                return '<xml><ToUserName><![CDATA[]]></ToUserName><FromUserName><![CDATA[]]></FromUserName><CreateTime>0</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[解密失败]]></Content></xml>'
            
            # 解析解密后的XML
            decrypted_root = ET.fromstring(decrypted_xml)
            msg_type = decrypted_root.find('MsgType').text
            from_user = decrypted_root.find('FromUserName').text
            
            # 处理不同类型的消息
            response_content = ""
            if msg_type == 'text':
                # 处理文本消息
                content = decrypted_root.find('Content').text
                response_content = self._handle_text_message(content, from_user)
            elif msg_type == 'event':
                # 处理事件消息
                event = decrypted_root.find('Event').text
                if event == 'subscribe':
                    response_content = "欢迎使用停车场管理系统！"
                elif event == 'CLICK':
                    # 处理菜单点击事件
                    event_key = decrypted_root.find('EventKey').text
                    if event_key == 'STATISTICS':
                        response_content = "统计功能暂未实现"
                elif event == 'open_approval_change' or event == 'sys_approval_change':
                    # 处理审批状态变更事件
                    self._handle_approval_event(decrypted_root)
            
            # 构建回复XML
            if response_content:
                to_user = decrypted_root.find('FromUserName').text
                from_user = decrypted_root.find('ToUserName').text
                reply_xml = f"""
                <xml>
                    <ToUserName><![CDATA[{to_user}]]></ToUserName>
                    <FromUserName><![CDATA[{from_user}]]></FromUserName>
                    <CreateTime>{int(time.time())}</CreateTime>
                    <MsgType><![CDATA[text]]></MsgType>
                    <Content><![CDATA[{response_content}]]></Content>
                </xml>
                """
                
                # 加密回复
                encrypted_data = self.encrypt_message(reply_xml, timestamp, nonce)
                if encrypted_data:
                    # 构建加密响应XML
                    encrypt_reply = f"""
                    <xml>
                        <Encrypt><![CDATA[{encrypted_data['encrypt']}]]></Encrypt>
                        <MsgSignature><![CDATA[{encrypted_data['msg_signature']}]]></MsgSignature>
                        <TimeStamp>{encrypted_data['timestamp']}</TimeStamp>
                        <Nonce><![CDATA[{encrypted_data['nonce']}]]></Nonce>
                    </xml>
                    """
                    return encrypt_reply
            
            # 返回空响应
            return '<xml><ToUserName><![CDATA[]]></ToUserName><FromUserName><![CDATA[]]></FromUserName><CreateTime>0</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[]]></Content></xml>'
        except Exception as e:
            logger.error(f"[QYWeChat] 处理消息失败: {str(e)}", exc_info=True)
            return '<xml><ToUserName><![CDATA[]]></ToUserName><FromUserName><![CDATA[]]></FromUserName><CreateTime>0</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[处理失败]]></Content></xml>'
    
    def _handle_approval_event(self, decrypted_root):
        """处理审批事件"""
        try:
            # 获取事件类型
            event = decrypted_root.find('Event').text
            logger.info(f"[QYWeChat] 收到事件: {event}")

            if event == 'sys_approval_change':
                # 处理审批状态变更事件
                approval_info = decrypted_root.find('ApprovalInfo')
                if approval_info is not None:
                    sp_no = approval_info.find('SpNo').text
                    sp_status = int(approval_info.find('SpStatus').text)

                    logger.info(f"[QYWeChat] 收到审批状态变更 - 单号: {sp_no}, 状态: {sp_status}")

                    # 如果审批通过，获取详细信息并处理
                    if sp_status == 2:  # 2表示审批通过
                        # 获取审批申请详情
                        access_token = self.get_access_token()
                        if not access_token:
                            logger.error("[QYWeChat] 获取access_token失败")
                            return

                        # 调用获取审批详情接口
                        url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/getapprovaldetail?access_token={access_token}"
                        data = {
                            "sp_no": sp_no
                        }

                        try:
                            response = requests.post(url, json=data)
                            if response.status_code == 200:
                                result = response.json()
                                if result.get('errcode') == 0:
                                    # 解析审批数据
                                    approval_data = result.get('info', {})
                                    car_info = self._parse_approval_data_from_detail(approval_data)
                                    if car_info:
                                        # 处理审批通过的逻辑
                                        logger.info(f"[QYWeChat] 审批通过，车辆信息: {car_info}")
                                        if self._save_car_park_info(car_info):
                                            logger.info("[QYWeChat] 车辆信息保存成功")
                                            # 发送通知消息
                                            self.send_text_message(
                                                f"✅ 审批通过通知\n车牌号：{car_info.get('car_number')}\n车主：{car_info.get('apply_user')}\n到期时间：{car_info.get('end_time')}"
                                            )
                                        else:
                                            logger.error("[QYWeChat] 车辆信息保存失败")
                                    else:
                                        logger.error("[QYWeChat] 审批数据解析失败")
                                else:
                                    logger.error(f"[QYWeChat] 获取审批详情失败: {result}")
                            else:
                                logger.error(f"[QYWeChat] 获取审批详情请求失败: {response.text}")
                        except Exception as e:
                            logger.error(f"[QYWeChat] 获取审批详情异常: {str(e)}", exc_info=True)
        except Exception as e:
            logger.error(f"[QYWeChat] 处理审批事件失败: {str(e)}", exc_info=True)
    
    def _parse_approval_data_from_detail(self, approval_data):
        """从审批详情中解析数据"""
        try:
            # 获取表单数据
            apply_data = approval_data.get('apply_data', {})
            contents = apply_data.get('contents', [])
            
            # 构建字段映射
            form_data = {}
            for content in contents:
                control_id = content.get('id')
                title = content.get('title', [{}])[0].get('text', '')
                
                # 根据不同的control类型获取值
                if content.get('control') == 'Text':
                    value = content.get('value', {}).get('text', '')
                elif content.get('control') == 'Selector':
                    value = content.get('value', {}).get('selector', {}).get('options', [{}])[0].get('key', '')
                elif content.get('control') == 'Number':
                    value = content.get('value', {}).get('new_number', '')
                elif content.get('control') == 'Date':
                    value = content.get('value', {}).get('date', '')
                elif content.get('control') == 'Money':
                    value = content.get('value', {}).get('new_money', '')
                else:
                    value = str(content.get('value', ''))
                
                # 根据标题映射到对应的字段
                form_data[title] = value
            
            # 映射到统一格式
            car_info = {
                'car_number': form_data.get('车牌号', ''),
                'apply_user': form_data.get('车主姓名', ''),
                'car_type': form_data.get('车辆类型', ''),
                'month_count': form_data.get('时长（单位：月）', ''),
                'end_time': self._calculate_end_time(form_data.get('时长（单位：月）', '0')),
                'money': form_data.get('交费记录金额', '0')
            }
            
            return car_info
        except Exception as e:
            logger.error(f"[QYWeChat] 解析审批详情数据失败: {str(e)}")
            return None
    
    def _calculate_end_time(self, months_str):
        """计算到期时间"""
        try:
            months = int(months_str)
            # 从当前时间开始计算
            current_date = datetime.now()
            # 计算结束日期
            end_date = current_date
            for _ in range(months):
                # 处理月份增加和年末换行
                if end_date.month == 12:
                    end_date = end_date.replace(year=end_date.year + 1, month=1)
                else:
                    end_date = end_date.replace(month=end_date.month + 1)
            # 格式化为字符串
            return end_date.strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            logger.error(f"[QYWeChat] 无效的月份数: {months_str}")
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _save_car_park_info(self, car_info):
        """保存车辆信息"""
        try:
            from ..utils import get_db_connection, _normalize_input
            import re
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 获取车辆信息
            car_number = car_info.get('car_number')
            owner_name = car_info.get('apply_user')
            car_type = car_info.get('car_type')
            end_time = car_info.get('end_time')
            money = car_info.get('money', '0')
            
            if not car_number or not owner_name or not end_time:
                logger.error("[QYWeChat] 车辆信息不完整")
                conn.close()
                return False
            
            # 标准化车牌号
            normalized_car_number = _normalize_input(car_number)
            
            # 检查审批单号是否已经存在
            # 从审批信息中获取审批单号
            approval_no = car_info.get('sp_no', '')
            if approval_no:
                cursor.execute("SELECT COUNT(*) FROM Sys_Park_Fee WHERE remark LIKE ?", (f"%{approval_no}%",))
                if cursor.fetchone()[0] > 0:
                    logger.warning(f"[QYWeChat] 审批单号 {approval_no} 已经存在")
                    # 发送企业微信通知
                    notification_content = f"⚠️ 停车场车辆信息保存失败\n原因：审批单号 {approval_no} 已经处理过\n车牌号：{car_number}\n申请人：{owner_name}\n车辆类型：{car_type}"
                    self.send_text_message(notification_content, to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"])
                    conn.close()
                    return False
            
            # 查找或创建车主信息
            cursor.execute("""
                SELECT id FROM Sys_Park_Person WHERE pName = ?
            """, (owner_name,))
            person = cursor.fetchone()
            
            if not person:
                # 创建新用户（如果不存在）
                cursor.execute("""
                    INSERT INTO Sys_Park_Person (pName, createTime) VALUES (?, ?)
                """, (owner_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                conn.commit()
                person_id = cursor.lastrowid
            else:
                person_id = person[0]  # SQLite返回元组
            
            # 解析车辆类型
            plate_standard = 1  # 默认业主首车
            if '租户' in car_type or '外部' in car_type:
                plate_standard = 2
            elif '二车' in car_type:
                plate_standard = 5
            
            # 查找是否已存在该车辆
            cursor.execute("""
                SELECT id, personId, plateStandard FROM Sys_Park_Plate 
                WHERE REPLACE(plateNumber, ' ', '') = ? AND isDel = 0
            """, (normalized_car_number,))
            existing_car = cursor.fetchone()
            
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if existing_car:
                # 更新现有车辆信息 - 使用元组索引访问
                existing_id = existing_car[0]
                existing_person_id = existing_car[1]
                existing_plate_standard = existing_car[2]
                
                # 如果车主发生变化，记录变更
                if existing_person_id != person_id:
                    logger.info(f"[QYWeChat] 车辆{car_number}变更车主: {existing_person_id} -> {person_id}")
                
                # 更新车辆信息
                cursor.execute("""
                    UPDATE Sys_Park_Plate 
                    SET personId = ?, plateStandard = ?, endTime = ?, updateTime = ? 
                    WHERE id = ?
                """, (person_id, plate_standard, end_time, current_time, existing_id))
                
                logger.info(f"[QYWeChat] 更新车辆信息: {car_number}, 到期时间: {end_time}")
            else:
                # 创建新车
                cursor.execute("""
                    INSERT INTO Sys_Park_Plate 
                    (plateNumber, personId, plateStandard, endTime, createTime, updateTime, isDel)
                    VALUES (?, ?, ?, ?, ?, ?, 0)
                """, (car_number, person_id, plate_standard, end_time, current_time, current_time))
                
                logger.info(f"[QYWeChat] 新增车辆: {car_number}, 车主: {owner_name}, 类型: {plate_standard}, 到期时间: {end_time}")
            
            # 记录续期缴费
            plate_id = existing_car[0] if existing_car else cursor.lastrowid
            # 备注中包含审批单号
            remark = f"审批通过-{car_type}"
            if approval_no:
                remark = f"{remark}-审批单号:{approval_no}"
            
            cursor.execute("""
                INSERT INTO Sys_Park_Fee 
                (plateId, personId, fee, createTime, remark)
                VALUES (?, ?, ?, ?, ?)
            """, (plate_id, person_id, money, current_time, remark))
            
            conn.commit()
            conn.close()
            
            # 发送成功通知
            notification_content = f"✅ 停车场车辆信息保存成功\n车牌号：{car_number}\n车辆类型：{CAR_TYPE_MAP.get(plate_standard, car_type)}\n申请人：{owner_name}\n到期时间：{end_time}\n金额：{money}元"
            if approval_no:
                notification_content += f"\n审批单号：{approval_no}"
            self.send_text_message(notification_content, to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"])
            
            return True
            
        except Exception as e:
            logger.error(f"[QYWeChat] 保存车辆信息失败: {str(e)}", exc_info=True)
            # 发送失败通知
            notification_content = f"❌ 停车场车辆信息保存失败\n错误：{str(e)}\n车牌号：{car_number}\n申请人：{owner_name}\n车辆类型：{car_type}"
            self.send_text_message(notification_content, to_user=CONFIG["DEFAULT_MESSAGE_RECEIVER"]["touser"])
            return False

# 懒加载企业微信服务实例
_qywechat_service_instance = None

def get_qywechat_service():
    """获取企业微信服务实例（懒加载模式）"""
    global _qywechat_service_instance
    if _qywechat_service_instance is None:
        _qywechat_service_instance = QYWeChatService()
    return _qywechat_service_instance

# 不自动初始化，只在实际使用时通过get_qywechat_service()获取实例