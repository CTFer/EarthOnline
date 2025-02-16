/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-13 21:56:01
 * @LastEditTime: 2025-02-15 18:50:53
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
export const SWIPER_CONFIG = {
    activeTasks: {
        slidesPerView: 3,
        spaceBetween: 30,
        direction: "horizontal",
        loop: false,
        freeMode: {
            enabled: true,
            momentum: true,
            momentumRatio: 1,
            momentumVelocityRatio: 1
        },
        mousewheel: {
            forceToAxis: true,
            invert: false,
            sensitivity: 1,
        },
        scrollbar: {
            el: '.swiper-scrollbar-active-tasks',
            draggable: true,
            hide: false,
            dragSize: 100,
            snapOnRelease: true,
            dragClass: 'swiper-scrollbar-drag',
            lockClass: 'swiper-scrollbar-lock',
        },
        resistance: true,
        resistanceRatio: 0.85,
        watchSlidesProgress: true,
        observer: true,
        observeParents: true,
        watchOverflow: true,
        updateOnWindowResize: true,
    },

    taskList: {
        direction: "vertical",
        slidesPerView: "auto",
        height: 'auto',
        freeMode: {
            enabled: true,
            momentum: true,
            momentumRatio: 1,
            momentumVelocityRatio: 1
        },
        mousewheel: {
            forceToAxis: true,
            sensitivity: 1
        },
        scrollbar: {
            el: ".swiper-scrollbar-task-list",
            draggable: true,
            hide: false,
            dragSize: 100,
            snapOnRelease: true,
            dragClass: 'swiper-scrollbar-drag',
            lockClass: 'swiper-scrollbar-lock',
        },
        resistance: true,
        resistanceRatio: 0.85,
        watchSlidesProgress: true,
        observer: true,
        observeParents: true,
        watchOverflow: true,
        updateOnWindowResize: true,
    }
}; 