class TaskService {
    constructor(apiClient, eventBus, store) {
        this.api = apiClient;
        this.eventBus = eventBus;
        this.store = store;
        this.activeTasksSwiper = null;
        this.taskListSwiper = null;
        this.loading = false;
        console.log('[TaskService] Initialized');
        
        // 订阅相关事件
        this.eventBus.on('task:complete', this.handleTaskComplete.bind(this));
        this.eventBus.on('task:new', this.handleNewTask.bind(this));
    }

    async loadTasks() {
        if (this.loading) return;
        
        console.log('[TaskService] Loading tasks');
        this.loading = true;
        try {
            const result = await this.api.getTaskList();
            if (result.code === 0) {
                this.store.setState({ taskList: result.data });
                this.eventBus.emit('tasks:loaded', result.data);
                return result.data;
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            console.error('[TaskService] Load tasks failed:', error);
            this.eventBus.emit('tasks:error', error);
            throw error;
        } finally {
            this.loading = false;
        }
    }

    async getCurrentTasks(playerId) {
        try {
            console.log('[TaskService] Loading current tasks for player:', playerId);
            const tasks = await this.api.request(`/api/tasks/current/${playerId}`);
            this.store.setState({ tasks: tasks.data });
            this.eventBus.emit('tasks:updated', tasks.data);
            return tasks.data;
        } catch (error) {
            console.error('[TaskService] Get current tasks failed:', error);
            ErrorHandler.handle(error, 'TaskService.getCurrentTasks');
            throw error;
        }
    }

    async acceptTask(taskId, playerId) {
        console.log('[TaskService] Accepting task:', taskId);
        try {
            const result = await this.api.acceptTask(taskId, playerId);
            if (result.code === 0) {
                this.eventBus.emit('task:accepted', result.data);
                await this.getCurrentTasks(playerId);
                return result.data;
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            console.error('[TaskService] Accept task failed:', error);
            this.eventBus.emit('task:error', error);
            throw error;
        }
    }

    async handleTaskComplete(taskId) {
        console.log('[TaskService] Handling task complete:', taskId);
        try {
            const result = await this.api.completeTask(taskId);
            if (result.code === 0) {
                this.eventBus.emit('task:completed', result.data);
                await this.loadTasks();
            } else {
                throw new Error(result.msg);
            }
        } catch (error) {
            console.error('[TaskService] Complete task failed:', error);
            this.eventBus.emit('task:error', error);
        }
    }

    async handleNewTask(taskData) {
        console.log('[TaskService] Handling new task:', taskData);
        try {
            await this.loadTasks();
            this.eventBus.emit('task:added', taskData);
        } catch (error) {
            console.error('[TaskService] Handle new task failed:', error);
            this.eventBus.emit('task:error', error);
        }
    }

    initTaskSwipers() {
        console.log('[TaskService] Initializing task swipers');
        this.initActiveTasksSwiper();
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
        console.log('[TaskService] Active tasks swiper initialized');
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
        console.log('[TaskService] Task list swiper initialized');
    }

    destroySwipers() {
        console.log('[TaskService] Destroying swipers');
        if (this.activeTasksSwiper) {
            this.activeTasksSwiper.destroy(true, true);
            this.activeTasksSwiper = null;
        }
        if (this.taskListSwiper) {
            this.taskListSwiper.destroy(true, true);
            this.taskListSwiper = null;
        }
    }
}

export default TaskService;