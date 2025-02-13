/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:29:01
 * @LastEditTime: 2025-02-13 23:15:29
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';

// API 请求封装
class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
        Logger.info('API', '初始化 API 客户端:', baseURL);
    }

    async request(endpoint, options = {}) {
        Logger.debug('API', `发起请求: ${endpoint}`, options);
        try {
            const url = `${this.baseURL}${endpoint}`;
            Logger.debug('API', '请求:', url);
            
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                }
            });

            if (!response.ok) {
                Logger.error('API', `请求失败: ${response.status}`, await response.text());
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            Logger.debug('API', `请求成功: ${endpoint}`, data);
            return data;
        } catch (error) {
            Logger.error('API', `请求异常: ${endpoint}`, error);
            throw error;
        }
    }

    // 任务相关 API
    async getCurrentTasks(playerId) {
        Logger.info('API', '获取当前任务:', playerId);
        return this.request(`/api/tasks/current/${playerId}`);
    }

    async acceptTask(taskId, playerId) {
        Logger.info('API', '接受任务:', taskId, 'for player:', playerId);
        return this.request(`/api/tasks/accept`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId, task_id: taskId })
        });
    }

    async abandonTask(taskId, playerId) {
        Logger.info('API', '放弃任务:', taskId, 'for player:', playerId);
        return this.request(`/api/tasks/${taskId}/abandon`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    async completeTask(taskId, playerId) {
        Logger.info('API', '完成任务:', taskId, 'for player:', playerId);
        return this.request(`/api/tasks/${taskId}/complete`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    // 玩家相关 API
    async getPlayerInfo(playerId) {
        Logger.info('API', '获取玩家信息:', playerId);
        return this.request(`/api/player/${playerId}`);
    }

    async getPlayerTags() {
        Logger.info('API', '获取玩家标签');
        return this.request('/api/player/tags');
    }

    // 任务列表相关
    async getTaskList(playerId) {
        Logger.info('API', '获取任务列表');
        return this.request(`/api/tasks/available/${playerId}`);
    }

    // NFC相关
    async getNFCStatus() {
        Logger.info('API', '获取NFC状态');
        return this.request('/api/nfc/status');
    }

    async handleNFCCard(cardData) {
        Logger.info('API', '处理NFC卡片');
        return this.request('/api/nfc/handle', {
            method: 'POST',
            body: JSON.stringify(cardData)
        });
    }

    // 错误处理
    handleApiError(error, context) {
        Logger.error('API', `错误: ${context}`, error);
        if (error.response) {
            layer.msg(error.response.data.msg || '操作失败', {icon: 2});
            Logger.error('API', '错误响应:', error.response);
        } else {
            layer.msg('网络请求失败，请检查连接', {icon: 2});
            Logger.error('API', '错误:', error);
        }
        throw error;
    }

    // 任务相关 API 扩展
    async loadAvailableTasks(playerId) {
        Logger.info('API', '加载可用任务:', playerId);
        return this.request(`/api/tasks/available/${playerId}`);
    }

    async loadTaskHistory(playerId) {
        Logger.info('API', '加载任务历史:', playerId);
        return this.request(`/api/tasks/history/${playerId}`);
    }

    async updateTaskStatus(taskId, status, playerId) {
        Logger.info('API', '更新任务状态:', { taskId, status, playerId });
        return this.request(`/api/tasks/${taskId}/status`, {
            method: 'POST',
            body: JSON.stringify({
                player_id: playerId,
                status: status
            })
        });
    }

    async checkTaskRequirements(taskId, playerId) {
        Logger.info('API', '检查任务要求:', { taskId, playerId });
        return this.request(`/api/tasks/${taskId}/check`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    // 玩家相关 API 扩展
    async updatePlayerInfo(playerId, data) {
        Logger.info('API', '更新玩家信息:', { playerId, data });
        return this.request(`/api/player/${playerId}/update`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getPlayerStats(playerId) {
        Logger.info('API', '获取玩家统计:', playerId);
        return this.request(`/api/player/${playerId}/stats`);
    }

    async updatePlayerTags(playerId, tags) {
        Logger.info('API', '更新玩家标签:', { playerId, tags });
        return this.request(`/api/player/${playerId}/tags`, {
            method: 'POST',
            body: JSON.stringify({ tags })
        });
    }

    // 词云相关
    async getWordCloud() {
        Logger.info('API', '获取词云数据');
        return this.request('/api/wordcloud');
    }

    async updateWordCloud(data) {
        Logger.info('API', '更新词云:', data);
        return this.request('/api/wordcloud/update', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // 通知相关
    async getNotifications(playerId) {
        Logger.info('API', '获取通知:', playerId);
        return this.request(`/api/notifications/${playerId}`);
    }

    async markNotificationRead(notificationId, playerId) {
        Logger.info('API', '标记通知为已读:', { notificationId, playerId });
        return this.request(`/api/notifications/${notificationId}/read`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    // 地图相关
    async getMapPoints(type) {
        Logger.info('API', '获取地图点:', type);
        return this.request(`/api/map/points/${type}`);
    }

    async updatePlayerLocation(playerId, location) {
        Logger.info('API', '更新玩家位置:', { playerId, location });
        return this.request(`/api/player/${playerId}/location`, {
            method: 'POST',
            body: JSON.stringify(location)
        });
    }

    // 排行榜相关
    async getLeaderboard(type = 'points', limit = 10) {
        Logger.info('API', '获取排行榜:', { type, limit });
        return this.request(`/api/leaderboard/${type}?limit=${limit}`);
    }

    // 成就相关
    async getAchievements(playerId) {
        Logger.info('API', '获取成就:', playerId);
        return this.request(`/api/achievements/${playerId}`);
    }

    // 系统相关
    async getSystemStatus() {
        Logger.info('API', '获取系统状态');
        return this.request('/api/system/status');
    }

    async getGameConfig() {
        Logger.info('API', '获取游戏配置');
        return this.request('/api/system/config');
    }
}

// 修改导出方式
export default APIClient;  // 使用默认导出 