"""
调度器服务模块
处理应用程序的定时任务调度功能
"""
import schedule
import threading
import time
import logging
from datetime import datetime, time as dt_time
import sqlite3
import os
from typing import Optional

logger = logging.getLogger(__name__)

class SchedulerService:
    """调度器服务类"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(SchedulerService, cls).__new__(cls)
        return cls._instance
        
    def __init__(self):
        """初始化调度器服务"""
        if not hasattr(self, 'initialized'):
            self.db_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), 
                'database', 
                'game.db'
            )
            self.scheduler_thread = None
            self.is_running = False
            self.initialized = True
            
    def get_db_connection(self) -> sqlite3.Connection:
        """创建数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def assign_daily_tasks(self) -> None:
        """分配每日任务并处理过期任务"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()

            # 获取当天的7点和22点时间戳
            today = datetime.now().date()
            start_time = datetime.combine(today, dt_time(7, 0))  # 早上7点
            end_time = datetime.combine(today, dt_time(22, 0))   # 晚上10点
            start_timestamp = int(start_time.timestamp())
            end_timestamp = int(end_time.timestamp())
            current_time = int(datetime.now().timestamp())
            
            # 更新过期任务状态为UNFINISH
            cursor.execute('''
                UPDATE player_task 
                SET status = 'UNFINISH'
                WHERE status = 'IN_PROGRESS' 
                AND endtime < ? 
                AND endtime != 0
            ''', (current_time,))

            # 获取所有启用的每日任务
            cursor.execute('''
                SELECT id, task_scope 
                FROM task 
                WHERE is_enabled = 1 AND task_type = 'DAILY'
            ''')
            daily_tasks = cursor.fetchall()

            # 获取所有玩家ID
            cursor.execute('SELECT player_id FROM player_data')
            all_players = [row[0] for row in cursor.fetchall()]

            # 为每个任务分配玩家
            for task_id, task_scope in daily_tasks:
                if task_scope == 0:  # 所有玩家都可见的任务
                    players = all_players
                else:  # 特定玩家的任务
                    players = [task_scope]

                # 为符合条件的玩家添加任务
                for player_id in players:
                    # 检查玩家是否已有该任务
                    cursor.execute('''
                        SELECT id FROM player_task 
                        WHERE player_id = ? AND task_id = ? 
                        AND starttime >= ? AND starttime < ?
                    ''', (player_id, task_id, start_timestamp, end_timestamp))

                    if not cursor.fetchone():  # 如果玩家在今天还没有这个任务
                        cursor.execute('''
                            INSERT INTO player_task 
                            (player_id, task_id, starttime, endtime, status) 
                            VALUES (?, ?, ?, ?, 'IN_PROGRESS')
                        ''', (player_id, task_id, start_timestamp, end_timestamp))

            conn.commit()
            logger.info(f"每日任务分配成功 {datetime.now()}")

        except sqlite3.Error as e:
            logger.error(f"数据库错误在assign_daily_tasks: {str(e)}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def check_daily_tasks(self) -> None:
        """在程序启动时检查今日任务分配情况"""
        current_hour = datetime.now().hour
        if current_hour >= 7:  # 如果当前时间已过早上7点
            logger.info(f"检查每日任务分配情况 {datetime.now()}")
            self.assign_daily_tasks()  # 执行一次任务分配检查

    def run_scheduler(self) -> None:
        """运行调度器"""
        schedule.every().day.at("07:00").do(self.assign_daily_tasks)

        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def start(self) -> None:
        """启动调度器"""
        if not self.is_running:
            self.is_running = True
            self.check_daily_tasks()  # 启动时检查今日任务
            self.scheduler_thread = threading.Thread(target=self.run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            logger.info("启动调度器")

    def stop(self) -> None:
        """停止调度器"""
        if self.is_running:
            self.is_running = False
            if self.scheduler_thread:
                self.scheduler_thread.join()
            logger.info("停止调度器")

# 创建调度器服务实例
scheduler_service = SchedulerService() 