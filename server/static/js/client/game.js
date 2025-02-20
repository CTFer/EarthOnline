/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-29 16:43:22
 * @LastEditTime: 2025-02-19 17:59:41
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import { SERVER } from "../config/config.js";
import APIClient from "./core/api.js"; 
import TemplateService from "./service/templateService.js";
import TaskService from "./service/taskService.js";
import EventBus from "./core/eventBus.js";
import Store from "./core/store.js";
import Logger from "../utils/logger.js";
import SwiperService from './service/swiperService.js';
import { ErrorHandler } from './core/errorHandler.js';
import WordcloudService from './service/wordcloudService.js';
import PlayerService from './service/playerService.js';
import NFCService from './service/nfcService.js';
import MapService from './service/mapService.js';
import UIService from './service/uiService.js';
import AudioService from './service/audioService.js';
import Live2DService from './service/live2dService.js';
import WebSocketService from './service/websocketService.js';
import { gameUtils } from "../utils/utils.js";
import { 
    TASK_EVENTS,
    PLAYER_EVENTS,
    MAP_EVENTS,
    UI_EVENTS,
    WS_EVENTS,
    AUDIO_EVENTS,
    LIVE2D_EVENTS 
} from "./config/events.js";
import EventManager from './core/EventManager.js';

// 在文件开头声明全局变量
let taskManager;

// 游戏管理类，程序入口
class GameManager {
  constructor() {
    Logger.info("GameManager", "开始初始化游戏管理器");

    // 确保核心组件最先初始化
    this.eventBus = new EventBus();
    this.store = new Store();
    this.api = new APIClient();
    
    this.initialized = false;
    this.initializationPromise = null;
    
    Logger.info("GameManager", "核心组件初始化完成");

    try {
      // 1. 初始化核心组件
      this.initializeCoreComponents();
      
      // 2. 初始化基础属性
      this.initializeBaseProperties();
      
      // 3. 初始化DOM观察器
      this.setupDOMObserver();
      
      // 4. 初始化服务
      this.initializeServices().then(() => {
        Logger.info("GameManager", "游戏管理器初始化完成");
        this.initialized = true;
      }).catch(error => {
        Logger.error("GameManager", "游戏管理器初始化失败:", error);
        layer.msg("初始化失败，请刷新页面重试", {icon: 2});
      });

    } catch (error) {
      Logger.error("GameManager", "游戏管理器初始化失败:", error);
      layer.msg("初始化失败，请刷新页面重试", {icon: 2});
      throw error;
    }
  }

  // 初始化核心组件
  initializeCoreComponents() {
    Logger.info("GameManager", "初始化核心组件");
    
    try {
      // 初始化API客户端
      this.api = new APIClient(SERVER);
      
      // 初始化事件总线
      this.eventBus = new EventBus();
      
      // 初始化数据存储
      this.store = new Store();
      
      Logger.info("GameManager", "核心组件初始化完成");
    } catch (error) {
      Logger.error("GameManager", "核心组件初始化失败:", error);
      throw error;
    }
  }

  // 初始化服务
  async initializeServices() {
    Logger.info("GameManager", "初始化服务组件");
    
    try {
        // 1. 初始化基础服务（无依赖）
        this.templateService = new TemplateService();
        
        // 2. 初始化WebSocket服务（依赖：eventBus）
        this.websocketService = new WebSocketService(this.eventBus);
        await this.websocketService.initialize();
        
        // 3. 初始化玩家服务（依赖：api, eventBus, store）
        this.playerService = new PlayerService(
            this.api,
            this.eventBus,
            this.store
        );
        
        // 4. 初始化任务服务（依赖：api, eventBus, store, playerService, templateService）
        this.taskService = new TaskService(
            this.api,
            this.eventBus,
            this.store,
            this.playerService,
            this.templateService
        );
        
        // 5. 初始化UI服务（依赖：eventBus, store, templateService, taskService）
        this.uiService = new UIService(
            this.eventBus, 
            this.store,
            this.templateService,
            this.taskService
        );

        // 6. 初始化其他服务
        await Promise.all([
            this.initializeMapService(),
            this.initializeOtherServices()
        ]);

        // 7. 设置事件监听器
        await this.setupEventListeners();
        await this.websocketService.connect();
        
        this.initialized = true;
        Logger.info("GameManager", "服务组件初始化完成");
    } catch (error) {
        Logger.error("GameManager", "初始化服务组件失败:", error);
        throw error;
    }
  }

  async initializeMapService() {
    this.mapService = new MapService(this.api, this.eventBus, this.store);
    await this.mapService.initMap();
  }

  async initializeOtherServices() {
    this.wordcloudService = new WordcloudService(
      this.api,
      this.eventBus,
      this.store,
      this.playerService
    );
    this.swiperService = new SwiperService();
    this.nfcService = new NFCService(this.api, this.eventBus, this.store);
    this.audioService = new AudioService(this.eventBus);
    this.live2dService = new Live2DService();
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
        Logger.info("[GameManager]", "初始化应用开始");
        
        // 等待所有服务初始化完成
        if (!this.initialized) {
          Logger.info("[GameManager]", "等待服务初始化完成");
          await new Promise(resolve => {
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
        
        // 1. 首先加载玩家信息
        Logger.info("[GameManager]", "开始加载玩家信息");
        await this.playerService.loadPlayerInfo();
        Logger.info("[GameManager]", "玩家信息加载完成");
        
        // 2. 初始化地图服务
        if (this.mapService) {
          Logger.info("[GameManager]", "开始初始化地图服务");
          await this.mapService.initMap();
          Logger.info("[GameManager]", "地图服务初始化完成");
        } else {
          Logger.warn("[GameManager]", "地图服务未就绪，跳过初始化");
        }
        
        // 3. 设置WebSocket订阅
        const playerId = this.playerService.getPlayerId();
        if (playerId && this.websocketService && this.mapService) {
          this.websocketService.subscribeToPlayerEvents(playerId);
          this.mapService.setWebSocketManager(this.websocketService.getWSManager());
        }
        
        // 4. 加载任务数据
        if (this.taskService && this.uiService) {
          await Promise.all([
            this.taskService.loadTasks().then(tasks => {
              this.uiService.renderTaskList(tasks);
            }),
            this.taskService.loadCurrentTasks().then(currentTasks => {
              this.uiService.renderCurrentTasks(currentTasks);
            })
          ]);
          Logger.info("[GameManager]", "任务数据加载完成");
        }
        
        // 5. 初始化滑动组件
        if (this.swiperService) {
          this.swiperService.initSwipers();
        }
        
        // 6. 初始化文字云
        await this.initWordCloud();
        
        Logger.info("[GameManager]", "初始化应用完成");
      } catch (error) {
        Logger.error("[GameManager]", "初始化应用失败:", error);
        layer.msg('初始化应用失败，请刷新页面重试', {icon: 2});
        ErrorHandler.handle(error, 'GameManager.initializeApplication');
        throw error;
      }
    })();

    return this.initializationPromise;
  }

  // 初始化观察器
  setupDOMObserver() {
    Logger.debug("GameManager", "初始化DOM观察器");

    const taskObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === "childList") {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1) {
              // 处理任务卡片
              if (node.classList?.contains("task-card")) {
                this.initializeTaskCard(node);
              }
              // 处理新添加节点中的任务卡片
              const taskCards = node.getElementsByClassName("task-card");
              Array.from(taskCards).forEach((card) => this.initializeTaskCard(card));
            }
          });
        }
      });
    });

    // 设置观察器配置
    const config = { childList: true, subtree: true };

    // 监听相关容器
    const containers = [
      document.getElementById("taskList"), 
      document.querySelector(".active-tasks-swiper .swiper-wrapper"),
      document.querySelector(".tasks-list")
    ].filter(Boolean);

    containers.forEach((container) => {
      taskObserver.observe(container, config);
      // 初始化已存在的任务卡片
      Array.from(container.getElementsByClassName("task-card")).forEach((card) => 
        this.initializeTaskCard(card)
      );
    });

    // 存储观察器实例以便后续清理
    this._taskObserver = taskObserver;
  }

  // 初始化任务卡片
  initializeTaskCard(taskCard) {
    const timeElement = taskCard.querySelector(".task-time");
    if (!timeElement) return;

    const endtime = parseInt(taskCard.dataset.endtime);
    if (!endtime) return;

    const timeUpdateInterval = setInterval(() => {
      const isActive = gameUtils.updateTaskTime(taskCard, endtime);
      if (!isActive) {
        clearInterval(timeUpdateInterval);
        taskCard.classList.add("expired");
      }
    }, 1000);
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
    Logger.info("GameManager", "开始设置事件监听器");

    try {
      // 检查必要服务是否已初始化
      if (!this.eventBus) throw new Error("事件总线未初始化");
      if (!this.playerService) throw new Error("玩家服务未初始化");
      if (!this.taskService) throw new Error("任务服务未初始化");
      if (!this.uiService) throw new Error("UI服务未初始化");
      if (!this.audioService) throw new Error("音频服务未初始化");
      if (!this.websocketService) throw new Error("WebSocket服务未初始化");

      // 设置玩家相关事件
      await this.setupPlayerEvents();
      
      // 设置地图相关事件
      await this.setupMapEvents();
      
      // 初始化后台服务
      await Promise.allSettled([
        this.audioService.init().catch(error => {
          Logger.warn("GameManager", "音频初始化失败，继续无声模式:", error);
        }),
        this.live2dService.initialize().catch(error => {
          Logger.warn("GameManager", "Live2D初始化失败，继续无模型模式:", error);
        })
      ]);

      Logger.info("GameManager", "事件监听器设置完成");
    } catch (error) {
      Logger.error("GameManager", "设置事件监听器失败:", {
        error: error.message,
        stack: error.stack,
        services: {
          eventBus: !!this.eventBus,
          playerService: !!this.playerService,
          taskService: !!this.taskService,
          uiService: !!this.uiService,
          audioService: !!this.audioService,
          websocketService: !!this.websocketService
        }
      });
      throw error;
    }
  }

  // 设置玩家相关事件
  async setupPlayerEvents() {
    Logger.debug("GameManager", "设置玩家相关事件监听");

    // 监听玩家ID更新事件
    this.eventBus.on(PLAYER_EVENTS.ID_UPDATED, (newId) => {
      try {
        Logger.info("GameManager", "玩家ID更新事件:", newId);
        
        // 使用Promise.all确保所有更新操作按顺序执行
        Promise.all([
          // 1. 更新WebSocket订阅
          this.websocketService.subscribeToPlayerEvents(newId),
          // 2. 更新任务服务（只清理缓存）
          this.taskService.updatePlayerId(newId),
          // 3. 重新加载玩家信息
          this.playerService.loadPlayerInfo()
        ]).then(() => {
          // 4. 最后一次性刷新任务列表
          this.taskService.refreshTasks();
        }).catch(error => {
          Logger.error("GameManager", "玩家ID更新处理失败:", error);
          this.handleEventError(error, "更新玩家信息失败");
        });
      } catch (error) {
        Logger.error("GameManager", "处理玩家ID更新事件失败:", error);
        this.handleEventError(error, "更新玩家信息失败");
      }
    });
  }

  // 设置地图相关事件
  async setupMapEvents() {
    Logger.debug("GameManager", "设置地图相关事件监听");

    // 监听GPS更新事件
    this.eventBus.on(MAP_EVENTS.GPS_UPDATED, (gpsData) => {
      try {
        Logger.debug("GameManager", "GPS更新事件");
        if (!this.initialized) {
          Logger.warn("GameManager", "应用尚未完成初始化，暂存GPS更新");
          return;
        }
        // 委托给MapService处理GPS更新
        this.mapService.handleGPSUpdate(gpsData);
      } catch (error) {
        Logger.error("GameManager", "处理GPS更新事件失败:", error);
        this.handleEventError(error, "更新GPS数据失败");
      }
    });
  }

  /**
   * 处理事件错误
   * @param {Error} error - 错误对象
   * @param {string} userMessage - 用户友好的错误消息
   */
  handleEventError(error, userMessage) {
    // 输出详细的错误信息到控制台
    Logger.error("GameManager", "错误详情:", {
      message: error.message,
      stack: error.stack,
      name: error.name,
      originalError: error
    });

    // 记录用户友好的错误消息
    Logger.error("GameManager", userMessage);

    // 通知用户
    this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
      type: "ERROR",
      message: userMessage,
      details: error.message // 添加原始错误信息
    });

    // 播放错误音效
    this.eventBus.emit(AUDIO_EVENTS.PLAY, "ERROR");
  }

  // 删除原有的 showTaskDetails 方法，改为调用 UIService
  handleTaskClick(taskData) {
    Logger.debug("GameManager", "处理任务点击:", taskData);
    this.uiService.showTaskDetails(taskData);
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

  /**
   * 初始化事件管理器
   */
  initializeEventManager() {
    Logger.info('Game', '初始化事件管理器');
    try {
      this.eventManager = new EventManager({
        eventBus: this.eventBus,
        taskService: this.taskService,
        playerService: this.playerService,
        uiService: this.uiService,
        mapService: this.mapService,
        audioService: this.audioService,
        wsService: this.websocketService,
        wordcloudService: this.wordcloudService,
        live2dService: this.live2dService,
        notificationService: this.notificationService
      });
      this.eventManager.initializeEventListeners();
      Logger.info('Game', '事件管理器初始化完成');
    } catch (error) {
      Logger.error('Game', '初始化事件管理器失败:', error);
      throw error;
    }
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
    layer.msg("初始化失败，请刷新页面重试", {icon: 2});
  }
});

// 页面卸载前清理
window.addEventListener("beforeunload", () => {
  if (window.GameManager) {
    window.GameManager.destroy();
  }
});
