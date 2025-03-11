/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 13:47:42
 * @LastEditTime: 2025-03-11 17:16:55
 * @LastEditors: 一根鱼骨棒
 * @Description: WebSocket服务管理
 */
import Logger from '../../utils/logger.js';
import { SERVER,DOMAIN } from '../../config/config.js';
import { 
    WS_STATE,
    WS_EVENT_TYPES,
    WS_CONFIG,
    WS_ERROR_TYPES
} from "../config/wsConfig.js";
import { 
    TASK_EVENTS,
    PLAYER_EVENTS,
    MAP_EVENTS,
    WS_EVENTS,
    UI_EVENTS 
} from "../config/events.js";

class WebSocketService {
    constructor(eventBus) {
        if (!eventBus) {
            throw new Error('EventBus is required for WebSocketService');
        }
        this.eventBus = eventBus;
        this.socket = null;
        this.state = WS_STATE.DISCONNECTED;
        this.reconnectAttempts = 0;
        this.currentSubscribedPlayerId = null;
        this.subscriptions = new Set();
        this.isInitializing = false;
        
        // 预先绑定事件处理方法
        this.handleGPSUpdate = this.handleGPSUpdate.bind(this);
        this.handlePlayerUpdate = this.handlePlayerUpdate.bind(this);
        
        Logger.info('WebSocketService', '初始化WebSocket服务');
    }

    // 创建WebSocket错误
    createWSError(type, message, details = null) {
        const error = {
            type,
            message,
            details,
            timestamp: Date.now()
        };
        Logger.error('WebSocketService', `WebSocket错误: ${message}`, error);
        return error;
    }

    // 处理WebSocket错误
    handleWSError(error, operation = '') {
        let wsError;
        
        if (error.type && Object.values(WS_ERROR_TYPES).includes(error.type)) {
            // 已经是格式化的WebSocket错误
            wsError = error;
        } else {
            // 根据错误类型创建相应的WebSocket错误
            switch(true) {
                case error.code === 'ECONNREFUSED':
                    wsError = this.createWSError(
                        WS_ERROR_TYPES.CONNECTION_ERROR,
                        '连接服务器失败',
                        { originalError: error.message }
                    );
                    break;
                case error.message?.includes('timeout'):
                    wsError = this.createWSError(
                        WS_ERROR_TYPES.TIMEOUT_ERROR,
                        `操作超时: ${operation}`,
                        { originalError: error.message }
                    );
                    break;
                case error.message?.includes('network'):
                    wsError = this.createWSError(
                        WS_ERROR_TYPES.NETWORK_ERROR,
                        '网络连接异常',
                        { originalError: error.message }
                    );
                    break;
                default:
                    wsError = this.createWSError(
                        WS_ERROR_TYPES.UNKNOWN_ERROR,
                        '发生未知错误',
                        { originalError: error.message }
                    );
            }
        }

        // 触发UI通知
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
            type: 'ERROR',
            message: wsError.message,
            details: wsError.details
        });

        return wsError;
    }

    // 获取WebSocket管理器
    getWSManager() {
        if (!this.socket) {
            Logger.warn('WebSocketService', 'WebSocket尚未初始化');
            return null;
        }

        return {
            socket: this.socket,
            state: this.state,
            // 返回socket实例而不是事件处理函数
            subscribe: (eventName, callback) => {
                if (typeof callback === 'function') {
                    this.socket.on(eventName, callback);
                    this.subscriptions.add({ eventName, callback });
                    Logger.debug('WebSocketService', `订阅事件: ${eventName}`);
                }
            },
            unsubscribe: (eventName, callback) => {
                if (typeof callback === 'function') {
                    this.socket.off(eventName, callback);
                    this.subscriptions.delete({ eventName, callback });
                    Logger.debug('WebSocketService', `取消订阅事件: ${eventName}`);
                }
            }
        };
    }

    handleGPSUpdate(data) {
        Logger.debug('WebSocketService', '收到GPS更新:', data);
        this.eventBus.emit(MAP_EVENTS.GPS_UPDATE, data);
    }

    handlePlayerUpdate(data) {
        Logger.debug('WebSocketService', '收到玩家更新:', data);
        this.eventBus.emit(PLAYER_EVENTS.INFO_UPDATED, data);
    }

    // 初始化WebSocket连接
    async initialize() {
        if (this.isInitializing) {
            Logger.warn('WebSocketService', 'WebSocket正在初始化中');
            return;
        }

        if (this.socket?.connected) {
            Logger.info('WebSocketService', 'WebSocket已连接');
            return;
        }

        this.isInitializing = true;
        this.state = WS_STATE.CONNECTING;
        Logger.info('WebSocketService', '开始初始化WebSocket');
        
        try {
            // 使用当前页面协议
            const protocol = window.location.protocol;
            const wsProtocol = protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            const serverUrl = `${wsProtocol}//${host}`;
            
            Logger.info('WebSocketService', `使用WebSocket URL: ${serverUrl}, 协议: ${wsProtocol}`);
            
            // 修改 socket.io 配置
            const socketConfig = {
                autoConnect: false,
                secure: protocol === 'https:',
                path: '/socket.io',
                transports: ['websocket', 'polling'],
                rejectUnauthorized: false,
                withCredentials: true,
                reconnection: true,
                reconnectionAttempts: WS_CONFIG.RECONNECT.maxAttempts,
                reconnectionDelay: WS_CONFIG.RECONNECT.baseDelay,
                timeout: WS_CONFIG.CONNECTION.timeout,
                forceNew: true,
                upgrade: true,
                rememberUpgrade: true,
                extraHeaders: {
                    'X-Forwarded-Proto': protocol.replace(':', ''),
                    'X-Forwarded-For': window.location.hostname,
                    'X-Real-IP': window.location.hostname
                },
                query: {
                    protocol: protocol.replace(':', ''),
                    EIO: '4',
                    transport: 'websocket'
                }
            };

            Logger.info('WebSocketService', '使用Socket.IO配置:', socketConfig);
            this.socket = io(serverUrl, socketConfig);

            // 添加更详细的连接事件监听
            this.socket.on('connect', () => {
                Logger.info('WebSocketService', '连接成功', {
                    id: this.socket.id,
                    transport: this.socket.io.engine.transport.name,
                    protocol: this.socket.io.engine.protocol,
                    hostname: window.location.hostname
                });
            });

            this.socket.on('connect_error', (error) => {
                Logger.error('WebSocketService', '连接错误:', {
                    error: error.message,
                    transport: this.socket.io.engine.transport.name,
                    protocol: protocol,
                    url: serverUrl,
                    stack: error.stack
                });
            });

            this.socket.on('disconnect', (reason) => {
                Logger.warn('WebSocketService', `连接断开: ${reason}`, {
                    wasConnected: this.socket.connected,
                    reconnecting: this.socket.io.reconnecting,
                    attempts: this.reconnectAttempts
                });
            });

            // 添加传输升级日志
            this.socket.on('upgrade', (transport) => {
                Logger.info('WebSocketService', `传输升级到: ${transport}`, {
                    previousTransport: this.socket.io.engine.transport.name
                });
            });

            // 添加ping/pong监控
            this.socket.on('ping', () => {
                Logger.debug('WebSocketService', 'Ping发送');
            });

            this.socket.on('pong', (latency) => {
                Logger.debug('WebSocketService', `Pong接收, 延迟: ${latency}ms`);
            });
            
            // 连接WebSocket
            await this.connect();
            
            this.isInitializing = false;
            Logger.info('WebSocketService', 'WebSocket初始化完成');
            
        } catch (error) {
            this.isInitializing = false;
            this.handleWSError(error, 'initialize');
            throw error;
        }
    }

    // 添加连接方法
    async connect() {
        if (!this.socket) {
            Logger.error('WebSocketService', '无法连接：WebSocket未初始化');
            return;
        }

        if (this.socket.connected) {
            Logger.info('WebSocketService', 'WebSocket已经连接');
            this.eventBus.emit(WS_EVENTS.CONNECTED);
            return;
        }

        try {
            this.state = WS_STATE.CONNECTING;
            this.eventBus.emit(WS_EVENTS.CONNECTING);
            
            Logger.info('WebSocketService', '开始连接WebSocket...', {
                attempts: this.reconnectAttempts,
                maxAttempts: WS_CONFIG.RECONNECT.maxAttempts
            });
            
            // 连接
            this.socket.connect();
            
            // 等待连接完成
            await this.waitForConnection();
            
            Logger.info('WebSocketService', 'WebSocket连接成功', {
                socketId: this.socket.id,
                transport: this.socket.io.engine.transport.name
            });
        } catch (error) {
            this.state = WS_STATE.ERROR;
            this.handleWSError(error, 'connect');
            this.eventBus.emit(WS_EVENTS.ERROR);
            throw error;
        }
    }

    // 等待连接完成
    waitForConnection() {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                Logger.error('WebSocketService', `连接超时 (${WS_CONFIG.CONNECTION.timeout}ms)`);
                reject(new Error('WebSocket连接超时'));
            }, WS_CONFIG.CONNECTION.timeout);

            this.socket.once(WS_EVENT_TYPES.SYSTEM.CONNECT, () => {
                clearTimeout(timeout);
                this.state = WS_STATE.CONNECTED;
                this.reconnectAttempts = 0;
                Logger.info('WebSocketService', 'WebSocket连接成功', {
                    id: this.socket.id,
                    transport: this.socket.io.engine.transport.name
                });
                this.eventBus.emit(WS_EVENTS.CONNECTED);
                resolve();
            });

            this.socket.once(WS_EVENT_TYPES.SYSTEM.CONNECT_ERROR, (error) => {
                clearTimeout(timeout);
                Logger.error('WebSocketService', '连接错误:', {
                    error: error.message,
                    transport: this.socket?.io?.engine?.transport?.name,
                    attempts: this.reconnectAttempts
                });
                reject(error);
            });
        });
    }

    // 设置事件处理器
    setupEventHandlers() {
        if (!this.socket) {
            Logger.error('WebSocketService', '无法设置事件处理器：socket未初始化');
            return;
        }

        // 事件监听器已迁移到EventManager.js
        // GPS更新事件
        // this.socket.on(WS_EVENT_TYPES.BUSINESS.GPS_UPDATE, (data) => {
        //     Logger.debug('WebSocketService', '收到GPS更新:', data);
        //     if (data && typeof data === 'object') {
        //         this.eventBus.emit(MAP_EVENTS.GPS_UPDATE, data);
        //     } else {
        //         Logger.warn('WebSocketService', '收到无效的GPS数据:', data);
        //     }
        // });

        // 系统事件监听
        this.socket.on(WS_EVENT_TYPES.SYSTEM.CONNECT, () => {
            this.state = WS_STATE.CONNECTED;
            this.reconnectAttempts = 0;
            Logger.info('WebSocketService', 'WebSocket连接成功');
            this.eventBus.emit(WS_EVENTS.CONNECTED);
        });

        this.socket.on(WS_EVENT_TYPES.SYSTEM.DISCONNECT, () => {
            this.state = WS_STATE.DISCONNECTED;
            Logger.warn('WebSocketService', 'WebSocket连接断开');
            this.eventBus.emit(WS_EVENTS.DISCONNECTED);
        });

        this.socket.on(WS_EVENT_TYPES.SYSTEM.CONNECT_ERROR, (error) => {
            this.state = WS_STATE.ERROR;
            this.handleWSError(error, 'connect');
            this.handleReconnect();
        });

        this.socket.on(WS_EVENT_TYPES.SYSTEM.ERROR, (error) => {
            this.state = WS_STATE.ERROR;
            this.eventBus.emit(WS_EVENTS.ERROR);
        });

        Logger.info('WebSocketService', 'WebSocket事件处理器设置完成');
    }

    // 处理重连
    handleReconnect() {
        if (this.reconnectAttempts >= WS_CONFIG.RECONNECT.maxAttempts) {
            this.eventBus.emit(WS_EVENTS.ERROR);
            Logger.error('WebSocketService', '重连次数超过最大限制');
            return;
        }

        this.reconnectAttempts++;
        
        // 发送重连事件时传递数字
        this.eventBus.emit(WS_EVENTS.RECONNECTING, this.reconnectAttempts);
        
        Logger.info('WebSocketService', `尝试重连 (${this.reconnectAttempts}/${WS_CONFIG.RECONNECT.maxAttempts})`);

        setTimeout(() => {
            this.connect();
        }, WS_CONFIG.RECONNECT.delay);
    }

    // 数据验证方法
    validateGPSData(data) {
        if (!data?.latitude || !data?.longitude) {
            this.handleWSError(
                this.createWSError(
                    WS_ERROR_TYPES.INVALID_DATA,
                    '无效的GPS数据',
                    { data }
                )
            );
            return false;
        }
        return true;
    }

    validateTaskData(data) {
        if (!data?.id || !data?.status) {
            this.handleWSError(
                this.createWSError(
                    WS_ERROR_TYPES.INVALID_DATA,
                    '无效的任务数据',
                    { data }
                )
            );
            return false;
        }
        return true;
    }

    validateNFCTaskData(data) {
        if (!data?.type || !data?.taskId) {
            this.handleWSError(
                this.createWSError(
                    WS_ERROR_TYPES.INVALID_DATA,
                    '无效的NFC任务数据',
                    { data }
                )
            );
            return false;
        }
        return true;
    }

    // 订阅相关方法
    subscribeToPlayerEvents(playerId) {
        if (!playerId) return;
        
        const room = `user_${playerId}`;
        
        // 如果已订阅相同玩家，跳过
        if (this.currentSubscribedPlayerId === playerId) {
            return;
        }

        // 取消之前的订阅
        if (this.currentSubscribedPlayerId) {
            this.unsubscribeFromPlayerEvents(this.currentSubscribedPlayerId);
        }

        try {
            this.currentSubscribedPlayerId = playerId;
            
            // 订阅任务和GPS
            this.socket.emit(WS_EVENT_TYPES.ROOM.SUBSCRIBE_TASKS, { player_id: playerId, room });
            this.socket.emit(WS_EVENT_TYPES.ROOM.SUBSCRIBE_GPS, { player_id: playerId, room });
            this.socket.emit(WS_EVENT_TYPES.ROOM.JOIN, { room });
            
            this.subscriptions.add(room);
            this.subscriptions.add(`gps_${room}`);
        } catch (error) {
            this.handleWSError(
                this.createWSError(
                    WS_ERROR_TYPES.SUBSCRIPTION_ERROR,
                    '订阅玩家事件失败',
                    { playerId, error: error.message }
                )
            );
        }
    }

    unsubscribeFromPlayerEvents(playerId) {
        if (!playerId) return;

        const room = `user_${playerId}`;
        
        try {
            this.socket.emit(WS_EVENT_TYPES.ROOM.UNSUBSCRIBE_TASKS, { player_id: playerId, room });
            this.socket.emit(WS_EVENT_TYPES.ROOM.UNSUBSCRIBE_GPS, { player_id: playerId, room });
            this.socket.emit(WS_EVENT_TYPES.ROOM.LEAVE, { room });
            
            this.subscriptions.delete(room);
            this.subscriptions.delete(`gps_${room}`);
            
            if (this.currentSubscribedPlayerId === playerId) {
                this.currentSubscribedPlayerId = null;
            }
        } catch (error) {
            Logger.error('WebSocketService', '取消订阅失败:', error);
        }
    }

    // 重新订阅所有房间
    resubscribeAll() {
        for (const subscription of this.subscriptions) {
            const isGPS = subscription.startsWith('gps_user_');
            const playerId = isGPS 
                ? subscription.replace('gps_user_', '')
                : subscription.replace('user_', '');
            
            if (isGPS) {
                this.socket.emit(WS_EVENT_TYPES.ROOM.SUBSCRIBE_GPS, {
                    player_id: playerId,
                    room: `user_${playerId}`
                });
            } else {
                this.socket.emit(WS_EVENT_TYPES.ROOM.SUBSCRIBE_TASKS, {
                    player_id: playerId,
                    room: subscription
                });
                this.socket.emit(WS_EVENT_TYPES.ROOM.JOIN, { room: subscription });
            }
        }
    }

    // 断开连接
    disconnect() {
        if (this.socket) {
            this.socket.disconnect();
            this.socket = null;
            this.state = WS_STATE.DISCONNECTED;
            this.subscriptions.clear();
            this.currentSubscribedPlayerId = null;
            this.eventBus.emit(WS_EVENTS.DISCONNECTED);
        }
    }

    // 获取连接状态
    isConnected() {
        return this.state === WS_STATE.CONNECTED;
    }
}

export default WebSocketService; 