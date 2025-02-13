import Logger from '../../utils/logger.js';
import { SERVER } from '../../config/config.js';

class WebSocketManager {
    constructor(eventBus) {
        this.url = SERVER;
        this.eventBus = eventBus;
        this.socket = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        Logger.info('WebSocket', '初始化');
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