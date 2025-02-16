/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:30:39
 * @LastEditTime: 2025-02-13 18:44:49
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';

class Store {
    constructor() {
        this.state = {
            player: null,
            currentTasks: [],
            availableTasks: [],
            loading: false
        };
        this.listeners = [];
        Logger.info('Store', '状态管理器初始化');
    }

    setState(newState) {
        Logger.debug('Store', '状态更新:', newState);
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    subscribe(listener) {
        this.listeners.push(listener);
        Logger.debug('Store', '添加状态监听器');
    }

    notify() {
        Logger.debug('Store', '通知状态更新');
        this.listeners.forEach(listener => listener(this.state));
    }
} 

export default Store;