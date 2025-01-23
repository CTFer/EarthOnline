/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 14:41:57
 * @LastEditTime: 2025-01-21 20:22:18
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */

// 后端服务器地址配置
const SERVER = 'http://192.168.5.18:5000/';

// WebSocket连接
const socket = io('http://192.168.5.18:5000/');

// 在文件开头声明全局变量
let taskManager;

// 任务管理类
class TaskManager {
    constructor() {
        this.activeTasksSwiper = null;
        this.playerId = localStorage.getItem('playerId') || '1';
        this.loading = false;
        this.initWebSocket();
        this.loadPlayerInfo(); // 在构造函数中调用加载角色信息
    }

    // 初始化WebSocket
    initWebSocket() {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        socket.on('connect', () => {
            console.log('[WebSocket] Connected to server');
            statusDot.classList.add('connected');
            statusText.textContent = 'WebSocket已连接';
            
            // 连接成功后订阅任务更新，使用统一的房间格式
            const room = `user_${this.playerId}`;
            const subscribeData = { 
                player_id: this.playerId,
                room: room 
            };
            console.log('[WebSocket] Subscribing to tasks with data:', subscribeData);
            socket.emit('subscribe_tasks', subscribeData);
            
            // 显式加入房间
            socket.emit('join', { room: room });
        });

        socket.on('disconnect', () => {
            console.log('[WebSocket] Disconnected from server');
            statusDot.classList.remove('connected');
            statusText.textContent = 'WebSocket已断开';
        });

        socket.on('connect_error', (error) => {
            console.error('[WebSocket] Connection error:', error);
            statusDot.classList.remove('connected');
            statusText.textContent = 'WebSocket连接错误';
        });

        // NFC任务更新处理
        socket.on('nfc_task_update', (data) => {
            console.log('[WebSocket] Received NFC task update:', data);
            this.handleTaskUpdate(data);
        });

        // 任务状态更新处理
        socket.on('task_update', (data) => {
            console.log('[WebSocket] Received task status update:', data);
            this.handleTaskStatusUpdate(data);
        });
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

        // 统一使用showNotification显示消息
        this.showNotification(data);

        // 处理特殊逻辑
        switch(data.type) {
            case 'IDENTITY':
                this.playerId = data.player_id;
                localStorage.setItem('playerId', data.player_id);
                this.refreshTasks();
                break;
            case 'NEW_TASK':
            case 'COMPLETE':
                this.refreshTasks();
                break;
        }
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
        taskList.innerHTML = '<div class="loading-state">加载中...</div>';
        
        try {
            const response = await fetch(`${SERVER}/api/tasks/available/${this.playerId}`);
            const result = await response.json();
            
            if (result.code === 0) {
                const tasks = result.data;
                taskList.innerHTML = '';
                
                if (!tasks || tasks.length === 0) {
                    taskList.innerHTML = '<div class="empty-tip">暂无可用任务</div>';
                    return;
                }

                tasks.forEach(task => {
                    const taskCard = this.createTaskCard(task);
                    taskList.appendChild(taskCard);
                });
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
        const taskCard = document.createElement('div');
        taskCard.className = 'task-card';
        taskCard.dataset.endtime = task.endtime;
        
        const taskTypeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);
        
        taskCard.innerHTML = `
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
                        ${task.endtime ? gameUtils.formatDate(task.endtime) : '永久'}
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
                    <button class="accept-btn" onclick="taskManager.acceptTask(${task.id})">
                        <i class="layui-icon layui-icon-ok"></i>
                        接受
                    </button>
                </div>
            </div>
        `;
        
        return taskCard;
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
                        <div class="task-type-badge" style="background: ${typeInfo.color}20; color: ${typeInfo.color}">
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
    getStatusColor(type) {
        switch(type) {
            case 'NEW_TASK':
            case 'COMPLETE':
                return '#009688';
            case 'ALREADY_COMPLETED':
                return '#FFB800';
            case 'CHECKING':
                return '#1E9FFF';
            case 'REJECTED':
            case 'ERROR':
                return '#FF5722';
            default:
                return '#393D49';
        }
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
}

// 修改页面初始化代码
document.addEventListener('DOMContentLoaded', async () => {
    taskManager = new TaskManager();
    await taskManager.initializeApplication();
    taskManager.initTaskEvents();
    
    // 加载任务数据
    await Promise.all([
        taskManager.loadTasks(),
        taskManager.loadCurrentTasks()
    ]);
});

// 页面卸载前清理
window.addEventListener('beforeunload', () => {
    if (taskManager.activeTasksSwiper) {
        taskManager.activeTasksSwiper.destroy(true, true);
    }
});     