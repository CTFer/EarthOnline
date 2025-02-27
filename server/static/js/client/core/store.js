/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:30:39
 * @LastEditTime: 2025-02-27 21:51:20
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';

class Store {
    constructor() {
        // 全局状态
        this.state = {
            player: null,
            currentTasks: [],
            availableTasks: [],
            loading: false,
            // 添加路由相关状态
            currentRoute: '/',
            // 添加页面状态管理
            pageStates: new Map(),
            // 添加组件状态管理
            componentStates: new Map()
        };
        
        // 状态变更监听器
        this.listeners = new Map();
        // 组件状态监听器
        this.componentListeners = new Map();
        
        Logger.info('Store', '状态管理器初始化');
    }

    // 设置全局状态
    setState(newState) {
        Logger.debug('Store', '全局状态更新:', newState);
        const oldState = { ...this.state };
        this.state = { ...this.state, ...newState };
        
        // 触发相关监听器
        this.notifyListeners('global', oldState, this.state);
    }

    // 获取全局状态
    getState() {
        return { ...this.state };
    }

    // 设置页面状态
    setPageState(pageName, state) {
        Logger.debug('Store', `页面[${pageName}]状态更新:`, state);
        const oldState = this.getPageState(pageName);
        this.state.pageStates.set(pageName, { ...oldState, ...state });
        
        // 触发页面状态变更监听器
        this.notifyListeners(`page:${pageName}`, oldState, this.getPageState(pageName));
    }

    // 获取页面状态
    getPageState(pageName) {
        return { ...this.state.pageStates.get(pageName) || {} };
    }

    // 设置组件状态
    setComponentState(componentId, state) {
        Logger.debug('Store', `组件[${componentId}]状态更新:`, state);
        const oldState = this.getComponentState(componentId);
        this.state.componentStates.set(componentId, { ...oldState, ...state });
        
        // 触发组件状态变更监听器
        this.notifyListeners(`component:${componentId}`, oldState, this.getComponentState(componentId));
    }

    // 获取组件状态
    getComponentState(componentId) {
        return { ...this.state.componentStates.get(componentId) || {} };
    }

    // 订阅状态变更
    subscribe(type, id, listener) {
        const key = `${type}:${id}`;
        if (!this.listeners.has(key)) {
            this.listeners.set(key, new Set());
        }
        this.listeners.get(key).add(listener);
        Logger.debug('Store', `添加[${key}]状态监听器`);
        
        // 返回取消订阅函数
        return () => this.unsubscribe(type, id, listener);
    }

    // 取消订阅
    unsubscribe(type, id, listener) {
        const key = `${type}:${id}`;
        const listeners = this.listeners.get(key);
        if (listeners) {
            listeners.delete(listener);
            if (listeners.size === 0) {
                this.listeners.delete(key);
            }
        }
        Logger.debug('Store', `移除[${key}]状态监听器`);
    }

    // 通知监听器
    notifyListeners(key, oldState, newState) {
        const listeners = this.listeners.get(key);
        if (listeners) {
            listeners.forEach(listener => {
                try {
                    listener(newState, oldState);
                } catch (error) {
                    Logger.error('Store', `状态监听器执行错误[${key}]:`, error);
                }
            });
        }
    }

    // 清理组件状态
    clearComponentState(componentId) {
        this.state.componentStates.delete(componentId);
        Logger.debug('Store', `清理组件[${componentId}]状态`);
    }

    // 清理页面状态
    clearPageState(pageName) {
        this.state.pageStates.delete(pageName);
        Logger.debug('Store', `清理页面[${pageName}]状态`);
    }

    // 保存组件状态快照
    saveComponentSnapshot(componentId) {
        const state = this.getComponentState(componentId);
        return JSON.stringify(state);
    }

    // 恢复组件状态快照
    restoreComponentSnapshot(componentId, snapshot) {
        try {
            const state = JSON.parse(snapshot);
            this.setComponentState(componentId, state);
            Logger.debug('Store', `恢复组件[${componentId}]状态快照`);
        } catch (error) {
            Logger.error('Store', `恢复组件[${componentId}]状态快照失败:`, error);
        }
    }
} 

export default Store;