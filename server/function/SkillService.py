"""
技能服务模块
处理技能相关的业务逻辑
"""
import sqlite3
import os
import logging
from utils.response_handler import ResponseHandler, StatusCode

logger = logging.getLogger(__name__)

class SkillService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SkillService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'database', 
                'game.db'
            )
            self.initialized = True
            
    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_skills(self):
        """获取所有技能"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT id, name, proficiency, description FROM skills')
            skills = [dict(row) for row in cursor.fetchall()]
            return ResponseHandler.success(
                data=skills,
                msg="获取技能列表成功"
            )
        except Exception as e:
            logger.error(f"获取技能列表失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取技能列表失败: {str(e)}"
            )
        finally:
            conn.close()

    def add_skill(self, data):
        """添加新技能"""
        try:
            # 验证必要字段
            if not data.get('name') or not data.get('proficiency'):
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="技能名称和熟练度不能为空"
                )

            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO skills (name, proficiency, description)
                VALUES (?, ?, ?)
            ''', (data['name'], data['proficiency'], data.get('description', '')))

            skill_id = cursor.lastrowid
            conn.commit()

            return ResponseHandler.success(
                data={"id": skill_id},
                msg="添加技能成功"
            )
        except Exception as e:
            logger.error(f"添加技能失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"添加技能失败: {str(e)}"
            )
        finally:
            conn.close()

    def get_skill(self, skill_id):
        """获取指定技能"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, name, proficiency, description FROM skills WHERE id = ?', 
                (skill_id,)
            )
            skill = cursor.fetchone()

            if skill is None:
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg="技能不存在"
                )

            return ResponseHandler.success(
                data=dict(skill),
                msg="获取技能成功"
            )
        except Exception as e:
            logger.error(f"获取技能信息失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取技能信息失败: {str(e)}"
            )
        finally:
            conn.close()

    def update_skill(self, skill_id, data):
        """更新技能"""
        try:
            # 验证必要字段
            if not data.get('name') or not data.get('proficiency'):
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="技能名称和熟练度不能为空"
                )

            conn = self.get_db()
            cursor = conn.cursor()

            # 检查技能是否存在
            cursor.execute('SELECT id FROM skills WHERE id = ?', (skill_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg="技能不存在"
                )

            cursor.execute('''
                UPDATE skills 
                SET name = ?, proficiency = ?, description = ?
                WHERE id = ?
            ''', (
                data['name'], 
                data['proficiency'], 
                data.get('description', ''), 
                skill_id
            ))

            conn.commit()

            return ResponseHandler.success(msg="更新技能成功")
        except Exception as e:
            logger.error(f"更新技能失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"更新技能失败: {str(e)}"
            )
        finally:
            conn.close()

    def delete_skill(self, skill_id):
        """删除技能"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 检查技能是否存在
            cursor.execute('SELECT id FROM skills WHERE id = ?', (skill_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.NOT_FOUND,
                    msg="技能不存在"
                )

            # 首先删除相关的技能关系
            cursor.execute('''
                DELETE FROM skill_relations 
                WHERE parent_skill_id = ? OR child_skill_id = ?
            ''', (skill_id, skill_id))

            # 然后删除技能
            cursor.execute('DELETE FROM skills WHERE id = ?', (skill_id,))

            conn.commit()
            return ResponseHandler.success(msg="删除技能成功")
        except Exception as e:
            logger.error(f"删除技能失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"删除技能失败: {str(e)}"
            )
        finally:
            conn.close()

skill_service = SkillService() 