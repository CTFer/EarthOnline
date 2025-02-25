/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:10:30
 * @LastEditors: 一根鱼骨棒
 * @Description: 高德地图渲染器
 */
import Logger from "../../../utils/logger.js";
import { AMAP_CONFIG, MARKER_STYLE, PATH_STYLE } from "../../config/mapConfig.js";

class AMapRenderer {
  constructor(apiClient) {
    this.api = apiClient;
    Logger.info('AMapRenderer', 'constructor:13', '初始化高德地图渲染器');
    this.mapInstance = null;
    this.markers = new Map();
    this.pathLine = null;
    this.currentZoom = null;
    this.currentCenter = null;
    this.SimpleMarker = null;
    this.gpsData = [];
    this.batteryLevel = 100;
    this.timeRange = "today"; // 默认显示今天
    this.customStartTime = null;
    this.customEndTime = null;
    this.displayMode = "path"; // 默认为轨迹模式

    // 初始化时记录显示模式
    Logger.info("AMapRenderer", "constructor:28", "初始化显示模式: path");
  }

  async loadAMapScript() {
    Logger.debug('AMapRenderer', 'loadAMapScript:32', '加载高德地图脚本');
    if (typeof AMap === "undefined") {
      return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = `https://webapi.amap.com/maps?v=2.0&key=${AMAP_CONFIG.key}&plugin=AMap.Scale,AMap.ToolBar`;
        script.async = true;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }
  }

  async initializeMap() {
    Logger.debug('AMapRenderer', 'initializeMap:46', '初始化地图实例');
    const container = document.getElementById("gpsMapContainer");
    if (!container) {
      throw new Error("地图容器不存在");
    }

    try {
      // 使用配置初始化地图
      this.mapInstance = new AMap.Map(container, {
        ...AMAP_CONFIG,
        center: [116.397428, 39.90923], // 默认中心点
      });

      // 等待地图加载完成
      await new Promise((resolve) => {
        this.mapInstance.on("complete", resolve);
      });

      // 加载UI组件
      await this.loadUIComponents();

      // 加载控件
      await this.loadControls();

      // 初始化卫星图层
      await this.initSatelliteLayer();

      // 初始化时间筛选器
      this.initTimeFilter();

      Logger.info('AMapRenderer', 'initializeMap:76', '地图初始化完成');
    } catch (error) {
      Logger.error('AMapRenderer', 'initializeMap:78', '初始化地图失败:', error);
      throw error;
    }
  }

  async loadUIComponents() {
    Logger.debug('AMapRenderer', 'loadUIComponents:84', '加载UI组件');
    return Promise.all([
      new Promise((resolve) => {
        AMapUI.loadUI(["overlay/SimpleMarker"], (SimpleMarker) => {
          this.SimpleMarker = SimpleMarker;
          resolve();
        });
      }),
    ]);
  }

  async loadControls() {
    Logger.debug('AMapRenderer', 'loadControls:96', '加载地图控件');
    return new Promise((resolve) => {
      AMap.plugin(["AMap.Scale", "AMap.ToolBar"], () => {
        this.mapInstance.addControl(new AMap.Scale());
        this.mapInstance.addControl(new AMap.ToolBar());
        resolve();
      });
    });
  }

  /**
   * 初始化卫星图层
   * @private
   */
  async initSatelliteLayer() {
    Logger.debug('AMapRenderer', 'initSatelliteLayer:111', '初始化卫星图层');
    try {
      // 创建卫星图层
      this.satelliteLayer = new AMap.TileLayer.Satellite({
        ...AMAP_CONFIG.satellite,
      });

      // 创建路网图层
      this.roadNetLayer = new AMap.TileLayer.RoadNet({
        ...AMAP_CONFIG.roadNet,
      });

      // 根据配置添加图层
      if (AMAP_CONFIG.satellite.visible) {
        this.mapInstance.add([this.satelliteLayer]);
        if (AMAP_CONFIG.roadNet.visible) {
          this.mapInstance.add([this.roadNetLayer]);
        }
      }

      Logger.info('AMapRenderer', 'initSatelliteLayer:131', '卫星图层初始化完成');
    } catch (error) {
      Logger.error('AMapRenderer', 'initSatelliteLayer:133', '初始化卫星图层失败:', error);
      throw error;
    }
  }

  /**
   * 切换卫星图层显示状态
   * @param {boolean} showSatellite - 是否显示卫星图层
   * @param {boolean} showRoadNet - 是否显示路网图层
   */
  toggleSatelliteLayer(showSatellite, showRoadNet = true) {
    Logger.debug("AMapRenderer", "toggleSatelliteLayer:144", `切换卫星图层: satellite=${showSatellite}, roadNet=${showRoadNet}`);
    try {
      if (showSatellite) {
        this.mapInstance.add([this.satelliteLayer]);
        if (showRoadNet) {
          this.mapInstance.add([this.roadNetLayer]);
        } else {
          this.mapInstance.remove([this.roadNetLayer]);
        }
      } else {
        this.mapInstance.remove([this.satelliteLayer, this.roadNetLayer]);
      }
      Logger.info("AMapRenderer", "toggleSatelliteLayer:156", "卫星图层切换完成");
    } catch (error) {
      Logger.error("AMapRenderer", "toggleSatelliteLayer:158", "切换卫星图层失败:", error);
      throw error;
    }
  }

  /**
   * 设置卫星图层透明度
   * @param {number} opacity - 透明度值 (0-1)
   * @param {boolean} isRoadNet - 是否设置路网图层
   */
  setSatelliteLayerOpacity(opacity, isRoadNet = false) {
    Logger.debug("AMapRenderer", `设置图层透明度: ${opacity}, isRoadNet=${isRoadNet}`);
    try {
      const layer = isRoadNet ? this.roadNetLayer : this.satelliteLayer;
      if (layer) {
        layer.setOpacity(opacity);
        Logger.info("AMapRenderer", "图层透明度设置完成");
      }
    } catch (error) {
      Logger.error("AMapRenderer", "设置图层透明度失败:", error);
      throw error;
    }
  }
  // 这个方法没有使用
  async updatePosition(gpsData) {
    Logger.debug('AMapRenderer', 'updatePosition:183', '更新位置:', gpsData);
    if (!this.mapInstance) {
      Logger.error('AMapRenderer', 'updatePosition:185', '地图实例不存在');
      return;
    }

    try {
      // 保存当前视图状态
      this.saveViewState();

      // 添加到数据数组
      this.gpsData.push(gpsData);

      // 使用轨迹纠偏服务
      if (AMAP_CONFIG.GRASP_ROAD_CONFIG.enabled) {
        Logger.debug("AMapRenderer", "updatePosition:198", "使用轨迹纠偏服务");
        const graspedPath = await this.graspRoad(this.gpsData);
        // 根据显示模式更新地图
        if (this.displayMode === "point") {
          await this.updatePointMode();
        } else {
          await this.updatePathMode(graspedPath); // 使用纠偏后的路径
        }
      } else {
        // 如果未开启纠偏，直接更新路径
        Logger.debug("AMapRenderer", "updatePosition:208", "未开启轨迹纠偏");
        if (this.displayMode === "point") {
          await this.updatePointMode();
        } else {
          await this.updatePathMode(this.gpsData); // 使用原始路径
        }
      }

      // 恢复视图状态
      this.restoreViewState();

      // 更新实时信息显示
      this.updateGPSInfo(gpsData);

      Logger.debug('AMapRenderer', 'updatePosition:222', '位置更新完成');
    } catch (error) {
      Logger.error('AMapRenderer', 'updatePosition:224', '更新位置失败:', error);
      throw error;
    }
  }

  async updatePointMode() {
    Logger.debug("AMapRenderer", "更新点位显示模式");
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

  async updatePathMode(path) {
    Logger.debug('AMapRenderer', 'updatePathMode:244', '更新轨迹显示模式', path);
    
    // 确保路径数据有效
    if (!path || path.length === 0) {
        Logger.error('AMapRenderer', 'updatePathMode:248', '无效的路径数据');
        return;
    }

    try {
        // 格式化路径数据
        const formattedPath = path.map(point => {
            // 如果是GPS数据对象格式
            if (typeof point === 'object' && 'x' in point && 'y' in point) {
                return [parseFloat(point.x), parseFloat(point.y)];
            }
            // 如果已经是坐标数组格式
            else if (Array.isArray(point) && point.length === 2) {
                return [parseFloat(point[0]), parseFloat(point[1])];
            }
            // 其他情况，记录错误并返回null
            Logger.error('AMapRenderer', 'updatePathMode:264', '无效的点位数据:', point);
            return null;
        }).filter(point => point !== null); // 过滤掉无效的点

        if (formattedPath.length < 2) {
            Logger.error('AMapRenderer', 'updatePathMode:269', '有效路径点数量不足');
            return;
        }

        // 更新路径线
        if (this.pathLine) {
            this.pathLine.setPath(formattedPath); // 更新路径线的点
        } else {
            this.pathLine = new AMap.Polyline({
                path: formattedPath,
                strokeColor: PATH_STYLE.lineStyle.color,
                strokeWeight: PATH_STYLE.lineStyle.width,
                strokeOpacity: PATH_STYLE.lineStyle.opacity,
                showDir: true,
                lineJoin: PATH_STYLE.lineStyle.join,
                zIndex: 1  // 确保线在点位下方
            });
            this.mapInstance.add(this.pathLine); // 将路径线添加到地图
        }

        // 更新点的样式
        this.markers.forEach((marker, index) => {
            const isStart = index === 0;
            const isEnd = index === this.markers.size - 1;
            const content = `
                <div class="custom-marker path-mode ${isStart ? "start" : ""} ${isEnd ? "end" : ""}" style="z-index: 2;">
                    <div class="marker-label">${isStart ? "起" : isEnd ? "终" : ""}</div>
                </div>
            `;
            marker.setContent(content);
        });

        Logger.debug('AMapRenderer', 'updatePathMode', '路径更新成功，点位数量:', formattedPath.length);
    } catch (error) {
        Logger.error('AMapRenderer', 'updatePathMode', '更新路径失败:', error);
    }
  }

  toggleDisplayMode() {
    Logger.debug("AMapRenderer", "切换显示模式");
    this.displayMode = this.displayMode === "path" ? "point" : "path";

    if (this.displayMode === "point") {
      this.updatePointMode();
    } else {
      // 使用保存的GPS数据更新路径
      this.updatePathMode(this.gpsData);
    }

    Logger.info("AMapRenderer", `显示模式已切换为: ${this.displayMode}`);
  }

  async createMarker(gpsData, index) {
    Logger.debug('AMapRenderer', 'createMarker:321', '创建标记点:', { gpsData, index });

    // 创建标记点
    const marker = new AMap.Marker({
      map: this.mapInstance,
      position: [parseFloat(gpsData.x), parseFloat(gpsData.y)],
      content: "",
      offset: new AMap.Pixel(-13, -30)
    });

    // 创建信息窗体内容
    const infoContent = this.createInfoWindowContent(gpsData, index);
    // Logger.debug('AMapRenderer', 'createMarker:333', '信息窗体内容:', infoContent);

    // 添加信息窗体
    const infoWindow = new AMap.InfoWindow({
      isCustom: true, // 使用自定义窗体
      content: infoContent,
      offset: new AMap.Pixel(0, -30),
      autoMove: true,
      closeWhenClickMap: true
    });

    // 绑定点击事件
    marker.on("click", () => {
      Logger.debug('AMapRenderer', 'createMarker:346', '点击标记点，打开信息窗口');
      infoWindow.open(this.mapInstance, marker.getPosition());
    });

    // 保存到标记集合
    const pointId = Date.now().toString();
    this.markers.set(pointId, marker);

    return marker;
  }

  createMarkerContent(index) {
    const content = `
      <div class="custom-marker ${this.displayMode === "path" ? "path-mode" : "point-mode"}" style="
        background-color: #fff;
        border-radius: 50%;
        padding: 4px 8px;
        color: #333;
        font-size: 12px;
        border: 2px solid #1890ff;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 20px;
        min-height: 20px;
      ">
        <div class="marker-label" style="line-height: 1;">${index}</div>
      </div>
    `;
    Logger.debug("AMapRenderer", "createMarkerContent", `创建标记内容, 序号: ${index}`);
    return content;
  }

  createInfoWindowContent(gpsData, index) {
    // Logger.debug('AMapRenderer', 'createInfoWindowContent:366', '创建信息窗口内容，参数:', { gpsData, index });
    
    if (!gpsData || !gpsData.addtime) {
      Logger.error('AMapRenderer', 'createInfoWindowContent:369', '无效的GPS数据');
      return '';
    }

    try {
      const time = new Date(gpsData.addtime * 1000).toLocaleString();
      const content = `
        <div class="amap-info-window" style="padding: 10px; min-width: 180px; background-color: white; border-radius: 4px; box-shadow: 0 2px 6px rgba(0,0,0,0.1);">
          <h4 style="margin: 0 0 10px 0; color: #333; font-size: 14px;">${gpsData.remark || `位置 ${index}`}</h4>
          <p style="margin: 5px 0; color: #666; font-size: 12px;"><span style="color: #333;">序号:</span> ${index}</p>
          <p style="margin: 5px 0; color: #666; font-size: 12px;"><span style="color: #333;">经度:</span> ${gpsData.x}</p>
          <p style="margin: 5px 0; color: #666; font-size: 12px;"><span style="color: #333;">纬度:</span> ${gpsData.y}</p>
          <p style="margin: 5px 0; color: #666; font-size: 12px;"><span style="color: #333;">时间:</span> ${time}</p>
          ${gpsData.device ? `<p style="margin: 5px 0; color: #666; font-size: 12px;"><span style="color: #333;">设备:</span> ${gpsData.device}</p>` : ""}
        </div>
      `;
      // Logger.debug('AMapRenderer', 'createInfoWindowContent:385', '生成的内容:', content);
      return content;
    } catch (error) {
      Logger.error('AMapRenderer', 'createInfoWindowContent:388', '创建信息窗口内容失败:', error);
      return '';
    }
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
    Logger.debug("AMapRenderer", "更新GPS信息:", point);

    const speedElement = document.getElementById("currentSpeed");
    const timeElement = document.getElementById("lastUpdateTime");
    const batteryElement = document.getElementById("batteryLevel");

    if (speedElement && typeof point.speed !== "undefined") {
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

    if (batteryElement && typeof point.battery !== "undefined") {
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
      icon.style.color = "var(--danger-color)";
    } else if (this.batteryLevel <= 50) {
      icon.style.color = "var(--warning-color)";
    } else {
      icon.style.color = "var(--theme-color)";
    }
  }

  destroy() {
    Logger.info("AMapRenderer", "销毁高德地图实例");
    this.clearMap();
    if (this.satelliteLayer) {
      this.mapInstance.remove([this.satelliteLayer]);
      this.satelliteLayer = null;
    }
    if (this.roadNetLayer) {
      this.mapInstance.remove([this.roadNetLayer]);
      this.roadNetLayer = null;
    }
    if (this.mapInstance) {
      this.mapInstance.destroy();
      this.mapInstance = null;
    }
  }

  // 添加时间筛选器初始化
  initTimeFilter() {
    Logger.debug("AMapRenderer", "初始化时间筛选器");
    const timeRangeSelect = document.getElementById("timeRangeSelect");
    if (timeRangeSelect) {
      timeRangeSelect.value = this.timeRange;
    }

    // 显示/隐藏自定义时间输入框
    const customTimeContainer = document.getElementById("customTimeContainer");
    if (customTimeContainer) {
      customTimeContainer.style.display = this.timeRange === "custom" ? "block" : "none";

      // 设置自定义时间值
      if (this.timeRange === "custom") {
        const startInput = document.getElementById("customStartTime");
        const endInput = document.getElementById("customEndTime");
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
    Logger.debug("AMapRenderer", "构建时间查询参数");
    const params = new URLSearchParams();
    const now = Date.now();

    try {
      switch (this.timeRange) {
        case "today":
          params.append("start_time", Math.floor(new Date().setHours(0, 0, 0, 0) / 1000));
          params.append("end_time", Math.floor(new Date().setHours(23, 59, 59, 999) / 1000));
          break;
        case "week":
          params.append("start_time", Math.floor(now / 1000 - 7 * 24 * 60 * 60));
          params.append("end_time", Math.floor(now / 1000));
          break;
        case "month":
          params.append("start_time", Math.floor(now / 1000 - 30 * 24 * 60 * 60));
          params.append("end_time", Math.floor(now / 1000));
          break;
        case "year":
          params.append("start_time", Math.floor(now / 1000 - 365 * 24 * 60 * 60));
          params.append("end_time", Math.floor(now / 1000));
          break;
        case "custom":
          if (this.customStartTime && this.customEndTime) {
            params.append("start_time", Math.floor(new Date(this.customStartTime).getTime() / 1000));
            params.append("end_time", Math.floor(new Date(this.customEndTime).getTime() / 1000));
          }
          break;
      }

      Logger.debug("AMapRenderer", "时间参数构建完成:", params.toString());
      return params;
    } catch (error) {
      Logger.error("AMapRenderer", "构建时间参数失败:", error);
      throw error;
    }
  }

  // 更新地图数据
  async updateMapData(params) {
    Logger.debug("AMapRenderer", "更新地图数据，参数:", params);
    try {
      if (Array.isArray(params.gpsData)) {
        this.gpsData = params.gpsData;

        // 清除现有标记
        this.clearMap();

        // 添加新标记
        for (let i = 0; i < this.gpsData.length; i++) {
          await this.createMarker(this.gpsData[i], i + 1);
        }
        if (AMAP_CONFIG.GRASP_ROAD_CONFIG.enabled) {
          Logger.debug("AMapRenderer", "使用轨迹纠偏服务");
          const graspedPath = await this.graspRoad(this.gpsData);
          // 根据显示模式更新地图
          if (this.displayMode === "point") {
            await this.updatePointMode();
          } else {
            await this.updatePathMode(graspedPath);
          }
        } else {
          // 如果未开启轨迹纠偏，直接更新路径
          Logger.debug("AMapRenderer", "未开启轨迹纠偏");
          if (this.displayMode === "point") {
            await this.updatePointMode();
          } else {
            await this.updatePathMode(this.gpsData);
          }
        }

        // 调整地图视图
        if (params.bounds) {
          Logger.debug("AMapRenderer", "使用边界数据调整视图");
          const bounds = new AMap.Bounds([params.bounds.min_x, params.bounds.min_y], [params.bounds.max_x, params.bounds.max_y]);
          // 使用 setFitView 自动调整视图以显示所有标记
          this.mapInstance.setFitView([...this.markers.values()], true, [50, 50, 50, 50]);
        } else if (params.center) {
          Logger.debug("AMapRenderer", "使用中心点数据调整视图");
          this.mapInstance.setCenter([params.center.x, params.center.y]);
          this.mapInstance.setZoom(this.calculateZoomLevel(params));
        }

        Logger.debug("AMapRenderer", "地图数据更新完成");
      }
    } catch (error) {
      Logger.error("AMapRenderer", "更新地图数据失败:", error);
      throw error;
    }
  }

  // 根据数据范围计算合适的缩放级别
  calculateZoomLevel(params) {
    if (params.bounds) {
      const lngSpan = params.bounds.max_x - params.bounds.min_x;
      const latSpan = params.bounds.max_y - params.bounds.min_y;
      const maxSpan = Math.max(lngSpan, latSpan);

      if (maxSpan > 5) return 5; // 国家级
      else if (maxSpan > 2) return 7; // 省级
      else if (maxSpan > 1) return 8; // 市级
      else if (maxSpan > 0.5) return 9; // 区县级
      else if (maxSpan > 0.2) return 10; // 街道级
      else if (maxSpan > 0.1) return 11; // 小区级
      else if (maxSpan > 0.05) return 12; // 建筑级
      return 13; // 最详细级别
    }
    return 14; // 默认缩放级别
  }

  clearMap() {
    Logger.debug("AMapRenderer", "清除地图标记和路径");
    // 清除所有标记点
    this.markers.forEach((marker) => {
      marker.setMap(null);
    });
    this.markers.clear();

    // 清除路径线
    if (this.pathLine) {
      this.pathLine.setMap(null);
      this.pathLine = null;
    }
  }

  // 添加轨迹纠偏方法
  async graspRoad(gpsData) {
    Logger.debug('AMapRenderer', 'graspRoad:570', '开始轨迹纠偏');
    return new Promise((resolve, reject) => {
        // 异步加载 GraspRoad 插件
        AMap.plugin("AMap.GraspRoad", () => {
            const grasp = new AMap.GraspRoad();
            grasp.driving(gpsData, {
            }, (error, result) => {
                if (!error) {
                    resolve(result.data.points); // 返回纠偏后的轨迹
                    Logger.debug('AMapRenderer', 'graspRoad:579', '轨迹纠偏完成:', result.data.points);
                } else {
                    reject(error);
                }
            });
        });
    });
  }
}

export default AMapRenderer;
