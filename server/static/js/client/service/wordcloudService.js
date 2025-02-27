import Logger from '../../utils/logger.js';
import { TASK_EVENTS } from '../config/events.js';


class WordcloudService {
    constructor(apiClient, eventBus, store, playerService) {
        this.api = apiClient;
        this.eventBus = eventBus;
        this.store = store;
        this.playerService = playerService;
        this.playerId = this.playerService.getPlayerId();
        this.playerData = null;
        this.wordCloudChart = null;
        
        // 订阅相关事件
        this.handleResize = this.handleResize.bind(this);
        this.setupEventListeners();
        Logger.info('WordcloudService', '初始化文字云服务');
    }

    handleResize() {
        if (this.wordCloudChart) {
            this.wordCloudChart.resize();
        }
    }

    setupEventListeners() {
        window.addEventListener("resize", this.handleResize);
        // 移除TASK_EVENTS.COMPLETED事件监听
        // this.eventBus.on(TASK_EVENTS.COMPLETED, this.updateWordCloud.bind(this));
    }

    /**
     * 将后端勋章数据转换为词云数据格式
     * @param {Array} medals - 后端返回的勋章数据
     * @returns {Array} - 转换后的词云数据
     */
    transformMedalsToWordCloudData(medals) {
        Logger.debug('转换勋章数据为词云格式', medals);
        
        return medals.map(([name, level]) => {  // 解构数组格式的勋章数据
            // 根据勋章等级设置不同的样式
            let textStyle = {};
            
            switch(level) {
                case 'gold':
                    textStyle = {
                        color: "#ffd700",  // 金色
                        fontSize: 32,       // 较大字号
                        fontWeight: 'bold'
                    };
                    break;
                case 'silver':
                    textStyle = {
                        color: "#c0c0c0",  // 银色
                        fontSize: 24        // 中等字号
                    };
                    break;
                default:
                    textStyle = {
                        color: "#8aa2c1",  // 青色
                        fontSize: 18        // 较小字号
                    };
            }

            return {
                name: name,                 // 勋章名称
                value: 50,                  // 默认权重
                textStyle: textStyle,       // 文字样式
                emphasis: {                 // 鼠标悬停效果
                    textStyle: {
                        color: '#ff9966'    // 悬停时的颜色
                    }
                }
            };
        });
    }

    /**
     * 初始化词云图表
     */
    async initWordCloud() {
        Logger.info('开始初始化文字云');
        
        try {
            // 获取词云容器
            const container = document.getElementById('wordCloudContainer');
            if (!container) {
                Logger.error('找不到词云容器元素');
                return;
            }

            // 初始化ECharts实例
            this.wordCloudChart = echarts.init(container);
            
            // 从后端获取勋章数据
            const response = await this.api.request('/api/wordcloud');
            if (response.code === 0 && response.data) {
                // 转换数据格式
                const wordCloudData = this.transformMedalsToWordCloudData(response.data);
                Logger.debug('转换后的词云数据', wordCloudData);
                // 设置词云配置项
                const option = {
                    tooltip: {
                        show: true
                    },
                    series: [{
                        type: 'wordCloud',
                        shape: 'circle',         // 词云形状
                        sizeRange: [12, 60],     // 字体大小范围
                        rotationRange: [-45, 45], // 旋转角度范围
                        gridSize: 8,             // 网格大小
                        drawOutOfBound: false,   // 是否允许词语超出边界
                        layoutAnimation: true,    // 启用布局动画
                        textStyle: {
                            fontFamily: 'sans-serif',
                            fontWeight: 'bold'
                        },
                        emphasis: {
                            focus: 'self'
                        },
                        data: wordCloudData
                    }]
                };

                // 应用配置
                this.wordCloudChart.setOption(option);
                Logger.info('文字云初始化完成');
            } else {
                Logger.error('获取勋章数据失败:', response.msg);
            }
        } catch (error) {
            Logger.error('初始化文字云失败:', error);
        }
    }

    /**
     * 更新词云数据
     */
    async updateWordCloud() {
        Logger.debug('开始更新文字云');
        
        try {
            if (!this.wordCloudChart) {
                await this.initWordCloud();
                return;
            }

            const response = await this.api.get('/api/wordcloud');
            if (response.code === 0 && response.data) {
                const wordCloudData = this.transformMedalsToWordCloudData(response.data);
                this.wordCloudChart.setOption({
                    series: [{
                        data: wordCloudData
                    }]
                });
                Logger.debug('文字云更新完成');
            }
        } catch (error) {
            Logger.error('更新文字云失败:', error);
        }
    }

    destroy() {
        if (this.wordCloudChart) {
            this.wordCloudChart.dispose();
            this.wordCloudChart = null;
        }
        // 移除事件监听
        window.removeEventListener("resize", this.handleResize);
        // this.eventBus.off("task:completed", this.updateWordCloud);
        Logger.info('WordcloudService', '文字云服务已销毁');
    }

    async getWordCloudData() {
        const playerId = this.playerService.getPlayerId();
        // ... 使用 playerId 的代码
    }
}

export default WordcloudService;
