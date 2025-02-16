/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 13:47:39
 * @LastEditTime: 2025-02-15 13:53:12
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 */
import Logger from '../../utils/logger.js';

class UIService {
    constructor(eventBus, store, templateService) {
        this.eventBus = eventBus;
        this.store = store;
        this.templateService = templateService;
        this.observers = new Map();
        Logger.info('UIService', '初始化UI服务');
    }

    setupDOMObserver() {
        Logger.debug('UIService', '设置DOM观察器');
        // DOM观察器逻辑
    }

    updateTaskList(tasks) {
        Logger.debug('UIService', '更新任务列表UI');
        // 任务列表更新逻辑
    }

    /**
     * 显示任务详情
     * @param {Object} taskData 任务数据
     */
    showTaskDetails(taskData) {
        Logger.debug('UIService', '显示任务详情:', taskData);
        
        try {
            // 解析任务奖励
            const rewards = this.templateService.parseTaskRewards(taskData.task_rewards);
            
            // 构建详情内容
            const content = `
                <div class="task-detail-popup">
                    <div class="task-header ${taskData.typeInfo?.class || ''}">
                        <div class="task-type">
                            <i class="layui-icon ${taskData.typeInfo?.icon}"></i>
                            <span>${taskData.typeInfo?.text || '普通任务'}</span>
                        </div>
                        <h3>${taskData.name}</h3>
                    </div>
                    <div class="task-content">
                        <div class="description">${taskData.description}</div>
                        <div class="rewards-section">
                            <h4>任务奖励</h4>
                            <div class="rewards-list">
                                ${this._renderRewardsDetail(rewards)}
                            </div>
                        </div>
                        <div class="stamina-cost">
                            <i class="layui-icon layui-icon-fire"></i>
                            <span>消耗体力: ${taskData.stamina_cost}</span>
                        </div>
                    </div>
                </div>`;

            // 使用 layer 弹窗显示
            layer.open({
                type: 1,
                title: false,
                closeBtn: true,
                shadeClose: true,
                skin: 'task-detail-layer',
                area: ['420px', 'auto'],
                content: content,
                success: () => {
                    Logger.debug('UIService', '任务详情弹窗打开成功');
                }
            });
        } catch (error) {
            Logger.error('UIService', '显示任务详情失败:', error);
            this.showNotification('显示任务详情失败', 'error');
        }
    }

    /**
     * 显示通知消息
     * @param {Object|string} data 通知数据或消息文本
     * @param {string} type 通知类型
     */
    showNotification(data, type = 'info') {
        Logger.debug('UIService', '显示通知:', data);
        
        try {
            let message, icon;
            
            // 处理不同的输入格式
            if (typeof data === 'string') {
                message = data;
            } else {
                message = data.message || '未知消息';
                type = data.type?.toLowerCase() || type;
            }

            // 根据类型设置图标
            switch (type.toUpperCase()) {
                case 'SUCCESS':
                case 'COMPLETE':
                    icon = 1;
                    break;
                case 'ERROR':
                case 'REJECT':
                    icon = 2;
                    break;
                case 'WARNING':
                case 'CHECKING':
                    icon = 3;
                    break;
                default:
                    icon = -1;
            }

            // 使用 layer 显示通知
            layer.msg(message, {
                icon: icon,
                offset: 't',
                anim: 6
            });

            // 发送通知事件
            this.eventBus.emit('ui:notification', { message, type });
        } catch (error) {
            Logger.error('UIService', '显示通知失败:', error);
            // 使用原生alert作为后备方案
            alert(typeof data === 'string' ? data : data.message || '发生错误');
        }
    }

    /**
     * 渲染奖励详情
     * @private
     */
    _renderRewardsDetail(rewards) {
        let html = '';
        
        if (rewards.exp > 0) {
            html += `
                <div class="reward-item">
                    <i class="layui-icon layui-icon-star"></i>
                    <span>经验值 +${rewards.exp}</span>
                </div>`;
        }
        
        if (rewards.points > 0) {
            html += `
                <div class="reward-item">
                    <i class="layui-icon layui-icon-diamond"></i>
                    <span>积分 +${rewards.points}</span>
                </div>`;
        }
        
        if (rewards.cards.length > 0) {
            rewards.cards.forEach(card => {
                html += `
                    <div class="reward-item">
                        <i class="layui-icon layui-icon-template"></i>
                        <span>${card.name} x${card.number}</span>
                    </div>`;
            });
        }
        
        if (rewards.medals.length > 0) {
            rewards.medals.forEach(medal => {
                html += `
                    <div class="reward-item">
                        <i class="layui-icon layui-icon-medal"></i>
                        <span>${medal.name}</span>
                    </div>`;
            });
        }
        
        return html || '<div class="no-rewards">无奖励</div>';
    }

    renderTaskList(tasks) {
        Logger.info('UIService', '开始渲染任务列表，任务数量:', tasks.length);

        const container = document.querySelector('.task-list-swiper .swiper-wrapper');
        if (!container) {
            Logger.error('UIService', '找不到任务列表容器');
            return;
        }

        try {
            if (!tasks || !tasks.length) {
                container.innerHTML = this.getEmptyTaskTemplate();
            } else {
                container.innerHTML = tasks.map(task => 
                    this.templateService.getAvailableTaskTemplate(task)
                ).join('');
            }

            // 发送渲染完成事件
            this.eventBus.emit('ui:taskList:rendered');
            Logger.debug('UIService', '任务列表渲染完成');
        } catch (error) {
            Logger.error('UIService', '渲染任务列表失败:', error);
            container.innerHTML = this.getErrorTemplate(error.message);
        }
    }

    getEmptyTaskTemplate() {
        return `
            <div class="swiper-slide">
                <div class="empty-task">暂无可用任务</div>
            </div>`;
    }

    getErrorTemplate(message) {
        return `
            <div class="swiper-slide">
                <div class="error-task">加载任务失败: ${message}</div>
            </div>`;
    }

    // ... 其他UI相关方法
}

export default UIService; 