/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-26 22:10:58
 * @LastEditors: 一根鱼骨棒
 * @Description: 路由核心模块
 */

import Logger from '../../utils/logger.js';
import { ROUTE_EVENTS } from '../config/events.js';

class Router {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentRoute = '/';
        
        // 路由配置
        this.routes = {
            '/': {
                container: '.game-container',
                template: '/api/templates/home',
                title: '团总的地球Online'
            },
            '/shop': {
                container: '.game-container',
                template: '/api/templates/shop',
                title: '商城 - 团总的地球Online'
            }
        };

        // 监听浏览器前进后退
        window.addEventListener('popstate', (e) => this.handleRoute(e.state?.path || '/'));
    }

    /**
     * 初始化路由
     */
    async initialize() {
        Logger.info('Router', 'initialize', '初始化路由系统');
        await this.handleRoute(window.location.pathname);
    }

    /**
     * 路由跳转
     */
    async navigate(path) {
        Logger.info('Router', 'navigate', '路由跳转:', path);
        
        // 触发路由变化前事件
        this.eventBus.emit(ROUTE_EVENTS.BEFORE_CHANGE, { 
            from: this.currentRoute,
            to: path 
        });

        // 更新历史记录
        window.history.pushState({ path }, '', path);
        await this.handleRoute(path);
    }

    /**
     * 处理路由变化
     */
    async handleRoute(path) {
        const route = this.routes[path];
        if (!route) {
            Logger.error('Router', 'handleRoute', '路由不存在:', path);
            this.eventBus.emit(ROUTE_EVENTS.ERROR, {
                error: '路由不存在',
                path: path
            });
            return;
        }

        try {
            Logger.info('Router', 'handleRoute', '开始处理路由:', path);
            
            // 触发路由加载开始事件
            this.eventBus.emit(ROUTE_EVENTS.LOADING_START, { path });

            // 加载模板
            const response = await fetch(route.template);
            if (!response.ok) {
                throw new Error(`模板加载失败: ${response.status} ${response.statusText}`);
            }
            const html = await response.text();

            // 更新页面内容
            const container = document.querySelector(route.container);
            if (!container) {
                throw new Error(`找不到容器: ${route.container}`);
            }

            // 清理旧页面内容
            this.eventBus.emit(ROUTE_EVENTS.BEFORE_CONTENT_CLEAR, {
                from: this.currentRoute,
                to: path
            });
            container.innerHTML = '';

            // 更新页面内容
            container.innerHTML = html;
            document.title = route.title;
            
            const oldPath = this.currentRoute;
            this.currentRoute = path;
            
            // 触发路由变化事件
            this.eventBus.emit(ROUTE_EVENTS.CHANGED, { 
                from: oldPath,
                to: path 
            });

            // 触发路由变化后事件
            this.eventBus.emit(ROUTE_EVENTS.AFTER_CHANGE, { 
                from: oldPath,
                to: path 
            });

            // 触发路由加载完成事件
            this.eventBus.emit(ROUTE_EVENTS.LOADING_END, { path });
            
            Logger.info('Router', 'handleRoute', '路由处理完成:', path);
        } catch (error) {
            Logger.error('Router', 'handleRoute', '路由处理失败:', error);
            this.eventBus.emit(ROUTE_EVENTS.ERROR, {
                error: error.message,
                path: path
            });
            throw error;
        }
    }

    /**
     * 获取当前路由
     */
    getCurrentRoute() {
        return this.currentRoute;
    }
}

export default Router; 