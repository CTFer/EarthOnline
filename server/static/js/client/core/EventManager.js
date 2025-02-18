/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 19:48:00
 * @LastEditors: 一根鱼骨棒
 * @Description: 事件管理器，负责处理所有事件监听和分发
 */
import Logger from '../../utils/logger.js';

class EventManager {
    constructor(services, core) {
        this.services = services;
        this.core = core;
        this.eventHandlers = new Map();
        Logger.info('EventManager', '初始化事件管理器');
    }

    /**
     * 初始化所有事件监听
     */
    initializeEventListeners() {
        Logger.info('EventManager', '开始设置事件监听器');
        
        try {
            // 设置各类事件监听
            this.setupTaskEvents();
            this.setupPlayerEvents();
            this.setupMapEvents();
            this.setupUIEvents();
            this.setupGlobalEvents();
            
            Logger.info('EventManager', '事件监听器设置完成');
        } catch (error) {
            Logger.error('EventManager', '设置事件监听器失败:', error);
            throw error;
        }
    }

    /**
     * 设置任务相关事件
     */
    setupTaskEvents() {
        Logger.debug('EventManager', '设置任务相关事件监听');

        // 任务加载完成事件
        this.core.eventBus.on('tasks:loaded', this.handleTasksLoaded.bind(this));
        
        // 当前任务更新事件
        this.core.eventBus.on('currentTasks:updated', this.handleCurrentTasksUpdated.bind(this));
        
        // 任务状态更新事件
        this.core.eventBus.on('task:status:updated', this.handleTaskStatusUpdated.bind(this));
        
        // 任务操作事件
        this.core.eventBus.on('task:accepted', this.handleTaskAccepted.bind(this));
        this.core.eventBus.on('task:abandoned', this.handleTaskAbandoned.bind(this));
        this.core.eventBus.on('task:completed', this.handleTaskCompleted.bind(this));
    }

    /**
     * 设置玩家相关事件
     */
    setupPlayerEvents() {
        Logger.debug('EventManager', '设置玩家相关事件监听');

        // 玩家ID更新事件
        this.core.eventBus.on('player:id-updated', this.handlePlayerIdUpdated.bind(this));
        
        // 玩家信息更新事件
        this.core.eventBus.on('player:info-updated', this.handlePlayerInfoUpdated.bind(this));
    }

    /**
     * 设置地图相关事件
     */
    setupMapEvents() {
        Logger.debug('EventManager', '设置地图相关事件监听');

        // 地图渲染器切换事件
        this.core.eventBus.on('map:renderer:changed', this.handleMapRendererChanged.bind(this));
        
        // GPS更新事件
        this.core.eventBus.on('gps:update', this.handleGPSUpdate.bind(this));
    }

    /**
     * 设置UI相关事件
     */
    setupUIEvents() {
        Logger.debug('EventManager', '设置UI相关事件监听');
        
        // 初始化UI服务的任务事件监听
        this.services.uiService.initTaskEvents();
    }

    /**
     * 设置全局事件
     */
    setupGlobalEvents() {
        Logger.debug('EventManager', '设置全局事件监听');
        
        // 全局错误事件
        this.core.eventBus.on('error', this.handleGlobalError.bind(this));
        
        // 应用初始化完成事件
        this.core.eventBus.on('app:initialized', () => {
            Logger.info('EventManager', '应用初始化完成');
        });
    }

    // 事件处理方法
    async handleTasksLoaded(tasks) {
        try {
            Logger.info('EventManager', '处理任务加载完成事件');
            await this.services.uiService.renderTaskList(tasks);
        } catch (error) {
            this.handleError(error, '任务加载失败');
        }
    }

    async handleCurrentTasksUpdated(tasks) {
        try {
            Logger.info('EventManager', '处理当前任务更新事件');
            await this.services.uiService.renderCurrentTasks(tasks);
        } catch (error) {
            this.handleError(error, '更新当前任务失败');
        }
    }

    async handleTaskStatusUpdated(data) {
        try {
            Logger.info('EventManager', '处理任务状态更新事件');
            await this.services.taskService.updateTaskStatus(data);
            await this.services.uiService.updateTaskStatus(data);
            
            if (data.status === 'COMPLETED') {
                this.services.audioService.playSound('COMPLETE');
            }
        } catch (error) {
            this.handleError(error, '更新任务状态失败');
        }
    }

    async handleTaskAccepted(data) {
        try {
            Logger.info('EventManager', '处理任务接受事件');
            const result = await this.services.taskService.acceptTask(data.taskId, data.playerId);
            
            if (result.code === 0) {
                this.services.uiService.showSuccessMessage('任务接受成功');
                this.services.audioService.playSound('ACCEPT');
            } else {
                this.services.uiService.showErrorMessage(result.msg || '接受任务失败');
                this.services.audioService.playSound('ERROR');
            }
        } catch (error) {
            this.handleError(error, '接受任务失败');
        }
    }

    async handleTaskAbandoned(data) {
        try {
            Logger.info('EventManager', '处理任务放弃事件');
            const result = await this.services.taskService.abandonTask(data.taskId, data.playerId);
            
            if (result.code === 0) {
                this.services.uiService.showSuccessMessage('任务已放弃');
                this.services.audioService.playSound('ABANDON');
            } else {
                this.services.uiService.showErrorMessage(result.msg || '放弃任务失败');
                this.services.audioService.playSound('ERROR');
            }
        } catch (error) {
            this.handleError(error, '放弃任务失败');
        }
    }

    async handleTaskCompleted(taskData) {
        try {
            Logger.info('EventManager', '处理任务完成事件');
            await this.services.wordcloudService.updateWordCloud();
            this.services.audioService.playSound('COMPLETE');
            this.services.uiService.showNotification({
                type: 'SUCCESS',
                message: `任务 ${taskData.name} 已完成！`
            });
        } catch (error) {
            this.handleError(error, '处理任务完成失败');
        }
    }

    async handlePlayerIdUpdated(newId) {
        try {
            Logger.info('EventManager', '处理玩家ID更新事件');
            this.services.wsManager.subscribeToTasks(newId);
            this.services.taskService.updatePlayerId(newId);
            await this.services.playerService.loadPlayerInfo();
            await this.services.taskService.loadTasks();
        } catch (error) {
            this.handleError(error, '更新玩家信息失败');
        }
    }

    async handlePlayerInfoUpdated(playerInfo) {
        try {
            Logger.info('EventManager', '处理玩家信息更新事件');
            await this.services.uiService.updatePlayerInfo(playerInfo);
        } catch (error) {
            this.handleError(error, '更新玩家界面失败');
        }
    }

    handleMapRendererChanged(type) {
        try {
            Logger.info('EventManager', '处理地图渲染器变更事件');
            this.services.mapService.switchRenderer(type);
        } catch (error) {
            this.handleError(error, '切换地图显示失败');
        }
    }

    handleGPSUpdate(gpsData) {
        try {
            Logger.debug('EventManager', '处理GPS更新事件');
            if (this.services.mapService.currentRenderer) {
                this.services.mapService.currentRenderer.updatePosition(gpsData);
                this.services.mapService.currentRenderer.updateGPSInfo(gpsData);
            }
        } catch (error) {
            this.handleError(error, '更新GPS数据失败');
        }
    }

    handleGlobalError(error) {
        Logger.error('EventManager', '全局错误:', error);
        this.services.uiService.showErrorMessage(error.message || '操作失败，请重试');
    }

    /**
     * 统一的错误处理方法
     * @param {Error} error 错误对象
     * @param {string} userMessage 用户友好的错误消息
     */
    handleError(error, userMessage) {
        Logger.error('EventManager', '事件处理错误:', error);
        this.services.uiService.showNotification({
            type: 'ERROR',
            message: userMessage || '操作失败，请重试'
        });
        this.services.audioService.playSound('ERROR');
    }
}

export default EventManager; 