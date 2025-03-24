# -*- coding: utf-8 -*-
from flask import Blueprint, request, render_template
from admin import admin_required
import logging
from utils.response_handler import ResponseHandler, StatusCode, api_response
from function.ShopService import shop_service
from function.PlayerService import player_service
# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# 创建蓝图
shop_bp = Blueprint('shop', __name__)

def init_shop(app):
    """初始化商店"""
    shop_service.init_app(app)

@shop_bp.record
def on_blueprint_registered(state):
    """当蓝图被注册时调用"""
    app = state.app
    init_shop(app)

@shop_bp.route('/api/shop/items')
@api_response
def get_items():
    """获取商品列表"""
    try:
        logger.info(f"请求参数: {request.args}")
        
        # 获取请求参数
        sort_by = request.args.get('sort', 'price')
        order = request.args.get('order', 'asc')
        enabled_only = request.args.get('enabled_only', '1') == '1'
        
        logger.info(f"查询参数: sort_by={sort_by}, order={order}, enabled_only={enabled_only}")
        
        # 获取商品列表
        return shop_service.get_items(sort_by, order, enabled_only)
        
    except Exception as e:
        logger.error(f"处理请求失败: {str(e)}")
        logger.exception("详细错误信息:")
        return ResponseHandler.error(
            code=StatusCode.SHOP_ITEM_NOT_FOUND,
            msg=str(e)
        )

@shop_bp.route('/api/shop/items', methods=['POST'])
@admin_required
@api_response
def add_item():
    """添加商品"""
    data = request.get_json()
    logger.debug(f"收到添加商品请求: {data}")
    
    try:
        # 验证必填字段
        required_fields = ['name', 'description', 'price', 'stock', 'image_url', 'product_type']
        for field in required_fields:
            if field not in data:
                return ResponseHandler.error(
                    code=StatusCode.PARAM_ERROR,
                    msg=f"缺少必填字段: {field}"
                )
        
        return shop_service.add_item(
            name=data['name'],
            description=data['description'],
            price=int(data['price']),
            stock=int(data['stock']),
            image_url=data['image_url'],
            product_type=data['product_type'],
            online_time=data.get('online_time'),
            offline_time=data.get('offline_time')
        )
    except Exception as e:
        logger.error(f"添加商品失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SHOP_PURCHASE_FAILED,
            msg=str(e)
        )

@shop_bp.route('/api/shop/items/<int:item_id>', methods=['PUT'])
@admin_required
@api_response
def update_item(item_id):
    """更新商品"""
    data = request.get_json()
    logger.debug(f"收到更新商品请求: item_id={item_id}, data={data}")
    
    try:
        return shop_service.update_item(item_id, **data)
    except Exception as e:
        logger.error(f"更新商品失败: {str(e)}")
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=str(e)
        )

@shop_bp.route('/api/shop/items/<int:item_id>', methods=['DELETE'])
@admin_required
@api_response
def delete_item(item_id):
    """删除商品"""
    try:
        return shop_service.delete_item(item_id)
    except Exception as e:
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=str(e)
        )

@shop_bp.route('/api/shop/purchase', methods=['POST'])
@api_response
@player_service.player_required
def purchase():
    """购买商品"""
    try:
        data = request.get_json()
        if not all(k in data for k in ['player_id', 'item_id']):
            return ResponseHandler.error(
                code=StatusCode.PARAM_ERROR,
                msg="缺少必要参数"
            )
            
        player_id = data['player_id']
        item_id = data['item_id']
        quantity = data.get('quantity', 1)
        
        return shop_service.purchase_item(player_id, item_id, quantity)
    except Exception as e:
        return ResponseHandler.error(
            code=StatusCode.SERVER_ERROR,
            msg=str(e)
        )

# 特殊格式的路由 - 不需要使用 ResponseHandler
@shop_bp.route('/admin/shop')
@admin_required
def shop_manage():
    """商店管理页面"""
    return render_template('admin/shop_manage.html')

@shop_bp.route('/shop')
def shop_page():
    """商店页面"""
    return render_template('client/shop.html') 