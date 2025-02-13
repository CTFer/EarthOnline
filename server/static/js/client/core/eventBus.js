/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:29:54
 * @LastEditTime: 2025-02-12 22:53:16
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
// 事件总线
class EventBus {
    constructor() {
        this.events = {};
        console.log('[EventBus] Event bus initialized');
    }

    on(event, callback) {
        if (!this.events[event]) {
            this.events[event] = [];
        }
        this.events[event].push(callback);
        console.log(`[EventBus] Registered handler for event: ${event}`);
    }

    off(event, callback) {
        if (this.events[event]) {
            this.events[event] = this.events[event].filter(cb => cb !== callback);
            console.log(`[EventBus] Removed handler for event: ${event}`);
        }
    }

    emit(event, data) {
        console.log(`[EventBus] Emitting event: ${event}`, data);
        if (this.events[event]) {
            this.events[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[EventBus] Error in event handler for ${event}:`, error);
                }
            });
        }
    }

    // 清理所有事件监听
    clear() {
        this.events = {};
        console.log('[EventBus] Cleared all event handlers');
    }

    // 获取特定事件的监听器数量
    getListenerCount(event) {
        return this.events[event] ? this.events[event].length : 0;
    }
}

export default EventBus; 