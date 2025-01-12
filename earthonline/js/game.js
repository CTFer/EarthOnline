/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 14:41:57
 * @LastEditTime: 2025-01-12 23:01:19
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */

// 后端服务器地址配置
const SERVER = 'http://192.168.1.12:5000/';

// WebSocket连接
const socket = io('http://192.168.1.12:5000/');

// 在文件开头声明全局变量
let taskManager;

// 任务管理类
class TaskManager {
    constructor() {
        this.activeTasksSwiper = null;
        this.userId = localStorage.getItem('userId') || '1';
        this.initWebSocket();
    }

    // 初始化WebSocket
    initWebSocket() {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        socket.on('connect', () => {
            statusDot.classList.add('connected');
            statusText.textContent = 'WebSocket已连接';
            
            // 连接成功后订阅任务更新
            socket.emit('subscribe_tasks', {
                user_id: this.userId
            });
        });

        socket.on('disconnect', () => {
            statusDot.classList.remove('connected');
            statusText.textContent = 'WebSocket已断开';
        });

        // 保留NFC任务更新处理
        socket.on('nfc_task_update', (data) => this.handleTaskUpdate(data));
        
        // 添加任务状态更新处理
        socket.on('task_update', (data) => this.handleTaskStatusUpdate(data));
    }

    // 处理NFC任务更新通知
    handleTaskUpdate(data) {
        const typeInfo = gameUtils.getTaskTypeInfo(data.task_type);
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
                            <h3>${data.task_name}</h3>
                            <small>${typeInfo.text}</small>
                        </div>
                    </div>
                    <div class="task-description">${data.task_description}</div>
                    <div class="task-time">打卡时间: ${data.timestamp}</div>
                </div>
            `
        });
        this.loadCurrentTasks();  // 更新任务列表
    }

    // 处理任务状态更新
    handleTaskStatusUpdate(data) {
        const container = document.querySelector('.swiper-wrapper');
        if (!container) return;

        // 根据任务状态更新UI
        if (data.status === 'COMPLETED' || data.status === 'ABANDONED') {
            // 移除已完成或放弃的任务
            const taskCard = container.querySelector(`[data-task-id="${data.id}"]`);
            if (taskCard) {
                taskCard.remove();
            }
        } else {
            // 更新任务信息
            const taskCard = container.querySelector(`[data-task-id="${data.id}"]`);
            if (taskCard) {
                const newCard = this.createCurrentTaskCard(data);
                taskCard.outerHTML = newCard;
            }
        }

        // 刷新Swiper
        this.initSwiper();
    }

    // 加载可用任务
    async loadTasks() {
        try {
            const taskList = document.getElementById('taskList');
            if (!taskList) {
                throw new Error('找不到taskList元素');
            }

            const userId = localStorage.getItem('userId') || '1';
            const response = await fetch(`${SERVER}/api/tasks/available/${userId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const availableData = await response.json();
            this.renderAvailableTasks(taskList, availableData);
        } catch (error) {
            console.error('加载任务失败:', error);
            this.showError('taskList', '加载任务失败');
        }
    }

    // 渲染可用任务列表
    renderAvailableTasks(container, tasks) {
        if (!tasks || !Array.isArray(tasks) || tasks.length === 0) {
            container.innerHTML = '<div class="empty-tip">暂无可用任务</div>';
            return;
        }

        container.innerHTML = tasks.map(task => this.createAvailableTaskCard(task)).join('');
    }

    // 创建可用任务卡片
    createAvailableTaskCard(task) {
        const typeInfo = TASK_TYPE_MAP[task.task_type] || TASK_TYPE_MAP['UNDEFINED'];
        const statusInfo = TASK_STATUS_MAP[task.task_status] || TASK_STATUS_MAP['UNAVAILABLE'];
        const statusClass = task.task_status.toLowerCase();
        
        return `
            <div class="task-card ${statusClass}">
                <div class="task-icon-container" style="color: ${typeInfo.color}">
                    <i class="layui-icon ${typeInfo.icon}"></i>
                </div>
                <div class="task-main-content">
                    <div class="task-header">
                        <span class="task-type" style="background: ${typeInfo.color}20; color: ${typeInfo.color}">
                            ${typeInfo.text}
                        </span>
                        <span class="task-status" style="background: ${statusInfo.color}20; color: ${statusInfo.color}">
                            <i class="layui-icon ${statusInfo.icon}"></i>
                            ${statusInfo.text}
                        </span>
                    </div>
                    <div class="task-content">
                        <h3>${task.name}</h3>
                        <p>${task.description}</p>
                    </div>
                    <div class="task-footer">
                        <div class="task-rewards">
                            <span class="points">+${task.points}分</span>
                            ${task.stamina_cost ? `<span class="stamina">-${task.stamina_cost}体力</span>` : ''}
                        </div>
                        <button class="layui-btn layui-btn-normal layui-btn-sm accept-task" 
                                data-task-id="${task.id}"
                                ${task.task_status !== 'AVAILABLE' ? 'disabled' : ''}>
                            <i class="layui-icon layui-icon-ok"></i>
                            接受任务
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // 加载当前任务（仅在页面首次加载时调用）
    async loadCurrentTasks() {
        try {
            const response = await fetch(`${SERVER}/api/tasks/current/${this.userId}`);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const currentTasks = await response.json();
            this.renderCurrentTasks(currentTasks);
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
            <div class="swiper-slide">
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
        const progressPercent = Math.max(0, Math.min(100, 
            ((task.endtime - Date.now()/1000) / (task.endtime - task.starttime)) * 100
        ));

        return `
            <div class="task-card current" data-task-id="${task.id}">
                <div class="task-progress-bar" style="width: ${progressPercent}%"></div>
                <div class="task-content-wrapper">
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
                    <div class="task-body">
                        <h3 class="task-title">${task.name}</h3>
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
            slidesPerView: 1,
            spaceBetween: 20,
            centeredSlides: true,
            loop: slideCount > 1, // 只有多于一个slide时启用循环
            watchOverflow: true, // 当只有一个slide时，禁用所有效果
            loopAdditionalSlides: 1,
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
            navigation: {
                nextEl: '.swiper-button-next',
                prevEl: '.swiper-button-prev',
                hideOnClick: false,
                disabledClass: 'swiper-button-disabled',
            },
            autoplay: slideCount > 1 ? {
                delay: 5000,
                disableOnInteraction: false,
                pauseOnMouseEnter: true
            } : false,
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
            console.log('Accepting task with user_id:', this.userId); // 调试日志
            
            const response = await fetch(`${SERVER}/api/tasks/${taskId}/accept`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    user_id: this.userId
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Task accepted:', data); // 调试日志
                layer.msg('成功接受任务', {icon: 1});
                await this.refreshTasks();
            } else {
                const data = await response.json();
                throw new Error(data.error || '接受任务失败');
            }
        } catch (error) {
            console.error('接受任务失败:', error);
            layer.msg('接受任务失败', {icon: 2});
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
                        user_id: this.userId
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
                    user_id: this.userId
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
        await Promise.all([
            this.loadTasks(),
        ]);
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
}

// 修改页面初始化代码
document.addEventListener('DOMContentLoaded', () => {
    taskManager = new TaskManager();
    taskManager.initTaskEvents();
    taskManager.loadTasks();
    taskManager.loadCurrentTasks();
});

// 页面卸载前清理
window.addEventListener('beforeunload', () => {
    if (taskManager.activeTasksSwiper) {
        taskManager.activeTasksSwiper.destroy(true, true);
    }
});     