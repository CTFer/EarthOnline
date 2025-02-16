/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:10:30
 * @LastEditors: 一根鱼骨棒
 * @Description: 高德地图渲染器
 */
import Logger from '../../../utils/logger.js';
import { MAP_CONFIG } from '../../../config/config.js';

class AMapRenderer {
    constructor(apiClient) {
        this.api = apiClient;
        Logger.info('AMapRenderer', '初始化高德地图渲染器');
        this.mapInstance = null;
        this.markers = new Map();
        this.pathLine = null;
        this.currentZoom = null;
        this.currentCenter = null;
        this.SimpleMarker = null;
        this.gpsData = [];
        this.batteryLevel = 100;
        this.timeRange = 'today';  // 默认显示今天
        this.customStartTime = null;
        this.customEndTime = null;
        this.displayMode = 'path'; // 默认为轨迹模式
    }

    async loadAMapScript() {
        Logger.debug('AMapRenderer', '加载高德地图脚本');
        if (typeof AMap === 'undefined') {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = `https://webapi.amap.com/maps?v=2.0&key=${MAP_CONFIG.AMAP.key}&plugin=AMap.Scale,AMap.ToolBar`;
                script.async = true;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
    }

    async initializeMap() {
        Logger.debug('AMapRenderer', '初始化地图实例');
        const container = document.getElementById('gpsMapContainer');
        if (!container) {
            throw new Error('地图容器不存在');
        }

        try {
            // 初始化地图
            this.mapInstance = new AMap.Map(container, {
                ...MAP_CONFIG.AMAP,
                center: [116.397428, 39.90923]
            });

            // 等待地图加载完成
            await new Promise(resolve => {
                this.mapInstance.on('complete', resolve);
            });

            // 加载UI组件
            await this.loadUIComponents();
            
            // 加载控件
            await this.loadControls();

            // 初始化时间筛选器
            this.initTimeFilter();

            Logger.info('AMapRenderer', '地图初始化完成');
        } catch (error) {
            Logger.error('AMapRenderer', '初始化地图失败:', error);
            throw error;
        }
    }

    async loadUIComponents() {
        Logger.debug('AMapRenderer', '加载UI组件');
        return Promise.all([
            new Promise(resolve => {
                AMapUI.loadUI(['overlay/SimpleMarker'], SimpleMarker => {
                    this.SimpleMarker = SimpleMarker;
                    resolve();
                });
            })
        ]);
    }

    async loadControls() {
        Logger.debug('AMapRenderer', '加载地图控件');
        return new Promise(resolve => {
            AMap.plugin(['AMap.Scale', 'AMap.ToolBar'], () => {
                this.mapInstance.addControl(new AMap.Scale());
                this.mapInstance.addControl(new AMap.ToolBar());
                resolve();
            });
        });
    }

    async updatePosition(gpsData) {
        Logger.debug('AMapRenderer', '更新位置:', gpsData);
        if (!this.mapInstance) {
            Logger.error('AMapRenderer', '地图实例不存在');
            return;
        }

        try {
            // 保存当前视图状态
            this.saveViewState();
            
            // 添加到数据数组
            this.gpsData.push(gpsData);
            
            // 根据显示模式更新地图
            if (this.displayMode === 'point') {
                await this.updatePointMode();
            } else {
                await this.updatePathMode();
            }
            
            // 恢复视图状态
            this.restoreViewState();
            
            // 更新实时信息显示
            this.updateGPSInfo(gpsData);
            
            Logger.debug('AMapRenderer', '位置更新完成');
        } catch (error) {
            Logger.error('AMapRenderer', '更新位置失败:', error);
            throw error;
        }
    }

    async updatePointMode() {
        Logger.debug('AMapRenderer', '更新点位显示模式');
        // 清除现有路径线
        if (this.pathLine) {
            this.pathLine.setMap(null);
            this.pathLine = null;
        }
        
        // 更新所有点的样式
        this.markers.forEach((marker, index) => {
            marker.setContent(this.createMarkerContent(index + 1));
        });
    }

    async updatePathMode() {
        Logger.debug('AMapRenderer', '更新轨迹显示模式');
        const path = Array.from(this.markers.values()).map(m => m.getPosition());
        
        // 更新或创建路径线
        if (this.pathLine) {
            this.pathLine.setPath(path);
        } else {
            this.pathLine = new AMap.Polyline({
                path: path,
                strokeColor: '#ffc447',
                strokeWeight: 3,
                strokeOpacity: 0.8,
                showDir: true,
                lineJoin: 'round'
            });
            this.mapInstance.add(this.pathLine);
        }
        
        // 更新点的样式
        this.markers.forEach((marker, index) => {
            const isStart = index === 0;
            const isEnd = index === this.markers.size - 1;
            const content = `
                <div class="custom-marker path-mode ${isStart ? 'start' : ''} ${isEnd ? 'end' : ''}">
                    <div class="marker-label">${isStart ? '起' : (isEnd ? '终' : '')}</div>
                </div>
            `;
            marker.setContent(content);
        });
    }

    toggleDisplayMode() {
        Logger.debug('AMapRenderer', '切换显示模式');
        this.displayMode = this.displayMode === 'path' ? 'point' : 'path';
        
        if (this.displayMode === 'point') {
            this.updatePointMode();
        } else {
            this.updatePathMode();
        }
        
        Logger.info('AMapRenderer', `显示模式已切换为: ${this.displayMode}`);
    }

    async createMarker(gpsData, index) {
        Logger.debug('AMapRenderer', '创建标记点:', index);
        
        // 创建标记点
        const marker = new AMap.Marker({
            map: this.mapInstance,
            position: [parseFloat(gpsData.x), parseFloat(gpsData.y)],
            content: this.createMarkerContent(index),
            offset: new AMap.Pixel(-13, -30)
        });

        // 添加信息窗体
        const infoWindow = new AMap.InfoWindow({
            content: this.createInfoWindowContent(gpsData, index),
            offset: new AMap.Pixel(0, -30)
        });

        marker.on('click', () => {
            infoWindow.open(this.mapInstance, marker.getPosition());
        });

        // 保存到标记集合
        const pointId = Date.now().toString();
        this.markers.set(pointId, marker);

        return marker;
    }

    createMarkerContent(index) {
        return `
            <div class="custom-marker ${this.displayMode === 'path' ? 'path-mode' : 'point-mode'}">
                <div class="marker-label">${index}</div>
            </div>
        `;
    }

    createInfoWindowContent(gpsData, index) {
        const time = new Date(gpsData.addtime * 1000).toLocaleString();
        return `
            <div class="amap-info-window">
                <h4>${gpsData.remark || `位置 ${index}`}</h4>
                <p>序号: ${index}</p>
                <p>经度: ${gpsData.x}</p>
                <p>纬度: ${gpsData.y}</p>
                <p>时间: ${time}</p>
                ${gpsData.device ? `<p>设备: ${gpsData.device}</p>` : ''}
            </div>
        `;
    }

    saveViewState() {
        if (this.mapInstance) {
            this.currentZoom = this.mapInstance.getZoom();
            this.currentCenter = this.mapInstance.getCenter();
        }
    }

    restoreViewState() {
        if (this.mapInstance && this.currentZoom && this.currentCenter) {
            this.mapInstance.setZoomAndCenter(this.currentZoom, this.currentCenter);
        }
    }

    updateGPSInfo(point) {
        Logger.debug('AMapRenderer', '更新GPS信息:', point);
        
        const speedElement = document.getElementById('currentSpeed');
        const timeElement = document.getElementById('lastUpdateTime');
        const batteryElement = document.getElementById('batteryLevel');
        
        if (speedElement && typeof point.speed !== 'undefined') {
            const speed = point.speed || 0;
            speedElement.textContent = `${speed.toFixed(1)} km/h`;
        }
        
        if (timeElement) {
            const timestamp = point.timestamp || point.addtime;
            if (timestamp) {
                const time = new Date(timestamp * 1000);
                timeElement.textContent = time.toLocaleString();
            }
        }

        if (batteryElement && typeof point.battery !== 'undefined') {
            this.batteryLevel = point.battery;
            batteryElement.textContent = `${this.batteryLevel}%`;
            
            const batteryIcon = batteryElement.previousElementSibling;
            if (batteryIcon) {
                this.updateBatteryIcon(batteryIcon);
            }
        }
    }

    updateBatteryIcon(icon) {
        if (this.batteryLevel <= 20) {
            icon.style.color = 'var(--danger-color)';
        } else if (this.batteryLevel <= 50) {
            icon.style.color = 'var(--warning-color)';
        } else {
            icon.style.color = 'var(--theme-color)';
        }
    }

    destroy() {
        Logger.info('AMapRenderer', '销毁高德地图实例');
        this.clearMap();
        if (this.mapInstance) {
            this.mapInstance.destroy();
            this.mapInstance = null;
        }
    }

    // 添加时间筛选器初始化
    initTimeFilter() {
        Logger.debug('AMapRenderer', '初始化时间筛选器');
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

    // 构建时间查询参数
    buildTimeParams() {
        Logger.debug('AMapRenderer', '构建时间查询参数');
        const params = new URLSearchParams();
        const now = Date.now();

        try {
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
            
            Logger.debug('AMapRenderer', '时间参数构建完成:', params.toString());
            return params;
        } catch (error) {
            Logger.error('AMapRenderer', '构建时间参数失败:', error);
            throw error;
        }
    }

    // 更新地图数据
    async updateMapData(params) {
        Logger.debug('AMapRenderer', '更新地图数据，参数:', params);
        try {
            if (Array.isArray(params.gpsData)) {
                this.gpsData = params.gpsData;
                
                // 清除现有标记
                this.clearMap();
                
                // 添加新标记
                for (let i = 0; i < this.gpsData.length; i++) {
                    await this.createMarker(this.gpsData[i], i + 1);
                }
                
                // 根据显示模式更新地图
                if (this.displayMode === 'point') {
                    await this.updatePointMode();
                } else {
                    await this.updatePathMode();
                }

                // 调整地图视图
                if (params.bounds) {
                    Logger.debug('AMapRenderer', '使用边界数据调整视图');
                    const bounds = new AMap.Bounds(
                        [params.bounds.min_x, params.bounds.min_y],
                        [params.bounds.max_x, params.bounds.max_y]
                    );
                    // 使用 setFitView 自动调整视图以显示所有标记
                    this.mapInstance.setFitView([...this.markers.values()], true, [50, 50, 50, 50]);
                }
                else if (params.center) {
                    Logger.debug('AMapRenderer', '使用中心点数据调整视图');
                    this.mapInstance.setCenter([params.center.x, params.center.y]);
                    this.mapInstance.setZoom(this.calculateZoomLevel(params));
                }
                
                Logger.debug('AMapRenderer', '地图数据更新完成');
            }
        } catch (error) {
            Logger.error('AMapRenderer', '更新地图数据失败:', error);
            throw error;
        }
    }

    // 根据数据范围计算合适的缩放级别
    calculateZoomLevel(params) {
        if (params.bounds) {
            const lngSpan = params.bounds.max_x - params.bounds.min_x;
            const latSpan = params.bounds.max_y - params.bounds.min_y;
            const maxSpan = Math.max(lngSpan, latSpan);
            
            if (maxSpan > 5) return 5;       // 国家级
            else if (maxSpan > 2) return 7;   // 省级
            else if (maxSpan > 1) return 8;   // 市级
            else if (maxSpan > 0.5) return 9; // 区县级
            else if (maxSpan > 0.2) return 10;// 街道级
            else if (maxSpan > 0.1) return 11;// 小区级
            else if (maxSpan > 0.05) return 12;// 建筑级
            return 13;                        // 最详细级别
        }
        return 14; // 默认缩放级别
    }

    clearMap() {
        Logger.debug('AMapRenderer', '清除地图标记和路径');
        // 清除所有标记点
        this.markers.forEach(marker => {
            marker.setMap(null);
        });
        this.markers.clear();
        
        // 清除路径线
        if (this.pathLine) {
            this.pathLine.setMap(null);
            this.pathLine = null;
        }
    }
}

export default AMapRenderer; 