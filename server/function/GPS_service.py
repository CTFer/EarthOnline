import sqlite3

import os
import logging
import time
from config import *
from datetime import datetime, timedelta
import numpy as np
from flask import request
import json
logger = logging.getLogger(__name__)


class GPSService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPSService, cls).__new__(cls)
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

    def add_gps(self, data):
        """添加GPS记录，如果位置变化不大则只更新时间"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 获取当前玩家最新的GPS记录
            cursor.execute('''
                SELECT id, x, y, addtime 
                FROM GPS 
                WHERE player_id = ? 
                ORDER BY addtime DESC 
                LIMIT 1
            ''', (data.get('player_id'),))

            last_record = cursor.fetchone()
            print(f"[GPS] 获取最新GPS记录: {last_record}")
            current_time = int(time.time())

            # 如果存在最新记录，比较坐标
            if last_record:
                # 将坐标转换为浮点数并保留GPS_ACCURACY位小数
                last_x = round(float(last_record['x']), GPS_ACCURACY)
                last_y = round(float(last_record['y']), GPS_ACCURACY)
                current_x = round(float(data.get('x')), GPS_ACCURACY)
                current_y = round(float(data.get('y')), GPS_ACCURACY)

                # 如果坐标相同（精确到6位小数），则只更新时间
                if last_x == current_x and last_y == current_y:
                    print("坐标相同更新时间")
                    cursor.execute('''
                        UPDATE GPS 
                        SET addtime = ? 
                        WHERE id = ?
                    ''', (current_time, last_record['id']))

                    conn.commit()
                    return json.dumps({
                        'code': 0,
                        'msg': '更新GPS时间成功',
                        'data': {'id': last_record['id']}
                    })

            # 如果是新位置或没有最新记录，则插入新记录
            cursor.execute('''
                INSERT INTO GPS (x, y, player_id, addtime, device, remark)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data.get('x'),
                data.get('y'),
                data.get('player_id'),
                current_time,
                data.get('device'),
                data.get('remark')
            ))
            print(f"[GPS] 插入新GPS记录: {data}")
            gps_id = cursor.lastrowid
            conn.commit()

            return json.dumps({
                'code': 0,
                'msg': '添加GPS记录成功',
                'data': {'id': gps_id}
            })

        except sqlite3.Error as e:
            logger.error(f"添加GPS记录失败: {str(e)}")
            return json.dumps({
                'code': 1,
                'msg': f'添加GPS记录失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()

    def get_gps(self, gps_id):
        """获取单个GPS记录"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM GPS WHERE id = ?', (gps_id,))
            gps = cursor.fetchone()

            if not gps:
                return json.dumps({
                    'code': 1,
                    'msg': 'GPS记录不存在',
                    'data': None
                }), 404

            return json.dumps({
                'code': 0,
                'msg': '获取GPS记录成功',
                'data': dict(gps)
            })

        except sqlite3.Error as e:
            return json.dumps({
                'code': 1,
                'msg': f'获取GPS记录失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()

    def get_player_gps(self, player_id):
        """
        获取玩家GPS记录
        """
        try:
            # 获取时间筛选参数
            start_time = request.args.get('start_time', type=int)
            end_time = request.args.get('end_time', type=int)
            
            # 获取分页参数
            page = request.args.get('page', type=int)
            per_page = request.args.get('per_page', type=int)
            
            print(f"[GPS] 获取玩家GPS记录")
            print(f"[GPS] 玩家ID: {player_id}")
            print(f"[GPS] 时间范围: {start_time} -> {end_time}")
            print(f"[GPS] 分页: page={page}, per_page={per_page}")
            
            # 添加数据验证
            if start_time and end_time and start_time > end_time:
                return json.dumps({
                    'code': 400,
                    'msg': '开始时间不能大于结束时间',
                    'data': None
                })

            result = gps_service.get_gps_records(
                player_id=player_id,
                start_time=start_time,
                end_time=end_time,
                page=page,
                per_page=per_page
            )
            
            # 添加调试日志
            # print(f"[GPS] 返回数据: {result.get_json() if hasattr(result, 'get_json') else result}")
            return result

        except Exception as e:
            error_msg = f"获取玩家GPS记录失败: {str(e)}"
            print(f"[GPS] 错误: {error_msg}")
            return json.dumps({
                'code': 500,
                'msg': error_msg,
                'data': None
            })

    def analyze_gps_data(self, data):
        """分析GPS数据的特征"""
        if not data:
            return

        # 计算时间间隔
        time_diffs = []
        for i in range(1, len(data)):
            time_diff = data[i]['addtime'] - data[i-1]['addtime']
            time_diffs.append(time_diff)

        # 计算距离间隔
        distances = []
        for i in range(1, len(data)):
            dist = ((float(data[i]['x']) - float(data[i-1]['x']))**2 + 
                    (float(data[i]['y']) - float(data[i-1]['y']))**2)**0.5
            distances.append(dist)

        # 计算统计信息
        if time_diffs:
            avg_time_diff = sum(time_diffs) / len(time_diffs)
            max_time_diff = max(time_diffs)
            min_time_diff = min(time_diffs)
        else:
            avg_time_diff = max_time_diff = min_time_diff = 0

        if distances:
            avg_distance = sum(distances) / len(distances)
            max_distance = max(distances)
            min_distance = min(distances)
        else:
            avg_distance = max_distance = min_distance = 0

        print(f"""
            [GPS] 数据分析结果:
            - 总点数: {len(data)}
            - 时间间隔(秒): 平均={avg_time_diff:.2f}, 最大={max_time_diff}, 最小=           {min_time_diff}
            - 距离间隔: 平均={avg_distance:.6f}, 最大={max_distance:.6f}, 最小=         {min_distance:.6f}
        """)

        return {
            'avg_time_diff': avg_time_diff,
            'max_time_diff': max_time_diff,
            'min_time_diff': min_time_diff,
            'avg_distance': avg_distance,
            'max_distance': max_distance,
            'min_distance': min_distance
        }

    def get_master_GPS_data(self, player_id, start_time=None, end_time=None, optimization_level=1):
        """获取优化后的GPS主数据"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 获取原始数据
            query = '''
                SELECT id, player_id, x, y, speed, accuracy, addtime 
                FROM GPS 
                WHERE player_id = ?
            '''
            params = [player_id]

            if start_time:
                query += ' AND addtime >= ?'
                params.append(start_time)
            if end_time:
                query += ' AND addtime <= ?'
                params.append(end_time)
            
            query += ' ORDER BY addtime ASC'
            cursor.execute(query, params)
            data = cursor.fetchall()
            
            original_count = len(data)
            print(f"[GPS] 原始数据条数: {original_count}")

            # 如果数据量小于阈值，直接返回
            if original_count <= GPS_CONFIG['SAMPLING_THRESHOLD']:
                print(f"[GPS] 数据量未超过阈值，返回原始数据: {original_count}条")
                return [{
                    'id': row['id'],
                    'x': float(row['x']),
                    'y': float(row['y']),
                    'speed': float(row['speed'] or 0),
                    'accuracy': float(row['accuracy'] or 0),
                    'addtime': row['addtime']
                } for row in data]

            # 分析数据特征
            stats = self.analyze_gps_data([dict(row) for row in data])

            # 根据数据特征动态调整采样策略
            if GPS_CONFIG['AUTO_OPTIMIZE']:
                target_count = GPS_CONFIG['MAX_DATA_NUMBER']
                time_window = end_time - start_time if end_time and start_time else stats['max_time_diff']
                
                # 计算理想采样间隔
                ideal_interval = max(
                    time_window / target_count,  # 基于目标数量
                    stats['avg_time_diff'] * 2   # 基于平均时间间隔
                )

                print(f"[GPS] 计算采样间隔: {ideal_interval:.2f}秒")
                optimized_data = []
                last_added = None

                for row in data:
                    current_point = {
                        'id': row['id'],
                        'x': float(row['x']),
                        'y': float(row['y']),
                        'speed': float(row['speed'] or 0),
                        'accuracy': float(row['accuracy'] or 0),
                        'addtime': row['addtime']
                    }

                    # 始终保留第一个点
                    if not last_added:
                        optimized_data.append(current_point)
                        last_added = current_point
                        continue

                    # 计算与上一个点的时间和距离差
                    time_diff = current_point['addtime'] - last_added['addtime']
                    dist = ((current_point['x'] - last_added['x'])**2 + 
                           (current_point['y'] - last_added['y'])**2)**0.5

                    # 动态调整采样条件
                    should_add = (
                        time_diff >= ideal_interval or              # 时间间隔足够大
                        dist >= stats['avg_distance'] * 2 or        # 距离变化显著
                        current_point['speed'] >= 20 or             # 高速移动点
                        abs(current_point['speed'] - last_added['speed']) >= 10  # 速度变化显著
                    )

                    if should_add:
                        optimized_data.append(current_point)
                        last_added = current_point

                # 始终保留最后一个点
                if optimized_data[-1]['id'] != data[-1]['id']:
                    optimized_data.append({
                        'id': data[-1]['id'],
                        'x': float(data[-1]['x']),
                        'y': float(data[-1]['y']),
                        'speed': float(data[-1]['speed'] or 0),
                        'accuracy': float(data[-1]['accuracy'] or 0),
                        'addtime': data[-1]['addtime']
                    })

            else:
                # 使用固定参数优化
                optimized_data = []
                last_added = None

                for row in data:
                    current_point = {
                        'id': row['id'],
                        'x': float(row['x']),
                        'y': float(row['y']),
                        'speed': float(row['speed'] or 0),
                        'accuracy': float(row['accuracy'] or 0),
                        'addtime': row['addtime']
                    }

                    if not last_added:
                        optimized_data.append(current_point)
                        last_added = current_point
                        continue

                    dist = ((current_point['x'] - last_added['x'])**2 + 
                           (current_point['y'] - last_added['y'])**2)**0.5
                    time_diff = current_point['addtime'] - last_added['addtime']

                    if (dist > GPS_CONFIG['MIN_DISTANCE'] or 
                        time_diff > GPS_CONFIG['TIME_INTERVAL']):
                        optimized_data.append(current_point)
                        last_added = current_point

                # 始终保留最后一个点
                if optimized_data[-1]['id'] != data[-1]['id']:
                    optimized_data.append({
                        'id': data[-1]['id'],
                        'x': float(data[-1]['x']),
                        'y': float(data[-1]['y']),
                        'speed': float(data[-1]['speed'] or 0),
                        'accuracy': float(data[-1]['accuracy'] or 0),
                        'addtime': data[-1]['addtime']
                    })

            optimized_count = len(optimized_data)
            print(f"[GPS] 优化后数据条数: {optimized_count}")
            print(f"[GPS] 优化率: {((original_count - optimized_count) / original_count * 100):.2f}%")
            
            return optimized_data

        except Exception as e:
            logger.error(f"获取GPS主数据失败: {str(e)}")
            return []
        finally:
            conn.close()

    def get_gps_records_origin(self, player_id=None, start_time=None, end_time=None, page=None, per_page=None):
        """原始的GPS记录获取函数，支持分页"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            # 构建基础查询
            query = 'SELECT * FROM GPS WHERE 1=1'
            params = []

            # 添加玩家ID筛选
            if player_id:
                query += ' AND player_id = ?'
                params.append(player_id)

            # 添加时间筛选条件
            if start_time:
                query += ' AND addtime >= ?'
                params.append(start_time)
            if end_time:
                query += ' AND addtime <= ?'
                params.append(end_time)

            print(f"[GPS Service] SQL查询: {query}")
            print(f"[GPS Service] 参数: {params}")

            # 添加排序
            query += ' ORDER BY addtime ASC'

            # 添加分页
            if page is not None and per_page is not None:
                offset = (page - 1) * per_page
                query += ' LIMIT ? OFFSET ?'
                params.extend([per_page, offset])

            cursor.execute(query, params)
            records = [dict(row) for row in cursor.fetchall()]

            return json.dumps({
                'code': 0,
                'msg': '获取GPS记录成功',
                'data': {
                    'records': records,
                    'total': len(records)
                }
            })

        except Exception as e:
            print(f"Error in get_gps_records: {str(e)}")
            return json.dumps({
                'code': 1,
                'msg': str(e),
                'data': None
            })
        finally:
            conn.close()


    def get_gps_records(self, player_id=None, start_time=None, end_time=None, page=None, per_page=None):
        """获取优化后的GPS记录，支持分页"""
        try:
            print(f"[GPS Service] 开始获取GPS记录")
            print(f"[GPS Service] 参数: player_id={player_id}, start_time={start_time}, end_time={end_time}")
            
            # 默认获取当天数据
            if not start_time:
                start_time = int(datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0).timestamp())
            if not end_time:
                end_time = int((datetime.now() + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0).timestamp())
            
            print(f"[GPS Service] 处理后的时间范围: {start_time} -> {end_time}")

            # 获取优化后的数据
            records = self.get_master_GPS_data(player_id, start_time, end_time)
            print(f"[GPS Service] 获取到原始记录数: {len(records)}")

            # 如果需要分页
            if page is not None and per_page is not None:
                total = len(records)
                start_idx = (page - 1) * per_page
                end_idx = start_idx + per_page
                records = records[start_idx:end_idx]
                print(f"[GPS Service] 分页后记录数: {len(records)}")
            else:
                total = len(records)

            response = {
                'code': 0,
                'msg': '获取GPS记录成功',
                'data': {
                    'records': records,
                    'total': total
                }
            }
            return json.dumps(response)

        except Exception as e:
            error_msg = f"获取GPS记录失败: {str(e)}"
            print(f"[GPS Service] 错误: {error_msg}")
            logger.error(error_msg)
            return json.dumps({
                'code': 1,
                'msg': error_msg,
                'data': None
            })

    def update_gps(self, gps_id, data):
        """更新GPS记录"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE GPS 
                SET x = ?, y = ?, device = ?, remark = ?
                WHERE id = ?
            ''', (
                data.get('x'),
                data.get('y'),
                data.get('device'),
                data.get('remark'),
                gps_id
            ))

            if cursor.rowcount == 0:
                return json.dumps({
                    'code': 1,
                    'msg': 'GPS记录不存在',
                    'data': None
                })

            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': '更新GPS记录成功',
                'data': None
            })

        except sqlite3.Error as e:
            return json.dumps({
                'code': 1,
                'msg': f'更新GPS记录失败: {str(e)}',
                'data': None
            })
        finally:
            conn.close()

    def delete_gps(self, gps_id):
        """删除GPS记录"""
        try:
            conn = self.get_db()
            cursor = conn.cursor()

            cursor.execute('DELETE FROM GPS WHERE id = ?', (gps_id,))

            if cursor.rowcount == 0:
                return json.dumps({
                    'code': 1,
                    'msg': 'GPS记录不存在',
                    'data': None
                }), 404

            conn.commit()
            return json.dumps({
                'code': 0,
                'msg': '删除GPS记录成功',
                'data': None
            })

        except sqlite3.Error as e:
            return json.dumps({
                'code': 1,
                'msg': f'删除GPS记录失败: {str(e)}',
                'data': None
            }), 500
        finally:
            conn.close()


gps_service = GPSService()
