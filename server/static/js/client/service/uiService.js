/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:39
 * @LastEditTime: 2025-02-17 14:50:30
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */
import Logger from '../../utils/logger.js';

class UIService {
    constructor(eventBus, store, templateService) {
        this.eventBus = eventBus;
        this.store = store;
        this.templateService = templateService;
        this.observers = new Map();
        Logger.info('UIService', '初始化UI服务');
    }

    setupDOMObserver() {
        Logger.debug('UIService', '设置DOM观察器');
        // DOM观察器逻辑
    }

    updateTaskList(tasks) {
        Logger.debug('UIService', '更新任务列表UI');
        // 任务列表更新逻辑
    }

    /**
     * 显示任务详情
     * @param {string} taskId 任务ID
     */
    showTaskDetails(taskId) {
        Logger.info("UIService", "显示任务详情:", taskId);
        
        try {
            const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);
            if (!taskCard) {
                Logger.error("UIService", "未找到任务卡片:", taskId);
                return;
            }
            
            // 从store中获取完整的任务数据
            const tasks = this.store.state.taskList || [];
            const task = tasks.find(t => t.id.toString() === taskId.toString());
            
            if (!task) {
                Logger.error("UIService", "未找到任务数据:", taskId);
                return;
            }
            
            layer.open({
                type: 1,
                title: false,
                content: this.templateService.createTaskDetailTemplate(task),
                area: ['500px', '400px'],
                shadeClose: true,
                success: (layero) => {
                    // 绑定接受任务按钮事件
                    const acceptBtn = layero.find('.accept-task');
                    if (acceptBtn.length) {
                        acceptBtn.on('click', () => {
                            this.eventBus.emit('task:accept', taskId);
                            layer.closeAll();
                        });
                    }
                }
            });
            
            Logger.debug("UIService", "任务详情显示完成");
        } catch (error) {
            Logger.error("UIService", "显示任务详情失败:", error);
            this.showNotification({
                type: "ERROR",
                message: "显示任务详情失败"
            });
        }
    }

    /**
     * 显示通知消息
     * @param {Object|string} data 通知数据或消息文本
     * @param {string} type 通知类型
     */
    showNotification(data, type = 'info') {
        Logger.debug('UIService', '显示通知:', data);
        
        try {
            let message, icon;
            
            // 处理不同的输入格式
            if (typeof data === 'string') {
                message = data;
            } else {
                message = data.message || '未知消息';
                type = data.type?.toLowerCase() || type;
            }

            // 根据类型设置图标
            switch (type.toUpperCase()) {
                case 'SUCCESS':
                case 'COMPLETE':
                    icon = 1;
                    break;
                case 'ERROR':
                case 'REJECT':
                    icon = 2;
                    break;
                case 'WARNING':
                case 'CHECKING':
                    icon = 3;
                    break;
                default:
                    icon = -1;
            }

            // 使用 layer 显示通知
            layer.msg(message, {
                icon: icon,
                offset: 't',
                anim: 6
            });

            // 发送通知事件
            this.eventBus.emit('ui:notification', { message, type });
        } catch (error) {
            Logger.error('UIService', '显示通知失败:', error);
            // 使用原生alert作为后备方案
            alert(typeof data === 'string' ? data : data.message || '发生错误');
        }
    }

    /**
     * 渲染奖励详情
     * @private
     */
    _renderRewardsDetail(rewards) {
        let html = '';
        
        if (rewards.exp > 0) {
            html += `
                <div class="reward-item">
                    <i class="layui-icon layui-icon-star"></i>
                    <span>经验值 +${rewards.exp}</span>
                </div>`;
        }
        
        if (rewards.points > 0) {
            html += `
                <div class="reward-item">
                    <i class="layui-icon layui-icon-diamond"></i>
                    <span>积分 +${rewards.points}</span>
                </div>`;
        }
        
        if (rewards.cards.length > 0) {
            rewards.cards.forEach(card => {
                html += `
                    <div class="reward-item">
                        <i class="layui-icon layui-icon-template"></i>
                        <span>${card.name} x${card.number}</span>
                    </div>`;
            });
        }
        
        if (rewards.medals.length > 0) {
            rewards.medals.forEach(medal => {
                html += `
                    <div class="reward-item">
                        <i class="layui-icon layui-icon-medal"></i>
                        <span>${medal.name}</span>
                    </div>`;
            });
        }
        
        return html || '<div class="no-rewards">无奖励</div>';
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
     * 显示成功消息
     * @param {string} message 消息内容
     */
    showSuccessMessage(message) {
        layer.msg(message, { icon: 1 });
    }

    /**
     * 显示错误消息
     * @param {string} message 消息内容
     */
    showErrorMessage(message) {
        layer.msg(message, { icon: 2 });
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
                const taskCards = tasks.map(task => {
                    try {
                        return this.templateService.createTaskCard(task);
                    } catch (err) {
                        Logger.error("UIService", "渲染单个任务卡片失败:", err);
                        return null;
                    }
                }).filter(Boolean);

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
                const taskCards = tasks.map(task => {
                    try {
                        return this.templateService.createActiveTaskCard(task);
                    } catch (err) {
                        Logger.error("UIService", "渲染单个当前任务卡片失败:", err);
                        return null;
                    }
                }).filter(Boolean);

                container.innerHTML = taskCards.map(card => `
                    <div class="swiper-slide">
                        <div class="task-panel">
                            ${card}
                        </div>
                    </div>
                `).join("");
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
                    const slideElement = taskCard.closest('.swiper-slide');
                    if (slideElement) {
                        // 添加淡出动画
                        slideElement.style.transition = 'opacity 0.5s';
                        slideElement.style.opacity = '0';
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
                    taskCard.classList.add('checking');
                    const statusElement = taskCard.querySelector('.task-status');
                    if (statusElement) {
                        statusElement.textContent = '审核中';
                        statusElement.classList.add('checking');
                    }
                    break;

                case "REJECTED":
                    Logger.debug("UIService", `更新任务状态为已驳回: ${data.id}`);
                    taskCard.classList.add('rejected');
                    const rejectStatusElement = taskCard.querySelector('.task-status');
                    if (rejectStatusElement) {
                        rejectStatusElement.textContent = '已驳回';
                        rejectStatusElement.classList.add('rejected');
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

            // 触发任务状态更新事件
            this.eventBus.emit('ui:task:status:updated', data);
            
            Logger.info("UIService", "任务状态UI更新完成");
        } catch (error) {
            Logger.error("UIService", "更新任务状态UI失败:", error);
            this.showNotification({
                type: "ERROR",
                message: "更新任务状态显示失败"
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
                progressBar.setAttribute('aria-valuenow', progress);
                
                // 更新进度文本
                const progressText = progressBar.querySelector('.progress-text');
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
                timeElement.classList.add('expired');
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
        Logger.info("UIService", "初始化任务相关事件监听");
        
        try {
            document.addEventListener("click", (e) => {
                // 处理任务卡片点击
                const taskCard = e.target.closest(".task-card");
                if (taskCard && !e.target.closest("button")) {
                    const taskId = taskCard.dataset.taskId;
                    if (taskId) {
                        this.showTaskDetails(taskId);
                    }
                }
                
                // 处理接受任务按钮点击
                if (e.target.closest(".accept-btn")) {
                    const taskId = e.target.closest(".task-card").dataset.taskId;
                    if (taskId) {
                        this.eventBus.emit('task:accept', taskId);
                    }
                }
                
                // 处理放弃任务按钮点击
                if (e.target.closest(".abandon-task")) {
                    const taskId = e.target.closest(".task-card").dataset.taskId;
                    if (taskId) {
                        this.eventBus.emit('task:abandon', taskId);
                    }
                }
            });
            
            Logger.info("UIService", "任务事件监听初始化完成");
        } catch (error) {
            Logger.error("UIService", "初始化任务事件监听失败:", error);
            throw error;
        }
    }

    // ... 其他UI相关方法
}

export default UIService; 