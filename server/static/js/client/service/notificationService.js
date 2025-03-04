/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-17 15:30:00
 * @LastEditors: 一根鱼骨棒
 * @Description: 通知服务
 */
import Logger from '../../utils/logger.js';

class NotificationService {
    constructor(eventBus, wsManager, api) {
        Logger.info('NotificationService', '初始化通知服务');
        this.eventBus = eventBus;
        this.wsManager = wsManager;
        this.notifications = [];
        this.container = document.querySelector('.notification-list');
        this.api = api;
        
        // 绑定WebSocket事件
        // if (this.wsManager) {
        //     this.wsManager.socket.on('notification:new', this.handleNewNotification.bind(this));
        //     this.wsManager.socket.on('notification:update', this.handleNotificationUpdate.bind(this));
        //     this.wsManager.socket.on('notification:delete', this.handleNotificationDelete.bind(this));
        // }
        
        // 初始化通知列表
        this.loadNotifications();
    }

    // 加载通知列表
    async loadNotifications() {
        Logger.info('NotificationService', '加载通知列表');
        try {
            const response = await this.api.getNotifications();
            const data = await response.json();
            
            if (data.code === 0) {
                this.notifications = data.data;
                this.renderNotifications();
            } else {
                throw new Error(data.msg || '加载通知失败');
            }
        } catch (error) {
            Logger.error('NotificationService', '加载通知失败:', error);
        }
    }

    // 渲染通知列表
    renderNotifications() {
        Logger.debug('NotificationService', '渲染通知列表');
        if (!this.container) return;
        
        this.container.innerHTML = this.notifications
            .sort((a, b) => b.timestamp - a.timestamp)
            .map(notification => this.createNotificationElement(notification))
            .join('');
    }

    // 创建通知元素
    createNotificationElement(notification) {
        const time = this.formatTime(notification.timestamp);
        const icons = {
            success: 'layui-icon-ok-circle',
            warning: 'layui-icon-tips',
            info: 'layui-icon-notice',
            error: 'layui-icon-close-fill'
        };
        
        return `
            <div class="notification-item ${notification.type}" data-id="${notification.id}">
                <div class="notification-header">
                    <div class="notification-title">
                        <i class="layui-icon ${icons[notification.type]} notification-icon ${notification.type}"></i>
                        ${notification.title}
                    </div>
                    <span class="notification-time">${time}</span>
                </div>
                <div class="notification-content">${notification.content}</div>
            </div>
        `;
    }

    // 添加新通知
    addNotification(notification) {
        Logger.info('NotificationService', '添加新通知:', notification);
        
        // 添加到数组
        this.notifications.unshift(notification);
        
        // 创建新通知元素
        const notificationElement = document.createElement('div');
        notificationElement.innerHTML = this.createNotificationElement(notification);
        const newNotification = notificationElement.firstElementChild;
        
        // 添加到容器
        if (this.container) {
            this.container.insertBefore(newNotification, this.container.firstChild);
            
            // 添加动画效果
            requestAnimationFrame(() => {
                newNotification.style.animation = 'slideInDown 0.5s ease forwards';
            });
        }
        
        // 如果是临时通知，设置自动删除
        if (notification.duration) {
            setTimeout(() => {
                this.removeNotification(notification.id);
            }, notification.duration);
        }
    }

    // 更新通知
    updateNotification(notification) {
        Logger.info('NotificationService', '更新通知:', notification);
        
        const index = this.notifications.findIndex(n => n.id === notification.id);
        if (index !== -1) {
            this.notifications[index] = notification;
            
            const element = this.container?.querySelector(`[data-id="${notification.id}"]`);
            if (element) {
                const newElement = document.createElement('div');
                newElement.innerHTML = this.createNotificationElement(notification);
                
                // 添加更新动画
                element.style.animation = 'fadeOut 0.3s ease forwards';
                setTimeout(() => {
                    element.replaceWith(newElement.firstElementChild);
                    newElement.firstElementChild.style.animation = 'fadeIn 0.3s ease forwards';
                }, 300);
            }
        }
    }

    // 删除通知
    removeNotification(id) {
        Logger.info('NotificationService', '删除通知:', id);
        
        const index = this.notifications.findIndex(n => n.id === id);
        if (index !== -1) {
            this.notifications.splice(index, 1);
            
            const element = this.container?.querySelector(`[data-id="${id}"]`);
            if (element) {
                // 添加删除动画
                element.style.animation = 'slideOutRight 0.5s ease forwards';
                setTimeout(() => {
                    element.remove();
                }, 500);
            }
        }
    }

    // 处理新通知
    handleNewNotification(data) {
        Logger.debug('NotificationService', '收到新通知:', data);
        this.addNotification(data);
    }

    // 处理通知更新
    handleNotificationUpdate(data) {
        Logger.debug('NotificationService', '收到通知更新:', data);
        this.updateNotification(data);
    }

    // 处理通知删除
    handleNotificationDelete(data) {
        Logger.debug('NotificationService', '收到通知删除:', data);
        this.removeNotification(data.id);
    }

    // 格式化时间
    formatTime(timestamp) {
        const now = new Date();
        const date = new Date(timestamp * 1000);
        const diff = now - date;
        
        // 一分钟内
        if (diff < 60000) {
            return '刚刚';
        }
        // 一小时内
        if (diff < 3600000) {
            return `${Math.floor(diff / 60000)}分钟前`;
        }
        // 今天内
        if (date.toDateString() === now.toDateString()) {
            return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        }
        // 昨天
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        if (date.toDateString() === yesterday.toDateString()) {
            return '昨天';
        }
        // 一周内
        if (diff < 604800000) {
            return `${Math.floor(diff / 86400000)}天前`;
        }
        // 其他
        return date.toLocaleDateString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit'
        });
    }

    // 清理资源
    destroy() {
        Logger.info('NotificationService', '清理通知服务资源');
        if (this.wsManager) {
            // this.wsManager.socket.off('notification:new');
            // this.wsManager.socket.off('notification:update');
            // this.wsManager.socket.off('notification:delete');
        }
        this.notifications = [];
        if (this.container) {
            this.container.innerHTML = '';
        }
    }
}

export default NotificationService; 