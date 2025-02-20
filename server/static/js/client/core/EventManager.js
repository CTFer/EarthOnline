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

class EventManager {
    constructor({
        eventBus,
        taskService,
        playerService,
        uiService,
        mapService,
        audioService,
        wsService,
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
        this.wsService = wsService;
        this.wordcloudService = wordcloudService;
        this.live2dService = live2dService;
        this.notificationService = notificationService;

        Logger.info('EventManager', '初始化事件管理器');
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
            
            Logger.info('EventManager', '事件监听器设置完成');
        } catch (error) {
            this.handleError('初始化事件监听器', error, '初始化事件监听失败');
            throw error;
        }
    }

    /**
     * 初始化任务相关事件
     */
    async handleTaskStatusUpdate(data) {
        try {
            await this.taskService.updateTaskStatus(data);
            await this.uiService.updateTaskStatus(data);
        } catch (error) {
            this.handleError('任务状态更新', error, '更新任务状态失败');
        }
    }

    async handleTaskComplete(data) {
        try {
            await this.playerService.handleTaskComplete(data);
            await this.wordcloudService.updateWordCloud();
            this.eventBus.emit(AUDIO_EVENTS.PLAY, 'COMPLETE');
        } catch (error) {
            this.handleError('任务完成', error, '处理任务完成失败');
        }
    }

    async handleTaskAccept(data) {
        try {
            const result = await this.taskService.acceptTask(data.taskId);
            if (result.code === 0) {
                this.eventBus.emit(AUDIO_EVENTS.PLAY, 'ACCEPT');
            }
        } catch (error) {
            this.handleError('任务接受', error, '接受任务失败');
        }
    }

    async handleTaskAbandon(data) {
        try {
            await this.taskService.handleTaskAbandoned(data);
        } catch (error) {
            this.handleError('任务放弃', error, '放弃任务失败');
        }
    }

    initializeTaskEvents() {
        this.eventBus.on(TASK_EVENTS.STATUS_UPDATED, this.handleTaskStatusUpdate.bind(this));
        this.eventBus.on(TASK_EVENTS.COMPLETED, this.handleTaskComplete.bind(this));
        this.eventBus.on(TASK_EVENTS.ACCEPTED, this.handleTaskAccept.bind(this));
        this.eventBus.on(TASK_EVENTS.ABANDONED, this.handleTaskAbandon.bind(this));
    }

    /**
     * 初始化玩家相关事件
     */
    async handlePlayerIdUpdate(newId) {
        try {
            await this.wsService.subscribeToPlayerEvents(newId);
            await this.taskService.updatePlayerId(newId);
            await this.playerService.loadPlayerInfo();
        } catch (error) {
            this.handleError('玩家ID更新', error, '更新玩家信息失败');
        }
    }

    async handlePlayerInfoUpdate(playerInfo) {
        try {
            await this.uiService.updatePlayerInfo(playerInfo);
        } catch (error) {
            this.handleError('玩家信息更新', error, '更新玩家界面失败');
        }
    }

    async handlePlayerExpUpdate(data) {
        try {
            await this.uiService.updateLevelAndExp(data);
        } catch (error) {
            this.handleError('经验值更新', error, '更新经验值失败');
        }
    }

    initializePlayerEvents() {
        this.eventBus.on(PLAYER_EVENTS.ID_UPDATED, this.handlePlayerIdUpdate.bind(this));
        this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, this.handlePlayerInfoUpdate.bind(this));
        this.eventBus.on(PLAYER_EVENTS.EXP_UPDATED, this.handlePlayerExpUpdate.bind(this));
    }

    /**
     * 初始化地图相关事件
     */
    async handleMapRendererChange(type) {
        try {
            await this.mapService.switchRenderer(type);
            this.uiService.updateMapSwitchButton(type);
        } catch (error) {
            this.handleError('地图渲染器切换', error, '切换地图显示失败');
        }
    }

    handleGPSUpdate(data) {
        try {
            this.mapService.handleGPSUpdate(data);
        } catch (error) {
            this.handleError('GPS更新', error, '更新GPS位置失败');
        }
    }

    initializeMapEvents() {
        this.eventBus.on(MAP_EVENTS.RENDERER_CHANGED, this.handleMapRendererChange.bind(this));
        this.eventBus.on(MAP_EVENTS.GPS_UPDATED, this.handleGPSUpdate.bind(this));
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

    initializeUIEvents() {
        this.eventBus.on(UI_EVENTS.NOTIFICATION_SHOW, this.handleNotificationShow.bind(this));
        this.eventBus.on(UI_EVENTS.MODAL_SHOW, this.handleModalShow.bind(this));
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

    handleVolumeChange(data) {
        try {
            this.audioService.handleVolumeChange(data);
        } catch (error) {
            this.handleError('音量调节', error, '调节音量失败');
        }
    }

    initializeAudioEvents() {
        this.eventBus.on(AUDIO_EVENTS.PLAY, this.handlePlaySound.bind(this));
        this.eventBus.on(AUDIO_EVENTS.VOLUME_CHANGED, this.handleVolumeChange.bind(this));
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

    initializeWSEvents() {
        this.eventBus.on(WS_EVENTS.CONNECTED, this.handleWSConnect.bind(this));
        this.eventBus.on(WS_EVENTS.DISCONNECTED, this.handleWSDisconnect.bind(this));
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
     * 初始化通知相关事件
     */
    initializeNotificationEvents() {
        // 通知相关事件监听
        if (this.notificationService) {
            this.eventBus.on(NOTIFICATION_EVENTS.NEW, this.notificationService.handleNewNotification.bind(this.notificationService));
            this.eventBus.on(NOTIFICATION_EVENTS.UPDATE, this.notificationService.handleNotificationUpdate.bind(this.notificationService));
            this.eventBus.on(NOTIFICATION_EVENTS.DELETE, this.notificationService.handleNotificationDelete.bind(this.notificationService));
        }
    }
}

export default EventManager;
