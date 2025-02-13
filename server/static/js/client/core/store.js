/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:30:39
 * @LastEditTime: 2025-02-12 20:30:45
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
class Store {
    constructor() {
        this.state = {
            player: null,
            tasks: [],
            loading: false
        };
        this.listeners = [];
        console.log('[Store] Store initialized');
    }

    setState(newState) {
        console.log('[Store] State update:', newState);
        this.state = { ...this.state, ...newState };
        this.notify();
    }

    subscribe(listener) {
        this.listeners.push(listener);
    }

    notify() {
        this.listeners.forEach(listener => listener(this.state));
    }
} 