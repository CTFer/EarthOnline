import Logger from '../../utils/logger.js';
import { gameUtils } from '../../utils/utils.js';
import { 
    TASK_EVENTS,
    UI_EVENTS,
    AUDIO_EVENTS 
} from "../config/events.js";

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
        this.processingTasks = new Set(); // 添加任务处理状态集合
        Logger.info('TaskService', '初始化任务服务');
        
        // 初始化事件监听
        this.initEvents();
    }

    /**
     * 初始化事件监听
     * @private
     */
    initEvents() {
        Logger.debug('TaskService', '初始化事件监听');
        
        // 任务相关事件监听
        this.eventBus.on(TASK_EVENTS.COMPLETED, this.handleTaskComplete.bind(this));
        this.eventBus.on(TASK_EVENTS.STATUS_UPDATED, this.handleTaskStatusUpdate.bind(this));
        this.eventBus.on(TASK_EVENTS.ABANDONED, this.handleTaskAbandoned.bind(this));
        
        Logger.info('TaskService', '事件监听初始化完成');
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
                Logger.debug('TaskService', '任务列表加载完成:', result.data);
                return result.data;
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('TaskService', '加载任务列表失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '加载任务列表失败'
            });
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
        Logger.info("TaskService", `接受任务: ${taskId} 玩家ID: ${playerId}`);
        
        try {
            const response = await this.api.acceptTask(taskId, playerId);
            Logger.debug("TaskService", "接受任务响应:", response);
            
            // 更新任务状态
            const taskStatus = {
                id: taskId,
                status: 'ACCEPTED'
            };
            
            await this.updateTaskStatus(taskStatus);
            await this.loadCurrentTasks();
            
            // 触发任务状态更新事件
            this.eventBus.emit(TASK_EVENTS.STATUS_UPDATED, taskStatus);
            
            return response;
        } catch (error) {
            Logger.error("TaskService", "接受任务失败:", error);
            throw error;
        }
    }

    async handleTaskComplete(taskId) {
        Logger.info('TaskService', '处理任务完成:', taskId);
        try {
            const result = await this.api.completeTask(taskId);
            if (result.code === 0) {
                // 发送任务完成事件
                this.eventBus.emit(TASK_EVENTS.COMPLETED, {
                    taskId,
                    rewards: result.data.rewards,
                    message: result.data.message
                });
                
                // 播放完成音效
                this.eventBus.emit(AUDIO_EVENTS.PLAY, 'COMPLETE');
                
                // 显示完成通知
                this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                    type: 'SUCCESS',
                    message: `任务完成！获得 ${result.data.rewards.points} 点经验`
                });
                
                // 直接加载任务列表，不触发额外事件
                await this.loadTasks();
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('TaskService', '任务完成失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '任务完成失败'
            });
            this.eventBus.emit(AUDIO_EVENTS.PLAY, 'ERROR');
        }
    }

    async handleTaskStatusUpdate(data) {
        Logger.info('TaskService', '处理任务状态更新:', data);
        try {
            // 如果是列表更新，直接返回避免循环
            if (data.type === 'LIST_UPDATED') {
                return;
            }
            
            await this.updateTaskStatus(data);
            // 只在特定状态下重新加载任务
            if (['COMPLETED', 'ABANDONED', 'ACCEPTED'].includes(data.status)) {
                await Promise.all([
                    this.loadTasks(),
                    this.loadCurrentTasks()
                ]);
            }
        } catch (error) {
            Logger.error('TaskService', '处理任务状态更新失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '更新任务状态失败'
            });
        }
    }

    async handleTaskAbandoned(data) {
        Logger.info('TaskService', '处理任务放弃:', data);
        try {
            const result = await this.api.abandonTask(data.taskId, data.playerId);
            if (result.code === 0) {
                // 更新任务状态
                await this.updateTaskStatus({
                    id: data.taskId,
                    status: 'ABANDONED'
                });
                
                // 发送状态更新事件
                this.eventBus.emit(TASK_EVENTS.STATUS_UPDATED, {
                    taskId: data.taskId,
                    status: 'ABANDONED'
                });
                
                // 播放放弃音效
                this.eventBus.emit(AUDIO_EVENTS.PLAY, 'ABANDON');
                
                // 显示放弃通知
                this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                    type: 'SUCCESS',
                    message: '任务已放弃'
                });
                
                // 重新加载任务列表
                await this.loadTasks();
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            Logger.error('TaskService', '放弃任务失败:', error);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'ERROR',
                message: '放弃任务失败'
            });
            this.eventBus.emit(AUDIO_EVENTS.PLAY, 'ERROR');
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

    /**
     * 更新玩家ID并清理任务缓存
     * @param {string} newId - 新的玩家ID
     * @returns {Promise} 返回一个Promise表示操作完成
     */
    updatePlayerId(newId) {
        return new Promise((resolve, reject) => {
            try {
                Logger.debug("TaskService", "清理任务缓存，玩家ID更新为:", newId);
                
                // 清理任务缓存
                this.store.setState({
                    taskList: [],
                    currentTasks: []
                });
                
                // 更新存储的玩家ID
                this._playerId = newId;
                
                resolve();
            } catch (error) {
                Logger.error("TaskService", "清理任务缓存失败:", error);
                reject(error);
            }
        });
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

    /**
     * 处理NFC任务更新通知
     * @param {Object} data 任务更新数据
     */
    handleTaskUpdate(data) {
        Logger.info("TaskService", "开始处理NFC任务更新:", data);

        // 参数验证
        if (!data || !data.type) {
            Logger.error("TaskService", "无效的任务更新数据:", data);
            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: "ERROR",
                message: "收到无效的任务更新",
            });
            return;
        }

        Logger.debug("TaskService", "处理任务类型:", data.type);
        
        // 使用Map对象替代switch语句，提高可维护性
        const taskHandlers = {
            // 处理身份识别更新
            "IDENTITY": () => {
                Logger.info("TaskService", "处理身份识别更新");
                // 更新玩家ID
                this.playerService.setPlayerId(data.player_id);
                // 重新加载玩家信息
                this.playerService.loadPlayerInfo();
                // 刷新任务列表
                this.refreshTasks();
            },
            
            // 处理需要刷新任务的更新类型
            "NEW_TASK": () => {
                Logger.info("TaskService", "处理新任务更新");
                this.refreshTasks();
                this.eventBus.emit(AUDIO_EVENTS.PLAY, data.type);
            },
            "COMPLETE": () => {
                Logger.info("TaskService", "处理任务完成更新");
                this.refreshTasks();
                this.eventBus.emit(AUDIO_EVENTS.PLAY, data.type);
            },
            "CHECK": () => {
                Logger.info("TaskService", "处理任务检查更新");
                this.refreshTasks();
                this.eventBus.emit(AUDIO_EVENTS.PLAY, data.type);
            },
            
            // 处理只需要显示通知的更新类型
            "ALREADY_COMPLETED": () => {
                Logger.info("TaskService", "处理任务重复完成通知");
            },
            "REJECT": () => {
                Logger.info("TaskService", "处理任务驳回通知");
            },
            "CHECKING": () => {
                Logger.info("TaskService", "处理任务审核中通知");
            },
            
            // 处理错误情况
            "ERROR": () => {
                Logger.info("TaskService", "处理错误消息");
                this.eventBus.emit(AUDIO_EVENTS.PLAY, "ERROR");
            }
        };

        // 执行对应的处理函数
        const handler = taskHandlers[data.type];
        if (handler) {
            try {
                handler();
            } catch (error) {
                Logger.error("TaskService", `处理任务类型 ${data.type} 时发生错误:`, error);
                this.handleEventError(error, `处理任务更新失败: ${data.type}`);
            }
        } else {
            Logger.warn("TaskService", "未知的任务类型:", data.type);
        }

        // 显示通知
        Logger.debug("TaskService", "准备显示通知:", data);
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, data);
        Logger.debug("TaskService", "通知显示完成");
    }

    /**
     * 刷新所有任务
     */
    async refreshTasks() {
        try {
            Logger.info("TaskService", "开始刷新任务列表");
            
            // 使用防抖，避免频繁刷新
            if (this._refreshTimeout) {
                clearTimeout(this._refreshTimeout);
            }
            
            this._refreshTimeout = setTimeout(async () => {
                // 并行加载所有任务和当前任务
                await Promise.all([
                    this.loadTasks().then(tasks => {
                        this.eventBus.emit(TASK_EVENTS.LIST_UPDATED, tasks);
                    }),
                    this.loadCurrentTasks().then(currentTasks => {
                        this.eventBus.emit(TASK_EVENTS.CURRENT_UPDATED, currentTasks);
                    })
                ]);
                
                Logger.info("TaskService", "任务列表刷新完成");
            }, 300); // 300ms 的防抖时间
            
        } catch (error) {
            Logger.error("TaskService", "刷新任务失败:", error);
            this.handleEventError(error, "刷新任务失败");
        }
    }

    /**
     * 处理事件错误
     * @private
     */
    handleEventError(error, userMessage) {
        Logger.error("TaskService", userMessage, error);
        this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
            type: "ERROR",
            message: userMessage
        });
        this.eventBus.emit(AUDIO_EVENTS.PLAY, "ERROR");
    }
}

export default TaskService;