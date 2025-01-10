# -*- coding: utf-8 -*-


# Author: 一根鱼骨棒 Email 775639471@qq.com

# Date: 2025-01-07 14:02:42

# LastEditTime: 2025-01-10 12:21:37

# LastEditors: 一根鱼骨棒

# Description: 本开源代码使用GPL 3.0协议

# Software: VScode

# Copyright 2025 迷舍


from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3
import os
from admin import admin_bp
from flask_socketio import SocketIO, emit
from datetime import datetime, time, timedelta
import schedule
import threading
import time as time_module


app = Flask(__name__)
CORS(app)  # 启用CORS支持跨域请求


# 数据库路径

DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')


app.secret_key = '00000000000000000000000000000000'  # 设置session密钥
app.register_blueprint(admin_bp, url_prefix='/admin')


# 初始化Flask-SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")


def get_db_connection():
    """创建数据库连接"""

    try:

        # 确保数据库目录存在

        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

        # 创建连接

        conn = sqlite3.connect(DB_PATH)

        print(f"Successfully connected to database at {DB_PATH}")  # 调试输出
        return conn

    except Exception as e:

        print(f"Database connection error: {str(e)}")  # 调试输出
        raise


@app.route('/api/player', methods=['GET'])
def get_player():
    """获取角色信息"""

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        # 从player_data表获取角色信息

        cursor.execute('''

            SELECT * FROM player_data where id=1
        ''')

        # 获取列名

        columns = [description[0] for description in cursor.description]

        # 获取结果并转换为字典
        character = cursor.fetchone()

        if character:
            player_data = dict(zip(columns, character))

            return jsonify({

                'id': player_data['id'],

                'user_id': player_data['user_id'],

                'stamina': player_data['stamina'],

                'strength': player_data['strength'],

                'intelligence': player_data['intelligence'],

                'player_name': player_data['player_name'],

                'create_time': player_data['create_time'],

                'level': player_data['level'],

                'experience': player_data['experience']

            })
        else:

            return jsonify({'error': 'Character not found'}), 404

    except sqlite3.Error as e:

        print("Database error:", str(e))  # 调试输出

        return jsonify({'error': str(e)}), 500

    finally:

        conn.close()


@app.route('/api/tasks/available/<int:user_id>', methods=['GET'])
def get_available_tasks(user_id):
    """获取可用任务列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 从tasks表获取可用任务，区分每日任务和普通任务
        # 添加user_id限制：task_scope=0表示所有玩家可见，或task_scope等于指定玩家ID
        cursor.execute('''
            SELECT 
                t.id,
                t.name,
                t.description,
                t.task_rewards,
                t.task_type,
                t.task_status
            FROM tasks t
            WHERE t.is_enabled = 1 
            AND (t.task_scope = 0 OR t.task_scope = ?)
            AND t.id NOT IN (
                SELECT task_id 
                FROM player_task 
                WHERE user_id = ? 
            )
        ''', (user_id, user_id))

        tasks = []
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        for row in rows:
            task_dict = dict(zip(columns, row))
            tasks.append(task_dict)

        return jsonify(tasks)

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 添加获取玩家当前任务的API


@app.route('/api/tasks/current/<int:user_id>', methods=['GET'])
def get_current_tasks(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    try:
        # 获取玩家当前进行中的任务
        c.execute('''
            SELECT 
                pt.id,
                t.name,
                t.description,
                t.points,
                t.stamina_cost,
                t.task_type,
                pt.starttime,
                pt.points_earned,
                pt.status
            FROM player_task pt
            JOIN tasks t ON pt.task_id = t.id
            WHERE pt.user_id = ? 
            ORDER BY pt.starttime DESC
        ''', (user_id,))

        tasks = []
        for row in c.fetchall():
            tasks.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'points': row[3],
                'stamina_cost': row[4],
                'starttime': row[5],
                'points_earned': row[6],
                'status': row[7],
                'task_type': row[8]
            })
        
        return jsonify(tasks)

    finally:
        conn.close()


@app.route('/api/tasks/<int:task_id>/accept', methods=['POST'])
def accept_task(task_id):
    """接受任务"""

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        # 检查任务是否存在且可接受

        cursor.execute('''

            SELECT status 

            FROM tasks 

            WHERE id = ?

        ''', (task_id,))

        task = cursor.fetchone()

        if not task:

            return jsonify({'error': 'Task not found'}), 404

        if task['status'] != 'AVAILABLE':

            return jsonify({'error': 'Task is not available'}), 400

        # 更新任务状态

        cursor.execute('''

            UPDATE tasks 

            SET status = 'IN_PROGRESS', character_id = 1 

            WHERE id = ?

        ''', (task_id,))

        conn.commit()

        return jsonify({'message': 'Task accepted successfully'})

    except sqlite3.Error as e:

        conn.rollback()

        return jsonify({'error': str(e)}), 500

    finally:

        conn.close()


@app.route('/api/tasks/<int:task_id>/complete', methods=['POST'])
def complete_task(task_id):
    """完成任务"""

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        # 检查任务状态

        cursor.execute('''

            SELECT status, reward_exp, reward_gold 

            FROM tasks 

            WHERE id = ? AND character_id = 1

        ''', (task_id,))

        task = cursor.fetchone()

        if not task:

            return jsonify({'error': 'Task not found'}), 404

        if task['status'] != 'IN_PROGRESS':

            return jsonify({'error': 'Task is not in progress'}), 400

        # 更新任务状态

        cursor.execute('''

            UPDATE tasks 

            SET status = 'COMPLETED' 

            WHERE id = ?

        ''', (task_id,))

        # 更新角色属性和经验值

        cursor.execute('''

            UPDATE characters 

            SET exp = exp + ?,

                gold = gold + ?,

                stamina = MIN(stamina + 5, 100),

                intelligence = intelligence + 1,

                strength = strength + 1

            WHERE id = 1

        ''', (task['reward_exp'], task['reward_gold']))

        conn.commit()

        return jsonify({

            'message': 'Task completed successfully',

            'rewards': {

                'exp': task['reward_exp'],

                'gold': task['reward_gold']

            }

        })

    except sqlite3.Error as e:

        conn.rollback()

        return jsonify({'error': str(e)}), 500

    finally:

        conn.close()


@app.route('/api/tasks/<int:task_id>/abandon', methods=['POST'])
def abandon_task(task_id):
    """放弃任务"""

    try:

        conn = get_db_connection()

        cursor = conn.cursor()

        # 检查任务状态

        cursor.execute('''

            SELECT status 

            FROM tasks 

            WHERE id = ? AND character_id = 1

        ''', (task_id,))

        task = cursor.fetchone()

        if not task:

            return jsonify({'error': 'Task not found'}), 404

        if task['status'] != 'IN_PROGRESS':

            return jsonify({'error': 'Task is not in progress'}), 400

        # 更新任务状态

        cursor.execute('''

            UPDATE tasks 

            SET status = 'ABANDONED' 

            WHERE id = ?

        ''', (task_id,))

        conn.commit()

        return jsonify({'message': 'Task abandoned successfully'})

    except sqlite3.Error as e:

        conn.rollback()

        return jsonify({'error': str(e)}), 500

    finally:

        conn.close()


@app.route('/api/tasks/nfc_post', methods=['POST'])
def nfc_task_post():
    """处理NFC任务提交"""
    conn = None  # 初始化连接变量
    try:
        data = request.values  # 使用request.values获取form-data数据

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # 验证必要字段
        required_fields = ['id', 'character', 'device']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # 检查任务状态
        cursor.execute('''
            SELECT id, name, description, is_enabled 
            FROM tasks 
            WHERE id = ? AND is_enabled = 1
        ''', (data['id'],))

        task = cursor.fetchone()

        if not task:
            return jsonify({'error': 'Task not found or not enabled'}), 404

        # 记录NFC打卡数据
        # cursor.execute('''
        #     INSERT INTO nfc_records (
        #         task_id,
        #         character_id,
        #         device_type,
        #         add_time
        #     ) VALUES (?, ?, ?, ?)
        # ''', (
        #     data['id'],
        #     data['character'],
        #     data['device'],
        #     data['addtime']
        # ))

        conn.commit()

        # 构建推送消息
        task_data = {
            'task_id': task[0],
            'task_name': task[1],
            'task_description': task[2],
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        # 通过WebSocket发送任务通知
        socketio.emit('nfc_task_update', task_data)

        return jsonify({
            'message': 'NFC task recorded successfully',
            'task': task_data
        })

    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")
        if conn:
            conn.rollback()  # 发生错误时回滚事务
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        print(f"Error: {str(e)}")
        if conn:
            conn.rollback()  # 发生错误时回滚事务
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:  # 只在连接存在时关闭
            conn.close()


def assign_daily_tasks():
    """每天早上7点分配每日任务"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 获取当天的7点和22点时间戳
        today = datetime.now().date()
        start_time = datetime.combine(today, time(7, 0))  # 早上7点
        end_time = datetime.combine(today, time(22, 0))   # 晚上10点
        start_timestamp = int(start_time.timestamp())
        end_timestamp = int(end_time.timestamp())

        # 获取所有启用的每日任务
        cursor.execute('''
            SELECT id, task_scope 
            FROM tasks 
            WHERE is_enabled = 1 AND task_type = 4
        ''')
        daily_tasks = cursor.fetchall()

        # 获取所有玩家ID
        cursor.execute('SELECT user_id FROM player_data')
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
                    WHERE user_id = ? AND task_id = ? 
                    AND starttime = ?
                ''', (player_id, task_id, start_timestamp))
                
                if not cursor.fetchone():  # 如果玩家还没有这个任务
                    cursor.execute('''
                        INSERT INTO player_task 
                        (user_id, task_id, starttime, endtime, status) 
                        VALUES (?, ?, ?, ?, 'available')
                    ''', (player_id, task_id, start_timestamp, end_timestamp))

        conn.commit()
        print(f"Daily tasks assigned successfully at {datetime.now()}")

    except sqlite3.Error as e:
        print(f"Database error in assign_daily_tasks: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

def run_scheduler():
    """运行调度器"""
    schedule.every().day.at("07:00").do(assign_daily_tasks)
    
    while True:
        schedule.run_pending()
        time_module.sleep(60)  # 每分钟检查一次

# 在应用启动时启动调度器
def start_scheduler():
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True  # 设置为守护线程
    scheduler_thread.start()

# 在应用启动时调用
if __name__ == '__main__':
    start_scheduler()
    # assign_daily_tasks() 测试使用
    app.run(debug=True)
