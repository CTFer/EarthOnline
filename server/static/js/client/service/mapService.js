/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:42
 * @LastEditTime: 2025-02-18 14:09:33
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
/*
 * @Author: 一根鱼骨棒
 * @Description: 地图服务管理器
 */
import Logger from '../../utils/logger.js';
import { MAP_CONFIG } from '../../config/config.js';
import AMapRenderer from './map/amapRenderer.js';
import EchartsRenderer from './map/echartsRenderer.js';
import { 
    MAP_EVENTS,
    UI_EVENTS 
} from "../config/events.js";

class MapService {
    constructor(api, eventBus) {
        // 首先记录构造函数开始执行的日志
        Logger.info('MapService', '开始初始化地图服务');
        
        // 检查必要的依赖
        if (!api || !eventBus) {
            Logger.error('MapService', '初始化失败：缺少必要的依赖');
            throw new Error('MapService requires api and eventBus dependencies');
        }
        
        // 保存核心依赖
        this.api = api;
        this.eventBus = eventBus;
        
        try {
            // 渲染器相关初始化
            Logger.debug('MapService', '初始化渲染器配置');
            this.currentRenderer = null;
            this.renderType = localStorage.getItem('mapType') || MAP_CONFIG.RENDER_TYPE;
            
            // 初始化时间范围
            Logger.debug('MapService', '初始化时间范围配置');
            this.timeRange = localStorage.getItem('mapTimeRange');
            if (!this.timeRange) {
                this.timeRange = 'today';
                localStorage.setItem('mapTimeRange', 'today');
                Logger.debug('MapService', '设置默认时间范围: today');
            } else {
                Logger.debug('MapService', '从localStorage读取时间范围:', this.timeRange);
            }
            
            // 初始化自定义时间范围
            this.customStartTime = null;
            this.customEndTime = null;
            
            // 初始化WebSocket管理器引用
            this.wsManager = null;
            
            // 设置事件监听
            Logger.debug('MapService', '开始设置事件监听');
            this.setupEventListeners();
            
            Logger.info('MapService', '地图服务初始化完成');
        } catch (error) {
            Logger.error('MapService', '地图服务初始化失败:', error);
            throw error;
        }
    }

    setupEventListeners() {
        Logger.debug('MapService', '设置事件监听');
        
        // GPS更新事件
        this.eventBus.on(MAP_EVENTS.GPS_UPDATED, this.handleGPSUpdate.bind(this));
        
        // 地图切换事件
        this.eventBus.on(MAP_EVENTS.RENDERER_CHANGED, this.handleMapSwitch.bind(this));
        
        // 显示模式切换事件
        this.eventBus.on(MAP_EVENTS.DISPLAY_MODE_CHANGED, this.handleDisplayModeSwitch.bind(this));
        
        // 时间范围变更事件
        this.eventBus.on(MAP_EVENTS.TIME_RANGE_CHANGED, this.handleTimeRangeChange.bind(this));
        
        Logger.info('MapService', '事件监听设置完成');
    }

    // 初始化UI组件
    initializeUI() {
        Logger.info('MapService', '初始化地图UI组件');
        
        try {
            this.initMapSwitchButton();
            this.initTimeRangeSelector();
            this.initCustomTimeRange();
            this.initDisplayModeButton();
            
            Logger.info('MapService', '地图UI组件初始化完成');
        } catch (error) {
            Logger.error('MapService', '初始化地图UI组件失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '初始化地图控件失败'
            });
        }
    }

    initMapSwitchButton() {
        Logger.debug('MapService', '初始化地图切换按钮');
        
        // 使用多个选择器尝试找到按钮
        const mapSwitchBtn = document.getElementById('switchMapType');
                            
        if (!mapSwitchBtn) {
            Logger.error('MapService', '找不到地图容器，无法创建切换按钮');
        } else {
            this.initMapSwitchButtonEvents(mapSwitchBtn);
        }
    }

    initMapSwitchButtonEvents(button) {
        if (!button) return;
        
        button.addEventListener('click', () => {
            const newType = this.renderType === 'AMAP' ? 'ECHARTS' : 'AMAP';
            this.eventBus.emit(MAP_EVENTS.RENDERER_CHANGED, newType);
        });
        
        this.updateMapSwitchButtonText(button);
    }

    updateMapSwitchButtonText(button) {
        const btn = button || document.querySelector('.map-switch-btn');
        if (!btn) {
            Logger.warn('MapService', '找不到地图切换按钮，无法更新文本');
            return;
        }

        try {
            const buttonText = btn.querySelector('span') || btn;
            const currentType = this.renderType;
            const targetType = currentType === 'AMAP' ? 'Echarts' : '高德';
            buttonText.textContent = `切换到${targetType}地图`;
            btn.dataset.type = currentType;
            Logger.debug('MapService', `更新按钮文本为: ${buttonText.textContent}, 当前地图类型: ${currentType}`);
        } catch (error) {
            Logger.error('MapService', '更新按钮文本失败:', error);
        }
    }

    initTimeRangeSelector() {
        Logger.debug('MapService', '初始化时间范围选择器');
        const timeRangeSelect = document.getElementById('timeRangeSelect');
        
        if (!timeRangeSelect) {
            Logger.warn('MapService', '找不到时间范围选择器');
            return;
        }

        try {
            // 从localStorage获取保存的时间范围
            const savedTimeRange = localStorage.getItem('mapTimeRange');
            if (savedTimeRange) {
                timeRangeSelect.value = savedTimeRange;
                this.timeRange = savedTimeRange;
                Logger.debug('MapService', `设置时间范围选择器值为: ${savedTimeRange}`);
            }

            // 添加change事件监听
            timeRangeSelect.addEventListener('change', (e) => {
                const newValue = e.target.value;
                Logger.debug('MapService', `时间范围变更为: ${newValue}`);
                this.eventBus.emit(MAP_EVENTS.TIME_RANGE_CHANGED, newValue);
            });

            // 初始化自定义时间范围的显示状态
            this.updateCustomTimeRangeVisibility();
        } catch (error) {
            Logger.error('MapService', '初始化时间范围选择器失败:', error);
        }
    }

    initCustomTimeRange() {
        const startInput = document.getElementById('startTime');
        const endInput = document.getElementById('endTime');
        const applyButton = document.getElementById('applyCustomRange');
        
        if (startInput && endInput) {
            if (this.timeRange === 'custom' && this.customStartTime && this.customEndTime) {
                startInput.value = this.customStartTime;
                endInput.value = this.customEndTime;
            }
            
            startInput.addEventListener('change', () => {
                this.customStartTime = startInput.value;
            });
            
            endInput.addEventListener('change', () => {
                this.customEndTime = endInput.value;
            });
            
            if (applyButton) {
                applyButton.addEventListener('click', () => {
                    if (!this.validateTimeRange(startInput.value, endInput.value)) {
                        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                            type: 'WARNING',
                            message: '请选择有效的时间范围'
                        });
                        return;
                    }
                    
                    this.customStartTime = startInput.value;
                    this.customEndTime = endInput.value;
                    this.updateMapData();
                });
            }
        }
        
        this.updateCustomTimeRangeVisibility();
    }

    initDisplayModeButton() {
        Logger.debug('MapService', '初始化显示模式切换按钮');
        const displayModeSwitchBtn = document.getElementById('switchDisplayMode');
        if (!displayModeSwitchBtn) {
            Logger.warn('MapService', '找不到显示模式切换按钮');
            return;
        }

        // 添加点击事件监听
        displayModeSwitchBtn.addEventListener('click', () => {
            this.handleDisplayModeSwitch();
        });
    }

    validateTimeRange(start, end) {
        if (!start || !end) return false;
        
        const startTime = new Date(start);
        const endTime = new Date(end);
        
        if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) return false;
        if (startTime >= endTime) return false;
        
        return true;
    }

    updateDisplayModeButtonText() {
        const displayModeSwitchBtn = document.getElementById('switchDisplayMode');
        if (!displayModeSwitchBtn) {
            Logger.warn('MapService', '找不到显示模式切换按钮，无法更新文本');
            return;
        }

        try {
            const buttonText = displayModeSwitchBtn.querySelector('span') || displayModeSwitchBtn;
            // 获取当前显示模式
            Logger.debug('MapService', '获取currentRenderer:', this.currentRenderer);
            Logger.debug('MapService', '获取当前显示模式:', this.currentRenderer?.displayMode);
            const currentMode = this.currentRenderer?.displayMode || 'path';
            // 根据当前模式设置目标模式
            const targetMode = currentMode === 'point' ? '轨迹' : '点位';
            buttonText.textContent = `切换到${targetMode}显示`;
            displayModeSwitchBtn.dataset.mode = currentMode;
            Logger.debug('MapService', `更新显示模式按钮文本为: ${buttonText.textContent}, 当前模式: ${currentMode}`);
        } catch (error) {
            Logger.error('MapService', '更新显示模式按钮文本失败:', error);
        }
    }

    updateCustomTimeRangeVisibility() {
        const customDateRange = document.getElementById('customDateRange');
        if (customDateRange) {
            customDateRange.style.display = this.timeRange === 'custom' ? 'block' : 'none';
        }
    }

    async handleTimeRangeChange(range) {
        Logger.debug('MapService', '时间范围变更:', range);
        try {
            this.timeRange = range;
            localStorage.setItem('mapTimeRange', range);
            
            this.updateCustomTimeRangeVisibility();
            
            if (range === 'custom') {
                if (!this.customStartTime || !this.customEndTime) {
                    this.setDefaultCustomTimeRange();
                }
                return;
            }
            
            await this.updateMapData();
        } catch (error) {
            Logger.error('MapService', '处理时间范围变更失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '更新时间范围失败'
            });
        }
    }

    setDefaultCustomTimeRange() {
        const now = new Date();
        const startTime = new Date(now.setHours(0, 0, 0, 0));
        const endTime = new Date(now.setHours(23, 59, 59, 999));
        
        this.customStartTime = startTime.toISOString().slice(0, 16);
        this.customEndTime = endTime.toISOString().slice(0, 16);
        
        const startInput = document.getElementById('startTime');
        const endInput = document.getElementById('endTime');
        
        if (startInput) startInput.value = this.customStartTime;
        if (endInput) endInput.value = this.customEndTime;
    }

    async handleGPSUpdate(data) {
        Logger.debug('MapService', 'GPS更新:', data);
        try {
            if (!this.validateGPSData(data)) {
                Logger.warn('MapService', '无效的GPS数据:', data);
                return;
            }

            if (this.currentRenderer) {
                await this.currentRenderer.updatePosition(data);
                await this.currentRenderer.updateGPSInfo(data);
            } else {
                Logger.warn('MapService', '没有活动的渲染器');
            }
        } catch (error) {
            Logger.error('MapService', '处理GPS更新失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '更新GPS位置失败'
            });
        }
    }

    validateGPSData(data) {
        if (!data || typeof data !== 'object') return false;
        if (!data.latitude || !data.longitude) return false;
        if (typeof data.latitude !== 'number' || typeof data.longitude !== 'number') return false;
        return true;
    }

    async handleMapSwitch(type) {
        Logger.debug('MapService', '收到地图切换请求:', type);
        try {
            this.switchRenderer(type).catch(error => {
                Logger.error('MapService', '地图切换失败:', error);
                this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                    type: 'ERROR',
                    message: '地图切换失败'
                });
                // 切换到Echarts
                this.switchRenderer('ECHARTS');
            });
        } catch (error) {
            Logger.error('MapService', '处理地图切换请求失败:', error);
        }
    }

    handleDisplayModeSwitch() {
        Logger.debug('MapService', '切换显示模式');
        try {
            if (this.currentRenderer && typeof this.currentRenderer.toggleDisplayMode === 'function') {
                const previousMode = this.currentRenderer.displayMode;
                this.currentRenderer.toggleDisplayMode();
                const newMode = this.currentRenderer.displayMode;
                Logger.debug('MapService', `显示模式从 ${previousMode} 切换到 ${newMode}`);
                this.updateDisplayModeButtonText();
            } else {
                Logger.warn('MapService', '当前渲染器不支持切换显示模式');
            }
        } catch (error) {
            Logger.error('MapService', '切换显示模式失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '切换显示模式失败'
            });
        }
    }

    async initMap() {
        Logger.info('MapService', '开始初始化地图');
        
        try {
            // 初始化地图UI组件
            Logger.info('MapService', '初始化地图UI组件');
            await this.initializeUI();
            Logger.info('MapService', '地图UI组件初始化完成');
            
            // 再次确认时间范围设置
            Logger.debug('MapService', '确认时间范围设置');
            if (!this.timeRange) {
                this.timeRange = 'today';
                localStorage.setItem('mapTimeRange', 'today');
                Logger.debug('MapService', '重新设置默认时间范围: today');
            }
            Logger.debug('MapService', '当前时间范围:', this.timeRange);
            
            // 从localStorage获取渲染器类型
            const rendererType = localStorage.getItem('mapType') || 'ECHARTS';
            Logger.info('MapService', '从localStorage获取渲染器类型:', rendererType);
            
            // 初始化渲染器
            await this.initRenderer(rendererType);
            Logger.info('MapService', '地图渲染器初始化完成');
            
            // 在渲染器初始化完成后更新显示模式按钮文本
            this.updateDisplayModeButtonText();
            
            // 更新地图数据
            Logger.debug('MapService', '开始更新地图数据，时间范围:', this.timeRange);
            await this.updateMapData();
            
        } catch (error) {
            Logger.error('MapService', '地图初始化失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '地图初始化失败: ' + error.message,
                duration: 5000
            });
            
            // 如果初始化失败，尝试使用Echarts作为后备方案
            if (!this.currentRenderer) {
                Logger.warn('MapService', '尝试使用Echarts作为后备渲染器');
                try {
                    await this.initRenderer('ECHARTS');
                    await this.updateMapData();
                } catch (backupError) {
                    Logger.error('MapService', '后备渲染器初始化也失败了:', backupError);
                }
            }
        }
        
        Logger.info('MapService', '地图初始化完成');
    }

    /**
     * 初始化渲染器（仅在首次加载时使用）
     * @private
     */
    async initRenderer(type) {
        Logger.info('MapService', `初始化地图渲染器: ${type}`);
        
        try {
            // 如果没有指定类型，从localStorage获取，默认为ECHARTS
            const renderType = type || localStorage.getItem('mapType') || 'ECHARTS';
            // 转换为大写以确保一致性
            const normalizedType = renderType.toUpperCase();
            
            Logger.debug('MapService', `使用渲染器类型: ${normalizedType}`);
            
            // 清理现有渲染器
            if (this.currentRenderer) {
                this.currentRenderer.destroy();
                this.currentRenderer = null;
            }

            // 根据类型创建新的渲染器
            switch (normalizedType) {
                case 'AMAP':
                    this.currentRenderer = new AMapRenderer(this.api);
                    await this.currentRenderer.loadAMapScript();
                    break;
                case 'ECHARTS':
                    this.currentRenderer = new EchartsRenderer(this.api);
                    break;
                default:
                    Logger.warn('MapService', `未知的渲染器类型: ${normalizedType}，使用默认的Echarts渲染器`);
                    this.currentRenderer = new EchartsRenderer(this.api);
            }

            // 初始化渲染器
            await this.currentRenderer.initializeMap();
            
            // 更新本地存储
            localStorage.setItem('mapType', normalizedType);
            
            Logger.info('MapService', `地图渲染器(${normalizedType})初始化完成`);
            
            // 触发渲染器变更事件
            this.eventBus.emit(MAP_EVENTS.RENDERER_CHANGED, normalizedType);
            
            return normalizedType;
        } catch (error) {
            Logger.error('MapService', '初始化渲染器失败:', error);
            throw error;
        }
    }

    /**
     * 切换地图渲染器（用于用户手动切换）
     */
    async switchRenderer(type) {
        // 如果类型相同，不进行切换
        if (type === this.renderType) {
            Logger.debug('MapService', '地图类型相同，无需切换');
            return;
        }
        
        Logger.info('MapService', `切换地图渲染器: ${type}`);
        
        try {
            // 保存当前设置
            if (this.currentRenderer) {
                this.timeRange = this.currentRenderer.timeRange;
                this.customStartTime = this.currentRenderer.customStartTime;
                this.customEndTime = this.currentRenderer.customEndTime;
            }

            // 清理现有渲染器
            if (this.currentRenderer) {
                Logger.debug('MapService', '清理现有渲染器');
                await this.currentRenderer.destroy();
            }

            // 清空地图容器
            const container = document.getElementById('gpsMapContainer');
            if (!container) {
                throw new Error('找不到地图容器');
            }
            container.innerHTML = '';

            // 更新按钮文本
            const mapSwitchBtn = document.getElementById('switchMapType');
            if (mapSwitchBtn) {
                this.updateMapSwitchButtonText(mapSwitchBtn);
            }

            // 初始化新渲染器
            await this.initRenderer(type);

            // 更新存储的渲染器类型
            this.renderType = type;
            localStorage.setItem('mapType', type);
            
            // 更新地图数据
            await this.updateMapData();
            
            // 显示成功通知
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'SUCCESS',
                message: '地图切换成功'
            });
            
            Logger.info('MapService', '地图渲染器切换完成');
        } catch (error) {
            Logger.error('MapService', '切换渲染器失败:', error);
            throw error;
        }
    }

    // 设置WebSocket管理器
    setWebSocketManager(wsManager) {
        Logger.info('MapService', '设置WebSocket管理器');
        if (!wsManager) {
            Logger.error('MapService', 'WebSocket管理器无效');
            return;
        }

        this.wsManager = wsManager;
        
        // 确保handleGPSUpdate已经绑定到this
        if (!this.handleGPSUpdate) {
            this.handleGPSUpdate = this.handleGPSUpdate.bind(this);
        }

        try {
            // 检查wsManager是否有onGPSUpdate方法
            if (typeof this.wsManager.onGPSUpdate === 'function') {
                this.wsManager.onGPSUpdate(this.handleGPSUpdate);
                Logger.info('MapService', 'GPS更新处理器设置成功');
            } else {
                Logger.error('MapService', 'WebSocket管理器缺少onGPSUpdate方法');
            }
        } catch (error) {
            Logger.error('MapService', 'GPS更新处理器设置失败:', error);
        }
    }

    // 更新地图数据
    async updateMapData() {
        Logger.debug('MapService', '开始更新地图数据');
        
        // 检查渲染器是否已初始化
        if (!this.currentRenderer) {
            Logger.warn('MapService', '渲染器未初始化，无法更新地图数据');
            return;
        }
        
        // 验证时间范围
        if (!this.timeRange) {
            Logger.warn('MapService', '时间范围未设置，使用默认值: today');
            this.timeRange = 'today';
            localStorage.setItem('mapTimeRange', 'today');
        }
        Logger.debug('MapService', `当前时间范围: ${this.timeRange}`);
        
        const playerId = localStorage.getItem('playerId');
        if (!playerId) {
            Logger.error('MapService', '无法更新地图数据: 未找到玩家ID');
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '无法更新地图数据: 未找到玩家ID',
                duration: 5000
            });
            return;
        }
        
        try {
            Logger.debug('MapService', `准备获取GPS数据，时间范围: ${this.timeRange}, 玩家ID: ${playerId}`);
            const params = new URLSearchParams();
            const now = Date.now();
            let startTime, endTime;
            
            // 计算时间范围
            switch(this.timeRange) {
                case 'today':
                    startTime = Math.floor(new Date().setHours(0,0,0,0) / 1000);
                    endTime = Math.floor(new Date().setHours(23,59,59,999) / 1000);
                    Logger.debug('MapService', `今日时间范围: ${new Date(startTime * 1000).toLocaleString()} - ${new Date(endTime * 1000).toLocaleString()}`);
                    break;
                case 'week':
                    startTime = Math.floor(now / 1000 - 7 * 24 * 60 * 60);
                    endTime = Math.floor(now / 1000);
                    break;
                case 'month':
                    startTime = Math.floor(now / 1000 - 30 * 24 * 60 * 60);
                    endTime = Math.floor(now / 1000);
                    break;
                case 'year':
                    startTime = Math.floor(now / 1000 - 365 * 24 * 60 * 60);
                    endTime = Math.floor(now / 1000);
                    break;
                case 'custom':
                    if (this.customStartTime && this.customEndTime) {
                        startTime = Math.floor(new Date(this.customStartTime).getTime() / 1000);
                        endTime = Math.floor(new Date(this.customEndTime).getTime() / 1000);
                    } else {
                        Logger.warn('MapService', '自定义时间范围未设置，使用今天作为默认值');
                        startTime = Math.floor(new Date().setHours(0,0,0,0) / 1000);
                        endTime = Math.floor(new Date().setHours(23,59,59,999) / 1000);
                    }
                    break;
                default:
                    Logger.error('MapService', `不支持的时间范围类型: ${this.timeRange}`);
                    this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                        type: 'ERROR',
                        message: `不支持的时间范围: ${this.timeRange}，已重置为today`,
                        duration: 5000
                    });
                    this.timeRange = 'today';
                    localStorage.setItem('mapTimeRange', 'today');
                    startTime = Math.floor(new Date().setHours(0,0,0,0) / 1000);
                    endTime = Math.floor(new Date().setHours(23,59,59,999) / 1000);
            }
            
            // 验证时间参数
            if (!Number.isInteger(startTime) || !Number.isInteger(endTime)) {
                throw new Error(`时间参数无效: startTime=${startTime}, endTime=${endTime}`);
            }
            
            Logger.debug('MapService', `发起GPS数据请求，开始时间: ${new Date(startTime * 1000).toLocaleString()}, 结束时间: ${new Date(endTime * 1000).toLocaleString()}`);
            
            params.append('start_time', startTime);
            params.append('end_time', endTime);
            
            // 使用API获取GPS数据
            const result = await this.api.getGPSData(playerId, params);
            
            if (result.code === 0 && result.data) {
                Logger.debug('MapService', `获取到 ${result.data.records?.length || 0} 条GPS记录`);
                
                if (!Array.isArray(result.data.records)) {
                    throw new Error('GPS数据格式无效');
                }
                
                // 更新渲染器数据
                await this.currentRenderer.updateMapData({
                    timeRange: this.timeRange,
                    startTime: startTime,
                    endTime: endTime,
                    gpsData: result.data.records.sort((a, b) => a.addtime - b.addtime),
                    center: result.data.center || null,
                    bounds: result.data.bounds || null
                });
                
                Logger.info('MapService', '地图数据更新完成');
            } else {
                throw new Error(result.msg || '获取GPS数据失败');
            }
        } catch (error) {
            Logger.error('MapService', '更新地图数据失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: `更新地图数据失败: ${error.message}`,
                duration: 5000
            });
        }
    }

    destroy() {
        Logger.info('MapService', '开始销毁地图服务');
        
        // 取消事件订阅
        this.eventBus.off(MAP_EVENTS.GPS_UPDATED, this.handleGPSUpdate);
        this.eventBus.off(MAP_EVENTS.RENDERER_CHANGED, this.handleMapSwitch);
        this.eventBus.off(MAP_EVENTS.DISPLAY_MODE_CHANGED, this.handleDisplayModeSwitch);
        this.eventBus.off(MAP_EVENTS.TIME_RANGE_CHANGED, this.handleTimeRangeChange);
        
        // 销毁当前渲染器
        if (this.currentRenderer) {
            this.currentRenderer.destroy();
        }
        
        Logger.info('MapService', '地图服务销毁完成');
    }

    // ... 其他地图相关方法
}

export default MapService; 