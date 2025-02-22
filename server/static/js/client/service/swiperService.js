/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-13 21:56:14
 * @LastEditTime: 2025-02-22 21:38:18
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
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
        const container = document.querySelector(".active-tasks-swiper");
        if (!container) {
            Logger.warn('SwiperService', '活动任务滑动容器不存在');
            return;
        }

        try {
            this.activeTasksSwiper = new Swiper(container, {
                ...SWIPER_CONFIG.activeTasks,

                navigation: {
                    nextEl: '.swiper-button-next',
                    prevEl: '.swiper-button-prev',
                },
                scrollbar: {
                    el: ".swiper-scrollbar-active-tasks",
                    draggable: true,
                    hide: false,
                    dragSize: 100,
                    snapOnRelease: true,
                    dragClass: 'swiper-scrollbar-drag',
                    lockClass: 'swiper-scrollbar-lock',
                },
            });

            Logger.info('SwiperService', '活动任务滑动组件初始化完成');
        } catch (error) {
            Logger.error('SwiperService', '初始化活动任务滑动组件失败:', error);
        }
    }

    initTaskListSwiper() {
        const container = document.querySelector(".task-list-swiper");
        if (!container) {
            Logger.warn('SwiperService', '任务列表滑动容器不存在');
            return;
        }

        try {
            this.taskListSwiper = new Swiper(container, {
                ...SWIPER_CONFIG.taskList,
                scrollbar: {
                    el: ".swiper-scrollbar-task-list",
                    draggable: true,
                    hide: false,
                    dragSize: 100,
                    snapOnRelease: true,
                    dragClass: 'swiper-scrollbar-drag',
                    lockClass: 'swiper-scrollbar-lock',
                },
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