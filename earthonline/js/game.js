/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 14:41:57
 * @LastEditTime: 2025-01-12 16:00:28
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */

// 后端服务器地址配置
const SERVER = 'http://192.168.1.12:5000/';

// WebSocket连接
const socket = io('http://192.168.1.12:5000/');

// 任务管理类
class TaskManager {
    constructor() {
        this.activeTasksSwiper = null;
        this.initWebSocket();
    }

    // 初始化WebSocket
    initWebSocket() {
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.querySelector('.status-text');

        socket.on('connect', () => {
            statusDot.classList.add('connected');
            statusText.textContent = 'WebSocket已连接';
        });

        socket.on('disconnect', () => {
            statusDot.classList.remove('connected');
            statusText.textContent = 'WebSocket已断开';
        });

        socket.on('nfc_task_update', (data) => this.handleTaskUpdate(data));
    }

    // 处理任务更新通知
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
        this.loadTasks();
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
        const typeInfo = gameUtils.getTaskTypeInfo(task.task_type);
        return `
            <div class="task-card">
                <div class="task-icon-container" style="color: ${typeInfo.color}">
                    <i class="layui-icon ${typeInfo.icon}"></i>
                </div>
                <div class="task-main-content">
                    <div class="task-header">
                        <span class="task-type" style="background: ${typeInfo.color}20; color: ${typeInfo.color}">
                            ${typeInfo.text}
                        </span>
                    </div>
                    <div class="task-content">
                        <h3>${task.name}</h3>
                        <p>${task.description}</p>
                    </div>
                    <div class="task-footer">
                        <button class="layui-btn layui-btn-normal layui-btn-sm" onclick="taskManager.acceptTask(${task.id})">
                            <i class="layui-icon layui-icon-ok"></i>
                            接受任务
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    // 加载进行中的任务
    async loadCurrentTasks() {
        try {
            const userId = localStorage.getItem('userId') || '1';
            const response = await fetch(`${SERVER}/api/tasks/current/${userId}`);
            
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

    // 渲染进行中的任务
    renderCurrentTasks(tasks) {
        const container = document.querySelector('.swiper-wrapper');
        if (!container) return;

        if (!tasks || !Array.isArray(tasks) || tasks.length === 0) {
            container.innerHTML = '<div class="swiper-slide"><div class="empty-tip">暂无进行中的任务</div></div>';
            return;
        }

        // 每页显示3个任务
        const taskGroups = [];
        for (let i = 0; i < tasks.length; i += 3) {
            taskGroups.push(tasks.slice(i, Math.min(i + 3, tasks.length)));
        }

        container.innerHTML = taskGroups.map(group => `
            <div class="swiper-slide">
                <div class="active-tasks-row">
                    ${group.map(task => this.createCurrentTaskCard(task)).join('')}
                </div>
            </div>
        `).join('');

        this.initSwiper();
    }

    // 创建进行中的任务卡片
    createCurrentTaskCard(task) {
        const typeInfo = gameUtils.getTaskTypeInfo(task.task_type);
        const endTime = gameUtils.calculateTaskEndTime(task);
        const timeRemaining = endTime - new Date();
        const timeDisplay = gameUtils.formatTimeRemaining(timeRemaining);

        return `
            <div class="task-card">
                <div class="task-icon-container" style="color: ${typeInfo.color}">
                    <i class="layui-icon ${typeInfo.icon}"></i>
                </div>
                <div class="task-main-content">
                    <div class="task-header">
                        <span class="task-type" style="background: ${typeInfo.color}20; color: ${typeInfo.color}">
                            ${typeInfo.text}
                        </span>
                        <span class="task-time">剩余 ${timeDisplay}</span>
                    </div>
                    <div class="task-content">
                        <h3>${task.name}</h3>
                        <p>${task.description}</p>
                    </div>
                    <div class="task-footer">
                        <span class="task-reward">
                            <i class="layui-icon layui-icon-diamond"></i>
                            奖励: ${task.points || 0}点数
                        </span>
                        <button class="layui-btn layui-btn-danger layui-btn-sm" onclick="taskManager.abandonTask(${task.id})">
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

        this.activeTasksSwiper = new Swiper('.active-tasks-swiper', {
            slidesPerView: 1,
            spaceBetween: 30,
            mousewheel: true,
            pagination: {
                el: '.swiper-pagination',
                clickable: true
            },
            autoplay: {
                delay: 5000,
                disableOnInteraction: false
            }
        });
    }

    // 接受任务
    async acceptTask(taskId) {
        try {
            const response = await fetch(`${SERVER}/api/tasks/${taskId}/accept`, {
                method: 'POST'
            });
            
            if (response.ok) {
                layer.msg('成功接受任务', {icon: 1});
                await this.refreshTasks();
            } else {
                throw new Error('接受任务失败');
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
                    method: 'POST'
                });
                
                if (response.ok) {
                    layer.msg('已放弃任务', {icon: 1});
                    await this.refreshTasks();
                } else {
                    throw new Error('放弃任务失败');
                }
            } catch (error) {
                console.error('放弃任务失败:', error);
                layer.msg('放弃任务失败', {icon: 2});
            }
        });
    }

    // 刷新所有任务
    async refreshTasks() {
        await Promise.all([
            this.loadTasks(),
            this.loadCurrentTasks()
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
}

// 创建任务管理器实例
const taskManager = new TaskManager();

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    taskManager.loadTasks();
    taskManager.loadCurrentTasks();
    taskManager.startAutoRefresh();
});

// 页面卸载前清理
window.addEventListener('beforeunload', () => {
    if (taskManager.activeTasksSwiper) {
        taskManager.activeTasksSwiper.destroy(true, true);
    }
});     