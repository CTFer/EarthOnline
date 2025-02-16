import Logger from '../../utils/logger.js';
import { gameUtils } from '../../utils/utils.js';

class TaskService {
    constructor(apiClient, eventBus, store, playerService, templateService) {
        this.api = apiClient;
        this.eventBus = eventBus;
        this.store = store;
        this.playerService = playerService;
        this.activeTasksSwiper = null;
        this.taskListSwiper = null;
        this.loading = false;
        this.templateService = templateService;
        Logger.info('TaskService', '初始化任务服务');
        
        // 订阅相关事件
        this.eventBus.on('task:complete', this.handleTaskComplete.bind(this));
        this.eventBus.on('task:new', this.handleNewTask.bind(this));
        this.eventBus.on('task:status:update', this.handleTaskStatusUpdate.bind(this));
    }

    async loadTasks() {
        if (this.loading) return;
        
        Logger.info('TaskService', '开始加载任务');
        this.loading = true;
        try {
            const result = await this.api.getTaskList(this.playerService.getPlayerId());
            Logger.debug('TaskService', '任务列表 API 数据:', result);
            
            if (result.code === 0) {
                this.store.setState({ taskList: result.data });
                Logger.debug('TaskService', 'Emitting tasks:loaded event with data:', result.data);
                this.eventBus.emit('tasks:loaded', result.data);
                return result.data;
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('TaskService', '加载任务列表失败:', error);
            this.eventBus.emit('tasks:error', error);
            throw error;
        } finally {
            this.loading = false;
        }
    }

    async loadCurrentTasks() {
        try {
            Logger.info('TaskService', '开始加载当前任务');
            const currentTasks = await this.getCurrentTasks();
            
            if (currentTasks) {
                Logger.debug('TaskService', '当前任务加载完成:', currentTasks);
                this.store.setState({ currentTasks });
                this.eventBus.emit('currentTasks:loaded', currentTasks);
                return currentTasks;
            }
        } catch (error) {
            Logger.error('TaskService', '加载当前任务失败:', error);
            this.eventBus.emit('tasks:error', error);
            throw error;
        }
    }

    async getCurrentTasks() {
        try {
            Logger.info('TaskService', 'Loading current tasks for player:', this.playerService.getPlayerId());
            const result = await this.api.getCurrentTasks(this.playerService.getPlayerId());
            
            if (result.code === 0) {
                let currentTasks = result.data;
                
                // 如果没有进行中的任务，添加测试任务（保持原有逻辑）
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

                Logger.debug('TaskService', '获取到当前任务:', currentTasks);
                return currentTasks;
            } else {
                throw new Error(result.msg || '获取当前任务失败');
            }
        } catch (error) {
            Logger.error('TaskService', 'Get current tasks failed:', error);
            throw error;
        }
    }

    async acceptTask(taskId) {
        const playerId = this.playerService.getPlayerId();
        Logger.info('TaskService', '接受任务:', taskId, '玩家ID:', playerId);
        try {
            if (!this.api) {
                throw new Error('API client not initialized');
            }

            const result = await this.api.acceptTask(taskId, playerId);
            Logger.debug('TaskService', '接受任务响应:', result);
            
            if (result.code === 0) {
                Logger.info('TaskService', '任务接受成功:', result.data);
                this.eventBus.emit('task:accepted', result.data);
                // 重新加载当前任务列表
                await this.loadCurrentTasks();
                return result;
            } else {
                throw new Error(result.msg || '接受任务失败');
            }
        } catch (error) {
            Logger.error('TaskService', '接受任务失败:', error);
            this.eventBus.emit('task:error', error);
            throw error;
        }
    }

    async handleTaskComplete(taskId) {
        Logger.info('TaskService', '处理任务完成:', taskId);
        try {
            const result = await this.api.completeTask(taskId);
            if (result.code === 0) {
                this.eventBus.emit('task:completed', result.data);
                await this.loadTasks();
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('TaskService', '任务完成失败:', error);
            this.eventBus.emit('task:error', error);
        }
    }

    async handleNewTask(taskData) {
        Logger.info('TaskService', '处理新任务:', taskData);
        try {
            await this.loadTasks();
            this.eventBus.emit('task:added', taskData);
        } catch (error) {
            Logger.error('TaskService', '处理新任务失败:', error);
            this.eventBus.emit('task:error', error);
        }
    }

    initTaskSwipers() {
        Logger.info('TaskService', 'Initializing task swipers');
        this.initActiveTasksSwiper();
        
        const taskListContainer = document.querySelector('.task-list-swiper');
        if (!taskListContainer) {
            Logger.error('TaskService', 'Task list container not found');
            return;
        }
        
        const taskCards = taskListContainer.querySelectorAll('.swiper-slide');
        Logger.debug('TaskService', 'Found', taskCards.length, 'task cards');
        
        this.initTaskListSwiper();
    }

    initActiveTasksSwiper() {
        const container = document.querySelector('.active-tasks-swiper');
        if (!container) return;

        this.activeTasksSwiper = new Swiper('.active-tasks-swiper', {
            slidesPerView: 'auto',
            spaceBetween: 20,
            pagination: {
                el: '.swiper-pagination',
                clickable: true
            }
        });
        Logger.info('TaskService', 'Active tasks swiper initialized');
    }

    initTaskListSwiper() {
        const container = document.querySelector('.task-list-swiper');
        if (!container) return;

        this.taskListSwiper = new Swiper('.task-list-swiper', {
            direction: 'vertical',
            slidesPerView: 'auto',
            freeMode: true,
            scrollbar: {
                el: '.swiper-scrollbar',
            },
            mousewheel: true,
        });
        Logger.info('TaskService', 'Task list swiper initialized');
    }

    destroySwipers() {
        Logger.info('TaskService', 'Destroying swipers');
        if (this.activeTasksSwiper) {
            this.activeTasksSwiper.destroy(true, true);
            this.activeTasksSwiper = null;
        }
        if (this.taskListSwiper) {
            this.taskListSwiper.destroy(true, true);
            this.taskListSwiper = null;
        }
    }

    // 创建活动任务卡片DOM
    createActiveTaskCard(task) {
        Logger.debug('TaskService', '创建活动任务卡片:', task);
        const taskTypeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);
        const currentTime = Math.floor(Date.now()/1000);
        const progressPercent = Math.max(0, Math.min(100, 
            ((task.endtime - currentTime) / (task.endtime - task.starttime)) * 100
        ));

        const slide = document.createElement('div');
        slide.className = 'swiper-slide';
        slide.innerHTML = this.templateService.getActiveTaskTemplate(task, taskTypeInfo, progressPercent);
        return slide;
    }

    // 创建可用任务卡片DOM
    createAvailableTaskCard(task) {
        Logger.debug('TaskService', '创建可用任务卡片:', task);
        const taskTypeInfo = gameUtils.getTaskTypeInfo(task.task_type, task.icon);
        const rewards = this.templateService.parseTaskRewards(task.task_rewards);
        return this.templateService.getAvailableTaskTemplate(task, taskTypeInfo, rewards);
    }

    // 处理任务状态更新
    handleTaskStatusUpdate(data) {
        Logger.info("TaskService", "处理任务状态更新:", data);

        try {
            const container = document.querySelector(".active-tasks-swiper .swiper-wrapper");
            if (!container) {
                Logger.warn("TaskService", "任务容器未找到");
                return;
            }

            // 根据任务状态更新UI
            if (data.status === "COMPLETED" || data.status === "ABANDONED") {
                Logger.info("TaskService", `移除任务 ${data.id} (${data.status})`);
                const taskCard = container.querySelector(`[data-task-id="${data.id}"]`);
                if (taskCard) {
                    const slideElement = taskCard.closest('.swiper-slide');
                    if (slideElement) {
                        slideElement.remove();
                    }
                }
            } else {
                Logger.info("TaskService", `更新任务 ${data.id} 状态为 ${data.status}`);
                const taskCard = container.querySelector(`[data-task-id="${data.id}"]`);
                if (taskCard) {
                    const slideElement = taskCard.closest('.swiper-slide');
                    if (slideElement) {
                        const newSlide = this.createActiveTaskCard(data);
                        slideElement.replaceWith(newSlide);
                    }
                }
            }

            // 刷新Swiper
            this.initTaskSwipers();
            
            // 发送任务状态更新完成事件
            this.eventBus.emit('task:status:updated', data);
            
        } catch (error) {
            Logger.error("TaskService", "处理任务状态更新错误:", error);
            this.eventBus.emit('task:error', error);
        }
    }

    updatePlayerId(newId) {
        Logger.info('TaskService', '更新玩家ID:', newId);
        // 如果需要清理或重置任何与玩家相关的数据
        this.store.clearTaskCache();
    }

    async updateTaskStatus(taskData) {
        Logger.debug('TaskService', '更新任务状态:', taskData);
        
        try {
            // 更新本地任务状态
            const currentTasks = this.store.state.currentTasks || [];
            const taskIndex = currentTasks.findIndex(t => t.id === taskData.id);
            
            if (taskIndex !== -1) {
                currentTasks[taskIndex] = {
                    ...currentTasks[taskIndex],
                    ...taskData
                };
                
                // 更新 store
                this.store.setState({
                    currentTasks: currentTasks
                });
                
                // 发送任务更新事件
                this.eventBus.emit('task:updated', taskData);
            }
            
            Logger.debug('TaskService', '任务状态更新完成');
        } catch (error) {
            Logger.error('TaskService', '更新任务状态失败:', error);
            throw error;
        }
    }
}

export default TaskService;