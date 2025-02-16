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
        if (!container) {
            Logger.warn('SwiperService', '活动任务滑动容器不存在');
            return;
        }

        try {
            this.activeTasksSwiper = new Swiper(".active-tasks-swiper", {
                ...SWIPER_CONFIG.activeTasks,
                on: {
                    // 滑动时实时更新滚动条
                    setTranslate: function(swiper, translate) {
                        const scrollbar = this.scrollbar;
                        if (scrollbar && scrollbar.el) {
                            const progress = Math.abs(translate) / (this.virtualSize - this.width);
                            const dragEl = scrollbar.el.querySelector('.swiper-scrollbar-drag');
                            if (dragEl) {
                                const translateX = progress * (scrollbar.el.offsetWidth - dragEl.offsetWidth);
                                dragEl.style.transform = `translate3d(${translateX}px, 0, 0)`;
                            }
                        }
                    },
                    // 监听滚动条拖动
                    scrollbarDragMove: function() {
                        this.updateProgress();
                        this.updateActiveIndex();
                        this.updateSlidesClasses();
                    }
                }
            });
            
            Logger.info('SwiperService', '活动任务滑动组件初始化完成');
        } catch (error) {
            Logger.error('SwiperService', '初始化活动任务滑动组件失败:', error);
        }
    }

    initTaskListSwiper() {
        if (this.taskListSwiper) {
            this.taskListSwiper.destroy(true, true);
        }

        const container = document.querySelector(".task-list-swiper");
        if (!container) {
            Logger.warn('SwiperService', '任务列表滑动容器不存在');
            return;
        }

        try {
            this.taskListSwiper = new Swiper(".task-list-swiper", {
                ...SWIPER_CONFIG.taskList,
                on: {
                    // 滑动时实时更新滚动条
                    setTranslate: function(swiper, translate) {
                        const scrollbar = this.scrollbar;
                        if (scrollbar && scrollbar.el) {
                            const progress = Math.abs(translate) / (this.virtualSize - this.height);
                            const dragEl = scrollbar.el.querySelector('.swiper-scrollbar-drag');
                            if (dragEl) {
                                const translateY = progress * (scrollbar.el.offsetHeight - dragEl.offsetHeight);
                                dragEl.style.transform = `translate3d(0, ${translateY}px, 0)`;
                            }
                        }
                    },
                    // 监听滚动条拖动
                    scrollbarDragMove: function() {
                        this.updateProgress();
                        this.updateActiveIndex();
                        this.updateSlidesClasses();
                    }
                }
            });
            
            Logger.info('SwiperService', '任务列表滑动组件初始化完成');
        } catch (error) {
            Logger.error('SwiperService', '初始化任务列表滑动组件失败:', error);
        }
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