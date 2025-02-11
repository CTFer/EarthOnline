// 任务管理类
class TaskManager {
    constructor() {
        this.activeTasksSwiper = null;
        this.playerId = localStorage.getItem('playerId') || localStorage.setItem('playerId', '1');// 如果本地没有playerId，则设置为1
        this.loading = false;
        this.initWebSocket();
        this.loadPlayerInfo(); // 在构造函数中调用加载角色信息
    }



    // 处理NFC任务更新通知
    handleTaskUpdate(data) {
        console.log('[WebSocket] Processing task update:', data);
        
        if (!data || !data.type) {
            console.error('[WebSocket] Invalid task update data');
            this.showNotification({
                type: 'ERROR',
                message: '收到无效的任务更新'
            });
            return;
        }

        // 处理特殊类型
        switch(data.type) {
            case 'IDENTITY':
                this.playerId = data.player_id;
                localStorage.setItem('playerId', data.player_id);
                this.loadPlayerInfo(); // 重新加载玩家信息
                this.refreshTasks();   // 刷新任务列表
                break;
            
            case 'NEW_TASK':
            case 'COMPLETE':
            case 'CHECK':
                // 刷新任务列表
                this.refreshTasks();
                // 播放相应的音效
                this.playTaskSound(data.type);
                break;
            
            case 'ALREADY_COMPLETE':
            case 'REJECT':
            case 'CHECKING':
                // 这些状态只需要显示通知，不需要刷新任务
                break;
            
            case 'ERROR':
                // 错误状态可以播放错误音效
                this.playErrorSound();
                break;
        }

        // 显示通知
        this.showNotification(data);
    }

    // 播放任务相关音效
    playTaskSound(type) {
        const audio = new Audio();
        switch(type) {
            case 'NEW_TASK':
                audio.src = '/static/sounds/new_task.mp3';
                break;
            case 'COMPLETE':
                audio.src = '/static/sounds/complete.mp3';
                break;
            case 'CHECK':
                audio.src = '/static/sounds/check.mp3';
                break;
        }
        audio.play().catch(e => console.log('音效播放失败:', e));
    }

    // 播放错误音效
    playErrorSound() {
        const audio = new Audio('/static/sounds/error.mp3');
        audio.play().catch(e => console.log('音效播放失败:', e));
    }

    // 显示通知
    showNotification(data) {
        const typeInfo = data.task?.task_type ? 
            gameUtils.getTaskTypeInfo(data.task.task_type) : 
            { color: '#009688', icon: 'layui-icon-notice', text: '系统消息' };

        layer.open({
            type: 1,
            title: false,
            closeBtn: true,
            shadeClose: true,
            area: ['500px', 'auto'],
            skin: 'layui-layer-nobg',
            content: `
                <div class="task-notification">
                    <div class="task-header">
                        <div class="task-icon" style="color: ${typeInfo.color}">
                            <i class="layui-icon ${typeInfo.icon}"></i>
                        </div>
                        <div class="task-title">
                            <h3>${data.task?.name || '系统消息'}</h3>
                            <small>${typeInfo.text}</small>
                        </div>
                    </div>
                    ${data.task?.description ? `
                        <div class="task-description">${data.task.description}</div>
                    ` : ''}
                    <div class="task-status">
                        <span class="status-badge" style="background: ${this.getStatusColor(data.type)}">
                            ${this.getStatusText(data.type)}
                        </span>
                        <span class="task-message">${data.message || this.getDefaultMessage(data.type)}</span>
                    </div>
                    ${data.task?.rewards ? `
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
                    ` : ''}
                    ${data.timestamp ? `
                        <div class="task-time">
                            打卡时间: ${new Date(data.timestamp * 1000).toLocaleString()}
                        </div>
                    ` : ''}
                </div>
            `
        });
    }

    // 获取默认消息
    getDefaultMessage(type) {
        switch(type) {
            case 'IDENTITY':
                return '身份识别成功';
            case 'NEW_TASK':
                return '新任务已添加';
            case 'COMPLETE':
                return '任务完成';
            case 'ALREADY_COMPLETED':
                return '该任务已完成';
            case 'CHECKING':
                return '任务正在审核中';
            case 'REJECTED':
                return '任务被驳回';
            case 'ERROR':
                return '任务处理出错';
            default:
                return '收到任务更新';
        }
    }

    // 获取消息图标
    getMessageIcon(type) {
        switch(type) {
            case 'IDENTITY':
            case 'NEW_TASK':
            case 'COMPLETE':
                return 1;  // 成功
            case 'ALREADY_COMPLETED':
            case 'CHECKING':
                return 0;  // 信息
            case 'REJECTED':
            case 'ERROR':
                return 2;  // 错误
            default:
                return 0;  // 默认信息
        }
    }

    // 处理任务状态更新
    handleTaskStatusUpdate(data) {
        console.log('[WebSocket] Processing task status update:', data);
        
        if (!data || !data.id) {
            console.error('[WebSocket] Invalid task status update data');
            return;
        }

        try {
            const container = document.querySelector('.swiper-wrapper');
            if (!container) {
                console.warn('[WebSocket] Task container not found');
                return;
            }

            // 根据任务状态更新UI
            if (data.status === 'COMPLETED' || data.status === 'ABANDONED') {
                console.log(`[WebSocket] Removing task ${data.id} (${data.status})`);
                const taskCard = container.querySelector(`[data-task-id="${data.id}"]`);
                if (taskCard) {
                    taskCard.remove();
                }
            } else {
                console.log(`[WebSocket] Updating task ${data.id} status to ${data.status}`);
                const taskCard = container.querySelector(`[data-task-id="${data.id}"]`);
                if (taskCard) {
                    const newCard = this.createCurrentTaskCard(data);
                    taskCard.outerHTML = newCard;
                }
            }

            // 刷新Swiper
            this.initSwiper();
        } catch (error) {
            console.error('[WebSocket] Error handling task status update:', error);
        }
    }

    // 加载可用任务列表
    async loadTasks() {
        if (this.loading) return;
        
        this.loading = true;
        const taskList = document.getElementById('taskList');
        taskList.innerHTML = `
            <div class="swiper task-list-swiper">
                <div class="swiper-wrapper">
                    <div class="swiper-slide">
                        <div class="loading-state">加载中...</div>
                    </div>
                </div>
                <div class="swiper-scrollbar"></div>
            </div>
        `;
        
        try {
            const response = await fetch(`${SERVER}/api/tasks/available/${this.playerId}`);
            const result = await response.json();
            
            if (result.code === 0) {
                const tasks = result.data;
                const swiperWrapper = taskList.querySelector('.swiper-wrapper');
                
                if (!tasks || tasks.length === 0) {
                    swiperWrapper.innerHTML = `
                        <div class="swiper-slide">
                            <div class="empty-tip">暂无可用任务</div>
                        </div>
                    `;
                } else {
                    swiperWrapper.innerHTML = tasks.map(task => this.createTaskCard(task)).join('');
                }
                
                // 初始化任务列表的 Swiper
                this.initTaskListSwiper();
            } else {
                this.showError('taskList', result.msg);
            }
        } catch (error) {
            console.error('加载任务失败:', error);
            this.showError('taskList', '加载任务失败，请稍后重试');
        } finally {
            this.loading = false;
        }
    }

    // 创建任务卡片
    createTaskCard(task) {
        const taskTypeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);
        let rewards = { points: 0, exp: 0, cards: [], medals: [] };
        
        // 解析任务奖励
        try {
            if (task.task_rewards) {
                const rewardsData = typeof task.task_rewards === 'string' ? 
                    JSON.parse(task.task_rewards) : task.task_rewards;
                
                if (rewardsData.points_rewards?.length) {
                    rewards.exp = rewardsData.points_rewards[0]?.number || 0;
                    rewards.points = rewardsData.points_rewards[1]?.number || 0;
                }
                rewards.cards = rewardsData.card_rewards || [];
                rewards.medals = rewardsData.medal_rewards || [];
            }
        } catch (error) {
            console.error('解析任务奖励失败:', error);
        }
        
        return `
            <div class="swiper-slide">
                <div class="task-card" onclick="taskManager.showTaskDetails(${JSON.stringify({
                    ...task,
                    typeInfo: taskTypeInfo,
                    rewards: rewards
                }).replace(/"/g, '&quot;')})">
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
                            </div>
                            <button class="accept-btn" onclick="event.stopPropagation(); taskManager.acceptTask(${task.id})">
                                <i class="layui-icon layui-icon-ok"></i>
                                接受
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    // 显示任务详情
    showTaskDetails(taskData) {
        const { typeInfo, rewards } = taskData;
        console.log(typeInfo);
        layui.use('layer', function() {
            const layer = layui.layer;
            
            layer.open({
                type: 1,
                title: false,
                closeBtn: 1,
                shadeClose: true,
                skin: 'task-detail-layer',
                area: ['600px', 'auto'],
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
                                        <span class="value">${taskData.task_scope || '无限制'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">体力消耗</span>
                                        <span class="value">${taskData.stamina_cost}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">时间限制</span>
                                        <span class="value">${taskData.limit_time ? `${Math.floor(taskData.limit_time/3600)}小时` : '无限制'}</span>
                                    </div>
                                    <div class="info-item">
                                        <span class="label">可重复次数</span>
                                        <span class="value">${taskData.repeat_time || (taskData.repeatable ? '无限' : '1')}</span>
                                    </div>
                                </div>
                            </div>

                            <div class="detail-section">
                                <h3>任务奖励</h3>
                                <div class="rewards-grid">
                                    ${rewards.exp > 0 ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-star"></i>
                                            <span>${rewards.exp} 经验</span>
                                        </div>
                                    ` : ''}
                                    ${rewards.points > 0 ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-diamond"></i>
                                            <span>${rewards.points} 积分</span>
                                        </div>
                                    ` : ''}
                                    ${rewards.cards.length > 0 ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-picture"></i>
                                            <span>${rewards.cards.length}张卡片</span>
                                        </div>
                                    ` : ''}
                                    ${rewards.medals.length > 0 ? `
                                        <div class="reward-detail">
                                            <i class="layui-icon layui-icon-medal"></i>
                                            <span>${rewards.medals.length}枚勋章</span>
                                        </div>
                                    ` : ''}
                                </div>
                            </div>
                            
                            ${taskData.parent_task_id ? `
                                <div class="detail-section">
                                    <h3>前置任务</h3>
                                    <p>需要完成任务ID: ${taskData.parent_task_id}</p>
                                </div>
                            ` : ''}
                        </div>
                        <div class="task-detail-footer">
                            <button class="accept-task-btn" onclick="taskManager.acceptTask(${taskData.id}); layer.closeAll();">
                                <i class="layui-icon layui-icon-ok"></i>
                                接受任务
                            </button>
                        </div>
                    </div>
                `
            });
        });
    }

    // 加载当前任务（仅在页面首次加载时调用）
    async loadCurrentTasks() {
        try {
            const response = await fetch(`${SERVER}/api/tasks/current/${this.playerId}`);
            const result = await response.json();

            if (result.code === 0) {
                let currentTasks = result.data;

                // 如果没有进行中的任务，添加测试任务
                if (!currentTasks || !currentTasks.length) {
                    currentTasks = [{
                        id: 'test-3',
                        name: '探索神秘遗迹',
                        description: '在荒野中寻找并调查一处古代遗迹，记录发现的文物和历史痕迹。',
                        task_type: 'EXPLORE',
                        points: 1000,
                        points_earned: 450,
                        stamina_cost: 50,
                        endtime: Math.floor(Date.now() / 1000) + 7200,
                        starttime: Math.floor(Date.now() / 1000) - 3600,
                        progress: 45
                    }];
                }

                this.renderCurrentTasks(currentTasks);
            } else {
                console.error('加载进行中任务失败:', result.msg);
                this.showError('active-tasks-wrapper', result.msg);
            }
        } catch (error) {
            console.error('加载进行中任务失败:', error);
            this.showError('active-tasks-wrapper', '加载任务失败');
        }
    }

    // 修改渲染进行中的任务列表
    renderCurrentTasks(tasks) {
        const container = document.querySelector('.swiper-wrapper');
        if (!container) return;

        // 确保分页器容器存在
        const swiperContainer = container.closest('.active-tasks-swiper');
        if (swiperContainer) {
            // 检查并添加分页器元素
            if (!swiperContainer.querySelector('.swiper-pagination')) {
                swiperContainer.insertAdjacentHTML('beforeend', '<div class="swiper-pagination"></div>');
            }

            // 检查并添加滚动条
            if (!swiperContainer.querySelector('.swiper-scrollbar')) {
                swiperContainer.insertAdjacentHTML('beforeend', '<div class="swiper-scrollbar"></div>');
            }
        }

        if (!tasks || !Array.isArray(tasks) || tasks.length === 0) {
            container.innerHTML = `
                <div class="swiper-slide">
                    <div class="empty-tip">暂无进行中的任务</div>
                </div>
            `;
            this.initSwiper();
            return;
        }

        // 每个任务渲染到独立的slide中
        const slidesHtml = tasks.map(task => `
            <div class="swiper-slide">
                <div class="task-panel">
                    ${this.createCurrentTaskCard(task)}
                </div>
            </div>
        `).join('');

        container.innerHTML = slidesHtml;
        this.initSwiper();
    }

    // 创建进行中的任务卡片
    createCurrentTaskCard(task) {
        const typeInfo = gameUtils.getTaskTypeInfo(task.task_type);
        const endTime = gameUtils.calculateTaskEndTime(task);
        const timeRemaining = endTime - new Date();
        const timeDisplay = gameUtils.formatTimeRemaining(timeRemaining);
        const currentTime = Math.floor(Date.now()/1000);
        const progressPercent = Math.max(0, Math.min(100, 
            ((task.endtime - currentTime) / (task.endtime - task.starttime)) * 100
        ));

        return `
            <div class="task-card current" data-task-id="${task.id}">
                <div class="task-progress-bar" style="width: ${progressPercent}%"></div>
                <div class="task-content">
                    <div class="task-header">
                        <div class="task-type-badge" style="background: ${typeInfo.color}; color: ${typeInfo.color}">
                            <i class="layui-icon ${typeInfo.icon}"></i>
                            <span>${typeInfo.text}</span>
                        </div>
                        <div class="task-timer" data-end-time="${task.endtime}">
                            <i class="layui-icon layui-icon-time"></i>
                            <span>${timeDisplay}</span>
                        </div>
                    </div>
                    <div class="task-content">
                        <h3 class="task-name">${task.name}</h3>
                        <p class="task-description">${task.description}</p>
                    </div>
                    <div class="task-footer">
                        <div class="task-rewards">
                            <div class="reward-item">
                                <i class="layui-icon layui-icon-diamond"></i>
                                <span>${task.points || 0}</span>
                            </div>
                            <div class="reward-item">
                                <i class="layui-icon layui-icon-dollar"></i>
                                <span>${task.gold_reward || 0}</span>
                            </div>
                        </div>
                        <button class="layui-btn layui-btn-danger layui-btn-sm abandon-task" data-task-id="${task.id}">
                            <i class="layui-icon layui-icon-close"></i>
                            放弃任务
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // 初始化Swiper
    initSwiper() {
        if (this.activeTasksSwiper) {
            this.activeTasksSwiper.destroy(true, true);
        }

        const swiperContainer = document.querySelector('.active-tasks-swiper');
        if (!swiperContainer) return;

        this.activeTasksSwiper = new Swiper('.active-tasks-swiper', {
            slidesPerView: 3,
            spaceBetween: 30,
            direction: 'horizontal',

            loop: false,
            
            // 添加分页器
            // pagination: {
            //     el: '.swiper-pagination',
            //     clickable: true, // 允许点击分页器切换
            //     dynamicBullets: true, // 动态分页器
            //     dynamicMainBullets: 3 // 主要显示的分页点数量
            // },



            mousewheel: {
                forceToAxis: true,
                invert: false,
                sensitivity: 1
            },
            
            scrollbar: {
                el: '.swiper-scrollbar',
                draggable: true,
                hide: false,
                snapOnRelease: true
            }
        });
    }

    // 接受任务
    async acceptTask(taskId) {
        try {
            console.group('接受任务请求');
            console.log('任务ID:', taskId);
            console.log('玩家ID:', this.playerId);
            
            const response = await fetch(`${SERVER}/api/tasks/${taskId}/accept`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    player_id: this.playerId
                })
            });
            
            const result = await response.json();
            console.log('API响应:', result);

            if (result.code === 0) {
                layer.msg(`成功接受任务: ${result.data.task_name}`, {icon: 1});
                await this.refreshTasks();
            } else {
                let icon = 2;
                switch(result.code) {
                    case 1: // 参数错误
                        icon = 0;
                        break;
                    case 2: // 前置任务未完成
                        icon = 4;
                        break;
                    default:
                        icon = 2;
                }
                layer.msg(result.msg, {icon: icon});
            }
        } catch (error) {
            console.error('接受任务失败:', error);
            layer.msg('接受任务失败，请检查网络连接', {icon: 2});
        } finally {
            console.groupEnd();
        }
    }

    // 放弃任务
    async abandonTask(taskId) {
        layer.confirm('确定要放弃这个任务吗？', {
            btn: ['确定','取消']
        }, async () => {
            try {
                const response = await fetch(`${SERVER}/api/tasks/${taskId}/abandon`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        player_id: this.playerId
                    })
                });
                
                const result = await response.json();
                
                if (result.code === 0) {
                    layer.msg(result.msg, {icon: 1});
                    await this.refreshTasks();
                } else {
                    layer.msg(result.msg, {icon: 2});
                }
            } catch (error) {
                console.error('放弃任务失败:', error);
                layer.msg('放弃任务失败，请检查网络连接', {icon: 2});
            }
        });
    }

    // 完成任务
    async completeTask(taskId) {
        try {
            const response = await fetch(`${SERVER}/api/tasks/${taskId}/complete`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    player_id: this.playerId
                })
            });
            
            const result = await response.json();
            
            if (result.code === 0) {
                layer.msg(`${result.msg}，获得 ${result.data.points} 点经验`, {icon: 1});
                await this.refreshTasks();
            } else {
                layer.msg(result.msg, {icon: 2});
            }
        } catch (error) {
            console.error('完成任务失败:', error);
            layer.msg('完成任务失败，请检查网络连接', {icon: 2});
        }
    }

    // 刷新所有任务
    async refreshTasks() {
        try {
            await Promise.all([
                this.loadTasks(),
            ]);
        } catch (error) {
            console.error('刷新任务失败:', error);
            layer.msg('刷新任务失败', {icon: 2});
        }
    }

    // 显示错误信息
    showError(containerId, message) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="empty-tip">${message}</div>`;
        }
    }

    // 开始自动刷新任务
    startAutoRefresh() {
        setInterval(() => this.refreshTasks(), 30000); // 每30秒刷新一次
    }

    // 添加事件监听器初始化方法
    initTaskEvents() {
        document.addEventListener('click', (e) => {
            // 处理接受任务按钮点击
            if (e.target.closest('.accept-task')) {
                const taskId = e.target.closest('.accept-task').dataset.taskId;
                this.acceptTask(taskId);
            }
            // 处理放弃任务按钮点击
            if (e.target.closest('.abandon-task')) {
                const taskId = e.target.closest('.abandon-task').dataset.taskId;
                this.abandonTask(taskId);
            }
        });
    }

    // 获取状态颜色
    getStatusColor(task) {
        // 从配置文件中获取任务类型的颜色
        if (task.type && TASK_TYPE_MAP[task.type]) {
            return TASK_TYPE_MAP[task.type].color;
        }
        
        // 如果是玩家任务，使用玩家任务状态颜色
        if (task.player_id && PLAYER_TASK_STATUS_MAP[task.status]) {
            return PLAYER_TASK_STATUS_MAP[task.status].color;
        }
        
        // 如果是任务池中的任务，使用任务池状态颜色
        if (TASK_STATUS_MAP[task.status]) {
            return TASK_STATUS_MAP[task.status].color;
        }
        
        // 默认返回未定义任务的颜色
        return TASK_TYPE_MAP['UNDEFINED'].color;
    }

    // 获取状态文本
    getStatusText(type) {
        switch(type) {
            case 'NEW_TASK':
                return '新任务';
            case 'COMPLETE':
                return '已完成';
            case 'ALREADY_COMPLETED':
                return '重复完成';
            case 'CHECKING':
                return '审核中';
            case 'REJECTED':
                return '已驳回';
            case 'ERROR':
                return '错误';
            default:
                return '未知状态';
        }
    }


    // 初始化应用
    async initializeApplication() {
        // 等待 DOM 加载完成
        if (document.readyState !== 'complete') {
            await new Promise(resolve => window.addEventListener('load', resolve));
        }

        // 延迟一帧执行初始化，避免与 Layui 的初始化冲突
        await new Promise(resolve => requestAnimationFrame(resolve));

        // 初始化 Layui
        await new Promise(resolve => {
            layui.use(['element'], function() {
                const element = layui.element;
                element.render('tab');
                resolve();
            });
        });

        // 初始化观察器
        this.initializeObservers();
    }

    // 初始化观察器
    initializeObservers() {
        // 任务卡片观察器
        const taskObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        if (node.classList?.contains('task-card')) {
                            this.initializeTaskCard(node);
                        }
                        const taskCards = node.getElementsByClassName('task-card');
                        Array.from(taskCards).forEach(card => this.initializeTaskCard(card));
                    }
                });
            });
        });

        // 设置观察器配置
        const config = { childList: true, subtree: true };

        // 监听相关容器
        const containers = [
            document.getElementById('taskList'),
            document.querySelector('.active-tasks-swiper .swiper-wrapper'),
            document.querySelector('.tasks-list')
        ].filter(Boolean);

        containers.forEach(container => {
            taskObserver.observe(container, config);
            // 初始化已存在的任务卡片
            Array.from(container.getElementsByClassName('task-card'))
                .forEach(card => this.initializeTaskCard(card));
        });

        return taskObserver;
    }

    // 初始化任务卡片
    initializeTaskCard(taskCard) {
        const timeElement = taskCard.querySelector('.task-time');
        if (!timeElement) return;
        
        const endtime = parseInt(taskCard.dataset.endtime);
        if (!endtime) return;
        
        const timeUpdateInterval = setInterval(() => {
            const isActive = this.updateTaskTime(taskCard, endtime);
            if (!isActive) {
                clearInterval(timeUpdateInterval);
                taskCard.classList.add('expired');
            }
        }, 1000);
    }

    // 更新任务时间
    updateTaskTime(taskElement, endtime) {
        const now = Math.floor(Date.now() / 1000);
        const timeLeft = endtime - now;
        
        if (timeLeft <= 0) {
            taskElement.querySelector('.task-time').textContent = '已过期';
            return false;
        }
        
        const hours = Math.floor(timeLeft / 3600);
        const minutes = Math.floor((timeLeft % 3600) / 60);
        const seconds = timeLeft % 60;
        
        const timeString = `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        taskElement.querySelector('.task-time').textContent = `剩余时间：${timeString}`;
        return true;
    }

    // 创建进行中的任务卡片
    createActiveTaskCard(task) {
        const taskTypeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);
        const currentTime = Math.floor(Date.now()/1000);
        const progressPercent = Math.max(0, Math.min(100, 
            ((task.endtime - currentTime) / (task.endtime - task.starttime)) * 100
        ));
        
        const slide = document.createElement('div');
        slide.className = 'swiper-slide';
        
        slide.innerHTML = `
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
                        <button class="abandon-task" onclick="taskManager.abandonTask(${task.id})">
                            <i class="layui-icon layui-icon-close"></i>
                            放弃
                        </button>
                    </div>
                </div>
                <div class="task-progress-bar" style="width: ${progressPercent}%"></div>
            </div>
        `;
        
        return slide;
    }

    // 添加加载角色信息的方法
    async loadPlayerInfo() {
        try {
            const response = await fetch(`${SERVER}/api/player/${this.playerId}`);
            const result = await response.json();
            
            if (result.code === 0) {
                const playerData = result.data;
                
                // 更新角色信息显示
                document.getElementById('playerName').textContent = playerData.player_name;
                document.getElementById('playerPoints').textContent = playerData.experience;
                
                // 更新等级和经验条
                const levelElement = document.querySelector('.level');
                const expElement = document.querySelector('.exp');
                if (levelElement) {
                    levelElement.textContent = `${playerData.level}/100`;
                }
                if (expElement) {
                    expElement.textContent = `${playerData.experience}/99999`;
                }
                
                // 更新经验条
                const expBarInner = document.querySelector('.exp-bar-inner');
                if (expBarInner) {
                    const expPercentage = (playerData.experience / 99999) * 100;
                    expBarInner.style.width = `${Math.min(100, expPercentage)}%`;
                }
                
            } else {
                console.error('加载角色信息失败:', result.msg);
                document.getElementById('playerName').textContent = '加载失败';
                document.getElementById('playerPoints').textContent = '0';
            }
        } catch (error) {
            console.error('加载角色信息失败:', error);
            document.getElementById('playerName').textContent = '加载失败';
            document.getElementById('playerPoints').textContent = '0';
        }
    }

    // 添加任务列表 Swiper 初始化方法
    initTaskListSwiper() {
        if (this.taskListSwiper) {
            this.taskListSwiper.destroy(true, true);
        }

        this.taskListSwiper = new Swiper('.task-list-swiper', {
            direction: 'vertical',
            slidesPerView: 'auto',
            freeMode: true,
            mousewheel: true,
            scrollbar: {
                el: '.swiper-scrollbar',
                draggable: true,
                hide: false
            },
            height: 500, // 设置固定高度
            spaceBetween: 15
        });
    }

    // 初始化文字云
    initWordCloud() {
        const wordCloudChart = echarts.init(document.getElementById('wordCloudContainer'));
        
        // 模拟数据
        const testData = [
            // 头衔（较大字体，金色）
            { name: '尿不湿守护者', value: 100, textStyle: { color: '#ffd700', fontSize: 32 } },
            { name: '爬行先锋', value: 90, textStyle: { color: '#ffd700', fontSize: 28 } },
            
            // 荣誉（中等字体，银色）
            { name: '卫生纸摧毁达人', value: 80, textStyle: { color: '#c0c0c0' } },
            { name: '干饭小能手', value: 75, textStyle: { color: '#c0c0c0' } },
            { name: '玩具保护使者', value: 70, textStyle: { color: '#c0c0c0' } },
            
            // 个人标签（较小字体，青色系）
            { name: '热心干饭', value: 60, textStyle: { color: '#8aa2c1' } },
            { name: '推车出行', value: 55, textStyle: { color: '#8aa2c1' } },
            { name: '吃奶能手', value: 50, textStyle: { color: '#8aa2c1' } },
            { name: '植树达人', value: 45, textStyle: { color: '#8aa2c1' } },
            { name: '节水卫士', value: 40, textStyle: { color: '#8aa2c1' } },
            { name: '夜间嚎叫者', value: 35, textStyle: { color: '#8aa2c1' } },
            { name: '米粉爱好者', value: 30, textStyle: { color: '#8aa2c1' } }
        ];

        const option = {
            backgroundColor: 'transparent',
            tooltip: {
                show: true,
                formatter: function(params) {
                    return params.data.name;
                }
            },
            series: [{
                type: 'wordCloud',
                shape: 'circle',
                left: 'center',
                top: 'center',
                width: '100%',
                height: '100%',
                right: null,
                bottom: null,
                sizeRange: [16, 50],
                rotationRange: [-45, 45],
                rotationStep: 45,
                gridSize: 8,
                drawOutOfBound: false,
                layoutAnimation: true,
                textStyle: {
                    fontFamily: 'Microsoft YaHei',
                    fontWeight: 'bold',
                    color: function () {
                        return 'rgb(' + [
                            Math.round(Math.random() * 160) + 60,
                            Math.round(Math.random() * 160) + 60,
                            Math.round(Math.random() * 160) + 60
                        ].join(',') + ')';
                    }
                },
                emphasis: {
                    textStyle: {
                        shadowBlur: 10,
                        shadowColor: 'rgba(255, 196, 71, 0.5)'
                    }
                },
                data: testData
            }]
        };

        wordCloudChart.setOption(option);

        // 响应窗口大小变化
        window.addEventListener('resize', function() {
            wordCloudChart.resize();
        });

        // 将图表实例存储在全局变量中，以便后续更新
        window.wordCloudChart = wordCloudChart;
    }

    // 更新文字云数据
    async updateWordCloud() {
        try {
            // TODO: 替换为实际的API调用
            const response = await fetch('/api/player/tags');
            const data = await response.json();
            
            if (window.wordCloudChart && data.success) {
                window.wordCloudChart.setOption({
                    series: [{
                        data: data.tags
                    }]
                });
            }
        } catch (error) {
            console.error('更新文字云失败:', error);
        }
    }
}
// 导出 TaskManager 类
// export default TaskManager;