/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-13 21:56:01
 * @LastEditTime: 2025-02-14 14:30:30
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
        freeMode: true,
        mousewheel: true,
        mousewheel: {
            forceToAxis: true,
            invert: false,
            sensitivity: 1,
        }
    },
    
    taskList: {
        direction: "vertical",
        slidesPerView: "auto",
        freeMode: true,
        mousewheel: true,
        scrollbar: {
            el: ".swiper-scrollbar",
        }
    }
}; 