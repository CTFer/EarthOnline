# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-03-08 20:04:48
# LastEditTime: 2025-03-09 10:35:03
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

import os
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Union
from utils.response_handler import ResponseHandler, StatusCode

logger = logging.getLogger(__name__)

class ShopService:
    """商店服务类"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ShopService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ShopService._initialized:
            return
            
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            '..', 
            'database', 
            'game.db'
        )
        logger.info(f"初始化 ShopService 实例，数据库路径: {self.db_path}")
        ShopService._initialized = True
            
    def init_app(self, app):
        """初始化与应用的关联"""
        if not hasattr(self, 'app'):
            self.app = app
            logger.info("ShopService 实例与应用关联完成")
            
    def get_db(self) -> sqlite3.Connection:
        """获取数据库连接"""
        try:
            db = sqlite3.connect(self.db_path, check_same_thread=False)
            db.row_factory = sqlite3.Row
            return db
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise
        
    def get_items(self, sort_by: str = 'price', order: str = 'asc', enabled_only: bool = True) -> Dict:
        """
        获取商品列表
        :param sort_by: 排序字段
        :param order: 排序方式(asc/desc)
        :param enabled_only: 是否只返回启用的商品
        :return: 商品列表
        """
        try:
            current_timestamp = int(datetime.now().timestamp())
            with self.get_db() as db:
                cursor = db.cursor()
                
                query = """
                    SELECT 
                        product_id as id,
                        product_name as name,
                        product_description as description,
                        product_price as price,
                        product_stock as stock,
                        product_type,
                        product_image as image_url,
                        online_time,
                        offline_time,
                        create_time
                    FROM shop 
                    WHERE (online_time IS NULL OR online_time <= ?)
                    AND (offline_time='' OR offline_time IS NULL OR offline_time > ?)
                """
                
                # 安全的排序
                sort_map = {
                    'price': 'product_price',
                    'stock': 'product_stock',
                    'online_time': 'online_time',
                    'offline_time': 'offline_time',
                    'product_type': 'product_type',
                    'name': 'product_name'
                }
                sort_field = sort_map.get(sort_by, 'product_price')
                sort_order = 'ASC' if order.lower() == 'asc' else 'DESC'
                
                query += f" ORDER BY {sort_field} {sort_order}"
                
                cursor.execute(query, (current_timestamp, current_timestamp))
                items = cursor.fetchall()
                logger.info(f"查询到 {len(items)} 个商品")
                
                # 将 sqlite3.Row 对象转换为字典列表
                items_list = [{
                    'id': item['id'],
                    'name': item['name'],
                    'description': item['description'],
                    'price': item['price'],
                    'stock': item['stock'],
                    'product_type': item['product_type'],
                    'image_url': item['image_url'],
                    'online_time': item['online_time'],
                    'offline_time': item['offline_time'],
                    'create_time': item['create_time']
                } for item in items]
                
                return ResponseHandler.success(data=items_list)
                
        except Exception as e:
            logger.error(f"获取商品列表失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SHOP_ITEM_NOT_FOUND,
                msg=str(e)
            )
        
    def add_item(self, name: str, description: str, price: int, stock: int, 
                 image_url: str, product_type: str, online_time: int = None, 
                 offline_time: int = None) -> Dict:
        """
        添加商品
        :param name: 商品名称
        :param description: 商品描述
        :param price: 商品价格
        :param stock: 商品库存
        :param image_url: 商品图片URL
        :param product_type: 商品类型
        :param online_time: 上架时间
        :param offline_time: 下架时间
        :return: 添加结果
        """
        try:
            # 设置默认时间戳
            current_timestamp = int(datetime.now().timestamp())
            if not online_time:
                online_time = current_timestamp
            if not offline_time:
                # 默认下架时间为2099年
                offline_time = int(datetime(2099, 12, 31, 23, 59, 59).timestamp())
            
            logger.debug(f"添加商品: name={name}, price={price}, stock={stock}, "
                        f"type={product_type}, online={online_time}, offline={offline_time}")
            
            with self.get_db() as db:
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO shop (
                        product_name, 
                        product_description, 
                        product_price, 
                        product_stock, 
                        product_image,
                        product_type,
                        online_time,
                        offline_time,
                        create_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, description, price, stock, image_url, 
                      product_type, online_time, offline_time, current_timestamp))
                
                item_id = cursor.lastrowid
                db.commit()
                logger.info(f"商品添加成功: id={item_id}")
                return ResponseHandler.success(data={"id": item_id}, msg="商品添加成功")
                
        except Exception as e:
            logger.error(f"添加商品失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SHOP_PURCHASE_FAILED,
                msg=str(e)
            )
        
    def update_item(self, item_id: int, **kwargs) -> Dict:
        """
        更新商品信息
        :param item_id: 商品ID
        :param kwargs: 更新的字段
        :return: 更新结果
        """
        try:
            logger.debug(f"更新商品: item_id={item_id}, data={kwargs}")
            with self.get_db() as db:
                cursor = db.cursor()
                
                # 字段映射
                field_map = {
                    'name': 'product_name',
                    'description': 'product_description',
                    'price': 'product_price',
                    'stock': 'product_stock',
                    'image_url': 'product_image',
                    'product_type': 'product_type',
                    'online_time': 'online_time',
                    'offline_time': 'offline_time'
                }
                
                updates = []
                values = []
                
                for key, value in kwargs.items():
                    if key in field_map and value is not None:
                        updates.append(f"{field_map[key]} = ?")
                        # 对数值类型进行转换
                        if key in ['price', 'stock', 'online_time', 'offline_time']:
                            values.append(int(value))
                        else:
                            values.append(value)
                
                if not updates:
                    logger.warning("没有需要更新的字段")
                    return ResponseHandler.error(
                        code=StatusCode.PARAM_ERROR,
                        msg="没有需要更新的字段"
                    )
                    
                values.append(item_id)  # WHERE 条件的参数
                query = f"""
                    UPDATE shop 
                    SET {', '.join(updates)}
                    WHERE product_id = ?
                """
                
                logger.debug(f"执行SQL: {query}, 参数: {values}")
                cursor.execute(query, values)
                db.commit()
                
                affected_rows = cursor.rowcount
                logger.info(f"更新商品成功: 影响行数={affected_rows}")
                
                if affected_rows > 0:
                    return ResponseHandler.success(msg="商品更新成功")
                return ResponseHandler.error(
                    code=StatusCode.SHOP_ITEM_NOT_FOUND,
                    msg="商品不存在或更新失败"
                )
                
        except Exception as e:
            logger.error(f"更新商品失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=str(e)
            )
        
    def delete_item(self, item_id: int) -> Dict:
        """
        删除商品（软删除）
        :param item_id: 商品ID
        :return: 删除结果
        """
        try:
            with self.get_db() as db:
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE shop 
                    SET delete_time = datetime('now')
                    WHERE product_id = ?
                """, (item_id,))
                db.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"商品删除成功: id={item_id}")
                    return ResponseHandler.success(msg="商品删除成功")
                
                logger.warning(f"商品删除失败: id={item_id} - 商品不存在")
                return ResponseHandler.error(
                    code=StatusCode.SHOP_ITEM_NOT_FOUND,
                    msg="商品不存在或删除失败"
                )
                
        except Exception as e:
            logger.error(f"删除商品失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SERVER_ERROR,
                msg=str(e)
            )
        
    def purchase_item(self, player_id: int, item_id: int, quantity: int = 1) -> Dict:
        """
        购买商品
        :param player_id: 玩家ID
        :param item_id: 商品ID
        :param quantity: 购买数量
        :return: 购买结果
        """
        try:
            current_timestamp = int(datetime.now().timestamp())
            conn = self.get_db()
            cursor = conn.cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            # 获取商品信息并检查是否可购买
            cursor.execute("""
                SELECT 
                    product_id as id,
                    product_name as name,
                    product_price as price,
                    product_stock as stock
                FROM shop 
                WHERE product_id = ? 
                AND online_time <= ?
                AND (offline_time IS NULL OR offline_time > ?)
            """, (item_id, current_timestamp, current_timestamp))
            
            item = cursor.fetchone()
            if not item:
                return ResponseHandler.error(
                    code=StatusCode.SHOP_ITEM_NOT_FOUND,
                    msg="商品不存在或已下架"
                )
            
            if item['stock'] < quantity:
                return ResponseHandler.error(
                    code=StatusCode.SHOP_ITEM_SOLD_OUT,
                    msg="库存不足"
                )
                
            total_price = item['price'] * quantity
            
            # 检查并更新用户积分
            cursor.execute(
                "SELECT points FROM player_data WHERE player_id = ?", 
                (player_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                return ResponseHandler.error(
                    code=StatusCode.PLAYER_NOT_FOUND,
                    msg="用户不存在"
                )
                
            if user['points'] < total_price:
                return ResponseHandler.error(
                    code=StatusCode.PLAYER_POINTS_NOT_ENOUGH,
                    msg="积分不足"
                )
                
            # 扣除积分
            cursor.execute("""
                UPDATE player_data 
                SET points = points - ? 
                WHERE player_id = ?
            """, (total_price, player_id))
            
            # 记录积分变动
            cursor.execute("""
                INSERT INTO points_record 
                (player_id, number, addtime, total)
                VALUES (?, ?, strftime('%s','now'), (
                    SELECT points FROM player_data WHERE player_id = ?
                ))
            """, (player_id, -total_price, player_id))
            
            # 更新库存
            cursor.execute("""
                UPDATE shop 
                SET product_stock = product_stock - ? 
                WHERE product_id = ?
            """, (quantity, item_id))
            
            # 记录购买记录
            cursor.execute("""
                INSERT INTO shop_record 
                (user_id, product_id, exchange_quantity, exchange_time, status)
                VALUES (?, ?, ?, datetime('now'), '已完成')
            """, (player_id, item_id, quantity))
            
            conn.commit()
            return ResponseHandler.success(msg="购买成功")
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"购买商品失败: {str(e)}")
            return ResponseHandler.error(
                code=StatusCode.SHOP_PURCHASE_FAILED,
                msg=str(e)
            )
        finally:
            if cursor:
                cursor.close()

# 创建全局实例
shop_service = ShopService() 