/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 22:49:55
 * @LastEditTime: 2025-02-17 12:45:39
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';

class PlayerService {
    constructor(apiClient, eventBus, store) {
        this.api = apiClient;
        this.eventBus = eventBus;
        this.store = store;
        this.playerId = localStorage.getItem('playerId') || '1';
        this.playerData = null;
        
        // 发布玩家ID初始化事件
        this.eventBus.emit('player:id-initialized', this.playerId);
        Logger.info('PlayerService', '初始化玩家服务');
    }

    setupEventListeners() {
        // 监听任务完成事件，更新玩家经验值
        this.eventBus.on('task:completed', this.handleTaskComplete.bind(this));
        // 监听NFC识别事件，更新玩家ID
        this.eventBus.on('nfc:identity', this.handleIdentityUpdate.bind(this));
    }

    async loadPlayerInfo() {
        Logger.info('PlayerService', '加载玩家信息:', this.playerId);
        try {
            if (!this.api) {
                throw new Error("API client not initialized");
            }

            const result = await this.api.getPlayerInfo(this.playerId);

            if (result.code === 0) {
                const playerData = result.data;
                this.playerData = playerData;
                this.updatePlayerUI(playerData);
                this.eventBus.emit('player:loaded', playerData);
                return playerData;
            } else {
                Logger.error('PlayerService', '加载玩家信息失败:', result.msg);
                this.showPlayerError();
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('PlayerService', '加载玩家信息失败:', error);
            this.showPlayerError();
            throw error;
        }
    }

    updatePlayerUI(playerData) {
        Logger.debug('PlayerService', '更新玩家UI:', playerData);
        document.getElementById('playerName').textContent = playerData.player_name;
        document.getElementById('playerPoints').textContent = playerData.points;
        
        this.updateLevelAndExp(playerData);
        this.eventBus.emit('player:ui-updated', playerData);
    }

    updateLevelAndExp(playerData) {
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
    }

    showPlayerError() {
        Logger.debug('PlayerService', '显示玩家错误状态');
        document.getElementById('playerName').textContent = '加载失败';
        document.getElementById('playerPoints').textContent = '0';
        
        const levelElement = document.querySelector('.level');
        const expElement = document.querySelector('.exp');
        const expBarInner = document.querySelector('.exp-bar-inner');

        if (levelElement) levelElement.textContent = '0/100';
        if (expElement) expElement.textContent = '0/99999';
        if (expBarInner) expBarInner.style.width = '0%';
        
        this.eventBus.emit('player:error-ui-updated');
    }

    // 处理任务完成事件
    async handleTaskComplete(taskData) {
        Logger.info('PlayerService', '处理任务完成:', taskData);
        if (taskData.points) {
            await this.loadPlayerInfo(); // 重新加载玩家信息以更新经验值
        }
    }

    // 处理身份识别更新
    handleIdentityUpdate(data) {
        Logger.info('PlayerService', '处理身份识别更新:', data);
        if (data.player_id) {
            this.playerId = data.player_id;
            localStorage.setItem('playerId', data.player_id);
            this.loadPlayerInfo();
            this.eventBus.emit('player:identity-updated', data);
        }
    }

    // 获取玩家ID
    getPlayerId() {
        return this.playerId;
    }

    // 设置玩家ID
    setPlayerId(id) {
        this.playerId = id;
        localStorage.setItem('playerId', id);
        // 发布玩家ID更新事件
        this.eventBus.emit('player:id-updated', id);
        Logger.info('PlayerService', '更新玩家ID:', id);
    }

    // 获取玩家数据
    getPlayerData() {
        return this.playerData;
    }

    // 检查玩家是否已初始化
    isInitialized() {
        return !!this.playerData;
    }

    async updatePlayerStats(stats) {
        Logger.info('PlayerService', '更新玩家状态:', stats);
        try {
            const result = await this.api.updatePlayerStats(this.playerId, stats);
            Logger.debug('PlayerService', '玩家状态更新成功:', result);
            await this.loadPlayerInfo();
            return result;
        } catch (error) {
            Logger.error('PlayerService', '更新玩家状态失败:', error);
            throw error;
        }
    }
}

export default PlayerService; 