/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-10 17:02:31
 * @LastEditTime: 2025-02-22 17:35:45
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */

// 声明配置变量
export const SERVER = "http://192.168.5.18/";

export const Live2D_MODE = false;
// 角色图片配置，使用player_id作为key
export const Character_image = {
  1: "/static/img/character_image.png",
};

// 控制台日志配置
// 现在日志系统的工作方式如下：
// 1、如果模块在白名单中（allowedModules 不为空），只输出白名单中的模块日志
// 2、如果白名单为空，则检查黑名单：
// - 如果模块在黑名单中，不输出该模块的日志
// - 如果模块不在黑名单中，输出该模块的日志
// 特例：如果是错误日志且 alwaysError 为 true，则始终输出，不受黑白名单影响
export const LOG_CONFIG = {
  enableConsoleLog: true, // 是否启用控制台输出
  logLevel: "debug", // 日志级别: 'debug', 'info', 'warn', 'error'
  allowedModules: ['EventManager','Live2DService','GameManager'], // 允许输出日志的模块，为空输出全部模块（白名单优先级高于黑名单）
  blockedModules: ["Utils"], // 禁止输出日志的模块（黑名单）
  alwaysError: true, // 是否总是输出error级别的日志
  timeFormat: true, // 是否在日志中显示时间
  styleOutput: true, // 是否启用样式输出
  styles: {
    debug: "color: #9E9E9E", // 灰色
    info: "color: #2196F3", // 蓝色
    warn: "color: #FF9800", // 橙色
    error: "color: #F44336", // 红色
  },
};

// 音频配置
export const AUDIO_CONFIG = {
  enabled: false, // 是否启用音频
  preloadStrategy: "ON_DEMAND", // 加载策略: 'IMMEDIATE'(立即加载) | 'ON_DEMAND'(按需加载)
  sounds: {
    COMPLETE: {
      path: "/static/audio/complete.mp3",
      preload: true, // 是否预加载
    },
    ACCEPT: {
      path: "/static/audio/accept.mp3",
      preload: false,
    },
    ERROR: {
      path: "/static/audio/error.mp3",
      preload: true, // 错误提示音最好预加载
    },
    ABANDON: {
      path: "/static/audio/abandon.mp3",
      preload: false,
    },
    CHECKING: {
      path: "/static/audio/check.mp3",
      preload: false,
    },
  },
};
// 任务类型配置
export const TASK_TYPE_MAP = {
  MAIN: {
    // 主线任务
    text: "主线任务",
    color: "#FFC107", // 金色
    icon: "layui-icon-star",
  },
  BRANCH: {
    // 支线任务
    text: "支线任务",
    color: "#2196F3", // 蓝色
    icon: "layui-icon-note",
  },
  SPECIAL: {
    // 特殊任务
    text: "特殊任务",
    color: "#9C27B0", // 紫色
    icon: "layui-icon-gift",
  },
  DAILY: {
    // 每日任务
    text: "每日任务",
    color: "#4CAF50", // 绿色
    icon: "layui-icon-date",
  },
  UNDEFINED: {
    // 未定义任务
    text: "未知任务",
    color: "#9E9E9E", // 灰色
    icon: "layui-icon-help",
  },
};

// 任务池中的任务状态配置
export const TASK_STATUS_MAP = {
  ACCEPT: {
    // 已接受
    text: "已接受",
    color: "#2196F3", // 蓝色
    icon: "layui-icon-flag",
  },
  LOCKED: {
    // 未解锁
    text: "未解锁",
    color: "#9E9E9E", // 灰色
    icon: "layui-icon-password",
  },
  AVAIL: {
    // 可接受
    text: "可接受",
    color: "#4CAF50", // 绿色
    icon: "layui-icon-ok-circle",
  },
  COMPLETED: {
    // 已完成
    text: "已完成",
    color: "#9C27B0", // 紫色
    icon: "layui-icon-check",
  },
};

// 用户任务表中的任务状态配置
export const PLAYER_TASK_STATUS_MAP = {
  IN_PROGRESS: {
    // 进行中
    text: "进行中",
    color: "#2196F3", // 蓝色
    icon: "layui-icon-time",
  },
  CHECK: {
    // 待检查
    text: "待检查",
    color: "#FF9800", // 橙色
    icon: "layui-icon-survey",
  },
  REJECT: {
    // 已驳回
    text: "已驳回",
    color: "#F44336", // 红色
    icon: "layui-icon-close-fill",
  },
  UNFINISH: {
    // 未完成
    text: "未完成",
    color: "#9E9E9E", // 灰色
    icon: "layui-icon-close",
  },
  COMPLETED: {
    // 已完成
    text: "已完成",
    color: "#9C27B0", // 紫色
    icon: "layui-icon-check",
  },
};
// 修改导出语法为传统方式
// window.SERVER = SERVER;
// window.MAP_CONFIG = MAP_CONFIG;
// window.TASK_TYPE_MAP = TASK_TYPE_MAP;
// window.TASK_STATUS_MAP = TASK_STATUS_MAP;
// window.PLAYER_TASK_STATUS_MAP = PLAYER_TASK_STATUS_MAP;
// window.LOG_CONFIG = LOG_CONFIG;
