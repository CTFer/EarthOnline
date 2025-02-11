class MapSwitcher {
    constructor() {
        console.log('[MapSwitcher Debug] 初始化开始');
        this.currentMapType = localStorage.getItem('mapType') || MAP_CONFIG.RENDER_TYPE;
        this.mapInstance = null;
        this.timeRange = 'today';
        this.customStartTime = null;
        this.customEndTime = null;
        
        // WebSocket 管理器引用
        this.wsManager = null;
        
        console.log('[MapSwitcher Debug] 当前地图类型:', this.currentMapType);
        // 确保脚本加载完成后再初始化
        this.initializeMap();
    }

    async initializeMap() {
        try {
            console.log('[Debug] MapSwitcher 初始化开始');
            
            // 等待DOM加载完成
            await this.waitForDOM();
            
            // 如果是高德地图，确保相关脚本加载完成
            if (this.currentMapType === 'AMAP') {
                await this.loadAMapScripts();
            }
            
            // 初始化切换按钮事件
            this.initSwitchButton();
            // 初始化地图
            await this.initMap();
            
            console.log('[Debug] MapSwitcher 初始化完成');
        } catch (error) {
            console.error('地图初始化失败:', error);
            layui.layer.msg('地图加载失败，请刷新页面重试');
        }
    }

    // 等待DOM元素加载
    async waitForDOM() {
        return new Promise(resolve => {
            const checkDOM = () => {
                const mapControls = document.querySelector('.map-controls');
                const switchMapBtn = document.getElementById('switchMapType');
                const switchDisplayBtn = document.getElementById('switchDisplayMode');
                
                if (mapControls && switchMapBtn && switchDisplayBtn) {
                    console.log('[MapSwitcher Debug] DOM元素已加载');
                    resolve();
                } else {
                    console.log('[MapSwitcher Debug] 等待DOM元素加载...');
                    setTimeout(checkDOM, 100);
                }
            };
            checkDOM();
        });
    }

    async loadAMapScripts() {
        if (typeof AMap === 'undefined') {
            await new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = "https://webapi.amap.com/maps?v=2.0&key=16de1da59d44d6967f9a6bf5248963c5&plugin=AMap.Scale,AMap.ToolBar";
                script.async = true;
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
    }

    initSwitchButton() {
        console.log('[MapSwitcher Debug] 初始化切换按钮');
        const switchMapBtn = document.getElementById('switchMapType');
        const switchDisplayBtn = document.getElementById('switchDisplayMode');

        if (!switchMapBtn || !switchDisplayBtn) {
            console.error('[MapSwitcher Debug] 找不到切换按钮:', {
                switchMapBtn: !!switchMapBtn,
                switchDisplayBtn: !!switchDisplayBtn
            });
            return;
        }

        // 更新初始按钮文本
        const mapTypeText = switchMapBtn.querySelector('.map-type-text');
        if (mapTypeText) {
            this.updateSwitchButtonText(mapTypeText);
        }

        // 地图类型切换
        switchMapBtn.addEventListener('click', async (e) => {
            console.log('[MapSwitcher Debug] 切换按钮被点击');
            e.preventDefault(); // 防止事件冒泡
            
            // 切换地图类型
            this.currentMapType = this.currentMapType === 'AMAP' ? 'ECHARTS' : 'AMAP';
            console.log('[MapSwitcher Debug] 新地图类型:', this.currentMapType);
            localStorage.setItem('mapType', this.currentMapType);
            
            // 更新按钮文本
            if (mapTypeText) {
                this.updateSwitchButtonText(mapTypeText);
            }
            
            // 重新初始化地图
            await this.initMap();
        });

        // 显示模式切换
        switchDisplayBtn.addEventListener('click', (e) => {
            console.log('[MapSwitcher Debug] 显示模式切换按钮被点击');
            e.preventDefault(); // 防止事件冒泡
            
            if (this.mapInstance && typeof this.mapInstance.toggleDisplayMode === 'function') {
                console.log('[MapSwitcher Debug] 切换显示模式');
                this.mapInstance.toggleDisplayMode();
            } else {
                console.warn('[MapSwitcher Debug] 无法切换显示模式:', {
                    hasInstance: !!this.mapInstance,
                    hasToggleFunction: !!(this.mapInstance && this.mapInstance.toggleDisplayMode),
                    currentType: this.currentMapType
                });
            }
        });
    }

    updateSwitchButtonText(element) {
        const text = this.currentMapType === 'AMAP' ? 'Echarts' : '高德';
        console.log('[MapSwitcher Debug] 更新按钮文本为:', `切换至${text}地图`);
        element.textContent = `切换至${text}地图`;
    }

    async initMap() {
        // 保存当前的时间范围设置
        if (this.mapInstance) {
            this.timeRange = this.mapInstance.timeRange;
            this.customStartTime = this.mapInstance.customStartTime;
            this.customEndTime = this.mapInstance.customEndTime;
        }

        // 清除现有地图
        if (this.mapInstance && typeof this.mapInstance.destroy === 'function') {
            await this.mapInstance.destroy();
        }
        const container = document.getElementById('gpsMapContainer');
        if (container) {
            container.innerHTML = '';
        }

        try {
            // 根据类型初始化相应的地图
            if (this.currentMapType === 'AMAP') {
                const { default: AMapManager } = await import('./AMapManager.js');
                this.mapInstance = new AMapManager();
            } else {
                const { default: GPSManager } = await import('./GPSManager.js');
                this.mapInstance = new GPSManager();
                
                // 为 GPSManager 特别处理：确保 echarts 实例正确初始化
                await new Promise(resolve => setTimeout(resolve, 100));
                if (this.mapInstance.mapChart) {
                    this.mapInstance.mapChart.resize();
                }
            }

            // 恢复时间范围设置
            if (this.timeRange) {
                this.mapInstance.timeRange = this.timeRange;
                this.mapInstance.customStartTime = this.customStartTime;
                this.mapInstance.customEndTime = this.customEndTime;
                await this.mapInstance.updateMapData();
            }

            // 设置 WebSocket 管理器
            if (this.wsManager) {
                this.setWebSocketManager(this.wsManager);
            }

        } catch (error) {
            console.error('初始化地图失败:', error);
            layui.layer.msg('切换地图失败，请刷新页面重试');
        }
    }

    // 设置 WebSocket 管理器
    setWebSocketManager(wsManager) {
        console.log('[MapSwitcher Debug] 设置WebSocket管理器');
        this.wsManager = wsManager;
        if (this.mapInstance) {
            console.log('[MapSwitcher Debug] 注册GPS更新处理器');
            this.wsManager.onGPSUpdate((data) => {
                console.log('[MapSwitcher Debug] 收到GPS更新:', data);
                this.handleGPSUpdate(data);
            });
        }
    }

    // 处理 GPS 更新
    handleGPSUpdate(data) {
        if (!this.mapInstance || !data) {
            console.warn('[MapSwitcher Debug] GPS更新处理失败:', {
                hasInstance: !!this.mapInstance,
                hasData: !!data
            });
            return;
        }

        console.log('[MapSwitcher Debug] 处理GPS更新:', data);
        
        // 检查是否只是状态更新（无坐标）
        if (!data.x || !data.y) {
            console.log('[MapSwitcher Debug] 仅状态更新，无需添加新点位');
            // 只更新状态信息
            if (typeof this.mapInstance.updateGPSInfo === 'function') {
                this.mapInstance.updateGPSInfo(data);
            } else {
                console.warn('[MapSwitcher Debug] 地图实例不支持状态更新');
            }
            return;
        }

        // 有坐标信息时，添加新点位
        this.mapInstance.addNewGPSPoint(data);
    }
}

export default MapSwitcher; 