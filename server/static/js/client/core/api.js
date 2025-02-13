/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:29:01
 * @LastEditTime: 2025-02-12 20:52:39
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
// API 请求封装
class APIClient {
    constructor(baseURL) {
        this.baseURL = baseURL;
        console.log('[API] Initializing API client with base URL:', baseURL);
    }

    async request(endpoint, options = {}) {
        try {
            const url = `${this.baseURL}${endpoint}`;
            console.log('[API] Making request to:', url);
            
            const response = await fetch(url, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    ...options.headers
                }
            });
            
            const data = await response.json();
            console.log('[API] Response received:', data);
            
            return data;
        } catch (error) {
            console.error('[API] Request failed:', error);
            throw error;
        }
    }

    // 任务相关 API
    async getCurrentTasks(playerId) {
        console.log('[API] Getting current tasks for player:', playerId);
        return this.request(`/api/tasks/current/${playerId}`);
    }

    async acceptTask(taskId, playerId) {
        console.log('[API] Accepting task:', taskId, 'for player:', playerId);
        return this.request(`/api/tasks/${taskId}/accept`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    async abandonTask(taskId, playerId) {
        console.log('[API] Abandoning task:', taskId, 'for player:', playerId);
        return this.request(`/api/tasks/${taskId}/abandon`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    async completeTask(taskId, playerId) {
        console.log('[API] Completing task:', taskId, 'for player:', playerId);
        return this.request(`/api/tasks/${taskId}/complete`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    // 玩家相关 API
    async getPlayerInfo(playerId) {
        console.log('[API] Getting player info:', playerId);
        return this.request(`/api/player/${playerId}`);
    }

    async getPlayerTags() {
        console.log('[API] Getting player tags');
        return this.request('/api/player/tags');
    }

    // 任务列表相关
    async getTaskList() {
        console.log('[API] Getting task list');
        return this.request('/api/tasks/list');
    }

    // NFC相关
    async getNFCStatus() {
        console.log('[API] Getting NFC status');
        return this.request('/api/nfc/status');
    }

    async handleNFCCard(cardData) {
        console.log('[API] Handling NFC card');
        return this.request('/api/nfc/handle', {
            method: 'POST',
            body: JSON.stringify(cardData)
        });
    }

    // 错误处理
    handleApiError(error, context) {
        console.error(`[API] Error in ${context}:`, error);
        if (error.response) {
            layer.msg(error.response.data.msg || '操作失败', {icon: 2});
            console.error('[API] Error response:', error.response);
        } else {
            layer.msg('网络请求失败，请检查连接', {icon: 2});
            console.error('[API] Error:', error);
        }
        throw error;
    }

    // 任务相关 API 扩展
    async loadAvailableTasks(playerId) {
        console.log('[API] Loading available tasks for player:', playerId);
        return this.request(`/api/tasks/available/${playerId}`);
    }

    async loadTaskHistory(playerId) {
        console.log('[API] Loading task history for player:', playerId);
        return this.request(`/api/tasks/history/${playerId}`);
    }

    async updateTaskStatus(taskId, status, playerId) {
        console.log('[API] Updating task status:', { taskId, status, playerId });
        return this.request(`/api/tasks/${taskId}/status`, {
            method: 'POST',
            body: JSON.stringify({
                player_id: playerId,
                status: status
            })
        });
    }

    async checkTaskRequirements(taskId, playerId) {
        console.log('[API] Checking task requirements:', { taskId, playerId });
        return this.request(`/api/tasks/${taskId}/check`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    // 玩家相关 API 扩展
    async updatePlayerInfo(playerId, data) {
        console.log('[API] Updating player info:', { playerId, data });
        return this.request(`/api/player/${playerId}/update`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getPlayerStats(playerId) {
        console.log('[API] Getting player stats:', playerId);
        return this.request(`/api/player/${playerId}/stats`);
    }

    async updatePlayerTags(playerId, tags) {
        console.log('[API] Updating player tags:', { playerId, tags });
        return this.request(`/api/player/${playerId}/tags`, {
            method: 'POST',
            body: JSON.stringify({ tags })
        });
    }

    // 词云相关
    async getWordCloud() {
        console.log('[API] Getting word cloud data');
        return this.request('/api/wordcloud');
    }

    async updateWordCloud(data) {
        console.log('[API] Updating word cloud:', data);
        return this.request('/api/wordcloud/update', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    // 通知相关
    async getNotifications(playerId) {
        console.log('[API] Getting notifications for player:', playerId);
        return this.request(`/api/notifications/${playerId}`);
    }

    async markNotificationRead(notificationId, playerId) {
        console.log('[API] Marking notification as read:', { notificationId, playerId });
        return this.request(`/api/notifications/${notificationId}/read`, {
            method: 'POST',
            body: JSON.stringify({ player_id: playerId })
        });
    }

    // 地图相关
    async getMapPoints(type) {
        console.log('[API] Getting map points for type:', type);
        return this.request(`/api/map/points/${type}`);
    }

    async updatePlayerLocation(playerId, location) {
        console.log('[API] Updating player location:', { playerId, location });
        return this.request(`/api/player/${playerId}/location`, {
            method: 'POST',
            body: JSON.stringify(location)
        });
    }

    // 排行榜相关
    async getLeaderboard(type = 'points', limit = 10) {
        console.log('[API] Getting leaderboard:', { type, limit });
        return this.request(`/api/leaderboard/${type}?limit=${limit}`);
    }

    // 成就相关
    async getAchievements(playerId) {
        console.log('[API] Getting achievements for player:', playerId);
        return this.request(`/api/achievements/${playerId}`);
    }

    // 系统相关
    async getSystemStatus() {
        console.log('[API] Getting system status');
        return this.request('/api/system/status');
    }

    async getGameConfig() {
        console.log('[API] Getting game configuration');
        return this.request('/api/system/config');
    }
}

// 修改导出方式
export default APIClient;  // 使用默认导出 