/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-10 17:02:31
 * @LastEditTime: 2025-01-22 11:09:50
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
// 任务类型配置
const TASK_TYPE_MAP = {
    'MAIN': {  // 主线任务
        text: '主线任务',
        color: '#FFC107',  // 金色
        icon: 'layui-icon-star'
    },
    'BRANCH': {  // 支线任务
        text: '支线任务',
        color: '#2196F3',  // 蓝色
        icon: 'layui-icon-note'
    },
    'SPECIAL': {  // 特殊任务
        text: '特殊任务',
        color: '#9C27B0',  // 紫色
        icon: 'layui-icon-gift'
    },
    'DAILY': {  // 每日任务
        text: '每日任务',
        color: '#4CAF50',  // 绿色
        icon: 'layui-icon-date'
    },
    'UNDEFINED': {  // 未定义任务
        text: '未知任务',
        color: '#9E9E9E',  // 灰色
        icon: 'layui-icon-help'
    }
}; 

// 任务状态配置 任务表中的任务有AVAILABLE IN_PROGRESS COMPLETED ABANDONED CHECKED UNAVAILABLE等状态
// 用户任务表中的任务有IN_PROGRESS进行中 COMPLETED已完成 ABANDONED已放弃等状态
const TASK_STATUS_MAP = {
    'AVAILABLE': {  // 可接受
        text: '可接受',
        color: '#4CAF50',  // 绿色
        icon: 'layui-icon-ok-circle'
    },
    'IN_PROGRESS': {  // 进行中
        text: '进行中',
        color: '#2196F3',  // 蓝色
        icon: 'layui-icon-time'
    },
    'COMPLETED': {  // 已完成
        text: '已完成',
        color: '#9C27B0',  // 紫色
        icon: 'layui-icon-check'
    },
    'ABANDONED': {  // 已放弃
        text: '已放弃',
        color: '#9E9E9E',  // 灰色
        icon: 'layui-icon-close'
    },
    'UNAVAILABLE': {  // 不可接受
        text: '不可接受',
        color: '#F44336',  // 红色
        icon: 'layui-icon-close-circle'
    }
}; 