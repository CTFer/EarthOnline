/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:42
 * @LastEditTime: 2025-02-27 23:16:31
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:42
 * @LastEditTime: 2025-02-27 21:16:00
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
/*
 * @Author: 一根鱼骨棒
 * @Description: 地图服务管理器
 */
import Logger from "../../utils/logger.js";
import { MAP_CONFIG } from "../config/mapConfig.js";
import AMapRenderer from "./map/amapRenderer.js";

import EchartsRenderer from "./map/echartsRenderer.js";
import { MAP_EVENTS, UI_EVENTS } from "../config/events.js";
import { WS_EVENT_TYPES } from "../config/wsConfig.js";
class MapService {
  constructor(api, eventBus, uiService, playerService, store) {
    Logger.info("MapService", "constructor:23", "开始初始化地图服务");

    // 检查必要的依赖
    if (!api || !eventBus || !uiService || !playerService) {
      Logger.error("MapService", "初始化失败：缺少必要的依赖");
    }

    // 检查uiService是否为正确的实例
    if (!uiService.initializeMapUI || typeof uiService.initializeMapUI !== "function") {
      Logger.error("MapService", "初始化失败：uiService不是有效的UI服务实例");
      throw new Error("UI服务实例无效");
    }

    // 保存核心依赖
    this.api = api;
    this.eventBus = eventBus;
    this.uiService = uiService;
    this.playerService = playerService;
    this.store = store; // 确保这里有 store
    this.componentId = "mapService"; // 添加组件ID

    // 初始化默认状态
    this.defaultState = {
      renderType: localStorage.getItem("mapType") || MAP_CONFIG.RENDER_TYPE,
      timeRange: localStorage.getItem("mapTimeRange") || "today",
      customStartTime: null,
      customEndTime: null,
      displayMode: "path",
      backgroundOpacity: MAP_CONFIG.backgroundOpacity || localStorage.getItem("mapBackgroundOpacity"),
      isInitialized: false,
    };

    // 从store获取保存的状态或使用默认状态
    this.state = this.loadState();

    // 初始化其他属性
    this.currentRenderer = null;
    this.wsManager = null;
    this._isToggling = false;

    // 绑定方法
    this.handleDisplayModeSwitch = this.handleDisplayModeSwitch.bind(this);
    this.handleMapSwitch = this.handleMapSwitch.bind(this);
    this.handleTimeRangeChange = this.handleTimeRangeChange.bind(this);
    this.handleGPSUpdate = this.handleGPSUpdate.bind(this);

    Logger.info("MapService", "constructor:70", "地图服务初始化完成");
  }

  // 加载状态
  loadState() {
    try {
      const savedState = this.store?.getComponentState(this.componentId);
      return { ...this.defaultState, ...savedState };
    } catch (error) {
      Logger.warn("MapService", "从Store加载状态失败，使用默认状态", error);
      return { ...this.defaultState };
    }
  }

  // 保存状态
  saveState() {
    try {
      if (this.store) {
        const stateToSave = {
          renderType: this.state.renderType,
          timeRange: this.state.timeRange,
          customStartTime: this.state.customStartTime,
          customEndTime: this.state.customEndTime,
          displayMode: this.currentRenderer?.displayMode || "path",
          backgroundOpacity: this.state.backgroundOpacity,
          isInitialized: this.state.isInitialized,
        };
        this.store.setComponentState(this.componentId, stateToSave);
        Logger.debug("MapService", "状态保存成功", stateToSave);
      }
    } catch (error) {
      Logger.error("MapService", "保存状态失败:", error);
    }
  }

  // 更新状态
  updateState(partialState) {
    this.state = { ...this.state, ...partialState };
    this.saveState();
  }

  async initMap() {
    if (this.state.isInitialized) {
      Logger.info("MapService", "initMap:79", "地图已经初始化，跳过初始化过程");
      return;
    }

    Logger.info("MapService", "initMap:76", "开始初始化地图");

    try {
      // 初始化地图UI组件
      Logger.info("MapService", "initMap:82", "初始化地图UI组件");
      await this.initializeUI();

      // 再次确认时间范围设置
      Logger.debug("MapService", "确认时间范围设置");
      if (!this.state.timeRange) {
        this.state.timeRange = "today";
        localStorage.setItem("mapTimeRange", "today");
        Logger.debug("MapService", "重新设置默认时间范围: today");
      }
      Logger.debug("MapService", "当前时间范围:", this.state.timeRange);

      // 从localStorage获取渲染器类型
      const rendererType = localStorage.getItem("mapType") || "ECHARTS";
      Logger.info("MapService", "从localStorage获取渲染器类型:", rendererType);

      // 初始化渲染器
      await this.initRenderer(rendererType);
      Logger.info("MapService", "地图渲染器初始化完成");

      // 在渲染器初始化完成后更新显示模式按钮文本
      this.updateDisplayModeButtonText();

      // 更新地图数据
      Logger.debug("MapService", "initMap:112", "开始更新地图数据，时间范围:", this.state.timeRange);
      await this.updateMapData();

      this.updateState({ isInitialized: true });
      Logger.info("MapService", "initMap:116", "地图初始化完成");
    } catch (error) {
      Logger.error("MapService", "initMap:118", "地图初始化失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "地图初始化失败: " + error.message,
        duration: 5000,
      });

      // 如果初始化失败，尝试使用Echarts作为后备方案
      if (!this.currentRenderer) {
        Logger.warn("MapService", "initMap:127", "尝试使用Echarts作为后备渲染器");
        try {
          await this.initRenderer("ECHARTS");
          await this.updateMapData();
        } catch (backupError) {
          Logger.error("MapService", "initMap:132", "后备渲染器初始化也失败了:", backupError);
        }
      }
    }

    Logger.info("MapService", "initMap:137", "地图初始化完成");
  }

  /**
   * 初始化地图UI组件
   */
  async initializeUI() {
    if (!this.uiService) {
      Logger.error("MapService", "uiService未初始化");
      throw new Error("uiService未初始化");
    }

    try {
      await this.uiService.initializeMapUI();
      Logger.info("MapService", "地图UI组件初始化完成");
    } catch (error) {
      Logger.error("MapService", "initializeUI:146", "初始化地图UI组件失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "初始化地图UI组件失败",
      });
      throw error; // 继续抛出错误以便上层处理
    }
  }

  initTimeRangeSelector() {
    Logger.debug("MapService", "初始化时间范围选择器");
    const timeRangeSelect = document.getElementById("timeRangeSelect");

    if (!timeRangeSelect) {
      Logger.warn("MapService", "找不到时间范围选择器");
      return;
    }

    try {
      // 从localStorage获取保存的时间范围
      const savedTimeRange = localStorage.getItem("mapTimeRange");
      if (savedTimeRange) {
        timeRangeSelect.value = savedTimeRange;
        this.state.timeRange = savedTimeRange;
        Logger.debug("MapService", `设置时间范围选择器值为: ${savedTimeRange}`);
      }

      // 添加change事件监听
      timeRangeSelect.addEventListener("change", (e) => {
        const newValue = e.target.value;
        Logger.debug("MapService", `时间范围变更为: ${newValue}`);
        this.eventBus.emit(MAP_EVENTS.TIME_RANGE_CHANGED, newValue);
      });

      // 初始化自定义时间范围的显示状态
      this.updateCustomTimeRangeVisibility();
    } catch (error) {
      Logger.error("MapService", "初始化时间范围选择器失败:", error);
    }
  }

  initCustomTimeRange() {
    const startInput = document.getElementById("startTime");
    const endInput = document.getElementById("endTime");
    const applyButton = document.getElementById("applyCustomRange");

    if (startInput && endInput) {
      if (this.state.timeRange === "custom" && this.state.customStartTime && this.state.customEndTime) {
        startInput.value = this.state.customStartTime;
        endInput.value = this.state.customEndTime;
      }

      startInput.addEventListener("change", () => {
        this.state.customStartTime = startInput.value;
      });

      endInput.addEventListener("change", () => {
        this.state.customEndTime = endInput.value;
      });

      if (applyButton) {
        applyButton.addEventListener("click", () => {
          if (!this.validateTimeRange(startInput.value, endInput.value)) {
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
              type: "WARNING",
              message: "请选择有效的时间范围",
            });
            return;
          }

          this.state.customStartTime = startInput.value;
          this.state.customEndTime = endInput.value;
          this.updateMapData();
        });
      }
    }

    this.updateCustomTimeRangeVisibility();
  }

  initDisplayModeButton() {
    Logger.debug("MapService", "初始化显示模式切换按钮");
    const displayModeSwitchBtn = document.getElementById("switchDisplayMode");
    if (!displayModeSwitchBtn) {
      Logger.warn("MapService", "找不到显示模式切换按钮");
      return;
    }

    // 如果已经有绑定的处理函数，先移除
    if (displayModeSwitchBtn._handleClick) {
      displayModeSwitchBtn.removeEventListener("click", displayModeSwitchBtn._handleClick);
    }

    // 使用已绑定到实例的方法
    displayModeSwitchBtn.addEventListener("click", this.handleDisplayModeSwitch);
    displayModeSwitchBtn._handleClick = this.handleDisplayModeSwitch;
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
    const displayModeSwitchBtn = document.getElementById("switchDisplayMode");
    if (!displayModeSwitchBtn) {
      Logger.warn("MapService", "找不到显示模式切换按钮，无法更新文本");
      return;
    }

    try {
      const buttonText = displayModeSwitchBtn.querySelector("span") || displayModeSwitchBtn;
      // 获取当前显示模式
      Logger.debug("MapService", "获取currentRenderer:", this.currentRenderer);
      Logger.debug("MapService", "获取当前显示模式:", this.currentRenderer?.displayMode);
      const currentMode = this.currentRenderer?.displayMode || "path";
      // 根据当前模式设置目标模式
      const targetMode = currentMode === "point" ? "轨迹" : "点位";
      buttonText.textContent = `切换到${targetMode}显示`;
      displayModeSwitchBtn.dataset.mode = currentMode;
      Logger.debug("MapService", `更新显示模式按钮文本为: ${buttonText.textContent}, 当前模式: ${currentMode}`);
    } catch (error) {
      Logger.error("MapService", "更新显示模式按钮文本失败:", error);
    }
  }

  updateCustomTimeRangeVisibility() {
    const customDateRange = document.getElementById("customDateRange");
    if (customDateRange) {
      customDateRange.style.display = this.state.timeRange === "custom" ? "block" : "none";
    }
  }

  async handleTimeRangeChange(range) {
    Logger.debug("MapService", "handleTimeRangeChange", "处理时间范围变化:", range);
    try {
      this.updateState({ timeRange: range });

      if (range === "custom") {
        if (!this.state.customStartTime || !this.state.customEndTime) {
          this.setDefaultCustomTimeRange();
        }
        return;
      }

      await this.updateMapData();
    } catch (error) {
      Logger.error("MapService", "handleTimeRangeChange", "更新时间范围失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "更新时间范围失败",
      });
    }
  }

  setDefaultCustomTimeRange() {
    const now = new Date();
    const startTime = new Date(now.setHours(0, 0, 0, 0));
    const endTime = new Date(now.setHours(23, 59, 59, 999));

    this.state.customStartTime = startTime.toISOString().slice(0, 16);
    this.state.customEndTime = endTime.toISOString().slice(0, 16);

    const startInput = document.getElementById("startTime");
    const endInput = document.getElementById("endTime");

    if (startInput) startInput.value = this.state.customStartTime;
    if (endInput) endInput.value = this.state.customEndTime;
  }

  validateGPSData(data) {
    if (!data || typeof data !== "object") return false;
    if (!data.latitude || !data.longitude) return false;
    if (typeof data.latitude !== "number" || typeof data.longitude !== "number") return false;
    return true;
  }

  async handleMapSwitch(type) {
    Logger.debug("MapService", "handleMapSwitch:328", "切换地图类型:", type);
    // 确保从 localStorage 获取当前渲染器类型
    const currentRenderType = localStorage.getItem("mapType");
    // 判断当前渲染器类型是否为ECHARTS 是则切换为AMAP 否则切换为ECHARTS
    Logger.debug("MapService", "currentRenderType:", currentRenderType);
    if (currentRenderType === "ECHARTS") {
      this.state.renderType = "AMAP";
    } else {
      this.state.renderType = "ECHARTS";
    }
    Logger.debug("MapService", "收到地图切换请求:", type);
    try {
      this.switchRenderer(type).catch((error) => {
        Logger.error("MapService", "handleMapSwitch:341", "切换地图失败:", error);
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
          type: "ERROR",
          message: "地图切换失败",
        });

        this.switchRenderer(this.state.renderType);
      });
    } catch (error) {
      Logger.error("MapService", "处理地图切换请求失败:", error);
    }
  }

  handleDisplayModeSwitch(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }

    Logger.debug("MapService", "handleDisplayModeSwitch", "切换显示模式");
    try {
      if (this._isToggling) {
        return;
      }

      this._isToggling = true;

      if (this.currentRenderer && typeof this.currentRenderer.toggleDisplayMode === "function") {
        const previousMode = this.currentRenderer.displayMode;
        this.currentRenderer.toggleDisplayMode();
        const newMode = this.currentRenderer.displayMode;

        // 保存新的显示模式
        this.updateState({ displayMode: newMode });

        Logger.debug("MapService", `显示模式从 ${previousMode} 切换到 ${newMode}`);
        this.updateDisplayModeButtonText();
      } else {
        Logger.warn("MapService", "当前渲染器不支持切换显示模式");
      }
    } catch (error) {
      Logger.error("MapService", "handleDisplayModeSwitch", "切换显示模式失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "切换显示模式失败",
      });
    } finally {
      // 确保在操作完成后重置标志
      setTimeout(() => {
        this._isToggling = false;
      }, 100);
    }
  }

  /**
   * 初始化渲染器（仅在首次加载时使用）
   * @private
   */
  async initRenderer(type) {
    Logger.debug("MapService", "initRenderer:380", "初始化渲染器:", type);

    try {
      // 如果没有指定类型，从localStorage获取，默认为ECHARTS
      const renderType = type || localStorage.getItem("mapType") || "ECHARTS";
      // 转换为大写以确保一致性
      const normalizedType = renderType.toUpperCase();

      Logger.debug("MapService", `使用渲染器类型: ${normalizedType}`);

      // 清理现有渲染器
      if (this.currentRenderer) {
        this.currentRenderer.destroy();
        this.currentRenderer = null;
      }

      // 根据类型创建新的渲染器
      switch (normalizedType) {
        case "AMAP":
          this.currentRenderer = new AMapRenderer(this.api);
          await this.currentRenderer.loadAMapScript();
          break;
        case "ECHARTS":
          this.currentRenderer = new EchartsRenderer(this.api);
          break;
        default:
          Logger.warn("MapService", `未知的渲染器类型: ${normalizedType}，使用默认的Echarts渲染器`);
          this.currentRenderer = new EchartsRenderer(this.api);
      }

      // 初始化渲染器
      await this.currentRenderer.initializeMap();

      // 更新本地存储
      localStorage.setItem("mapType", normalizedType);

      // 设置初始透明度
      this.setBackgroundOpacity(this.state.backgroundOpacity);
      Logger.debug("MapService", "设置初始透明度:", this.state.backgroundOpacity);

      Logger.info("MapService", `地图渲染器(${normalizedType})初始化完成`);

      // 触发渲染器变更事件
      this.eventBus.emit(MAP_EVENTS.RENDERER_CHANGED, normalizedType);

      return normalizedType;
    } catch (error) {
      Logger.error("MapService", "initRenderer:427", "初始化渲染器失败:", error);
      throw error;
    }
  }

  /**
   * 切换地图渲染器（用于用户手动切换）
   */
  async switchRenderer(type) {
    Logger.debug("MapService", "switchRenderer:436", "切换渲染器:", type);

    // 确保从 localStorage 获取当前渲染器类型
    const currentRenderType = localStorage.getItem("mapType") || this.state.renderType;

    // 如果类型相同，直接返回
    if (currentRenderType === type) {
      Logger.debug("MapService", "地图类型相同，无需切换");
      return;
    }

    Logger.info("MapService", `切换地图渲染器: ${type}`);
    try {
      // 清理现有渲染器
      if (this.currentRenderer) {
        Logger.debug("MapService", "清理现有渲染器");
        await this.currentRenderer.destroy();
      }

      // 更新存储的渲染器类型
      this.state.renderType = type;
      localStorage.setItem("mapType", type);

      // 初始化新渲染器
      await this.initRenderer(type);

      // 更新地图数据
      await this.updateMapData();

      // 切换成功后发送通知
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "SUCCESS",
        message: "地图切换成功",
      });

      Logger.info("MapService", "地图渲染器切换完成");
    } catch (error) {
      Logger.error("MapService", "switchRenderer:473", "切换渲染器失败:", error);
      // 切换失败时回退到Echarts
      if (type === "AMAP") {
        Logger.warn("MapService", "切换到高德地图失败，回退到Echarts");
        this.state.renderType = "ECHARTS";
        localStorage.setItem("mapType", "ECHARTS");
        await this.initRenderer("ECHARTS");
      }
      throw error;
    }
  }

  // 设置WebSocket管理器
  setWebSocketManager(wsManager) {
    Logger.info("MapService", "设置WebSocket管理器");

    if (!wsManager || !wsManager.socket) {
      Logger.error("MapService", "WebSocket管理器无效或未初始化");
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "WARNING",
        message: "GPS实时更新功能可能不可用",
      });
      return;
    }

    this.wsManager = wsManager;

    try {
      // 使用新的订阅方法
      this.wsManager.subscribe(WS_EVENT_TYPES.BUSINESS.GPS_UPDATE, (data) => {
        Logger.debug("MapService", "handleGPSUpdate:505", "处理GPS更新:", data);
        this.handleGPSUpdate(data);
      });

      Logger.info("MapService", "GPS更新处理器设置成功");
    } catch (error) {
      Logger.error("MapService", "GPS更新处理器设置失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "GPS更新功能初始化失败",
      });
    }
  }

  handleGPSUpdate(data) {
    if (!data || typeof data !== "object") {
      Logger.warn("MapService", "收到无效的GPS数据:", data);
      return;
    }

    try {
      // 更新地图上的GPS点位
      this.currentRenderer?.updateGPSPoint(data);

      // 触发GPS更新事件
      this.eventBus.emit(MAP_EVENTS.GPS_UPDATED, data);

      Logger.debug("MapService", "GPS数据更新成功");
    } catch (error) {
      Logger.error("MapService", "handleGPSUpdate:534", "处理GPS更新失败:", error);
    }
  }

  // 更新地图数据
  async updateMapData() {
    Logger.debug("MapService", "updateMapData:540", "更新地图数据");

    // 检查渲染器是否已初始化
    if (!this.currentRenderer) {
      Logger.warn("MapService", "渲染器未初始化，无法更新地图数据");
      return;
    }

    // 验证时间范围
    if (!this.state.timeRange) {
      Logger.warn("MapService", "时间范围未设置，使用默认值: today");
      this.state.timeRange = "today";
      localStorage.setItem("mapTimeRange", "today");
    }
    Logger.debug("MapService", `当前时间范围: ${this.state.timeRange}`);

    const playerId = this.playerService.getPlayerId();
    if (!playerId) {
      Logger.error("MapService", "无法更新地图数据: 未找到玩家ID");
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "无法更新地图数据: 未找到玩家ID",
        duration: 5000,
      });
      return;
    }

    try {
      Logger.debug("MapService", `准备获取GPS数据，时间范围: ${this.state.timeRange}, 玩家ID: ${playerId}`);
      const params = new URLSearchParams();
      const now = Date.now();
      let startTime, endTime;

      // 计算时间范围
      switch (this.state.timeRange) {
        case "today":
          startTime = Math.floor(new Date().setHours(0, 0, 0, 0) / 1000);
          endTime = Math.floor(new Date().setHours(23, 59, 59, 999) / 1000);
          Logger.debug("MapService", `今日时间范围: ${new Date(startTime * 1000).toLocaleString()} - ${new Date(endTime * 1000).toLocaleString()}`);
          break;
        case "week":
          startTime = Math.floor(now / 1000 - 7 * 24 * 60 * 60);
          endTime = Math.floor(now / 1000);
          break;
        case "month":
          startTime = Math.floor(now / 1000 - 30 * 24 * 60 * 60);
          endTime = Math.floor(now / 1000);
          break;
        case "year":
          startTime = Math.floor(now / 1000 - 365 * 24 * 60 * 60);
          endTime = Math.floor(now / 1000);
          break;
        case "custom":
          if (this.state.customStartTime && this.state.customEndTime) {
            startTime = Math.floor(new Date(this.state.customStartTime).getTime() / 1000);
            endTime = Math.floor(new Date(this.state.customEndTime).getTime() / 1000);
          } else {
            Logger.warn("MapService", "自定义时间范围未设置，使用今天作为默认值");
            startTime = Math.floor(new Date().setHours(0, 0, 0, 0) / 1000);
            endTime = Math.floor(new Date().setHours(23, 59, 59, 999) / 1000);
          }
          break;
        default:
          Logger.error("MapService", `不支持的时间范围类型: ${JSON.stringify(this.state.timeRange, null, 2)}`);
          this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
            type: "ERROR",
            message: `不支持的时间范围: ${this.state.timeRange}，已重置为today`,
            duration: 5000,
          });
          this.state.timeRange = "today";
          localStorage.setItem("mapTimeRange", "today");
          startTime = Math.floor(new Date().setHours(0, 0, 0, 0) / 1000);
          endTime = Math.floor(new Date().setHours(23, 59, 59, 999) / 1000);
      }

      // 验证时间参数
      if (!Number.isInteger(startTime) || !Number.isInteger(endTime)) {
        throw new Error(`时间参数无效: startTime=${startTime}, endTime=${endTime}`);
      }

      Logger.debug("MapService", `发起GPS数据请求，开始时间: ${new Date(startTime * 1000).toLocaleString()}, 结束时间: ${new Date(endTime * 1000).toLocaleString()}`);

      params.append("start_time", startTime);
      params.append("end_time", endTime);

      // 使用API获取GPS数据
      const result = await this.api.getGPSData(playerId, params);

      if (result.code === 0 && result.data) {
        Logger.debug("MapService", `获取到 ${result.data.records?.length || 0} 条GPS记录`);

        if (!Array.isArray(result.data.records)) {
          throw new Error("GPS数据格式无效");
        }

        // 更新渲染器数据
        await this.currentRenderer.updateMapData({
          timeRange: this.state.timeRange,
          startTime: startTime,
          endTime: endTime,
          gpsData: result.data.records.sort((a, b) => a.addtime - b.addtime),
          center: result.data.center || null,
          bounds: result.data.bounds || null,
        });

        Logger.info("MapService", "地图数据更新完成");
      } else {
        throw new Error(result.msg || "获取GPS数据失败");
      }
    } catch (error) {
      Logger.error("MapService", "updateMapData:650", "更新地图数据失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: `更新地图数据失败: ${error.message}`,
        duration: 5000,
      });
    }
  }

  destroy() {
    Logger.info("MapService", "destroy:660", "开始销毁地图服务");

    // 移除显示模式切换按钮的事件监听器
    const displayModeSwitchBtn = document.getElementById("switchDisplayMode");
    if (displayModeSwitchBtn && displayModeSwitchBtn._handleClick) {
      displayModeSwitchBtn.removeEventListener("click", displayModeSwitchBtn._handleClick);
      delete displayModeSwitchBtn._handleClick;
    }

    // 取消事件订阅
    this.eventBus.off(MAP_EVENTS.GPS_UPDATED, this.handleGPSUpdate);
    this.eventBus.off(MAP_EVENTS.RENDERER_CHANGED, this.handleMapSwitch);
    this.eventBus.off(MAP_EVENTS.DISPLAY_MODE_CHANGED, this.handleDisplayModeSwitch);
    this.eventBus.off(MAP_EVENTS.TIME_RANGE_CHANGED, this.handleTimeRangeChange);

    // 销毁当前渲染器
    if (this.currentRenderer) {
      this.currentRenderer.destroy();
    }

    Logger.info("MapService", "地图服务销毁完成");
  }

  /**
   * 设置地图整体透明度
   * @param {number} opacity - 透明度值 (0-1)
   */
  setBackgroundOpacity(opacity) {
    Logger.debug("MapService", `设置地图透明度: ${opacity}`);

    try {
      // 更新地图容器透明度
      const container = document.querySelector(".gps-map-container");
      if (container) {
        container.style.opacity = opacity;
      }

      // 保存到本地存储
      localStorage.setItem("mapBackgroundOpacity", opacity.toString());
    } catch (error) {
      Logger.error("MapService", "设置地图透明度失败:", error);
    }
  }

  /**
   * 初始化地图服务
   */
  async initialize() {
    if (!this.store) {
        Logger.error("MapService", "initialize", "store 未定义");
        throw new Error("store 未定义");
    }
    Logger.info("MapService", "initialize", "初始化地图服务");
    try {
      // 从保存的状态恢复
      if (this.state.isInitialized) {
        Logger.info("MapService", "initialize", "从保存的状态恢复地图");
        await this.restoreFromState();
      } else {
        // 首次初始化
        await this.initMap();
        this.updateState({ isInitialized: true });
      }

      // 从状态中恢复时间范围
      const timeRange = this.store.getComponentState(this.componentId).timeRange || "today";
      this.setTimeRangeSelect(timeRange);

      Logger.info("MapService", "initialize", "地图服务初始化完成");
    } catch (error) {
      Logger.error("MapService", "initialize", "地图服务初始化失败:", error);
      throw error;
    }
  }
  /**
   * 设置时间范围选择器
   * @param {string} timeRange - 时间范围
   */
  setTimeRangeSelect(timeRange) {
    // 设置选择器timeRangeSelect的显示
    const timeRangeSelect = document.getElementById("timeRangeSelect");
    if (timeRangeSelect) {
      timeRangeSelect.value = timeRange;
    }
  }
  /**
   * 清理地图服务
   */
  cleanup() {
    Logger.info("MapService", "cleanup", "清理地图服务");
    try {
      // 保存当前状态
      this.saveState();

      // 销毁地图实例
      if (this.currentRenderer) {
        this.currentRenderer.destroy();
        this.currentRenderer = null;
      }

      Logger.info("MapService", "cleanup", "地图服务清理完成");
    } catch (error) {
      Logger.error("MapService", "cleanup", "地图服务清理失败:", error);
      throw error;
    }
  }

  // 从状态恢复
  async restoreFromState() {
    try {
      // 初始化渲染器
      await this.initRenderer(this.state.renderType);

      // 恢复显示模式
      if (this.currentRenderer && this.state.displayMode) {
        this.currentRenderer.displayMode = this.state.displayMode;
        this.updateDisplayModeButtonText();
      }

      // 恢复时间范围
      this.state.timeRange = this.state.timeRange;
      if (this.state.timeRange === "custom") {
        this.state.customStartTime = this.state.customStartTime;
        this.state.customEndTime = this.state.customEndTime;
      }

      // 恢复透明度
      this.setBackgroundOpacity(this.state.backgroundOpacity);

      // 更新地图数据
      await this.updateMapData();

      Logger.info("MapService", "restoreFromState", "地图状态恢复完成");
    } catch (error) {
      Logger.error("MapService", "restoreFromState", "恢复地图状态失败:", error);
      throw error;
    }
  }

  // ... 其他地图相关方法
}

export default MapService;
