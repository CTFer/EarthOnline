/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 19:48:00
 * @LastEditors: 一根鱼骨棒
 * @Description: 事件管理器，负责处理所有事件监听和分发
 */
import Logger from '../../utils/logger.js';
import { 
    TASK_EVENTS,
    PLAYER_EVENTS,
    MAP_EVENTS,
    UI_EVENTS,
    AUDIO_EVENTS,
    WS_EVENTS,
    LIVE2D_EVENTS,
    NOTIFICATION_EVENTS,
    SHOP_EVENTS,
    ROUTE_EVENTS
} from "../config/events.js";
import { WS_EVENT_TYPES,WS_STATE } from '../config/wsConfig.js';

class EventManager {
    constructor({
        eventBus,
        taskService,
        playerService,
        uiService,
        mapService,
        audioService,
        websocketService,
        wordcloudService,
        live2dService,
        notificationService,
        shopService,
        router
    }) {
        // 事件总线
        this.eventBus = eventBus;
        
        // 服务注入
        this.taskService = taskService;
        this.playerService = playerService;
        this.uiService = uiService;
        this.mapService = mapService;
        this.audioService = audioService;
        this.websocketService = websocketService;
        this.wordcloudService = wordcloudService;
        this.live2dService = live2dService;
        this.notificationService = notificationService;
        this.shopService = shopService;
        this.router = router;

        Logger.info('EventManager', 'constructor:47', '初始化事件管理器');

        this.initializeEventListeners();
    }

    /**
     * 统一的错误处理方法
     * @private
     */
    handleError(context, error, userMessage) {
        Logger.error('EventManager', 'handleError:57', `${context}:`, error);
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
            type: 'ERROR',
            message: userMessage || '操作失败'
        });
        this.eventBus.emit(AUDIO_EVENTS.PLAY, 'ERROR');
    }

    /**
     * 初始化所有事件监听
     */
    initializeEventListeners() {
        Logger.info('EventManager', 'initializeEventListeners:69', '开始设置事件监听器');
        
        try {
            // 初始化各类事件监听
            this.initializeRouteEvents();
            this.initializeTaskEvents();
            this.initializePlayerEvents();
            this.initializeMapEvents();
            this.initializeUIEvents();
            this.initializeAudioEvents();
            this.initializeWSEvents();
            this.initializeLive2DEvents();
            this.initializeNotificationEvents();
            this.initializeShopEvents();
            
            // 初始化UI组件
            this.uiService.initializeMapUI();
            
            Logger.info('EventManager', 'initializeEventListeners:85', '事件监听器设置完成');
        } catch (error) {
            this.handleError('初始化事件监听器', error, '初始化事件监听失败');
            throw error;
        }
    }

    /**
     * 初始化路由相关事件
     */
    initializeRouteEvents() {
        // 路由变化事件监听
        this.eventBus.on(ROUTE_EVENTS.CHANGED, async (event) => {
            const { from, to } = event;
            Logger.info('EventManager', 'handleRouteChange', `路由变化: ${from} -> ${to}`);
            
            try {
                switch (to) {
                    case '/':
                        await this.handleHomeRoute();
                        break;
                    case '/shop':
                        await this.handleShopRoute();
                        break;
                }
            } catch (error) {
                Logger.error('EventManager', 'handleRouteChange', '处理路由变化失败:', error);
                this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                    type: 'ERROR',
                    message: '页面加载失败，请刷新重试'
                });
            }
        });
        
        Logger.info('EventManager', 'initializeRouteEvents', '路由事件监听器设置完成');
    }

    /**
     * 处理首页路由
     */
    async handleHomeRoute() {
        try {
            Logger.info('EventManager', 'handleHomeRoute', '处理首页路由');
            await Promise.all([
                this.taskService.loadTasks(),
                this.playerService.loadPlayerInfo(),
                this.mapService.initMap()
            ]);
            this.wordcloudService.updateWordCloud();
        } catch (error) {
            Logger.error('EventManager', 'handleHomeRoute', '处理首页路由失败:', error);
            throw error;
        }
    }

    /**
     * 处理商城路由
     */
    async handleShopRoute() {
        try {
            Logger.info('EventManager', 'handleShopRoute', '处理商城路由');
            
            // 初始化商城
            if (this.shopService) {
                await this.shopService.initializeShop();
                Logger.info('EventManager', 'handleShopRoute', '商城初始化完成');
            } else {
                throw new Error('商城服务未初始化');
            }
        } catch (error) {
            Logger.error('EventManager', 'handleShopRoute', '处理商城路由失败:', error);
            this.uiService.showErrorMessage('商城加载失败，请刷新重试');
            throw error;
        }
    }

    /**
     * 初始化任务相关事件
     */
    async handleTaskComplete(taskData) {
        try {
            await this.taskService.handleTaskComplete(taskData);
            this.eventBus.emit(PLAYER_EVENTS.EXP_UPDATED, {
                points: taskData.points,
                newExp: this.playerService.getPlayerData().experience
            });
        } catch (error) {
            this.handleError('处理任务完成', error, '处理任务完成失败');
        }
    }

    async handleTaskStatusUpdate(data) {
        try {
            await this.taskService.handleTaskStatusUpdate(data);
        } catch (error) {
            this.handleError('任务状态更新', error, '更新任务状态失败');
        }
    }

    async handleTaskAbandon(data) {
        try {
            await this.taskService.handleTaskAbandoned(data);
        } catch (error) {
            this.handleError('任务放弃', error, '放弃任务失败');
        }
    }

    async handleTaskCompleted(data) {
        try {
            await this.wordcloudService.updateWordCloud();
        } catch (error) {
            this.handleError('处理任务完成', error, '更新文字云失败');
        }
    }

    initializeTaskEvents() {
        this.eventBus.on(TASK_EVENTS.COMPLETED, this.handleTaskCompleted.bind(this));
        this.eventBus.on(TASK_EVENTS.STATUS_UPDATED, this.handleTaskStatusUpdate.bind(this));
        this.eventBus.on(TASK_EVENTS.ABANDONED, this.handleTaskAbandon.bind(this));
        
        Logger.info('EventManager', 'initializeTaskEvents:136', '任务事件监听器设置完成');
    }

    /**
     * 初始化玩家相关事件
     */
    async handlePlayerIdUpdate(newId) {
        try {
            await this.websocketService.subscribeToPlayerEvents(newId);
            await this.taskService.updatePlayerId(newId);
            await this.playerService.loadPlayerInfo();
        } catch (error) {
            this.handleError('玩家ID更新', error, '更新玩家信息失败');
        }
    }

    handlePlayerInfoUpdate(playerInfo) {
        try {
            this.playerService.handlePlayerInfoUpdate(playerInfo);
        } catch (error) {
            this.handleError('玩家信息更新', error, '更新玩家信息失败');
        }
    }

    initializePlayerEvents() {
        // 玩家相关事件监听
        this.eventBus.on(TASK_EVENTS.COMPLETED, this.handleTaskComplete.bind(this));
        this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, this.handlePlayerInfoUpdate.bind(this));
        
        Logger.info('EventManager', 'initializePlayerEvents:155', '玩家事件监听器设置完成');
    }

    /**
     * 初始化地图相关事件
     */
    async handleGPSUpdate(data) {
        try {
            await this.mapService.handleGPSUpdate(data);
        } catch (error) {
            this.handleError('GPS更新', error, '更新GPS失败');
        }
    }

    async handleMapRendererChange(type) {
        Logger.debug('EventManager', 'handleMapRendererChange:180', '处理地图渲染器切换:', type);
        try {
            // 获取当前渲染器类型
            const currentType = localStorage.getItem('mapType') || 'ECHARTS';
            if (currentType === type) {
                Logger.debug('EventManager', 'handleMapRendererChange:165', '地图类型相同，无需切换');
                return;
            }

            // 直接调用mapService的switchRenderer方法
            await this.mapService.switchRenderer(type);
            Logger.debug('EventManager', 'handleMapRendererChange:191', '地图切换完成:', type);
        } catch (error) {
            this.handleError('地图渲染器切换', error, '切换地图渲染器失败');
        }
    }

    async handleMapDisplayModeChange() {
        try {
            const newMode = await this.mapService.handleDisplayModeSwitch();
            if (newMode) {
                this.uiService.updateDisplayModeButtonText(newMode);
            }
        } catch (error) {
            this.handleError('显示模式切换', error, '切换显示模式失败');
        }
    }

    async handleMapTimeRangeChange(range) {
        try {
            await this.mapService.handleTimeRangeChange(range);
            this.uiService.updateCustomTimeRangeVisibility();
        } catch (error) {
            this.handleError('时间范围变化', error, '更新时间范围失败');
        }
    }

    initializeMapEvents() {
        this.eventBus.on(MAP_EVENTS.GPS_UPDATED, this.handleGPSUpdate.bind(this));
        this.eventBus.on(MAP_EVENTS.RENDERER_CHANGED, this.handleMapRendererChange.bind(this));
        this.eventBus.on(MAP_EVENTS.DISPLAY_MODE_CHANGED, this.handleMapDisplayModeChange.bind(this));
        this.eventBus.on(MAP_EVENTS.TIME_RANGE_CHANGED, this.handleMapTimeRangeChange.bind(this));
        
        Logger.info('EventManager', 'initializeMapEvents:223', '地图事件监听器设置完成');
    }

    /**
     * 初始化UI相关事件
     */
    handleNotificationShow(data) {
        try {
            this.uiService.showNotification(data);
        } catch (error) {
            this.handleError('显示通知', error, '显示通知失败');
        }
    }

    handleModalShow(data) {
        try {
            this.uiService.showModal(data);
        } catch (error) {
            this.handleError('显示模态框', error, '显示对话框失败');
        }
    }



    handleUIPlayerInfoUpdate(playerInfo) {
        try {
            this.uiService.updatePlayerInfo(playerInfo);
        } catch (error) {
            this.handleError('更新玩家信息UI', error, '更新玩家信息界面失败');
        }
    }

    initializeUIEvents() {
        // UI相关事件监听
        this.eventBus.on(UI_EVENTS.NOTIFICATION_SHOW, this.handleNotificationShow.bind(this));
        this.eventBus.on(UI_EVENTS.MODAL_SHOW, this.handleModalShow.bind(this));
        
        // 地图相关UI事件

        
        // 玩家相关UI事件
        this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, this.handleUIPlayerInfoUpdate.bind(this));
        
        Logger.info('EventManager', 'initializeUIEvents:266', 'UI事件监听器设置完成');
    }

    /**
     * 初始化音频相关事件
     */
    handlePlaySound(soundId) {
        try {
            this.audioService.handlePlaySound(soundId);
        } catch (error) {
            this.handleError('播放音效', error, '播放音效失败');
        }
    }

    handleStopSound(soundId) {
        try {
            this.audioService.handleStopSound(soundId);
        } catch (error) {
            this.handleError('停止音效', error, '停止音效失败');
        }
    }

    handleVolumeChange(data) {
        try {
            this.audioService.handleVolumeChange(data);
        } catch (error) {
            this.handleError('音量调节', error, '调节音量失败');
        }
    }

    initializeAudioEvents() {
        // 音频相关事件监听
        this.eventBus.on(AUDIO_EVENTS.PLAY, this.handlePlaySound.bind(this));
        this.eventBus.on(AUDIO_EVENTS.STOP, this.handleStopSound.bind(this));
        this.eventBus.on(AUDIO_EVENTS.VOLUME_CHANGED, this.handleVolumeChange.bind(this));
        
        Logger.info('EventManager', 'initializeAudioEvents:302', '音频事件监听器设置完成');
    }

    /**
     * 初始化WebSocket相关事件
     */
    initializeWSEvents() {
        // WebSocket连接状态事件
        this.eventBus.on(WS_EVENTS.CONNECTED, () => {
            this.uiService.updateWebSocketStatus('connected');
        });
        this.eventBus.on(WS_EVENTS.DISCONNECTED, () => {
            this.uiService.updateWebSocketStatus('disconnected');
        });
        this.eventBus.on(WS_EVENTS.ERROR, () => {
            this.uiService.updateWebSocketStatus('error');
        });
        
        Logger.info('EventManager', 'initializeWSEvents:320', 'WebSocket事件监听器设置完成');
    }

    /**
     * 初始化Live2D相关事件
     */
    initializeLive2DEvents() {
        // Live2D相关事件监听
        this.eventBus.on(LIVE2D_EVENTS.MODEL_LOADED, () => {
            Logger.info('EventManager', 'initializeLive2DEvents:329', 'Live2D模型加载完成');
        });
    }

    /**
     * 处理新通知
     */
    handleNewNotification(data) {
        try {
            this.notificationService.addNotification(data);
        } catch (error) {
            this.handleError('处理新通知', error, '添加新通知失败');
        }
    }

    /**
     * 处理通知更新
     */
    handleNotificationUpdate(data) {
        try {
            this.notificationService.updateNotification(data);
        } catch (error) {
            this.handleError('处理通知更新', error, '更新通知失败');
        }
    }

    /**
     * 处理通知删除
     */
    handleNotificationDelete(data) {
        try {
            this.notificationService.removeNotification(data.id);
        } catch (error) {
            this.handleError('处理通知删除', error, '删除通知失败');
        }
    }

    /**
     * 初始化通知相关事件
     */
    initializeNotificationEvents() {
        if (this.notificationService) {
            this.eventBus.on(NOTIFICATION_EVENTS.NEW, this.handleNewNotification.bind(this));
            this.eventBus.on(NOTIFICATION_EVENTS.UPDATE, this.handleNotificationUpdate.bind(this));
            this.eventBus.on(NOTIFICATION_EVENTS.DELETE, this.handleNotificationDelete.bind(this));
        }
        Logger.info('EventManager', 'initializeNotificationEvents:375', '通知事件监听器设置完成');
    }

    /**
     * 处理进入商城事件
     */
    handleShopEnter() {
        try {
            Logger.info('EventManager', 'handleShopEnter', '处理进入商城事件');
            this.router.navigate('/shop');
        } catch (error) {
            this.handleError('进入商城', error, '进入商城失败');
        }
    }

    /**
     * 处理离开商城事件
     */
    handleShopLeave() {
        try {
            Logger.info('EventManager', 'handleShopLeave', '处理离开商城事件');
            this.router.navigate('/');
        } catch (error) {
            this.handleError('离开商城', error, '离开商城失败');
        }
    }

    handleShopPurchase(data) {
        try {
            Logger.info('EventManager', 'handleShopPurchase:405', '处理商品购买事件:', data);
            this.shopService.purchaseItem(data);
        } catch (error) {
            this.handleError('购买商品', error, '购买商品失败');
        }
    }

    /**
     * 初始化商城事件
     */
    initializeShopEvents() {
        if (this.shopService) {
            this.eventBus.on(SHOP_EVENTS.ENTER, this.handleShopEnter.bind(this));
            this.eventBus.on(SHOP_EVENTS.LEAVE, this.handleShopLeave.bind(this));
            this.eventBus.on(SHOP_EVENTS.PURCHASE, this.handleShopPurchase.bind(this));
        }
        Logger.info('EventManager', 'initializeShopEvents', '商城事件监听器设置完成');
        // 监听商品列表更新事件
        this.eventBus.on(SHOP_EVENTS.ITEMS_UPDATED, (data) => {
            Logger.info('EventManager', 'initializeShopEvents', '商品列表更新');
            this.uiService.handleShopUIUpdate(data);
        });

        // 监听购买成功事件
        this.eventBus.on(SHOP_EVENTS.PURCHASE_SUCCESS, (data) => {
            Logger.info('EventManager', 'initializeShopEvents', '购买成功');
            this.uiService.showNotification({
                type: 'SUCCESS',
                message: data.message || '购买成功'
            });
        });

        // 监听购买失败事件
        this.eventBus.on(SHOP_EVENTS.PURCHASE_FAILED, (data) => {
            Logger.info('EventManager', 'initializeShopEvents', '购买失败');
            this.uiService.showNotification({
                type: 'ERROR',
                message: data.message || '购买失败'
            });
        });
    }
}

export default EventManager;
