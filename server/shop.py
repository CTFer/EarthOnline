import eventlet
eventlet.monkey_patch()

from flask import Blueprint, jsonify, request, render_template, current_app
from admin import admin_required
from datetime import datetime
from dataclasses import dataclass
import sqlite3
import os
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 修正数据库路径计算
current_dir = os.path.dirname(os.path.abspath(__file__))  # 获取当前文件所在目录
DATABASE = os.path.join(current_dir, 'database', 'game.db')  # 拼接正确的数据库路径

logger.info(f"当前目录: {current_dir}")
logger.info(f"数据库路径: {DATABASE}")

class Shop:
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Shop, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if Shop._initialized:
            return
            
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            'database', 
            'game.db'
        )
        logger.info(f"初始化 Shop 实例，数据库路径: {self.db_path}")
        Shop._initialized = True
            
    def init_app(self, app):
        """初始化与应用的关联"""
        if not hasattr(self, 'app'):
            self.app = app
            logger.info("Shop 实例与应用关联完成")
            
    def init_db(self):
        """初始化数据库连接"""
        try:
            logger.debug(f"尝试连接数据库: {self.db_path}")
            if not os.path.exists(self.db_path):
                logger.error(f"数据库文件不存在: {self.db_path}")
                raise FileNotFoundError(f"数据库文件不存在: {self.db_path}")
                
            db = sqlite3.connect(self.db_path)
            db.row_factory = sqlite3.Row
            
            # 测试连接
            cursor = db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop'")
            if not cursor.fetchone():
                logger.error("shop表不存在")
                raise Exception("shop表不存在")
            
            logger.debug("数据库连接成功")
            return db
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise
            
    def get_db(self):
        """获取数据库连接"""
        try:
            logger.debug(f"尝试连接数据库: {DATABASE}")
            if not os.path.exists(DATABASE):
                logger.error(f"数据库文件不存在: {DATABASE}")
                raise FileNotFoundError(f"数据库文件不存在: {DATABASE}")
                
            db = sqlite3.connect(DATABASE, check_same_thread=False)
            db.row_factory = sqlite3.Row
            
            # 测试连接
            cursor = db.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shop'")
            if not cursor.fetchone():
                logger.error("shop表不存在")
                raise Exception("shop表不存在")
                
            logger.debug("数据库连接成功")
            return db
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise
        
    def get_items(self, sort_by='price', order='asc', enabled_only=True):
        """获取商品列表"""
        try:
            with self.get_db() as db:
                cursor = db.cursor()
                query = """
                    SELECT 
                        product_id as id,
                        product_name as name,
                        product_description as description,
                        product_price as price,
                        product_stock as stock,
                        product_image as image_url,
                        create_time as created_at,
                        CASE WHEN delete_time IS NULL THEN 1 ELSE 0 END as is_enabled
                    FROM shop 
                    WHERE 1=1
                """
                if enabled_only:
                    query += " AND delete_time IS NULL"
                    
                # 安全处理排序字段
                sort_field_map = {
                    'price': 'product_price',
                    'stock': 'product_stock',
                    'created_at': 'create_time',
                    'name': 'product_name'
                }
                sort_by = sort_field_map.get(sort_by, 'product_price')
                    
                query += f" ORDER BY {sort_by} {'ASC' if order=='asc' else 'DESC'}"
                
                logger.debug(f"执行查询: {query}")
                
                cursor.execute(query)
                items = cursor.fetchall()
                
                logger.debug(f"查询结果: {len(items)} 条记录")
                return [dict(item) for item in items]
                
        except Exception as e:
            logger.error(f"获取商品列表失败: {str(e)}")
            raise
        
    def add_item(self, name: str, description: str, price: int, 
                stock: int, image_url: str) -> int:
        """添加商品"""
        cursor = self.get_db().cursor()
        cursor.execute("""
            INSERT INTO shop (
                product_name, 
                product_description, 
                product_price, 
                product_stock, 
                product_image,
                create_time
            ) VALUES (?, ?, ?, ?, ?, datetime('now'))
        """, (name, description, price, stock, image_url))
        self.get_db().commit()
        return cursor.lastrowid
        
    def update_item(self, item_id: int, **kwargs) -> bool:
        """更新商品信息"""
        field_map = {
            'name': 'product_name',
            'description': 'product_description',
            'price': 'product_price',
            'stock': 'product_stock',
            'image_url': 'product_image',
            'is_enabled': 'delete_time'
        }
        
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in field_map:
                if key == 'is_enabled':
                    fields.append(f"delete_time = {'NULL' if value else 'datetime(''now'')'}")
                else:
                    fields.append(f"{field_map[key]} = ?")
                    values.append(value)
        
        if not fields:
            return False
            
        values.append(item_id)
        query = f"""
            UPDATE shop 
            SET {', '.join(fields)}
            WHERE product_id = ?
        """
        
        cursor = self.get_db().cursor()
        cursor.execute(query, values)
        self.get_db().commit()
        return True
        
    def delete_item(self, item_id: int) -> bool:
        """删除商品（软删除）"""
        cursor = self.get_db().cursor()
        cursor.execute("""
            UPDATE shop 
            SET delete_time = datetime('now')
            WHERE product_id = ?
        """, (item_id,))
        self.get_db().commit()
        return True
        
    def purchase_item(self, user_id: int, item_id: int, quantity: int = 1) -> dict:
        """购买商品"""
        try:
            cursor = self.get_db().cursor()
            cursor.execute("BEGIN TRANSACTION")
            
            # 获取商品信息
            cursor.execute("""
                SELECT 
                    product_id as id,
                    product_name as name,
                    product_price as price,
                    product_stock as stock
                FROM shop 
                WHERE product_id = ? AND delete_time IS NULL
            """, (item_id,))
            item = cursor.fetchone()
            
            if not item:
                raise ValueError("商品不存在或已下架")
                
            if item['stock'] < quantity:
                raise ValueError("库存不足")
                
            total_price = item['price'] * quantity
            
            # 检查并更新用户积分
            cursor.execute(
                "SELECT points FROM player_data WHERE player_id = ?", 
                (user_id,)
            )
            user = cursor.fetchone()
            
            if not user:
                raise ValueError("用户不存在")
                
            if user['points'] < total_price:
                raise ValueError("积分不足")
                
            # 扣除积分
            cursor.execute("""
                UPDATE player_data 
                SET points = points - ? 
                WHERE player_id = ?
            """, (total_price, user_id))
            
            # 记录积分变动
            cursor.execute("""
                INSERT INTO points_record 
                (player_id, number, addtime, total)
                VALUES (?, ?, strftime('%s','now'), (
                    SELECT points FROM player_data WHERE player_id = ?
                ))
            """, (user_id, -total_price, user_id))
            
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
            """, (user_id, item_id, quantity))
            
            self.get_db().commit()
            return {"success": True}
            
        except Exception as e:
            self.get_db().rollback()
            return {"success": False, "error": str(e)}
        finally:
            cursor.close()

# 创建蓝图
shop_bp = Blueprint('shop', __name__)

# 创建 Shop 实例
shop = Shop()

def init_shop(app):
    """初始化商店"""
    shop.init_app(app)

@shop_bp.record
def on_blueprint_registered(state):
    """当蓝图被注册时调用"""
    app = state.app
    init_shop(app)

@shop_bp.route('/api/shop/items')
def get_items():
    """获取商品列表API"""
    try:
        logger.debug("收到获取商品列表请求")
        sort_by = request.args.get('sort', 'price')
        order = request.args.get('order', 'asc')
        enabled_only = request.args.get('enabled_only', '1') == '1'
        
        items = shop.get_items(sort_by, order, enabled_only)
        return jsonify({"code": 0, "data": items})
    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        return jsonify({"code": 1, "msg": str(e)}), 500

@shop_bp.route('/api/shop/items', methods=['POST'])
@admin_required
def add_item():
    """添加商品"""
    data = request.get_json()
    try:
        item_id = shop.add_item(
            name=data['name'],
            description=data['description'],
            price=int(data['price']),
            stock=int(data['stock']),
            image_url=data['image_url']
        )
        return jsonify({"code": 0, "data": {"id": item_id}})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

@shop_bp.route('/api/shop/items/<int:item_id>', methods=['PUT'])
@admin_required
def update_item(item_id):
    """更新商品"""
    data = request.get_json()
    try:
        success = shop.update_item(item_id, **data)
        return jsonify({"code": 0 if success else 1})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

@shop_bp.route('/api/shop/items/<int:item_id>', methods=['DELETE'])
@admin_required
def delete_item(item_id):
    """删除商品"""
    try:
        success = shop.delete_item(item_id)
        return jsonify({"code": 0 if success else 1})
    except Exception as e:
        return jsonify({"code": 1, "msg": str(e)})

@shop_bp.route('/api/shop/purchase', methods=['POST'])
def purchase():
    """购买商品"""
    data = request.get_json()
    user_id = data['user_id']
    item_id = data['item_id']
    quantity = data.get('quantity', 1)
    
    result = shop.purchase_item(user_id, item_id, quantity)
    return jsonify({"code": 0 if result['success'] else 1, "msg": result.get('error')})

@shop_bp.route('/admin/shop')
@admin_required
def shop_manage():
    """商店管理页面"""
    return render_template('admin/shop_manage.html')

@shop_bp.route('/shop')
def shop_page():
    """商店页面"""
    return render_template('shop.html')

# 启动时检查数据库
try:
    logger.info("正在检查数据库连接...")
    with shop.get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM shop")
        count = cursor.fetchone()[0]
        logger.info(f"商品表中有 {count} 条记录")
except Exception as e:
    logger.error(f"数据库检查失败: {str(e)}") 