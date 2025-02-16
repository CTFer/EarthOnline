/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:07:30
 * @LastEditTime: 2025-02-16 14:00:45
 * @LastEditors: 一根鱼骨棒
 * @Description: WebSocket通信管理器
 */
import { SERVER } from '../config/config.js';
import Logger from '../utils/logger.js';

// 新建 WebSocketManager 类
export default class WebSocketManager {
    constructor() {
        Logger.info('WebSocket', '初始化 WebSocketManager');
        Logger.debug('WebSocketManager', 'SERVER地址:', SERVER);
        this.socket = io(SERVER);
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.taskUpdateCallback = null;
        this.tagsUpdateCallback = null;
        this.gpsUpdateCallback = null;
        this.nfcTaskUpdateCallback = null;  // 添加NFC任务更新回调
        this.subscriptions = new Set();
        Logger.info('WebSocket', '管理器初始化');
        this.initializeSocket();
    }

    initializeSocket() {
        Logger.info('WebSocket', '开始初始化Socket连接');
        this.socket.on('connect', () => {
            Logger.info('WebSocket', 'WebSocket连接成功');
            this.updateStatus(true, 'WebSocket已连接');
        });

        this.socket.on('disconnect', () => {
            Logger.info('WebSocket', 'WebSocket断开');
            this.updateStatus(false, 'WebSocket已断开');
        });

        this.socket.on('connect_error', (error) => {
            Logger.error('WebSocket', 'WebSocket连接错误:', error);
            this.updateStatus(false, 'WebSocket连接错误');
        });

        // 添加 GPS 更新事件监听
        this.socket.on('gps_update', (data) => {
            Logger.info('WebSocket', 'Received GPS update:', data);
            if (this.gpsUpdateCallback) {
                this.gpsUpdateCallback(data);
            }
        });

        // 添加NFC任务更新事件监听
        this.socket.on('nfc_task_update', (data) => {
            Logger.info('WebSocket', '收到NFC任务更新:', data);
            if (this.nfcTaskUpdateCallback) {
                this.nfcTaskUpdateCallback(data);
            }
        });

        // 添加任务更新事件监听
        this.socket.on('task_update', (data) => {
            Logger.info('WebSocket', '收到任务更新:', data);
            if (this.taskUpdateCallback) {
                this.taskUpdateCallback(data);
            }
        });
    }

    updateStatus(connected, message) {
        if (connected) {
            this.statusDot.classList.add('connected');
        } else {
            this.statusDot.classList.remove('connected');
        }
        this.statusText.textContent = message;
    }

    subscribeToTasks(playerId) {
        const room = `user_${playerId}`;
        this.socket.emit('subscribe_tasks', { 
            player_id: playerId,
            room: room 
        });
        this.socket.emit('join', { room: room });
    }

    onTaskUpdate(callback) {
        Logger.debug('WebSocketManager', '注册任务更新回调');
        this.taskUpdateCallback = callback;
    }

    onTagsUpdate(callback) {
        Logger.debug('WebSocketManager', '注册标签更新回调');
        this.tagsUpdateCallback = callback;
    }

    // 添加 GPS 更新回调注册方法
    onGPSUpdate(callback) {
        this.gpsUpdateCallback = callback;
    }

    // 订阅 GPS 更新
    subscribeToGPS(playerId) {
        const room = `user_${playerId}`;
        Logger.info('WebSocket', '订阅GPS更新:', room);
        this.socket.emit('subscribe_gps', { player_id: playerId, room: room });
    }

    // 添加NFC任务更新回调注册方法
    onNFCTaskUpdate(callback) {
        Logger.debug('WebSocketManager', '注册NFC任务更新回调');
        this.nfcTaskUpdateCallback = callback;
    }
} 