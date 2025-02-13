/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:29:54
 * @LastEditTime: 2025-02-12 22:53:16
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';

// 事件总线
class EventBus {
    constructor() {
        this.events = {};
        Logger.info('EventBus', '事件总线初始化');
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
        Logger.debug('EventBus', `注册事件处理器: ${event}`);
    }

    off(event, callback) {
        if (this.events[event]) {
            this.events[event] = this.events[event].filter(cb => cb !== callback);
            Logger.debug('EventBus', `移除事件处理器: ${event}`);
        }
    }

    emit(event, data) {
        Logger.debug('EventBus', `触发事件: ${event}`, data);
        if (this.events[event]) {
            this.events[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    Logger.error('EventBus', `事件处理器错误 ${event}:`, error);
                }
            });
        }
    }

    // 清理所有事件监听
    clear() {
        this.events = {};
        Logger.info('EventBus', '清理所有事件处理器');
    }

    // 获取特定事件的监听器数量
    getListenerCount(event) {
        return this.events[event] ? this.events[event].length : 0;
    }
}

export default EventBus; 