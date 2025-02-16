/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:42
 * @LastEditTime: 2025-02-16 18:57:50
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

class MapService {
    constructor(api, eventBus) {
        this.api = api;
        this.eventBus = eventBus;
        
        this.currentRenderer = null;
        this.renderType = localStorage.getItem('mapType') || MAP_CONFIG.RENDER_TYPE;
        
        // 时间范围设置
        this.timeRange = localStorage.getItem('mapTimeRange') || 'today';
        this.customStartTime = null;
        this.customEndTime = null;
        
        // WebSocket管理器引用
        this.wsManager = null;
        
        // 绑定事件处理器
        this.handleGPSUpdate = this.handleGPSUpdate.bind(this);
        this.handleMapSwitch = this.handleMapSwitch.bind(this);
        this.handleDisplayModeSwitch = this.handleDisplayModeSwitch.bind(this);
        this.handleTimeRangeChange = this.handleTimeRangeChange.bind(this);
        
        // 订阅相关事件
        this.eventBus.on('gps:update', this.handleGPSUpdate);
        this.eventBus.on('map:switch', this.handleMapSwitch);
        this.eventBus.on('map:display:switch', this.handleDisplayModeSwitch);
        this.eventBus.on('map:timerange:change', this.handleTimeRangeChange);
        
        Logger.info('MapService', '初始化地图服务');
    }

    // 初始化UI组件
    initializeUI() {
        Logger.info('MapService', '初始化地图UI组件');
        
        // 初始化地图切换按钮
        const mapSwitchBtn = document.getElementById('switchMapType');
        if (mapSwitchBtn) {
            mapSwitchBtn.addEventListener('click', () => {
                const newType = this.renderType === 'AMAP' ? 'ECHARTS' : 'AMAP';
                this.handleMapSwitch(newType);
            });
            
            // 设置初始按钮文本
            const buttonText = mapSwitchBtn.querySelector('span');
            if (buttonText) {
                buttonText.textContent = `切换到${this.renderType === 'AMAP' ? 'Echarts' : '高德'}地图`;
            }
        } else {
            Logger.warn('MapService', '地图切换按钮未找到');
        }

        // 初始化时间范围选择器
        const timeRangeSelect = document.getElementById('timeRangeSelect');
        if (timeRangeSelect) {
            timeRangeSelect.value = this.timeRange;
            timeRangeSelect.addEventListener('change', (e) => {
                this.handleTimeRangeChange(e.target.value);
            });
        }

        // 初始化自定义时间输入框
        const startInput = document.getElementById('startTime');
        const endInput = document.getElementById('endTime');
        const applyButton = document.getElementById('applyCustomRange');
        
        if (startInput && endInput) {
            // 设置初始值
            if (this.timeRange === 'custom' && this.customStartTime && this.customEndTime) {
                startInput.value = this.customStartTime;
                endInput.value = this.customEndTime;
            }
            
            // 添加时间输入事件监听
            startInput.addEventListener('change', () => {
                this.customStartTime = startInput.value;
            });
            
            endInput.addEventListener('change', () => {
                this.customEndTime = endInput.value;
            });
            
            // 添加应用按钮事件监听
            if (applyButton) {
                applyButton.addEventListener('click', async () => {
                    if (!startInput.value || !endInput.value) {
                        layer.msg('请选择完整的时间范围', {icon: 2});
                        return;
                    }
                    
                    this.customStartTime = startInput.value;
                    this.customEndTime = endInput.value;
                    await this.updateMapData();
                });
            }
        }
        
        // 设置初始显示状态
        const customDateRange = document.getElementById('customDateRange');
        if (customDateRange) {
            customDateRange.style.display = this.timeRange === 'custom' ? 'block' : 'none';
        }

        // 初始化显示模式切换按钮
        const displayModeSwitchBtn = document.getElementById('switchDisplayMode');
        if (displayModeSwitchBtn) {
            displayModeSwitchBtn.addEventListener('click', () => {
                this.handleDisplayModeSwitch();
            });
            
            // 设置初始按钮文本
            const buttonText = displayModeSwitchBtn.querySelector('span');
            if (buttonText) {
                const mode = this.currentRenderer?.displayMode === 'point' ? '轨迹' : '点位';
                buttonText.textContent = `切换到${mode}显示`;
            }
        }
    }

    async handleTimeRangeChange(range) {
        Logger.debug('MapService', '时间范围变更:', range);
        this.timeRange = range;
        localStorage.setItem('mapTimeRange', range);
        
        // 修正自定义时间范围的显示/隐藏逻辑
        const customDateRange = document.getElementById('customDateRange');
        const customTimeContainer = document.getElementById('customTimeContainer');
        
        if (customDateRange) {
            customDateRange.style.display = range === 'custom' ? 'block' : 'none';
        }
        
        if (customTimeContainer) {
            customTimeContainer.style.display = range === 'custom' ? 'block' : 'none';
        }
        
        // 如果是自定义时间范围，设置默认值并等待用户选择
        if (range === 'custom') {
            Logger.debug('MapService', '切换到自定义时间范围模式');
            if (!this.customStartTime || !this.customEndTime) {
                const now = new Date();
                const startTime = new Date(now.setHours(0, 0, 0, 0));
                const endTime = new Date(now.setHours(23, 59, 59, 999));
                
                this.customStartTime = startTime.toISOString().slice(0, 16);
                this.customEndTime = endTime.toISOString().slice(0, 16);
            }
            
            const startInput = document.getElementById('startTime');
            const endInput = document.getElementById('endTime');
            const applyButton = document.getElementById('applyCustomRange');
            
            if (startInput) startInput.value = this.customStartTime;
            if (endInput) endInput.value = this.customEndTime;
            
            // 移除之前的事件监听器
            if (applyButton) {
                const newButton = applyButton.cloneNode(true);
                applyButton.parentNode.replaceChild(newButton, applyButton);
                
                // 添加新的事件监听器
                newButton.addEventListener('click', async () => {
                    const start = startInput ? startInput.value : null;
                    const end = endInput ? endInput.value : null;
                    
                    if (!start || !end) {
                        layer.msg('请选择完整的时间范围', {icon: 2});
                        return;
                    }
                    
                    this.customStartTime = start;
                    this.customEndTime = end;
                    await this.updateMapData();
                });
            }
            
            // 不立即更新数据，等待用户点击应用按钮
            return;
        }
        
        // 非自定义时间范围，直接更新数据
        await this.updateMapData();
    }

    async handleGPSUpdate(data) {
        Logger.debug('MapService', '收到GPS更新:', data);
        if (!this.currentRenderer || !data) {
            Logger.warn('MapService', 'GPS更新处理失败:', {
                hasRenderer: !!this.currentRenderer,
                hasData: !!data
            });
            return;
        }

        try {
            // 检查是否只是状态更新（无坐标）
            if (!data.x || !data.y) {
                Logger.debug('MapService', '仅状态更新，无需添加新点位');
                if (typeof this.currentRenderer.updateGPSInfo === 'function') {
                    this.currentRenderer.updateGPSInfo(data);
                }
                return;
            }

            // 有坐标信息时，更新位置
            await this.currentRenderer.updatePosition(data);
            
            // 更新地图数据
            await this.updateMapData();
        } catch (error) {
            Logger.error('MapService', 'GPS更新处理错误:', error);
        }
    }

    async handleMapSwitch(type) {
        Logger.debug('MapService', '收到地图切换请求:', type);
        try {
            await this.switchRenderer(type);
            localStorage.setItem('mapType', type);
            
            // 更新按钮文本
            const mapSwitchBtn = document.getElementById('switchMapType');
            if (mapSwitchBtn) {
                const buttonText = mapSwitchBtn.querySelector('span');
                if (buttonText) {
                    buttonText.textContent = `切换到${type === 'AMAP' ? 'Echarts' : '高德'}地图`;
                }
            }
            
            // 切换后立即加载数据
            await this.updateMapData();
        } catch (error) {
            Logger.error('MapService', '地图切换失败:', error);
            layer.msg('地图切换失败，请重试', {icon: 2});
        }
    }

    handleDisplayModeSwitch() {
        Logger.debug('MapService', '切换显示模式');
        if (this.currentRenderer && typeof this.currentRenderer.toggleDisplayMode === 'function') {
            this.currentRenderer.toggleDisplayMode();
            
            // 更新按钮文本
            const displayModeSwitchBtn = document.getElementById('switchDisplayMode');
            if (displayModeSwitchBtn) {
                const buttonText = displayModeSwitchBtn.querySelector('span');
                if (buttonText) {
                    const mode = this.currentRenderer.displayMode === 'point' ? '轨迹' : '点位';
                    buttonText.textContent = `切换到${mode}显示`;
                }
            }
        }
    }

    async initMap() {
        Logger.info('MapService', '开始初始化地图');
        try {
            // 先切换渲染器
            await this.switchRenderer(this.renderType);
            
            // 初始化UI组件
            this.initializeUI();
            
            // 确保有默认时间范围
            if (!this.timeRange) {
                this.timeRange = 'today';
                localStorage.setItem('mapTimeRange', 'today');
            }
            
            // 立即加载当天数据
            await this.updateMapData();
            
            Logger.info('MapService', '地图初始化完成');
        } catch (error) {
            Logger.error('MapService', '地图初始化失败:', error);
            throw error;
        }
    }

    /**
     * 切换地图渲染器
     * @param {string} type - 地图类型 ('AMAP' | 'ECHARTS')
     */
    async switchRenderer(type) {
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

            // 清理容器
            const container = document.getElementById('gpsMapContainer');
            if (container) {
                container.innerHTML = '';
            }

            // 创建新的渲染器
            Logger.debug('MapService', '创建新渲染器');
            switch (type) {
                case 'AMAP':
                    this.currentRenderer = new AMapRenderer(this.api);
                    break;
                case 'ECHARTS':
                    this.currentRenderer = new EchartsRenderer(this.api);
                    break;
                default:
                    throw new Error(`不支持的地图类型: ${type}`);
            }

            // 初始化新渲染器
            await this.currentRenderer.initializeMap();

            // 恢复时间范围设置
            this.currentRenderer.timeRange = this.timeRange;
            this.currentRenderer.customStartTime = this.customStartTime;
            this.currentRenderer.customEndTime = this.customEndTime;

            // 更新存储的渲染器类型
            this.renderType = type;
            localStorage.setItem('mapType', type);
            
            // 发送切换事件
            this.eventBus.emit('map:renderer:changed', type);
            
            Logger.info('MapService', '地图渲染器切换完成');
        } catch (error) {
            Logger.error('MapService', '切换渲染器失败:', error);
            throw error;
        }
    }

    // 设置WebSocket管理器
    setWebSocketManager(wsManager) {
        Logger.info('MapService', '设置WebSocket管理器');
        this.wsManager = wsManager;
        if (this.wsManager) {
            this.wsManager.onGPSUpdate(this.handleGPSUpdate);
        }
    }

    // 更新地图数据
    async updateMapData() {
        Logger.debug('MapService', '开始更新地图数据');
        if (!this.currentRenderer) {
            Logger.warn('MapService', '没有活动的渲染器');
            return;
        }

        try {
            // 构建查询参数
            let params = new URLSearchParams();
            const now = Date.now();

            // 确保有默认的时间范围
            if (!this.timeRange) {
                this.timeRange = 'today';
            }

            switch (this.timeRange) {
                case 'today':
                    params.append('start_time', Math.floor(new Date().setHours(0,0,0,0) / 1000));
                    params.append('end_time', Math.floor(new Date().setHours(23,59,59,999) / 1000));
                    break;
                case 'week':
                    params.append('start_time', Math.floor(now / 1000 - 7 * 24 * 60 * 60));
                    params.append('end_time', Math.floor(now / 1000));
                    break;
                case 'month':
                    params.append('start_time', Math.floor(now / 1000 - 30 * 24 * 60 * 60));
                    params.append('end_time', Math.floor(now / 1000));
                    break;
                case 'year':
                    params.append('start_time', Math.floor(now / 1000 - 365 * 24 * 60 * 60));
                    params.append('end_time', Math.floor(now / 1000));
                    break;
                case 'custom':
                    if (this.customStartTime && this.customEndTime) {
                        params.append('start_time', Math.floor(new Date(this.customStartTime).getTime() / 1000));
                        params.append('end_time', Math.floor(new Date(this.customEndTime).getTime() / 1000));
                    }
                    break;
            }

            // 获取玩家ID
            const playerId = localStorage.getItem('playerId') || '1';
            
            // 使用API获取GPS数据
            const result = await this.api.getGPSData(playerId, params);
            
            if (result.code === 0 && result.data) {
                // 更新渲染器数据
                await this.currentRenderer.updateMapData({
                    timeRange: this.timeRange,
                    startTime: this.customStartTime,
                    endTime: this.customEndTime,
                    gpsData: result.data.records.sort((a, b) => a.addtime - b.addtime),
                    center: result.data.center,
                    bounds: result.data.bounds
                });
                Logger.debug('MapService', '地图数据更新完成');
            } else {
                throw new Error('获取GPS数据失败: ' + result.msg);
            }
        } catch (error) {
            Logger.error('MapService', '更新地图数据失败:', error);
            layer.msg('更新地图数据失败', {icon: 2});
        }
    }

    destroy() {
        Logger.info('MapService', '开始销毁地图服务');
        // 取消事件订阅
        this.eventBus.off('gps:update', this.handleGPSUpdate);
        this.eventBus.off('map:switch', this.handleMapSwitch);
        this.eventBus.off('map:display:switch', this.handleDisplayModeSwitch);
        this.eventBus.off('map:timerange:change', this.handleTimeRangeChange);
        
        // 销毁当前渲染器
        if (this.currentRenderer) {
            this.currentRenderer.destroy();
        }
        Logger.info('MapService', '地图服务销毁完成');
    }

    // ... 其他地图相关方法
}

export default MapService; 