/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:07:30
 * @LastEditTime: 2025-02-16 14:00:13
 * @LastEditors: 一根鱼骨棒
 * @Description: WebSocket通信管理器
 */
import { SERVER } from '../../config/config.js';
import Logger from '../../utils/logger.js';

export default class WebSocketManager {
    constructor() {
        Logger.info('WebSocket', '初始化 WebSocketManager');
        Logger.debug('WebSocketManager', 'SERVER地址:', SERVER);
        
        // 确保socket.io客户端库已加载
        if (typeof io === 'undefined') {
            Logger.error('WebSocketManager', 'Socket.IO client library not loaded');
            throw new Error('Socket.IO client library not loaded');
        }
        Logger.debug('WebSocketManager', 'Socket.IO 客户端库已加载');
        
        // 初始化socket连接 - 使用默认配置
        try {
            Logger.debug('WebSocketManager', '尝试创建Socket连接');
            this.socket = io(SERVER, {
                reconnection: true,
                reconnectionAttempts: 3,  // 最多重试3次
                reconnectionDelay: 500,   // 初始重连延迟500ms
                reconnectionDelayMax: 2000, // 最大重连延迟2秒
                timeout: 5000,            // 连接超时时间5秒
                autoConnect: true,
                transports: ['websocket'], // 强制使用WebSocket
                upgrade: false            // 禁用协议升级
            });
            Logger.debug('WebSocketManager', 'Socket实例创建成功');
        } catch (error) {
            Logger.error('WebSocketManager', '初始化socket连接失败:', error);
            throw error;
        }
        
        this.statusDot = document.querySelector('.status-dot');
        this.statusText = document.querySelector('.status-text');
        
        // 使用与原版本相同的回调方式
        this.taskUpdateCallback = null;
        this.tagsUpdateCallback = null;
        this.gpsUpdateCallback = null;
        this.nfcTaskUpdateCallback = null;
        
        // 订阅集合
        this.subscriptions = new Set();
        
        this.initializeSocket();
        Logger.info('WebSocketManager', '初始化完成');
    }

    initializeSocket() {
        Logger.info('WebSocketManager', '开始初始化Socket事件监听');
        
        // 连接成功事件
        this.socket.on('connect', () => {
            Logger.info('WebSocketManager', 'WebSocket连接成功');
            Logger.debug('WebSocketManager', 'Socket ID:', this.socket.id);
            this.updateStatus(true, 'WebSocket已连接');
            // 重新订阅之前的房间
            this.resubscribe();
        });

        // 连接中事件
        this.socket.on('connecting', () => {
            Logger.info('WebSocketManager', 'WebSocket正在连接...');
            this.updateStatus(false, 'WebSocket连接中...');
        });

        // 重连事件
        this.socket.on('reconnect_attempt', (attemptNumber) => {
            Logger.info('WebSocketManager', `WebSocket尝试重连 (第${attemptNumber}次)`);
            this.updateStatus(false, `WebSocket重连中 (${attemptNumber})`);
        });

        // 断开连接事件
        this.socket.on('disconnect', (reason) => {
            Logger.info('WebSocketManager', 'WebSocket断开, 原因:', reason);
            this.updateStatus(false, 'WebSocket已断开');
        });

        // 连接错误事件
        this.socket.on('connect_error', (error) => {
            Logger.error('WebSocketManager', 'WebSocket连接错误:', error);
            Logger.debug('WebSocketManager', '错误详情:', {
                message: error.message,
                type: error.type,
                description: error.description
            });
            this.updateStatus(false, 'WebSocket连接错误');
        });

        // GPS更新事件
        this.socket.on('gps_update', (data) => {
            Logger.debug('WebSocketManager', '收到GPS更新:', data);
            if (this.gpsUpdateCallback) {
                try {
                    this.gpsUpdateCallback(data);
                } catch (error) {
                    Logger.error('WebSocketManager', 'GPS回调执行错误:', error);
                }
            }
        });

        // NFC任务更新事件
        this.socket.on('nfc_task_update', (data) => {
            Logger.debug('WebSocketManager', '收到NFC任务更新:', data);
            if (this.nfcTaskUpdateCallback) {
                try {
                    this.nfcTaskUpdateCallback(data);
                } catch (error) {
                    Logger.error('WebSocketManager', 'NFC任务回调执行错误:', error);
                }
            }
        });

        // 任务更新事件
        this.socket.on('task_update', (data) => {
            Logger.debug('WebSocketManager', '收到任务更新:', data);
            if (this.taskUpdateCallback) {
                try {
                    this.taskUpdateCallback(data);
                } catch (error) {
                    Logger.error('WebSocketManager', '任务更新回调执行错误:', error);
                }
            }
        });

        // 标签更新事件
        this.socket.on('tags_update', (data) => {
            Logger.debug('WebSocketManager', '收到标签更新:', data);
            if (this.tagsUpdateCallback) {
                try {
                    this.tagsUpdateCallback(data);
                } catch (error) {
                    Logger.error('WebSocketManager', '标签更新回调执行错误:', error);
                }
            }
        });

        Logger.info('WebSocketManager', 'Socket事件监听初始化完成');
    }

    updateStatus(connected, message) {
        Logger.debug('WebSocketManager', `更新连接状态: ${connected}, 消息: ${message}`);
        if (this.statusDot && this.statusText) {
            if (connected) {
                this.statusDot.classList.add('connected');
            } else {
                this.statusDot.classList.remove('connected');
            }
            this.statusText.textContent = message;
        } else {
            Logger.warn('WebSocketManager', '状态显示元素未找到');
        }
    }

    subscribeToTasks(playerId) {
        Logger.info('WebSocketManager', '开始订阅任务更新');
        if (!playerId) {
            Logger.error('WebSocketManager', '订阅任务时playerId不能为空');
            return;
        }
        const room = `user_${playerId}`;
        Logger.info('WebSocketManager', '订阅任务更新:', room);
        
        try {
            this.socket.emit('subscribe_tasks', { 
                player_id: playerId,
                room: room 
            });
            Logger.debug('WebSocketManager', '发送任务订阅请求');
            
            this.socket.emit('join', { room: room });
            Logger.debug('WebSocketManager', '发送加入房间请求');
            
            this.subscriptions.add({ type: 'tasks', playerId, room });
            Logger.debug('WebSocketManager', '添加到订阅列表');
        } catch (error) {
            Logger.error('WebSocketManager', '订阅任务失败:', error);
        }
    }

    // 回调注册方法
    onTaskUpdate(callback) {
        Logger.debug('WebSocketManager', '注册任务更新回调');
        this.taskUpdateCallback = callback;
    }

    onTagsUpdate(callback) {
        Logger.debug('WebSocketManager', '注册标签更新回调');
        this.tagsUpdateCallback = callback;
    }

    onGPSUpdate(callback) {
        Logger.debug('WebSocketManager', '注册GPS更新回调');
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

    // 断开连接方法
    disconnect() {
        Logger.info('WebSocketManager', '开始断开WebSocket连接');
        if (this.socket) {
            try {
                this.socket.disconnect();
                Logger.debug('WebSocketManager', 'Socket断开连接成功');
            } catch (error) {
                Logger.error('WebSocketManager', 'Socket断开连接失败:', error);
            }
        }
        this.subscriptions.clear();
        this.taskUpdateCallback = null;
        this.tagsUpdateCallback = null;
        this.gpsUpdateCallback = null;
        this.nfcTaskUpdateCallback = null;
        Logger.info('WebSocketManager', '清理完成');
    }
}

