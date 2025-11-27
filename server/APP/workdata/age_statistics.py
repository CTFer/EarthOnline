# -*- coding: utf-8 -*-

"""
年龄统计模块
负责处理数据库中用户年龄分布的统计功能
"""
import sqlite3
import os
import json
from datetime import datetime
from flask import request, jsonify
from .database import SQLiteDatabase, DatabaseManager

def get_age_distribution(db_name=None, table_name=None, birthday_field=None):
    """
    获取年龄区间分布统计
    默认使用通讯录数据库、通讯录表和date字段，支持自定义年龄段划分
    
    Args:
        db_name: 数据库名称（可选，默认"通讯录.db"）
        table_name: 表格名称（可选，默认"通讯录"）
        birthday_field: 生日字段名称（可选，默认"date"）
    
    Returns:
        jsonify: 包含年龄分布统计结果的JSON响应
    """
    try:
        # 获取请求参数，设置默认值
        if db_name is None:
            db_name = request.args.get('db', '通讯录.db')
        if table_name is None:
            table_name = request.args.get('table', '通讯录')
        if birthday_field is None:
            birthday_field = request.args.get('birthday_field', 'date')
            
        # 构建数据库路径
        db_path = os.path.join(r"d:\code\EarthOnline\server\APP\workdata\database", db_name)
        
        # 验证参数
        if not db_name:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称不能为空'
            })
        if not table_name or not birthday_field:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '表格名称和生日字段不能为空'
            })
        
        # 验证数据库文件是否存在
        if not os.path.exists(db_path):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': f'数据库 {db_name} 不存在'
            })
        
        # 获取自定义年龄段参数
        custom_age_ranges = None
        age_ranges_param = request.args.get('age_ranges')
        if age_ranges_param:
            try:
                custom_age_ranges = json.loads(age_ranges_param)
                # 验证参数格式
                if not isinstance(custom_age_ranges, list) or len(custom_age_ranges) == 0:
                    return jsonify({
                        'code': 400,
                        'data': None,
                        'msg': '自定义年龄段必须是非空数组'
                    })
            except json.JSONDecodeError:
                return jsonify({
                    'code': 400,
                    'data': None,
                    'msg': '自定义年龄段参数格式错误'
                })
        
        with SQLiteDatabase(db_path) as db:
            # 检查表格是否存在
            tables = db.get_tables()
            if table_name not in tables:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格不存在'
                })
            
            # 检查生日字段是否存在
            structure = db.get_table_structure(table_name)
            fields = [col['name'] for col in structure]
            if birthday_field not in fields:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '生日字段不存在'
                })
            
            # 查询所有记录的生日字段
            query = f"SELECT {birthday_field} FROM {table_name} WHERE {birthday_field} IS NOT NULL AND {birthday_field} != ''"
            results = db.execute_query(query)
            
            # 定义年龄区间
            if custom_age_ranges:
                # 使用自定义年龄段
                age_ranges = {}
                for age_range_str in custom_age_ranges:
                    age_ranges[age_range_str] = 0
            else:
                # 默认年龄段
                age_ranges = {
                    '0-18': 0,
                    '19-25': 0,
                    '26-35': 0,
                    '36-45': 0,
                    '46-55': 0,
                    '56-65': 0,
                    '65+': 0
                }
            
            # 获取当前日期
            today = datetime.now()
            
            # 计算每个记录的年龄并统计
            for row in results:
                # 处理返回的行数据，可能是字典或元组
                if isinstance(row, dict):
                    birthday_str = row[birthday_field]
                else:
                    # 如果是元组，取第一个元素
                    birthday_str = row[0]
                
                if not birthday_str:
                    continue
                
                try:
                    # 尝试不同的日期格式
                    formats = ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y%m%d']
                    birthday = None
                    
                    for fmt in formats:
                        try:
                            birthday = datetime.strptime(birthday_str, fmt)
                            break
                        except ValueError:
                            continue
                    
                    if not birthday:
                        continue
                    
                    # 计算年龄
                    age = today.year - birthday.year
                    # 调整年龄（如果生日还没过）
                    if (today.month, today.day) < (birthday.month, birthday.day):
                        age -= 1
                    
                    # 统计到相应的区间
                    if custom_age_ranges:
                        # 使用自定义年龄段逻辑
                        age_assigned = False
                        for i, age_range_str in enumerate(custom_age_ranges):
                            # 处理最后一个为 '65+' 格式的情况
                            if age_range_str.endswith('+'):
                                # 确保是最后一个区间
                                if i == len(custom_age_ranges) - 1:
                                    try:
                                        min_age = int(age_range_str[:-1])
                                        if age >= min_age:
                                            age_ranges[age_range_str] += 1
                                            age_assigned = True
                                            break
                                    except ValueError:
                                        continue
                            elif '-' in age_range_str:
                                try:
                                    # 处理 '0-18' 格式的区间
                                    min_age, max_age = map(int, age_range_str.split('-'))
                                    if min_age <= age <= max_age:
                                        age_ranges[age_range_str] += 1
                                        age_assigned = True
                                        break
                                except ValueError:
                                    continue
                        
                        # 如果没有匹配到任何自定义区间，跳过此记录
                        if not age_assigned:
                            continue
                    else:
                        # 默认年龄段逻辑
                        if age <= 18:
                            age_ranges['0-18'] += 1
                        elif age <= 25:
                            age_ranges['19-25'] += 1
                        elif age <= 35:
                            age_ranges['26-35'] += 1
                        elif age <= 45:
                            age_ranges['36-45'] += 1
                        elif age <= 55:
                            age_ranges['46-55'] += 1
                        elif age <= 65:
                            age_ranges['56-65'] += 1
                        else:
                            age_ranges['65+'] += 1
                except Exception:
                    # 跳过无法解析的日期
                    continue
            
            # 计算总数和百分比
            total_count = sum(age_ranges.values())
            age_distribution = []
            
            for age_range, count in age_ranges.items():
                percentage = (count / total_count * 100) if total_count > 0 else 0
                age_distribution.append({
                    'range': age_range,
                    'count': count,
                    'percentage': round(percentage, 2)
                })
            
            return jsonify({
                'code': 0,
                'data': {
                    'total_count': total_count,
                    'age_distribution': age_distribution
                },
                'msg': 'success'
            })
    except Exception as e:
        import traceback
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'获取年龄分布失败: {str(e)}',
            'debug': traceback.format_exc()
        })