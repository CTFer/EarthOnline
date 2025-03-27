from dataclasses import dataclass
from typing import List, Dict, Optional

@dataclass
class APIEndpoint:
    path: str
    method: str
    description: str
    auth_required: bool
    parameters: Optional[List[Dict]] = None
    response: Optional[Dict] = None

class APIRegistry:
    def __init__(self):
        self.endpoints = []
        
    def register(self, path: str, method: str, description: str, auth_required: bool = False, 
                parameters: Optional[List[Dict]] = None, response: Optional[Dict] = None):
        """注册API端点"""
        endpoint = APIEndpoint(
            path=path,
            method=method,
            description=description,
            auth_required=auth_required,
            parameters=parameters,
            response=response
        )
        self.endpoints.append(endpoint)
        
    def get_all_endpoints(self) -> List[APIEndpoint]:
        """获取所有API端点"""
        return self.endpoints

# 创建全局API注册表
api_registry = APIRegistry()

# 注册管理后台API
api_registry.register(
    path="/admin/api/users",
    method="GET",
    description="获取所有用户列表",
    auth_required=True,
    response={
        "data": [
            {
                "id": "用户ID",
                "username": "用户名",
                "created_at": "创建时间"
            }
        ]
    }
)

api_registry.register(
    path="/admin/api/users",
    method="POST",
    description="添加新用户",
    auth_required=True,
    parameters=[
        {
            "name": "username",
            "type": "string",
            "required": True,
            "description": "用户名"
        },
        {
            "name": "password",
            "type": "string",
            "required": True,
            "description": "密码"
        }
    ],
    response={
        "id": "新创建的用户ID"
    }
)

# 注册游戏API
api_registry.register(
    path="/api/character",
    method="GET",
    description="获取角色信息",
    response={
        "name": "角色名称",
        "title": "称号",
        "stamina": "体力值",
        "intelligence": "智力值",
        "sex": "性别"
    }
)

api_registry.register(
    path="/api/tasks/available",
    method="GET",
    description="获取可用任务列表",
    response={
        "data": [
            {
                "id": "任务ID",
                "title": "任务标题",
                "description": "任务描述",
                "status": "任务状态",
                "reward": {
                    "exp": "经验值奖励",
                    "gold": "金币奖励"
                }
            }
        ]
    }
)

# 注册玩家相关API
api_registry.register(
    path="/api/player/<player_id>",
    method="GET",
    description="获取角色信息",
    response={
        "name": "角色名称",
        "title": "称号",
        "stamina": "体力值",
        "intelligence": "智力值",
        "sex": "性别"
    }
)

api_registry.register(
    path="/api/get_players",
    method="GET",
    description="获取所有玩家列表",
    response={
        "data": [
            {
                "player_id": "玩家ID",
                "name": "玩家名称",
                "title": "称号",
                "stamina": "体力值",
                "intelligence": "智力值",
                "sex": "性别"
            }
        ]
    }
)

# 注册任务相关API
api_registry.register(
    path="/api/tasks/available/<player_id>",
    method="GET",
    description="获取可用任务列表",
    response={
        "data": [
            {
                "id": "任务ID",
                "name": "任务名称",
                "description": "任务描述",
                "task_type": "任务类型",
                "task_status": "任务状态",
                "stamina_cost": "体力消耗",
                "task_rewards": "任务奖励"
            }
        ]
    }
)

api_registry.register(
    path="/api/tasks/current/<player_id>",
    method="GET",
    description="获取用户当前未过期的任务列表",
    response={
        "data": [
            {
                "id": "任务ID",
                "name": "任务名称",
                "description": "任务描述",
                "status": "任务状态",
                "starttime": "开始时间",
                "endtime": "结束时间"
            }
        ]
    }
)

api_registry.register(
    path="/api/tasks/accept",
    method="POST",
    description="接受任务",
    parameters=[
        {
            "name": "player_id",
            "type": "integer",
            "required": True,
            "description": "玩家ID"
        },
        {
            "name": "task_id",
            "type": "integer",
            "required": True,
            "description": "任务ID"
        }
    ],
    response={
        "code": "状态码",
        "msg": "处理结果信息"
    }
)

api_registry.register(
    path="/api/tasks/abandon",
    method="POST",
    description="放弃任务",
    parameters=[
        {
            "name": "player_id",
            "type": "integer",
            "required": True,
            "description": "玩家ID"
        },
        {
            "name": "task_id",
            "type": "integer",
            "required": True,
            "description": "任务ID"
        }
    ],
    response={
        "code": "状态码",
        "msg": "处理结果信息"
    }
)

api_registry.register(
    path="/api/tasks/complete",
    method="POST",
    description="完成任务",
    parameters=[
        {
            "name": "player_id",
            "type": "integer",
            "required": True,
            "description": "玩家ID"
        },
        {
            "name": "task_id",
            "type": "integer",
            "required": True,
            "description": "任务ID"
        }
    ],
    response={
        "code": "状态码",
        "msg": "处理结果信息"
    }
)

# 注册任务审批相关API
api_registry.register(
    path="/api/task/approval/status",
    method="GET",
    description="获取任务审批状态",
    auth_required=True,
    parameters=[
        {
            "name": "task_id",
            "type": "integer",
            "required": True,
            "description": "任务ID"
        },
        {
            "name": "player_id",
            "type": "integer",
            "required": True,
            "description": "玩家ID"
        }
    ],
    response={
        "data": {
            "sp_no": "审批单号",
            "status_code": "状态码",
            "status_text": "状态文本",
            "apply_time": "提交时间",
            "apply_user_id": "提交用户ID",
            "approval_nodes": [
                {
                    "approver_userid": "审批人ID",
                    "approver_name": "审批人姓名",
                    "status": "审批状态",
                    "speech": "审批意见",
                    "time": "审批时间"
                }
            ]
        }
    }
)

api_registry.register(
    path="/api/task/approval/sync",
    method="POST",
    description="同步企业微信审批状态到任务状态",
    auth_required=True,
    parameters=[
        {
            "name": "task_id",
            "type": "integer",
            "required": True,
            "description": "任务ID"
        },
        {
            "name": "player_id",
            "type": "integer",
            "required": True,
            "description": "玩家ID"
        }
    ],
    response={
        "data": {
            "task_id": "任务ID",
            "player_id": "玩家ID",
            "status": "更新后的任务状态",
            "approval_status": {
                "sp_no": "审批单号",
                "status_code": "状态码",
                "status_text": "状态文本"
            }
        }
    }
)