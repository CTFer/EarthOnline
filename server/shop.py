import eventlet
eventlet.monkey_patch()

from flask import Blueprint, jsonify, request, render_template, current_app
from admin import admin_required
from datetime import datetime, timedelta
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
            
    def get_db(self):
        """获取数据库连接"""
        try:
            db = sqlite3.connect(self.db_path, check_same_thread=False)
            db.row_factory = sqlite3.Row
            return db
        except Exception as e:
            logger.error(f"数据库连接失败: {str(e)}")
            raise
        
    def get_items(self, sort_by='price', order='asc', enabled_only=True):
        """获取商品列表"""
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
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取商品列表失败: {str(e)}")
            raise
        
    def add_item(self, name: str, description: str, price: int, stock: int, 
                 image_url: str, product_type: str, online_time: int = None, 
                 offline_time: int = None) -> int:
        """添加商品"""
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
                return item_id
                
        except Exception as e:
            logger.error(f"添加商品失败: {str(e)}")
            raise
        
    def update_item(self, item_id: int, **kwargs) -> bool:
        """更新商品信息"""
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
                    return False
                    
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
                return affected_rows > 0
                
        except Exception as e:
            logger.error(f"更新商品失败: {str(e)}")
            raise
        
    def delete_item(self, item_id: int) -> bool:
        """删除商品（软删除）"""
        try:
            with self.get_db() as db:
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE shop 
                    SET delete_time = datetime('now')
                    WHERE product_id = ?
                """, (item_id,))
                db.commit()
                
                success = cursor.rowcount > 0
                logger.info(f"删除商品 {item_id} {'成功' if success else '失败'}")
                return success
                
        except Exception as e:
            logger.error(f"删除商品失败: {str(e)}")
            raise
        
    def purchase_item(self, user_id: int, item_id: int, quantity: int = 1) -> dict:
        """购买商品"""
        try:
            current_timestamp = int(datetime.now().timestamp())
            cursor = self.get_db().cursor()
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
    logger.debug(f"收到添加商品请求: {data}")
    
    try:
        # 验证必填字段
        required_fields = ['name', 'description', 'price', 'stock', 'image_url', 'product_type']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"缺少必填字段: {field}")
        
        item_id = shop.add_item(
            name=data['name'],
            description=data['description'],
            price=int(data['price']),
            stock=int(data['stock']),
            image_url=data['image_url'],
            product_type=data['product_type'],
            online_time=data.get('online_time'),
            offline_time=data.get('offline_time')
        )
        logger.info(f"商品添加成功，ID: {item_id}")
        return jsonify({"code": 0, "data": {"id": item_id}})
    except Exception as e:
        logger.error(f"添加商品失败: {str(e)}")
        return jsonify({"code": 1, "msg": str(e)})

@shop_bp.route('/api/shop/items/<int:item_id>', methods=['PUT'])
@admin_required
def update_item(item_id):
    """更新商品"""
    data = request.get_json()
    logger.debug(f"收到更新商品请求: item_id={item_id}, data={data}")
    
    try:
        success = shop.update_item(item_id, **data)
        logger.info(f"商品更新{'成功' if success else '失败'}: item_id={item_id}")
        return jsonify({"code": 0 if success else 1})
    except Exception as e:
        logger.error(f"更新商品失败: {str(e)}")
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
    with shop.get_db() as db:
        cursor = db.cursor()
        cursor.execute("SELECT COUNT(*) FROM shop")
        count = cursor.fetchone()[0]
        logger.info(f"商品表中有 {count} 条记录")
except Exception as e:
    logger.error(f"数据库检查失败: {str(e)}") 