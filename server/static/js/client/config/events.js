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

/**
 * 路由相关事件
 */
export const ROUTE_EVENTS = {
    // 路由变化前
    BEFORE_CHANGE: 'route:before:change',
    // 路由变化时
    CHANGED: 'route:changed',
    // 路由变化后
    AFTER_CHANGE: 'route:after:change',
    // 路由加载开始
    LOADING_START: 'route:loading:start',
    // 路由加载结束
    LOADING_END: 'route:loading:end',
    // 路由错误
    ERROR: 'route:error',
    // 首页初始化
    HOME_INIT: 'route:home:init',
    // 首页清理
    HOME_CLEANUP: 'route:home:cleanup',
    // 商城初始化
    SHOP_INIT: 'route:shop:init',
    // 商城清理
    SHOP_CLEANUP: 'route:shop:cleanup'
}; 
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
    CURRENT_UPDATED: 'task:current:updated',
    // 任务错误
    ERROR: 'task:error',
    // 任务点击
    CLICKED: 'task:clicked',
    // 任务检查
    CHECKING: 'task:checking',
    // 任务驳回
    REJECTED: 'task:rejected'
};

// 玩家相关事件
export const PLAYER_EVENTS = {
    // 玩家ID更新
    ID_UPDATED: 'player:id:updated',
    // 玩家信息更新
    INFO_UPDATED: 'player:info:updated',
    // 玩家经验值更新
    EXP_UPDATED: 'player:exp:updated',
    // 玩家状态更新
    STATUS_UPDATED: 'player:status:updated',
    // 玩家位置更新
    LOCATION_UPDATED: 'player:location:updated',
    // 玩家统计更新
    STATS_UPDATED: 'player:stats:updated'
};

// 地图相关事件
export const MAP_EVENTS = {
    // 渲染器切换
    RENDERER_CHANGED: 'map:renderer:changed',
    // 地图初始化完成
    INITIALIZED: 'map:initialized',
    // GPS更新
    GPS_UPDATED: 'gps:update',
    // 显示模式改变
    DISPLAY_MODE_CHANGED: 'map:display:mode:changed',
    // 时间范围改变
    TIME_RANGE_CHANGED: 'map:time:range:changed',
    // 地图数据更新
    DATA_UPDATED: 'map:data:updated',
    // 地图中心点更新
    CENTER_UPDATED: 'map:center:updated',
    // 地图缩放级别更新
    ZOOM_UPDATED: 'map:zoom:updated'
};

// UI相关事件
export const UI_EVENTS = {
    // 通知显示
    NOTIFICATION_SHOW: 'ui:notification:show',
    // 模态框显示
    MODAL_SHOW: 'ui:modal:show',
    // 模态框关闭
    MODAL_CLOSE: 'ui:modal:close',
    // 加载状态改变
    LOADING_CHANGED: 'ui:loading:changed',
    // 主题改变
    THEME_CHANGED: 'ui:theme:changed',
    // 视图更新
    VIEW_UPDATED: 'ui:view:updated',
    // 错误显示
    ERROR_SHOW: 'ui:error:show'
};

// WebSocket相关事件
export const WS_EVENTS = {
    // 连接成功
    CONNECTED: 'ws:connected',
    // 连接断开
    DISCONNECTED: 'ws:disconnected',
    // 正在连接
    CONNECTING: 'ws:connecting',
    // 重新连接中
    RECONNECTING: 'ws:reconnecting',
    // 连接错误
    ERROR: 'ws:error',
    // 消息接收
    MESSAGE_RECEIVED: 'ws:message:received',
    // 消息发送
    MESSAGE_SENT: 'ws:message:sent'
};

// 音频相关事件
export const AUDIO_EVENTS = {
    // 音频播放
    PLAY: 'audio:play',
    // 音频停止
    STOP: 'audio:stop',
    // 音量改变
    VOLUME_CHANGED: 'audio:volume:changed',
    // 音频加载
    LOADED: 'audio:loaded',
    // 音频错误
    ERROR: 'audio:error',
    // 音频暂停
    PAUSE: 'audio:pause',
    // 音频恢复
    RESUME: 'audio:resume'
};

// Live2D相关事件
export const LIVE2D_EVENTS = {
    MODEL_LOADED: 'live2d:modelLoaded',
    INTERACTION: 'live2d:interaction',
    // 动作播放
    MOTION_PLAY: 'live2d:motion:play',
    // 表情改变
    EXPRESSION_CHANGED: 'live2d:expression:changed',
    // 模型错误
    ERROR: 'live2d:error',
    // 模型销毁
    DESTROYED: 'live2d:destroyed'
};

// 通知相关事件
export const NOTIFICATION_EVENTS = {
    // 新通知
    NEW: 'notification:new',
    // 通知更新
    UPDATE: 'notification:update',
    // 通知删除
    DELETE: 'notification:delete',
    // 通知已读
    READ: 'notification:read',
    // 通知清空
    CLEAR: 'notification:clear'
};

// 商城相关事件
export const SHOP_EVENTS = {
    // 进入商城
    ENTER: 'shop:enter',
    // 离开商城
    LEAVE: 'shop:leave',
    // 商品列表更新
    ITEMS_UPDATED: 'shop:items:updated',
    // 购买商品
    PURCHASE: 'shop:purchase',
    // 购买成功
    PURCHASE_SUCCESS: 'shop:purchase:success',
    // 购买失败
    PURCHASE_FAILED: 'shop:purchase:failed'
}; 
