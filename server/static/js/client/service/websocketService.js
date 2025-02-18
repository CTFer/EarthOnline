/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 13:47:42
 * @LastEditTime: 2025-02-18 10:41:53
 * @LastEditors: 一根鱼骨棒
 * @Description: WebSocket服务管理
 */
import Logger from '../../utils/logger.js';
import WebSocketManager from '../../function/WebSocketManager.js';
import { 
    TASK_EVENTS,
    PLAYER_EVENTS,
    MAP_EVENTS,
    WS_EVENTS,
    UI_EVENTS 
} from "../config/events.js";

class WebSocketService {
    constructor(eventBus, api) {
        this.eventBus = eventBus;
        this.api = api;
        this.wsManager = null;
        this.connected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // 初始重连延迟1秒
        this.connectionTimeout = null;
        this.currentSubscribedPlayerId = null;
        this.isInitializing = false; // 添加初始化状态标志
        this.hasShownError = false;  // 添加错误显示标志
        
        Logger.info('WebSocketService', '初始化WebSocket服务');
    }

    // 初始化WebSocket连接
    async initialize() {
        // 防止重复初始化
        if (this.isInitializing) {
            Logger.warn('WebSocketService', '初始化正在进行中，跳过重复初始化');
            return;
        }
        
        // 如果已经连接，不需要重新初始化
        if (this.connected && this.wsManager?.socket?.connected) {
            Logger.info('WebSocketService', 'WebSocket已连接，无需重新初始化');
            return;
        }

        this.isInitializing = true;
        Logger.info('WebSocketService', '开始初始化WebSocket管理器');
        
        try {
            // 清理之前的连接
            await this.disconnect();

            // 创建新的WebSocket管理器
            this.wsManager = new WebSocketManager();
            
            // 设置连接超时
            this.setConnectionTimeout();
            
            // 设置事件处理器
            this.setupEventHandlers();
            
            // 等待连接完成
            await new Promise((resolve, reject) => {
                const timeoutId = setTimeout(() => {
                    reject(new Error('WebSocket连接超时'));
                }, 5000);

                this.wsManager.onConnect(() => {
                    clearTimeout(timeoutId);
                    this.connected = true;
                    this.reconnectAttempts = 0;
                    this.hasShownError = false; // 重置错误显示标志
                    resolve();
                });

                this.wsManager.onError((error) => {
                    clearTimeout(timeoutId);
                    reject(error);
                });
            });

            Logger.info('WebSocketService', 'WebSocket初始化成功');
        } catch (error) {
            Logger.error('WebSocketService', 'WebSocket初始化失败:', error);
            throw error;
        } finally {
            this.isInitializing = false;
        }
    }

    // 设置连接超时
    setConnectionTimeout() {
        // 清除之前的超时
        if (this.connectionTimeout) {
            clearTimeout(this.connectionTimeout);
        }

        // 设置新的超时（5秒）
        this.connectionTimeout = setTimeout(() => {
            if (!this.connected) {
                const error = new Error('WebSocket连接超时');
                Logger.warn('WebSocketService', '连接超时详情:', {
                    attempts: this.reconnectAttempts,
                    maxAttempts: this.maxReconnectAttempts,
                    delay: this.reconnectDelay,
                    wsState: this.wsManager?.socket?.connected
                });
                this.handleReconnect();
            }
        }, 5000); // 增加超时时间到5秒
    }

    // 设置事件处理器
    setupEventHandlers() {
        if (!this.wsManager) {
            Logger.error('WebSocketService', 'WebSocket管理器未初始化');
            return;
        }

        // 使用WebSocketManager提供的事件接口
        this.wsManager.onConnect(() => {
            Logger.info('WebSocketService', 'WebSocket连接成功');
            this.connected = true;
            this.reconnectAttempts = 0;
            this.reconnectDelay = 1000;
            
            // 清除连接超时
            if (this.connectionTimeout) {
                clearTimeout(this.connectionTimeout);
            }
            
            this.eventBus.emit(WS_EVENTS.CONNECTED);
        });

        this.wsManager.onDisconnect(() => {
            Logger.warn('WebSocketService', 'WebSocket连接断开');
            this.connected = false;
            this.eventBus.emit(WS_EVENTS.DISCONNECTED);
            this.handleReconnect();
        });

        this.wsManager.onError((error) => {
            Logger.error('WebSocketService', 'WebSocket错误:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: 'WebSocket连接出错'
            });
        });

        // 设置GPS更新处理
        this.wsManager.onGPSUpdate((data) => {
            Logger.debug('WebSocketService', 'GPS更新:', data);
            if (this.validateGPSData(data)) {
                this.eventBus.emit(MAP_EVENTS.GPS_UPDATED, data);
            }
        });
        
        // 设置任务更新处理
        this.wsManager.onTaskUpdate((data) => {
            Logger.debug('WebSocketService', '任务更新:', data);
            if (this.validateTaskData(data)) {
                this.eventBus.emit(TASK_EVENTS.STATUS_UPDATED, {
                    ...data,
                    timestamp: Date.now()
                });
            }
        });
        
        // 设置NFC任务更新处理
        this.wsManager.onNFCTaskUpdate((data) => {
            Logger.debug('WebSocketService', 'NFC任务更新:', data);
            if (this.validateNFCTaskData(data)) {
                this.eventBus.emit(TASK_EVENTS.STATUS_UPDATED, {
                    ...data,
                    source: 'NFC',
                    timestamp: Date.now()
                });
            }
        });
    }

    // 处理重连逻辑
    handleReconnect() {
        // 如果正在初始化或已经连接，跳过重连
        if (this.isInitializing || this.connected) {
            Logger.debug('WebSocketService', '跳过重连: 正在初始化或已连接');
            return;
        }

        // 检查是否达到最大重试次数
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            if (!this.hasShownError) { // 只在第一次显示错误
                const error = new Error(`WebSocket重连失败(${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                Logger.error('WebSocketService', '重连失败详情:', {
                    attempts: this.reconnectAttempts,
                    maxAttempts: this.maxReconnectAttempts,
                    lastDelay: this.reconnectDelay,
                    wsState: this.wsManager?.socket?.connected,
                    serverUrl: this.wsManager?.socket?.io?.uri
                });
                
                this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                    type: 'ERROR',
                    message: 'WebSocket连接失败,请检查网络后刷新页面',
                    details: error.message
                });
                
                this.hasShownError = true; // 标记已显示错误
            }
            return;
        }

        // 使用指数退避策略
        const baseDelay = 2000;
        const maxDelay = 30000;
        const delay = Math.min(baseDelay * Math.pow(2, this.reconnectAttempts), maxDelay);
        
        Logger.info('WebSocketService', `准备重连(${this.reconnectAttempts + 1}/${this.maxReconnectAttempts}), 延迟: ${delay}ms`);
        
        // 清理之前的重连定时器
        if (this._reconnectTimer) {
            clearTimeout(this._reconnectTimer);
        }
        
        this._reconnectTimer = setTimeout(async () => {
            if (!this.connected) {
                this.reconnectAttempts++;
                try {
                    await this.initialize();
                    
                    // 重连成功后恢复之前的订阅
                    if (this.currentSubscribedPlayerId) {
                        await this.subscribeToPlayerEvents(this.currentSubscribedPlayerId);
                    }
                } catch (error) {
                    Logger.error('WebSocketService', '重连尝试失败:', {
                        attempt: this.reconnectAttempts,
                        error: error.message,
                        stack: error.stack,
                        nextDelay: delay * 2
                    });
                    
                    // 如果还没到最大重试次数,继续重连
                    if (this.reconnectAttempts < this.maxReconnectAttempts) {
                        this.handleReconnect();
                    }
                }
            }
        }, delay);
    }

    // 验证GPS数据
    validateGPSData(data) {
        if (!data || typeof data !== 'object') {
            Logger.error('WebSocketService', '无效的GPS数据格式');
            return false;
        }

        const { latitude, longitude, accuracy } = data;
        if (typeof latitude !== 'number' || typeof longitude !== 'number') {
            Logger.error('WebSocketService', 'GPS坐标无效');
            return false;
        }

        return true;
    }

    // 验证任务数据
    validateTaskData(data) {
        if (!data || typeof data !== 'object') {
            Logger.error('WebSocketService', '无效的任务数据格式');
            return false;
        }

        if (!data.id || !data.status) {
            Logger.error('WebSocketService', '任务数据缺少必要字段');
            return false;
        }

        return true;
    }

    // 验证NFC任务数据
    validateNFCTaskData(data) {
        if (!data || typeof data !== 'object') {
            Logger.error('WebSocketService', '无效的NFC任务数据格式');
            return false;
        }

        if (!data.type || !data.taskId) {
            Logger.error('WebSocketService', 'NFC任务数据缺少必要字段');
            return false;
        }

        return true;
    }

    // 订阅玩家相关的WebSocket事件
    subscribeToPlayerEvents(playerId) {
        if (!this.wsManager || !playerId) {
            Logger.error('WebSocketService', '无法订阅玩家事件: WebSocket未初始化或玩家ID无效');
            return;
        }

        // 如果已经订阅了相同的玩家ID，则跳过
        if (this.currentSubscribedPlayerId === playerId) {
            Logger.debug('WebSocketService', `已经订阅了玩家(${playerId})的事件，跳过重复订阅`);
            return;
        }

        Logger.info('WebSocketService', `订阅玩家(${playerId})的WebSocket事件`);
        
        try {
            // 如果之前订阅了其他玩家，先取消订阅
            if (this.currentSubscribedPlayerId) {
                this.unsubscribeFromPlayerEvents(this.currentSubscribedPlayerId);
            }

            // 更新当前订阅的玩家ID
            this.currentSubscribedPlayerId = playerId;
            
            // 执行新的订阅
            this.wsManager.subscribeToTasks(playerId);
            this.wsManager.subscribeToGPS(playerId);
        } catch (error) {
            Logger.error('WebSocketService', '订阅玩家事件失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '订阅玩家事件失败'
            });
        }
    }

    // 取消玩家事件订阅
    unsubscribeFromPlayerEvents(playerId) {
        if (!this.wsManager || !playerId) return;

        Logger.info('WebSocketService', `取消订阅玩家(${playerId})的WebSocket事件`);
        
        try {
            const room = `user_${playerId}`;
            this.wsManager.socket.emit('unsubscribe_tasks', { player_id: playerId, room });
            this.wsManager.socket.emit('unsubscribe_gps', { player_id: playerId, room });
            this.wsManager.socket.emit('leave', { room });
            
            // 清除当前订阅的玩家ID
            if (this.currentSubscribedPlayerId === playerId) {
                this.currentSubscribedPlayerId = null;
            }
        } catch (error) {
            Logger.error('WebSocketService', '取消订阅玩家事件失败:', error);
        }
    }

    // 断开连接
    async disconnect() {
        if (this.wsManager) {
            // 清理超时定时器
            if (this.connectionTimeout) {
                clearTimeout(this.connectionTimeout);
                this.connectionTimeout = null;
            }
            
            // 断开WebSocket连接
            if (this.wsManager.socket) {
                this.wsManager.socket.disconnect();
            }
            
            this.wsManager = null;
            this.connected = false;
            this.eventBus.emit(WS_EVENTS.DISCONNECTED);
        }
    }

    // 获取WebSocket管理器实例
    getWSManager() {
        return this.wsManager;
    }

    // 获取连接状态
    isConnected() {
        return this.connected;
    }
}

export default WebSocketService; 