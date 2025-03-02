/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-26 22:10:58
 * @LastEditors: 一根鱼骨棒
 * @Description: 路由核心模块
 */

import Logger from '../../utils/logger.js';
import { ROUTE_EVENTS } from '../config/events.js';
import { WEBNAME } from '../../config/config.js';

class Router {
    constructor(eventBus) {
        this.eventBus = eventBus;
        this.currentRoute = '/';
        this.history = [];
        this.isNavigating = false;
        this.pendingNavigation = null;
        
        // 路由配置
        this.routes = {
            '/': {
                container: '.game-container',
                template: '/api/templates/home',
                title: `${WEBNAME} - 地球Online`,
                init: () => this.eventBus.emit(ROUTE_EVENTS.HOME_INIT),
                cleanup: () => this.eventBus.emit(ROUTE_EVENTS.HOME_CLEANUP)
            },
            '/shop': {
                container: '.game-container',
                template: '/api/templates/shop',
                title: `兑换商店 - ${WEBNAME}`,
                init: () => this.eventBus.emit(ROUTE_EVENTS.SHOP_INIT),
                cleanup: () => this.eventBus.emit(ROUTE_EVENTS.SHOP_CLEANUP)
            }
        };

        // 监听浏览器前进后退
        window.addEventListener('popstate', async (e) => {
            const path = e.state?.path || '/';
            if (!this.isNavigating && path !== this.currentRoute) {
                this.pendingNavigation = { path, isPopState: true };
                await this.processNavigation();
            }
        });
    }

    /**
     * 初始化路由
     */
    async initialize() {
        Logger.info('Router', 'initialize', '初始化路由系统');
        this.pendingNavigation = { 
            path: window.location.pathname, 
            isPopState: false 
        };
        await this.processNavigation();
    }

    /**
     * 路由跳转
     */
    async navigate(path) {
        Logger.info('Router', 'navigate', '路由跳转:', path);
        
        if (path === this.currentRoute || this.isNavigating) {
            return;
        }

        this.pendingNavigation = { path, isPopState: false };
        await this.processNavigation();
    }

    /**
     * 处理导航请求
     */
    async processNavigation() {
        if (this.isNavigating || !this.pendingNavigation) {
            Logger.info('Router', 'processNavigation', '导航请求已处理或不存在');
            return;
        }

        const { path, isPopState } = this.pendingNavigation;
        this.pendingNavigation = null;

        try {
            this.isNavigating = true;
            
            // 如果是相同路由，不处理
            if (path === this.currentRoute) {
                return;
            }
            Logger.debug('Router', 'processNavigation', '触发路由变化前事件');
            // 触发路由变化前事件
            this.eventBus.emit(ROUTE_EVENTS.BEFORE_CHANGE, { 
                from: this.currentRoute,
                to: path 
            });

            if (!isPopState) {
                Logger.debug('Router', 'processNavigation', '更新历史记录');
                // 更新历史记录
                window.history.pushState({ path }, '', path);
                if (!this.history.includes(path)) {
                    this.history.push(this.currentRoute);
                }
            }
            
            await this.handleRoute(path, isPopState);
        } catch (error) {
            Logger.error('Router', 'processNavigation', '导航处理失败:', error);
            this.eventBus.emit(ROUTE_EVENTS.ERROR, {
                error: error.message,
                path: path
            });
        } finally {
            this.isNavigating = false;
            
            // 如果有待处理的导航，继续处理
            if (this.pendingNavigation) {
                await this.processNavigation();
            }
        }
    }

    /**
     * 处理路由变化
     */
    async handleRoute(path, isPopState = false) {
        const route = this.routes[path];
        if (!route) {
            throw new Error(`路由不存在: ${path}`);
        }

        try {
            Logger.info('Router', 'handleRoute', '开始处理路由:', path);

            // 仅在实际的路由跳转时触发路由加载开始事件
            if (isPopState && path === '/') {
                this.eventBus.emit(ROUTE_EVENTS.LOADING_START, { path });
            }

            // 执行当前路由的清理函数
            const currentRoute = this.routes[this.currentRoute];
            if (currentRoute && currentRoute.cleanup) {
                await currentRoute.cleanup();
            }

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

            // 清理旧页面内容并更新
            container.innerHTML = html;
            document.title = route.title;

            const oldPath = this.currentRoute;
            this.currentRoute = path;

            // 处理历史记录
            if (isPopState) {
                const index = this.history.indexOf(path);
                if (index !== -1) {
                    this.history = this.history.slice(0, index);
                }
            }

            // 触发路由变化事件
            this.eventBus.emit(ROUTE_EVENTS.CHANGED, { 
                from: oldPath,
                to: path,
                isPopState 
            });

            // 执行新路由的初始化函数
            if (route.init) {
                await route.init();
            }

            // 触发路由加载结束事件
            this.eventBus.emit(ROUTE_EVENTS.LOADING_END, { path });

            // 触发路由变化后事件
            this.eventBus.emit(ROUTE_EVENTS.AFTER_CHANGE, { 
                from: oldPath,
                to: path,
                isPopState
            });

            Logger.info('Router', 'handleRoute', `路由处理完成: ${path}, isPopState: ${isPopState}`);
        } catch (error) {
            Logger.error('Router', 'handleRoute', '路由处理失败:', error);
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