/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-25 21:50:58
 * @LastEditors: 一根鱼骨棒
 * @Description: 商城服务模块
 */

import Logger from "../../utils/logger.js";
import { SHOP_EVENTS,UI_EVENTS } from '../config/events.js';

class ShopService {
    constructor(eventBus, api, playerService, router) {
        // 初始化日志记录器
        this.eventBus = eventBus;
        this.api = api;
        this.playerService = playerService;
        this.router = router;
    }

    /**
     * 进入商城页面
     */
    enterShop() {
        Logger.info('ShopService', 'enterShop', '正在进入商城页面...');
        this.router.navigate('/shop');
    }

    /**
     * 离开商城页面
     */
    leaveShop() {
        Logger.info('ShopService', 'leaveShop', '正在离开商城页面...');
        this.router.navigate('/');
    }

    /**
     * 加载用户积分
     */
    async loadUserPoints() {
        try {
            const points = await this.playerService.loadUserPoints();
            this.eventBus.emit(SHOP_EVENTS.ITEMS_UPDATED, { points });
            return points;
        } catch (error) {
            Logger.error('ShopService', 'loadUserPoints', '加载积分失败:', error);
            throw error;
        }
    }

    /**
     * 创建商品卡片数据对象
     */
    createItemCard(item) {
        // 返回标准化的商品数据对象
        return {
            id: item.id,
            name: item.name,
            description: item.description,
            price: item.price,
            image_url: item.image_url || '/static/img/default_item.png',
            stock: item.stock,
            product_type: item.product_type,
            online_time: item.online_time,
            offline_time: item.offline_time
        };
    }

    /**
     * 加载商品列表
     */
    async loadItems(sort = 'price', order = 'asc') {
        try {
            Logger.info('ShopService', 'loadItems', '开始加载商品列表');
            Logger.debug('ShopService', 'loadItems', `参数: sort=${sort}, order=${order}`);
            
            const response = await this.api.request(`/api/shop/items?sort=${sort}&order=${order}`, {
                method: 'GET'
            });
            Logger.debug('ShopService', 'loadItems', '收到响应:', response);
            
            if (!response) {
                throw new Error('服务器返回空响应');
            }

            if (response.code !== 0) {
                throw new Error(response.msg || '加载商品列表失败');
            }

            if (!response.data || !Array.isArray(response.data)) {
                throw new Error('商品数据格式错误');
            }
            
            const items = response.data.map(item => this.createItemCard(item));
            Logger.info('ShopService', 'loadItems', `成功加载 ${items.length} 个商品`);
            
            this.eventBus.emit(SHOP_EVENTS.ITEMS_UPDATED, { items });
            return items;
        } catch (error) {
            Logger.error('ShopService', 'loadItems', '加载商品列表失败:', error);
            this.eventBus.emit(SHOP_EVENTS.ITEMS_UPDATED, { 
                items: [], 
                error: error.message || '加载商品列表失败' 
            });
            throw error;
        }
    }

    /**
     * 购买商品
     */
    async purchaseItem(itemData) {
        try {
            const currentPlayerId = this.playerService.getPlayerId();
            const quantity = itemData.quantity || 1;
            
            Logger.debug('ShopService', 'purchaseItem', '准备购买商品:', {
                user_id: currentPlayerId,
                item_id: itemData.id,
                quantity: quantity
            });

            // 使用 Promise 包装购买流程
            return new Promise((resolve, reject) => {
                // 显示购买确认框
                this.eventBus.emit(UI_EVENTS.MODAL_SHOW, {
                    type: 'purchaseConfirm',
                    data: {
                        item: itemData,
                        quantity: quantity,
                        onConfirm: async (index) => {
                            try {
                                const response = await this.api.request('/api/shop/purchase', {
                                    method: 'POST',
                                    body: JSON.stringify({
                                        user_id: parseInt(currentPlayerId),
                                        item_id: itemData.id,
                                        quantity: quantity
                                    })
                                });

                                Logger.debug('ShopService', 'purchaseItem', '购买响应:', response);

                                if (response.code === 0) {
                                    this.eventBus.emit(SHOP_EVENTS.PURCHASE_SUCCESS, {
                                        item: itemData,
                                        message: '购买成功',
                                        quantity: quantity,
                                        totalPrice: quantity * itemData.price
                                    });
                                    
                                    // 重新加载积分和商品列表
                                    await Promise.all([
                                        this.loadUserPoints(),
                                        this.loadItems()
                                    ]);

                                    layer.close(index);
                                    resolve(true);
                                } else {
                                    this.eventBus.emit(SHOP_EVENTS.PURCHASE_FAILED, {
                                        item: itemData,
                                        message: response.msg || '购买失败',
                                        quantity: quantity,
                                        totalPrice: quantity * itemData.price
                                    });
                                    layer.close(index);
                                    resolve(false);
                                }
                            } catch (error) {
                                Logger.error('ShopService', 'purchaseItem', '购买失败:', error);
                                this.eventBus.emit(SHOP_EVENTS.PURCHASE_FAILED, {
                                    item: itemData,
                                    message: error.message || '购买失败',
                                    quantity: quantity,
                                    totalPrice: quantity * itemData.price
                                });
                                layer.close(index);
                                reject(error);
                            }
                        },
                        onCancel: (index) => {
                            layer.close(index);
                            resolve(false);
                        }
                    }
                });
            });
        } catch (error) {
            Logger.error('ShopService', 'purchaseItem', '购买失败:', error);
            this.eventBus.emit(SHOP_EVENTS.PURCHASE_FAILED, {
                item: itemData,
                message: error.message || '购买失败'
            });
            throw error;
        }
    }

    /**
     * 初始化商城页面
     */
    async initializeShop() {
        try {

            
            // 加载玩家信息
            await this.playerService.loadPlayerInfo();
            this.playerService.updatePlayerUI(this.playerService.getPlayerData());
            
            // 加载商品列表
            await this.loadItems();
            
            // 绑定排序按钮事件
            this.bindSortButtons();
            
            Logger.info('ShopService', 'initializeShop', '商城页面初始化完成');
        } catch (error) {
            Logger.error('ShopService', 'initializeShop', '商城页面初始化失败:', error);
            throw error;
        }
    }

    /**
     * 绑定排序按钮事件
     */
    bindSortButtons() {
        document.querySelectorAll('.shop-filter button').forEach(btn => {
            btn.addEventListener('click', async () => {
                try {
                    // 移除所有按钮的active类
                    document.querySelectorAll('.shop-filter button').forEach(b => {
                        b.classList.remove('layui-btn-normal');
                        b.classList.add('layui-btn-primary');
                    });
                    
                    // 添加当前按钮的active类
                    btn.classList.remove('layui-btn-primary');
                    btn.classList.add('layui-btn-normal');
                    
                    // 加载排序后的商品
                    await this.loadItems(btn.dataset.sort, btn.dataset.order);
                } catch (error) {
                    Logger.error('ShopService', 'bindSortButtons', '排序商品失败:', error);
                }
            });
        });
    }
}

export default ShopService;