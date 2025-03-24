import Logger from "../../utils/logger.js";
import { gameUtils } from "../../utils/utils.js";

class TemplateService {
  constructor(apiClient, eventBus, store) {
    this.api = apiClient;
    this.eventBus = eventBus;
    this.store = store;
    Logger.info("TemplateService", "初始化模板服务");
  }

  /**
   * 获取任务奖励的详细信息
   * @param {Object} task 任务数据
   * @returns {Promise<Object>} 包含完整奖励信息的对象
   */
  async getTaskRewardDetails(task) {
    try {
      const rewards = this.parseTaskRewards(task.task_rewards);

      // 获取道具卡详细信息
      const cardPromises =
        rewards.card_rewards?.map(async (card) => {
          try {
            if (!card || card.id === 0) {
              return null;
            }
            const response = await this.api.request(`/api/game_cards/${card.id}`);
            if (response.code === 0 && response.data) {
              return {
                ...card,
                name: response.data.name,
                icon: response.data.icon || "layui-icon-gift",
              };
            }
            return card;
          } catch (error) {
            Logger.error("TemplateService", `获取道具卡信息失败: ${error}`);
            return null;
          }
        }) || [];

      // 获取勋章详细信息
      const medalPromises =
        rewards.medal_rewards?.map(async (medal) => {
          try {
            if (!medal || medal.id === 0) {
              return null;
            }
            const response = await this.api.request(`/api/medals/${medal.id}`);
            if (response.code === 0 && response.data) {
              return {
                ...medal,
                name: response.data.name,
                icon: response.data.icon || "layui-icon-medal",
              };
            }
            return medal;
          } catch (error) {
            Logger.error("TemplateService", `获取勋章信息失败: ${error}`);
            return null;
          }
        }) || [];

      // 等待所有请求完成
      const [enrichedCards, enrichedMedals] = await Promise.all([Promise.all(cardPromises), Promise.all(medalPromises)]);

      return {
        ...rewards,
        enrichedCards: enrichedCards.filter(Boolean),
        enrichedMedals: enrichedMedals.filter(Boolean),
      };
    } catch (error) {
      Logger.error("TemplateService", "获取任务奖励详情失败:", error);
      throw error;
    }
  }
  // 获取任务卡片内容模板（复用）
  getTaskCardContent(task, taskTypeInfo, rewards) {
    return `
            <div class="task-header" style="background-color: ${taskTypeInfo.color}">
                <div class="task-icon">
                    <i class="layui-icon ${taskTypeInfo.icon}"></i>
                </div>
                <div class="task-info">
                    <h3 class="task-name">${task.name}</h3>
                    <span class="task-type">${taskTypeInfo.text}</span>
                </div>
            </div>
            <div class="task-content">
                <div class="task-details">
                    <p class="task-description">${task.description}</p>
                    <div class="task-time">
                        <i class="layui-icon layui-icon-time"></i>
                        ${task.limit_time ? `限时${Math.floor(task.limit_time / 3600)}小时` : "永久"}
                    </div>
                </div>
                <div class="task-footer">
                    <div class="task-rewards">
                        ${this.renderRewardItems(rewards, task)}
                    </div>
                    <button class="accept-btn accept-task" data-task-id="${task.id}">
                        <i class="layui-icon layui-icon-ok"></i>
                        接受
                    </button>
                </div>
            </div>
        `;
  }

  // 创建任务列表项
  createTaskListItem(task) {
    Logger.debug("TemplateService", "创建任务列表项:", task);
    const taskTypeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);

    const listItem = document.createElement("div");
    listItem.className = "task-list-item";
    listItem.innerHTML = this.getTaskListTemplate(task, taskTypeInfo);
    return listItem;
  }

  // 任务列表项模板
  getTaskListTemplate(task, taskTypeInfo) {
    return `
            <div class="task-card" data-task-id="${task.id}">
                <div class="task-header" style="background-color: ${taskTypeInfo.color}">
                    <div class="task-icon">
                        <i class="layui-icon ${taskTypeInfo.icon}"></i>
                    </div>
                    <div class="task-info">
                        <h3 class="task-name">${task.name}</h3>
                        <span class="task-type">${taskTypeInfo.text}</span>
                    </div>
                </div>
                <div class="task-content">
                    <p class="task-description">${task.description}</p>
                    <div class="task-rewards">
                        <div class="reward-item">
                            <i class="layui-icon layui-icon-diamond"></i>
                            <span>+${task.points}</span>
                        </div>
                        <div class="reward-item">
                            <i class="layui-icon layui-icon-fire"></i>
                            <span>-${task.stamina_cost}</span>
                        </div>
                    </div>
                    <button class="accept-task" data-task-id="${task.id}">
                        <i class="layui-icon layui-icon-add-1"></i>
                        接受任务
                    </button>
                </div>
            </div>
        `;
  }

  // 创建玩家信息面板
  createPlayerInfoPanel(playerData) {
    Logger.debug("TemplateService", "创建玩家信息面板:", playerData);
    const panel = document.createElement("div");
    panel.className = "player-info-panel";
    panel.innerHTML = this.getPlayerInfoTemplate(playerData);
    return panel;
  }

  // 玩家信息面板模板
  getPlayerInfoTemplate(playerData) {
    return `
            <div class="player-header">
                <div class="player-avatar">
                    <img src="${playerData.avatar || "default-avatar.png"}" alt="玩家头像">
                </div>
                <div class="player-basic-info">
                    <h2 id="playerName">${playerData.player_name}</h2>
                    <div class="player-stats">
                        <span class="points">
                            <i class="layui-icon layui-icon-diamond"></i>
                            <span id="playerPoints">${playerData.points}</span>
                        </span>
                        <span class="level">Lv.${playerData.level}</span>
                    </div>
                </div>
            </div>
            <div class="exp-bar">
                <div class="exp-bar-inner" style="width: ${(playerData.experience / 99999) * 100}%"></div>
                <span class="exp">${playerData.experience}/99999</span>
            </div>
        `;
  }

  /**
   *显示错误信息
   * @param {string} containerId 容器ID
   * @param {string} message 错误信息
   */
  showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (container) {
      container.innerHTML = `<div class="empty-tip">${message}</div>`;
    }
  }

  // 解析任务奖励
  parseTaskRewards(taskRewards) {
    let rewards = {
      points: 0,
      exp: 0,
      card_rewards: [],
      medal_rewards: [],
      real_rewards: [],
    };

    try {
      if (taskRewards) {
        const rewardsData = typeof taskRewards === "string" ? JSON.parse(taskRewards) : taskRewards;

        if (rewardsData.points_rewards?.length) {
          rewards.exp = rewardsData.points_rewards[0]?.number || 0;
          rewards.points = rewardsData.points_rewards[1]?.number || 0;
        }
        rewards.card_rewards = rewardsData.card_rewards || [];
        rewards.medal_rewards = rewardsData.medal_rewards || [];
        rewards.real_rewards = rewardsData.real_rewards || [];
      }
    } catch (error) {
      Logger.error("TemplateService", "解析任务奖励失败:", error);
    }

    return rewards;
  }

  // 渲染奖励项
  async renderRewardItems(task) {
    try {
      const rewards = await this.getTaskRewardDetails(task);

      return `
                ${
                  rewards.exp > 0
                    ? `
                    <div class="reward-item">
                        <i class="layui-icon layui-icon-star"></i>
                        <span>+${rewards.exp}</span>
                    </div>
                `
                    : ""
                }
                ${
                  rewards.points > 0
                    ? `
                    <div class="reward-item">
                         <img src="/static/img/points.png" alt="积分">
                        <span>+${rewards.points}</span>
                    </div>
                `
                    : ""
                }
                ${rewards.enrichedCards
                  .map(
                    (card) => `
                    <div class="reward-item" title="${card?.name || "道具卡"}">
                        <img src="${card?.icon || "/static/img/default-icon.png"}" alt="${card?.name || "道具卡"}" >
                        <span>${card?.name || "道具卡"} ${card?.number > 1 ? `x${card.number}` : ""}</span>
                    </div>
                `
                  )
                  .join("")}
                ${rewards.enrichedMedals
                  .map(
                    (medal) => `
                    <div class="reward-item" title="${medal?.name || "勋章"}">
                        <img src="${medal?.icon || "/static/img/default-medal.png"}" alt="${medal?.name || "勋章"}" >
                        <span>${medal?.name || "勋章"}</span>
                    </div>
                `
                  )
                  .join("")}
                ${
                  rewards.real_rewards
                    ?.map(
                      (reward) => `
                    <div class="reward-item" title="${reward?.name || "实物"}">
                        <img src="${reward?.icon || "/static/img/default-reward.png"}" alt="${reward?.name || "实物"}" style="width: 20px; height: 20px;">
                        <span>${reward?.name || "实物"} ${reward?.number > 1 ? `x${reward.number}` : ""}</span>
                    </div>
                `
                    )
                    .join("") || ""
                }
                ${
                  task.stamina_cost
                    ? `
                    <div class="reward-item">
                        <i class="layui-icon layui-icon-fire"></i>
                        <span>-${task.stamina_cost}</span>
                    </div>
                `
                    : ""
                }
            `;
    } catch (error) {
      Logger.error("TemplateService", "渲染任务奖励失败:", error);
      return '<div class="reward-item">奖励加载失败</div>'; // 返回一个错误提示
    }
  }
  /**
   * 创建可用任务卡片
   * @param {Object} task 任务数据
   * @returns {string} 任务卡片HTML
   */
  createTaskCard(task) {
    // Logger.debug("TemplateService", "创建任务卡片:", task);

    try {
      const typeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);
      const rewardsHtml = this.renderRewardItems(task);
      return `
                <div class="swiper-slide" role="group">
                    <div class="task-card" data-task-id="${task.id}"> 
                        <div class="task-header" style="background-color: ${typeInfo.color}">
                            <div class="task-icon">
                                <i class="layui-icon ${typeInfo.icon}"></i>
                            </div>
                            <div class="task-info">
                                <h3 class="task-name">${task.name}</h3>
                                <span class="task-type">${typeInfo.text}</span>
                            </div>
                        </div>
                   <!-- <div class="task-content">
                            <div class="task-footer">
                                <div class="task-rewards">
                                    ${rewardsHtml}
                                </div>
                                <button class="accept-btn accept-task" data-task-id="${task.id}">
                                    <i class="layui-icon layui-icon-ok"></i>
                                    接受
                                </button>
                            </div>
                        </div>-->
                    </div>
                </div>`;
    } catch (error) {
      Logger.error("TemplateService", "创建任务卡片失败:", error);
      return "";
    }
  }

  /**
   * 创建进行中任务卡片
   * @param {Object} task 任务数据
   * @returns {string} 任务卡片HTML
   */
  createActiveTaskCard(task) {
    // Logger.debug("TemplateService", "创建进行中任务卡片:", task);

    try {
      const typeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);
      // const rewards = this.parseTaskRewards(task.task_rewards);
      const rewardsHtml = this.renderRewardItems(task);
      return `
                <div class="task-card active-task" data-task-id="${task.id}" data-endtime="${task.endtime}">
                    <div class="task-header" style="background-color: ${typeInfo.color}">
                        <div class="task-icon">
                            <i class="layui-icon ${typeInfo.icon}"></i>
                        </div>
                        <div class="task-info">
                            <h3 class="task-name">${task.name}</h3>
                            <span class="task-type">${typeInfo.text}</span>
                        </div>
                    </div>
                    <div class="task-content">
                        <div class="task-details">
                            <!--<p class="task-description">${task.description}</p>-->
                            <div class="task-time">
                                <i class="layui-icon layui-icon-time"></i>
                                计算中...
                            </div>
                        </div>
                        <!--<div class="task-footer">
                            <div class="task-rewards">
                                ${rewardsHtml}
                            </div>
                            <button class="abandon-task" data-task-id="${task.id}">
                                <i class="layui-icon layui-icon-close"></i>
                                放弃
                            </button>
                        </div>-->
                    </div>
                    ${task.progress !== undefined ? `<div class="task-progress-bar" style="width: ${task.progress}%"></div>` : ""}
                </div>`;
    } catch (error) {
      Logger.error("TemplateService", "创建进行中任务卡片失败:", error);
      return "";
    }
  }

  /**
   * 创建任务详情模板
   * @param {Object} taskData 任务数据
   * @returns {string} 任务详情HTML
   */
  async createTaskDetailTemplate(taskData) {
    try {
      const typeInfo = gameUtils.getTaskTypeInfo(taskData.task_type, taskData.icon);
      const rewardsHtml = await this.renderRewardItems(taskData);

      return `
                <div class="task-detail-popup">
                    <div class="task-header" style="background-color: ${typeInfo?.color || "#4CAF50"}">
                        <div class="task-icon">
                            <i class="layui-icon ${typeInfo?.icon || "layui-icon-flag"}"></i>
                        </div>
                        <div class="task-info">
                            <h3 class="task-name">${taskData.name}</h3>
                            <span class="task-type">${typeInfo?.text || "未知类型"}</span>
                        </div>
                    </div>
                    <div class="task-content">
                        <div class="description">${taskData.description}</div>
                        <div class="rewards-section">
                            <h4>任务奖励</h4>
                            <div class="rewards-list">
                                ${rewardsHtml}
                            </div>
                        </div>
                        ${
                          taskData.endTime
                            ? `
                            <div class="task-deadline">
                                <i class="layui-icon layui-icon-time"></i>
                                <span>截止时间: ${this.formatTime(taskData.endTime)}</span>
                            </div>
                        `
                            : ""
                        }
                        <div class="task-actions">
                            <button class="accept-btn accept-task layui-btn" data-task-id="${taskData.id}">
                                <i class="layui-icon layui-icon-ok"></i>
                                接受任务
                            </button>
                        </div>
                    </div>
                </div>`;
    } catch (error) {
      Logger.error("TemplateService", "创建任务详情模板失败:", error);
      return "";
    }
  }

  /**
   * 获取空任务提示模板
   * @returns {string} 空任务提示HTML
   */
  getEmptyTaskTemplate() {
    return `
            <div class="swiper-slide">
                <div class="empty-task">
                    <i class="layui-icon layui-icon-face-surprised"></i>
                    <p>暂无任务</p>
                </div>
            </div>`;
  }

  /**
   * 渲染任务进度条
   * @param {Object} task 任务数据
   * @returns {string} 进度条HTML
   */
  renderProgress(task) {
    if (!task.progress && task.progress !== 0) return "";

    return `
            <div class="task-progress">
                <div class="progress-bar" style="width: ${task.progress}%" aria-valuenow="${task.progress}">
                    <span class="progress-text">${task.progress}%</span>
                </div>
            </div>`;
  }

  /**
   * 渲染任务奖励
   * @param {Array} rewards 奖励数据
   * @returns {string} 奖励HTML
   */
  renderRewards(rewards) {
    if (!rewards || !rewards.length) return "";

    return rewards
      .map(
        (reward) =>
          `<div class="reward-item">
                <i class="layui-icon ${reward.icon}"></i>
                <span>${reward.value} ${reward.unit}</span>
            </div>`
      )
      .join("");
  }

  /**
   * 格式化时间
   * @param {number} timestamp 时间戳
   * @returns {string} 格式化后的时间
   */
  formatTime(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  /**
   * 创建当前任务详情模板
   * @param {Object} taskData 任务数据
   * @returns {string} 当前任务详情HTML
   */
  async createCurrentTaskDetailTemplate(taskData) {
    try {
      const typeInfo = gameUtils.getTaskTypeInfo(taskData.task_type, taskData.icon);
      const rewardsHtml = await this.renderRewardItems(taskData);

      return `
                <div class="task-detail-popup">
                    <div class="task-header" style="background-color: ${typeInfo?.color || "#4CAF50"}">
                        <div class="task-icon">
                            <i class="layui-icon ${typeInfo?.icon || "layui-icon-flag"}"></i>
                        </div>
                        <div class="task-info">
                            <h3 class="task-name">${taskData.name}</h3>
                            <span class="task-type">${typeInfo?.text || "未知类型"}</span>
                        </div>
                    </div>
                    <div class="task-content">
                        <div class="description">${taskData.description}</div>
                        <div class="rewards-section">
                            <h4>任务奖励</h4>
                            <div class="rewards-list">
                                ${rewardsHtml}
                            </div>
                        </div>
                        <div class="task-time-info">
                            <div class="task-starttime">
                                <i class="layui-icon layui-icon-time"></i>
                                <span>开始时间: ${this.formatTime(taskData.starttime)}</span>
                            </div>
                            ${
                              taskData.endtime
                                ? `
                                <div class="task-deadline">
                                    <i class="layui-icon layui-icon-time"></i>
                                    <span>截止时间: ${this.formatTime(taskData.endtime)}</span>
                                </div>
                            `
                                : ""
                            }
                        </div>
                        <div class="task-actions">
                            <button class="submit-btn submit-task" data-task-id="${taskData.id}">
                                <i class="layui-icon layui-icon-ok"></i>
                                提交任务
                            </button>
                            <button class="abandon-btn abandon-task" data-task-id="${taskData.id}">
                                <i class="layui-icon layui-icon-close"></i>
                                放弃任务
                            </button>
                        </div>
                    </div>
                </div>`;
    } catch (error) {
      Logger.error("TemplateService", "创建当前任务详情模板失败:", error);
      return "";
    }
  }

  /**
   * 创建登录弹窗模板
   * @param {Array} players 可选的玩家列表
   * @returns {string} 登录弹窗HTML
   */
  createLoginDialogTemplate(players = []) {
    return `
        <div class="login-dialog">
            <div class="layui-form login-form">
                <div class="layui-form-item">
                    <label class="layui-form-label">选择角色</label>
                    <div class="layui-input-block">
                        <div class="player-type-container">
                            ${players
                                .map(
                                    (player) => `
                                <input type="radio" name="player_id" value="${player.player_id}" title="${player.player_name}" lay-skin="none" lay-ignore>
                                <div lay-radio class="lay-skin-taskcard" data-player-id="${player.player_id}" data-player-name="${player.player_name}">
                                    <div class="lay-skin-taskcard-detail">
                                        <div class="lay-skin-taskcard-header">
                                            <i class="layui-icon layui-icon-username"></i>
                                            ${player.player_name}
                                        </div>
                                        <div class="lay-skin-taskcard-description">
                                            <span>等级 ${player.level || 1}</span>
                                        </div>
                                    </div>
                                </div>
                            `
                                )
                                .join("")}
                        </div>
                    </div>
                </div>
                <div class="layui-form-item">
                    <label class="layui-form-label">密码</label>
                    <div class="layui-input-block">
                        <input type="password" name="password" class="layui-input" 
                            placeholder="请输入密码" lay-verify="required" 
                            lay-reqText="请输入密码">
                    </div>
                </div>
                <div class="layui-form-item">
                    <div class="layui-input-block">
                        <button class="layui-btn" lay-submit lay-filter="login-submit">
                            <i class="layui-icon layui-icon-ok"></i> 登录
                        </button>
                        <button type="reset" class="layui-btn layui-btn-primary">
                            <i class="layui-icon layui-icon-refresh"></i> 重置
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
  }

  /**
   * 更新登录按钮状态
   * @param {boolean} isLoggedIn 是否已登录
   * @param {string} playerName 玩家名称
   */
  updateLoginButton(isLoggedIn, playerName = "") {
    const loginBtn = document.getElementById("loginBtn");
    if (!loginBtn) return;

    const loginText = loginBtn.querySelector(".login-text");
    if (isLoggedIn) {
      loginBtn.classList.add("logged-in");
      loginText.textContent = playerName;
    } else {
      loginBtn.classList.remove("logged-in");
      loginText.textContent = "登录";
    }
  }

  /**
   * 渲染商店物品卡片
   * @param {Object} item 物品数据
   * @returns {string} 物品卡片HTML
   */
  renderShopItemCard(item) {
    // 使用base64默认图片
    const DEFAULT_ITEM_IMAGE = "/static/img/shop/default_item.svg";

    return `
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
  }
  /**
   * 渲染购买确认对话框
   * @param {Object} item 商品数据
   * @param {number} quantity 购买数量
   * @param {number} totalPrice 总价
   * @returns {string} 购买确认对话框HTML
   *
   * */
  renderPurchaseConfirmDialog(item, quantity, totalPrice) {
    return `
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
  }
}

export default TemplateService;
