/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 13:47:42
 * @LastEditTime: 2025-02-19 14:34:33
 * @LastEditors: 一根鱼骨棒
 * @Description: WebSocket服务管理
 */
import Logger from '../../utils/logger.js';
import { SERVER } from '../../config/config.js';
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
            // 不立即触发连接事件，等待其他服务初始化完成
            return;
        }

        this.isInitializing = true;
        this.state = WS_STATE.CONNECTING;
        Logger.info('WebSocketService', '开始初始化WebSocket');
        
        try {
            // 创建socket连接，但不自动连接
            this.socket = io(SERVER, {
                ...WS_CONFIG.CONNECTION,
                autoConnect: false
            });
            
            // 设置事件处理器
            this.setupEventHandlers();
            
            Logger.info('WebSocketService', 'WebSocket初始化配置完成，等待连接');
            this.isInitializing = false;
        } catch (error) {
            this.isInitializing = false;
            this.state = WS_STATE.ERROR;
            this.handleWSError(error, 'initialize');
            throw error;
        }
    }

    // 开始连接
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
            
            // 连接
            this.socket.connect();
            
            // 等待连接完成
            await this.waitForConnection();
            
            Logger.info('WebSocketService', 'WebSocket连接成功');
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
                reject(new Error('WebSocket连接超时'));
            }, WS_CONFIG.CONNECTION.timeout);

            this.socket.once(WS_EVENT_TYPES.SYSTEM.CONNECT, () => {
                clearTimeout(timeout);
                this.state = WS_STATE.CONNECTED;
                this.eventBus.emit(WS_EVENTS.CONNECTED);
                resolve();
            });

            this.socket.once(WS_EVENT_TYPES.SYSTEM.CONNECT_ERROR, (error) => {
                clearTimeout(timeout);
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

        // GPS更新事件
        this.socket.on(WS_EVENT_TYPES.BUSINESS.GPS_UPDATE, (data) => {
            Logger.debug('WebSocketService', '收到GPS更新:', data);
            if (data && typeof data === 'object') {
                this.eventBus.emit(MAP_EVENTS.GPS_UPDATE, data);
            } else {
                Logger.warn('WebSocketService', '收到无效的GPS数据:', data);
            }
        });

        // 玩家更新事件
        this.socket.on(WS_EVENT_TYPES.BUSINESS.PLAYER_UPDATE, (data) => {
            Logger.debug('WebSocketService', '收到玩家更新:', data);
            if (data && typeof data === 'object') {
                this.eventBus.emit(PLAYER_EVENTS.INFO_UPDATED, data);
            } else {
                Logger.warn('WebSocketService', '收到无效的玩家数据:', data);
            }
        });

        // 连接事件
        this.socket.on(WS_EVENT_TYPES.SYSTEM.CONNECT, () => {
            Logger.info('WebSocketService', 'WebSocket连接成功');
            this.state = WS_STATE.CONNECTED;
            this.reconnectAttempts = 0;
            this.eventBus.emit(WS_EVENTS.CONNECTED);
        });

        // 断开连接事件
        this.socket.on(WS_EVENT_TYPES.SYSTEM.DISCONNECT, (reason) => {
            Logger.warn('WebSocketService', 'WebSocket断开连接:', reason);
            this.state = WS_STATE.DISCONNECTED;
            this.eventBus.emit(WS_EVENTS.DISCONNECTED);
            this.handleReconnect();
        });

        // 错误事件
        this.socket.on(WS_EVENT_TYPES.SYSTEM.ERROR, (error) => {
            Logger.error('WebSocketService', 'WebSocket错误:', error);
            this.handleWSError(error, 'socket');
        });
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