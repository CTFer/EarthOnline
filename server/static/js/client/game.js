/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-29 16:43:22
 * @LastEditTime: 2025-02-17 16:37:30
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import { SERVER, MAP_CONFIG } from "../config/config.js";
import WebSocketManager from "../function/WebSocketManager.js"; 
// import WebSocketManager from "./core/websocketManager.js";//TODO: 存在BUG 页面卡死
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

// 在文件开头声明全局变量
let taskManager;

// 游戏管理类，程序入口
class GameManager {
  constructor() {
    Logger.info("GameManager", "开始初始化游戏管理器");

    // 添加初始化状态标志
    this.initialized = false;
    this.initializationPromise = null;

    try {
      // 初始化核心组件
      this.initializeCoreComponents();
      
      // 初始化服务
      this.initializeServices();
      
      // 初始化WebSocket
      this.initializeWebSocket();
      
      // 初始化事件监听
      this.setupEventListeners();
      
      // 初始化基础属性
      this.initializeBaseProperties();
      
      // 初始化DOM观察器
      this.setupDOMObserver();

      Logger.info("GameManager", "游戏管理器初始化完成");
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
  initializeServices() {
    Logger.info("GameManager", "初始化服务组件");
    
    try {
      // 1. 初始化玩家服务（最优先）
      this.playerService = new PlayerService(this.api, this.eventBus, this.store);
      
      // 2. 初始化模板服务
      this.templateService = new TemplateService();
      
      // 3. 初始化依赖玩家服务的其他服务
      this.taskService = new TaskService(
        this.api,
        this.eventBus,
        this.store,
        this.playerService,
        this.templateService
      );

      this.wordcloudService = new WordcloudService(
        this.api,
        this.eventBus,
        this.store,
        this.playerService
      );

      // 4. 初始化独立服务
      this.swiperService = new SwiperService();
      this.mapService = new MapService(this.api, this.eventBus, this.store);
      this.nfcService = new NFCService(this.api, this.eventBus, this.store);
      this.uiService = new UIService(this.eventBus, this.store, this.templateService);
      this.audioService = new AudioService();
      this.live2dService = new Live2DService();
      
      // 5. 初始化音频服务
      this.audioService.init().catch(error => {
        Logger.warn("GameManager", "音频初始化失败，继续无声模式:", error);
      });

      // 6. 初始化Live2D服务
      this.live2dService.initialize().catch(error => {
        Logger.warn("GameManager", "Live2D初始化失败，继续无模型模式:", error);
      });

      Logger.info("GameManager", "服务组件初始化完成");
    } catch (error) {
      Logger.error("GameManager", "服务组件初始化失败:", error);
      throw error;
    }
  }

  // 初始化WebSocket
  initializeWebSocket() {
    Logger.info("GameManager", "初始化WebSocket");
    
    try {
      Logger.info("GameManager", "开始初始化WebSocket管理器");
      this.wsManager = new WebSocketManager();
      
      const playerId = this.playerService.getPlayerId();
      Logger.debug("GameManager", "当前玩家ID:", playerId);
      
      if (playerId) {
        Logger.info("GameManager", "开始设置WebSocket事件监听");
        this.wsManager.subscribeToTasks(playerId);
        this.wsManager.onTaskUpdate(this.handleTaskStatusUpdate.bind(this));
        this.wsManager.onNFCTaskUpdate(this.handleTaskUpdate.bind(this));
        this.wsManager.onTagsUpdate(() => {
          Logger.debug("GameManager", "触发词云更新");
          this.updateWordCloud();
        });
        Logger.info("GameManager", "WebSocket事件监听设置完成");
      } else {
        Logger.warn("GameManager", "玩家ID未设置，WebSocket订阅将在ID可用时进行");
      }
    } catch (error) {
      Logger.error("GameManager", "WebSocket初始化失败:", error);
      layer.msg("WebSocket连接失败，部分功能可能不可用", {icon: 2});
      // 不抛出错误，允许在WebSocket失败的情况下继续运行
    }
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
        
        // 1. 首先加载玩家信息
        Logger.info("[GameManager]", "开始加载玩家信息");
        await this.playerService.loadPlayerInfo();
        Logger.info("[GameManager]", "玩家信息加载完成");
        
        // 2. 初始化地图服务
        await this.mapService.initMap();
        Logger.info("[GameManager]", "地图服务初始化完成");
        
        // 3. 设置WebSocket订阅
        const playerId = this.playerService.getPlayerId();
        if (playerId) {
          this.wsManager.subscribeToGPS(playerId);
          this.mapService.setWebSocketManager(this.wsManager);
        }
        
        // 4. 加载任务数据
        await Promise.all([
          this.taskService.loadTasks().then(tasks => {
            this.uiService.renderTaskList(tasks);
          }),
          this.taskService.loadCurrentTasks().then(currentTasks => {
            this.uiService.renderCurrentTasks(currentTasks);
          })
        ]);
        Logger.info("[GameManager]", "任务数据加载完成");
        
        // 5. 初始化滑动组件
        this.swiperService.initSwipers();
        
        // 6. 初始化文字云
        await this.initWordCloud();
        
        this.initialized = true;
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

  // 处理NFC任务更新通知
  handleTaskUpdate(data) {
    Logger.info("GameManager", "开始处理NFC任务更新:", data);

    // 参数验证
    if (!data || !data.type) {
      Logger.error("GameManager", "无效的任务更新数据:", data);
      this.uiService.showNotification({
        type: "ERROR",
        message: "收到无效的任务更新",
      });
      return;
    }

    Logger.debug("GameManager", "处理任务类型:", data.type);
    
    // 使用Map对象替代switch语句，提高可维护性
    const taskHandlers = {
      // 处理身份识别更新
      "IDENTITY": () => {
        Logger.info("GameManager", "处理身份识别更新");
        // 更新玩家ID
        this.playerService.setPlayerId(data.player_id);
        // 重新加载玩家信息
        this.playerService.loadPlayerInfo();
        // 刷新任务列表
        this.refreshTasks();
      },
      
      // 处理需要刷新任务的更新类型
      "NEW_TASK": () => {
        Logger.info("GameManager", "处理新任务更新");
        this.refreshTasks();
        this.playTaskSound(data.type);
      },
      "COMPLETE": () => {
        Logger.info("GameManager", "处理任务完成更新");
        this.refreshTasks();
        this.playTaskSound(data.type);
      },
      "CHECK": () => {
        Logger.info("GameManager", "处理任务检查更新");
        this.refreshTasks();
        this.playTaskSound(data.type);
      },
      
      // 处理只需要显示通知的更新类型
      "ALREADY_COMPLETED": () => {
        Logger.info("GameManager", "处理任务重复完成通知");
      },
      "REJECT": () => {
        Logger.info("GameManager", "处理任务驳回通知");
      },
      "CHECKING": () => {
        Logger.info("GameManager", "处理任务审核中通知");
      },
      
      // 处理错误情况
      "ERROR": () => {
        Logger.info("GameManager", "处理错误消息");
        this.playErrorSound();
      }
    };

    // 执行对应的处理函数
    const handler = taskHandlers[data.type];
    if (handler) {
      try {
        handler();
      } catch (error) {
        Logger.error("GameManager", `处理任务类型 ${data.type} 时发生错误:`, error);
        this.handleEventError(error, `处理任务更新失败: ${data.type}`);
      }
    } else {
      Logger.warn("GameManager", "未知的任务类型:", data.type);
    }

    // 显示通知
    Logger.debug("GameManager", "准备显示通知:", data);
    this.uiService.showNotification(data);
    Logger.debug("GameManager", "通知显示完成");
  }

  // 播放任务相关音效
  playTaskSound(type) {
    this.audioService.playSound(type);
  }

  // 播放错误音效
  playErrorSound() {
    const audio = new Audio("/static/sounds/error.mp3");
    audio.play().catch((e) => Logger.error("GameManager", "音效播放失败:", e));
  }

  // 修改loadTasks方法，使用taskService和uiService
  async loadTasks() {
    try {
      Logger.info("GameManager", "开始加载任务列表");
      const tasks = await this.taskService.loadTasks();
      this.uiService.renderTaskList(tasks);
      Logger.info("GameManager", "任务列表加载完成");
    } catch (error) {
      Logger.error("GameManager", "加载任务失败:", error);
      this.handleEventError(error, "加载任务失败");
    }
  }

  // 修改loadCurrentTasks方法
  async loadCurrentTasks() {
    try {
      Logger.info("GameManager", "加载进行中的任务");
      const currentTasks = await this.taskService.getCurrentTasks(this.playerService.getPlayerId());
      this.uiService.renderCurrentTasks(currentTasks);
      Logger.info("GameManager", "进行中任务加载完成");
      return currentTasks;
    } catch (error) {
      Logger.error("GameManager", "加载进行中的任务失败:", error);
      this.handleEventError(error, "加载进行中任务失败");
      throw error;
    }
  }

  // 显示错误信息
  showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `<div class="empty-tip">${message}</div>`;
    }
  }

  // 获取状态颜色
  getStatusColor(type) {
    Logger.log(type);
    Logger.log(TASK_TYPE_MAP[type]);
    // 从配置文件中获取任务类型的颜色
    if (type && TASK_TYPE_MAP[type]) {
      return TASK_TYPE_MAP[type].color;
    }

    // 默认返回未定义任务的颜色
    return TASK_TYPE_MAP["UNDEFINED"].color;
  }

  // 获取状态文本
  getStatusText(type) {
    switch (type) {
      case "NEW_TASK":
        return "新任务";
      case "COMPLETE":
        return "已完成";
      case "ALREADY_COMPLETED":
        return "重复完成";
      case "CHECKING":
        return "审核中";
      case "REJECTED":
        return "已驳回";
      case "ERROR":
        return "错误";
      default:
        return "未知状态";
    }
  }

  // 接受任务
  async acceptTask(taskId) {
    try {
      Logger.info("[GameManager]", "开始接受任务", taskId);
      
      if (!taskId) {
        throw new Error("任务ID不能为空");
      }

      const result = await this.taskService.acceptTask(taskId, this.playerService.getPlayerId());
      
      if (result.code === 0) {
        layer.msg(`成功接受任务: ${result.data.task_name}`, { icon: 1 });
        await this.taskService.loadCurrentTasks();
      } else {
        let icon = 2;
        switch (result.code) {
          case 1: // 参数错误
            icon = 0;
            break;
          case 2: // 前置任务未完成
            icon = 4;
            break;
          default:
            icon = 2;
        }
        layer.msg(result.msg, { icon: icon });
      }
    } catch (error) {
      Logger.error("[GameManager]", "接受任务失败:", error);
      layer.msg("网络请求失败，请检查连接", { icon: 2 });
      ErrorHandler.handle(error, 'GameManager.acceptTask');
    }
  }

  // 放弃任务
  async abandonTask(taskId) {
    // 委托给UIService处理确认对话框
    this.uiService.showConfirmDialog({
      title: "放弃任务",
      content: "确定要放弃这个任务吗？",
      onConfirm: async () => {
        try {
          // 委托给TaskService处理业务逻辑
          const result = await this.taskService.abandonTask(taskId, this.playerService.getPlayerId());
          
          // 委托给UIService处理结果展示
          if (result.code === 0) {
            this.uiService.showSuccessMessage(result.msg);
            await this.refreshTasks();
          } else {
            this.uiService.showErrorMessage(result.msg);
          }
        } catch (error) {
          Logger.error("GameManager", "放弃任务失败:", error);
          this.handleEventError(error, "放弃任务失败");
        }
      }
    });
  }

  // 完成任务
  async completeTask(taskId) {
    try {
      // 委托给TaskService处理业务逻辑
      const result = await this.taskService.completeTask(taskId, this.playerService.getPlayerId());
      
      // 委托给UIService处理结果展示
      if (result.code === 0) {
        this.uiService.showSuccessMessage(`${result.msg}，获得 ${result.data.points} 点经验`);
        await this.refreshTasks();
        
        // 触发任务完成事件
        this.eventBus.emit('task:completed', {
          taskId: taskId,
          points: result.data.points,
          name: result.data.task_name
        });
      } else {
        this.uiService.showErrorMessage(result.msg);
      }
    } catch (error) {
      Logger.error("GameManager", "完成任务失败:", error);
      this.handleEventError(error, "完成任务失败");
    }
  }

  // 刷新所有任务
  async refreshTasks() {
    try {
      Logger.info("GameManager", "开始刷新任务列表");
      
      // 并行加载所有任务和当前任务
      await Promise.all([
        this.taskService.loadTasks().then(tasks => {
          this.uiService.renderTaskList(tasks);
        }),
        this.taskService.loadCurrentTasks().then(currentTasks => {
          this.uiService.renderCurrentTasks(currentTasks);
        })
      ]);
      
      Logger.info("GameManager", "任务列表刷新完成");
    } catch (error) {
      Logger.error("GameManager", "刷新任务失败:", error);
      this.handleEventError(error, "刷新任务失败");
    }
  }

  // 初始化观察器
  initializeObservers() {
    // 任务卡片观察器
    const taskObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) {
            if (node.classList?.contains("task-card")) {
              this.initializeTaskCard(node);
            }
            const taskCards = node.getElementsByClassName("task-card");
            Array.from(taskCards).forEach((card) => this.initializeTaskCard(card));
          }
        });
      });
    });

    // 设置观察器配置
    const config = { childList: true, subtree: true };

    // 监听相关容器
    const containers = [document.getElementById("taskList"), document.querySelector(".active-tasks-swiper .swiper-wrapper"), document.querySelector(".tasks-list")].filter(Boolean);

    containers.forEach((container) => {
      taskObserver.observe(container, config);
      // 初始化已存在的任务卡片
      Array.from(container.getElementsByClassName("task-card")).forEach((card) => this.initializeTaskCard(card));
    });

    return taskObserver;
  }

  // 初始化任务卡片
  initializeTaskCard(taskCard) {
    const timeElement = taskCard.querySelector(".task-time");
    if (!timeElement) return;

    const endtime = parseInt(taskCard.dataset.endtime);
    if (!endtime) return;

    const timeUpdateInterval = setInterval(() => {
      const isActive = this.updateTaskTime(taskCard, endtime);
      if (!isActive) {
        clearInterval(timeUpdateInterval);
        taskCard.classList.add("expired");
      }
    }, 1000);
  }

  // 更新任务时间
  updateTaskTime(taskElement, endtime) {
    const now = Math.floor(Date.now() / 1000);
    const timeLeft = endtime - now;

    if (timeLeft <= 0) {
      taskElement.querySelector(".task-time").textContent = "已过期";
      return false;
    }

    const hours = Math.floor(timeLeft / 3600);
    const minutes = Math.floor((timeLeft % 3600) / 60);
    const seconds = timeLeft % 60;

    const timeString = `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
    taskElement.querySelector(".task-time").textContent = `剩余时间：${timeString}`;
    return true;
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

  // 添加事件处理方法
  handleCurrentTasksUpdated(tasks) {
    Logger.info("[GameManager]", "Current tasks updated:", tasks);
    this.renderCurrentTasks(tasks);
  }

  handleTaskError(error) {
    Logger.error("GameManager", "Task error:", error);
    layer.msg(error.message || "任务操作失败", { icon: 2 });
  }

  setupEventListeners() {
    Logger.info("GameManager", "开始设置事件监听器");

    try {
      // 任务相关事件
      this.setupTaskEvents();
      
      // 玩家相关事件
      this.setupPlayerEvents();
      
      // 地图相关事件
      this.setupMapEvents();
      
      // UI相关事件
      this.setupUIEvents();

      Logger.info("GameManager", "事件监听器设置完成");
    } catch (error) {
      Logger.error("GameManager", "设置事件监听器失败:", error);
      throw error;
    }
  }

  // 设置任务相关事件
  setupTaskEvents() {
    Logger.debug("GameManager", "设置任务相关事件监听");

    // 监听任务加载完成事件
    this.eventBus.on("tasks:loaded", (tasks) => {
      try {
        Logger.info("GameManager", "收到任务加载完成事件，任务数量:", tasks.length);
        this.renderTaskList(tasks);
      } catch (error) {
        Logger.error("GameManager", "处理任务加载事件失败:", error);
        this.handleEventError(error, "任务加载失败");
      }
    });

    // 监听当前任务更新事件
    this.eventBus.on("currentTasks:updated", (tasks) => {
      try {
        Logger.info("GameManager", "当前任务更新事件，任务数量:", tasks.length);
        this.renderCurrentTasks(tasks);
      } catch (error) {
        Logger.error("GameManager", "处理当前任务更新事件失败:", error);
        this.handleEventError(error, "更新当前任务失败");
      }
    });

    // 监听任务错误事件
    this.eventBus.on("tasks:error", (error) => {
      Logger.error("GameManager", "任务错误事件:", error);
      this.handleEventError(error, "任务操作失败");
    });

    // 监听任务完成事件
    this.eventBus.on("task:completed", (taskData) => {
      try {
        Logger.info("GameManager", "任务完成事件:", taskData);
        this.handleTaskCompletion(taskData);
      } catch (error) {
        Logger.error("GameManager", "处理任务完成事件失败:", error);
        this.handleEventError(error, "处理任务完成失败");
      }
    });
  }

  // 设置玩家相关事件
  setupPlayerEvents() {
    Logger.debug("GameManager", "设置玩家相关事件监听");

    // 监听玩家ID更新事件
    this.eventBus.on("player:id-updated", (newId) => {
      try {
        Logger.info("GameManager", "玩家ID更新事件:", newId);
        this.handlePlayerIdUpdate(newId);
      } catch (error) {
        Logger.error("GameManager", "处理玩家ID更新事件失败:", error);
        this.handleEventError(error, "更新玩家信息失败");
      }
    });

    // 监听玩家信息更新事件
    this.eventBus.on("player:info-updated", (playerInfo) => {
      try {
        Logger.info("GameManager", "玩家信息更新事件");
        this.updatePlayerUI(playerInfo);
      } catch (error) {
        Logger.error("GameManager", "处理玩家信息更新事件失败:", error);
        this.handleEventError(error, "更新玩家界面失败");
      }
    });
  }

  // 设置地图相关事件
  setupMapEvents() {
    Logger.debug("GameManager", "设置地图相关事件监听");

    // 监听地图渲染器切换事件
    this.eventBus.on("map:renderer:changed", (type) => {
      try {
        Logger.info("GameManager", `地图渲染器切换事件: ${type}`);
        this.handleMapRendererChange(type);
      } catch (error) {
        Logger.error("GameManager", "处理地图渲染器切换事件失败:", error);
        this.handleEventError(error, "切换地图显示失败");
      }
    });

    // 监听GPS更新事件
    this.eventBus.on("gps:update", (gpsData) => {
      try {
        Logger.debug("GameManager", "GPS更新事件");
        this.handleGPSUpdate(gpsData);
      } catch (error) {
        Logger.error("GameManager", "处理GPS更新事件失败:", error);
        this.handleEventError(error, "更新GPS数据失败");
      }
    });
  }

  // 设置UI相关事件
  setupUIEvents() {
    Logger.debug("GameManager", "设置UI相关事件监听");

    try {
        // 初始化UI服务的任务事件监听
        this.uiService.initTaskEvents();
        
        // 监听任务相关事件
        this.eventBus.on('task:accept', (taskId) => {
            this.acceptTask(taskId);
        });
        
        this.eventBus.on('task:abandon', (taskId) => {
            this.abandonTask(taskId);
        });
        
        this.eventBus.on('task:complete', (taskId) => {
            this.completeTask(taskId);
        });
        
        Logger.info("GameManager", "UI事件监听设置完成");
    } catch (error) {
        Logger.error("GameManager", "设置UI事件监听失败:", error);
        this.handleEventError(error, "设置UI事件监听失败");
    }
  }

  // 处理玩家ID更新
  handlePlayerIdUpdate(newId) {
    Logger.info("GameManager", "处理玩家ID更新:", newId);
    
    // 更新相关服务
    this.wsManager.subscribeToTasks(newId);
    this.taskService.updatePlayerId(newId);
    
    // 重新加载数据
    this.playerService.loadPlayerInfo();
    this.taskService.loadTasks();
  }

  // 处理任务完成
  handleTaskCompletion(taskData) {
    Logger.info("GameManager", "处理任务完成:", taskData);
    
    // 更新词云
    this.wordcloudService.updateWordCloud();
    
    // 播放完成音效
    this.audioService.playSound("COMPLETE");
    
    // 显示完成通知
    this.uiService.showNotification({
      type: "SUCCESS",
      message: `任务 ${taskData.name} 已完成！`
    });
  }

  // 优化地图渲染器变更处理方法
  handleMapRendererChange(type) {
    Logger.info("GameManager", "处理地图渲染器变更:", type);
    
    try {
      // 更新按钮文本
      const mapSwitchBtn = document.getElementById('switchMapType');
      if (mapSwitchBtn) {
        const buttonText = mapSwitchBtn.querySelector('span');
        if (buttonText) {
          buttonText.textContent = `切换到${type === 'AMAP' ? 'Echarts' : '高德'}地图`;
        }
      }
    } catch (error) {
      Logger.error("GameManager", "处理地图渲染器变更失败:", error);
      this.handleEventError(error, "切换地图显示失败");
    }
  }

  // 优化GPS更新处理方法
  handleGPSUpdate(gpsData) {
    Logger.debug("GameManager", "处理GPS更新");
    
    if (!this.initialized) {
      Logger.warn("GameManager", "应用尚未完成初始化，暂存GPS更新");
      return;
    }
    
    try {
      if (this.mapService.currentRenderer) {
        this.mapService.currentRenderer.updatePosition(gpsData);
        this.mapService.currentRenderer.updateGPSInfo(gpsData);
      }
    } catch (error) {
      Logger.error("GameManager", "处理GPS更新失败:", error);
      this.handleEventError(error, "更新GPS数据失败");
    }
  }

  // 统一的事件错误处理
  handleEventError(error, userMessage) {
    Logger.error("GameManager", "事件处理错误:", error);
    
    // 显示用户友好的错误消息
    this.uiService.showNotification({
      type: "ERROR",
      message: userMessage || "操作失败，请重试"
    });
    
    // 记录错误
    ErrorHandler.handle(error, "GameManager.handleEventError");
  }

  setupDOMObserver() {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === "childList") {
          // 处理 DOM 变化
          this.handleDOMChanges(mutation.target);
        }
      });
    });

    // 配置观察选项
    const config = {
      childList: true,
      subtree: true,
    };

    // 开始观察
    observer.observe(document.body, config);
  }

  handleDOMChanges(target) {
    // 处理 DOM 变化的逻辑
    // Logger.debug("GameManager", "DOM changed:", target);
    // ... 其他处理逻辑 ...
  }

  // 添加新的渲染方法
  renderTaskList(tasks) {
    Logger.info("GameManager", "开始渲染任务列表，任务数量:", tasks.length);

    const container = document.querySelector(".task-list-swiper .swiper-wrapper");
    if (!container) {
      Logger.error("GameManager", "找不到任务列表容器");
      return;
    }

    try {
      if (!tasks || !tasks.length) {
        Logger.info("GameManager", "没有可用任务");
        container.innerHTML = `
                    <div class="swiper-slide">
                        <div class="empty-task">暂无可用任务</div>
                    </div>`;
      } else {
        Logger.debug("GameManager", "开始渲染任务卡片");
        const taskCards = tasks.map((task) => {
          try {
            return this.taskService.createAvailableTaskCard(task);
          } catch (err) {
            Logger.error("GameManager", "渲染单个任务卡片失败:", err, task);
            return "";
          }
        });

        container.innerHTML = taskCards.join("");
        Logger.debug("GameManager", "任务卡片渲染完成");
      }

      // 初始化滑动组件
      Logger.info("GameManager", "重新初始化滑动组件");
      this.taskService.initTaskSwipers();

      Logger.info("GameManager", "任务列表渲染完成");
    } catch (error) {
      Logger.error("GameManager", "渲染任务列表失败:", error);
      container.innerHTML = `
                <div class="swiper-slide">
                    <div class="error-task">加载任务失败: ${error.message}</div>
                </div>`;
    }
  }

  // 删除原有的 showTaskDetails 方法，改为调用 UIService
  handleTaskClick(taskData) {
    Logger.debug("GameManager", "处理任务点击:", taskData);
    this.uiService.showTaskDetails(taskData);
  }

  // 处理任务状态更新通知
  handleTaskStatusUpdate(data) {
    Logger.info("GameManager", "开始处理任务状态更新:", data);

    try {
      // 参数验证
      if (!data || !data.id) {
        Logger.error("GameManager", "无效的任务状态更新数据:", data);
        this.uiService.showNotification({
          type: "ERROR",
          message: "收到无效的任务状态更新"
        });
        return;
      }

      // 记录详细日志
      Logger.debug("GameManager", "任务状态更新详情:", {
        taskId: data.id,
        status: data.status,
        timestamp: new Date().toISOString()
      });

      // 更新任务服务中的状态
      this.taskService.updateTaskStatus(data).then(() => {
        Logger.debug("GameManager", "任务服务状态更新成功");
        
        // 通过UIService更新界面
        this.uiService.updateTaskStatus(data);
        
        // 播放相应的音效
        if (data.status === "COMPLETE") {
          this.audioService.playSound("COMPLETE");
        }
        
        // 发送状态更新事件
        this.eventBus.emit("task:status:updated", data);
        
        Logger.info("GameManager", "任务状态更新处理完成");
      }).catch(error => {
        Logger.error("GameManager", "更新任务状态失败:", error);
        this.handleEventError(error, "更新任务状态失败");
      });

    } catch (error) {
      Logger.error("GameManager", "处理任务状态更新错误:", error);
      this.handleEventError(error, "处理任务状态更新失败");
    }
  }

  // 修改销毁方法
  destroy() {
    this.swiperService.destroySwipers();
    this.wordcloudService.destroy();
    this.audioService.destroy();
    this.wsManager.disconnect();
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
    layer.msg("初始化失败，请刷新页面重试", {icon: 2});
  }
});

// 页面卸载前清理
window.addEventListener("beforeunload", () => {
  if (window.GameManager) {
    window.GameManager.destroy();
  }
});
