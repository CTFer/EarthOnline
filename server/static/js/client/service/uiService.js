/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:39
 * @LastEditTime: 2025-03-03 11:44:46
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */
import Logger from "../../utils/logger.js";
import { TASK_EVENTS, UI_EVENTS, AUDIO_EVENTS, MAP_EVENTS, WS_EVENTS, PLAYER_EVENTS, SHOP_EVENTS } from "../config/events.js";
import { WS_STATE, WS_CONFIG } from "../config/wsConfig.js";
import { gameUtils } from "../../utils/utils.js";
import NotificationService from "./notificationService.js";
class UIService {
  constructor(eventBus, store, templateService, taskService, playerService,swiperService, notificationService) {
    this.eventBus = eventBus;
    this.store = store;
    this.templateService = templateService;
    this.taskService = taskService;
    this.playerService = playerService;
    this.swiperService = swiperService;
    this.notificationService = new NotificationService();
    this.observers = new Map();
    this.componentId = "uiService";
    // 初始化默认状态
    this.defaultState = {
      initialized: false,
      notifications: [],
      taskCards: new Map(),
      modals: new Map(),
      wsStatus: "disconnected",
      uiComponents: {
        taskList: {
          visible: true,
          expanded: false,
        },
        notifications: {
          visible: true,
          position: "top-right",
        },
        modals: {
          activeModal: null,
        },
        playerInfo: {
          visible: true,
          loading: false,
          error: null,
        },
      },
    };

    // 初始化状态
    this.state = this.loadState();

    // 设置状态监听
    this.setupStateListeners();
    // 地图相关状态
    this.mapRenderType = localStorage.getItem('mapType') || 'ECHARTS';
    this.mapTimeRange = localStorage.getItem('mapTimeRange') || 'today';
    this.customStartTime = null;
    this.customEndTime = null;

    Logger.info("UIService", "初始化UI服务");
  }

  // 加载状态
  loadState() {
    const savedState = this.store.getComponentState(this.componentId);
    return { 
        ...this.defaultState, 
        ...savedState,
        mapRenderType: savedState.mapRenderType || 'ECHARTS',
        mapTimeRange: savedState.mapTimeRange || 'today',
        customStartTime: savedState.customStartTime || null,
        customEndTime: savedState.customEndTime || null,
    };
  }

  // 保存状态
  saveState() {
    this.store.setComponentState(this.componentId, {
        ...this.state,
        mapRenderType: this.state.mapRenderType,
        mapTimeRange: this.state.mapTimeRange,
        customStartTime: this.state.customStartTime,
        customEndTime: this.state.customEndTime,
    });
  }

  // 设置状态监听器 这个函数在页面刷新时不应该运行的
  setupStateListeners() {
    this.store.subscribe("component", this.componentId, async (newState, oldState) => {
        Logger.debug("UIService", "状态更新:", { old: oldState, new: newState });
    });
  }

  // 更新状态
  updateState(newState) {
    this.state = { ...this.state, ...newState };
    this.saveState();
  }

  // 处理通知状态变化
  handleNotificationsStateChange(notifications) {
    try {
      // 更新通知UI
      this.renderNotifications(notifications);
    } catch (error) {
      Logger.error("UIService", "处理通知状态变化失败:", error);
    }
  }

  // 处理任务卡片状态变化
  handleTaskCardsStateChange(taskCards) {
    try {
      // 更新任务卡片UI
      // this.renderTaskCards(taskCards);
    } catch (error) {
      Logger.error("UIService", "处理任务卡片状态变化失败:", error);
    }
  }

  // 处理UI组件状态变化
  handleUIComponentsStateChange(uiComponents) {
    try {
      // 更新任务列表可见性
      if (uiComponents.taskList) {
        const taskListContainer = document.querySelector(".task-list-container");
        if (taskListContainer) {
          taskListContainer.style.display = uiComponents.taskList.visible ? "block" : "none";
          taskListContainer.classList.toggle("expanded", uiComponents.taskList.expanded);
        }
      }

      // 更新通知面板位置
      if (uiComponents.notifications) {
        const notificationPanel = document.querySelector(".notification-panel");
        if (notificationPanel) {
          notificationPanel.className = `notification-panel ${uiComponents.notifications.position}`;
          notificationPanel.style.display = uiComponents.notifications.visible ? "block" : "none";
        }
      }

      // 处理模态框状态
      if (uiComponents.modals && uiComponents.modals.activeModal) {
        this.handleModalState(uiComponents.modals.activeModal);
      }
    } catch (error) {
      Logger.error("UIService", "处理UI组件状态变化失败:", error);
    }
  }

  // 处理模态框状态
  handleModalState(modalState) {
    try {
      const { id, visible, data } = modalState;
      if (visible) {
        this.showModal(id, data);
      } else {
        this.hideModal(id);
      }
    } catch (error) {
      Logger.error("UIService", "处理模态框状态失败:", error);
    }
  }

  /**
   * 初始化UI服务
   * @returns {Promise<void>}
   */
  async initialize() {
    Logger.info("UIService", "开始初始化UI服务");
    try {
      // 初始化状态显示元素
      this.initStatusElements();
      // 初始化DOM观察器
      this.setupDOMObserver();
      // 初始化事件监听
      this.initEvents();
      // 初始化任务事件
      this.initTaskEvents();
      // 初始化玩家信息UI
      await this.initPlayerInfoUI();

      this.mapRenderType = this.state.mapRenderType;
      this.mapTimeRange = this.state.mapTimeRange;
      this.customStartTime = this.state.customStartTime;
      this.customEndTime = this.state.customEndTime;

      Logger.info("UIService", "UI服务初始化完成");
    } catch (error) {
      Logger.error("UIService", "UI服务初始化失败:", error);
      throw error;
    }
  }

  /**
   * 初始化所有事件监听
   * @private
   */
  initEvents() {
    Logger.debug("UIService", "初始化事件监听");

    this.setupEventListeners();
    this.initShopEvents();
    this.initPlayerEvents();

    Logger.info("UIService", "事件监听初始化完成");
  }

  /**
   * 设置事件监听器
   */
  setupEventListeners() {
    Logger.info("UIService", "setupEventListeners", "设置UI事件监听器");

    try {
      // 绑定商城入口点击事件
      document.addEventListener("click", (e) => {
        const shopEntrance = e.target.closest(".shop-entrance");
        if (shopEntrance) {
          Logger.info("UIService", "handleShopEntranceClick", "点击商城入口");
          this.eventBus.emit(SHOP_EVENTS.ENTER);
        }
      });

      // 其他事件监听保持不变
    } catch (error) {
      Logger.error("UIService", "setupEventListeners", "设置UI事件监听器失败:", error);
      throw error;
    }
  }

  updateWebSocketStatus(status) {
    const statusDot = document.querySelector(".status-dot");
    const statusText = document.querySelector(".status-text");
    // 移除所有状态类
    statusDot.classList.remove("connected", "disconnected", "connecting", "error", "reconnecting");
    if (status === "connected") {
      statusDot.classList.add("connected");
      statusText.textContent = "WebSocket连接成功";
    } else if (status === "disconnected") {
      statusDot.classList.add("disconnected");
      statusText.textContent = "WebSocket已断开";
    } else if (status === "error") {
      statusDot.classList.add("error");
      statusText.textContent = "WebSocket连接错误";
    }
  }

  initStatusElements() {
    // 获取状态显示元素
    this.statusDot = document.querySelector(".status-dot");
    this.statusText = document.querySelector(".status-text");
    Logger.debug("UIService", "WebSocket状态显示元素:", this.statusDot, this.statusText);
    if (!this.statusDot || !this.statusText) {
      Logger.warn("UIService", "WebSocket状态显示元素未找到");
    }
  }

  /**
   * 设置DOM观察器
   * @private
   */
  setupDOMObserver() {
    Logger.debug("UIService", "初始化DOM观察器");

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
    const containers = [document.getElementById("taskList"), document.querySelector(".active-tasks-swiper .swiper-wrapper"), document.querySelector(".tasks-list")].filter(Boolean);

    containers.forEach((container) => {
      taskObserver.observe(container, config);
      // 初始化已存在的任务卡片
      Array.from(container.getElementsByClassName("task-card")).forEach((card) => this.initializeTaskCard(card));
    });

    // 存储观察器实例以便后续清理
    this.observers.set("taskObserver", taskObserver);
  }

  /**
   * 初始化任务卡片
   * @private
   * @param {HTMLElement} taskCard - 任务卡片DOM元素
   */
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

  /**
   * 清理所有观察器
   * @public
   */
  destroy() {
    Logger.info("UIService", "开始清理UI服务");

    // 清理所有观察器
    this.observers.forEach((observer) => observer.disconnect());
    this.observers.clear();

    Logger.info("UIService", "UI服务清理完成");
  }

  updateTaskList(tasks) {
    Logger.debug("UIService", "更新任务列表UI");
    // 任务列表更新逻辑
  }

  /**
   * 显示任务详情
   * @param {Object} taskId 任务ID
   */
  async showTaskDetails(taskId) {
    Logger.info("UIService", "显示任务详情:", taskId);

    try {
      const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);
      if (!taskCard) {
        Logger.error("UIService", "未找到任务卡片:", taskId);
        return;
      }

      // 从store中获取完整的任务数据
      const tasks = this.store.state.taskList || [];
      // 获取任务数据
      // 如果任务数据中没有找到，则从taskService中获取
      const task = tasks.find((t) => t.id.toString() === taskId.toString()) || this.taskService.getTaskById(taskId);

      if (!task) {
        Logger.error("UIService", "未找到任务数据:", taskId);
        return;
      }

      layer.open({
        type: 1,
        title: false,
        content: await this.templateService.createTaskDetailTemplate(task),
        area: ["500px", "400px"],
        shadeClose: true,
        success: (layero) => {
          // 确保layero是jQuery对象
          const $layero = $(layero);

          // 绑定接受任务按钮事件
          const acceptBtn = $layero.find(".accept-task");
          if (acceptBtn.length) {
            acceptBtn.on("click", () => {
              this.showConfirmDialog({
                title: "确认接受",
                  content: "确定要接受这个任务吗？",
                  onConfirm: () => {
                    this.eventBus.emit(TASK_EVENTS.ACCEPT, { taskId, playerId: this.playerService.getPlayerId() });
                    layer.closeAll();
                  },
              });
            });
          }

          // 绑定放弃任务按钮事件
          const abandonBtn = $layero.find(".abandon-task");
          if (abandonBtn.length) {
            abandonBtn.on("click", () => {
              this.showConfirmDialog({
                title: "确认放弃",
                content: "确定要放弃这个任务吗？",
                onConfirm: () => {
                  this.eventBus.emit(TASK_EVENTS.ABANDONED, { taskId, playerId: this.playerService.getPlayerId() });
                  layer.closeAll();
                },
              });
            });
          }
        },
      });

      Logger.debug("UIService", "任务详情显示完成");
    } catch (error) {
      Logger.error("UIService", "显示任务详情失败:", error);
      this.showNotification({
        type: "ERROR",
        message: "显示任务详情失败",
      });
    }
  }
  /**
   * 显示当前任务详情
   * @param {Object} taskId 任务ID
   */
  async showCurrentTaskDetails(taskId) {
    Logger.info("UIService", "显示当前任务详情:", taskId);

    try {
      // 从store中获取当前任务数据
      const currentTasks = this.store.state.currentTasks || [];
      Logger.info('UIService',"currentTasks:", currentTasks);
      const task = currentTasks.find(t => t.id.toString() === taskId.toString());

      if (!task) {
        // 如果任务不在当前任务列表中，则从API获取
        const response = await this.api.getCurrentTaskById(taskId);
        if (response.code === 0) {
          const taskDetails = response.data;
          layer.open({
            type: 1,
            title: false,
            content: await this.templateService.createCurrentTaskDetailTemplate(taskDetails),
            area: ["500px", "400px"],
            shadeClose: true,
          });
        } else {
          Logger.error("UIService", "未找到任务数据:", taskId);
        }
      } else {
        // 如果任务在当前任务列表中，直接显示
        layer.open({
          type: 1,
          title: false,
          content: await this.templateService.createCurrentTaskDetailTemplate(task),
          area: ["500px", "400px"],
          shadeClose: true,
        });
      }
    } catch (error) {
      Logger.error("UIService", "显示当前任务详情失败:", error);
    }
  }

  /**
   * 显示通知消息
   * @param {Object} data 通知数据
   */
  showNotification(data) {
    Logger.debug("UIService", "显示通知:", data);

    // 防止重复通知
    const notificationKey = `${data.type}-${data.message}`;
    const now = Date.now();

    if (this._lastNotification && this._lastNotification.key === notificationKey && now - this._lastNotification.time < 1000) {
      // 1秒内的相同通知将被忽略
      Logger.debug("UIService", "忽略重复通知");
      return;
    }

    // 记录本次通知
    this._lastNotification = {
      key: notificationKey,
      time: now,
    };

    try {
      // 使用 layer 显示通知
      const icon = this._getNotificationIcon(data.type);
      layer.msg(data.message, {
        icon: icon,
        time: 2000,
        offset: "15px",
      });
    } catch (error) {
      Logger.error("UIService", "显示通知失败:", error);
      console.error("显示通知失败:", error);
    }
  }

  _getNotificationIcon(type) {
    const iconMap = {
      SUCCESS: 1,
      ERROR: 2,
      WARNING: 0,
      INFO: 6,
    };
    return iconMap[type] || 6;
  }


  /**
   * 显示确认对话框
   * @param {Object} options 对话框配置
   * @param {string} options.title 标题
   * @param {string} options.content 内容
   * @param {Function} options.onConfirm 确认回调
   * @param {Function} options.onCancel 取消回调
   */
  showConfirmDialog(options) {
    layer.confirm(
      options.content,
      {
        title: options.title,
        btn: ["确定", "取消"],
      },
      // 确认回调
      () => {
        if (options.onConfirm) {
          options.onConfirm();
        }
      },
      // 取消回调
      () => {
        if (options.onCancel) {
          options.onCancel();
        }
      }
    );
  }


  /**
   * 显示错误消息
   * @param {string} message 消息内容
   */
  showErrorMessage(message) {
    layui.layer.msg(message, {
      icon: 2,
      time: 2000,
    });
  }

  /**
   * 渲染任务列表
   * @param {Array} tasks 任务列表数据
   */
  renderTaskList(tasks) {
    Logger.info("UIService", "开始渲染任务列表");
    const container = document.querySelector(".task-list-swiper .swiper-wrapper");

    if (!container) {
      Logger.error("UIService", "找不到任务列表容器");
      return;
    }

    try {
      if (!tasks || !tasks.length) {
        container.innerHTML = this.templateService.getEmptyTaskTemplate();
      } else {
        const taskCards = tasks
          .map((task) => {
            try {
              return this.templateService.createTaskCard(task);
            } catch (err) {
              Logger.error("UIService", "渲染单个任务卡片失败:", err);
              return null;
            }
          })
          .filter(Boolean);

        container.innerHTML = taskCards.join("");

        // 初始化或刷新Swiper
        if (this.swiperService) {
          this.swiperService.initTaskListSwiper();
        }
      }
    } catch (error) {
      Logger.error("UIService", "渲染任务列表失败:", error);
      container.innerHTML = `<div class="error-task">加载任务失败: ${error.message}</div>`;
    }
  }

  /**
   * 渲染当前任务列表
   * @param {Array} tasks 当前任务列表数据
   */
  renderCurrentTasks(tasks) {
    Logger.info("UIService", "开始渲染当前任务列表");
    const container = document.querySelector(".active-tasks-swiper .swiper-wrapper");

    if (!container) {
      Logger.error("UIService", "找不到当前任务列表容器");
      return;
    }

    try {
      if (!tasks || !tasks.length) {
        container.innerHTML = this.templateService.getEmptyTaskTemplate();
      } else {
        const taskCards = tasks
          .map((task) => {
            try {
              return this.templateService.createActiveTaskCard(task);
            } catch (err) {
              Logger.error("UIService", "渲染单个当前任务卡片失败:", err);
              return null;
            }
          })
          .filter(Boolean);

        container.innerHTML = taskCards
          .map(
            (card) => `
                    <div class="swiper-slide">
                        <div class="task-panel">
                            ${card}
                        </div>
                    </div>
                `
          )
          .join("");
      }
    } catch (error) {
      Logger.error("UIService", "渲染当前任务列表失败:", error);
      container.innerHTML = `<div class="error-task">加载当前任务失败: ${error.message}</div>`;
    }
  }

  /**
   * 更新任务状态的UI显示
   * @param {Object} data 任务状态数据
   */
  updateTaskStatus(data) {
    Logger.info("UIService", "更新任务状态UI:", data);
    try {
      // 同时更新任务列表和当前任务列表
      this.renderTaskList(this.store.state.taskList);
      this.renderCurrentTasks(this.store.state.currentTasks);
      return;
      // 获取任务容器
      const container = document.querySelector(".active-tasks-swiper .swiper-wrapper");
      if (!container) {
        Logger.error("UIService", "找不到任务容器");
        return;
      }

      // 查找对应的任务卡片
      const taskCard = container.querySelector(`[data-task-id="${data.id}"]`);
      if (!taskCard) {
        Logger.warn("UIService", `未找到任务卡片: ${data.id}`);
        return;
      }

      // 根据任务状态更新UI
      switch (data.status) {
        case "COMPLETE":
        case "ABANDONED":
          Logger.debug("UIService", `移除已完成/放弃的任务卡片: ${data.id}`);
          const slideElement = taskCard.closest(".swiper-slide");
          if (slideElement) {
            // 添加淡出动画
            slideElement.style.transition = "opacity 0.5s";
            slideElement.style.opacity = "0";
            // 等待动画完成后移除
            setTimeout(() => {
              slideElement.remove();
              // 检查是否需要显示空任务提示
              if (!container.children.length) {
                container.innerHTML = this.templateService.getEmptyTaskTemplate();
              }
            }, 500);
          }
          break;

        case "CHECKING":
          Logger.debug("UIService", `更新任务状态为审核中: ${data.id}`);
          taskCard.classList.add("checking");
          const statusElement = taskCard.querySelector(".task-status");
          if (statusElement) {
            statusElement.textContent = "审核中";
            statusElement.classList.add("checking");
          }
          break;

        case "REJECTED":
          Logger.debug("UIService", `更新任务状态为已驳回: ${data.id}`);
          taskCard.classList.add("rejected");
          const rejectStatusElement = taskCard.querySelector(".task-status");
          if (rejectStatusElement) {
            rejectStatusElement.textContent = "已驳回";
            rejectStatusElement.classList.add("rejected");
          }
          break;

        default:
          Logger.debug("UIService", `更新任务状态: ${data.status}`);
          // 更新任务卡片内容
          const newCard = this.templateService.createActiveTaskCard(data);
          if (newCard) {
            taskCard.innerHTML = newCard.innerHTML;
          }
      }

      Logger.info("UIService", "任务状态UI更新完成");
    } catch (error) {
      Logger.error("UIService", "更新任务状态UI失败:", error);
      this.showNotification({
        type: "ERROR",
        message: "更新任务状态显示失败",
      });
    }
  }

  /**
   * 更新任务进度条
   * @param {string} taskId 任务ID
   * @param {number} progress 进度值(0-100)
   */
  updateTaskProgress(taskId, progress) {
    Logger.debug("UIService", `更新任务进度: ${taskId}, ${progress}%`);

    try {
      const progressBar = document.querySelector(`[data-task-id="${taskId}"] .progress-bar`);
      if (progressBar) {
        progressBar.style.width = `${progress}%`;
        progressBar.setAttribute("aria-valuenow", progress);

        // 更新进度文本
        const progressText = progressBar.querySelector(".progress-text");
        if (progressText) {
          progressText.textContent = `${progress}%`;
        }
      }
    } catch (error) {
      Logger.error("UIService", "更新任务进度失败:", error);
    }
  }

  /**
   * 更新任务剩余时间
   * @param {string} taskId 任务ID
   * @param {number} endTime 结束时间戳
   */
  updateTaskTime(taskId, endTime) {
    Logger.debug("UIService", `更新任务时间: ${taskId}`);

    try {
      const timeElement = document.querySelector(`[data-task-id="${taskId}"] .task-time`);
      if (!timeElement) return;

      const now = Math.floor(Date.now() / 1000);
      const timeLeft = endTime - now;

      if (timeLeft <= 0) {
        timeElement.textContent = "已过期";
        timeElement.classList.add("expired");
        return false;
      }

      const hours = Math.floor(timeLeft / 3600);
      const minutes = Math.floor((timeLeft % 3600) / 60);
      const seconds = timeLeft % 60;

      const timeString = `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
      timeElement.textContent = `剩余时间：${timeString}`;
      return true;
    } catch (error) {
      Logger.error("UIService", "更新任务时间失败:", error);
      return false;
    }
  }

  /**
   * 初始化任务相关事件监听
   */
  initTaskEvents() {
    Logger.info("UIService", "initTaskEvents", "初始化任务事件");
    try {
      // 绑定任务相关事件
      document.querySelectorAll(".task-card").forEach((taskCard) => {
        this.initializeTaskCard(taskCard);
      });
      // 绑定全局任务事件
      document.addEventListener("click", (e) => this.handleDocumentClick(e));

      Logger.info("UIService", "initTaskEvents", "任务事件初始化完成");
    } catch (error) {
      Logger.error("UIService", "initTaskEvents", "任务事件初始化失败:", error);
      throw error;
    }
  }

  /**
   * 移除任务事件
   */
  removeTaskEvents() {
    Logger.info("UIService", "removeTaskEvents", "移除任务事件");
    try {
      // 移除所有任务卡片的事件监听
      document.querySelectorAll(".task-card").forEach((taskCard) => {
        const acceptBtn = taskCard.querySelector(".accept-task-btn");
        const abandonBtn = taskCard.querySelector(".abandon-task");

        if (acceptBtn) {
          acceptBtn.removeEventListener("click", this.handleTaskAccept);
        }
        if (abandonBtn) {
          abandonBtn.removeEventListener("click", this.handleTaskAbandon);
        }
        taskCard.removeEventListener("click", this.handleTaskClick);
      });

      // 移除全局任务事件
      document.removeEventListener("click", this.handleDocumentClick);

      Logger.info("UIService", "removeTaskEvents", "任务事件移除完成");
    } catch (error) {
      Logger.error("UIService", "removeTaskEvents", "任务事件移除失败:", error);
      throw error;
    }
  }

  /**
   * 处理任务接受事件
   * @param {string} taskId 任务ID
   */
  async handleTaskAccept(taskId) {
    Logger.info("UIService", `处理接受任务: ${taskId}`);

    try {
      // 使用 Promise 包装 layer.confirm
      await new Promise((resolve, reject) => {
        layer.confirm(
          "确定要接受这个任务吗？",
          {
            title: "接受任务",
            btn: ["确定", "取消"],
            icon: 3,
          },
          async (index) => {
            try {
              // 关闭确认对话框
              layer.close(index);

              // 调用任务服务接受任务
              const result = await this.taskService.handleTaskAccept(taskId);
              Logger.info("UIService", "接受任务结果:", result);
              // 根据返回结果显示不同的提示
              if (result.code === 1) {
                // 已接受的情况
                this.showNotification({
                  type: "INFO",
                  message: result.msg || "已接受该任务",
                });
              } else if (result.code === 0) {
                // 成功接受的情况
                this.showNotification({
                  type: "SUCCESS",
                  message: "任务接受成功",
                });
                // 任务接受完成，更新任务状态
                this.eventBus.emit(TASK_EVENTS.ACCEPTED, {
                  taskId: taskId,
                  playerId: this.playerService.getPlayerId(),
                });
                // 发送音频播放事件
                this.eventBus.emit(AUDIO_EVENTS.PLAY, "ACCEPT");
              }

              resolve();
            } catch (error) {
              Logger.error("UIService", "接受任务失败:", error);
              this.showNotification({
                type: "ERROR",
                message: error.message || "接受任务失败",
              });

              // 发送错误音频事件
              this.eventBus.emit(AUDIO_EVENTS.PLAY, "ERROR");
              reject(error);
            }
          },
          () => {
            // 取消按钮回调
            resolve();
          }
        );
      });
    } catch (error) {
      Logger.error("UIService", "处理任务接受失败:", error);
      this.showNotification({
        type: "ERROR",
        message: "处理任务接受失败",
      });
    }
  }

  /**
   * 处理任务放弃事件
   * @param {Object} data 任务数据
   */
  async handleTaskAbandon(taskId) {
    Logger.info("UIService", "处理放弃任务:", taskId);
    try {
      // 显示确认对话框
      layer.confirm(
        "确定要放弃这个任务吗？放弃后将无法恢复。",
        {
          title: "放弃任务",
          btn: ["确定", "取消"],
          icon: 3,
        },
        () => {
          try {
            // 用户点击确定后触发任务放弃事件
            this.eventBus.emit(TASK_EVENTS.ABANDONED, {
              taskId: taskId,
              playerId: this.playerService.getPlayerId(),
            });
            layer.closeAll();
          } catch (error) {
            Logger.error("UIService", "放弃任务失败:", error);
            this.showErrorMessage("放弃任务失败: " + error.message);
          }
        }
      );
    } catch (error) {
      Logger.error("UIService", "放弃任务失败:", error);
      this.showNotification({
        type: "ERROR",
        message: "放弃任务失败",
      });
      this.eventBus.emit(AUDIO_EVENTS.PLAY, "ERROR");
    }
  }

  // ... 其他UI相关方法
  // 优化地图渲染器变更处理方法
  updatePlayerInfo(playerData) {
    Logger.debug("UIService", "更新玩家UI:", playerData);

    try {
      if (!playerData) {
        Logger.warn("UIService", "无效的玩家数据");
        return;
      }

      // 更新基本信息
      const nameElement = document.getElementById("playerName");
      const pointsElement = document.getElementById("playerPoints");

      if (nameElement) nameElement.textContent = playerData.player_name || "未知玩家";
      if (pointsElement) pointsElement.textContent = playerData.points || "0";

      // 更新等级和经验值
      this.updateLevelAndExp(playerData);

      // 更新状态
      this.updateState({
        uiComponents: {
          ...this.state.uiComponents,
          playerInfo: {
            ...this.state.uiComponents.playerInfo,
            visible: true,
            error: null,
          },
        },
      });

      Logger.debug("UIService", "玩家UI更新完成");
    } catch (error) {
      Logger.error("UIService", "更新玩家UI失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "更新玩家界面失败",
      });
    }
  }

  updateLevelAndExp(playerData) {
    try {
      if (!playerData) return;

      const levelElement = document.querySelector(".level");
      const expElement = document.querySelector(".exp");
      const expBarInner = document.querySelector(".exp-bar-inner");

      if (levelElement) {
        levelElement.textContent = `${playerData.level || 0}/100`;
      }
      if (expElement) {
        expElement.textContent = `${playerData.experience || 0}/99999`;
      }
      if (expBarInner) {
        const expPercentage = ((playerData.experience || 0) / 99999) * 100;
        expBarInner.style.width = `${Math.min(100, expPercentage)}%`;
      }

      Logger.debug("UIService", "等级和经验值更新完成");
    } catch (error) {
      Logger.error("UIService", "更新等级和经验值失败:", error);
      throw error;
    }
  }

  /**
   * 处理任务完成事件
   * @param {Object} taskData 任务数据
   */
  handleTaskComplete(taskData) {
    Logger.info("UIService", "处理任务完成事件:", taskData);
    try {
      // 更新UI显示
      this.showNotification({
        type: "SUCCESS",
        message: `任务完成！获得 ${taskData.rewards?.points || 0} 点经验`,
      });

      // 播放完成音效
      this.eventBus.emit(AUDIO_EVENTS.PLAY, "COMPLETE");

      // 刷新任务列表
      this.taskService.refreshTasks().then(() => {
        Logger.debug("UIService", "任务列表已刷新");
      });
    } catch (error) {
      Logger.error("UIService", "处理任务完成事件失败:", error);
      this.showNotification({
        type: "ERROR",
        message: "处理任务完成失败",
      });
    }
  }

  // 处理任务错误
  handleTaskError(error) {
    Logger.error("UIService", "任务错误:", error);
    this.showNotification({
      type: "ERROR",
      message: error.message || "任务操作失败",
    });
    this.eventBus.emit(AUDIO_EVENTS.PLAY, "ERROR");
  }

  // 处理任务点击
  handleTaskClick(taskData) {
    Logger.debug("UIService", "处理任务点击:", taskData);
    this.showTaskDetails(taskData);
  }

  // 处理当前任务更新
  handleCurrentTasksUpdated(tasks) {
    Logger.info("UIService", "当前任务更新:", tasks);
    this.renderCurrentTasks(tasks);
  }

  // 处理文档点击事件的函数
  handleDocumentClick(e) {
    const target = e.target;

    // 处理任务卡片点击 需要判断是进行中的任务还是可用任务    
    const taskCard = target.closest(".task-card");
    if (taskCard && !target.closest("button")) {
        const taskId = taskCard.dataset.taskId;
        if (taskId) {
            // 判断任务类型
            const isActiveTask = taskCard.closest(".active-tasks-container") !== null;
            const isAvailableTask = taskCard.closest(".task-list-swiper") !== null;
            
            Logger.debug("UIService", `处理任务卡片点击 - ${isActiveTask ? '进行中任务' : isAvailableTask ? '可用任务' : '未知类型任务'} ID: ${taskId}`);
            if(isActiveTask){
              this.showCurrentTaskDetails(taskId);
            }else{
              this.showTaskDetails(taskId);
            }
        }
    }

    // 处理接受任务按钮点击
    if (target.classList.contains(".accept-task")) {
      const taskId =target.dataset.taskId;
      Logger.debug("UIService", "处理接受任务按钮点击::, taskId ", taskId);
      if (taskId) {
        this.handleTaskAccept(taskId);
      }
    }

    // 处理放弃任务按钮点击
    if (target.classList.contains('abandon-task')) {
      const taskId = target.dataset.taskId;
      Logger.debug("UIService", "处理放弃任务按钮点击::, taskId ", taskId);
      if (taskId) {
        this.handleTaskAbandon(taskId);
      }
    }
  }

  /**
   * 初始化地图UI组件
   */
  async initializeMapUI() {
    Logger.info("UIService", "初始化地图UI组件");
    try {
      Logger.debug("UIService", "开始初始化各个UI组件");
      this.initMapSwitchButton();
      this.initTimeRangeSelector();
      this.initCustomTimeRange();
      this.initDisplayModeButton();
      Logger.info("UIService", "地图UI组件初始化完成");
    } catch (error) {
      Logger.error("UIService", "初始化地图UI组件失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: "ERROR",
        message: "初始化地图控件失败",
      });
      throw error; // 抛出错误以便上层处理
    }
  }

  /**
   * 初始化地图切换按钮
   */
  initMapSwitchButton() {
    Logger.debug("UIService", "初始化地图切换按钮");
    const mapSwitchBtn = document.getElementById("switchMapType");
    if (!mapSwitchBtn) {
      Logger.error("UIService", "找不到地图切换按钮");
      return;
    }

    // 移除可能存在的旧事件监听器
    mapSwitchBtn.removeEventListener("click", this.handleMapSwitchClick);

    // 使用箭头函数保持this上下文
    this.handleMapSwitchClick = () => {
      const currentType = localStorage.getItem("mapType") || "ECHARTS";
      const newType = currentType === "AMAP" ? "ECHARTS" : "AMAP";
      Logger.debug("UIService", "触发地图切换事件:", newType);
      this.eventBus.emit(MAP_EVENTS.RENDERER_CHANGED, newType);
    };

    mapSwitchBtn.addEventListener("click", this.handleMapSwitchClick);
  }

  /**
   * 初始化时间范围选择器
   */
  initTimeRangeSelector() {
    Logger.debug("UIService", "初始化时间范围选择器");
    const timeRangeSelect = document.getElementById("timeRangeSelect");

    if (!timeRangeSelect) {
      Logger.warn("UIService", "找不到时间范围选择器");
      return;
    }

    try {
      // 设置选择器的值
      timeRangeSelect.value = this.mapTimeRange;

      // 添加change事件监听
      timeRangeSelect.addEventListener("change", (e) => {
        const newValue = e.target.value;
        Logger.debug("UIService", `时间范围变更为: ${newValue}`);
        this.mapTimeRange = newValue;
        this.store.setComponentState(this.componentId, { mapTimeRange: newValue }); // 更新到store
        // mapTimeRange是否需要同步更新到localstorage

        this.eventBus.emit(MAP_EVENTS.TIME_RANGE_CHANGED, newValue);
      });

      this.updateCustomTimeRangeVisibility();
    } catch (error) {
      Logger.error("UIService", "初始化时间范围选择器失败:", error);
    }
  }

  /**
   * 初始化自定义时间范围
   */
  initCustomTimeRange() {
    const startInput = document.getElementById("startTime");
    const endInput = document.getElementById("endTime");
    const applyButton = document.getElementById("applyCustomRange");

    if (startInput && endInput) {
      if (this.mapTimeRange === "custom" && this.customStartTime && this.customEndTime) {
        startInput.value = this.customStartTime;
        endInput.value = this.customEndTime;
      }

      startInput.addEventListener("change", () => {
        this.customStartTime = startInput.value;
      });

      endInput.addEventListener("change", () => {
        this.customEndTime = endInput.value;
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

          this.customStartTime = startInput.value;
          this.customEndTime = endInput.value;
          this.eventBus.emit(MAP_EVENTS.TIME_RANGE_CHANGED, "custom");
        });
      }
    }

    this.updateCustomTimeRangeVisibility();
  }

  /**
   * 初始化显示模式按钮
   */
  initDisplayModeButton() {
    Logger.debug("UIService", "初始化显示模式切换按钮");
    const displayModeSwitchBtn = document.getElementById("switchDisplayMode");
    if (!displayModeSwitchBtn) {
      Logger.warn("UIService", "找不到显示模式切换按钮");
      return;
    }

    displayModeSwitchBtn.addEventListener("click", () => {
      this.eventBus.emit(MAP_EVENTS.DISPLAY_MODE_CHANGED);
    });
  }

  /**
   * 更新自定义时间范围的显示状态
   */
  updateCustomTimeRangeVisibility() {
    const customDateRange = document.getElementById("customDateRange");
    if (customDateRange) {
      customDateRange.style.display = this.mapTimeRange === "custom" ? "block" : "none";
    }
  }

  /**
   * 验证时间范围
   */
  validateTimeRange(start, end) {
    if (!start || !end) return false;

    const startTime = new Date(start);
    const endTime = new Date(end);

    if (isNaN(startTime.getTime()) || isNaN(endTime.getTime())) return false;
    if (startTime >= endTime) return false;

    return true;
  }

  /**
   * 初始化商城相关事件
   */
  initShopEvents() {
    Logger.info("UIService", "initShopEvents", "初始化商城事件");
    // 绑定商城入口点击事件
    const shopEntrance = document.querySelector(".shop-entrance");
    if (shopEntrance) {
      shopEntrance.addEventListener("click", this.handleShopEntranceClick);
    }
  }

  // 移除商城事件监听器
  removeShopEvents() {
    Logger.info("UIService", "removeShopEvents", "移除商城事件");
    const shopEntrance = document.querySelector(".shop-entrance");
    if (shopEntrance) {
      shopEntrance.removeEventListener("click", this.handleShopEntranceClick);
    }
  }

  // 处理商城入口点击
  handleShopEntranceClick = () => {
    Logger.info("UIService", "handleShopEntranceClick", "点击商城入口");
    this.eventBus.emit(SHOP_EVENTS.ENTER);
  };

  /**
   * 处理商城相关UI更新
   */
  handleShopUIUpdate(data) {
    Logger.info("UIService", "handleShopUIUpdate", "更新商城UI");

    if (data.points !== undefined) {
      // 更新积分显示
      const pointsElement = document.getElementById("userPoints");
      if (pointsElement) {
        pointsElement.textContent = data.points;
      }
    }

    if (data.items !== undefined) {
      // 更新商品列表
      const container = document.getElementById("shopItems");
      if (!container) {
        Logger.error("UIService", "handleShopUIUpdate", "找不到商品容器元素");
        return;
      }

      // 清空现有内容
      container.innerHTML = "";

      // 创建商品卡片
      data.items.forEach((item) => {
        const card = this.createShopItemCard(item);
        container.appendChild(card);
      });

      Logger.info("UIService", "handleShopUIUpdate", `渲染了 ${data.items.length} 个商品`);
    }
  }

  /**
   * 创建商品卡片DOM元素
   */
  createShopItemCard(item) {
    Logger.debug("UIService", "createShopItemCard", "创建商品卡片:", item);

    const itemElement = document.createElement("div");
    itemElement.className = "shop-item";
    itemElement.setAttribute("data-item-id", item.id);

    // 使用base64默认图片
    const DEFAULT_ITEM_IMAGE ='/static/img/shop/default_item.svg';

    itemElement.innerHTML = `
        <div class="item-image">
            <img src="${item.image_url || DEFAULT_ITEM_IMAGE}" alt="${item.name}" 
                 onerror="this.src='${DEFAULT_ITEM_IMAGE}'">
        </div>
        <div class="item-info">
            <div class="item-name">${item.name}</div>
            <div class="item-description">${item.description}</div>
            <div class="item-price">
                <img src="/static/img/points.png" alt="积分">
                <span>${item.price}</span>
            </div>
            <div class="item-stock">库存: ${item.stock}</div>
        </div>
    `;

    // 点击商品卡片显示详情
    itemElement.addEventListener("click", () => {
      this.showItemDetail(item);
    });

    return itemElement;
  }

  /**
   * 显示商品购买确认对话框
   * @param {Object} options 对话框配置
   * @param {Object} options.item 商品数据
   * @param {number} options.quantity 购买数量
   * @param {Function} options.onConfirm 确认回调
   * @param {Function} options.onCancel 取消回调
   */
  showPurchaseConfirmDialog(options) {
    const { item, quantity = 1 } = options;
    const totalPrice = quantity * item.price;

    // 构建确认框内容
    const content = `
      <div class="purchase-confirm-content">
        <div class="item-info">
          <img src="${item.image_url}" alt="${item.name}" class="item-image">
          <div class="item-details">
            <h3>${item.name}</h3>
            <p class="item-description">${item.description}</p>
          </div>
        </div>
        <div class="purchase-details">
          <div class="detail-row">
            <span>购买数量：</span>
            <span class="value">${quantity}</span>
          </div>
          <div class="detail-row">
            <span>单价：</span>
            <span class="value">${item.price} 积分</span>
          </div>
          <div class="detail-row total">
            <span>总价：</span>
            <span class="value">${totalPrice} 积分</span>
          </div>
        </div>
      </div>
    `;

    layer.confirm(
      content,
      {
        title: "购买确认",
        btn: ["确认购买", "取消"],
        area: ["400px", "500px"],
        skin: "purchase-confirm-dialog",
        success: (layero) => {
          // 添加自定义样式
          const style = document.createElement("style");
          style.textContent = `
          .purchase-confirm-dialog .layui-layer-content {
            padding: 20px;
          }
          .purchase-confirm-content {
            color: #b0b6c2;
          }
          .purchase-confirm-content .item-info {
            display: flex;
            gap: 15px;
            margin-bottom: 20px;
          }
          .purchase-confirm-content .item-image {
            width: 80px;
            height: 80px;
            object-fit: cover;
            border-radius: 8px;
          }
          .purchase-confirm-content .item-details h3 {
            margin: 0 0 10px;
            color: #57CAFF;
            font-size: 16px;
          }
          .purchase-confirm-content .item-description {
            font-size: 14px;
            margin: 0;
            color: rgba(176, 182, 194, 0.8);
          }
          .purchase-confirm-content .purchase-details {
            background: rgba(27, 39, 53, 0.5);
            border-radius: 8px;
            padding: 15px;
          }
          .purchase-confirm-content .detail-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
          }
          .purchase-confirm-content .detail-row:last-child {
            margin-bottom: 0;
          }
          .purchase-confirm-content .detail-row.total {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(87, 202, 255, 0.2);
          }
          .purchase-confirm-content .detail-row .value {
            color: #57CAFF;
            font-weight: bold;
          }
        `;
          document.head.appendChild(style);
        },
      },
      (index) => {
        // 确认回调
        if (options.onConfirm) {
          options.onConfirm(index);
        }
      },
      (index) => {
        // 取消回调
        if (options.onCancel) {
          options.onCancel(index);
        }
        layer.close(index);
      }
    );
  }

  /**
   * 显示商品详情
   * @param {Object} item - 商品信息
   */
  showItemDetail(item) {
    Logger.debug("UIService", "showItemDetail", "显示商品详情:", item);

    try {
      // 更新模态框内容
      const modalImage = document.getElementById("modalItemImage");
      const modalName = document.getElementById("modalItemName");
      const modalDescription = document.getElementById("modalItemDescription");
      const modalPrice = document.getElementById("modalItemPrice");
      const modalStock = document.getElementById("modalItemStock");
      const modalDate = document.getElementById("modalItemDate");
      const quantityInput = document.getElementById("itemQuantity");
      const purchaseBtn = document.getElementById("purchaseBtn");

      if (modalImage) modalImage.src = item.image_url || DEFAULT_ITEM_IMAGE;
      if (modalName) modalName.textContent = item.name;
      if (modalDescription) modalDescription.textContent = item.description;
      if (modalPrice) modalPrice.textContent = item.price;
      if (modalStock) modalStock.textContent = item.stock;
      if (modalDate) {
        const onlineTime = new Date(item.online_time).toLocaleString();
        const offlineTime = new Date(item.offline_time).toLocaleString();
        modalDate.textContent = `上架时间: ${onlineTime}\n下架时间: ${offlineTime}`;
      }
      if (quantityInput) quantityInput.value = "1";

      // 绑定数量控制按钮事件
      const decreaseBtn = document.getElementById("decreaseQty");
      const increaseBtn = document.getElementById("increaseQty");

      if (decreaseBtn) {
        decreaseBtn.onclick = () => {
          const currentValue = parseInt(quantityInput.value);
          if (currentValue > 1) {
            quantityInput.value = currentValue - 1;
          }
        };
      }

      if (increaseBtn) {
        increaseBtn.onclick = () => {
          const currentValue = parseInt(quantityInput.value);
          if (currentValue < item.stock) {
            quantityInput.value = currentValue + 1;
          }
        };
      }

      // 绑定购买按钮事件
      if (purchaseBtn) {
        purchaseBtn.onclick = () => {
          const quantity = parseInt(quantityInput.value);
          this.showPurchaseConfirmDialog({
            item: item,
            quantity: quantity,
            onConfirm: (index) => {
              this.eventBus.emit(SHOP_EVENTS.PURCHASE_REQUESTED, {
                item: item,
                quantity: quantity,
              });
              layer.close(index);
            },
            onCancel: (index) => {
              layer.close(index);
            },
          });
        };
      }

      // 显示模态框
      layer.open({
        type: 1,
        title: false,
        content: $("#itemDetailModal"),
        area: ["800px", "500px"],
        shadeClose: true,
        success: () => {
          Logger.debug("UIService", "showItemDetail", "商品详情模态框打开成功");
        },
      });
    } catch (error) {
      Logger.error("UIService", "showItemDetail", "显示商品详情失败:", error);
      this.showNotification({
        type: "ERROR",
        message: "显示商品详情失败",
      });
    }
  }

  /**
   * 初始化玩家信息UI
   */
  async initPlayerInfoUI() {
    Logger.info("UIService", "初始化玩家信息UI");
    try {
      // 更新状态
      this.updateState({
        uiComponents: {
          ...this.state.uiComponents,
          playerInfo: {
            ...this.state.uiComponents.playerInfo,
            loading: true,
          },
        },
      });

      // 加载玩家信息
      await this.playerService.loadPlayerInfo();
      const playerData = this.playerService.getPlayerData();

      if (playerData) {
        this.updatePlayerInfo(playerData);
      } else {
        throw new Error("无法获取玩家信息");
      }

      // 更新状态
      this.updateState({
        uiComponents: {
          ...this.state.uiComponents,
          playerInfo: {
            ...this.state.uiComponents.playerInfo,
            loading: false,
            error: null,
          },
        },
      });

      Logger.info("UIService", "玩家信息UI初始化完成");
    } catch (error) {
      Logger.error("UIService", "初始化玩家信息UI失败:", error);
      this.updateState({
        uiComponents: {
          ...this.state.uiComponents,
          playerInfo: {
            ...this.state.uiComponents.playerInfo,
            loading: false,
            error: error.message,
          },
        },
      });
      this.showPlayerError("加载失败");
    }
  }

  /**
   * 显示玩家错误消息
   */
  showPlayerError(message) {
    this.showErrorMessage(message);
  }

  /**
   * 初始化玩家相关事件
   */
  initPlayerEvents() {
    Logger.info("UIService", "初始化玩家事件监听");

    // 监听玩家信息更新事件
    this.eventBus.on(PLAYER_EVENTS.INFO_UPDATED, (playerData) => {
      this.updatePlayerInfo(playerData);
    });

    // 监听经验值更新事件
    this.eventBus.on(PLAYER_EVENTS.EXP_UPDATED, (data) => {
      const playerData = this.playerService.getPlayerData();
      if (playerData) {
        this.updateLevelAndExp(playerData);
      }
    });
  }

  cleanup() {
    Logger.info("UIService", "清理UI服务");
    try {
      // 保存当前状态
      this.saveState();

      // 取消状态订阅
      this.store.unsubscribe("component", this.componentId);

      // 清理DOM事件监听器
      this.removeTaskEvents();
      this.removeShopEvents();

      // 清理所有模态框
      this.state.modals.forEach((modal, id) => {
        this.hideModal(id);
      });

      // 重置玩家信息UI状态
      this.updateState({
        uiComponents: {
          ...this.state.uiComponents,
          playerInfo: {
            ...this.state.uiComponents.playerInfo,
            visible: true,
            loading: false,
            error: null,
          },
        },
      });

      Logger.info("UIService", "UI服务清理完成");
    } catch (error) {
      Logger.error("UIService", "UI服务清理失败:", error);
    }
  }
  // 这个函数是store用来渲染通知列表的
  renderNotifications(notifications) {
    Logger.info("UIService", "开始渲染通知列表");
    const container = document.querySelector(".notification-list");

    if (!container) {
      Logger.error("UIService", "找不到通知列表容器");
      return;
    }

    try {
      if (!notifications || !notifications.length) {
        container.innerHTML = '<div class="no-notifications">无通知</div>';
      } else {
        const notificationItems = notifications
          .map((notification) => {
            return `<div class="notification-item">${notification.message}</div>`;
          })
          .join("");
        container.innerHTML = notificationItems;
      }
    } catch (error) {
      Logger.error("UIService", "渲染通知列表失败:", error);
      container.innerHTML = '<div class="error-notification">加载通知失败</div>';
    }
  }


}

export default UIService;
