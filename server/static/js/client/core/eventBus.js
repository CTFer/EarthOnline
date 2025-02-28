/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:29:54
 * @LastEditTime: 2025-02-28 16:49:28
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
        this.eventTrace = {}; // 用于记录事件的传播路径
        Logger.info('EventBus', '事件总线初始化');
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
            this.eventTrace[event] = []; // 初始化事件的传播路径记录
        }
        // 检查回调是否已经注册
        if (!this.events[event].includes(callback)) {
            this.events[event].push(callback);
            Logger.debug('EventBus', `注册事件处理器: ${event}`);
        } else {
            Logger.debug('EventBus', `事件处理器已存在: ${event}`);
        }
    }

    off(event, callback) {
        if (this.events[event]) {
            this.events[event] = this.events[event].filter(cb => cb !== callback);
            Logger.debug('EventBus', `移除事件处理器: ${event}`);
        }
    }

    emit(event, data) {
        // 获取调用栈信息
        const stack = new Error().stack;
        const caller = stack.split('\n')[2].trim();
        
        Logger.debug('EventBus', `触发事件: ${event}, 来源: ${caller}`, {
            event,
            data,
            caller
        });
        
        if (this.events[event]) {
            this.eventTrace[event] = []; // 重置事件的传播路径记录
            this.events[event].forEach((callback, index) => {
                try {
                    this.eventTrace[event].push(`Callback ${index}: ${callback.name || '匿名函数'}`); // 记录回调函数的调用
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