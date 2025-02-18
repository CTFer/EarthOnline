/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 22:49:55
 * @LastEditTime: 2025-02-18 10:13:03
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';
import { 
    TASK_EVENTS,
    PLAYER_EVENTS,
    UI_EVENTS 
} from "../config/events.js";

class PlayerService {
    constructor(apiClient, eventBus, store) {
        this.api = apiClient;
        this.eventBus = eventBus;
        this.store = store;
        this.playerId = localStorage.getItem('playerId') || '1';
        this.playerData = null;
        this.loading = false;
        this.lastEmittedId = null;
        this.updateTimeout = null;
        
        // 初始化事件监听
        this.setupEventListeners();
        
        // 发布玩家ID初始化事件（使用防抖）
        this.emitPlayerIdUpdate(this.playerId);
        Logger.info('PlayerService', '初始化玩家服务');
    }

    setupEventListeners() {
        Logger.debug('PlayerService', '设置事件监听');
        
        // 监听任务完成事件，更新玩家经验值
        this.eventBus.on(TASK_EVENTS.COMPLETED, this.handleTaskComplete.bind(this));
        
        // 监听玩家信息更新事件
        this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, this.handlePlayerInfoUpdate.bind(this));
        
        Logger.info('PlayerService', '事件监听设置完成');
    }

    async loadPlayerInfo() {
        if (this.loading) {
            Logger.warn('PlayerService', '玩家信息正在加载中，跳过重复请求');
            return;
        }

        Logger.info('PlayerService', '加载玩家信息:', this.playerId);
        this.loading = true;

        try {
            if (!this.api) {
                throw new Error("API client not initialized");
            }

            const result = await this.api.getPlayerInfo(this.playerId);

            if (result.code === 0) {
                const playerData = result.data;
                this.playerData = playerData;
                
                // 更新store
                this.store.setState({ playerInfo: playerData });
                
                // 更新UI
                this.updatePlayerUI(playerData);
                
                // 发送玩家信息更新事件
                this.eventBus.emit(PLAYER_EVENTS.INFO_UPDATED, playerData);
                
                return playerData;
            } else {
                Logger.error('PlayerService', '加载玩家信息失败:', result.msg);
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('PlayerService', '加载玩家信息失败:', error);
            this.showPlayerError(error.message);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '加载玩家信息失败'
            });
            throw error;
        } finally {
            this.loading = false;
        }
    }

    updatePlayerUI(playerData) {
        Logger.debug('PlayerService', '更新玩家UI:', playerData);
        
        try {
            // 更新基本信息
            const nameElement = document.getElementById('playerName');
            const pointsElement = document.getElementById('playerPoints');
            
            if (nameElement) nameElement.textContent = playerData.player_name;
            if (pointsElement) pointsElement.textContent = playerData.points;
            
            // 更新等级和经验值
            this.updateLevelAndExp(playerData);
            
        } catch (error) {
            Logger.error('PlayerService', '更新玩家UI失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '更新玩家界面失败'
            });
        }
    }

    updateLevelAndExp(playerData) {
        try {
            const levelElement = document.querySelector('.level');
            const expElement = document.querySelector('.exp');
            const expBarInner = document.querySelector('.exp-bar-inner');

            if (levelElement) {
                levelElement.textContent = `${playerData.level}/100`;
            }
            if (expElement) {
                expElement.textContent = `${playerData.experience}/99999`;
            }
            if (expBarInner) {
                const expPercentage = (playerData.experience / 99999) * 100;
                expBarInner.style.width = `${Math.min(100, expPercentage)}%`;
            }
        } catch (error) {
            Logger.error('PlayerService', '更新等级和经验值失败:', error);
        }
    }

    showPlayerError(message = '加载失败') {
        Logger.debug('PlayerService', '显示玩家错误状态:', message);
        
        try {
            const nameElement = document.getElementById('playerName');
            const pointsElement = document.getElementById('playerPoints');
            const levelElement = document.querySelector('.level');
            const expElement = document.querySelector('.exp');
            const expBarInner = document.querySelector('.exp-bar-inner');

            if (nameElement) nameElement.textContent = message;
            if (pointsElement) pointsElement.textContent = '0';
            if (levelElement) levelElement.textContent = '0/100';
            if (expElement) expElement.textContent = '0/99999';
            if (expBarInner) expBarInner.style.width = '0%';
            
        } catch (error) {
            Logger.error('PlayerService', '显示玩家错误状态失败:', error);
        }
    }

    async handleTaskComplete(taskData) {
        Logger.info('PlayerService', '处理任务完成:', taskData);
        try {
            if (taskData.points) {
                await this.loadPlayerInfo();
                
                // 发送经验值更新事件
                this.eventBus.emit(PLAYER_EVENTS.EXP_UPDATED, {
                    points: taskData.points,
                    newExp: this.playerData.experience
                });
            }
        } catch (error) {
            Logger.error('PlayerService', '处理任务完成失败:', error);
        }
    }

    handlePlayerInfoUpdate(playerInfo) {
        Logger.info('PlayerService', '处理玩家信息更新:', playerInfo);
        try {
            this.playerData = playerInfo;
            this.updatePlayerUI(playerInfo);
        } catch (error) {
            Logger.error('PlayerService', '处理玩家信息更新失败:', error);
        }
    }

    getPlayerId() {
        return this.playerId;
    }

    setPlayerId(id) {
        if (!id) {
            Logger.error('PlayerService', '无效的玩家ID');
            return;
        }

        Logger.info('PlayerService', '设置玩家ID:', id);
        
        try {
            this.playerId = id;
            localStorage.setItem('playerId', id);
            
            // 使用防抖发送ID更新事件
            this.emitPlayerIdUpdate(id);
            
            // 重新加载玩家信息
            this.loadPlayerInfo();
        } catch (error) {
            Logger.error('PlayerService', '设置玩家ID失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '更新玩家ID失败'
            });
        }
    }

    getPlayerData() {
        return this.playerData;
    }

    isInitialized() {
        return !!this.playerData;
    }

    async updatePlayerStats(stats) {
        Logger.info('PlayerService', '更新玩家状态:', stats);
        try {
            const result = await this.api.updatePlayerStats(this.playerId, stats);
            
            if (result.code === 0) {
                Logger.debug('PlayerService', '玩家状态更新成功:', result);
                await this.loadPlayerInfo();
                return result;
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('PlayerService', '更新玩家状态失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '更新玩家状态失败'
            });
            throw error;
        }
    }

    // 添加防抖的ID更新事件发送方法
    emitPlayerIdUpdate(id) {
        if (this.updateTimeout) {
            clearTimeout(this.updateTimeout);
        }
        
        // 如果ID相同且不是首次发送，则跳过
        if (this.lastEmittedId === id) {
            return;
        }

        this.updateTimeout = setTimeout(() => {
            this.lastEmittedId = id;
            this.eventBus.emit(PLAYER_EVENTS.ID_UPDATED, id);
            Logger.info('PlayerService', `发送玩家ID更新事件: ${id}`);
        }, 300); // 300ms 防抖
    }
}

export default PlayerService; 