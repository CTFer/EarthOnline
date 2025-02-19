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
    WS_EVENTS
} from "../config/events.js";

class EventManager {
    constructor(services) {
        this.services = services;
        this.eventBus = services.eventBus;
        Logger.info('EventManager', '初始化事件管理器');
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
            
            Logger.info('EventManager', '事件监听器设置完成');
        } catch (error) {
            Logger.error('EventManager', '设置事件监听器失败:', error);
            throw error;
        }
    }

    /**
     * 初始化任务相关事件
     */
    initializeTaskEvents() {
        // 任务状态更新
        this.eventBus.on(TASK_EVENTS.STATUS_UPDATED, async (data) => {
            try {
                await this.services.taskService.updateTaskStatus(data);
                await this.services.uiService.updateTaskStatus(data);
            } catch (error) {
                Logger.error('EventManager', '处理任务状态更新失败:', error);
            }
        });

        // 任务完成
        this.eventBus.on(TASK_EVENTS.COMPLETED, async (data) => {
            try {
                await this.services.playerService.handleTaskComplete(data);
                await this.services.wordcloudService.updateWordCloud();
                this.eventBus.emit(AUDIO_EVENTS.PLAY, 'COMPLETE');
            } catch (error) {
                Logger.error('EventManager', '处理任务完成失败:', error);
            }
        });

        // 任务接受
        this.eventBus.on(TASK_EVENTS.ACCEPTED, async (data) => {
            try {
                const result = await this.services.taskService.acceptTask(data.taskId);
                if (result.code === 0) {
                    this.eventBus.emit(AUDIO_EVENTS.PLAY, 'ACCEPT');
                }
            } catch (error) {
                Logger.error('EventManager', '处理任务接受失败:', error);
            }
        });

        // 任务放弃
        this.eventBus.on(TASK_EVENTS.ABANDONED, async (data) => {
            try {
                await this.services.taskService.handleTaskAbandoned(data);
            } catch (error) {
                Logger.error('EventManager', '处理任务放弃失败:', error);
            }
        });
    }

    /**
     * 初始化玩家相关事件
     */
    initializePlayerEvents() {
        // 玩家ID更新
        this.eventBus.on(PLAYER_EVENTS.ID_UPDATED, async (newId) => {
            try {
                await this.services.wsService.subscribeToPlayerEvents(newId);
                await this.services.taskService.updatePlayerId(newId);
                await this.services.playerService.loadPlayerInfo();
            } catch (error) {
                Logger.error('EventManager', '处理玩家ID更新失败:', error);
            }
        });

        // 玩家信息更新
        this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, async (playerInfo) => {
            try {
                await this.services.uiService.updatePlayerInfo(playerInfo);
            } catch (error) {
                Logger.error('EventManager', '处理玩家信息更新失败:', error);
            }
        });

        // 玩家经验值更新
        this.eventBus.on(PLAYER_EVENTS.EXP_UPDATED, async (data) => {
            try {
                await this.services.uiService.updateLevelAndExp(data);
            } catch (error) {
                Logger.error('EventManager', '处理经验值更新失败:', error);
            }
        });
    }

    /**
     * 初始化地图相关事件
     */
    initializeMapEvents() {
        // 渲染器切换
        this.eventBus.on(MAP_EVENTS.RENDERER_CHANGED, async (type) => {
            try {
                await this.services.mapService.switchRenderer(type);
                this.services.uiService.updateMapSwitchButton(type);
            } catch (error) {
                Logger.error('EventManager', '处理地图渲染器切换失败:', error);
            }
        });

        // GPS更新
        this.eventBus.on(MAP_EVENTS.GPS_UPDATED, (data) => {
            try {
                this.services.mapService.handleGPSUpdate(data);
            } catch (error) {
                Logger.error('EventManager', '处理GPS更新失败:', error);
            }
        });
    }

    /**
     * 初始化UI相关事件
     */
    initializeUIEvents() {
        // 显示通知
        this.eventBus.on(UI_EVENTS.NOTIFICATION_SHOW, (data) => {
            try {
                this.services.uiService.showNotification(data);
            } catch (error) {
                Logger.error('EventManager', '显示通知失败:', error);
            }
        });

        // 显示模态框
        this.eventBus.on(UI_EVENTS.MODAL_SHOW, (data) => {
            try {
                this.services.uiService.showModal(data);
            } catch (error) {
                Logger.error('EventManager', '显示模态框失败:', error);
            }
        });
    }

    /**
     * 初始化音频相关事件
     */
    initializeAudioEvents() {
        // 播放音效
        this.eventBus.on(AUDIO_EVENTS.PLAY, (soundId) => {
            try {
                this.services.audioService.handlePlaySound(soundId);
            } catch (error) {
                Logger.error('EventManager', '播放音效失败:', error);
            }
        });

        // 音量变化
        this.eventBus.on(AUDIO_EVENTS.VOLUME_CHANGED, (data) => {
            try {
                this.services.audioService.handleVolumeChange(data);
            } catch (error) {
                Logger.error('EventManager', '处理音量变化失败:', error);
            }
        });
    }

    /**
     * 初始化WebSocket相关事件
     */
    initializeWSEvents() {
        // WebSocket连接状态
        this.eventBus.on(WS_EVENTS.CONNECTED, () => {
            try {
                this.services.uiService.showNotification({
                    type: 'SUCCESS',
                    message: 'WebSocket连接成功'
                });
            } catch (error) {
                Logger.error('EventManager', '处理WebSocket连接成功失败:', error);
            }
        });

        this.eventBus.on(WS_EVENTS.DISCONNECTED, () => {
            try {
                this.services.uiService.showNotification({
                    type: 'WARNING',
                    message: 'WebSocket连接断开'
                });
            } catch (error) {
                Logger.error('EventManager', '处理WebSocket断开连接失败:', error);
            }
        });
    }
}

export default EventManager;
