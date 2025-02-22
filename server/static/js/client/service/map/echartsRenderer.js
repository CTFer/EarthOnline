/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:11:15
 * @LastEditors: 一根鱼骨棒
 * @Description: Echarts地图渲染器
 */
import Logger from '../../../utils/logger.js';
import { ECHARTS_CONFIG, MARKER_STYLE, PATH_STYLE } from '../../config/mapConfig.js';

class EchartsRenderer {
    constructor(apiClient) {
        Logger.info('EchartsRenderer', '初始化Echarts地图渲染器');
        this.api = apiClient;
        this.mapChart = null;
        this.gpsData = [];
        this.currentZoom = null;
        this.currentCenter = null;
        this.displayMode = 'path';  // 默认为轨迹模式
        this.batteryLevel = 100;
        // 添加时间筛选相关属性
        this.timeRange = 'today';
        this.customStartTime = null;
        this.customEndTime = null;
        
        // 初始化时记录显示模式
        Logger.info('EchartsRenderer', '初始化显示模式: path');
    }

    async initializeMap() {
        Logger.debug('EchartsRenderer', '初始化地图');
        const container = document.getElementById('gpsMapContainer');
        if (!container) {
            throw new Error('地图容器不存在');
        }

        try {
            // 检查echarts是否已加载
            if (typeof echarts === 'undefined') {
                Logger.error('EchartsRenderer', 'Echarts库未加载');
                throw new Error('Echarts库未加载');
            }

            // 等待DOM完全准备好
            await new Promise(resolve => setTimeout(resolve, 100));

            // 初始化Echarts实例
            this.mapChart = echarts.init(container, null, {
                renderer: 'canvas',
                useDirtyRect: false
            });

            // 确保mapChart不为null
            if (!this.mapChart) {
                throw new Error('Echarts实例初始化失败');
            }

            // 先加载地图数据
            Logger.debug('EchartsRenderer', '加载地图数据');
            const chinaJson = await this.loadMapData();
            
            // 注册地图数据
            Logger.debug('EchartsRenderer', '注册地图数据');
            echarts.registerMap('china', chinaJson);

            // 等待一帧以确保地图数据已注册
            await new Promise(resolve => setTimeout(resolve, 50));

            // 设置初始配置
            Logger.debug('EchartsRenderer', '设置初始配置');
            const option = this.getInitialOption();
            this.mapChart.setOption(option, true);

            // 添加事件监听
            this.setupEventListeners();
            
            // 初始化时间筛选器
            this.initTimeFilter();

            Logger.info('EchartsRenderer', '地图初始化完成');
        } catch (error) {
            Logger.error('EchartsRenderer', '初始化地图失败:', error);
            throw error;
        }
    }

    async loadMapData() {
        Logger.debug('EchartsRenderer', '加载地图数据');
        try {
            const response = await fetch('/static/js/china.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (!data || !data.features) {
                throw new Error('无效的地图数据格式');
            }
            return data;
        } catch (error) {
            Logger.error('EchartsRenderer', '加载地图数据失败:', error);
            throw error;
        }
    }

    getInitialOption() {
        return {
            ...ECHARTS_CONFIG,
            geo: {
                ...ECHARTS_CONFIG.geo,
                map: 'china'  // 添加地图类型
            },
            series: []
        };
    }

    setupEventListeners() {
        this.mapChart.on('georoam', () => {
            const option = this.mapChart.getOption();
            if (option.geo && option.geo[0]) {
                this.currentZoom = option.geo[0].zoom;
                this.currentCenter = option.geo[0].center;
            }
        });
    }

    async updatePosition(gpsData) {
        Logger.debug('EchartsRenderer', '更新位置:', gpsData);
        
        try {
            // 保存当前视图状态
            this.saveViewState();
            
            // 添加新数据点
            this.gpsData.push(gpsData);
            
            // 更新地图显示
            await this.updateMap();
            
            // 更新实时信息
            this.updateGPSInfo(gpsData);
            
            Logger.debug('EchartsRenderer', '位置更新完成');
        } catch (error) {
            Logger.error('EchartsRenderer', '更新位置失败:', error);
            throw error;
        }
    }

    async updateMap() {
        if (!this.mapChart || !this.gpsData.length) {
            return;
        }

        const series = this.displayMode === 'path' ? 
            this.createPathSeries() : 
            this.createPointSeries();

        const option = {
            ...this.getInitialOption(),
            series: series
        };

        if (this.currentZoom && this.currentCenter) {
            option.geo.zoom = this.currentZoom;
            option.geo.center = this.currentCenter;
        }

        this.mapChart.setOption(option);
    }

    createPointSeries() {
        Logger.debug('EchartsRenderer', '创建点位显示系列');
        
        // 所有GPS点的散点图
        const pointSeries = {
            name: 'GPS点位',
            type: 'scatter',
            coordinateSystem: 'geo',
            data: this.gpsData.map((point, index) => ({
                name: `位置 ${index + 1}`,
                value: [parseFloat(point.x), parseFloat(point.y)],
                time: new Date(point.addtime * 1000).toLocaleString(),
                speed: point.speed || 0
            })),
            ...MARKER_STYLE.point
        };

        // 起点标记
        const startPoint = {
            name: '起点',
            type: 'scatter',
            coordinateSystem: 'geo',
            data: [{
                name: '起点',
                value: [parseFloat(this.gpsData[0].x), parseFloat(this.gpsData[0].y)],
                ...MARKER_STYLE.start,
                label: {
                    show: true,
                    position: 'top',
                    formatter: '起点',
                    color: '#fff',
                    fontSize: 12
                }
            }]
        };

        // 终点标记
        const endPoint = {
            name: '终点',
            type: 'scatter',
            coordinateSystem: 'geo',
            data: [{
                name: '终点',
                value: [
                    parseFloat(this.gpsData[this.gpsData.length - 1].x),
                    parseFloat(this.gpsData[this.gpsData.length - 1].y)
                ],
                ...MARKER_STYLE.end,
                label: {
                    show: true,
                    position: 'top',
                    formatter: '终点',
                    color: '#fff',
                    fontSize: 12
                }
            }]
        };

        return [pointSeries, startPoint, endPoint];
    }

    createPathSeries() {
        Logger.debug('EchartsRenderer', '创建轨迹显示系列');
        
        // 按时间排序
        const sortedData = [...this.gpsData].sort((a, b) => a.addtime - b.addtime);
        
        // 提取坐标点
        const pathData = sortedData.map(point => [
            parseFloat(point.x), 
            parseFloat(point.y)
        ]);

        return [
            // 轨迹线
            {
                name: '轨迹',
                type: 'lines',
                coordinateSystem: 'geo',
                polyline: true,
                data: [{
                    coords: pathData
                }],
                lineStyle: PATH_STYLE.lineStyle,
                effect: PATH_STYLE.effect,
                zlevel: 1
            },
            // 路径点
            {
                name: '路径点',
                type: 'scatter',
                coordinateSystem: 'geo',
                ...MARKER_STYLE.point,
                data: pathData.map((coord, index) => ({
                    name: `位置 ${index + 1}`,
                    value: coord
                }))
            },
            // 起点
            {
                name: '起点',
                type: 'scatter',
                coordinateSystem: 'geo',
                ...MARKER_STYLE.start,
                data: [{
                    name: '起点',
                    value: pathData[0],
                    label: {
                        show: true,
                        position: 'top',
                        formatter: '起点',
                        color: '#fff'
                    }
                }],
                zlevel: 2
            },
            // 终点
            {
                name: '终点',
                type: 'scatter',
                coordinateSystem: 'geo',
                ...MARKER_STYLE.end,
                data: [{
                    name: '终点',
                    value: pathData[pathData.length - 1],
                    label: {
                        show: true,
                        position: 'top',
                        formatter: '终点',
                        color: '#fff'
                    }
                }],
                zlevel: 2
            }
        ];
    }

    saveViewState() {
        if (this.mapChart) {
            const option = this.mapChart.getOption();
            if (option.geo && option.geo[0]) {
                this.currentZoom = option.geo[0].zoom;
                this.currentCenter = option.geo[0].center;
            }
        }
    }

    restoreViewState() {
        if (this.mapChart && this.currentZoom && this.currentCenter) {
            const option = this.mapChart.getOption();
            option.geo[0].zoom = this.currentZoom;
            option.geo.center = this.currentCenter;
            this.mapChart.setOption(option);
        }
    }

    updateGPSInfo(point) {
        Logger.debug('EchartsRenderer', '更新GPS信息:', point);
        
        const speedElement = document.getElementById('currentSpeed');
        const timeElement = document.getElementById('lastUpdateTime');
        const batteryElement = document.getElementById('batteryLevel');
        
        if (speedElement && typeof point.speed !== 'undefined') {
            const speed = point.speed || 0;
            Logger.debug('EchartsRenderer', '更新速度:', speed);
            speedElement.textContent = `${speed.toFixed(1)} km/h`;
        }
        
        if (timeElement) {
            const timestamp = point.timestamp || point.addtime;
            if (timestamp) {
                const time = new Date(timestamp * 1000);
                Logger.debug('EchartsRenderer', '更新时间:', time.toLocaleString());
                timeElement.textContent = time.toLocaleString();
            }
        }

        if (batteryElement && typeof point.battery !== 'undefined') {
            this.batteryLevel = point.battery;
            Logger.debug('EchartsRenderer', '更新电量:', this.batteryLevel);
            batteryElement.textContent = `${this.batteryLevel}%`;
            
            const batteryIcon = batteryElement.previousElementSibling;
            if (batteryIcon) {
                if (this.batteryLevel <= 20) {
                    batteryIcon.style.color = 'var(--danger-color)';
                } else if (this.batteryLevel <= 50) {
                    batteryIcon.style.color = 'var(--warning-color)';
                } else {
                    batteryIcon.style.color = 'var(--theme-color)';
                }
            }
        }
    }

    toggleDisplayMode() {
        Logger.debug('EchartsRenderer', '切换显示模式');
        this.displayMode = this.displayMode === 'path' ? 'point' : 'path';
        Logger.debug('EchartsRenderer', '新显示模式:', this.displayMode);
        this.updateMap();
    }

    calculateBounds() {
        let minLng = Infinity;
        let maxLng = -Infinity;
        let minLat = Infinity;
        let maxLat = -Infinity;

        this.gpsData.forEach(point => {
            const lng = parseFloat(point.x);
            const lat = parseFloat(point.y);
            minLng = Math.min(minLng, lng);
            maxLng = Math.max(maxLng, lng);
            minLat = Math.min(minLat, lat);
            maxLat = Math.max(maxLat, lat);
        });

        return {
            min: [minLng - 0.02, minLat - 0.02],
            max: [maxLng + 0.02, maxLat + 0.02]
        };
    }

    destroy() {
        Logger.debug('EchartsRenderer', '销毁Echarts渲染器');
        try {
            if (this.mapChart) {
                // 移除事件监听
                this.mapChart.off('georoam');
                
                // 销毁实例
                this.mapChart.dispose();
                this.mapChart = null;
            }
            
            // 清理数据
            this.gpsData = [];
            this.currentZoom = null;
            this.currentCenter = null;
            
            Logger.info('EchartsRenderer', 'Echarts渲染器销毁完成');
        } catch (error) {
            Logger.error('EchartsRenderer', '销毁Echarts渲染器失败:', error);
            throw error;
        }
    }

    // 初始化时间筛选器
    initTimeFilter() {
        Logger.debug('EchartsRenderer', '初始化时间筛选器');
        const timeRangeSelect = document.getElementById('timeRangeSelect');
        if (timeRangeSelect) {
            timeRangeSelect.value = this.timeRange;
        }
        
        // 显示/隐藏自定义时间输入框
        const customTimeContainer = document.getElementById('customTimeContainer');
        if (customTimeContainer) {
            customTimeContainer.style.display = this.timeRange === 'custom' ? 'block' : 'none';
            
            // 设置自定义时间值
            if (this.timeRange === 'custom') {
                const startInput = document.getElementById('customStartTime');
                const endInput = document.getElementById('customEndTime');
                if (startInput && this.customStartTime) {
                    startInput.value = this.customStartTime;
                }
                if (endInput && this.customEndTime) {
                    endInput.value = this.customEndTime;
                }
            }
        }
    }

    // 添加新的GPS点位
    async addNewGPSPoint(gpsData) {
        Logger.debug('EchartsRenderer', '添加新GPS点位:', gpsData);
        
        if (!this.mapChart) {
            Logger.error('EchartsRenderer', '地图实例不存在');
            return;
        }
        
        try {
            // 保存当前视图状态
            this.saveViewState();
            
            // 格式化并添加新点位
            const newPoint = {
                x: gpsData.x,
                y: gpsData.y,
                addtime: gpsData.timestamp || Math.floor(Date.now() / 1000),
                remark: gpsData.remark || '新位置',
                device: gpsData.device || 'unknown',
                speed: gpsData.speed || 0,
                battery: gpsData.battery
            };
            
            this.gpsData.push(newPoint);
            
            // 更新地图显示
            await this.updateMap();
            
            // 更新GPS信息显示
            this.updateGPSInfo(newPoint);
            
        } catch (error) {
            Logger.error('EchartsRenderer', '添加GPS点位失败:', error);
            throw error;
        }
    }

    async updateMapData(params) {
        Logger.debug('EchartsRenderer', '更新地图数据，参数:', params);
        
        try {
            // 更新GPS数据
            if (Array.isArray(params.gpsData)) {
                this.gpsData = params.gpsData;
                
                // 计算视图参数
                let viewParams = {};
                
                // 优先使用边界数据
                if (params.bounds) {
                    Logger.debug('EchartsRenderer', '使用边界数据调整视图');
                    const center = [
                        (params.bounds.min_x + params.bounds.max_x) / 2,
                        (params.bounds.min_y + params.bounds.max_y) / 2
                    ];
                    const zoom = this.calculateZoomLevel(params.bounds);
                    viewParams = { center, zoom };
                }
                // 其次使用中心点数据
                else if (params.center) {
                    Logger.debug('EchartsRenderer', '使用中心点数据调整视图');
                    viewParams = {
                        center: [params.center.x, params.center.y],
                        zoom: 8
                    };
                }

                // 更新地图显示
                const option = {
                    geo: {
                        ...this.getInitialOption().geo,
                        center: viewParams.center,
                        zoom: viewParams.zoom
                    },
                    series: this.displayMode === 'path' ? 
                        this.createPathSeries() : 
                        this.createPointSeries()
                };

                this.mapChart.setOption(option, true);  // 使用 true 强制更新
                Logger.debug('EchartsRenderer', '地图视图已更新', viewParams);
            }
        } catch (error) {
            Logger.error('EchartsRenderer', '更新地图数据失败:', error);
            throw error;
        }
    }

    // 根据边界计算合适的缩放级别
    calculateZoomLevel(bounds) {
        // 计算经纬度跨度
        const lngSpan = bounds.max_x - bounds.min_x;
        const latSpan = bounds.max_y - bounds.min_y;
        
        // 根据跨度计算合适的缩放级别
        const maxSpan = Math.max(lngSpan, latSpan);
        let zoom = 12; // 默认缩放级别
        
        if (maxSpan > 5) zoom = 5;      // 国家级
        else if (maxSpan > 2) zoom = 7;  // 省级
        else if (maxSpan > 1) zoom = 8;  // 市级
        else if (maxSpan > 0.5) zoom = 9;// 区县级
        else if (maxSpan > 0.2) zoom = 10;// 街道级
        else if (maxSpan > 0.1) zoom = 11;// 小区级
        else if (maxSpan > 0.05) zoom = 12;// 建筑级
        else zoom = 13;                   // 最详细级别
        
        return zoom;
    }
}

export default EchartsRenderer; 