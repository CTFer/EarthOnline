import Logger from '../../utils/logger.js';

class TemplateService {
    constructor() {
        Logger.info('TemplateService', '初始化模板服务');
    }

    // 获取活动任务卡片模板
    getActiveTaskTemplate(task, taskTypeInfo, progressPercent) {
        Logger.debug('TemplateService', '生成活动任务卡片模板:', task);
        return `
            <div class="task-card active-task" data-endtime="${task.endtime}">
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
                            计算中...
                        </div>
                    </div>
                    <div class="task-footer">
                        <div class="task-rewards">
                            ${this.renderRewardItems(task)}
                        </div>
                        <button class="abandon-task" data-task-id="${task.id}">
                            <i class="layui-icon layui-icon-close"></i>
                            放弃
                        </button>
                    </div>
                </div>
                <div class="task-progress-bar" style="width: ${progressPercent}%"></div>
            </div>
        `;
    }

    // 获取可用任务卡片模板
    getAvailableTaskTemplate(task, taskTypeInfo, rewards) {
        Logger.debug('TemplateService', '生成可用任务卡片模板:', task);
        return `
            <div class="swiper-slide">
                <div class="task-card" onclick="GameManager.uiService.showTaskDetails(${JSON.stringify({
                    ...task,
                    typeInfo: taskTypeInfo,
                    rewards: rewards
                }).replace(/"/g, '&quot;')})">
                    ${this.getTaskCardContent(task, taskTypeInfo, rewards)}
                </div>
            </div>
        `;
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
                        ${task.limit_time ? `限时${Math.floor(task.limit_time/3600)}小时` : '永久'}
                    </div>
                </div>
                <div class="task-footer">
                    <div class="task-rewards">
                        ${this.renderRewardItems(rewards, task)}
                    </div>
                    <button class="accept-btn" onclick="event.stopPropagation(); GameManager.acceptTask(${task.id})">
                        <i class="layui-icon layui-icon-ok"></i>
                        接受
                    </button>
                </div>
            </div>
        `;
    }

    // 创建任务列表项
    createTaskListItem(task) {
        Logger.debug('TemplateService', '创建任务列表项:', task);
        const taskTypeInfo = this.getTaskTypeInfo(task.task_type, task.icon);
        
        const listItem = document.createElement('div');
        listItem.className = 'task-list-item';
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
        Logger.debug('TemplateService', '创建玩家信息面板:', playerData);
        const panel = document.createElement('div');
        panel.className = 'player-info-panel';
        panel.innerHTML = this.getPlayerInfoTemplate(playerData);
        return panel;
    }

    // 玩家信息面板模板
    getPlayerInfoTemplate(playerData) {
        return `
            <div class="player-header">
                <div class="player-avatar">
                    <img src="${playerData.avatar || 'default-avatar.png'}" alt="玩家头像">
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


    // 显示错误信息
    showError(containerId, message) {
        Logger.warn('TemplateService', '显示错误信息:', message);
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="empty-tip">${message}</div>`;
        }
    }

    // 解析任务奖励
    parseTaskRewards(taskRewards) {
        let rewards = { points: 0, exp: 0, cards: [], medals: [] };
        
        try {
            if (taskRewards) {
                const rewardsData = typeof taskRewards === 'string' ? 
                    JSON.parse(taskRewards) : taskRewards;
                
                if (rewardsData.points_rewards?.length) {
                    rewards.exp = rewardsData.points_rewards[0]?.number || 0;
                    rewards.points = rewardsData.points_rewards[1]?.number || 0;
                }
                rewards.cards = rewardsData.card_rewards || [];
                rewards.medals = rewardsData.medal_rewards || [];
            }
        } catch (error) {
            Logger.error('TemplateService', '解析任务奖励失败:', error);
        }
        
        return rewards;
    }

    // 渲染奖励项
    renderRewardItems(task) {
        const rewards = this.parseTaskRewards(task.task_rewards);
        return `
            ${rewards.exp > 0 ? `
                <div class="reward-item">
                    <i class="layui-icon layui-icon-star"></i>
                    <span>+${rewards.exp}</span>
                </div>
            ` : ''}
            ${rewards.points > 0 ? `
                <div class="reward-item">
                    <i class="layui-icon layui-icon-diamond"></i>
                    <span>+${rewards.points}</span>
                </div>
            ` : ''}
            <div class="reward-item">
                <i class="layui-icon layui-icon-fire"></i>
                <span>-${task.stamina_cost}</span>
            </div>
        `;
    }
}

export default TemplateService; 