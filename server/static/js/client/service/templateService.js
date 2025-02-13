class TemplateService {
    constructor() {
        console.log('[TemplateService] Initialized');
    }

    // 创建活动任务卡片
    createActiveTaskCard(task) {
        console.log('[TemplateService] Creating active task card:', task);
        const taskTypeInfo = this.getTaskTypeInfo(task.task_type, task.icon);
        const currentTime = Math.floor(Date.now()/1000);
        const progressPercent = Math.max(0, Math.min(100, 
            ((task.endtime - currentTime) / (task.endtime - task.starttime)) * 100
        ));
        
        const slide = document.createElement('div');
        slide.className = 'swiper-slide';
        
        slide.innerHTML = this.getActiveTaskTemplate(task, taskTypeInfo, progressPercent);
        return slide;
    }

    // 活动任务卡片模板
    getActiveTaskTemplate(task, taskTypeInfo, progressPercent) {
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
                            <div class="reward-item">
                                <i class="layui-icon layui-icon-diamond"></i>
                                <span>+${task.points}</span>
                            </div>
                            <div class="reward-item">
                                <i class="layui-icon layui-icon-fire"></i>
                                <span>-${task.stamina_cost}</span>
                            </div>
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

    // 创建任务列表项
    createTaskListItem(task) {
        console.log('[TemplateService] Creating task list item:', task);
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
        console.log('[TemplateService] Creating player info panel:', playerData);
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

    // 获取任务类型信息
    getTaskTypeInfo(type, defaultIcon = '') {
        const typeMap = {
            DAILY: { text: '日常任务', color: '#4CAF50', icon: 'layui-icon-date' },
            WEEKLY: { text: '每周任务', color: '#2196F3', icon: 'layui-icon-log' },
            ACHIEVEMENT: { text: '成就任务', color: '#9C27B0', icon: 'layui-icon-trophy' },
            EVENT: { text: '活动任务', color: '#FF9800', icon: 'layui-icon-gift' },
            MAIN: { text: '主线任务', color: '#F44336', icon: 'layui-icon-flag' }
        };

        return typeMap[type] || { text: '未知任务', color: '#9E9E9E', icon: defaultIcon || 'layui-icon-help' };
    }

    // 显示错误信息
    showError(containerId, message) {
        console.log('[TemplateService] Showing error message:', message);
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="empty-tip">${message}</div>`;
        }
    }
}

export default TemplateService; 