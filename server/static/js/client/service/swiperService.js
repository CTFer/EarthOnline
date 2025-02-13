import Logger from '../../utils/logger.js';
import { SWIPER_CONFIG } from '../config/swiperConfig.js';

class SwiperService {
    constructor() {
        this.activeTasksSwiper = null;
        this.taskListSwiper = null;
        Logger.info('SwiperService', '初始化滑动组件服务');
    }

    initSwipers() {
        Logger.info('SwiperService', '初始化所有滑动组件');
        this.initActiveTasksSwiper();
        this.initTaskListSwiper();
    }

    initActiveTasksSwiper() {
        if (this.activeTasksSwiper) {
            this.activeTasksSwiper.destroy(true, true);
        }
        
        const container = document.querySelector(".active-tasks-swiper");
        if (!container) return;

        this.activeTasksSwiper = new Swiper(".active-tasks-swiper", SWIPER_CONFIG.activeTasks);
        Logger.info('SwiperService', '活动任务滑动组件初始化完成');
    }

    initTaskListSwiper() {
        if (this.taskListSwiper) {
            this.taskListSwiper.destroy(true, true);
        }

        const container = document.querySelector(".task-list-swiper");
        if (!container) return;

        this.taskListSwiper = new Swiper(".task-list-swiper", SWIPER_CONFIG.taskList);
        Logger.info('SwiperService', '任务列表滑动组件初始化完成');
    }

    destroySwipers() {
        Logger.info('SwiperService', '销毁所有滑动组件');
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

export default SwiperService; 