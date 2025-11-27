/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 13:47:42
 * @LastEditTime: 2025-11-20 16:52:41
 * @LastEditors: 一根鱼骨棒
 * @Description: SSE(Server-Sent Events)服务管理 - 替代WebSocket的轻量级实时通信方案
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

class SSEService {
    constructor(eventBus) {
        if (!eventBus) {
            throw new Error('EventBus is required for SSEService');
        }
        this.eventBus = eventBus;
        this.eventSource = null;
        this.state = WS_STATE.DISCONNECTED;
        this.reconnectAttempts = 0;
        this.currentSubscribedPlayerId = null;
        this.subscriptions = new Set();
        this.isInitializing = false;
        this.heartbeatInterval = null;
        this.lastHeartbeatTime = 0;
        this.connectionTimeout = null;
        
        // 预先绑定事件处理方法
        this.handleGPSUpdate = this.handleGPSUpdate.bind(this);
        this.handlePlayerUpdate = this.handlePlayerUpdate.bind(this);
        this.handleHeartbeat = this.handleHeartbeat.bind(this);
        
        Logger.info('SSEService', '初始化SSE服务');
    }

    // 创建SSE错误
    createWSError(type, message, details = null) {
        const error = {
            type,
            message,
            details,
            timestamp: Date.now()
        };
        Logger.error('SSEService', `SSE错误: ${message}`, error);
        return error;
    }

    // 处理SSE错误
    handleWSError(error, operation = '') {
        let wsError;
        
        if (error.type && Object.values(WS_ERROR_TYPES).includes(error.type)) {
            // 已经是格式化的WebSocket错误
            wsError = error;
        } else {
            // 根据错误类型创建相应的WebSocket错误
            switch(true) {
                case error.code === 'ECONNREFUSED':
                case error.message?.includes('connection'):
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
                        { originalError: error.message || String(error) }
                    );
            }
        }

        // 触发UI通知
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
            type: 'ERROR',
            message: wsError.message,
            details: wsError.details
        });
    }

    handleGPSUpdate(data) {
        Logger.debug('SSEService', '收到GPS更新:', data);
        this.eventBus.emit(MAP_EVENTS.GPS_UPDATE, data);
    }

    handlePlayerUpdate(data) {
        Logger.debug('SSEService', '收到玩家更新:', data);
        this.eventBus.emit(PLAYER_EVENTS.UPDATE, data);
    }

    handleHeartbeat() {
        // 检查心跳是否正常
        const now = Date.now();
        const timeSinceLastHeartbeat = now - this.lastHeartbeatTime;
        
        // 如果超过45秒没有收到心跳，认为连接异常
        if (this.state === WS_STATE.CONNECTED && timeSinceLastHeartbeat > 45000) {
            Logger.warn('SSEService', '心跳超时，重新连接');
            this.disconnect();
            this.connect();
        }
    }

    async initialize() {
        if (this.isInitializing) {
            Logger.warn('SSEService', 'SSE正在初始化中');
            return;
        }

        if (this.eventSource && this.eventSource.readyState === EventSource.OPEN) {
            Logger.info('SSEService', 'SSE已连接');
            return;
        }

        this.isInitializing = true;
        this.state = WS_STATE.CONNECTING;
        Logger.info('SSEService', '开始初始化SSE');
        
        try {
            // 使用当前页面协议和主机
            const protocol = window.location.protocol;
            const host = window.location.host;
            const serverUrl = `${protocol}//${host}`;
            
            Logger.info('SSEService', `使用SSE URL: ${serverUrl}`);
            
            this.isInitializing = false;
            Logger.info('SSEService', 'SSE初始化完成');
            
        } catch (error) {
            this.isInitializing = false;
            this.handleWSError(error, 'initialize');
            throw error;
        }
    }

    // 连接SSE
    async connect(playerId = null) {
        if (this.eventSource && this.eventSource.readyState === EventSource.OPEN) {
            Logger.info('SSEService', 'SSE已经连接');
            this.eventBus.emit(WS_EVENTS.CONNECTED);
            return;
        }

        try {
            this.state = WS_STATE.CONNECTING;
            this.eventBus.emit(WS_EVENTS.CONNECTING);
            
            Logger.info('SSEService', '开始连接SSE...', {
                attempts: this.reconnectAttempts,
                maxAttempts: WS_CONFIG.RECONNECT.maxAttempts,
                playerId: playerId || this.currentSubscribedPlayerId
            });
            
            // 清除之前的事件源
            this.disconnect();
            
            // 构建SSE URL
            const protocol = window.location.protocol;
            const host = window.location.host;
            const playerIdToUse = playerId || this.currentSubscribedPlayerId;
            
            if (!playerIdToUse) {
                throw new Error('Player ID is required for SSE connection');
            }
            
            const sseUrl = `${protocol}//${host}/api/sse/connect?player_id=${playerIdToUse}`;
            Logger.info('SSEService', `连接SSE URL: ${sseUrl}`);
            
            // 创建事件源
            this.eventSource = new EventSource(sseUrl);
            
            // 设置事件监听器
            this.setupEventHandlers();
            
            // 启动心跳检测
            this.startHeartbeatCheck();
            
            // 设置连接超时
            this.connectionTimeout = setTimeout(() => {
                if (this.state === WS_STATE.CONNECTING) {
                    Logger.error('SSEService', 'SSE连接超时');
                    this.handleWSError(new Error('Connection timeout'), 'connect');
                    this.disconnect();
                    this.handleReconnection();
                }
            }, WS_CONFIG.CONNECTION.timeout);
            
        } catch (error) {
            Logger.error('SSEService', 'SSE连接失败:', error);
            this.handleWSError(error, 'connect');
            this.handleReconnection();
        }
    }

    // 设置事件处理器
    setupEventHandlers() {
        if (!this.eventSource) {
            Logger.error('SSEService', '无法设置事件处理器：EventSource未初始化');
            return;
        }

        // 连接打开事件
        this.eventSource.onopen = (event) => {
            Logger.info('SSEService', 'SSE连接成功', {
                event: event
            });
            this.state = WS_STATE.CONNECTED;
            this.reconnectAttempts = 0;
            this.lastHeartbeatTime = Date.now();
            
            // 清除连接超时计时器
            if (this.connectionTimeout) {
                clearTimeout(this.connectionTimeout);
                this.connectionTimeout = null;
            }
            
            // 触发连接成功事件
            this.eventBus.emit(WS_EVENTS.CONNECTED);
            
            // 重新订阅所有事件
            if (this.currentSubscribedPlayerId) {
                this.resubscribeAll();
            }
        };

        // 连接错误事件
        this.eventSource.onerror = (error) => {
            if (this.state === WS_STATE.CONNECTED) {
                Logger.error('SSEService', 'SSE连接错误:', error);
                this.state = WS_STATE.ERROR;
                this.eventBus.emit(WS_EVENTS.ERROR);
            } else if (this.state === WS_STATE.CONNECTING) {
                // 连接过程中的错误
                Logger.error('SSEService', 'SSE连接过程中发生错误:', error);
            }
            
            // 清除连接超时计时器
            if (this.connectionTimeout) {
                clearTimeout(this.connectionTimeout);
                this.connectionTimeout = null;
            }
            
            // 处理重连
            this.handleReconnection();
        };

        // 消息事件
        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                Logger.debug('SSEService', '收到消息:', data);
                
                // 这里可以处理通用消息
            } catch (error) {
                Logger.error('SSEService', '解析消息失败:', error);
            }
        };

        // GPS更新事件
        this.eventSource.addEventListener('gps_update', (event) => {
            try {
                const data = JSON.parse(event.data);
                Logger.debug('SSEService', '收到GPS更新:', data);
                this.eventBus.emit(MAP_EVENTS.GPS_UPDATE, data);
            } catch (error) {
                Logger.error('SSEService', '解析GPS更新失败:', error);
            }
        });

        // 任务更新事件
        this.eventSource.addEventListener('task_update', (event) => {
            try {
                const data = JSON.parse(event.data);
                Logger.debug('SSEService', '收到任务更新:', data);
                this.eventBus.emit(TASK_EVENTS.UPDATE, data);
            } catch (error) {
                Logger.error('SSEService', '解析任务更新失败:', error);
            }
        });

        // NFC任务更新事件
        this.eventSource.addEventListener('nfc_task_update', (event) => {
            try {
                const data = JSON.parse(event.data);
                Logger.debug('SSEService', '收到NFC任务更新:', data);
                this.eventBus.emit(TASK_EVENTS.NFC_UPDATE, data);
            } catch (error) {
                Logger.error('SSEService', '解析NFC任务更新失败:', error);
            }
        });

        // 心跳事件
        this.eventSource.addEventListener('ping', (event) => {
            try {
                const data = JSON.parse(event.data);
                Logger.debug('SSEService', '收到心跳:', data);
                this.lastHeartbeatTime = Date.now();
            } catch (error) {
                Logger.error('SSEService', '解析心跳失败:', error);
            }
        });

        // 连接确认事件
        this.eventSource.addEventListener('connected', (event) => {
            try {
                const data = JSON.parse(event.data);
                Logger.debug('SSEService', '连接确认:', data);
            } catch (error) {
                Logger.error('SSEService', '解析连接确认失败:', error);
            }
        });

        Logger.info('SSEService', 'SSE事件处理器设置完成');
    }

    // 启动心跳检测
    startHeartbeatCheck() {
        // 清除之前的心跳检测
        this.stopHeartbeatCheck();
        
        // 每30秒检查一次心跳
        this.heartbeatInterval = setInterval(this.handleHeartbeat, 30000);
    }

    // 停止心跳检测
    stopHeartbeatCheck() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    // 处理重连
    handleReconnection() {
        if (this.reconnectAttempts >= WS_CONFIG.RECONNECT.maxAttempts) {
            this.eventBus.emit(WS_EVENTS.ERROR);
            Logger.error('SSEService', '重连次数超过最大限制');
            return;
        }

        this.reconnectAttempts++;
        
        // 发送重连事件
        this.eventBus.emit(WS_EVENTS.RECONNECTING, this.reconnectAttempts);
        
        Logger.info('SSEService', `尝试重连 (${this.reconnectAttempts}/${WS_CONFIG.RECONNECT.maxAttempts})`);

        // 使用指数退避算法计算重连延迟
        const delay = Math.min(
            WS_CONFIG.RECONNECT.baseDelay * Math.pow(2, this.reconnectAttempts - 1),
            WS_CONFIG.RECONNECT.maxDelay
        );

        setTimeout(() => {
            this.connect();
        }, delay);
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

    // 订阅相关方法 - 注意：在SSE中，订阅是通过连接URL参数实现的
    // 这里保持与WebSocket相同的接口，但实现逻辑简化
    subscribeToPlayerEvents(playerId) {
        if (!playerId) return;
        
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
            
            // 在SSE中，我们通过重新连接来改变订阅
            this.connect(playerId);
            
            // 记录订阅信息
            const room = `user_${playerId}`;
            this.subscriptions.add(room);
            this.subscriptions.add(`gps_${room}`);
            
            Logger.info('SSEService', `订阅玩家事件: playerId=${playerId}`);
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
            // 在SSE中，我们通过断开连接来取消订阅
            if (this.currentSubscribedPlayerId === playerId) {
                this.disconnect();
                this.currentSubscribedPlayerId = null;
            }
            
            this.subscriptions.delete(room);
            this.subscriptions.delete(`gps_${room}`);
            
            Logger.info('SSEService', `取消订阅玩家事件: playerId=${playerId}`);
        } catch (error) {
            Logger.error('SSEService', '取消订阅失败:', error);
        }
    }

    // 重新订阅所有
    resubscribeAll() {
        if (this.currentSubscribedPlayerId) {
            Logger.info('SSEService', '重新订阅所有事件');
            // 在SSE中，连接已经包含了订阅信息
            // 这里只需要确保连接是活跃的
            if (!this.isConnected()) {
                this.connect(this.currentSubscribedPlayerId);
            }
        }
    }

    // 断开连接
    disconnect() {
        // 清除事件源
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        // 停止心跳检测
        this.stopHeartbeatCheck();
        
        // 清除连接超时计时器
        if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
            this.connectionTimeout = null;
        }
        
        // 更新状态
        this.state = WS_STATE.DISCONNECTED;
        
        // 触发断开连接事件
        this.eventBus.emit(WS_EVENTS.DISCONNECTED, {
            reason: 'manual_disconnect',
            wasConnected: false
        });
        
        Logger.info('SSEService', 'SSE连接已断开');
    }

    // 检查连接状态
    isConnected() {
        return this.eventSource && this.eventSource.readyState === EventSource.OPEN;
    }

    // 获取连接状态
    getConnectionState() {
        return this.state;
    }
    
    // 提供与WebSocketService兼容的getWSManager方法
    // 为了保持API兼容性，确保mapService等组件能够正常工作
    getWSManager() {
        Logger.info('SSEService', 'getWSManager: 提供兼容接口');
        
        return {
            subscribe: (eventName, callback) => {
                // 在SSE中，我们通过eventBus来处理事件订阅
                if (typeof callback === 'function') {
                    this.eventBus.on(eventName, callback);
                    Logger.debug('SSEService', `通过eventBus订阅事件: ${eventName}`);
                }
            },
            unsubscribe: (eventName, callback) => {
                // 在SSE中，我们通过eventBus来处理事件取消订阅
                if (typeof callback === 'function') {
                    this.eventBus.off(eventName, callback);
                    Logger.debug('SSEService', `通过eventBus取消订阅事件: ${eventName}`);
                }
            },
            state: this.state,
            // 兼容WebSocket的一些常用属性
            readyState: this.eventSource ? this.eventSource.readyState : 0
        };
    }
    
    // 发送消息 - SSE是单向的，所以这里通过HTTP POST发送
    async send(type, data) {
        if (!this.currentSubscribedPlayerId) {
            const error = this.createWSError(
                WS_ERROR_TYPES.SEND_ERROR,
                '未连接到服务器，无法发送消息',
                { type, data }
            );
            this.handleWSError(error, 'send');
            return Promise.reject(error);
        }

        try {
            const protocol = window.location.protocol;
            const host = window.location.host;
            const url = `${protocol}//${host}/api/sse/message`;
            
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_id: this.currentSubscribedPlayerId,
                    type: type,
                    data: data
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            Logger.debug('SSEService', `消息发送成功: ${type}`, result);
            return result;
        } catch (error) {
            const wsError = this.createWSError(
                WS_ERROR_TYPES.SEND_ERROR,
                `发送消息失败: ${type}`,
                { type, data, error: error.message }
            );
            this.handleWSError(wsError, 'send');
            return Promise.reject(wsError);
        }
    }
    
    // 发送GPS数据
    async sendGPSData(data) {
        if (!this.validateGPSData(data)) {
            return Promise.reject(new Error('无效的GPS数据'));
        }
        
        return this.send(WS_EVENT_TYPES.BUSINESS.GPS_UPDATE, data);
    }
    
    // 发送任务更新
    async sendTaskUpdate(data) {
        if (!this.validateTaskData(data)) {
            return Promise.reject(new Error('无效的任务数据'));
        }
        
        return this.send(WS_EVENT_TYPES.BUSINESS.TASK_UPDATE, data);
    }
    
    // 发送NFC任务更新
    async sendNFCTaskUpdate(data) {
        if (!this.validateNFCTaskData(data)) {
            return Promise.reject(new Error('无效的NFC任务数据'));
        }
        
        return this.send(WS_EVENT_TYPES.BUSINESS.NFC_TASK_UPDATE, data);
    }
    
    // 发送测试消息
    async sendTestMessage(data) {
        return this.send('test_message', data);
    }
    
    // 发送玩家更新
    async sendPlayerUpdate(data) {
        return this.send(WS_EVENT_TYPES.BUSINESS.PLAYER_UPDATE, data);
    }
}

export default SSEService;