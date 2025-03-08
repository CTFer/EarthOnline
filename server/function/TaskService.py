"""
任务服务模块
处理任务相关的业务逻辑
"""
import sqlite3
import os
import logging
import time
from datetime import datetime
import json
from typing import Dict, List, Optional
from utils.response_handler import ResponseHandler, StatusCode
from function.PlayerService import player_service

logger = logging.getLogger(__name__)

class TaskService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskService, cls).__new__(cls)
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

    def get_task_by_id(self, task_id: int) -> Dict:
        """获取任务详情"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM task WHERE id = ?', (task_id,))
            task = cursor.fetchone()

            if not task:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )

            # 转换查询结果为字典
            columns = [col[0] for col in cursor.description]
            task_dict = dict(zip(columns, task))

            return ResponseHandler.success(
                data=task_dict,
                msg="获取任务详情成功"
            )

        except Exception as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取任务详情失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def get_current_task_by_id(self, task_id):
        """获取当前任务详情"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 联表查询player_task和task表的数据
            cursor.execute('''
                SELECT 
                    pt.id,
                    pt.player_id,
                    pt.status,
                    pt.starttime,
                    pt.endtime,
                    pt.complete_time,
                    t.name,
                    t.description,
                    t.task_type,
                    t.stamina_cost,
                    t.task_rewards,
                    t.icon,
                    t.limit_time
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.id = ?
            ''', (task_id,))
            
            task = cursor.fetchone()
            
            if task:
                # 将查询结果转换为字典
                task_data = dict(task)
                
                return ResponseHandler.success(
                    data=task_data,
                    msg="获取当前任务详情成功"
                )
            else:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )
                
        except sqlite3.Error as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取当前任务详情失败: {str(e)}"
            )
        finally:
            conn.close()
            
    def get_available_tasks(self, player_id: int) -> Dict:
        """获取可用任务列表"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 获取玩家当前进行中的任务
            cursor.execute('''
                SELECT t.task_type, t.id
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.player_id = ? AND pt.status = 'IN_PROGRESS'
            ''', (player_id,))
            current_tasks = cursor.fetchall()
            
            # 获取玩家已完成的任务
            cursor.execute('''
                SELECT t.id, t.task_type
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.player_id = ? AND pt.status = 'COMPLETED'
            ''', (player_id,))
            completed_tasks = {row['id']: row['task_type'] for row in cursor.fetchall()}

            # 获取今日已接受的日常任务
            today_start = int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
            cursor.execute('''
                SELECT t.id, COUNT(*) as accept_count
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.player_id = ? 
                AND t.task_type = 'DAILY'
                AND pt.starttime >= ?
                GROUP BY t.id
            ''', (player_id, today_start))
            daily_task_counts = {row['id']: row['accept_count'] for row in cursor.fetchall()}

            available_tasks = []
            
            # 获取所有可能的任务
            cursor.execute('''
                SELECT 
                    t.id, t.name, t.description, t.stamina_cost,
                    t.task_rewards, t.task_type, t.task_status, t.limit_time, t.icon,
                    t.parent_task_id, t.task_scope, t.repeatable, t.repeat_time
                FROM task t
                WHERE t.is_enabled = 1 
                AND (t.task_scope = 0 OR t.task_scope = ?)
                AND t.id NOT IN (
                    SELECT task_id 
                    FROM player_task 
                    WHERE player_id = ? 
                    AND (status = 'IN_PROGRESS' OR status = 'COMPLETED')
                )
            ''', (player_id, player_id))
            
            all_tasks = cursor.fetchall()
            
            # 处理每个任务
            for task in all_tasks:
                task_dict = dict(task)
                
                # 根据任务类型处理
                if task_dict['task_type'] == 'MAIN':
                    # 主线任务处理
                    current_main = next((t for t in current_tasks if t['task_type'] == 'MAIN'), None)
                    
                    if current_main:
                        # 如果有进行中的主线任务，只显示其直接后续任务
                        if task_dict['parent_task_id'] == current_main['id']:
                            available_tasks.append(task_dict)
                    elif task_dict['parent_task_id'] == 0 or task_dict['parent_task_id'] in completed_tasks:
                        # 如果没有进行中的主线任务，显示第一个主线任务或前置任务已完成的任务
                        available_tasks.append(task_dict)
                        
                elif task_dict['task_type'] == 'BRANCH':
                    # 支线任务处理
                    current_BRANCH_tasks = [t for t in current_tasks if t['task_type'] == 'BRANCH']
                    
                    # 检查是否是当前支线任务的直接后续任务
                    is_next_BRANCH = any(task_dict['parent_task_id'] == t['id'] for t in current_BRANCH_tasks)
                    
                    if is_next_BRANCH:
                        available_tasks.append(task_dict)
                    elif task_dict['parent_task_id'] == 0 or task_dict['parent_task_id'] in completed_tasks:
                        # 新的支线任务线或前置任务已完成
                        available_tasks.append(task_dict)
                        
                elif task_dict['task_type'] == 'DAILY':
                    # 日常任务处理
                    task_id = task_dict['id']
                    current_count = daily_task_counts.get(task_id, 0)
                    
                    if task_dict['repeatable']:
                        # 可重复任务，检查次数限制
                        if current_count < task_dict['repeat_time']:
                            available_tasks.append(task_dict)
                    elif current_count == 0:
                        # 不可重复任务，今天还未接受过
                        available_tasks.append(task_dict)

            return ResponseHandler.success(
                data=available_tasks,
                msg="获取可用任务成功"
            )

        except sqlite3.Error as e:
            logger.error(f"获取任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取任务失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def get_current_tasks(self, player_id: int) -> Dict:
        """获取用户当前未过期的任务列表"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            current_timestamp = int(datetime.now().timestamp())

            cursor.execute('''
                SELECT 
                    pt.id,
                    t.name,
                    t.description,
                    t.stamina_cost,
                    pt.starttime,
                    pt.status,
                    t.task_type,
                    pt.endtime,
                    t.icon,
                    t.task_rewards
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.player_id = ? 
                AND (pt.endtime > ? or pt.endtime is null)
                AND pt.status = 'IN_PROGRESS'
                ORDER BY pt.starttime DESC
            ''', (player_id, current_timestamp))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row[0],
                    'name': row[1],
                    'description': row[2],
                    'stamina_cost': row[3],
                    'starttime': row[4],
                    'status': row[5],
                    'task_type': row[6],
                    'endtime': row[7],
                    'icon': row[8],
                    'task_rewards':row[9]
                })

            return ResponseHandler.success(
                data=tasks,
                msg="获取当前任务列表成功"
            )

        except sqlite3.Error as e:
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取当前任务列表失败: {str(e)}"
            )
        finally:
            conn.close()

    def accept_task(self, player_id: int, task_id: int) -> Dict:
        """接受任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 检查任务是否存在且启用
            cursor.execute('''
                SELECT * FROM task 
                WHERE id = ? AND is_enabled = 1
            ''', (task_id,))
            task = cursor.fetchone()
            
            if not task:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在或未启用"
                )

            # 检查是否已接受该任务,状态为进行中
            cursor.execute('''
                SELECT * FROM player_task 
                WHERE player_id = ? AND task_id = ? AND status = 'IN_PROGRESS'
            ''', (player_id, task_id))
            
            if cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.FAIL,
                    msg="已接受该任务"
                )

            # 检查前置任务是否完成
            if task['parent_task_id']:
                cursor.execute('''
                    SELECT * FROM player_task 
                    WHERE player_id = ? AND task_id = ? AND status = 'COMPLETED'
                ''', (player_id, task['parent_task_id']))
                
                if not cursor.fetchone():
                    return ResponseHandler.error(
                        code=StatusCode.FAIL,
                        msg="需要先完成前置任务"
                    )

            # 检查是否有进行中的主线任务
            if task['task_type'] == 'MAIN':
                cursor.execute('''
                    SELECT * FROM player_task pt
                    JOIN task t ON pt.task_id = t.id
                    WHERE pt.player_id = ? AND t.task_type = 'MAIN' 
                    AND pt.status = 'IN_PROGRESS'
                ''', (player_id,))
                
                if cursor.fetchone():
                    return ResponseHandler.error(
                        code=StatusCode.FAIL,
                        msg="请先完成当前主线任务"
                    )

            # 添加任务记录
            current_time = int(time.time())
            endtime = current_time + task['limit_time'] if task['limit_time'] else None
            
            cursor.execute('''
                INSERT INTO player_task (
                    player_id, task_id, status, starttime, endtime
                ) VALUES (?, ?, 'IN_PROGRESS', ?, ?)
            ''', (player_id, task_id, current_time, endtime))
            
            conn.commit()
            return ResponseHandler.success(
                data={
                    'task_id': task_id,
                    'player_id': player_id,
                    'task_name': task['name']
                },
                msg="接受任务成功"
            )

        except sqlite3.Error as e:
            logger.error(f"接受任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"接受任务失败: {str(e)}"
            )
        finally:
            conn.close()

    def abandon_task(self, player_id: int, task_id: int) -> Dict:
        """放弃任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 首先检查任务是否存在且属于该玩家，同时获取任务类型
            cursor.execute('''
                SELECT pt.status, t.task_type 
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.player_id = ? AND pt.id = ?
            ''', (player_id, task_id))
            
            task = cursor.fetchone()
            if not task:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在或不属于该玩家"
                )
            
            # 检查是否为主线任务
            if task['task_type'] == 'MAIN':
                return ResponseHandler.error(
                    code=StatusCode.FAIL,
                    msg="主线任务不能放弃"
                )
            
            # 检查任务状态是否为进行中
            if task['status'] != 'IN_PROGRESS':
                return ResponseHandler.error(
                    code=StatusCode.FAIL,
                    msg="只能放弃进行中的任务"
                )
            
            # 更新任务状态
            cursor.execute('''
                UPDATE player_task 
                SET status = 'ABANDONED', 
                    complete_time = ? 
                WHERE player_id = ? 
                AND id = ? 
                AND status = 'IN_PROGRESS'
            ''', (int(time.time()), player_id, task_id))
            
            if cursor.rowcount == 0:
                conn.rollback()
                return ResponseHandler.error(
                    code=StatusCode.FAIL,
                    msg="放弃任务失败，请重试"
                )
                
            conn.commit()
            return ResponseHandler.success(
                msg="任务已放弃"
            )

        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            logger.error(f"放弃任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"放弃任务失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def is_main_quest(self, task_id):
        """判断是否为主线任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT task_type FROM task WHERE id = ?
            ''', (task_id,))
            
            result = cursor.fetchone()
            return result and result['task_type'] == 'MAIN'
            
        except Exception as e:
            logger.error(f"判断主线任务失败: {str(e)}")
            return False
        finally:
            conn.close()

    def check_main_quest_completion(self, player_id, main_quest_id):
        """检查主线任务是否满足完成条件"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 获取该主线任务的所有非主线子任务
            cursor.execute('''
                WITH RECURSIVE subtasks AS (
                    -- 直接子任务
                    SELECT id, task_type, parent_task_id
                    FROM task 
                    WHERE parent_task_id = ?
                    
                    UNION ALL
                    
                    -- 递归获取所有子任务
                    SELECT t.id, t.task_type, t.parent_task_id
                    FROM task t
                    INNER JOIN subtasks s ON t.parent_task_id = s.id
                )
                SELECT id FROM subtasks 
                WHERE task_type != 'MAIN'
            ''', (main_quest_id,))
            
            sub_tasks = cursor.fetchall()
            if not sub_tasks:
                return False
                
            # 检查所有子任务的完成状态
            sub_task_ids = [task['id'] for task in sub_tasks]
            placeholders = ','.join('?' * len(sub_task_ids))
            
            cursor.execute(f'''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed
                FROM player_tasks
                WHERE player_id = ? AND task_id IN ({placeholders})
            ''', (player_id, *sub_task_ids))
            
            result = cursor.fetchone()
            return result and result['total'] > 0 and result['total'] == result['completed']
            
        except Exception as e:
            logger.error(f"检查主线任务完成条件失败: {str(e)}")
            return False
        finally:
            conn.close()

    def get_parent_main_quests(self, task_id):
        """获取任务链上的所有主线父任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                WITH RECURSIVE parent_tasks AS (
                    -- 起始任务
                    SELECT id, task_type, parent_task_id
                    FROM task
                    WHERE id = ?
                    
                    UNION ALL
                    
                    -- 递归获取所有父任务
                    SELECT t.id, t.task_type, t.parent_task_id
                    FROM task t
                    INNER JOIN parent_tasks p ON t.id = p.parent_task_id
                )
                SELECT id FROM parent_tasks 
                WHERE task_type = 'MAIN' AND id != ?
            ''', (task_id, task_id))
            
            return [row['id'] for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"获取父主线任务失败: {str(e)}")
            return []
        finally:
            conn.close()

    def complete_task_api(self, player_id: int, task_id: int) -> Dict:
        """完成任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 1. 完成当前任务
            cursor.execute('''
                UPDATE player_tasks 
                SET status = 'COMPLETED', 
                    complete_time = CURRENT_TIMESTAMP
                WHERE player_id = ? AND task_id = ? 
                AND status = 'IN_PROGRESS'
            ''', (player_id, task_id))
            
            if cursor.rowcount == 0:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务状态无效或已完成"
                )
                
            # 2. 发放任务奖励
            success, message, rewards = self._grant_task_rewards(conn, player_id, task_id)
            if not success:
                conn.rollback()
                return ResponseHandler.error(
                    code=StatusCode.FAIL,
                    msg=f"发放奖励失败: {message}"
                )
                
            # 3. 检查父主线任务
            parent_main_quests = self.get_parent_main_quests(task_id)
            completed_main_quests = []
            
            for main_quest_id in parent_main_quests:
                if self.check_main_quest_completion(player_id, main_quest_id):
                    # 自动完成主线任务
                    cursor.execute('''
                        UPDATE player_tasks 
                        SET status = 'COMPLETED', 
                            complete_time = CURRENT_TIMESTAMP
                        WHERE player_id = ? AND task_id = ? 
                        AND status = 'IN_PROGRESS'
                    ''', (player_id, main_quest_id))
                    
                    if cursor.rowcount > 0:
                        # 发放主线任务奖励
                        main_success, main_message, main_rewards = self._grant_task_rewards(
                            conn, player_id, main_quest_id
                        )
                        if main_success:
                            completed_main_quests.append({
                                'task_id': main_quest_id,
                                'rewards': main_rewards
                            })
                        else:
                            logger.error(f"主线任务奖励发放失败: {main_message}")
            
            conn.commit()
            
            # 构建返回信息
            result = {
                'task_completed': True,
                'rewards': rewards,
                'main_quests_completed': completed_main_quests
            }
            
            return ResponseHandler.success(
                data=result,
                msg="任务完成"
            )
            
        except Exception as e:
            conn.rollback()
            logger.error(f"完成任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"完成任务失败: {str(e)}"
            )
        finally:
            conn.close()

    def _grant_task_rewards(self, conn, player_id, task_id):
        """发放任务奖励（保持现有实现）"""
        # ... 现有的奖励发放代码 ...
        pass

task_service = TaskService() 