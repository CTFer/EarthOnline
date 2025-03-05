/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 19:48:00
 * @LastEditors: 一根鱼骨棒
 * @Description: 事件管理器，负责处理所有事件监听和分发
 */
import Logger from "../../utils/logger.js";
import { TASK_EVENTS, PLAYER_EVENTS, MAP_EVENTS, UI_EVENTS, AUDIO_EVENTS, WS_EVENTS, LIVE2D_EVENTS, NOTIFICATION_EVENTS, SHOP_EVENTS, ROUTE_EVENTS } from "../config/events.js";
import { WS_EVENT_TYPES, WS_STATE } from "../config/wsConfig.js";

class EventManager {
  constructor({ eventBus, taskService, playerService, uiService, mapService, audioService, websocketService, wordcloudService, live2dService, notificationService, shopService, swiperService, router }) {
    // 事件总线
    this.eventBus = eventBus;

    // 服务注入
    this.taskService = taskService;
    this.playerService = playerService;
    this.uiService = uiService;
    this.mapService = mapService;
    this.audioService = audioService;
    this.websocketService = websocketService;
    this.wordcloudService = wordcloudService;
    this.live2dService = live2dService;
    this.notificationService = notificationService;
    this.shopService = shopService;
    this.swiperService = swiperService;
    this.router = router;

    Logger.info("EventManager", "constructor:47", "初始化事件管理器");

    this.initializeEventListeners();
  }

  /**
   * 统一的错误处理方法
   * @private
   */
  handleError(context, error, userMessage) {
    Logger.error("EventManager", "handleError", `${context}:`, error);

    // 避免重复显示错误通知
    if (!this._lastErrorTime || Date.now() - this._lastErrorTime > 2000) {
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: userMessage || "操作失败，请重试",
      });
      this.eventBus.emit(AUDIO_EVENTS.PLAY, "ERROR");
      this._lastErrorTime = Date.now();
    }
  }

  /**
   * 初始化所有事件监听
   */
  initializeEventListeners() {
    Logger.info("EventManager", "initializeEventListeners:69", "开始设置事件监听器");

    try {
      // 初始化各类事件监听
      this.initializeRouteEvents();
      this.initializeTaskEvents();
      this.initializePlayerEvents();
      this.initializeMapEvents();
      this.initializeUIEvents();
      this.initializeAudioEvents();
      this.initializeWSEvents();
      this.initializeLive2DEvents();
      this.initializeNotificationEvents();
      this.initializeShopEvents();

      // 初始化UI组件
      this.uiService.initializeMapUI();

      Logger.info("EventManager", "initializeEventListeners:85", "事件监听器设置完成");
    } catch (error) {
      this.handleError("初始化事件监听器", error, "初始化事件监听失败");
      throw error;
    }
  }

  /**
   * 初始化路由事件
   */
  initializeRouteEvents() {
    // 路由变化事件
    this.eventBus.on(ROUTE_EVENTS.CHANGED, async ({ from, to, isPopState }) => {
      Logger.info("EventManager", "initializeRouteEvents", `路由变化: ${from} -> ${to}, isPopState: ${isPopState}`);
      try {
        // 根据路由路径处理不同页面
        switch (to) {
          case "/":
            await this.handleHomeRoute();
            break;
          case "/shop":
            await this.handleShopRoute();
            break;
          default:
            Logger.warn("EventManager", "routeChanged", "未知路由:", to);
        }
      } catch (error) {
        this.handleError("路由处理", error, "页面加载失败，请刷新重试");
      }
    });

    // 路由错误事件
    this.eventBus.on(ROUTE_EVENTS.ERROR, (error) => {
      this.handleError("路由错误", error, "页面加载失败，请刷新重试");
    });
  }

  /**
   * 处理首页路由
   */
  async handleHomeRoute() {
    Logger.info('EventManager', 'handleHomeRoute 处理首页路由');
    try {
      await this.router.navigate("/");
      // 先进行清理
      await this.handleHomeCleanup();
      // 初始化首页
      await this.handleHomeInit();
      this.uiService.setupDOMObserver();
    } catch (error) {
      this.handleError("首页初始化", error, "首页加载失败，请刷新重试");
      throw error;
    }
  }

  /**
   * 处理商城路由
   */
  async handleShopRoute() {
    Logger.info("EventManager", "handleShopRoute", "处理商城路由");
    try {
      // 确保清理之前的状态
      await this.handleShopCleanup();
      // 初始化商城
      await this.handleShopInit();
    } catch (error) {
      this.handleError("商城初始化", error, "商城加载失败，请刷新重试");
      throw error;
    }
  }

  /**
   * 首页初始化处理
   */
  async handleHomeInit() {
    try {
      Logger.info("EventManager", "handleHomeInit", "开始初始化首页");

      // 1. 初始化玩家信息
      if (this.playerService) {
        await this.playerService.loadPlayerInfo();
      }

      // 2. 初始化地图服务
      if (this.mapService) {
        await this.mapService.initialize();
        this.uiService.initializeMapUI();
      }

      // 3. 初始化任务服务
      if (this.taskService) {
        if (this.taskService && this.uiService) {
          await Promise.all([
            this.taskService.loadTasks().then((tasks) => {
              this.uiService.renderTaskList(tasks);
            }),
            this.taskService.loadCurrentTasks().then((currentTasks) => {
              this.uiService.renderCurrentTasks(currentTasks);
            }),
          ]);
          Logger.info("EventManager", "[handleHomeInit]", "任务数据加载完成");
        }
      }
      this.swiperService.initSwipers();
      this.uiService.setupDOMObserver();
      // 4. 初始化词云服务
      if (this.wordcloudService) {
        await this.wordcloudService.initialize();
      }

      // 5. 初始化通知服务
      if (this.notificationService) {
        await this.notificationService.initialize();
      }

      // 6. 初始化UI服务的玩家信息
      if (this.uiService) {
        await this.uiService.initPlayerInfoUI();
      }

      // 7. 初始化Live2D
      if (this.live2dService) {
        await this.live2dService.initialize();
      } else {
        Logger.error("EventManager", "handleHomeInit", "Live2D服务未初始化");
      }

      Logger.info("EventManager", "handleHomeInit", "首页初始化完成");
    } catch (error) {
      Logger.error("EventManager", "handleHomeInit", "首页初始化失败:", error);
      this.handleError("首页初始化", error, "页面加载失败，请刷新重试");
      throw error;
    }
  }

  /**
   * 首页清理
   */
  handleHomeCleanup() {
    try {
      Logger.info("EventManager", "handleHomeCleanup", "开始清理首页");

      // 1. 清理任务相关
      if (this.uiService) {
        this.uiService.removeTaskEvents();
      }

      // 2. 清理地图相关
      if (this.mapService) {
        this.mapService.cleanup();
      }

      // 3. 清理词云相关
      if (this.wordcloudService) {
        this.wordcloudService.cleanup();
      }
      // 清理live2d
      if (this.live2dService) {
        this.live2dService.cleanup();
      }
      Logger.info("EventManager", "handleHomeCleanup", "首页清理完成");
    } catch (error) {
      Logger.error("EventManager", "handleHomeCleanup", "首页清理失败:", error);
      this.handleError("首页清理", error);
    }
  }

  // 商城初始化处理
  async handleShopInit() {
    try {
      await this.shopService.initializeShop();
      this.uiService.initShopEvents();
    } catch (error) {
      this.handleError("商城初始化", error);
    }
  }

  // 商城清理处理
  handleShopCleanup() {
    try {
      Logger.info("EventManager", "handleShopCleanup", "开始清理商城");

      // 1. 清理商城UI事件
      if (this.uiService) {
        this.uiService.removeShopEvents();
      }

      // 2. 清理商城服务
      if (this.shopService) {
        this.shopService.leaveShop();
      }

      Logger.info("EventManager", "handleShopCleanup", "商城清理完成");
    } catch (error) {
      Logger.error("EventManager", "handleShopCleanup", "商城清理失败:", error);
      this.handleError("商城清理", error);
    }
  }

  /**
   * 初始化任务相关事件
   */
  async handleTaskComplete(taskData) {
    try {
      await this.taskService.handleTaskComplete(taskData);
      this.eventBus.emit(PLAYER_EVENTS.EXP_UPDATED, {
        points: taskData.points,
        newExp: this.playerService.getPlayerData().experience,
      });
    } catch (error) {
      this.handleError("处理任务完成", error, "处理任务完成失败");
    }
  }
  /**
   * 处理任务状态更新
   */
  async handleTaskStatusUpdate(data) {
    Logger.info("EventManager", "handleTaskStatusUpdate", "处理任务状态更新:", data);
    try {
      this.uiService.updateTaskStatus(data);
    } catch (error) {
      this.handleError("任务状态更新", error, "更新任务状态失败");
    }
  }

  async handleTaskAbandon(data) {
    try {
      await this.taskService.handleTaskAbandoned(data);
    } catch (error) {
      this.handleError("任务放弃", error, "放弃任务失败");
    }
  }
  async handleTaskAccept(data) {
    try {
      await this.uiService.handleTaskAccept(data);
    } catch (error) {
      this.handleError("任务接受", error, "接受任务失败");
    }
  }

  async handleTaskAccepted(data) {
    try {
      await this.taskService.handleTaskAccepted(data);
    } catch (error) {
      this.handleError("任务接受", error, "接受任务失败");
    }
  }
  async handleTaskCompleted(data) {
    try {
      await this.wordcloudService.updateWordCloud();
    } catch (error) {
      this.handleError("处理任务完成", error, "更新文字云失败");
    }
  }

  initializeTaskEvents() {
    this.eventBus.on(TASK_EVENTS.COMPLETED, this.handleTaskCompleted.bind(this));
    this.eventBus.on(TASK_EVENTS.STATUS_UPDATED, this.handleTaskStatusUpdate.bind(this));
    this.eventBus.on(TASK_EVENTS.ABANDONED, this.handleTaskAbandon.bind(this));
    this.eventBus.on(TASK_EVENTS.ACCEPT, this.handleTaskAccept.bind(this));
    this.eventBus.on(TASK_EVENTS.ACCEPTED, this.handleTaskAccepted.bind(this));
    Logger.info("EventManager", "initializeTaskEvents:136", "任务事件监听器设置完成");
  }

  /**
   * 初始化玩家相关事件
   */
  async handlePlayerIdUpdate(newId) {
    try {
      await this.websocketService.subscribeToPlayerEvents(newId);
      await this.taskService.updatePlayerId(newId);
      await this.playerService.loadPlayerInfo();
    } catch (error) {
      this.handleError("玩家ID更新", error, "更新玩家信息失败");
    }
  }

  handlePlayerInfoUpdate(playerInfo) {
    try {
      this.playerService.handlePlayerInfoUpdate(playerInfo);
    } catch (error) {
      this.handleError("玩家信息更新", error, "更新玩家信息失败");
    }
  }

  initializePlayerEvents() {
    // 玩家相关事件监听
    // this.eventBus.on(TASK_EVENTS.COMPLETED, this.handleTaskComplete.bind(this));
    // this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, this.handlePlayerInfoUpdate.bind(this));
    Logger.info("EventManager", "initializePlayerEvents", "初始化玩家事件监听");

    // 监听玩家信息更新事件
    this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, (playerData) => {
      this.uiService.updatePlayerInfo(playerData);
    });

    // 监听经验值更新事件
    this.eventBus.on(PLAYER_EVENTS.EXP_UPDATED, (data) => {
      const playerData = this.playerService.getPlayerData();
      if (playerData) {
        this.uiService.updateLevelAndExp(playerData);
      }
    });

    Logger.info("EventManager", "initializePlayerEvents", "玩家事件监听器设置完成");
  }

  /**
   * 初始化地图相关事件
   */
  async handleGPSUpdate(data) {
    try {
      await this.mapService.handleGPSUpdate(data);
    } catch (error) {
      this.handleError("GPS更新", error, "更新GPS失败");
    }
  }

  async handleMapRendererChange(type) {
    Logger.debug("EventManager", "handleMapRendererChange:180", "处理地图渲染器切换:", type);
    try {
      // 获取当前渲染器类型
      const currentType = localStorage.getItem("mapType") || "ECHARTS";
      if (currentType === type) {
        Logger.debug("EventManager", "handleMapRendererChange:165", "地图类型相同，无需切换");
        return;
      }

      // 直接调用mapService的switchRenderer方法
      await this.mapService.switchRenderer(type);
      Logger.debug("EventManager", "handleMapRendererChange:191", "地图切换完成:", type);
    } catch (error) {
      this.handleError("地图渲染器切换", error, "切换地图渲染器失败");
    }
  }

  async handleMapDisplayModeChange() {
    try {
      const newMode = await this.mapService.handleDisplayModeSwitch();
      if (newMode) {
        this.uiService.updateDisplayModeButtonText(newMode);
      }
    } catch (error) {
      this.handleError("显示模式切换", error, "切换显示模式失败");
    }
  }

  async handleMapTimeRangeChange(range) {
    try {
      await this.mapService.handleTimeRangeChange(range);
      this.uiService.updateCustomTimeRangeVisibility();
    } catch (error) {
      this.handleError("时间范围变化", error, "更新时间范围失败");
    }
  }

  initializeMapEvents() {
    this.eventBus.on(MAP_EVENTS.GPS_UPDATED, this.handleGPSUpdate.bind(this));
    this.eventBus.on(MAP_EVENTS.RENDERER_CHANGED, this.handleMapRendererChange.bind(this));
    this.eventBus.on(MAP_EVENTS.DISPLAY_MODE_CHANGED, this.handleMapDisplayModeChange.bind(this));
    this.eventBus.on(MAP_EVENTS.TIME_RANGE_CHANGED, this.handleMapTimeRangeChange.bind(this));

    Logger.info("EventManager", "initializeMapEvents:223", "地图事件监听器设置完成");
  }

  /**
   * 初始化UI相关事件
   */
  handleNotificationShow(data) {
    try {
      this.uiService.showNotification(data);
    } catch (error) {
      this.handleError("显示通知", error, "显示通知失败");
    }
  }

  // handleModalShow(data) {
  //   try {
  //     this.uiService.showModal(data);
  //   } catch (error) {
  //     this.handleError("显示模态框", error, "显示对话框失败");
  //   }
  // }

  handleUIPlayerInfoUpdate(playerInfo) {
    try {
      this.uiService.updatePlayerInfo(playerInfo);
    } catch (error) {
      this.handleError("更新玩家信息UI", error, "更新玩家信息界面失败");
    }
  }

  initializeUIEvents() {
    // UI相关事件监听
    this.eventBus.on(UI_EVENTS.NOTIFICATION_SHOW, this.handleNotificationShow.bind(this));
    // this.eventBus.on(UI_EVENTS.MODAL_SHOW, this.handleModalShow.bind(this));

    // 地图相关UI事件

    // 玩家相关UI事件
    this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, this.handleUIPlayerInfoUpdate.bind(this));

    Logger.info("EventManager", "initializeUIEvents:266", "UI事件监听器设置完成");
  }

  /**
   * 初始化音频相关事件
   */
  handlePlaySound(soundId) {
    try {
      Logger.debug("EventManager", "handlePlaySound", `处理播放音效请求: ${soundId}`);

      // 检查音频服务状态
      if (!this.audioService.isReady()) {
        Logger.warn("EventManager", "handlePlaySound", "音频服务未就绪");
        return;
      }

      // 播放音频
      this.audioService.play(soundId).catch((error) => {
        Logger.error("EventManager", "handlePlaySound", `播放音效失败: ${soundId}`, error);
        this.handleError("播放音效", error, "播放音效失败");
      });
    } catch (error) {
      this.handleError("播放音效", error, "播放音效失败");
    }
  }

  handleStopSound(soundId) {
    try {
      Logger.debug("EventManager", "handleStopSound", `处理停止音效请求: ${soundId}`);

      // 检查音频服务状态
      if (!this.audioService.isReady()) {
        Logger.warn("EventManager", "handleStopSound", "音频服务未就绪");
        return;
      }

      // 检查音频是否正在播放
      if (!this.audioService.isPlaying(soundId)) {
        Logger.debug("EventManager", "handleStopSound", `音效未在播放: ${soundId}`);
        return;
      }

      // 停止音频
      this.audioService.stop(soundId);
    } catch (error) {
      this.handleError("停止音效", error, "停止音效失败");
    }
  }

  handleVolumeChange(data) {
    try {
      Logger.debug("EventManager", "handleVolumeChange", "处理音量变更:", data);

      // 检查音频服务状态
      if (!this.audioService.isReady()) {
        Logger.warn("EventManager", "handleVolumeChange", "音频服务未就绪");
        return;
      }

      // 设置音量
      this.audioService.setAudioVolume(data.volume, data.muted);

      // 发送通知
      if (typeof data.volume === "number") {
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
          type: "INFO",
          message: `音量已设置为 ${Math.round(data.volume * 100)}%`,
        });
      }

      if (typeof data.muted === "boolean") {
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
          type: "INFO",
          message: data.muted ? "已静音" : "已取消静音",
        });
      }
    } catch (error) {
      this.handleError("音量调节", error, "调节音量失败");
    }
  }

  handleAudioError(error) {
    Logger.error("EventManager", "handleAudioError", "音频错误:", error);
    this.handleError("音频错误", error, "音频播放出现错误");

    // 发送错误通知
    this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
      type: "ERROR",
      message: "音频播放出现错误，请刷新页面重试",
    });
  }

  handleAudioLoaded(soundId) {
    Logger.debug("EventManager", "handleAudioLoaded", `音频加载完成: ${soundId}`);

    // 发送加载完成通知
    this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
      type: "SUCCESS",
      message: "音频加载完成",
    });
  }

  handleAudioPause(soundId) {
    try {
      Logger.debug("EventManager", "handleAudioPause", `处理音频暂停请求: ${soundId}`);

      if (!this.audioService.isPlaying(soundId)) {
        return;
      }

      this.audioService.stop(soundId);
    } catch (error) {
      this.handleError("暂停音频", error, "暂停音频失败");
    }
  }

  handleAudioResume(soundId) {
    try {
      Logger.debug("EventManager", "handleAudioResume", `处理音频恢复请求: ${soundId}`);

      if (this.audioService.isPlaying(soundId)) {
        return;
      }

      this.audioService.play(soundId).catch((error) => {
        this.handleError("恢复音频", error, "恢复音频失败");
      });
    } catch (error) {
      this.handleError("恢复音频", error, "恢复音频失败");
    }
  }

  initializeAudioEvents() {
    Logger.info("EventManager", "initializeAudioEvents", "初始化音频事件监听器");

    // 基本音频控制事件
    this.eventBus.on(AUDIO_EVENTS.PLAY, this.handlePlaySound.bind(this));
    this.eventBus.on(AUDIO_EVENTS.STOP, this.handleStopSound.bind(this));
    this.eventBus.on(AUDIO_EVENTS.VOLUME_CHANGED, this.handleVolumeChange.bind(this));

    // 音频状态事件
    this.eventBus.on(AUDIO_EVENTS.ERROR, this.handleAudioError.bind(this));
    this.eventBus.on(AUDIO_EVENTS.LOADED, this.handleAudioLoaded.bind(this));
    this.eventBus.on(AUDIO_EVENTS.PAUSE, this.handleAudioPause.bind(this));
    this.eventBus.on(AUDIO_EVENTS.RESUME, this.handleAudioResume.bind(this));

    Logger.info("EventManager", "initializeAudioEvents", "音频事件监听器设置完成");
  }

  /**
   * 初始化WebSocket相关事件
   */
  initializeWSEvents() {
    // WebSocket连接状态事件
    this.eventBus.on(WS_EVENTS.CONNECTED, () => {
      this.uiService.updateWebSocketStatus("connected");
    });
    this.eventBus.on(WS_EVENTS.DISCONNECTED, () => {
      this.uiService.updateWebSocketStatus("disconnected");
    });
    this.eventBus.on(WS_EVENTS.ERROR, () => {
      this.uiService.updateWebSocketStatus("error");
    });

    Logger.info("EventManager", "initializeWSEvents:320", "WebSocket事件监听器设置完成");
  }

  /**
   * 初始化Live2D相关事件
   */
  initializeLive2DEvents() {
    // Live2D相关事件监听
    this.eventBus.on(LIVE2D_EVENTS.MODEL_LOADED, () => {
      Logger.info("EventManager", "initializeLive2DEvents:329", "Live2D模型加载完成");
    });
  }
  /**
   * 处理模型加载成功
   */
  handleModelLoaded() {
    Logger.info("Live2DService", "模型加载成功");
    // 其他处理逻辑...
  }
  /**
   * 处理模型销毁
   */
  handleModelDestroyed() {
    Logger.info("Live2DService", "模型销毁");
    // 其他处理逻辑...
  }
  /**
   * 处理新通知
   */
  handleNewNotification(data) {
    try {
      this.notificationService.addNotification(data);
    } catch (error) {
      this.handleError("处理新通知", error, "添加新通知失败");
    }
  }

  /**
   * 处理通知更新
   */
  handleNotificationUpdate(data) {
    try {
      this.notificationService.updateNotification(data);
    } catch (error) {
      this.handleError("处理通知更新", error, "更新通知失败");
    }
  }

  /**
   * 处理通知删除
   */
  handleNotificationDelete(data) {
    try {
      this.notificationService.removeNotification(data.id);
    } catch (error) {
      this.handleError("处理通知删除", error, "删除通知失败");
    }
  }

  /**
   * 初始化通知相关事件
   */
  initializeNotificationEvents() {
    if (this.notificationService) {
      this.eventBus.on(NOTIFICATION_EVENTS.NEW, this.handleNewNotification.bind(this));
      this.eventBus.on(NOTIFICATION_EVENTS.UPDATE, this.handleNotificationUpdate.bind(this));
      this.eventBus.on(NOTIFICATION_EVENTS.DELETE, this.handleNotificationDelete.bind(this));
    }
    Logger.info("EventManager", "initializeNotificationEvents:375", "通知事件监听器设置完成");
  }

  /**
   * 处理进入商城事件
   */
  handleShopEnter() {
    try {
      Logger.info("EventManager", "handleShopEnter", "处理进入商城事件");
      this.router.navigate("/shop");
    } catch (error) {
      this.handleError("进入商城", error, "进入商城失败");
    }
  }

  /**
   * 处理离开商城事件
   */
  handleShopLeave() {
    try {
      Logger.info("EventManager", "handleShopLeave", "处理离开商城事件");
      this.router.navigate("/");
    } catch (error) {
      this.handleError("离开商城", error, "离开商城失败");
    }
  }

  handleShopPurchase(data) {
    try {
      Logger.info("EventManager", "handleShopPurchase:405", "处理商品购买事件:", data);
      this.shopService.purchaseItem(data);
    } catch (error) {
      this.handleError("购买商品", error, "购买商品失败");
    }
  }

  /**
   * 初始化商城事件
   */
  initializeShopEvents() {
    if (this.shopService) {
      this.eventBus.on(SHOP_EVENTS.ENTER, this.handleShopEnter.bind(this));
      this.eventBus.on(SHOP_EVENTS.LEAVE, this.handleShopLeave.bind(this));
      this.eventBus.on(SHOP_EVENTS.PURCHASE, this.handleShopPurchase.bind(this));
    }
    Logger.info("EventManager", "initializeShopEvents", "商城事件监听器设置完成");
    // 监听商品列表更新事件
    this.eventBus.on(SHOP_EVENTS.ITEMS_UPDATED, (data) => {
      Logger.info("EventManager", "initializeShopEvents", "商品列表更新");
      this.uiService.handleShopUIUpdate(data);
    });

    // 监听购买成功事件
    this.eventBus.on(SHOP_EVENTS.PURCHASE_SUCCESS, (data) => {
      Logger.info("EventManager", "initializeShopEvents", "购买成功");
      this.uiService.showNotification({
        type: "SUCCESS",
        message: data.message || "购买成功",
      });
    });

    // 监听购买失败事件
    this.eventBus.on(SHOP_EVENTS.PURCHASE_FAILED, (data) => {
      Logger.info("EventManager", "initializeShopEvents", "购买失败");
      this.uiService.showNotification({
        type: "ERROR",
        message: data.message || "购买失败",
      });
    });
  }
}

export default EventManager;
