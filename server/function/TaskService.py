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

    def _get_task_base_query(self):
        """获取基础任务查询SQL"""
        return '''
            SELECT t.*, 
                   p.player_name,
                   COALESCE(pt.status, 'AVAIL') as current_status,
                   pt.starttime,
                   pt.submit_time,
                   pt.complete_time,
                   pt.comment,
                   pt.reject_reason
            FROM task t
            LEFT JOIN player_task pt ON t.id = pt.task_id 
            LEFT JOIN player_data p ON pt.player_id = p.player_id
        '''

    def _get_task_by_id_base(self, task_id: int, player_id: int = None) -> Dict:
        """基础的任务查询函数
        
        Args:
            task_id: 任务ID
            player_id: 玩家ID（可选）
            
        Returns:
            任务信息字典
        """
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            query = self._get_task_base_query()
            params = [task_id]
            
            if player_id:
                query += ' WHERE t.id = ? AND pt.player_id = ?'
                params.append(player_id)
            else:
                query += ' WHERE t.id = ?'
            
            cursor.execute(query, params)
            task = cursor.fetchone()
            
            if task:
                return ResponseHandler.success(
                    data=dict(task),
                    msg="获取任务成功"
                )
            return ResponseHandler.error(
                code=StatusCode.TASK_NOT_FOUND,
                msg="任务不存在"
            )
        except Exception as e:
            logger.error(f"获取任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取任务失败: {str(e)}"
            )
        finally:
            conn.close()

    def _get_tasks_base(self, conditions: str = "", params: list = None, 
                       page: int = None, limit: int = None) -> Dict:
        """基础的任务列表查询函数
        
        Args:
            conditions: WHERE条件语句
            params: 查询参数列表
            page: 页码
            limit: 每页数量
            
        Returns:
            任务列表字典
        """
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 构建基础查询
            query = self._get_task_base_query()
            if conditions:
                query += f" WHERE {conditions}"
            
            # 获取总数
            count_query = f"SELECT COUNT(*) FROM ({query})"
            cursor.execute(count_query, params or [])
            total = cursor.fetchone()[0]
            
            # 添加分页
            if page is not None and limit is not None:
                offset = (page - 1) * limit
                query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query, params or [])
            tasks = [dict(row) for row in cursor.fetchall()]
            
            return ResponseHandler.success(
                data={
                    "total": total,
                    "tasks": tasks
                },
                msg="获取任务列表成功"
            )
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取任务列表失败: {str(e)}"
            )
        finally:
            conn.close()

    def _update_task_status(self, task_id: int, player_id: int, 
                           new_status: str, extra_data: Dict = None) -> Dict:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            player_id: 玩家ID 
            new_status: 新状态
            extra_data: 额外更新的数据
            
        Returns:
            更新结果字典
        """
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 检查任务是否存在
            cursor.execute('''
                SELECT * FROM player_task 
                WHERE id = ? AND player_id = ?
            ''', (task_id, player_id))
            task = cursor.fetchone()
            
            if not task:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )
            
            # 构建更新字段
            update_fields = ['status = ?']
            params = [new_status]
            
            if extra_data:
                for key, value in extra_data.items():
                    update_fields.append(f"{key} = ?")
                    params.append(value)
            
            params.extend([task_id, player_id])
            
            # 执行更新
            cursor.execute(f'''
                UPDATE player_task 
                SET {", ".join(update_fields)}
                WHERE id = ? AND player_id = ?
            ''', params)
            
            conn.commit()
            # 返回更新后的任务状态
            return ResponseHandler.success(msg=f"任务状态更新为{new_status}",data={'status':new_status,'extra_data':extra_data})
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {str(e)}")
            if conn:
                conn.rollback()
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"更新任务状态失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def get_task_by_id(self, task_id: int) -> Dict:
        """获取任务信息"""
        return self._get_task_by_id_base(task_id)

    def get_current_task_by_id(self, task_id: int):
        """获取当前任务信息"""
        return self._get_task_by_id_base(task_id)

    def get_tasks(self, page=None, limit=None):
        """获取任务列表"""
        return self._get_tasks_base(page=page, limit=limit)

    def get_check_tasks(self, page: int = 1, limit: int = 20) -> Dict:
        """获取待审核任务列表"""
        conditions = "pt.status = 'CHECK'"
        return self._get_tasks_base(conditions, [], page, limit)

    def get_task_history(self, task_id: int = None, player_id: int = None, 
                        status: str = None, page: int = 1, limit: int = 20) -> Dict:
        """获取任务历史记录"""
        conditions = []
        params = []
        
        if task_id:
            conditions.append("t.id = ?")
            params.append(task_id)
        if player_id:
            conditions.append("pt.player_id = ?")
            params.append(player_id)
        if status:
            conditions.append("pt.status = ?")
            params.append(status)
        
        where_clause = " AND ".join(conditions) if conditions else ""
        return self._get_tasks_base(where_clause, params, page, limit)

    def submit_task(self, player_id: int, task_id: int, comment: str = None) -> Dict:
        """提交任务"""
        return self._update_task_status(
            task_id, 
            player_id, 
            'CHECK',
            {
                'submit_time': int(time.time()),
                'comment': comment
            }
        )

    def approve_task(self, task_id: int) -> Dict:
        """通过任务"""
        return self._update_task_status(
            task_id,
            player_id,
            'COMPLETED',
            {
                'complete_time': int(time.time())
            }
        )

    def reject_task(self, task_id: int, reject_reason: str = None) -> Dict:
        """驳回任务"""
        return self._update_task_status(
            task_id,
            player_id,
            'REJECT',
            {
                'reject_reason': reject_reason,
                'complete_time': int(time.time())
            }
        )

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
                WHERE pt.player_id = ? AND (pt.status = 'IN_PROGRESS' OR pt.status = 'CHECK')
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
                    t.task_rewards,t.need_check, t.task_type, t.task_status, t.limit_time, t.icon,
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
                else:
                    # 特殊任务处理
                    if task_dict['task_type'] == 'SPECIAL':
                        if task_dict['task_status'] == 'AVAIL':
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
                    t.need_check,
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
                    'need_check': row[4],
                    'starttime': row[5],
                    'status': row[6],
                    'task_type': row[7],
                    'endtime': row[8],
                    'icon': row[9],
                    'task_rewards':row[10]
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

    def complete_task_api(self, player_id: int, task_id: int, comment: str = None) -> Dict:
        """完成任务并发放奖励
        
        Args:
            player_id: 玩家ID
            task_id: 任务ID
            comment: 完成说明（可选）
            
        Returns:
            Dict: 包含完成状态和奖励信息的响应
        """
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 1. 检查任务状态
            cursor.execute('''
                SELECT pt.*, t.need_check, t.task_rewards
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.player_id = ? AND pt.task_id = ? 
                AND pt.status = 'IN_PROGRESS'
            ''', (player_id, task_id))
            
            task_info = cursor.fetchone()
            if not task_info:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务状态无效或不存在"
                )
            
            current_time = int(time.time())
            
            # 2. 根据任务配置决定是否需要审核
            if task_info['need_check']:
                # 需要审核的任务，更新状态为待审核
                return self._update_task_status(
                    task_id,
                    player_id,
                    'CHECK',
                    {
                        'submit_time': current_time,
                        'comment': comment
                    }
                )
            
            # 3. 不需要审核的任务，直接完成并发放奖励
            try:
                # 发放奖励
                rewards_summary = self._process_task_rewards(cursor, player_id, task_info, current_time)
                
                # 更新任务状态
                cursor.execute('''
                    UPDATE player_task
                    SET status = 'COMPLETED',
                        complete_time = ?,
                        comment = ?
                    WHERE player_id = ? AND task_id = ?
                ''', (current_time, comment, player_id, task_id))
                
                # 4. 检查并处理主线任务进度
                completed_main_quests = self._process_main_quest_completion(
                    cursor, player_id, task_id, current_time
                )
                
                conn.commit()
                
                # 构建返回结果
                result = {
                    'task_completed': True,
                    'rewards': rewards_summary,
                    'main_quests_completed': completed_main_quests
                }
                
                return ResponseHandler.success(
                    data=result,
                    msg="任务完成，奖励已发放"
                )
                
            except Exception as e:
                conn.rollback()
                logger.error(f"处理任务完成失败: {str(e)}")
                return ResponseHandler.error(
                    code=StatusCode.SERVER_ERROR,
                    msg=f"处理任务完成失败: {str(e)}"
                )
            
        except Exception as e:
            logger.error(f"完成任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"完成任务失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def _process_task_rewards(self, cursor, player_id: int, task_info: Dict, current_time: int) -> Dict:
        """处理任务奖励发放
        
        Args:
            cursor: 数据库游标
            player_id: 玩家ID
            task_info: 任务信息
            current_time: 当前时间戳
            
        Returns:
            Dict: 奖励发放摘要
        """
        rewards_summary = {
            'points': 0,
            'exp': 0,
            'cards': [],
            'medals': []
        }
        
        rewards = json.loads(task_info['task_rewards'])
        
        # 1. 处理积分奖励
        if rewards.get('points_rewards'):
            for reward in rewards['points_rewards']:
                if reward['type'] == 'points':
                    points = int(reward['number'])
                    cursor.execute('''
                        UPDATE player_data 
                        SET points = points + ? 
                        WHERE player_id = ?
                    ''', (points, player_id))
                    rewards_summary['points'] = points
                elif reward['type'] == 'exp':
                    exp = int(reward['number'])
                    cursor.execute('SELECT experience FROM player_data WHERE player_id = ?', (player_id,))
                    current_exp = cursor.fetchone()['experience']
                    new_exp = current_exp + exp
                    
                    cursor.execute('''
                        UPDATE player_data 
                        SET experience = ? 
                        WHERE player_id = ?
                    ''', (new_exp, player_id))
                    
                    cursor.execute('''
                        INSERT INTO exp_record (player_id, number, addtime, total)
                        VALUES (?, ?, ?, ?)
                    ''', (player_id, exp, current_time, new_exp))
                    
                    rewards_summary['exp'] = exp
        
        # 2. 处理卡片奖励
        if rewards.get('card_rewards'):
            for card in rewards['card_rewards']:
                card_id = card.get('id')
                number = card.get('number', 1)
                if not card_id:
                    continue
                
                cursor.execute('''
                    INSERT INTO player_game_card (player_id, game_card_id, number, timestamp)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(player_id, game_card_id) DO UPDATE
                    SET number = number + ?,
                        timestamp = ?
                ''', (player_id, card_id, number, current_time, number, current_time))
                
                rewards_summary['cards'].append({
                    'id': card_id,
                    'number': number
                })
        
        # 3. 处理勋章奖励
        if rewards.get('medal_rewards'):
            for medal in rewards['medal_rewards']:
                medal_id = medal.get('id')
                if not medal_id:
                    continue
                
                cursor.execute('''
                    INSERT OR IGNORE INTO player_medal (player_id, medal_id, addtime)
                    VALUES (?, ?, ?)
                ''', (player_id, medal_id, current_time))
                
                if cursor.rowcount > 0:
                    rewards_summary['medals'].append(medal_id)
        
        return rewards_summary

    def _process_main_quest_completion(self, cursor, player_id: int, task_id: int, 
                                     current_time: int) -> List[Dict]:
        """处理主线任务完成进度
        
        Args:
            cursor: 数据库游标
            player_id: 玩家ID
            task_id: 任务ID
            current_time: 当前时间戳
            
        Returns:
            List[Dict]: 完成的主线任务列表及其奖励
        """
        completed_main_quests = []
        
        # 获取父主线任务
        parent_main_quests = self.get_parent_main_quests(task_id)
        
        for main_quest_id in parent_main_quests:
            # 检查主线任务是否可以完成
            if self.check_main_quest_completion(player_id, main_quest_id):
                # 获取主线任务信息
                cursor.execute('''
                    SELECT t.*, pt.player_id
                    FROM task t
                    LEFT JOIN player_task pt ON t.id = pt.task_id AND pt.player_id = ?
                    WHERE t.id = ?
                ''', (player_id, main_quest_id))
                main_quest = cursor.fetchone()
                
                if main_quest and main_quest['player_id']:
                    # 更新主线任务状态
                    cursor.execute('''
                        UPDATE player_task
                        SET status = 'COMPLETED',
                            complete_time = ?
                        WHERE player_id = ? AND task_id = ?
                    ''', (current_time, player_id, main_quest_id))
                    
                    # 发放主线任务奖励
                    rewards = self._process_task_rewards(cursor, player_id, main_quest, current_time)
                    
                    completed_main_quests.append({
                        'task_id': main_quest_id,
                        'rewards': rewards
                    })
        
        return completed_main_quests

    def _get_admin_tasks_query(self):
        """获取管理后台任务查询SQL"""
        return '''
            SELECT t.*
            FROM task t
        '''

    def get_tasks(self, page=None, limit=None):
        """获取任务列表（管理后台接口）
        
        Args:
            page: 页码
            limit: 每页数量
            
        Returns:
            Dict: 任务列表数据
        """
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            # 构建基础查询
            query = self._get_admin_tasks_query()
            
            # 获取总数
            count_query = f"SELECT COUNT(*) FROM task"
            cursor.execute(count_query)
            total = cursor.fetchone()[0]
            
            # 添加排序和分页
            query += " ORDER BY id DESC"
            if page is not None and limit is not None:
                offset = (page - 1) * limit
                query += f" LIMIT {limit} OFFSET {offset}"
            
            cursor.execute(query)
            tasks = []
            for row in cursor.fetchall():
                task_data = dict(row)
                # 确保 task_rewards 是 JSON 格式
                if 'task_rewards' in task_data and isinstance(task_data['task_rewards'], str):
                    try:
                        task_data['task_rewards'] = json.loads(task_data['task_rewards'])
                    except:
                        task_data['task_rewards'] = {}
                tasks.append(task_data)
            
            return ResponseHandler.success(
                data={
                    "total": total,
                    "tasks": tasks
                },
                msg="获取任务列表成功"
            )
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取任务列表失败: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def get_task(self, task_id):
        """获取单个任务信息"""
        return self._get_task_by_id_base(task_id)

    def add_task(self, data):
        """添加新任务"""
        try:
            # 验证必要字段
            required_fields = ['name', 'task_type']
            for field in required_fields:
                if not data.get(field):
                    return ResponseHandler.error(
                        code=StatusCode.PARAM_ERROR,
                        msg=f"缺少必要字段: {field}"
                    )

            conn = self.get_db()
            cursor = conn.cursor()

            # 处理任务奖励数据
            task_rewards = {
                'points_rewards': [],
                'card_rewards': [],
                'medal_rewards': [],
                'real_rewards': []
            }

            # 处理各类奖励
            if 'task_rewards' in data:
                rewards_data = data['task_rewards']
                
                # 处理数值奖励
                if 'points_rewards' in rewards_data:
                    task_rewards['points_rewards'] = [
                        {
                            'type': reward.get('type', 'exp'),
                            'number': int(reward.get('number', 0))
                        }
                        for reward in rewards_data['points_rewards']
                        if reward.get('number') is not None
                    ]

                # 处理卡片奖励
                if 'card_rewards' in rewards_data:
                    task_rewards['card_rewards'] = [
                        {
                            'id': int(reward.get('id', 0)),
                            'number': int(reward.get('number', 0))
                        }
                        for reward in rewards_data['card_rewards']
                        if reward.get('id') is not None and reward.get('number') is not None
                    ]

                # 处理成就奖励
                if 'medal_rewards' in rewards_data:
                    task_rewards['medal_rewards'] = [
                        {
                            'id': int(reward.get('id', 0)),
                            'number': 1
                        }
                        for reward in rewards_data['medal_rewards']
                        if reward.get('id') is not None
                    ]

                # 处理实物奖励
                if 'real_rewards' in rewards_data:
                    task_rewards['real_rewards'] = [
                        {
                            'name': reward.get('name', ''),
                            'number': int(reward.get('number', 0))
                        }
                        for reward in rewards_data['real_rewards']
                        if reward.get('name') and reward.get('number') is not None
                    ]

            cursor.execute('''
                INSERT INTO task (
                    name, description, task_chain_id, parent_task_id,
                    task_type, task_status, task_scope, stamina_cost,
                    limit_time, repeat_time, is_enabled, repeatable,
                    need_check, task_rewards, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                data['name'],
                data.get('description', ''),
                int(data.get('task_chain_id', 0)),
                int(data.get('parent_task_id', 0)),
                data['task_type'],
                data.get('task_status', 'LOCKED'),
                int(data.get('task_scope', 0)),
                int(data.get('stamina_cost', 0)),
                int(data.get('limit_time', 0)),
                int(data.get('repeat_time', 1)),
                bool(data.get('is_enabled', False)),
                bool(data.get('repeatable', False)),
                bool(data.get('need_check', False)),
                json.dumps(task_rewards)
            ))

            task_id = cursor.lastrowid
            conn.commit()

            return ResponseHandler.success(
                data={"id": task_id},
                msg="添加任务成功"
            )

        except Exception as e:
            print(f"添加任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"添加任务失败: {str(e)}"
            )
        finally:
            conn.close()

    def update_task(self, task_id, data):
        """更新任务"""
        try:
            # 验证必要字段
            if not data.get('name'):
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg="任务名称不能为空"
                )

            conn = self.get_db()
            cursor = conn.cursor()
            logger.info(f"更新任务: {data}")
            # 检查任务是否存在
            cursor.execute('SELECT id FROM task WHERE id = ?', (task_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )

            # 处理任务奖励数据
            task_rewards = {
                'points_rewards': [],
                'card_rewards': [],
                'medal_rewards': [],
                'real_rewards': []
            }

            # 处理各类奖励
            if 'task_rewards' in data:
                rewards_data = data['task_rewards']
                
                # 处理数值奖励
                if 'points_rewards' in rewards_data:
                    task_rewards['points_rewards'] = [
                        {
                            'type': reward.get('type', 'exp'),
                            'number': int(reward.get('number', 0))
                        }
                        for reward in rewards_data['points_rewards']
                        if reward.get('number') is not None
                    ]

                # 处理卡片奖励
                if 'card_rewards' in rewards_data:
                    task_rewards['card_rewards'] = [
                        {
                            'id': int(reward.get('id', 0)),
                            'number': int(reward.get('number', 0))
                        }
                        for reward in rewards_data['card_rewards']
                        if reward.get('id') is not None and reward.get('number') is not None
                    ]

                # 处理成就奖励
                if 'medal_rewards' in rewards_data:
                    task_rewards['medal_rewards'] = [
                        {
                            'id': int(reward.get('id', 0)),
                            'number': 1
                        }
                        for reward in rewards_data['medal_rewards']
                        if reward.get('id') is not None
                    ]

                # 处理实物奖励
                if 'real_rewards' in rewards_data:
                    task_rewards['real_rewards'] = [
                        {
                            'name': reward.get('name', ''),
                            'number': int(reward.get('number', 0))
                        }
                        for reward in rewards_data['real_rewards']
                        if reward.get('name') and reward.get('number') is not None
                    ]

            cursor.execute('''
                UPDATE task 
                SET name = ?, 
                    description = ?, 
                    task_chain_id = ?,
                    parent_task_id = ?,
                    task_type = ?,
                    task_status = ?,
                    task_scope = ?,
                    stamina_cost = ?,
                    limit_time = ?,
                    repeat_time = ?,
                    is_enabled = ?,
                    repeatable = ?,
                    need_check = ?,
                    task_rewards = ?
                WHERE id = ?
            ''', (
                data['name'],
                data.get('description', ''),
                int(data.get('task_chain_id', 0)),
                int(data.get('parent_task_id', 0)),
                data['task_type'],
                data.get('task_status', 'LOCKED'),
                int(data.get('task_scope', 0)),
                int(data.get('stamina_cost', 0)),
                int(data.get('limit_time', 0)),
                int(data.get('repeat_time', 1)),
                bool(data.get('is_enabled', False)),
                bool(data.get('repeatable', False)),
                bool(data.get('need_check', False)),
                json.dumps(task_rewards),
                task_id
            ))

            conn.commit()

            return ResponseHandler.success(msg="更新任务成功")

        except Exception as e:
            print(f"更新任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"更新任务失败: {str(e)}"
            )
        finally:
            conn.close()

    def delete_task(self, task_id):
        """删除任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 检查任务是否存在
            cursor.execute('SELECT id FROM task WHERE id = ?', (task_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )

            # 删除任务
            cursor.execute('DELETE FROM task WHERE id = ?', (task_id,))
            conn.commit()

            return ResponseHandler.success(msg="删除任务成功")

        except Exception as e:
            print(f"删除任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"删除任务失败: {str(e)}"
            )
        finally:
            conn.close()

    # admin接口
    def get_player_tasks(self, page=1, limit=20):
        """获取玩家任务列表，支持分页"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 获取总数
            cursor.execute('SELECT COUNT(*) FROM player_task')
            total = cursor.fetchone()[0]

            # 计算偏移量
            offset = (page - 1) * limit

            # 获取分页数据
            cursor.execute('''
                SELECT 
                    pt.id,
                    pt.player_id,
                    pt.task_id,
                    t.name as task_name,
                    pt.starttime,
                    pt.endtime,
                    pt.status,
                    pt.complete_time,
                    pt.comment
                FROM player_task pt 
                LEFT JOIN task t ON pt.task_id = t.id 
                ORDER BY pt.id DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))

            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'id': row['id'],
                    'player_id': row['player_id'],
                    'task_id': row['task_id'],
                    'task_name': row['task_name'],
                    'starttime': row['starttime'],
                    'endtime': row['endtime'],
                    'status': row['status'],
                    'complete_time': row['complete_time'],
                    'comment': row['comment']
                })

            return ResponseHandler.success(
                data={
                    'tasks': tasks,
                    'total': total,
                    'page': page,
                    'limit': limit
                },
                msg="获取玩家任务列表成功"
            )

        except Exception as e:
            print(f"获取玩家任务列表失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取玩家任务列表失败: {str(e)}"
            )
        finally:
            conn.close()

    def get_player_task(self, task_id):
        """获取单个玩家任务详情"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 明确指定字段顺序
            cursor.execute('''
                SELECT 
                    pt.id,
                    pt.player_id,
                    pt.task_id,
                    t.name as task_name,
                    pt.starttime,
                    pt.endtime,
                    pt.status,
                    pt.complete_time,
                    pt.comment
                FROM player_task pt 
                LEFT JOIN task t ON pt.task_id = t.id 
                WHERE pt.id = ?
            ''', (task_id,))

            row = cursor.fetchone()
            if not row:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )

            # 使用字典构造确保字段顺序
            task = {
                'id': row['id'],
                'player_id': row['player_id'],
                'task_id': row['task_id'],
                'task_name': row['task_name'],
                'starttime': row['starttime'],
                'endtime': row['endtime'],
                'status': row['status'],
                'complete_time': row['complete_time'],
                'comment': row['comment']
            }

            return ResponseHandler.success(
                data=task,
                msg="获取玩家任务详情成功"
            )

        except Exception as e:
            print(f"获取玩家任务详情失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"获取玩家任务详情失败: {str(e)}"
            )
        finally:
            conn.close()

    def create_player_task(self, data):
        """创建玩家任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 验证必要字段
            required_fields = ['player_id', 'task_id']
            for field in required_fields:
                if field not in data:
                    return ResponseHandler.error(
                        code=StatusCode.PARAM_ERROR,
                        msg=f"缺少必要字段: {field}"
                    )

            # 设置默认值
            starttime = data.get('starttime', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            status = data.get('status', 'available')

            cursor.execute('''
                INSERT INTO player_task (
                    player_id, task_id, starttime, endtime,
                    status, complete_time, comment
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['player_id'],
                data['task_id'],
                starttime,
                data.get('endtime'),
                status,
                data.get('complete_time'),
                data.get('comment')
            ))

            task_id = cursor.lastrowid
            conn.commit()

            return ResponseHandler.success(
                data={'id': task_id},
                msg="创建玩家任务成功"
            )

        except Exception as e:
            print(f"创建玩家任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"创建玩家任务失败: {str(e)}"
            )
        finally:
            conn.close()

    def update_player_task(self, task_id, data):
        """更新玩家任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 检查任务是否存在
            cursor.execute('SELECT id FROM player_task WHERE id = ?', (task_id,))
            if not cursor.fetchone():
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )

            # 明确指定更新字段的顺序
            update_query = '''
                UPDATE player_task
                SET player_id = ?,
                    task_id = ?,
                    starttime = ?,
                    endtime = ?,
                    status = ?,
                    complete_time = ?,
                    comment = ?
                WHERE id = ?
            '''

            # 确保参数顺序与SQL字段顺序一致
            params = (
                data.get('player_id'),
                data.get('task_id'),
                data.get('starttime'),
                data.get('endtime'),
                data.get('status'),
                data.get('complete_time'),
                data.get('comment'),
                task_id
            )

            cursor.execute(update_query, params)
            conn.commit()

            # 获取更新后的数据
            cursor.execute('''
                SELECT 
                    pt.id,
                    pt.player_id,
                    pt.task_id,
                    t.name as task_name,
                    pt.starttime,
                    pt.endtime,
                    pt.status,
                    pt.complete_time,
                    pt.comment
                FROM player_task pt 
                LEFT JOIN task t ON pt.task_id = t.id 
                WHERE pt.id = ?
            ''', (task_id,))

            row = cursor.fetchone()
            updated_data = {
                'id': row['id'],
                'player_id': row['player_id'],
                'task_id': row['task_id'],
                'task_name': row['task_name'],
                'starttime': row['starttime'],
                'endtime': row['endtime'],
                'status': row['status'],
                'complete_time': row['complete_time'],
                'comment': row['comment']
            }

            return ResponseHandler.success(
                data=updated_data,
                msg="更新玩家任务成功"
            )

        except Exception as e:
            print(f"更新玩家任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"更新玩家任务失败: {str(e)}"
            )
        finally:
            conn.close()

    def delete_player_task(self, task_id):
        """删除玩家任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM player_task WHERE id = ?', (task_id,))
            
            if cursor.rowcount == 0:
                return ResponseHandler.error(
                    code=StatusCode.TASK_NOT_FOUND,
                    msg="任务不存在"
                )

            conn.commit()
            return ResponseHandler.success(msg="删除玩家任务成功")

        except Exception as e:
            print(f"删除玩家任务失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=f"删除玩家任务失败: {str(e)}"
            )
        finally:
            conn.close()

task_service = TaskService() 