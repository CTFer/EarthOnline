# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-10-31 16:58:15
# LastEditTime: 2025-10-31 17:05:07
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import sqlite3
import os

# 城市文件路径
city_file_path = r'd:\code\EarthOnline\server\test\city.txt'
# 数据库文件路径
db_path = r'd:\code\EarthOnline\server\APP\route\data.sqlite3'

def update_city_provinces():
    print("开始更新城市省份信息...")
    
    # 检查文件是否存在
    if not os.path.exists(city_file_path):
        print(f"错误：城市文件不存在 - {city_file_path}")
        return
    
    if not os.path.exists(db_path):
        print(f"错误：数据库文件不存在 - {db_path}")
        return
    
    # 读取城市-省份映射
    city_province_map = {}
    # 用于处理简写形式的映射表
    simplified_map = {
        # 明确添加常见的简写映射
        '怒江州': '云南省',
        '西双版纳': '云南省',
        '德宏州': '云南省',
        '恩施': '湖北省',
        '湘西州': '湖南省',
        '阿坝州': '四川省',
        '黔南州': '贵州省',
        '黔东南州': '贵州省',
        '黔西南州': '贵州省',
        '大理州': '云南省',
        '红河州': '云南省',
        '文山州': '云南省',
        '楚雄州': '云南省',
        '迪庆州': '云南省',
        '临夏州': '甘肃省',
        '甘南州': '甘肃省',
        '东方': '海南省',
        '五指山': '海南省',
        '九寨沟': '四川省',
        '耒阳': '湖南省',
        '道孚': '四川省',
        '阆中': '四川省'
    }
    
    try:
        with open(city_file_path, 'r', encoding='utf-8') as f:
            # 跳过表头
            next(f)
            line_count = 0
            update_count = 0
            
            for line in f:
                line_count += 1
                try:
                    # 按制表符分割
                    parts = line.strip().split('\t')
                    if len(parts) >= 5:
                        city_name = parts[1].strip()
                        province = parts[4].strip()
                        
                        # 处理特殊情况，例如莱芜（现属济南市代管）
                        if '（' in province:
                            # 提取括号前的内容
                            province = province.split('（')[0]
                        
                        # 存储完整名称映射
                        city_province_map[city_name] = province
                        
                        # 检查是否有括号形式的名称，提取简写形式
                        if '（' in city_name and '）' in city_name:
                            # 获取括号中的内容
                            bracket_content = city_name.split('（')[1].split('）')[0]
                            # 如果括号内容以州结尾，可能有简写形式（如"怒江州（怒江傈僳族自治州）"）
                            if bracket_content.endswith('州'):
                                # 提取州名作为简写（如"怒江州"）
                                simplified_name = bracket_content.split('族')[0] if '族' in bracket_content else bracket_content
                                simplified_map[simplified_name] = province
                                # 也可能只有"州"作为后缀
                                if city_name.startswith(bracket_content.split('族')[0] + '州'):
                                    simplified_map[bracket_content.split('族')[0] + '州'] = province
                        
                        # 处理其他可能的简写形式
                        if city_name.endswith('（省直辖县级市）') or city_name.endswith('（省直辖县级行政单位）'):
                            simplified_name = city_name.split('（')[0]
                            simplified_map[simplified_name] = province
                        elif city_name.endswith('（县级市）'):
                            simplified_name = city_name.split('（')[0]
                            simplified_map[simplified_name] = province
                        elif city_name.endswith('（县级行政区）'):
                            simplified_name = city_name.split('（')[0]
                            simplified_map[simplified_name] = province
                        
                        update_count += 1
                except Exception as e:
                    print(f"处理第{line_count}行时出错: {e}")
            
            # 添加一些常见的简写映射规则
            # 处理"XX州"的情况
            for full_name, province in city_province_map.items():
                if '自治州' in full_name:
                    # 提取州名（如"怒江傈僳族自治州" -> "怒江州"）
                    parts = full_name.split('族')
                    if len(parts) > 0:
                        short_name = parts[0] + '州'
                        if short_name not in simplified_map:
                            simplified_map[short_name] = province
            
            print(f"成功读取{update_count}条城市-省份映射数据")
            print(f"生成了{simplified_map.__len__()}条简写映射规则")
    except Exception as e:
        print(f"读取城市文件时出错: {e}")
        return
    
    # 连接数据库并更新
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 查询现有的城市记录
        cursor.execute("SELECT cid, name FROM city")
        cities = cursor.fetchall()
        
        print(f"数据库中找到{cities.__len__()}个城市记录")
        
        # 更新省份信息
        updated_count = 0
        simplified_updated = 0
        
        for city in cities:
            cid, city_name = city
            province = None
            
            # 首先尝试完全匹配
            if city_name in city_province_map:
                province = city_province_map[city_name]
            # 然后尝试简写匹配
            elif city_name in simplified_map:
                province = simplified_map[city_name]
                simplified_updated += 1
            # 特殊处理一些可能的名称变体
            elif '市' in city_name and city_name.replace('市', '') in simplified_map:
                province = simplified_map[city_name.replace('市', '')]
                simplified_updated += 1
            elif city_name.endswith('州') and city_name[:-1] + '族自治州' in city_province_map:
                province = city_province_map[city_name[:-1] + '族自治州']
                simplified_updated += 1
            
            if province:
                cursor.execute(
                    "UPDATE city SET province = ? WHERE cid = ?",
                    (province, cid)
                )
                updated_count += 1
            else:
                print(f"警告：未找到城市 '{city_name}' 的省份信息")
        
        print(f"其中通过简写匹配更新了{simplified_updated}个城市")
        
        # 提交更改
        conn.commit()
        print(f"成功更新{updated_count}个城市的省份信息")
        
    except Exception as e:
        print(f"更新数据库时出错: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    update_city_provinces()
    print("更新完成！")