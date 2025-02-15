/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:57:21
 * @LastEditTime: 2025-02-14 17:44:13
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';
import { SERVER } from '../../config/config.js';

class WebSocketManager {
    constructor(eventBus) {
        this.url = SERVER;
        this.eventBus = eventBus;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.playerService = null;
        Logger.info('WebSocket', '初始化');
    }

    setPlayerService(playerService) {
        this.playerService = playerService;
        Logger.debug('WebSocket','setPlayerService');
        this.subscribeToPlayerUpdates();
    }

    subscribeToPlayerUpdates() {
        if (!this.playerService) return;
        Logger.debug('WebSocket','subscribeToPlayerUpdates');
        const playerId = this.playerService.getPlayerId();
        this.socket.emit('subscribe', {
            type: 'player',
            playerId: playerId
        });
    }

    connect() {
        try {
            this.socket = io(this.url);
            this.setupEventHandlers();
            Logger.info('WebSocket', '连接成功');
        } catch (error) {
            Logger.error('WebSocket', '连接失败:', error);
            this.handleReconnect();
        }
    }

    setupEventHandlers() {
        // 任务相关
        this.socket.on('task_update', (data) => {
            Logger.info('WebSocket', '任务更新:', data);
            this.eventBus.emit('task:update', data);
        });

        // NFC相关
        this.socket.on('nfc_update', (data) => {
            Logger.info('WebSocket', 'NFC更新:', data);
            this.eventBus.emit('nfc:update', data);
        });

        // 玩家相关
        this.socket.on('player_update', (data) => {
            Logger.info('WebSocket', '玩家更新:', data);
            this.eventBus.emit('player:update', data);
        });

        // 连接状态
        this.socket.on('connect', () => {
            Logger.info('WebSocket', '连接成功');
            this.eventBus.emit('ws:connected');
        });

        this.socket.on('disconnect', () => {
            Logger.info('WebSocket', '断开连接');
            this.eventBus.emit('ws:disconnected');
            this.handleReconnect();
        });

        this.setupEventListeners();
    }

    setupEventListeners() {
        this.eventBus.on('player:id-updated', (newId) => {
            this.subscribeToPlayerUpdates();
        });
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            Logger.info('WebSocket', `尝试重新连接... 第 ${this.reconnectAttempts} 次`);
            setTimeout(() => this.connect(), 1000 * this.reconnectAttempts);
        }
    }

    // 发送消息方法
    emit(event, data) {
        if (this.socket && this.socket.connected) {
            Logger.info('WebSocket', `发送消息: ${event}`, data);
            this.socket.emit(event, data);
        } else {
            Logger.error('WebSocket', '无法发送消息: socket未连接');
        }
    }
}

export default WebSocketManager; 