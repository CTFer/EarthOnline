/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:07:30
 * @LastEditTime: 2025-02-18 10:41:33
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
        
        // 回调函数
        this.connectCallback = null;
        this.disconnectCallback = null;
        this.errorCallback = null;
        
        this.socket = io(SERVER, {
            reconnection: true,
            reconnectionAttempts: 5,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 3000,
            autoConnect: false,  // 改为手动连接
            transports: ['websocket'],
            upgrade: false,
            forceNew: true,     // 强制创建新连接
            closeOnBeforeunload: true  // 页面关闭时自动断开
        });

        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        this.taskUpdateCallback = null;
        this.tagsUpdateCallback = null;
        this.gpsUpdateCallback = null;
        this.nfcTaskUpdateCallback = null;
        this.subscriptions = new Set();
        
        // 初始化完成后手动连接
        this.initializeSocket();
        this.socket.connect();
        
        Logger.info('WebSocket', '管理器初始化完成');
    }

    // 添加回调接口
    onConnect(callback) {
        Logger.debug('WebSocketManager', '注册连接回调');
        this.connectCallback = callback;
    }

    onDisconnect(callback) {
        Logger.debug('WebSocketManager', '注册断开连接回调');
        this.disconnectCallback = callback;
    }

    onError(callback) {
        Logger.debug('WebSocketManager', '注册错误回调');
        this.errorCallback = callback;
    }

    initializeSocket() {
        Logger.info('WebSocket', '开始初始化Socket连接');
        
        this.socket.on('connect', () => {
            Logger.info('WebSocket', 'WebSocket连接成功');
            this.updateStatus(true, 'WebSocket已连接');
            if (this.connectCallback) {
                this.connectCallback();
            }
        });

        this.socket.on('disconnect', () => {
            Logger.info('WebSocket', 'WebSocket断开');
            this.updateStatus(false, 'WebSocket已断开');
            if (this.disconnectCallback) {
                this.disconnectCallback();
            }
        });

        this.socket.on('connect_error', (error) => {
            Logger.error('WebSocket', 'WebSocket连接错误:', error);
            this.updateStatus(false, 'WebSocket连接错误');
            if (this.errorCallback) {
                this.errorCallback(error);
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
        if (this.subscriptions.has(room)) {
            Logger.debug('WebSocketManager', `已经订阅了房间 ${room}，跳过重复订阅`);
            return;
        }
        
        this.socket.emit('subscribe_tasks', { 
            player_id: playerId,
            room: room 
        });
        this.socket.emit('join', { room: room });
        this.subscriptions.add(room);
        Logger.info('WebSocket', `订阅任务更新: ${room}`);
    }

    unsubscribeFromTasks(playerId) {
        const room = `user_${playerId}`;
        if (!this.subscriptions.has(room)) return;
        
        this.socket.emit('unsubscribe_tasks', { 
            player_id: playerId,
            room: room 
        });
        this.socket.emit('leave', { room: room });
        this.subscriptions.delete(room);
        Logger.info('WebSocket', `取消订阅任务更新: ${room}`);
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
        if (this.subscriptions.has(`gps_${room}`)) {
            Logger.debug('WebSocketManager', `已经订阅了GPS ${room}，跳过重复订阅`);
            return;
        }
        
        Logger.info('WebSocket', '订阅GPS更新:', room);
        this.socket.emit('subscribe_gps', { 
            player_id: playerId, 
            room: room 
        });
        this.subscriptions.add(`gps_${room}`);
    }

    // 取消订阅 GPS 更新
    unsubscribeFromGPS(playerId) {
        const room = `user_${playerId}`;
        if (!this.subscriptions.has(`gps_${room}`)) return;
        
        this.socket.emit('unsubscribe_gps', { 
            player_id: playerId, 
            room: room 
        });
        this.subscriptions.delete(`gps_${room}`);
        Logger.info('WebSocket', `取消订阅GPS更新: ${room}`);
    }

    // 添加NFC任务更新回调注册方法
    onNFCTaskUpdate(callback) {
        Logger.debug('WebSocketManager', '注册NFC任务更新回调');
        this.nfcTaskUpdateCallback = callback;
    }
} 