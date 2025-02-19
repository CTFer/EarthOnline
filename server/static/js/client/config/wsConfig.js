/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-19 13:00:00
 * @LastEditors: 一根鱼骨棒
 * @Description: WebSocket配置常量
 */

// WebSocket错误类型枚举
export const WS_ERROR_TYPES = {
    CONNECTION_ERROR: 'CONNECTION_ERROR',       // 连接错误
    TIMEOUT_ERROR: 'TIMEOUT_ERROR',            // 超时错误
    AUTHENTICATION_ERROR: 'AUTHENTICATION_ERROR',// 认证错误
    SUBSCRIPTION_ERROR: 'SUBSCRIPTION_ERROR',   // 订阅错误
    NETWORK_ERROR: 'NETWORK_ERROR',            // 网络错误
    PROTOCOL_ERROR: 'PROTOCOL_ERROR',          // 协议错误
    INVALID_DATA: 'INVALID_DATA',              // 无效数据
    UNKNOWN_ERROR: 'UNKNOWN_ERROR'             // 未知错误
};

// WebSocket连接状态枚举
export const WS_STATE = {
    CONNECTING: 'CONNECTING',    // 正在连接
    CONNECTED: 'CONNECTED',      // 已连接
    DISCONNECTED: 'DISCONNECTED',// 已断开
    RECONNECTING: 'RECONNECTING',// 重连中
    ERROR: 'ERROR'              // 错误状态
};

// WebSocket事件类型
export const WS_EVENT_TYPES = {
    // 系统事件
    SYSTEM: {
        CONNECT: 'connect',
        DISCONNECT: 'disconnect',
        CONNECT_ERROR: 'connect_error',
        RECONNECT_ATTEMPT: 'reconnect_attempt',
        RECONNECT: 'reconnect',
        RECONNECT_ERROR: 'reconnect_error',
        RECONNECT_FAILED: 'reconnect_failed',
        ERROR: 'error'
    },
    // 业务事件
    BUSINESS: {
        GPS_UPDATE: 'gps_update',
        TASK_UPDATE: 'task_update',
        NFC_TASK_UPDATE: 'nfc_task_update',
        PLAYER_UPDATE: 'player_update'
    },
    // 房间事件
    ROOM: {
        JOIN: 'join',
        LEAVE: 'leave',
        SUBSCRIBE_TASKS: 'subscribe_tasks',
        UNSUBSCRIBE_TASKS: 'unsubscribe_tasks',
        SUBSCRIBE_GPS: 'subscribe_gps',
        UNSUBSCRIBE_GPS: 'unsubscribe_gps'
    }
};

// WebSocket配置
export const WS_CONFIG = {
    // 连接配置
    CONNECTION: {
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        timeout: 3000,
        autoConnect: false,
        transports: ['websocket'],
        upgrade: false,
        forceNew: true,
        closeOnBeforeunload: true
    },
    // 重连配置
    RECONNECT: {
        maxAttempts: 5,
        baseDelay: 2000,
        maxDelay: 30000
    },
    // 心跳配置
    HEARTBEAT: {
        enabled: true,
        interval: 30000,  // 30秒
        timeout: 5000     // 5秒超时
    }
}; 