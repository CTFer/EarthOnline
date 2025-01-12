// 工具函数
const gameUtils = {
    // 格式化剩余时间
    formatTimeRemaining(milliseconds) {
        if (milliseconds <= 0) {
            return '已结束';
        }
        
        const seconds = Math.floor(milliseconds / 1000);
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const remainingSeconds = seconds % 60;
        
        if (hours > 0) {
            return `${hours}小时${minutes}分钟`;
        } else if (minutes > 0) {
            return `${minutes}分钟${remainingSeconds}秒`;
        } else {
            return `${remainingSeconds}秒`;
        }
    },

    // 获取任务类型信息
    getTaskTypeInfo(typeId) {
        return TASK_TYPE_MAP[typeId] || {
            text: '未知类型',
            color: '#757575',
            icon: 'layui-icon-help'
        };
    },

    // 计算任务结束时间
    calculateTaskEndTime(task) {
        const now = new Date();
        if (task.task_type === '4') { // 每日任务
            const endTime = new Date();
            endTime.setHours(22, 0, 0, 0);
            return endTime;
        }
        return new Date(parseInt(task.endtime) * 1000);
    }
}; 