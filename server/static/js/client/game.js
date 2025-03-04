/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-29 16:43:22
 * @LastEditTime: 2025-03-04 13:46:26
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import { SERVER, ICP, MPS, WEBNAME } from "../config/config.js";
import APIClient from "./core/api.js";
import TemplateService from "./service/templateService.js";
import TaskService from "./service/taskService.js";
import EventBus from "./core/eventBus.js";
import Store from "./core/store.js";
import Logger from "../utils/logger.js";
import SwiperService from "./service/swiperService.js";
import { ErrorHandler } from "./core/errorHandler.js";
import WordcloudService from "./service/wordcloudService.js";
import PlayerService from "./service/playerService.js";
import NFCService from "./service/nfcService.js";
import MapService from "./service/mapService.js";
import UIService from "./service/uiService.js";
import AudioService from "./service/audioService.js";
import Live2DService from "./service/live2dService.js";
import WebSocketService from "./service/websocketService.js";
import { gameUtils } from "../utils/utils.js";
import { TASK_EVENTS, PLAYER_EVENTS, MAP_EVENTS, UI_EVENTS, WS_EVENTS, AUDIO_EVENTS, LIVE2D_EVENTS, SHOP_EVENTS, ROUTE_EVENTS } from "./config/events.js";
import EventManager from "./core/eventManager.js";
import Router from "./core/router.js";
import ShopService from "./service/shopService.js";

// 在文件开头声明全局变量
let taskManager;

// 游戏管理类，程序入口
class GameManager {
  constructor() {
    Logger.info("GameManager", "constructor:37", "开始初始化游戏管理器");

    // 确保核心组件最先初始化
    // this.eventBus = new EventBus();
    // this.store = new Store();
    // this.api = new APIClient(SERVER);

    this.initialized = false;
    this.initializationPromise = null;

    Logger.info("GameManager", "constructor:47", "核心组件初始化完成");

    try {
      // 0. 设置页面标题
      gameUtils.setPageTitle(WEBNAME);
      // 1. 初始化核心组件
      this.initializeCoreComponents();

      // 2. 初始化基础属性
      this.initializeBaseProperties();

      // 4. 初始化服务
      this.initializeServices()
        .then(() => {
          Logger.info("GameManager", "initializeServices:62", "游戏管理器初始化完成");
          this.initialized = true;
        })
        .catch((error) => {
          Logger.error("GameManager", "initializeServices:66", "游戏管理器初始化失败:", error);
          layer.msg("初始化失败，请刷新页面重试", { icon: 2 });
        });
    } catch (error) {
      Logger.error("GameManager", "constructor:70", "游戏管理器初始化失败:", error);
      layer.msg("初始化失败，请刷新页面重试", { icon: 2 });
      throw error;
    }

  }

  // 初始化核心组件
  async initializeCoreComponents() {
    Logger.info("GameManager", "initializeCoreComponents:78", "初始化核心组件");

    try {
      // 初始化API客户端
      this.api = new APIClient(SERVER);

      // 初始化事件总线
      this.eventBus = new EventBus();

      // 初始化数据存储
      this.store = new Store();

      Logger.info("GameManager", "initializeCoreComponents:90", "核心组件初始化完成");
    } catch (error) {
      Logger.error("GameManager", "initializeCoreComponents:92", "核心组件初始化失败:", error);
      throw error;
    }
  }

  // 初始化服务
  async initializeServices() {
    Logger.info("GameManager", "[initializeServices:99]", "初始化服务组件");

    try {
      // 1. 初始化基础服务（无依赖）
      this.templateService = new TemplateService(this.api, this.eventBus, this.store);

      // 2. 初始化路由（优先处理，加载必要的DOM）
      this.router = new Router(this.eventBus);
      await this.router.initialize();

      // 3. 等待DOM完全加载
      await new Promise((resolve) => {
        const checkDom = () => {
          const container = document.querySelector(".game-container");
          if (container && container.children.length > 0) {
            resolve();
          } else {
            setTimeout(checkDom, 100);
          }
        };
        checkDom();
      });

      // 4. 处理路由，确保在DOM加载完成后再处理
      // await this.router.handleRoute(window.location.pathname);

      Logger.info("GameManager", "[initializeServices:120]", "DOM加载完成");

      // 5. 初始化WebSocket服务（依赖：eventBus）
      this.websocketService = new WebSocketService(this.eventBus);
      await this.websocketService.initialize();

      // 6. 初始化玩家服务（依赖：api, eventBus, store）
      this.playerService = new PlayerService(this.api, this.eventBus, this.store);

      // 7. 初始化任务服务（依赖：api, eventBus, store, playerService, templateService）
      this.taskService = new TaskService(this.api, this.eventBus, this.store, this.playerService, this.templateService);

      // 8. 初始化UI服务（依赖：eventBus, store, templateService, taskService, playerService）
      this.uiService = new UIService(this.eventBus, this.store, this.templateService, this.taskService, this.playerService, this.swiperService);
      await this.uiService.initialize();

      // 9. 初始化商城服务（依赖：eventBus, api, playerService, router）
      this.shopService = new ShopService(this.eventBus, this.api, this.playerService, this.router);

      // 10. 初始化地图服务（依赖：api, eventBus, uiService,playerService）
      await this.initializeMapService();
      if (this.mapService) {
        await this.mapService.initMap();
      }

      // 11. 初始化其他服务
      await this.initializeOtherServices();

      // 12. 设置事件监听器
      await this.setupEventListeners();
      await this.websocketService.connect();
      this.initialized = true;
      Logger.info("GameManager", "[initializeServices:131]", "服务组件初始化完成");
    } catch (error) {
      Logger.error("GameManager", "[initializeServices]", "服务初始化失败:", error);
      throw error;
    }
  }

  // 初始化地图服务
  async initializeMapService() {
    // 创建MapService实例，传入store
    this.mapService = new MapService(this.api, this.eventBus, this.uiService, this.playerService, this.store);
  }

  // 初始化其他服务
  async initializeOtherServices() {
    this.wordcloudService = new WordcloudService(this.api, this.eventBus, this.store, this.playerService);
    this.swiperService = new SwiperService();
    this.nfcService = new NFCService(this.api, this.eventBus, this.store);
    this.audioService = new AudioService(this.eventBus, this.store);
    this.live2dService = new Live2DService(this.eventBus, this.store);
    // 初始化 Live2D 服务
    await this.live2dService.initialize();

    // 设置ICP备案号
    gameUtils.setICPAndMPS(ICP, MPS);
  }

  // 初始化基础属性
  initializeBaseProperties() {
    Logger.info("GameManager", "初始化基础属性");

    // 滑动组件相关
    this.activeTasksSwiper = null;
    this.taskListSwiper = null;

    // 加载状态
    this.loading = false;

    Logger.info("GameManager", "基础属性初始化完成");
  }

  // 优化初始化应用方法
  async initializeApplication() {
    if (this.initializationPromise) {
      return this.initializationPromise;
    }

    this.initializationPromise = (async () => {
      try {
        Logger.info("GameManager", "[initializeApplication:178]", "初始化应用开始");

        // 等待所有服务初始化完成
        if (!this.initialized) {
          Logger.info("GameManager", "[initializeApplication:182]", "等待服务初始化完成");
          await new Promise((resolve) => {
            const checkInit = () => {
              if (this.initialized) {
                resolve();
              } else {
                setTimeout(checkInit, 100);
              }
            };
            checkInit();
          });
        }

        // 1. 加载玩家信息 这一步应该是多余的
        // Logger.info("GameManager", "[initializeApplication:196]", "开始加载玩家信息");
        // await this.playerService.loadPlayerInfo();
        // Logger.info("GameManager", "[initializeApplication:198]", "玩家信息加载完成");

        // 2. 设置WebSocket订阅
        const playerId = this.playerService.getPlayerId();
        if (playerId && this.websocketService && this.mapService) {
          this.websocketService.subscribeToPlayerEvents(playerId);
          this.mapService.setWebSocketManager(this.websocketService.getWSManager());
        }

        // 3. 加载任务数据
        if (this.taskService && this.uiService) {
          await Promise.all([
            this.taskService.loadTasks().then((tasks) => {
              this.uiService.renderTaskList(tasks);
            }),
            this.taskService.loadCurrentTasks().then((currentTasks) => {
              this.uiService.renderCurrentTasks(currentTasks);
            }),
          ]);
          Logger.info("GameManager", "[initializeApplication:226]", "任务数据加载完成");
        }

        // 4. 初始化滑动组件
        if (this.swiperService) {
          this.swiperService.initSwipers();
        }

        // 5. 初始化文字云
        await this.initWordCloud();

        Logger.info("GameManager", "[initializeApplication:237]", "初始化应用完成");
      } catch (error) {
        Logger.error("GameManager", "[initializeApplication]", "初始化应用失败:", error);
        layer.msg("初始化应用失败，请刷新页面重试", { icon: 2 });
        ErrorHandler.handle(error, "GameManager.initializeApplication");
        throw error;
      }
    })();

    return this.initializationPromise;
  }

  // 初始化观察器 已经在uiService中初始化
  setupDOMObserver() {
    Logger.debug("GameManager", "初始化DOM观察器");
    const taskObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === "childList") {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1) {
              // 处理任务卡片
              if (node.classList?.contains("task-card")) {
                this.uiService.initializeTaskCard(node);
              }
              // 处理新添加节点中的任务卡片
              // const taskCards = node.getElementsByClassName("task-card");
              // Array.from(taskCards).forEach((card) => this.uiService.initializeTaskCard(card));
            }
          });
        }
      });
    });

    // 设置观察器配置
    const config = { childList: true, subtree: true };

    // 监听相关容器
    const containers = [document.getElementById("taskList"), document.querySelector(".active-tasks-swiper .swiper-wrapper"), document.querySelector(".tasks-list")].filter(Boolean);

    containers.forEach((container) => {
      taskObserver.observe(container, config);
      // 初始化已存在的任务卡片
      // Array.from(container.getElementsByClassName("task-card")).forEach((card) => this.uiService.initializeTaskCard(card));
    });

    // 存储观察器实例以便后续清理
    this._taskObserver = taskObserver;
  }

  // 初始化文字云
  async initWordCloud() {
    Logger.info("GameManager", "初始化文字云");
    const container = document.getElementById("wordCloudContainer");
    if (container) {
      await this.wordcloudService.initWordCloud(container);
    } else {
      Logger.error("GameManager", "找不到文字云容器");
    }
  }

  // 设置事件监听器
  async setupEventListeners() {
    Logger.info("GameManager", "setupEventListeners:318", "设置事件监听器");

    try {
      // 检查必要服务是否已初始化
      if (!this.eventBus) throw new Error("事件总线未初始化");
      if (!this.playerService) throw new Error("玩家服务未初始化");
      if (!this.taskService) throw new Error("任务服务未初始化");
      if (!this.uiService) throw new Error("UI服务未初始化");
      if (!this.audioService) throw new Error("音频服务未初始化");
      if (!this.websocketService) throw new Error("WebSocket服务未初始化");

      // 初始化事件管理器
      await this.initializeEventManager();

      Logger.info("GameManager", "setupEventListeners:330", "事件监听器设置完成");
    } catch (error) {
      Logger.error("GameManager", "setupEventListeners:332", "设置事件监听器失败:", error);
      throw error;
    }
  }

  /**
   * 初始化事件管理器
   */
  async initializeEventManager() {
    Logger.info("GameManager", "初始化事件管理器");
    try {
      // 创建 EventManager 实例
      this.eventManager = new EventManager({
        eventBus: this.eventBus,
        taskService: this.taskService,
        playerService: this.playerService,
        uiService: this.uiService,
        mapService: this.mapService,
        audioService: this.audioService,
        websocketService: this.websocketService,
        shopService: this.shopService,
        wordcloudService: this.wordcloudService,
        live2dService: this.live2dService,
        swiperService: this.swiperService,
        router: this.router,
      });
    } catch (error) {
      Logger.error("GameManager", "初始化事件管理器失败:", error);
      throw error;
    }
  }

  // 修改销毁方法，添加观察器清理
  destroy() {
    if (this._taskObserver) {
      this._taskObserver.disconnect();
    }
    this.swiperService.destroySwipers();
    this.wordcloudService.destroy();
    this.audioService.destroy();
    this.websocketService.disconnect();
    this.live2dService.cleanup();
    Logger.info("GameManager", "资源清理完成");
  }
}

// 优化页面初始化代码
document.addEventListener("DOMContentLoaded", async () => {
  Logger.info("GameManager", "页面加载开始");

  try {
    // 创建全局管理器实例
    window.GameManager = new GameManager();

    // 等待应用完全初始化
    await window.GameManager.initializeApplication();

    Logger.info("GameManager", "页面初始化完成");
  } catch (error) {
    Logger.error("GameManager", "页面初始化失败:", error);
    layer.msg("初始化失败，请刷新页面重试", { icon: 2 });
  }
});

// 页面卸载前清理
window.addEventListener("beforeunload", () => {
  if (window.GameManager) {
    window.GameManager.destroy();
  }
});
