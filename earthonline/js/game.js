/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 14:41:57
 * @LastEditTime: 2025-01-21 15:47:20
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
            let tasks = await response.json();
            
            // 如果没有任务数据，添加测试任务
            if (!tasks || !tasks.length) {
                tasks = [{
                    id: 'test-1',
                    name: '每日锻炼',
                    description: '完成30分钟的体能训练，提升身体素质。每天坚持锻炼不仅能增强体魄，还能获得额外的经验奖励。',
                    task_type: 'DAILY',
                    points: 500,
                    stamina_cost: 30,
                    endtime: Math.floor(Date.now() / 1000) + 86400 // 24小时后过期
                }, {
                    id: 'test-2',
                    name: '拯救村庄',
                    description: '解决村庄面临的危机，帮助村民重建家园。这是一个艰巨的任务，需要智慧和勇气的考验。完成后将获得丰厚奖励和村民的感激。',
                    task_type: 'MAIN',
                    points: 2000,
                    stamina_cost: 100,
                    endtime: Math.floor(Date.now() / 1000) + 604800 // 7天后过期
                }];
            }

            const taskList = document.getElementById('taskList');
            if (!taskList) {
                console.error('Task list container not found');
                return;
            }

            taskList.innerHTML = '';
            tasks.forEach(task => {
                const taskCard = this.createTaskCard(task);
                taskList.appendChild(taskCard);
            });

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
            let currentTasks = await response.json();

            // 如果没有进行中的任务，添加测试任务
            if (!currentTasks || !currentTasks.length) {
                currentTasks = [{
                    id: 'test-3',
                    name: '探索神秘遗迹',
                    description: '在荒野中寻找并调查一处古代遗迹，记录发现的文物和历史痕迹。这个任务需要细心观察和耐心探索，每一个细节都可能藏有重要线索。',
                    task_type: 'EXPLORE',
                    points: 1000,
                    points_earned: 450,
                    stamina_cost: 50,
                    endtime: Math.floor(Date.now() / 1000) + 7200, // 2小时后过期
                    starttime: Math.floor(Date.now() / 1000) - 3600, // 1小时前开始
                    progress: 45
                }];
            }

            const container = document.querySelector('.active-tasks-swiper .swiper-wrapper');
            if (!container) {
                console.error('Active tasks container not found');
                return;
            }

            container.innerHTML = '';
            currentTasks.forEach(task => {
                const slide = document.createElement('div');
                slide.className = 'swiper-slide';
                slide.innerHTML = this.createCurrentTaskCard(task);
                container.appendChild(slide);
            });

            // 重新初始化 Swiper
            this.initSwiper();

        } catch (error) {
            console.error('加载进行中任务失败:', error);
            this.showError('active-tasks-wrapper', '加载任务失败');
        }
    }

    // 渲染进行中的任务列表
    renderCurrentTasks(tasks) {
        const container = document.querySelector('.swiper-wrapper');
        if (!container) return;

        if (!tasks || !Array.isArray(tasks) || tasks.length === 0) {
            container.innerHTML = `
                <div class="swiper-slide">
                    <div class="empty-tip">暂无进行中的任务</div>
                </div>
            `;
            this.initSwiper();
            return;
        }

        // 每个slide最多显示2个任务
        const taskGroups = [];
        for (let i = 0; i < tasks.length; i += 2) {
            taskGroups.push(tasks.slice(i, Math.min(i + 2, tasks.length)));
        }

        // 确保至少有两个slide以启用循环
        let slidesHtml = taskGroups.map(group => `
            <div class="swiper-slide task-panel">
                <div class="active-tasks-row">
                    ${group.map(task => this.createCurrentTaskCard(task)).join('')}
                </div>
            </div>
        `).join('');

        // 如果只有一个slide，复制一份以启用循环
        if (taskGroups.length === 1) {
            slidesHtml += slidesHtml;
        }

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

        // 获取实际的slide数量
        const slideCount = swiperContainer.querySelectorAll('.swiper-slide').length;

        this.activeTasksSwiper = new Swiper('.active-tasks-swiper', {
            slidesPerView: 2,
            spaceBetween: 10,
            loop: slideCount > 1, // 只有多于一个slide时启用循环
            watchOverflow: true, // 当只有一个slide时，禁用所有效果
            observer: true, // 监视DOM变化
            observeParents: true,
            mousewheel: {
                forceToAxis: true,
                sensitivity: 1
            },
            pagination: {
                el: '.swiper-pagination',
                clickable: true,
                dynamicBullets: true,
                renderBullet: function (index, className) {
                    return `<span class="${className}"></span>`;
                },
            },

            // autoplay: slideCount > 1 ? {
            //     delay: 5000,
            //     disableOnInteraction: false,
            //     pauseOnMouseEnter: true
            // } : false,
            on: {
                init: function() {
                    // 更新分页器状态
                    this.pagination.render();
                    this.pagination.update();
                },
                slideChange: function() {
                    // 确保分页器同步
                    this.pagination.render();
                    this.pagination.update();
                }
            }
        });

        // 确保分页器和导航按钮的显示状态正确
        if (slideCount <= 1) {
            const pagination = swiperContainer.querySelector('.swiper-pagination');
            const navigation = swiperContainer.querySelectorAll('.swiper-button-next, .swiper-button-prev');
            
            if (pagination) pagination.style.display = 'none';
            navigation.forEach(nav => nav.style.display = 'none');
        }
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
            
            const data = await response.json();
            console.log('API响应状态:', response.status);
            console.log('API响应数据:', data);

            if (response.ok) {
                layer.msg(`成功接受任务: ${data.task_name}`, {icon: 1});
                await this.refreshTasks();
            } else {
                // 根据错误代码显示不同的提示信息
                let errorMsg = data.error;
                let icon = 2;
                
                switch(data.code) {
                    case 'PREREQUISITE_NOT_STARTED':
                    case 'PREREQUISITE_NOT_COMPLETED':
                        icon = 0; // 使用信息图标
                        break;
                    case 'TASK_ALREADY_ACCEPTED':
                        icon = 4; // 使用锁定图标
                        break;
                    default:
                        errorMsg = '接受任务失败: ' + (data.error || '未知错误');
                }
                
                layer.msg(errorMsg, {icon: icon});
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
                
                if (response.ok) {
                    const data = await response.json();
                    console.log('Task abandoned:', data); // 调试日志
                    layer.msg('已放弃任务', {icon: 1});
                    await this.refreshTasks();
                } else {
                    const data = await response.json();
                    throw new Error(data.error || '放弃任务失败');
                }
            } catch (error) {
                console.error('放弃任务失败:', error);
                layer.msg('放弃任务失败', {icon: 2});
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
            
            if (response.ok) {
                const data = await response.json();
                console.log('Task completed:', data); // 调试日志
                layer.msg(`任务完成！获得 ${data.rewards || 0} 奖励`, {icon: 1});
                await this.refreshTasks();
            } else {
                const data = await response.json();
                throw new Error(data.error || '完成任务失败');
            }
        } catch (error) {
            console.error('完成任务失败:', error);
            layer.msg('完成任务失败', {icon: 2});
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

    // 插入测试用任务卡片
    insertTestTasks() {
        // 插入可用任务测试卡片
        const taskList = document.getElementById('taskList');
        if (taskList) {
            const dailyTask = this.createTaskCard({
                id: 'test-1',
                name: '每日锻炼',
                description: '完成30分钟的体能训练，提升身体素质。',
                task_type: 'DAILY',
                points: 500,
                stamina_cost: 30,
                endtime: 1735686000
            });
            
            const mainTask = this.createTaskCard({
                id: 'test-2',
                name: '拯救村庄',
                description: '解决村庄面临的危机，帮助村民重建家园。',
                task_type: 'MAIN',
                points: 2000,
                stamina_cost: 100,
                endtime: 1735686000
            });

            taskList.insertBefore(mainTask, taskList.firstChild);
            taskList.insertBefore(dailyTask, taskList.firstChild);
        }

        // 插入进行中任务测试卡片
        const swiperWrapper = document.querySelector('.active-tasks-swiper .swiper-wrapper');
        if (swiperWrapper) {
            const slide = document.createElement('div');
            slide.className = 'swiper-slide';
            slide.innerHTML = this.createCurrentTaskCard({
                id: 'test-3',
                name: '探索神秘遗迹',
                description: '在荒野中寻找并调查一处古代遗迹，记录发现的文物和历史痕迹。',
                task_type: 'EXPLORE',
                points: 1000,
                points_earned: 450,
                stamina_cost: 50,
                endtime: 1735686000,
                starttime: 1735686000 - 3600,
                progress: 45
            });
            swiperWrapper.insertBefore(slide, swiperWrapper.firstChild);
            
            // 重新初始化 Swiper
            this.initSwiper();
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