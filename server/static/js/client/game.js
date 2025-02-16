/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-29 16:43:22
 * @LastEditTime: 2025-02-16 14:37:34
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 14:41:57
 * @LastEditTime: 2025-02-16 14:36:45
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
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

// 在文件开头声明全局变量
let taskManager;

// 游戏管理类，程序入口
class GameManager {
  constructor() {
    Logger.info("GameManager", "构造函数开始");

    // 1. 初始化核心组件
    this.api = new APIClient(SERVER);
    this.eventBus = new EventBus();
    this.store = new Store();

    // 2. 初始化 PlayerService (最先初始化)
    this.playerService = new PlayerService(this.api, this.eventBus, this.store);
    
    // 3. 初始化其他依赖 PlayerService 的服务
    this.templateService = new TemplateService();
    this.taskService = new TaskService(
      this.api,
      this.eventBus,
      this.store,
      this.playerService, // 传入 playerService
      this.templateService
    );

    this.wordcloudService = new WordcloudService(
      this.api,
      this.eventBus,
      this.store,
      this.playerService // 传入 playerService
    );

    // 4. 初始化其他服务
    this.swiperService = new SwiperService();
    this.mapService = new MapService(this.api, this.eventBus, this.store);
    
    // 5. 设置事件监听
    this.setupEventListeners();

    // 初始化基础属性
    this.activeTasksSwiper = null;
    this.taskListSwiper = null;
    this.loading = false;

    // 初始化WebSocket管理器
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
      Logger.error("GameManager", "WebSocket管理器初始化失败:", error);
      layer.msg("WebSocket连接失败，部分功能可能不可用", {icon: 2});
    }

    // 加载玩家信息 - 移到API初始化之后
    this.loadPlayerInfo();

    // 添加事件监听
    this.eventBus.on("currentTasks:updated", this.handleCurrentTasksUpdated.bind(this));
    this.eventBus.on("tasks:error", this.handleTaskError.bind(this));

    // 在构造函数中调用
    this.setupDOMObserver();

    // 添加新的服务初始化
    this.nfcService = new NFCService(this.api, this.eventBus, this.store);
    this.uiService = new UIService(this.eventBus, this.store, this.templateService);

    // 添加音频服务
    this.audioService = new AudioService();
    
    // 初始化音频
    this.audioService.init().catch(error => {
      Logger.warn("GameManager", "音频初始化失败，继续无声模式:", error);
    });

    Logger.info("GameManager", "构造函数完成");
  }
  // 初始化应用
  async initializeApplication() {
    try {
      Logger.info("[GameManager]", "初始化应用开始");
      
      // 先加载任务列表
      await this.taskService.loadTasks();
      Logger.info("[GameManager]", "任务列表加载完成");
      
      // 再加载当前任务
      await this.taskService.loadCurrentTasks();
      Logger.info("[GameManager]", "当前任务加载完成");
      
      // 初始化滑动组件
      this.swiperService.initSwipers();
      Logger.info("[GameManager]", "初始化应用完成");
    } catch (error) {
      Logger.error("[GameManager]", "初始化应用失败:", error);
      layer.msg('初始化应用失败，请刷新页面重试', {icon: 2});
      ErrorHandler.handle(error, 'GameManager.initializeApplication');
    }
  }
  // 处理NFC任务更新通知
  handleTaskUpdate(data) {
    Logger.info("GameManager", "开始处理NFC任务更新:", data);

    if (!data || !data.type) {
      Logger.error("GameManager", "无效的任务更新数据:", data);
      this.uiService.showNotification({
        type: "ERROR",
        message: "收到无效的任务更新",
      });
      return;
    }

    Logger.debug("GameManager", "处理任务类型:", data.type);
    switch (data.type) {
      case "IDENTITY":
        Logger.info("GameManager", "处理身份识别更新");
        this.playerService.setPlayerId(data.player_id);
        this.loadPlayerInfo();
        this.refreshTasks();
        break;

      case "NEW_TASK":
      case "COMPLETE":
      case "CHECK":
        Logger.info("GameManager", "处理任务状态更新");
        this.refreshTasks();
        this.playTaskSound(data.type);
        break;

      case "ALREADY_COMPLETED":
      case "REJECT":
      case "CHECKING":
        Logger.info("GameManager", "处理通知消息");
        break;

      case "ERROR":
        Logger.info("GameManager", "处理错误消息");
        this.playErrorSound();
        break;

      default:
        Logger.info("GameManager", "未知的任务类型:", data.type);
    }

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

  // 修改loadTasks方法，使用taskService
  async loadTasks() {
    try {
      const tasks = await this.taskService.loadTasks();
      this.uiService.renderTaskList(tasks);
    } catch (error) {
      Logger.error("GameManager", "加载任务失败:", error);
      this.uiService.showNotification({
        type: 'ERROR',
        message: '加载任务失败'
      });
    }
  }

  // 修改渲染方法，使用templateService
  renderTasks(tasks) {
    Logger.info("[Game]", "开始渲染任务:", tasks);

    if (!tasks || !Array.isArray(tasks)) {
      Logger.error("[Game]", "无效的任务数据");
      return;
    }

    // 获取容器
    const container = document.querySelector(".active-tasks-swiper .swiper-wrapper");
    if (!container) {
      Logger.error("[Game]", "任务容器没有发现. DOM structure:", document.body.innerHTML);
      return;
    }

    Logger.info("[Game]", "发现容器渲染任务");

    // 使用 TemplateService 渲染任务
    if (!tasks.length) {
      Logger.info("[Game]", "没有任务");
      container.innerHTML = this.templateService.getEmptyTaskTemplate();
    } else {
      Logger.info("[Game]", "渲染任务卡片");
      container.innerHTML = tasks
        .map((task) => {
          const card = this.templateService.createActiveTaskCard(task);
          Logger.debug("[Game]", "创建任务卡片:", task.id, card.outerHTML);
          return card.outerHTML;
        })
        .join("");
    }

    Logger.info("[Game]", "初始化任务滑动组件");
    this.taskService.initTaskSwipers();
  }

  // 修改 loadCurrentTasks 方法
  async loadCurrentTasks() {
    try {
      Logger.info("[GameManager]", "加载进行中的任务");
      const currentTasks = await this.taskService.getCurrentTasks(this.playerService.getPlayerId());
      Logger.debug("[GameManager]", "进行中任务加载完成:", currentTasks);
      this.renderCurrentTasks(currentTasks);
    } catch (error) {
      Logger.error("[GameManager]", "加载进行中的任务失败:", error);
      this.showError("active-tasks-wrapper", "加载任务失败");
    }
  }

  // 修改 renderCurrentTasks 方法
  renderCurrentTasks(tasks) {
    Logger.info("[GameManager]", "开始渲染进行中的任务");
    const container = document.querySelector(".active-tasks-swiper .swiper-wrapper");
    if (!container) {
      Logger.error("[GameManager]", "找不到进行中任务容器");
      return;
    }

    try {
      if (!tasks || !Array.isArray(tasks) || tasks.length === 0) {
        Logger.info("[GameManager]", "没有进行中的任务");
        container.innerHTML = this.templateService.getEmptyTaskTemplate();
      } else {
        Logger.info("[GameManager]", `渲染 ${tasks.length} 个进行中的任务`);
        const taskCards = tasks.map(task => {
          try {
            return this.taskService.createActiveTaskCard(task);
          } catch (err) {
            Logger.error("[GameManager]", "渲染单个进行中任务失败:", err, task);
            return null;
          }
        }).filter(card => card !== null);

        container.innerHTML = taskCards.map(card => `
          <div class="swiper-slide">
            <div class="task-panel">
              ${card.outerHTML}
            </div>
          </div>
        `).join('');
      }

      // 初始化滑动组件
      Logger.info("[GameManager]", "初始化进行中任务滑动组件");
      this.taskService.initTaskSwipers();
      
    } catch (error) {
      Logger.error("[GameManager]", "渲染进行中任务失败:", error);
      container.innerHTML = `
        <div class="swiper-slide">
          <div class="error-task">加载进行中任务失败: ${error.message}</div>
        </div>`;
    }
  }

  // 显示错误信息
  showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `<div class="empty-tip">${message}</div>`;
    }
  }

  // 添加事件监听器初始化方法
  initTaskEvents() {
    document.addEventListener("click", (e) => {
      // 处理接受任务按钮点击
      if (e.target.closest(".accept-task")) {
        const taskId = e.target.closest(".accept-task").dataset.taskId;
        this.acceptTask(taskId);
      }
      // 处理放弃任务按钮点击
      if (e.target.closest(".abandon-task")) {
        const taskId = e.target.closest(".abandon-task").dataset.taskId;
        this.abandonTask(taskId);
      }
    });
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
    layer.confirm(
      "确定要放弃这个任务吗？",
      {
        btn: ["确定", "取消"],
      },
      async () => {
        try {
          const response = await fetch(`${SERVER}/api/tasks/${taskId}/abandon`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "application/json",
            },
            body: JSON.stringify({
              player_id: this.playerService.getPlayerId(),
            }),
          });

          const result = await response.json();

          if (result.code === 0) {
            layer.msg(result.msg, { icon: 1 });
            await this.refreshTasks();
          } else {
            layer.msg(result.msg, { icon: 2 });
          }
        } catch (error) {
          Logger.error("放弃任务失败:", error);
          layer.msg("放弃任务失败，请检查网络连接", { icon: 2 });
        }
      }
    );
  }

  // 完成任务
  async completeTask(taskId) {
    try {
      const response = await fetch(`${SERVER}/api/tasks/${taskId}/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          player_id: this.playerService.getPlayerId(),
        }),
      });

      const result = await response.json();

      if (result.code === 0) {
        layer.msg(`${result.msg}，获得 ${result.data.points} 点经验`, { icon: 1 });
        await this.refreshTasks();
      } else {
        layer.msg(result.msg, { icon: 2 });
      }
    } catch (error) {
      Logger.error("完成任务失败:", error);
      layer.msg("完成任务失败，请检查网络连接", { icon: 2 });
    }
  }

  // 刷新所有任务
  async refreshTasks() {
    try {
      await Promise.all([this.taskService.loadTasks()]);
    } catch (error) {
      Logger.error("刷新任务失败:", error);
      layer.msg("刷新任务失败", { icon: 2 });
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

  // 添加加载角色信息的方法
  async loadPlayerInfo() {
    try {
      if (!this.api) {
        throw new Error("API client not initialized");
      }

      const result = await this.api.getPlayerInfo(this.playerService.getPlayerId());

      if (result.code === 0) {
        const playerData = result.data;
        this.updatePlayerUI(playerData);
      } else {
        Logger.error("加载角色信息失败:", result.msg);
        this.showPlayerError();
      }
    } catch (error) {
      Logger.error("加载角色信息失败:", error);
      this.showPlayerError();
    }
  }

  // 新增方法：更新玩家UI
  updatePlayerUI(playerData) {
    document.getElementById("playerName").textContent = playerData.player_name;
    document.getElementById("playerPoints").textContent = playerData.points;

    // 更新等级和经验条
    const levelElement = document.querySelector(".level");
    const expElement = document.querySelector(".exp");
    if (levelElement) {
      levelElement.textContent = `${playerData.level}/100`;
    }
    if (expElement) {
      expElement.textContent = `${playerData.experience}/99999`;
    }

    // 更新经验条
    const expBarInner = document.querySelector(".exp-bar-inner");
    if (expBarInner) {
      const expPercentage = (playerData.experience / 99999) * 100;
      expBarInner.style.width = `${Math.min(100, expPercentage)}%`;
    }
  }

  // 新增方法：显示玩家错误状态
  showPlayerError() {
    document.getElementById("playerName").textContent = "加载失败";
    document.getElementById("playerPoints").textContent = "0";

    const levelElement = document.querySelector(".level");
    const expElement = document.querySelector(".exp");
    if (levelElement) {
      levelElement.textContent = "0/100";
    }
    if (expElement) {
      expElement.textContent = "0/99999";
    }

    const expBarInner = document.querySelector(".exp-bar-inner");
    if (expBarInner) {
      expBarInner.style.width = "0%";
    }
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
    Logger.info("GameManager", "设置事件监听器");

    // 监听任务加载完成事件
    this.eventBus.on("tasks:loaded", (tasks) => {
      Logger.info("GameManager", "收到任务加载完成事件，任务数量:", tasks.length);
      this.renderTaskList(tasks);
    });

    // 监听当前任务更新事件
    this.eventBus.on("currentTasks:updated", (tasks) => {
      Logger.info("[GameManager] 当前任务更新事件:", tasks);
      this.renderCurrentTasks(tasks);
    });

    // 监听任务错误事件
    this.eventBus.on("tasks:error", (error) => {
      Logger.error("[GameManager] 任务错误事件:", error);
      layer.msg(error.message || "任务加载失败", { icon: 2 });
    });

    // 监听任务完成事件，更新文字云
    this.eventBus.on("task:completed", () => {
        this.wordcloudService.updateWordCloud();
    });

    // 监听玩家ID更新
    this.eventBus.on('player:id-updated', (newId) => {
      // 更新相关服务
      this.wsManager.subscribeToTasks(newId);
      this.taskService.updatePlayerId(newId);
      // 重新加载数据
      this.loadPlayerInfo();
      this.taskService.loadTasks();
    });

    // 添加地图相关事件监听
    this.eventBus.on('map:renderer:changed', (type) => {
      Logger.info('GameManager', `地图渲染器已切换到: ${type}`);
    });
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

  // 添加回任务状态更新处理方法
  handleTaskStatusUpdate(data) {
    Logger.info("GameManager", "处理任务状态更新:", data);

    if (!data || !data.id) {
      Logger.error("GameManager", "无效的任务状态更新数据");
      this.uiService.showNotification({
        type: 'ERROR',
        message: '收到无效的任务状态更新'
      });
      return;
    }

    try {
      // 更新任务状态
      this.taskService.updateTaskStatus(data);
      
      // 显示状态更新通知
      this.uiService.showNotification({
        type: data.status,
        message: `任务状态更新: ${this.getStatusText(data.status)}`
      });

      // 如果任务完成，播放音效
      if (data.status === 'COMPLETE') {
        this.playTaskSound('COMPLETE');
      }

      // 刷新任务列表
      this.loadCurrentTasks();
      
      Logger.debug("GameManager", "任务状态更新处理完成");
    } catch (error) {
      Logger.error("GameManager", "处理任务状态更新错误:", error);
      this.uiService.showNotification({
        type: 'ERROR',
        message: '处理任务状态更新失败'
      });
    }
  }

  // 修改销毁方法
  destroy() {
    this.swiperService.destroySwipers();
    this.wordcloudService.destroy();
    this.audioService.destroy();
    this.wsManager.disconnect();
    Logger.info("GameManager", "资源清理完成");
  }
}

// 页面初始化代码
document.addEventListener("DOMContentLoaded", async () => {
  Logger.info("GameManager", "页面加载开始");
  Logger.debug("GameManager", "当前地图渲染类型:", MAP_CONFIG.RENDER_TYPE);

  // 创建全局管理器实例
  window.GameManager = new GameManager();
  Logger.info("GameManager", "GameManager 已创建");

  // 初始化应用
  await window.GameManager.initializeApplication();
  window.GameManager.initTaskEvents();

  // 加载任务数据
  await Promise.all([window.GameManager.taskService.loadTasks(), window.GameManager.loadCurrentTasks()]);

  // 初始化文字云
  await window.GameManager.initWordCloud();

  // 初始化地图
  await window.GameManager.mapService.initMap();

  // 设置 WebSocket 管理器并订阅 GPS 更新
  window.GameManager.mapService.setWebSocketManager(window.GameManager.wsManager);
  window.GameManager.wsManager.subscribeToGPS(window.GameManager.playerService.getPlayerId());

  Logger.info("GameManager", "页面初始化完成");
});

// 页面卸载前清理
window.addEventListener("beforeunload", () => {
  if (window.GameManager) {
    window.GameManager.destroy();
  }
});
