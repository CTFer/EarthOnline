/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 14:41:57
 * @LastEditTime: 2025-02-13 22:12:35
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */

import { SERVER, MAP_CONFIG } from "../config/config.js";
import WebSocketManager from "../function/WebSocketManager.js";
import MapSwitcher from "../function/MapSwitcher.js";
import APIClient from "./core/api.js"; // 导入默认导出的类
import TemplateService from "./service/templateService.js";
import TaskService from "./service/taskService.js";
import EventBus from "./core/eventBus.js";
import Store from "./core/store.js";
import Logger from "../utils/logger.js";
import SwiperService from './service/swiperService.js';
import { ErrorHandler } from './core/errorHandler.js';

// 在文件开头声明全局变量
let taskManager;
let gpsManager;

// 游戏管理类
class GameManager {
  constructor() {
    Logger.info("GameManager", "构造函数开始");

    // 初始化API客户端
    this.api = new APIClient(SERVER);
    // 初始化基础属性
    this.activeTasksSwiper = null;
    this.taskListSwiper = null;
    this.playerId = localStorage.getItem("playerId") || "1";
    this.loading = false;
    // 初始化事件总线
    this.eventBus = new EventBus();

    // 初始化Store
    this.store = new Store();

    // 先创建templateService
    this.templateService = new TemplateService();

    // 然后将templateService传给taskService
    this.taskService = new TaskService(
      this.api,
      this.eventBus,
      this.store,
      this.playerId,
      this.templateService
    );

    // 初始化WebSocket管理器
    this.wsManager = new WebSocketManager();

    // 设置事件监听
    this.wsManager.subscribeToTasks(this.playerId);
    this.wsManager.onTaskUpdate(this.handleTaskStatusUpdate.bind(this));
    this.wsManager.onNFCTaskUpdate(this.handleTaskUpdate.bind(this));
    this.wsManager.onTagsUpdate(() => this.updateWordCloud());

    // 加载玩家信息 - 移到API初始化之后
    this.loadPlayerInfo();

    // 添加事件监听
    this.eventBus.on("currentTasks:updated", this.handleCurrentTasksUpdated.bind(this));
    this.eventBus.on("tasks:error", this.handleTaskError.bind(this));

    // 在构造函数中调用
    this.setupDOMObserver();
    // 设置事件监听 - 确保这行代码存在
    this.setupEventListeners();

    // 初始化swiperService
    this.swiperService = new SwiperService();

    Logger.info("GameManager", "构造函数完成");
  }

  // 处理NFC任务更新通知
  handleTaskUpdate(data) {
    Logger.info("GameManager", "开始处理NFC任务更新:", data);

    if (!data || !data.type) {
      Logger.error("GameManager", "无效的任务更新数据:", data);
      this.showNotification({
        type: "ERROR",
        message: "收到无效的任务更新",
      });
      return;
    }

    Logger.debug("GameManager", "处理任务类型:", data.type);
    switch (data.type) {
      case "IDENTITY":
        Logger.info("GameManager", "处理身份识别更新");
        this.playerId = data.player_id;
        localStorage.setItem("playerId", data.player_id);
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
    this.showNotification(data);
    Logger.debug("GameManager", "通知显示完成");
  }

  // 播放任务相关音效
  playTaskSound(type) {
    const audio = new Audio();
    switch (type) {
      case "NEW_TASK":
        audio.src = "/static/sounds/new_task.mp3";
        break;
      case "COMPLETE":
        audio.src = "/static/sounds/complete.mp3";
        break;
      case "CHECK":
        audio.src = "/static/sounds/check.mp3";
        break;
    }
    audio.play().catch((e) => Logger.error("GameManager", "音效播放失败:", e));
  }

  // 播放错误音效
  playErrorSound() {
    const audio = new Audio("/static/sounds/error.mp3");
    audio.play().catch((e) => Logger.error("GameManager", "音效播放失败:", e));
  }

  // 显示通知
  showNotification(data) {
    Logger.info("GameManager", "开始显示通知:", data);
    const typeInfo = data.task?.task_type ? gameUtils.getTaskTypeInfo(data.task.task_type) : { color: "#009688", icon: "layui-icon-notice", text: "系统消息" };

    try {
      layer.open({
        type: 1,
        title: false,
        closeBtn: true,
        shadeClose: true,
        area: ["500px", "auto"],
        skin: "layui-layer-nobg",
        content: `
                    <div class="task-notification">
                        <div class="task-header">
                            <div class="task-icon" style="color: ${typeInfo.color}">
                                <i class="layui-icon ${typeInfo.icon}"></i>
                            </div>
                            <div class="task-title">
                                <h3>${data.task?.name || "系统消息"}</h3>
                                <small>${typeInfo.text}</small>
                            </div>
                        </div>
                        ${
                          data.task?.description
                            ? `
                            <div class="task-description">${data.task.description}</div>
                        `
                            : ""
                        }
                        <div class="task-status">
                            <span class="status-badge" style="background: ${this.getStatusColor(data.type)}">
                                ${this.getStatusText(data.type)}
                            </span>
                            <span class="task-message">${data.message || this.getDefaultMessage(data.type)}</span>
                        </div>
                        ${
                          data.task?.rewards
                            ? `
                            <div class="task-rewards">
                                <div class="reward-item">
                                    <i class="layui-icon layui-icon-diamond"></i>
                                    <span>经验 +${data.task.points || 0}</span>
                                </div>
                                <div class="reward-item">
                                    <i class="layui-icon layui-icon-dollar"></i>
                                    <span>奖励 ${data.task.rewards}</span>
                                </div>
                            </div>
                        `
                            : ""
                        }
                        ${
                          data.timestamp
                            ? `
                            <div class="task-time">
                                打卡时间: ${new Date(data.timestamp * 1000).toLocaleString()}
                            </div>
                        `
                            : ""
                        }
                    </div>
                `,
      });
      Logger.info("GameManager", "通知显示成功");
    } catch (error) {
      Logger.error("GameManager", "显示通知失败:", error);
    }
  }

  // 获取默认消息
  getDefaultMessage(type) {
    switch (type) {
      case "IDENTITY":
        return "身份识别成功";
      case "NEW_TASK":
        return "新任务已添加";
      case "COMPLETE":
        return "任务完成";
      case "ALREADY_COMPLETED":
        return "该任务已完成";
      case "CHECKING":
        return "任务正在审核中";
      case "REJECTED":
        return "任务被驳回";
      case "ERROR":
        return "任务处理出错";
      default:
        return "收到任务更新";
    }
  }

  // 获取消息图标
  getMessageIcon(type) {
    switch (type) {
      case "IDENTITY":
      case "NEW_TASK":
      case "COMPLETE":
        return 1; // 成功
      case "ALREADY_COMPLETED":
      case "CHECKING":
        return 0; // 信息
      case "REJECTED":
      case "ERROR":
        return 2; // 错误
      default:
        return 0; // 默认信息
    }
  }

  // 处理任务状态更新
  handleTaskStatusUpdate(data) {
    Logger.info("TaskManager", "处理任务状态更新:", data);

    if (!data || !data.id) {
        Logger.error("TaskManager", "无效的任务状态更新数据");
        return;
    }

    try {
        // 通过事件总线发送任务状态更新事件
        this.eventBus.emit('task:status:update', data);
    } catch (error) {
        Logger.error("TaskManager", "处理任务状态更新错误:", error);
    }
  }

  // 修改loadTasks方法，使用taskService
  async loadTasks() {
    try {
      Logger.info("[Game]", "加载任务");
      // 使用 TaskService 加载任务
      const tasks = await this.taskService.loadTasks();
      // 渲染任务列表
      this.renderTasks(tasks);
    } catch (error) {
      Logger.error("[Game]", "加载任务失败:", error);
      layer.msg("加载任务失败", { icon: 2 });
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

  // 显示任务详情
  showTaskDetails(taskData) {
    const { typeInfo, rewards } = taskData;
    Logger.debug(typeInfo);
    layui.use("layer", function () {
      const layer = layui.layer;

      layer.open({
        type: 1,
        title: false,
        closeBtn: 1,
        shadeClose: true,
        skin: "task-detail-layer",
        area: ["600px", "auto"],
        content: `
                    <div class="task-detail-popup">
                        <div class="task-detail-header" style="background-color: ${typeInfo.color}">
                            <div class="task-type-badge" style="background: ${typeInfo.color}; color: ${typeInfo.color}">
                                <i class="layui-icon ${typeInfo.icon}"></i>
                                <span>${typeInfo.text}</span>
                            </div>
                            <h2 class="task-name">${taskData.name}</h2>
                        </div>
                        <div class="task-detail-content">
                            <div class="detail-section">
                                <h3>任务描述</h3>
                                <p>${taskData.description}</p>
                            </div>
                            
                            <div class="detail-section">
                                <h3>任务信息</h3>
                                <div class="info-grid">
                                    <div class="info-item">
                                        <span class="label">任务范围</span>
                                        <span class="value">${taskData.task_scope || "无限制"}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">体力消耗</span>
                                        <span class="value">${taskData.stamina_cost}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">时间限制</span>
                                        <span class="value">${taskData.limit_time ? `${Math.floor(taskData.limit_time / 3600)}小时` : "无限制"}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">可重复次数</span>
                                        <span class="value">${taskData.repeat_time || (taskData.repeatable ? "无限" : "1")}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="detail-section">
                                <h3>任务奖励</h3>
                                <div class="rewards-grid">
                                    ${
                                      rewards.exp > 0
                                        ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-star"></i>
                                            <span>${rewards.exp} 经验</span>
                                        </div>
                                    `
                                        : ""
                                    }
                                    ${
                                      rewards.points > 0
                                        ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-diamond"></i>
                                            <span>${rewards.points} 积分</span>
                                        </div>
                                    `
                                        : ""
                                    }
                                    ${
                                      rewards.cards.length > 0
                                        ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-picture"></i>
                                            <span>${rewards.cards.length}张卡片</span>
                                        </div>
                                    `
                                        : ""
                                    }
                                    ${
                                      rewards.medals.length > 0
                                        ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-medal"></i>
                                            <span>${rewards.medals.length}枚勋章</span>
                                        </div>
                                    `
                                        : ""
                                    }
                                </div>
                            </div>
                            
                            ${
                              taskData.parent_task_id
                                ? `
                                <div class="detail-section">
                                    <h3>前置任务</h3>
                                    <p>需要完成任务ID: ${taskData.parent_task_id}</p>
                                </div>
                            `
                                : ""
                            }
                        </div>
                        <div class="task-detail-footer">
                            <button class="accept-task-btn" onclick="taskManager.acceptTask(${taskData.id}); layer.closeAll();">
                                <i class="layui-icon layui-icon-ok"></i>
                                接受任务
                            </button>
                        </div>
                    </div>
                `,
      });
    });
  }

  // 修改 loadCurrentTasks 方法
  async loadCurrentTasks() {
    try {
      Logger.info("[GameManager]", "加载进行中的任务");
      const currentTasks = await this.taskService.getCurrentTasks(this.playerId);
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
      ErrorHandler.handle(error, 'TaskManager.initializeApplication');
    }
  }

  // 接受任务
  async acceptTask(taskId) {
    try {
      Logger.info("[GameManager]", "开始接受任务", taskId);
      
      if (!taskId) {
        throw new Error("任务ID不能为空");
      }

      const result = await this.taskService.acceptTask(taskId, this.playerId);
      
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
      ErrorHandler.handle(error, 'TaskManager.acceptTask');
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
              player_id: this.playerId,
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
          player_id: this.playerId,
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

      const result = await this.api.getPlayerInfo(this.playerId);

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
  initWordCloud() {
    Logger.info("GameManager", "初始化文字云开始");
    const wordCloudChart = echarts.init(document.getElementById("wordCloudContainer"));

    // 模拟数据
    const testData = [
      // 头衔（较大字体，金色）
      { name: "尿不湿守护者", value: 100, textStyle: { color: "#ffd700", fontSize: 32 } },
      { name: "爬行先锋", value: 90, textStyle: { color: "#ffd700", fontSize: 28 } },

      // 荣誉（中等字体，银色）
      { name: "卫生纸摧毁达人", value: 80, textStyle: { color: "#c0c0c0" } },
      { name: "干饭小能手", value: 75, textStyle: { color: "#c0c0c0" } },
      { name: "玩具保护使者", value: 70, textStyle: { color: "#c0c0c0" } },

      // 个人标签（较小字体，青色系）
      { name: "热心干饭", value: 60, textStyle: { color: "#8aa2c1" } },
      { name: "推车出行", value: 55, textStyle: { color: "#8aa2c1" } },
      { name: "吃奶能手", value: 50, textStyle: { color: "#8aa2c1" } },
      { name: "植树达人", value: 45, textStyle: { color: "#8aa2c1" } },
      { name: "节水卫士", value: 40, textStyle: { color: "#8aa2c1" } },
      { name: "夜间嚎叫者", value: 35, textStyle: { color: "#8aa2c1" } },
      { name: "米粉爱好者", value: 30, textStyle: { color: "#8aa2c1" } },
    ];

    const option = {
      backgroundColor: "transparent",
      tooltip: {
        show: true,
        formatter: function (params) {
          return params.data.name;
        },
      },
      series: [
        {
          type: "wordCloud",
          shape: "circle",
          left: "center",
          top: "center",
          width: "100%",
          height: "100%",
          right: null,
          bottom: null,
          sizeRange: [16, 50],
          rotationRange: [-45, 45],
          rotationStep: 45,
          gridSize: 8,
          drawOutOfBound: false,
          layoutAnimation: true,
          textStyle: {
            fontFamily: "Microsoft YaHei",
            fontWeight: "bold",
            color: function () {
              return "rgb(" + [Math.round(Math.random() * 160) + 60, Math.round(Math.random() * 160) + 60, Math.round(Math.random() * 160) + 60].join(",") + ")";
            },
          },
          emphasis: {
            textStyle: {
              shadowBlur: 10,
              shadowColor: "rgba(255, 196, 71, 0.5)",
            },
          },
          data: testData,
        },
      ],
    };

    wordCloudChart.setOption(option);
    Logger.info("GameManager", "文字云初始化完成");

    // 响应窗口大小变化
    window.addEventListener("resize", function () {
      wordCloudChart.resize();
    });

    // 将图表实例存储在全局变量中，以便后续更新
    window.wordCloudChart = wordCloudChart;
  }

  // 更新文字云数据
  async updateWordCloud() {
    try {
      // TODO: 替换为实际的API调用
      const result = await this.api.getWordCloud();

      if (window.wordCloudChart && data.success) {
        window.wordCloudChart.setOption({
          series: [
            {
              data: data.tags,
            },
          ],
        });
      }
    } catch (error) {
      this.api.handleApiError(error, "updateWordCloud");
    }
  }

  // 添加事件处理方法
  handleCurrentTasksUpdated(tasks) {
    Logger.info("[Game]", "Current tasks updated:", tasks);
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
    Logger.debug("GameManager", "DOM changed:", target);
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
}

// 页面初始化代码
document.addEventListener("DOMContentLoaded", async () => {
  Logger.info("GameManager", "页面加载开始");
  Logger.debug("GameManager", "当前地图渲染类型:", MAP_CONFIG.RENDER_TYPE);

  // 创建全局管理器实例
  window.taskManager = new GameManager();
  Logger.info("GameManager", "GameManager 已创建");

  // 初始化应用
  await window.taskManager.initializeApplication();
  window.taskManager.initTaskEvents();

  // 加载任务数据
  await Promise.all([window.taskManager.taskService.loadTasks(), window.taskManager.loadCurrentTasks()]);

  // 初始化文字云
  window.taskManager.initWordCloud();

  // 初始化地图切换器
  window.mapSwitcher = new MapSwitcher();

  // 设置 WebSocket 管理器并订阅 GPS 更新
  window.mapSwitcher.setWebSocketManager(window.taskManager.wsManager);
  window.taskManager.wsManager.subscribeToGPS(window.taskManager.playerId);

  Logger.info("GameManager", "页面初始化完成");
});

// 页面卸载前清理
window.addEventListener("beforeunload", () => {
  if (window.taskManager) {
    window.taskManager.swiperService.destroySwipers();
  }
});
