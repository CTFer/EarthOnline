# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-10-31 20:04:55
# LastEditTime: 2025-10-31 20:06:38
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import sqlite3
import os

# 数据库路径
db_path = os.path.join('server', 'APP', 'route', 'data.sqlite3')

# 省份名称映射表
province_mapping = {
    '北京市': '北京',
    '上海市': '上海',
    '天津市': '天津',
    '重庆市': '重庆',
    '河北省': '河北',
    '山西省': '山西',
    '辽宁省': '辽宁',
    '吉林省': '吉林',
    '黑龙江省': '黑龙江',
    '江苏省': '江苏',
    '浙江省': '浙江',
    '安徽省': '安徽',
    '福建省': '福建',
    '江西省': '江西',
    '山东省': '山东',
    '河南省': '河南',
    '湖北省': '湖北',
    '湖南省': '湖南',
    '广东省': '广东',
    '海南省': '海南',
    '四川省': '四川',
    '贵州省': '贵州',
    '云南省': '云南',
    '陕西省': '陕西',
    '甘肃省': '甘肃',
    '青海省': '青海',
    '台湾省': '台湾',
    '内蒙古自治区': '内蒙古',
    '广西壮族自治区': '广西',
    '西藏自治区': '西藏',
    '宁夏回族自治区': '宁夏',
    '新疆维吾尔自治区': '新疆',
    '香港特别行政区': '香港',
    '澳门特别行政区': '澳门'
}

def update_province_names():
    try:
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 打印数据库连接信息
        print(f"成功连接到数据库: {db_path}")
        
        # 创建一个备份表
        cursor.execute("CREATE TABLE IF NOT EXISTS city_backup AS SELECT * FROM city")
        conn.commit()
        print("已创建城市表备份")
        
        # 获取所有城市记录
        cursor.execute("SELECT cid, province FROM city WHERE province IS NOT NULL")
        cities = cursor.fetchall()
        
        print(f"找到 {len(cities)} 条城市记录需要处理")
        
        # 更新每个城市的省份名称
        updated_count = 0
        for cid, province in cities:
            if province and province in province_mapping:
                new_province = province_mapping[province]
                cursor.execute("UPDATE city SET province = ? WHERE cid = ?", (new_province, cid))
                updated_count += 1
                print(f"更新城市ID {cid}: {province} -> {new_province}")
            elif province:
                print(f"未找到映射: {province}")
        
        conn.commit()
        print(f"成功更新 {updated_count} 条记录")
        
        # 验证更新结果
        cursor.execute("SELECT DISTINCT province FROM city WHERE province IS NOT NULL")
        unique_provinces = cursor.fetchall()
        print("更新后的省份列表:")
        for p in unique_provinces:
            print(f"- {p[0]}")
            
    except Exception as e:
        print(f"更新过程中发生错误: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("数据库连接已关闭")

if __name__ == "__main__":
    print("开始更新省份名称...")
    update_province_names()
    print("省份名称更新完成！")