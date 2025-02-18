import Logger from '../utils/logger.js';
import { MAP_CONFIG } from '../config/config.js';
// 已弃用
class GPSManager {
    constructor() {
        Logger.info('GPSManager', '初始化开始');
        this.mapChart = null;
        this.gpsData = [];
        this.playerId = localStorage.getItem('playerId') || '1';
        this.timeRange = 'today'; // 默认显示当日数据
        this.customStartTime = null;
        this.customEndTime = null;
        this.currentZoom = null;  // 添加当前缩放级别记录
        this.currentCenter = null; // 添加当前中心点记录
        this.batteryLevel = 100; // 初始化电量
        this.displayMode = 'path'; // 添加显示模式属性，默认为路径模式
        this.initMap();
        this.initTimeFilter();
        Logger.info('GPSManager', '初始化完成');
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

    async updateMapData() {
        let params = new URLSearchParams();
        
        switch (this.timeRange) {
            case 'today':
                params.append('start_time', Math.floor(new Date().setHours(0,0,0,0) / 1000));
                params.append('end_time', Math.floor(new Date().setHours(23,59,59,999) / 1000));
                break;
            case 'week':
                params.append('start_time', Math.floor(Date.now() / 1000 - 7 * 24 * 60 * 60));
                params.append('end_time', Math.floor(Date.now() / 1000));
                break;
            case 'month':
                params.append('start_time', Math.floor(Date.now() / 1000 - 30 * 24 * 60 * 60));
                params.append('end_time', Math.floor(Date.now() / 1000));
                break;
            case 'year':
                params.append('start_time', Math.floor(Date.now() / 1000 - 365 * 24 * 60 * 60));
                params.append('end_time', Math.floor(Date.now() / 1000));
                break;
            case 'custom':
                if (this.customStartTime && this.customEndTime) {
                    params.append('start_time', Math.floor(new Date(this.customStartTime).getTime() / 1000));
                    params.append('end_time', Math.floor(new Date(this.customEndTime).getTime() / 1000));
                }
                break;
        }

        try {
            // 修改为使用get_player_gps接口
            const response = await fetch(`/api/gps/player/${this.playerId}?${params.toString()}`);
            const result = await response.json();
            
            if (result.code === 0 && result.data && result.data.records) {
                this.gpsData = result.data.records.sort((a, b) => a.addtime - b.addtime);
                Logger.debug('GPSManager', '加载的GPS数据:', this.gpsData);
                this.updateMap();
            } else {
                Logger.error('GPSManager', '加载GPS数据失败:', result.msg);
            }
        } catch (error) {
            Logger.error('GPSManager', '加载GPS数据失败:', error);
        }
    }

    // 修改loadGPSData方法以使用新的updateMapData
    async loadGPSData() {
        await this.updateMapData();
    }

    async initMap() {
        Logger.info('GPSManager', 'initMap 开始');
        const container = document.getElementById('gpsMapContainer');
        if (!container) {
            Logger.error('GPSManager', 'GPS地图容器不存在');
            return;
        }

        // 初始化地图
        this.mapChart = echarts.init(container);
        
        // 加载中国地图数据
        try {
            const chinaMapResponse = await fetch('/static/js/china.json');
            const chinaJson = await chinaMapResponse.json();
            echarts.registerMap('china', chinaJson);

            // 初始化地图配置
            const option = {
                backgroundColor: 'transparent',
                geo: {
                    map: 'china',
                    roam: true,
                    label: {
                        show: true,
                        color: '#8aa2c1',
                        fontSize: 10
                    },
                    itemStyle: {
                        areaColor: '#15273f',
                        borderColor: '#1e3148',
                        borderWidth: 1
                    },
                    emphasis: {
                        itemStyle: {
                            areaColor: '#2a4a7c'
                        }
                    }
                },
                series: [{
                    name: 'GPS点',
                    type: 'scatter',  // 改用普通scatter而不是effectScatter
                    coordinateSystem: 'geo',
                    data: [],
                    symbol: 'pin',    // 使用大头针样式的标记
                    symbolSize: 20,   // 调整标记大小
                    label: {
                        show: true,
                        position: 'top',
                        formatter: '{b}',
                        color: '#fff'
                    },
                    itemStyle: {
                        color: '#ffc447'
                    }
                }]
            };

            this.mapChart.setOption(option);
            await this.loadGPSData();

        } catch (error) {
            Logger.error('GPSManager', '初始化地图失败:', error);
        }

        // 添加地图视图变化事件监听
        this.mapChart.on('georoam', () => {
            const option = this.mapChart.getOption();
            if (option.geo && option.geo[0]) {
                this.currentZoom = option.geo[0].zoom;
                this.currentCenter = option.geo[0].center;
            }
        });
        Logger.debug('GPSManager', 'GPSManager初始化地图完成');
    }

    // 计算GPS点的边界范围
    calculateBounds(gpsPoints) {
        let minLng = Infinity;
        let maxLng = -Infinity;
        let minLat = Infinity;
        let maxLat = -Infinity;

        gpsPoints.forEach(point => {
            const lng = parseFloat(point.x);
            const lat = parseFloat(point.y);
            minLng = Math.min(minLng, lng);
            maxLng = Math.max(maxLng, lng);
            minLat = Math.min(minLat, lat);
            maxLat = Math.max(maxLat, lat);
        });

        // 添加边距，使显示更加合适
        const padding = 0.02; // 可以调整这个值来改变边距大小
        return {
            min: [minLng - padding, minLat - padding],
            max: [maxLng + padding, maxLat + padding]
        };
    }

    // 根据边界范围计算地图中心点和缩放级别
    calculateView(bounds) {
        const center = [
            (bounds.min[0] + bounds.max[0]) / 2,
            (bounds.min[1] + bounds.max[1]) / 2
        ];

        // 计算合适的缩放级别
        const lngDiff = bounds.max[0] - bounds.min[0];
        const latDiff = bounds.max[1] - bounds.min[1];
        const maxDiff = Math.max(lngDiff, latDiff);
        
        // 更细致的缩放级别划分
        let zoom = 200;  // 默认非常大的缩放级别
        if (maxDiff > 0.0001) zoom = 160;  // 约10米范围
        if (maxDiff > 0.001) zoom = 120;   // 约100米范围
        if (maxDiff > 0.005) zoom = 80;    // 约500米范围
        if (maxDiff > 0.01) zoom = 40;     // 约1公里范围
        if (maxDiff > 0.05) zoom = 20;     // 约5公里范围
        if (maxDiff > 0.1) zoom = 10;      // 约10公里范围
        if (maxDiff > 0.5) zoom = 5;       // 更大范围

        return { center, zoom };
    }

    updateMap() {
        Logger.debug('GPSManager', '开始更新地图');

        if (!this.mapChart || !this.gpsData.length) {
            Logger.warn('GPSManager', '无地图实例或GPS数据为空');
            return;
        }

        try {
            // 保存当前视图状态
            const option = this.mapChart.getOption();
            if (option.geo && option.geo[0]) {
                this.currentZoom = option.geo[0].zoom;
                this.currentCenter = option.geo[0].center;
            }

            // 根据显示模式选择渲染方式
            const series = this.displayMode === 'path' ? 
                this.createPathSeries() : 
                this.createPointSeries();

            // 更新地图配置
            const mapOption = {
                backgroundColor: 'transparent',
                geo: {
                    map: 'china',
                    roam: true,
                    label: {
                        show: true,
                        color: '#8aa2c1',
                        fontSize: 10
                    },
                    itemStyle: {
                        areaColor: '#15273f',
                        borderColor: '#1e3148',
                        borderWidth: 1
                    },
                    emphasis: {
                        itemStyle: {
                            areaColor: '#2a4a7c'
                        }
                    }
                },
                series: series
            };

            // 恢复视图状态
            if (this.currentZoom && this.currentCenter) {
                mapOption.geo.zoom = this.currentZoom;
                mapOption.geo.center = this.currentCenter;
            }

            this.mapChart.setOption(mapOption);
            Logger.debug('GPSManager', '地图更新成功');

        } catch (error) {
            Logger.error('GPSManager', '更新地图失败:', error);
        }
    }

    // 创建路径显示的系列配置
    createPathSeries() {
        const pathData = this.gpsData.map(point => [parseFloat(point.x), parseFloat(point.y)]);
        
        return [
            // 路径线
            {
                name: '路径',
                type: 'lines',
                coordinateSystem: 'geo',
                data: [{
                    coords: pathData
                }],
                lineStyle: {
                    color: '#ffc447',
                    width: 2,
                    opacity: 0.8,
                    curveness: 0
                },
                effect: {
                    show: true,
                    period: 6,
                    trailLength: 0.7,
                    color: '#fff',
                    symbolSize: 3
                }
            },
            // 起点标记
            {
                name: '起点',
                type: 'scatter',
                coordinateSystem: 'geo',
                data: [{
                    name: '起点',
                    value: pathData[0],
                    symbol: 'circle',
                    symbolSize: 12,
                    itemStyle: {
                        color: '#4CAF50'
                    },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: 'S',
                        color: '#fff'
                    }
                }]
            },
            // 终点标记
            {
                name: '终点',
                type: 'scatter',
                coordinateSystem: 'geo',
                data: [{
                    name: '终点',
                    value: pathData[pathData.length - 1],
                    symbol: 'pin',
                    symbolSize: 12,
                    itemStyle: {
                        color: '#F44336'
                    },
                    label: {
                        show: true,
                        position: 'top',
                        formatter: 'E',
                        color: '#fff'
                    }
                }]
            }
        ];
    }

    // 创建点位显示的系列配置
    createPointSeries() {
        return [{
            name: 'GPS点',
            type: 'scatter',
            coordinateSystem: 'geo',
            data: this.gpsData.map((point, index) => ({
                name: `位置 ${index + 1}`,
                value: [parseFloat(point.x), parseFloat(point.y)],
                time: new Date(point.addtime * 1000).toLocaleString(),
                speed: point.speed || 0,
                symbolSize: 8,
                itemStyle: {
                    color: '#ffc447'
                }
            })),
            label: {
                show: true,
                position: 'top',
                formatter: (params) => `${params.dataIndex + 1}`,
                color: '#fff',
                backgroundColor: '#1e3148',
                padding: [2, 4],
                borderRadius: 2
            },
            emphasis: {
                itemStyle: {
                    color: '#ff9900',
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    formatter: (params) => {
                        return [
                            `位置 ${params.dataIndex + 1}`,
                            `时间: ${params.data.time}`,
                            `速度: ${params.data.speed.toFixed(1)} km/h`
                        ].join('\n');
                    }
                }
            }
        }];
    }

    // 修改 addNewGPSPoint 方法，添加详细调试信息
    addNewGPSPoint(gpsData) {
        Logger.debug('GPSManager', '添加新GPS点位:', gpsData);
        
        if (!this.mapChart) {
            Logger.error('GPSManager', '地图实例不存在');
            return;
        }
        
        try {


            // 保存当前视图状态
            const option = this.mapChart.getOption();
            if (option.geo && option.geo[0]) {
                this.currentZoom = option.geo[0].zoom;
                this.currentCenter = option.geo[0].center;
            }
            
            // 添加到现有数据中
            const newPoint = {
                x: gpsData.x,
                y: gpsData.y,
                addtime: gpsData.timestamp || Math.floor(Date.now() / 1000),
                remark: gpsData.remark || '新位置',
                device: gpsData.device || 'unknown',
                speed: gpsData.speed || 0,
                battery: gpsData.battery
            };
            
            Logger.debug('GPSManager', '格式化的新点位数据:', newPoint);

            this.gpsData.push(newPoint);

            // 立即更新地图显示
            this.updateMap();
            
            // 更新实时信息显示
            Logger.debug('GPSManager', '更新GPS信息显示');
            this.updateGPSInfo(gpsData);

        } catch (error) {
            Logger.error('GPSManager', '添加GPS点位失败:', error);
        }
    }

    // 修改 updateGPSInfo 方法，优化状态更新逻辑
    updateGPSInfo(point) {
        Logger.debug('GPSManager', '更新GPS信息:', point);
        
        const speedElement = document.getElementById('currentSpeed');
        const timeElement = document.getElementById('lastUpdateTime');
        const batteryElement = document.getElementById('batteryLevel');
        
        // 更新速度（如果有）
        if (speedElement && typeof point.speed !== 'undefined') {
            const speed = point.speed || 0;
            Logger.debug('GPSManager', '更新速度:', speed);
            speedElement.textContent = `${speed.toFixed(1)} km/h`;
        }
        
        // 更新时间（优先使用 timestamp）
        if (timeElement) {
            const timestamp = point.timestamp || point.addtime;
            if (timestamp) {
                const time = new Date(timestamp * 1000);
                Logger.debug('GPSManager', '更新时间:', time.toLocaleString());
                timeElement.textContent = time.toLocaleString();
            }
        }

        // 更新电量（如果有）
        if (batteryElement && typeof point.battery !== 'undefined') {
            this.batteryLevel = point.battery;
            Logger.debug('GPSManager', '更新电量:', this.batteryLevel);
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

    // 添加切换显示模式的方法
    toggleDisplayMode() {
        Logger.debug('GPSManager', '切换显示模式');
        this.displayMode = this.displayMode === 'path' ? 'point' : 'path';
        Logger.debug('GPSManager', '新显示模式:', this.displayMode);
        this.updateMap();
    }

    destroy() {
        Logger.debug('GPSManager', '销毁地图实例');
        if (this.mapChart) {
            this.mapChart.dispose();
            this.mapChart = null;
        }
        // 清理其他资源
        this.gpsData = [];
        this.currentZoom = null;
        this.currentCenter = null;
    }
}

export default GPSManager; 