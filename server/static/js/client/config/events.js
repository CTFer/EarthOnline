/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-18 09:03:41
 * @LastEditTime: 2025-02-19 14:17:47
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
/**
 * @description 事件常量配置文件
 */

// 任务相关事件
export const TASK_EVENTS = {
    // 任务状态更新
    STATUS_UPDATED: 'task:status:updated',
    // 任务完成
    COMPLETED: 'task:completed',
    // 任务接受
    ACCEPTED: 'task:accepted',
    // 任务放弃
    ABANDONED: 'task:abandoned',
    // 任务详情请求
    DETAILS_REQUESTED: 'task:details:requested',
    // 任务列表更新
    LIST_UPDATED: 'task:list:updated',
    // 当前任务更新
    CURRENT_UPDATED: 'task:current:updated'
};

// 玩家相关事件
export const PLAYER_EVENTS = {
    // 玩家ID更新
    ID_UPDATED: 'player:id:updated',
    // 玩家信息更新
    INFO_UPDATED: 'player:info:updated',
    // 玩家经验值更新
    EXP_UPDATED: 'player:exp:updated'
};

// 地图相关事件
export const MAP_EVENTS = {
    // 渲染器切换
    RENDERER_CHANGED: 'map:renderer:changed',
    // 地图初始化完成
    INITIALIZED: 'map:initialized',
    // GPS更新
    GPS_UPDATED: 'gps:update',
    // 玩家更新
    PLAYER_UPDATED: 'player:update'
};

// UI相关事件
export const UI_EVENTS = {
    // 通知显示
    NOTIFICATION_SHOW: 'ui:notification:show',
    // 模态框显示
    MODAL_SHOW: 'ui:modal:show',
    // 模态框关闭
    MODAL_CLOSE: 'ui:modal:close'
};

// WebSocket相关事件
export const WS_EVENTS = {
    // 连接成功
    CONNECTED: 'ws:connected',
    // 连接断开
    DISCONNECTED: 'ws:disconnected',
    // 消息接收
    MESSAGE_RECEIVED: 'ws:message:received'
};

// 音频相关事件
export const AUDIO_EVENTS = {
    // 音频播放
    PLAY: 'audio:play',
    // 音频停止
    STOP: 'audio:stop',
    // 音量改变
    VOLUME_CHANGED: 'audio:volume:changed'
};

// Live2D相关事件
export const LIVE2D_EVENTS = {
    // 模型加载完成
    MODEL_LOADED: 'live2d:model:loaded',
    // 动作播放
    MOTION_PLAY: 'live2d:motion:play'
}; 