# -*- coding: utf-8 -*-
import logging
import os
import requests
from .QYWeChat_Auth import qywechat_auth

logger = logging.getLogger(__name__)

class QYWeChatCloudDisk:
    """企业微信微盘功能类"""
    
    def __init__(self):
        """初始化企业微信微盘服务"""
        self.auth = qywechat_auth

    def upload_file_to_wecom(self, file_path, file_name=None):
        """
        上传文件到企业微信微盘
        :param file_path: 文件本地路径
        :param file_name: 文件名称（可选）
        :return: (success, file_id或错误信息)
        """
        try:
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 上传文件异常: {str(e)}")
            return False, f"上传文件异常: {str(e)}"

    def download_file_from_wecom(self, file_id, save_path):
        """
        从企业微信微盘下载文件
        :param file_id: 文件ID
        :param save_path: 保存路径
        :return: (success, message)
        """
        try:
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 下载文件异常: {str(e)}")
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
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 创建文件异常: {str(e)}")
            return False, f"创建文件异常: {str(e)}"

    def delete_wecom_file(self, file_id):
        """
        删除企业微信微盘文件
        :param file_id: 文件ID
        :return: (success, message)
        """
        try:
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 删除文件异常: {str(e)}")
            return False, f"删除文件异常: {str(e)}"

    def rename_wecom_file(self, file_id, new_name):
        """
        重命名企业微信微盘文件
        :param file_id: 文件ID
        :param new_name: 新文件名
        :return: (success, message)
        """
        try:
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 重命名文件异常: {str(e)}")
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
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 移动文件异常: {str(e)}")
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
            access_token = self.auth.get_access_token()
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
            logger.error(f"[QYWeChat] 获取文件列表异常: {str(e)}")
            return False, f"获取文件列表异常: {str(e)}"

    def create_wecom_space(self, space_name, auth_info=None):
        """
        创建微盘空间
        :param space_name: 空间名称
        :param auth_info: 权限信息（可选）
        :return: (success, space_id或错误信息)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/space_create?access_token={access_token}"
            
            data = {
                "space_name": space_name
            }
            if auth_info:
                data["auth_info"] = auth_info
            
            logger.info(f"[QYWeChat] 开始创建空间: {space_name}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                space_id = result.get("spaceid")
                logger.info(f"[QYWeChat] 空间创建成功，space_id: {space_id}")
                return True, space_id
            else:
                error_msg = f"空间创建失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 创建空间异常: {str(e)}")
            return False, f"创建空间异常: {str(e)}"

    def delete_wecom_space(self, space_id):
        """
        删除微盘空间
        :param space_id: 空间ID
        :return: (success, message)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/space_delete?access_token={access_token}"
            
            data = {
                "spaceid": space_id
            }
            
            logger.info(f"[QYWeChat] 开始删除空间: {space_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                logger.info(f"[QYWeChat] 空间删除成功")
                return True, "空间删除成功"
            else:
                error_msg = f"空间删除失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 删除空间异常: {str(e)}")
            return False, f"删除空间异常: {str(e)}"

    def get_wecom_space_info(self, space_id):
        """
        获取微盘空间信息
        :param space_id: 空间ID
        :return: (success, space_info或错误信息)
        """
        try:
            access_token = self.auth.get_access_token()
            url = f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/space_info?access_token={access_token}"
            
            data = {
                "spaceid": space_id
            }
            
            logger.info(f"[QYWeChat] 开始获取空间信息: {space_id}")
            response = requests.post(url, json=data)
            result = response.json()
            
            if result.get("errcode") == 0:
                space_info = {
                    "space_name": result.get("space_name"),
                    "auth_info": result.get("auth_info"),
                    "space_sub_type": result.get("space_sub_type"),
                    "space_type": result.get("space_type")
                }
                logger.info(f"[QYWeChat] 获取空间信息成功")
                return True, space_info
            else:
                error_msg = f"获取空间信息失败: [{result.get('errcode')}] {result.get('errmsg')}"
                logger.error(f"[QYWeChat] {error_msg}")
                return False, error_msg
                
        except Exception as e:
            logger.error(f"[QYWeChat] 获取空间信息异常: {str(e)}")
            return False, f"获取空间信息异常: {str(e)}"

# 创建微盘实例
qywechat_cloud_disk = QYWeChatCloudDisk()