import sqlite3
import os
import logging
import time
from datetime import datetime
import json

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

    def get_available_tasks(self, player_id):
        """获取可用任务列表"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    t.id, t.name, t.description, t.stamina_cost,
                    t.task_rewards, t.task_type, t.task_status, t.limit_time, t.icon
                FROM task t
                WHERE t.is_enabled = 1 
                AND (t.task_scope = 0 OR t.task_scope = ?)
                AND t.id NOT IN (
                    SELECT task_id FROM player_task WHERE player_id = ?
                )
            ''', (player_id, player_id))

            tasks = []
            columns = [description[0] for description in cursor.description]
            rows = cursor.fetchall()

            for row in rows:
                task_dict = dict(zip(columns, row))
                tasks.append(task_dict)

            return json.dumps({
                'code': 0,
                'msg': '获取可用任务成功',
                'data': tasks
            })

        except sqlite3.Error as e:
            return json.dumps({
                'code': 1,
                'msg': f'获取任务失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()

    def get_current_tasks(self, player_id):
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
                    t.icon
                FROM player_task pt
                JOIN task t ON pt.task_id = t.id
                WHERE pt.player_id = ? 
                AND (pt.endtime > ? or pt.endtime is null)
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
                    'icon': row[8]
                })

            return json.dumps({
                'code': 0,
                'msg': '获取当前任务成功',
                'data': tasks
            })

        except sqlite3.Error as e:
            return json.dumps({
                'code': 1,
                'msg': f'获取当前任务失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()

    def accept_task(self, player_id, task_id):
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
                return json.dumps({
                    'code': 1,
                    'msg': '任务不存在或未启用',
                    'data': None
                })

            # 检查是否已接受该任务
            cursor.execute('''
                SELECT * FROM player_task 
                WHERE player_id = ? AND task_id = ?
            ''', (player_id, task_id))
            
            if cursor.fetchone():
                return json.dumps({
                    'code': 1,
                    'msg': '已接受该任务',
                    'data': None
                })

            # 添加任务记录
            current_time = int(time.time())
            endtime = current_time + task['limit_time'] if task['limit_time'] else None
            
            cursor.execute('''
                INSERT INTO player_task (
                    player_id, task_id, status, starttime, endtime
                ) VALUES (?, ?, 'IN_PROGRESS', ?, ?)
            ''', (player_id, task_id, current_time, endtime))
            
            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': '任务接受成功',
                'data': None
            })

        except sqlite3.Error as e:
            return json.dumps({
                'code': 1,
                'msg': f'接受任务失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()

    def abandon_task(self, player_id, task_id):
        """放弃任务"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE player_task 
                SET status = 'ABANDONED', 
                    complete_time = ? 
                WHERE player_id = ? 
                AND task_id = ? 
                AND status = 'IN_PROGRESS'
            ''', (int(time.time()), player_id, task_id))
            
            if cursor.rowcount == 0:
                return json.dumps({
                    'code': 1,
                    'msg': '任务不存在或状态错误',
                    'data': None
                })
                
            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': '任务已放弃',
                'data': None
            })

        except sqlite3.Error as e:
            return json.dumps({
                'code': 1,
                'msg': f'放弃任务失败: {str(e)}',
                'data': None
            }), 500
        finally:
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

    def complete_task_api(self, player_id, task_id):
        """完成任务的API，包含主线任务的处理逻辑"""
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
                return False, "任务状态无效或已完成"
                
            # 2. 发放任务奖励
            success, message, rewards = self._grant_task_rewards(conn, player_id, task_id)
            if not success:
                conn.rollback()
                return False, f"发放奖励失败: {message}"
                
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
            
            return True, "任务完成", result
            
        except Exception as e:
            conn.rollback()
            logger.error(f"完成任务失败: {str(e)}")
            return False, f"完成任务失败: {str(e)}", None
        finally:
            conn.close()

    def _grant_task_rewards(self, conn, player_id, task_id):
        """发放任务奖励（保持现有实现）"""
        # ... 现有的奖励发放代码 ...
        pass

task_service = TaskService() 