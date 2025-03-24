/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:39
 * @LastEditTime: 2025-03-24 20:13:39
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */
import Logger from "../../utils/logger.js";
import { TASK_EVENTS, UI_EVENTS, AUDIO_EVENTS, MAP_EVENTS, WS_EVENTS, PLAYER_EVENTS, SHOP_EVENTS, ROUTE_EVENTS } from "../config/events.js";
import { WS_STATE, WS_CONFIG } from "../config/wsConfig.js";
import { gameUtils } from "../../utils/utils.js";
import NotificationService from "./notificationService.js";
class UIService {
  constructor(eventBus, store, templateService, taskService, playerService, swiperService, notificationService) {
    this.eventBus = eventBus;
    this.store = store;
    this.templateService = templateService;
    this.taskService = taskService;
    this.playerService = playerService;
    this.swiperService = swiperService;
    // this.notificationService = new NotificationService();
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
        },
        playerInfo: {
          visible: true,
          loading: false,
          error: null,
        },
      },
      mapRenderType: "ECHARTS", // 默认为Echarts渲染器
      mapTimeRange: "today", // 默认为今天
      mapViewMode: "points", // 默认为点状态
      customStartTime: null, // 自定义开始时间
      customEndTime: null, // 自定义结束时间
    };

    // 初始化状态
    this.state = { ...this.defaultState };

    // 记录事件监听器，用于后续清理
    this._eventListeners = new Map();

    // 定义点击处理器映射
    this._clickHandlers = {
      // 登录入口点击处理（处理带有login-entrance类的元素）
      "login-entrance": (e, element) => {
        this._handleLoginButtonClick(e);
      },
      // 任务卡片点击处理（仅当没有点击卡片内的按钮时）
      "task-card": (e, element) => {
        // 如果点击的是按钮，则不处理
        if (!e.target.closest("button")) {
          // 如果当前元素同时拥有task-card和active-task类，应该由active-task处理器处理
          if (element.classList.contains("active-task")) {
            Logger.debug("UIService", "由active-task处理器处理");
            return;
          }

          // 只处理普通任务卡片
          const taskId = element.dataset.taskId;
          Logger.debug("UIService", `处理普通任务卡片点击 - ID: ${taskId}`);
          this.showTaskDetails(taskId);
        }
      },
      // 活动任务卡片处理（处理带有active-task类的元素）
      "active-task": (e, element) => {
        // 如果点击的是按钮，则不处理
        if (!e.target.closest("button")) {
          const taskId = element.dataset.taskId;
          Logger.debug("UIService", `处理活动任务卡片点击 - ID: ${taskId}`);
          this.showCurrentTaskDetails(taskId);
        }
      },
      // 接受任务按钮点击处理
      "accept-task": (e, element) => {
        const taskId = element.dataset.taskId || element.closest(".task-card")?.dataset.taskId;
        Logger.debug("UIService", "处理接受任务按钮点击, taskId:", taskId);
        if (taskId) {
          this.handleTaskOperation(taskId, "accept");
        }
      },
      // 放弃任务按钮点击处理
      "abandon-task": (e, element) => {
        const taskId = element.dataset.taskId || element.closest(".task-card")?.dataset.taskId;
        Logger.debug("UIService", "处理放弃任务按钮点击, taskId:", taskId);
        if (taskId) {
          this.handleTaskOperation(taskId, "abandon");
        }
      },
      // 提交任务按钮点击处理
      "submit-task": (e, element) => {
        const taskId = element.dataset.taskId || element.closest(".task-card")?.dataset.taskId;
        Logger.debug("UIService", "处理提交任务按钮点击, taskId:", taskId);
        if (taskId) {
          this.handleTaskOperation(taskId, "submit");
        }
      },
      // 商城入口点击处理
      "shop-entrance": (e, element) => {
        Logger.debug("UIService", "处理商城入口点击");
        this.eventBus.emit(SHOP_EVENTS.ENTER);
      },
      // 带有clickable类的商城入口
      clickable: (e, element) => {
        // 只处理商城入口
        if (element.classList.contains("shop-entrance")) {
          Logger.debug("UIService", "处理商城入口点击(clickable)");
          this.eventBus.emit(SHOP_EVENTS.ENTER);
        }
        // 处理可能的其他clickable元素...
      },
    };

    // 设置状态监听
    this.setupStateListeners();
    // 地图相关状态
    this.mapRenderType = localStorage.getItem("mapType") || "ECHARTS";
    this.mapTimeRange = localStorage.getItem("mapTimeRange") || "today";
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
      mapRenderType: savedState.mapRenderType || "ECHARTS",
      mapTimeRange: savedState.mapTimeRange || "today",
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

  /**
   * 初始化UI服务
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

      // 初始化任务事件（只处理时间更新）
      this.initTaskEvents();

      // 初始化玩家信息UI
      await this.initPlayerInfoUI();

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
    Logger.info("UIService", "初始化事件监听");
    try {
      // 定义需要绑定点击事件的选择器列表
      const clickSelectors = [
        "#loginBtn", // 登录按钮
        ".task-card", // 任务卡片
        ".active-task", // 活动任务卡片
        ".accept-task", // 接受任务按钮
        ".abandon-task", // 放弃任务按钮
        ".submit-task", // 提交任务按钮
        ".shop-entrance", // 商城入口
      ];

      // 为每个选择器绑定点击事件
      clickSelectors.forEach((selector) => {
        this._bindClickEvent(selector);
      });

      Logger.info("UIService", "事件监听初始化完成");
    } catch (error) {
      Logger.error("UIService", "事件监听初始化失败:", error);
      throw error;
    }
  }

  /**
   * 初始化任务相关事件监听
   * 注意：此方法不再绑定点击事件，只处理任务卡片的定时器更新
   */
  initTaskEvents() {
    Logger.info("UIService", "初始化任务卡片时间更新");
    try {
      // 为所有已存在的任务卡片初始化时间更新
      document.querySelectorAll(".task-card").forEach((taskCard) => {
        this.initializeTaskCard(taskCard);
      });

      Logger.info("UIService", "任务卡片时间更新初始化完成");
    } catch (error) {
      Logger.error("UIService", "任务卡片时间更新初始化失败:", error);
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
          // 用于跟踪已绑定事件的元素，避免重复绑定
          const boundElements = new Set();

          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1) {
              // 元素节点
              // 处理任务卡片，优先处理active-task
              if (node.classList) {
                // 先检查active-task类
                if (node.classList.contains("active-task")) {
                  // 初始化任务卡片时间更新
                  this.initializeTaskCard(node);

                  // 为新添加的任务卡片绑定点击事件
                  const boundHandler = this.handleDocumentClick.bind(this);
                  node.addEventListener("click", boundHandler);

                  // 记录事件监听器
                  if (!this._eventListeners.has(".active-task")) {
                    this._eventListeners.set(".active-task", []);
                  }
                  this._eventListeners.get(".active-task").push({
                    element: node,
                    handler: boundHandler,
                  });

                  // 记录已绑定的元素
                  boundElements.add(node);

                  Logger.debug("UIService", `为新添加的 active-task 绑定点击事件`);
                }
                // 然后检查task-card类，但跳过已绑定过的元素
                else if (node.classList.contains("task-card") && !boundElements.has(node)) {
                  // 初始化任务卡片时间更新
                  this.initializeTaskCard(node);

                  // 为新添加的任务卡片绑定点击事件
                  const boundHandler = this.handleDocumentClick.bind(this);
                  node.addEventListener("click", boundHandler);

                  // 记录事件监听器
                  if (!this._eventListeners.has(".task-card")) {
                    this._eventListeners.set(".task-card", []);
                  }
                  this._eventListeners.get(".task-card").push({
                    element: node,
                    handler: boundHandler,
                  });

                  // 记录已绑定的元素
                  boundElements.add(node);

                  Logger.debug("UIService", `为新添加的 task-card 绑定点击事件`);
                }
              }

              // 查找任务卡片内的按钮并绑定事件
              ["accept-task", "abandon-task", "submit-task"].forEach((btnClass) => {
                const buttons = node.getElementsByClassName(btnClass);
                Array.from(buttons).forEach((btn) => {
                  const boundHandler = this.handleDocumentClick.bind(this);
                  btn.addEventListener("click", boundHandler);

                  // 记录事件监听器
                  if (!this._eventListeners.has(`.${btnClass}`)) {
                    this._eventListeners.set(`.${btnClass}`, []);
                  }
                  this._eventListeners.get(`.${btnClass}`).push({
                    element: btn,
                    handler: boundHandler,
                  });

                  Logger.debug("UIService", `为新添加的 ${btnClass} 按钮绑定点击事件`);
                });
              });

              // 处理新添加节点中的子任务卡片和活动任务卡片
              // 先处理active-task类元素
              const activeTaskCards = node.getElementsByClassName("active-task");
              Array.from(activeTaskCards).forEach((card) => {
                // 如果元素已经绑定过事件，跳过
                if (boundElements.has(card)) {
                  return;
                }

                // 初始化任务卡片时间更新
                this.initializeTaskCard(card);

                // 为新添加的卡片绑定点击事件
                const boundHandler = this.handleDocumentClick.bind(this);
                card.addEventListener("click", boundHandler);

                // 记录事件监听器
                if (!this._eventListeners.has(".active-task")) {
                  this._eventListeners.set(".active-task", []);
                }
                this._eventListeners.get(".active-task").push({
                  element: card,
                  handler: boundHandler,
                });

                // 记录已绑定的元素
                boundElements.add(card);

                Logger.debug("UIService", `为新添加的 active-task 绑定点击事件`);

                // 绑定按钮事件
                this._bindButtonsInCard(card);
              });

              // 再处理task-card类元素，但跳过已绑定过的元素
              const taskCards = node.getElementsByClassName("task-card");
              Array.from(taskCards).forEach((card) => {
                // 如果元素已经绑定过事件，跳过
                if (boundElements.has(card)) {
                  return;
                }

                // 初始化任务卡片时间更新
                this.initializeTaskCard(card);

                // 为新添加的卡片绑定点击事件
                const boundHandler = this.handleDocumentClick.bind(this);
                card.addEventListener("click", boundHandler);

                // 记录事件监听器
                if (!this._eventListeners.has(".task-card")) {
                  this._eventListeners.set(".task-card", []);
                }
                this._eventListeners.get(".task-card").push({
                  element: card,
                  handler: boundHandler,
                });

                // 记录已绑定的元素
                boundElements.add(card);

                Logger.debug("UIService", `为新添加的 task-card 绑定点击事件`);

                // 绑定按钮事件
                this._bindButtonsInCard(card);
              });
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
    });

    // 存储观察器实例以便后续清理
    this.observers.set("taskObserver", taskObserver);

    // 重要：为已存在的任务卡片绑定事件（解决从商城返回首页后点击事件失效的问题）
    this._bindExistingTaskElements();

    Logger.info("UIService", "DOM观察器初始化完成");
  }

  /**
   * 为卡片内的按钮绑定事件
   * @private
   * @param {HTMLElement} card - 任务卡片DOM元素
   */
  _bindButtonsInCard(card) {
    // 查找卡片内的按钮并绑定事件
    ["accept-task", "abandon-task", "submit-task"].forEach((btnClass) => {
      const buttons = card.getElementsByClassName(btnClass);
      Array.from(buttons).forEach((btn) => {
        const boundHandler = this.handleDocumentClick.bind(this);
        btn.addEventListener("click", boundHandler);

        // 记录事件监听器
        if (!this._eventListeners.has(`.${btnClass}`)) {
          this._eventListeners.set(`.${btnClass}`, []);
        }
        this._eventListeners.get(`.${btnClass}`).push({
          element: btn,
          handler: boundHandler,
        });

        Logger.debug("UIService", `为新添加的 ${btnClass} 按钮绑定点击事件`);
      });
    });
  }

  /**
   * 为已存在的任务卡片和按钮绑定点击事件
   * @private
   */
  _bindExistingTaskElements() {
    Logger.debug("UIService", "为已存在的任务卡片绑定事件");

    // 创建一个Set存储已经绑定事件的元素，避免重复绑定
    const boundElements = new Set();

    // 优先处理active-task，因为这些元素可能同时也有task-card类
    const activeTaskCards = document.querySelectorAll(".active-task");
    if (activeTaskCards.length > 0) {
      Logger.debug("UIService", `找到 ${activeTaskCards.length} 个已存在的 active-task 元素`);

      // 为每个active-task绑定点击事件，并记录已绑定的元素
      activeTaskCards.forEach((card) => {
        boundElements.add(card);

        // 绑定点击事件
        const boundHandler = this.handleDocumentClick.bind(this);
        card.addEventListener("click", boundHandler);

        // 记录事件监听器
        if (!this._eventListeners.has(".active-task")) {
          this._eventListeners.set(".active-task", []);
        }
        this._eventListeners.get(".active-task").push({
          element: card,
          handler: boundHandler,
        });
      });

      Logger.debug("UIService", `已为 ${activeTaskCards.length} 个 active-task 元素绑定点击事件`);
    }

    // 处理task-card，但跳过已绑定过的元素
    const taskCards = document.querySelectorAll(".task-card");
    if (taskCards.length > 0) {
      let boundCount = 0;

      taskCards.forEach((card) => {
        // 如果元素已经绑定过事件，跳过
        if (boundElements.has(card)) {
          Logger.debug("UIService", "跳过已绑定过的元素", card.className);
          return;
        }

        boundElements.add(card);
        boundCount++;

        // 绑定点击事件
        const boundHandler = this.handleDocumentClick.bind(this);
        card.addEventListener("click", boundHandler);

        // 记录事件监听器
        if (!this._eventListeners.has(".task-card")) {
          this._eventListeners.set(".task-card", []);
        }
        this._eventListeners.get(".task-card").push({
          element: card,
          handler: boundHandler,
        });
      });

      Logger.debug("UIService", `找到 ${taskCards.length} 个已存在的 task-card 元素，实际绑定了 ${boundCount} 个`);
    }

    // 绑定所有任务按钮
    ["accept-task", "abandon-task", "submit-task"].forEach((btnClass) => {
      const buttons = document.querySelectorAll(`.${btnClass}`);
      if (buttons.length > 0) {
        Logger.debug("UIService", `找到 ${buttons.length} 个已存在的 ${btnClass} 按钮`);

        buttons.forEach((btn) => {
          // 绑定点击事件
          const boundHandler = this.handleDocumentClick.bind(this);
          btn.addEventListener("click", boundHandler);

          // 记录事件监听器
          if (!this._eventListeners.has(`.${btnClass}`)) {
            this._eventListeners.set(`.${btnClass}`, []);
          }
          this._eventListeners.get(`.${btnClass}`).push({
            element: btn,
            handler: boundHandler,
          });
        });

        Logger.debug("UIService", `已为 ${buttons.length} 个 ${btnClass} 按钮绑定点击事件`);
      }
    });

    // 初始化所有任务卡片的时间更新
    document.querySelectorAll(".task-card, .active-task").forEach((card) => {
      this.initializeTaskCard(card);
    });

    Logger.info("UIService", "已为所有现有任务卡片和按钮绑定事件");
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
        area: ["50vw", "60vh"],
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

    // 防止重复弹窗
    const now = Date.now();
    const taskKey = `task_${taskId}`;

    if (this._lastTaskOpened && this._lastTaskOpened.id === taskKey && now - this._lastTaskOpened.time < 500) {
      // 500毫秒内不重复打开
      Logger.debug("UIService", "忽略短时间内重复打开的任务详情:", taskId);
      return;
    }

    // 记录本次打开
    this._lastTaskOpened = {
      id: taskKey,
      time: now,
    };

    try {
      // 从store中获取当前任务数据
      const currentTasks = this.store.state.currentTasks || [];
      Logger.info("UIService", "currentTasks:", currentTasks);
      const task = currentTasks.find((t) => t.id.toString() === taskId.toString());

      // 已经存在相同ID的任务详情弹窗，直接返回
      if (layer.index > 0 && document.querySelector(`.layui-layer[data-task-id="${taskId}"]`)) {
        Logger.debug("UIService", "任务详情弹窗已存在:", taskId);
        return;
      }

      if (!task) {
        // 如果任务不在当前任务列表中，则从API获取
        const response = await this.api.getCurrentTaskById(taskId);
        if (response.code === 0) {
          const taskDetails = response.data;
          layer.open({
            type: 1,
            title: false,
            content: await this.templateService.createCurrentTaskDetailTemplate(taskDetails),
            area: ["50vw", "60vh"],
            shadeClose: true,
            success: (layero) => {
              // 标记弹窗，便于后续检查是否存在
              $(layero).attr("data-task-id", taskId);

              // 绑定当前任务的按钮事件
              this._bindCurrentTaskButtons(layero, taskId);
            },
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
          area: ["50vw", "60vh"],
          shadeClose: true,
          success: (layero) => {
            // 标记弹窗，便于后续检查是否存在
            $(layero).attr("data-task-id", taskId);

            // 绑定当前任务的按钮事件
            this._bindCurrentTaskButtons(layero, taskId);
          },
        });
      }
    } catch (error) {
      Logger.error("UIService", "显示当前任务详情失败:", error);
    }
  }

  /**
   * 绑定当前任务详情弹窗中的按钮事件
   * @param {HTMLElement} layero 弹窗元素
   * @param {string} taskId 任务ID
   * @private
   */
  _bindCurrentTaskButtons(layero, taskId) {
    // 确保layero是jQuery对象
    const $layero = $(layero);

    // 绑定提交任务按钮事件
    const submitBtn = $layero.find(".submit-task");
    if (submitBtn.length) {
      // 先移除可能存在的旧事件
      submitBtn.off("click");
      submitBtn.on("click", (e) => {
        e.stopPropagation(); // 阻止事件冒泡
        Logger.debug("UIService", "点击提交任务按钮");
        this.showConfirmDialog({
          title: "确认提交",
          content: "确定要提交这个任务吗？",
          onConfirm: () => {
            this.eventBus.emit(TASK_EVENTS.SUBMIT, { taskId, playerId: this.playerService.getPlayerId() });
            layer.closeAll();
          },
        });
      });
      Logger.debug("UIService", "已绑定提交任务按钮事件");
    }

    // 绑定放弃任务按钮事件
    const abandonBtn = $layero.find(".abandon-task");
    if (abandonBtn.length) {
      // 先移除可能存在的旧事件
      abandonBtn.off("click");
      abandonBtn.on("click", (e) => {
        e.stopPropagation(); // 阻止事件冒泡
        Logger.debug("UIService", "点击放弃任务按钮");
        this.showConfirmDialog({
          title: "确认放弃",
          content: "确定要放弃这个任务吗？",
          onConfirm: () => {
            this.eventBus.emit(TASK_EVENTS.ABANDONED, { taskId, playerId: this.playerService.getPlayerId() });
            layer.closeAll();
          },
        });
      });
      Logger.debug("UIService", "已绑定放弃任务按钮事件");
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
                            ${card}
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
   * 统一处理任务操作（接受、放弃、提交）
   * @param {string} taskId 任务ID
   * @param {string} operation 操作类型: 'accept', 'abandon', 'submit'
   */
  async handleTaskOperation(taskId, operation) {
    const operationMap = {
      accept: {
        name: "接受",
        event: TASK_EVENTS.ACCEPTED,
        sound: "ACCEPT",
        needConfirm: false,
        message: "确定要接受这个任务吗？",
        title: "接受任务",
        directCall: true, // 是否直接调用任务服务而不是发送事件
      },
      abandon: {
        name: "放弃",
        event: TASK_EVENTS.ABANDONED,
        sound: "CANCEL",
        needConfirm: true,
        message: "确定要放弃这个任务吗？放弃后将无法恢复。",
        title: "放弃任务",
      },
      submit: {
        name: "提交",
        event: TASK_EVENTS.SUBMIT,
        sound: "SUBMIT",
        needConfirm: true,
        message: "确定要提交这个任务吗？",
        title: "提交任务",
      },
    };

    const config = operationMap[operation];
    if (!config) {
      Logger.error("UIService", `无效的任务操作类型: ${operation}`);
      return;
    }

    Logger.info("UIService", `处理${config.name}任务: ${taskId}`);

    try {
      // 对于需要确认的操作，显示确认对话框
      if (config.needConfirm) {
        layer.confirm(
          config.message,
          {
            title: config.title,
            btn: ["确定", "取消"],
            icon: 3,
          },
          () => {
            try {
              // 用户点击确定后触发相应事件
              this.eventBus.emit(config.event, {
                taskId: taskId,
                playerId: this.playerService.getPlayerId(),
              });
              layer.closeAll();
            } catch (error) {
              Logger.error("UIService", `${config.name}任务失败:`, error);
              this.showErrorMessage(`${config.name}任务失败: ${error.message}`);
            }
          }
        );
        return;
      }

      // 接受任务需要直接调用任务服务
      if (config.directCall) {
        const result = await this.taskService.handleTaskAccept(taskId);
        Logger.info("UIService", `${config.name}任务结果:`, result);

        if (result.code === 0) {
          // 只在成功接受的情况下触发事件和播放音效
          this.showNotification({
            type: "SUCCESS",
            message: `任务${config.name}成功`,
          });
          // 任务操作完成，更新任务状态
          this.eventBus.emit(config.event, {
            taskId: taskId,
            playerId: this.playerService.getPlayerId(),
          });
          // 发送音频播放事件
          this.eventBus.emit(AUDIO_EVENTS.PLAY, config.sound);
        } else {
          Logger.error("UIService", `${config.name}任务失败:`, result);
          // 其他情况只显示提示信息
          this.showNotification({
            type: "INFO",
            message: result.msg || `无法${config.name}该任务`,
          });
        }
      } else {
        // 直接触发事件
        this.eventBus.emit(config.event, {
          taskId: taskId,
          playerId: this.playerService.getPlayerId(),
        });

        this.showNotification({
          type: "SUCCESS",
          message: `任务${config.name}成功`,
        });

        // 发送音频播放事件
        this.eventBus.emit(AUDIO_EVENTS.PLAY, config.sound);
      }
    } catch (error) {
      Logger.error("UIService", `处理${config.name}任务失败:`, error);
      this.showNotification({
        type: "ERROR",
        message: error.message || `${config.name}任务失败`,
      });
      // 发送错误音频事件
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

  // 处理任务点击
  handleTaskClick(taskData) {
    Logger.debug("UIService", "处理任务点击:", taskData);
    this.showTaskDetails(taskData);
  }

  /**
   * 处理文档点击事件，作为所有点击事件的统一入口
   * @param {Event} e 点击事件对象
   */
  handleDocumentClick(e) {
    // 阻止默认行为和事件冒泡，避免重复触发
    e.preventDefault();
    e.stopPropagation();

    // 获取当前被点击的元素
    const currentTarget = e.currentTarget;
    const allClasses = currentTarget.className ? currentTarget.className.toString() : "";
    const dataAttrs = currentTarget.dataset ? JSON.stringify(currentTarget.dataset) : "{}";

    Logger.debug("UIService", "处理点击事件:", currentTarget.tagName, `[ID:${currentTarget.id || "none"}]`, `[CLASS:${allClasses}]`, `[DATA:${dataAttrs}]`);

    // 防止点击事件重复触发的标记
    if (e._handled) {
      Logger.debug("UIService", "点击事件已处理，忽略重复处理");
      return;
    }
    e._handled = true;

    // 查找匹配的处理函数并调用
    let handled = false;

    // 特殊处理任务卡片：如果是带有active-task类的任务卡片，优先使用active-task处理器
    if (currentTarget.classList && currentTarget.classList.contains("task-card") && currentTarget.classList.contains("active-task")) {
      const activeTaskHandler = this._clickHandlers["active-task"];
      if (activeTaskHandler) {
        Logger.debug("UIService", "优先使用active-task处理器");
        activeTaskHandler(e, currentTarget);
        return;
      }
    }

    // 遍历所有处理器，查找匹配的
    for (const [selector, handler] of Object.entries(this._clickHandlers)) {
      // 检查是否为ID选择器
      if (selector.startsWith("#")) {
        const id = selector.substring(1);
        if (currentTarget.id === id) {
          Logger.debug("UIService", `找到ID匹配: #${id}`);
          handler(e, currentTarget);
          handled = true;
          break;
        }
      }
      // 检查是否为类选择器
      else if (selector.startsWith(".")) {
        const className = selector.substring(1); // 移除开头的点号
        // 检查元素是否包含该类名 - 使用classList.contains更准确
        if (currentTarget.classList && currentTarget.classList.contains(className)) {
          Logger.debug("UIService", `找到类名匹配: .${className}, 使用处理器: ${selector}`);
          handler(e, currentTarget);
          handled = true;
          break;
        }
      }
      // 直接匹配类名（无点号前缀的选择器）
      else if (currentTarget.classList && currentTarget.classList.contains(selector)) {
        Logger.debug("UIService", `找到直接类名匹配: ${selector}`);
        handler(e, currentTarget);
        handled = true;
        break;
      }
      // 其他选择器（如标签名）
      else if (currentTarget.matches && currentTarget.matches(selector)) {
        Logger.debug("UIService", `找到选择器匹配: ${selector}`);
        handler(e, currentTarget);
        handled = true;
        break;
      }
      // 祖先元素选择器
      else if (currentTarget.closest && currentTarget.closest(selector)) {
        const matchedElement = currentTarget.closest(selector);
        Logger.debug("UIService", `找到祖先元素匹配: ${selector}`);
        handler(e, matchedElement);
        handled = true;
        break;
      }
    }

    if (!handled) {
      Logger.debug("UIService", "未找到匹配的点击处理器:", `元素: ${currentTarget.tagName}`, `[ID:${currentTarget.id || "none"}]`, `[CLASS:${allClasses}]`);
    }
  }

  /**
   * 绑定点击事件到指定选择器的元素
   * @param {string} selector 要绑定的元素选择器
   * @private
   */
  _bindClickEvent(selector) {
    // 移除可能存在的旧事件监听器
    this.removeEventListeners(selector);

    // 查找所有匹配的元素
    const elements = document.querySelectorAll(selector);
    if (elements.length === 0) {
      Logger.debug("UIService", `未找到匹配选择器 ${selector} 的元素`);
      return;
    }

    Logger.debug("UIService", `为 ${elements.length} 个 ${selector} 元素绑定点击事件`);

    // 为每个元素绑定点击事件
    elements.forEach((element) => {
      // 使用handleDocumentClick处理点击事件
      const boundHandler = this.handleDocumentClick.bind(this);
      element.addEventListener("click", boundHandler);

      // 记录事件监听器，用于后续清理
      if (!this._eventListeners.has(selector)) {
        this._eventListeners.set(selector, []);
      }
      this._eventListeners.get(selector).push({
        element,
        handler: boundHandler,
      });
    });
  }

  /**
   * 移除指定选择器的事件监听器
   * @param {string} selector 选择器
   */
  removeEventListeners(selector) {
    if (!this._eventListeners.has(selector)) {
      return;
    }

    const listeners = this._eventListeners.get(selector);
    listeners.forEach(({ element, handler }) => {
      element.removeEventListener("click", handler);
    });

    this._eventListeners.delete(selector);
    Logger.debug("UIService", `已移除 ${listeners.length} 个 ${selector} 元素的点击事件监听器`);
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

    itemElement.innerHTML = this.templateService.renderShopItemCard(item);

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
    const content = this.templateService.renderPurchaseConfirmDialog(item, quantity, totalPrice);

    layer.confirm(
      content,
      {
        title: "购买确认",
        btn: ["确认购买", "取消"],
        area: ["400px", "500px"],
        skin: "purchase-confirm-dialog",
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
              this.eventBus.emit(SHOP_EVENTS.PURCHASE, {
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
        area: ["60vw", "60vh"],
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
      // 检查登录状态并更新登录按钮
      const isLoggedIn = this.playerService.isLoggedIn();
      const playerName = playerData ? playerData.name : "";
      this.updateLoginButton(isLoggedIn, playerName);

      // 确保登录按钮的点击事件被正确绑定
      this._bindClickEvent("#loginBtn");
      this._bindClickEvent(".login-entrance");
      this._bindClickEvent(".shop-entrance");
      Logger.debug("UIService", "玩家信息UI点击事件绑定成功");
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
   * 清理UI服务
   */
  cleanup() {
    Logger.info("UIService", "清理UI服务");
    try {
      // 保存当前状态
      this.saveState();

      // 取消状态订阅
      this.store.unsubscribe("component", this.componentId);

      // 清理所有事件监听器
      this.removeEventListeners();

      // 清理所有观察器
      this.observers.forEach((observer) => observer.disconnect());
      this.observers.clear();

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

  /**
   * 移除所有或指定的事件监听器
   * @param {string} [selector] 可选的选择器，如果提供则只移除该选择器相关的监听器
   */
  removeEventListeners(selector) {
    if (selector) {
      // 移除特定选择器的监听器
      if (this._eventListeners.has(selector)) {
        const listeners = this._eventListeners.get(selector);
        listeners.forEach(({ element, handler }) => {
          element.removeEventListener("click", handler);
        });

        this._eventListeners.delete(selector);
        Logger.debug("UIService", `已移除 ${listeners.length} 个 ${selector} 元素的点击事件监听器`);
      }
    } else {
      // 移除所有监听器
      this._eventListeners.forEach((listeners, selector) => {
        listeners.forEach(({ element, handler }) => {
          element.removeEventListener("click", handler);
        });
        Logger.debug("UIService", `已移除 ${listeners.length} 个 ${selector} 元素的点击事件监听器`);
      });

      this._eventListeners.clear();
      Logger.info("UIService", "已移除所有事件监听器");
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

  // 更新登录按钮状态
  updateLoginButton(isLoggedIn, playerName = "") {
    const loginBtn = document.getElementById("loginBtn");
    if (!loginBtn) {
      Logger.warn("UIService", "未找到登录按钮元素");
      return;
    }

    const loginText = loginBtn.querySelector(".login-text");
    const loginIcon = loginBtn.querySelector(".layui-icon");

    if (isLoggedIn) {
      loginBtn.classList.add("logged-in");
      loginText.textContent = playerName || "已登录";
      loginIcon.classList.remove("layui-icon-user");
      loginIcon.classList.add("layui-icon-logout");
      // 更新按钮提示
      loginBtn.setAttribute("title", "点击登出");
    } else {
      loginBtn.classList.remove("logged-in");
      loginText.textContent = "登录";
      loginIcon.classList.remove("layui-icon-logout");
      loginIcon.classList.add("layui-icon-user");
      // 更新按钮提示
      loginBtn.setAttribute("title", "点击登录");
    }

    Logger.debug("UIService", `登录按钮状态已更新: ${isLoggedIn ? "已登录" : "未登录"}`);
  }

  /**
   * 处理登录按钮点击
   * @param {Event} e 点击事件对象
   * @private
   */
  _handleLoginButtonClick(e) {
    e.preventDefault();
    e.stopPropagation(); // 阻止事件冒泡

    Logger.info("UIService", "处理登录按钮点击");

    if (this.playerService.isLoggedIn()) {
      // 如果已登录，则执行登出
      try {
        const loadingIndex = layer.load(1, {
          shade: [0.2, "#000"],
        });

        this.playerService
          .logout()
          .then(() => {
            layer.close(loadingIndex);

            // 播放音效
            this.eventBus.emit(AUDIO_EVENTS.PLAY, "CLICK");

            // 显示提示
            layer.msg("登出成功", { icon: 1 });
            this.updateLoginButton(false);
          })
          .catch((error) => {
            layer.close(loadingIndex);
            layer.msg(error.message || "登出失败", { icon: 2 });
          });
      } catch (error) {
        layer.msg(error.message || "登出失败", { icon: 2 });
      }
    } else {
      // 如果未登录，显示登录对话框
      this.handleLoginClick();
    }
  }

  /**
   * 处理登录点击事件，显示登录对话框
   */
  async handleLoginClick() {
    Logger.info("UIService", "显示登录对话框");
    try {
      // 关闭可能存在的其他对话框
      layer.closeAll();

      // 获取玩家列表
      const response = await this.playerService.api.request("/api/get_players");
      if (response.code !== 0) {
        throw new Error(response.msg || "获取玩家列表失败");
      }

      const players = response.data;
      if (!players || players.length === 0) {
        layer.msg("暂无可用角色", { icon: 2 });
        return;
      }

      // 创建登录表单
      const loginFormHtml = this.templateService.createLoginDialogTemplate(players);

      layer.open({
        type: 1,
        title: "登录",
        content: loginFormHtml,
        area: ["500px", "auto"],
        shadeClose: false,
        success: (layero) => {
          const form = layui.form;
          // 渲染表单组件
          form.render();

          // 保存this引用，解决回调中this指向问题
          const self = this;

          // 监听表单提交
          form.on("submit(login-submit)", function (data) {
            try {
              let formData = data.field;

              // 修改：优先使用保存在弹窗数据中的已选玩家ID
              let playerId = layero.data("selected-player-id");

              // 如果没有通过data属性获取到，则尝试从选中的radio获取
              if (!playerId) {
                const selectedRadio = layero.find("input[type=radio][lay-ignore]:checked");
                if (selectedRadio.length > 0) {
                  playerId = selectedRadio.val();
                }
              }

              // 记录详细日志，帮助调试
              Logger.debug("UIService", "登录表单提交:", {
                playerId: playerId,
                selectedFromForm: formData.playerId,
                password: "******", // 不记录实际密码
              });

              // 开始登录流程，使用保存的self引用
              self.playerService
                .login(playerId, formData.password)
                .then(() => {
                  if (window.GameManager) {
                    window.GameManager.initializeServices();
                    window.GameManager.initializeApplication();
                    Logger.info("UIService", "登录成功，应用重新初始化完成");
                  }
                  // 关闭登录弹窗
                  layer.closeAll();
                })
                .catch((error) => {
                  Logger.error("UIService", "登录失败:", error);
                  layer.msg(error.message || "登录失败", { icon: 2 });
                });
            } catch (error) {
              Logger.error("UIService", "处理登录表单提交失败:", error);
              layer.msg(error.message || "登录处理失败", { icon: 2 });
            }
            return false; // 阻止表单默认提交
          });

          // 为表单添加必要的layui交互效果
          const playerRadios = layero.find("[lay-radio]");
          playerRadios.on("click", function () {
            // 修改：直接获取当前卡片上的data-player-id属性，确保选择正确的玩家ID
            const playerId = $(this).attr("data-player-id");
            const playerName = $(this).attr("data-player-name");

            // 获取关联的radio输入元素 - 确保选择正确的radio按钮
            const input = layero.find(`input[type=radio][value="${playerId}"]`);

            // 移除所有卡片的选中状态
            layero.find("[lay-radio]").removeClass("selected");

            // 取消选中所有radio按钮
            layero.find("input[type=radio][lay-ignore]").prop("checked", false);

            // 添加当前卡片的选中状态
            $(this).addClass("selected");

            // 选中关联的radio按钮
            input.prop("checked", true);

            // 保存选中的玩家ID到一个全局变量，确保提交时使用正确的ID
            layero.data("selected-player-id", playerId);

            Logger.debug("UIService", "选择玩家:", playerId, playerName);
          });

          // 默认选中第一个玩家
          if (playerRadios.length > 0) {
            playerRadios.first().click();
          }
        },
      });
    } catch (error) {
      Logger.error("UIService", "显示登录对话框失败:", error);
      layer.msg(error.message || "获取玩家列表失败", { icon: 2 });
    }
  }
}

export default UIService;
