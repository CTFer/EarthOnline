import Logger from '../utils/logger.js';
import { MAP_CONFIG } from '../config/config.js';

class AMapManager {
    constructor() {
        Logger.info('AMapManager', '构造函数开始');
        this.mapInstance = null;
        this.gpsData = [];
        this.playerId = localStorage.getItem('playerId') || '1';
        this.markers = new Map(); // 存储所有标记点
        this.pathLine = null;
        this.timeRange = 'today'; // 默认显示当日数据
        this.customStartTime = null;
        this.customEndTime = null;
        this.currentZoom = null;  // 保持当前缩放级别记录
        this.currentCenter = null; // 保持当前中心点记录
        this.SimpleMarker = null;  // SimpleMarker 组件引用
        this.displayMode = 'path'; // 'path' or 'point'
        this.pathSimplifier = null;
        this.pointSimplifier = null;
        this.batteryLevel = 100; // 初始化电量
        
        this.initMap();
        this.initTimeFilter();
        Logger.info('AMapManager', '构造函数完成');
    }

    async initMap() {
        Logger.info('AMapManager', 'initMap 开始');
        const container = document.getElementById('gpsMapContainer');
        if (!container) {
            Logger.error('AMapManager', 'GPS地图容器不存在');
            return;
        }

        try {
            // 初始化高德地图
            this.mapInstance = new AMap.Map(container, {
                ...MAP_CONFIG.AMAP,
                center: [116.397428, 39.90923]
            });

            // 等待地图实例完全初始化
            await new Promise(resolve => {
                this.mapInstance.on('complete', resolve);
            });

            // 加载 UI 组件
            await Promise.all([
                new Promise(resolve => {
                    AMapUI.loadUI(['overlay/SimpleMarker'], (SimpleMarker) => {
                        this.SimpleMarker = SimpleMarker;
                        resolve();
                    });
                }),
                new Promise(resolve => {
                    AMapUI.load(['ui/misc/PathSimplifier', 'ui/misc/PointSimplifier'], 
                        (PathSimplifier, PointSimplifier) => {
                            this.PathSimplifier = PathSimplifier;
                            this.PointSimplifier = PointSimplifier;
                            resolve();
                        }
                    );
                })
            ]);

            // 加载基础控件
            await new Promise(resolve => {
                AMap.plugin([
                    'AMap.Scale',
                    'AMap.ToolBar'
                ], () => {
                    this.mapInstance.addControl(new AMap.Scale());
                    this.mapInstance.addControl(new AMap.ToolBar());
                    resolve();
                });
            });

            await this.loadGPSData();
        } catch (error) {
            Logger.error('AMapManager', '初始化高德地图失败:', error);
        }
    }

    toggleDisplayMode() {
        this.displayMode = this.displayMode === 'path' ? 'point' : 'path';
        this.updateMap();
    }

    updateMap() {
        if (!this.mapInstance || !this.gpsData.length) {
            Logger.log('AMapManager', '地图实例或GPS数据不存在，跳过更新');
            return;
        }

        // 保存当前视图状态
        this.currentZoom = this.mapInstance.getZoom();
        this.currentCenter = this.mapInstance.getCenter();

        // 清除现有标记和路径
        this.clearMap();

        // 根据显示模式选择渲染方式
        if (this.displayMode === 'path') {
            this.drawPath();
        } else {
            this.drawPoints();
        }

        // 恢复之前的视图状态（如果存在）
        if (this.currentZoom && this.currentCenter) {
            this.mapInstance.setZoomAndCenter(this.currentZoom, this.currentCenter);
        } else {
            // 首次加载时才自动调整视图
            this.mapInstance.setFitView();
        }

        // 更新实时信息显示
        if (this.gpsData.length > 0) {
            const latestPoint = this.gpsData[this.gpsData.length - 1];
            this.updateGPSInfo(latestPoint);
        }
    }

    drawPath() {
        if (!this.pathSimplifier) {
            this.pathSimplifier = new this.PathSimplifier({
                map: this.mapInstance,
                getPath: (pathData) => pathData.path,
                renderOptions: {
                    pathLineStyle: {
                        strokeStyle: '#ffc447',
                        lineWidth: 6,
                        dirArrowStyle: true
                    }
                },
                progressive: true,
                progressiveThreshold: 1000
            });
        }

        const pathData = [{
            path: this.gpsData.map(point => [parseFloat(point.x), parseFloat(point.y)])
        }];

        this.pathSimplifier.setData(pathData);

        // 创建起点和终点标记
        if (this.gpsData.length > 0) {
            const startPoint = this.gpsData[0];
            const endPoint = this.gpsData[this.gpsData.length - 1];

            // 创建起点标记
            new this.SimpleMarker({
                iconLabel: 'S',
                iconTheme: 'default',
                iconStyle: 'green',
                map: this.mapInstance,
                position: [parseFloat(startPoint.x), parseFloat(startPoint.y)]
            });

            // 创建终点标记
            new this.SimpleMarker({
                iconLabel: 'E',
                iconTheme: 'default',
                iconStyle: 'red',
                map: this.mapInstance,
                position: [parseFloat(endPoint.x), parseFloat(endPoint.y)]
            });
        }
    }

    drawPoints() {
        if (!this.pointSimplifier) {
            this.pointSimplifier = new this.PointSimplifier({
                map: this.mapInstance,
                getPosition: (point) => [parseFloat(point.x), parseFloat(point.y)],
                getHoverTitle: (point, idx) => {
                    const time = new Date(point.addtime * 1000);
                    return `位置 ${idx + 1}\n${time.toLocaleString()}\n速度: ${point.speed || 0} km/h`;
                },
                renderOptions: {
                    pointStyle: {
                        width: 5,
                        height: 5,
                        fillStyle: '#ffc447'
                    },
                    pointHoverStyle: {
                        width: 8,
                        height: 8,
                        fillStyle: '#ff9900'
                    }
                },
                progressive: true,
                progressiveThreshold: 1000
            });
        }

        this.pointSimplifier.setData(this.gpsData);
    }

    clearMap() {
        // 清除标记点
        if (this.markers && this.markers.size > 0) {
            this.markers.forEach(marker => {
                marker.setMap(null);
            });
            this.markers.clear();
        }
        
        // 清除路径线
        if (this.pathLine) {
            this.mapInstance.remove(this.pathLine);
            this.pathLine = null;
        }

        // 清除 PathSimplifier 数据
        if (this.pathSimplifier) {
            this.pathSimplifier.setData([]);
        }

        // 清除 PointSimplifier 数据
        if (this.pointSimplifier) {
            this.pointSimplifier.setData([]);
        }
    }

    async loadGPSData() {
        Logger.info('AMapManager', '开始加载GPS数据');
        await this.updateMapData();
    }

    async updateMapData() {
        // 清除现有标记和路径
        this.clearMap();

        // 构建查询参数
        let params = this.buildTimeParams();

        try {
            const response = await fetch(`/api/gps/player/${this.playerId}?${params.toString()}`);
            const result = await response.json();
            
            if (result.code === 0 && result.data && result.data.records) {
                const gpsRecords = result.data.records.sort((a, b) => a.addtime - b.addtime);
                
                // 添加所有点位和路径
                gpsRecords.forEach(record => {
                    this.addNewGPSPoint(record);
                });

                // 调整视图以显示所有点
                if (this.markers.size > 0) {
                    this.mapInstance.setFitView([...this.markers.values()]);
                }
            }
        } catch (error) {
            Logger.error('AMapManager', '加载GPS数据失败:', error);
        }
    }

    // 修改添加新点位的方法
    addNewGPSPoint(gpsData) {
        
        
        if (!this.mapInstance) {
            Logger.error('AMapManager', '地图实例不存在');
            return;
        }
        
        try {
            // 保存当前视图状态
            this.currentZoom = this.mapInstance.getZoom();
            this.currentCenter = this.mapInstance.getCenter();
            
            // 添加到数据数组
            this.gpsData.push(gpsData);
            
            // 创建新标记点
            const marker = new this.SimpleMarker({
                iconLabel: `${this.gpsData.length}`,
                iconTheme: 'default',
                iconStyle: 'blue',
                map: this.mapInstance,
                position: [parseFloat(gpsData.x), parseFloat(gpsData.y)],
                showPositionPoint: false
            });

            // 添加到地图
            this.mapInstance.add(marker);
            
            // 更新标记点集合
            const pointId = Date.now().toString();
            this.markers.set(pointId, marker);

            // 更新路径线
            const path = Array.from(this.markers.values()).map(m => m.getPosition());
            if (this.pathLine) {
                this.pathLine.setPath(path);
            } else {
                this.pathLine = new AMap.Polyline({
                    path: path,
                    strokeColor: '#ffc447',
                    strokeWeight: 3,
                    strokeOpacity: 0.8,
                    showDir: true
                });
                this.mapInstance.add(this.pathLine);
            }

            // 添加信息窗体
            const infoWindow = new AMap.InfoWindow({
                content: this.createInfoWindowContent(gpsData, this.gpsData.length),
                offset: new AMap.Pixel(0, -30)
            });

            marker.on('click', () => {
                infoWindow.open(this.mapInstance, marker.getPosition());
            });

            // 恢复之前的视图状态
            if (this.currentZoom && this.currentCenter) {
                this.mapInstance.setZoomAndCenter(this.currentZoom, this.currentCenter);
            }

            // 更新实时信息显示
           
            this.updateGPSInfo(gpsData);

        } catch (error) {
            Logger.error('AMapManager', '添加GPS点位失败:', error);
        }
    }

    // 更新信息窗体内容方法，添加序号显示
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

    // 构建时间查询参数
    buildTimeParams() {
        const params = new URLSearchParams();
        const now = Date.now();

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

        return params;
    }

    // 更新GPS信息的方法
    updateGPSInfo(point) {
        Logger.debug('AMapManager', '更新GPS信息:', point);
        
        const speedElement = document.getElementById('currentSpeed');
        const timeElement = document.getElementById('lastUpdateTime');
        const batteryElement = document.getElementById('batteryLevel');
        
        if (speedElement) {
            const speed = point.speed || 0;
            Logger.debug('AMapManager', '更新速度:', speed);
            speedElement.textContent = `${speed.toFixed(1)} km/h`;
        } else {
            Logger.warn('AMapManager', '速度显示元素不存在');
        }
        
        if (timeElement) {
            const timestamp = point.addtime || point.timestamp;
            if (timestamp) {
                const time = new Date(timestamp * 1000);
                Logger.debug('AMapManager', '更新时间:', time.toLocaleString());
                timeElement.textContent = time.toLocaleString();
            }
        } else {
            Logger.warn('AMapManager', '时间显示元素不存在');
        }

        if (batteryElement && point.battery !== undefined) {
            this.batteryLevel = point.battery;
            Logger.debug('AMapManager', '更新电量:', this.batteryLevel);
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
        } else {
            Logger.debug('AMapManager', '电量显示元素不存在或数据中没有电量信息');
        }
    }

    initTimeFilter() {
        const timeSelect = document.getElementById('timeRangeSelect');
        const customDateRange = document.getElementById('customDateRange');
        const applyBtn = document.getElementById('applyCustomRange');

        timeSelect.addEventListener('change', (e) => {
            const value = e.target.value;
            this.timeRange = value;
            customDateRange.style.display = value === 'custom' ? 'flex' : 'none';
            
            if (value !== 'custom') {
                this.updateMapData();
            }
        });

        applyBtn.addEventListener('click', () => {
            const startTime = document.getElementById('startTime').value;
            const endTime = document.getElementById('endTime').value;
            
            if (startTime && endTime) {
                this.customStartTime = startTime;
                this.customEndTime = endTime;
                this.updateMapData();
            }
        });
    }
}

export default AMapManager; 