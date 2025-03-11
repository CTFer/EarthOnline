/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-13 21:56:01
 * @LastEditTime: 2025-03-10 10:15:49
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
export const SWIPER_CONFIG = {
    // 活动任务轮播配置
    activeTasks: {
        slidesPerView: 4,              // 同时显示的滑块数量
        spaceBetween: 20,              // 滑块之间的间距（像素）
        direction: "horizontal",        // 滑动方向：水平
        loop: false,                   // 是否循环播放
        
        // 响应式断点配置
        breakpoints: {
            1200: {                    // 当视窗宽度 >= 1200px
                slidesPerView: 4,      // 显示4个滑块
                spaceBetween: 20,      // 间距20px
            },
            768: {                     // 当视窗宽度 >= 768px
                slidesPerView: 2,      // 显示2个滑块
                spaceBetween: 15,      // 间距15px
            },
            0: {                       // 当视窗宽度 >= 0px
                slidesPerView: 1,      // 显示1个滑块
                spaceBetween: 10,      // 间距10px
            },
        },
        
        // 自由模式配置
        freeMode: {
            enabled: true,             // 启用自由模式
            momentum: true,            // 启用惯性滑动
            momentumRatio: 1,          // 惯性滑动的力度比率
            momentumVelocityRatio: 1   // 惯性滑动的速度比率
        },
        
        // 鼠标滚轮配置
        mousewheel: {
            forceToAxis: true,         // 强制滚轮只影响一个方向
            invert: false,             // 是否反转滚动方向
            sensitivity: 1,            // 滚轮灵敏度
        },
        
        // 滚动条配置
        scrollbar: {
            el: '.swiper-scrollbar-active-tasks',  // 滚动条容器的类名
            draggable: true,           // 是否可拖动
            hide: false,               // 是否自动隐藏
            dragSize: 100,             // 滚动条滑块的大小
            snapOnRelease: true,       // 释放时是否自动对齐
            dragClass: 'swiper-scrollbar-drag',    // 滚动条滑块的类名
            lockClass: 'swiper-scrollbar-lock',    // 滚动条锁定时的类名
        },
        
        resistance: true,              // 开启边缘阻力
        resistanceRatio: 0.85,         // 阻力大小（值越小阻力越大）
        watchSlidesProgress: true,     // 监视滑块进度
        observer: true,                // 监视容器变化
        observeParents: true,          // 监视父元素变化
        watchOverflow: true,           // 监视是否溢出
        updateOnWindowResize: true,    // 窗口调整大小时更新
    },

    // 任务列表轮播配置
    taskList: {
        slidesPerView: "auto",         // 自动计算显示的滑块数量
        spaceBetween: 10,              // 滑块之间的间距（像素）
        direction: "vertical",         // 滑动方向：垂直
        loop: false,                   // 不循环播放
        
        // 自由模式配置
        freeMode: {
            enabled: true,             // 启用自由模式
            momentum: true,            // 启用惯性滑动
            momentumRatio: 1,          // 惯性滑动的力度比率
            momentumVelocityRatio: 1   // 惯性滑动的速度比率
        },
        
        // 鼠标滚轮配置
        mousewheel: {
            forceToAxis: true,         // 强制滚轮只影响一个方向
            sensitivity: 1             // 滚轮灵敏度
        },
        
        // 滚动条配置
        scrollbar: {
            el: ".swiper-scrollbar-task-list",     // 滚动条容器的类名
            draggable: true,           // 是否可拖动
            hide: false,               // 是否自动隐藏
            dragSize: 100,             // 滚动条滑块的大小
            snapOnRelease: true,       // 释放时是否自动对齐
            dragClass: 'swiper-scrollbar-drag',    // 滚动条滑块的类名
            lockClass: 'swiper-scrollbar-lock',    // 滚动条锁定时的类名
        },
        
        resistance: true,              // 开启边缘阻力
        resistanceRatio: 0.85,         // 阻力大小（值越小阻力越大）
        watchSlidesProgress: true,     // 监视滑块进度
        observer: true,                // 监视容器变化
        observeParents: true,          // 监视父元素变化
        watchOverflow: true,           // 监视是否溢出
        updateOnWindowResize: true,    // 窗口调整大小时更新
    }
}; 