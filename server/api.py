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

# ... 继续注册其他API ... 