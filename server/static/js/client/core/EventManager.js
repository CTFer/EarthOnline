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
    NOTIFICATION_EVENTS
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
        notificationService
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

        Logger.info('EventManager', '初始化事件管理器');

        this.initializeEventListeners();
    }

    /**
     * 统一的错误处理方法
     * @private
     */
    handleError(context, error, userMessage) {
        Logger.error('EventManager', `${context}:`, error);
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
        Logger.info('EventManager', '开始设置事件监听器');
        
        try {
            // 初始化各类事件监听
            this.initializeTaskEvents();
            this.initializePlayerEvents();
            this.initializeMapEvents();
            this.initializeUIEvents();
            this.initializeAudioEvents();
            this.initializeWSEvents();
            this.initializeLive2DEvents();
            this.initializeNotificationEvents();
            
            // 初始化UI组件
            this.uiService.initializeMapUI();
            
            Logger.info('EventManager', '事件监听器设置完成');
        } catch (error) {
            this.handleError('初始化事件监听器', error, '初始化事件监听失败');
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
        
        Logger.info('EventManager', '任务事件监听器设置完成');
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
        
        Logger.info('EventManager', '玩家事件监听器设置完成');
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
        Logger.debug('EventManager', '处理地图渲染器切换:', type);
        try {
            // 获取当前渲染器类型
            const currentType = localStorage.getItem('mapType') || 'ECHARTS';
            if (currentType === type) {
                Logger.debug('EventManager', '地图类型相同，无需切换');
                return;
            }

            // 直接调用mapService的switchRenderer方法
            await this.mapService.switchRenderer(type);
            Logger.debug('EventManager', '地图切换完成:', type);
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
        
        Logger.info('EventManager', '地图事件监听器设置完成');
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
        
        Logger.info('EventManager', 'UI事件监听器设置完成');
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
        
        Logger.info('EventManager', '音频事件监听器设置完成');
    }

    /**
     * 初始化WebSocket相关事件
     */
    handleWSConnect() {
        try {
            this.uiService.showNotification({
                type: 'SUCCESS',
                message: 'WebSocket连接成功'
            });
        } catch (error) {
            this.handleError('WebSocket连接', error, 'WebSocket连接失败');
        }
    }

    handleWSDisconnect() {
        try {
            this.uiService.showNotification({
                type: 'WARNING',
                message: 'WebSocket连接断开'
            });
        } catch (error) {
            this.handleError('WebSocket断开', error, 'WebSocket断开连接失败');
        }
    }

    handleWSConnecting() {
        try {
            this.uiService.updateWebSocketStatus("WebSocket连接中...", WS_STATE.CONNECTING);
        } catch (error) {
            this.handleError('WebSocket连接中', error, 'WebSocket连接状态更新失败');
        }
    }

    handleWSError() {
        try {
            this.uiService.updateWebSocketStatus("WebSocket连接错误", WS_STATE.ERROR);
            this.uiService.showNotification({
                type: 'ERROR',
                message: 'WebSocket连接错误'
            });
        } catch (error) {
            this.handleError('WebSocket错误', error, 'WebSocket错误状态更新失败');
        }
    }

    handleWSReconnecting(attempt) {
        try {
            const currentAttempt = typeof attempt === 'number' ? attempt : 1;
            const maxAttempts = WS_CONFIG.RECONNECT.maxAttempts;
            
            this.uiService.updateWebSocketStatus(
                `WebSocket重连中(${currentAttempt}/${maxAttempts})`,
                WS_STATE.RECONNECTING
            );
        } catch (error) {
            this.handleError('WebSocket重连', error, 'WebSocket重连状态更新失败');
        }
    }

    handleGPSUpdate(data) {
        try {
            if (data && typeof data === 'object') {
                this.mapService.handleGPSUpdate(data);
            } else {
                Logger.warn('EventManager', '收到无效的GPS数据:', data);
            }
        } catch (error) {
            this.handleError('GPS更新', error, 'GPS数据更新失败');
        }
    }

    initializeWSEvents() {
        // WebSocket连接状态事件
        this.eventBus.on(WS_EVENTS.CONNECTED, this.handleWSConnect.bind(this));
        this.eventBus.on(WS_EVENTS.DISCONNECTED, this.handleWSDisconnect.bind(this));
        this.eventBus.on(WS_EVENTS.CONNECTING, this.handleWSConnecting.bind(this));
        this.eventBus.on(WS_EVENTS.ERROR, this.handleWSError.bind(this));
        this.eventBus.on(WS_EVENTS.RECONNECTING, this.handleWSReconnecting.bind(this));

        // GPS更新事件
        this.eventBus.on(WS_EVENT_TYPES.BUSINESS.GPS_UPDATE, this.handleGPSUpdate.bind(this));
        
        Logger.info('EventManager', 'WebSocket事件监听器设置完成');
    }

    /**
     * 初始化Live2D相关事件
     */
    initializeLive2DEvents() {
        // Live2D相关事件监听
        this.eventBus.on(LIVE2D_EVENTS.MODEL_LOADED, () => {
            Logger.info('EventManager', 'Live2D模型加载完成');
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
        Logger.info('EventManager', '通知事件监听器设置完成');
    }
}

export default EventManager;
