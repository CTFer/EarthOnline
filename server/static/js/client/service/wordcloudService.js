import Logger from '../../utils/logger.js';

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
        this.eventBus.on("task:completed", this.updateWordCloud.bind(this));
    }

    async initWordCloud(container) {
        Logger.info('WordcloudService', '开始初始化文字云');
        
        try {
            // 初始化 ECharts 实例
            this.wordCloudChart = echarts.init(container);
            
            // 模拟数据
            const testData = [
                // 头衔（较大字体，金色）
                { name: "尿不湿守护者", value: 100, textStyle: { color: "#ffd700", fontSize: 32 } },
                { name: "爬行先锋", value: 90, textStyle: { color: "#ffd700", fontSize: 28 } },

                // 荣誉（中等字体，银色）
                { name: "卫生纸摧毁达人", value: 80, textStyle: { color: "#c0c0c0" } },
                { name: "干饭小能手", value: 75, textStyle: { color: "#c0c0c0" } },
                { name: "玩具保护使者", value: 70, textStyle: { color: "#c0c0c0" } },

                // 个人标签（较小字体，青色系）
                { name: "热心干饭", value: 60, textStyle: { color: "#8aa2c1" } },
                { name: "推车出行", value: 55, textStyle: { color: "#8aa2c1" } },
                { name: "吃奶能手", value: 50, textStyle: { color: "#8aa2c1" } },
                { name: "植树达人", value: 45, textStyle: { color: "#8aa2c1" } },
                { name: "节水卫士", value: 40, textStyle: { color: "#8aa2c1" } },
                { name: "夜间嚎叫者", value: 35, textStyle: { color: "#8aa2c1" } },
                { name: "米粉爱好者", value: 30, textStyle: { color: "#8aa2c1" } },
            ];

            const option = {
                backgroundColor: "transparent",
                tooltip: {
                    show: true,
                    formatter: function (params) {
                        return params.data.name;
                    },
                },
                series: [
                    {
                        type: "wordCloud",
                        shape: "circle",
                        left: "center",
                        top: "center",
                        width: "100%",
                        height: "100%",
                        right: null,
                        bottom: null,
                        sizeRange: [16, 50],
                        rotationRange: [-45, 45],
                        rotationStep: 45,
                        gridSize: 8,
                        drawOutOfBound: false,
                        layoutAnimation: true,
                        textStyle: {
                            fontFamily: "Microsoft YaHei",
                            fontWeight: "bold",
                            color: function () {
                                return "rgb(" + [
                                    Math.round(Math.random() * 160) + 60,
                                    Math.round(Math.random() * 160) + 60,
                                    Math.round(Math.random() * 160) + 60
                                ].join(",") + ")";
                            },
                        },
                        emphasis: {
                            textStyle: {
                                shadowBlur: 10,
                                shadowColor: "rgba(255, 196, 71, 0.5)",
                            },
                        },
                        data: testData,
                    },
                ],
            };

            this.wordCloudChart.setOption(option);
            Logger.info('WordcloudService', '文字云初始化完成');
        } catch (error) {
            Logger.error('WordcloudService', '文字云初始化失败:', error);
        }
    }

    async updateWordCloud() {
        Logger.debug('WordcloudService', '开始更新文字云');
        try {
            const result = await this.api.getWordCloud();
            
            if (this.wordCloudChart && result.success) {
                this.wordCloudChart.setOption({
                    series: [{
                        data: result.data.tags
                    }]
                });
                Logger.info('WordcloudService', '文字云更新成功');
            }
        } catch (error) {
            Logger.error('WordcloudService', '更新文字云失败:', error);
            this.api.handleApiError(error, "updateWordCloud");
        }
    }

    destroy() {
        if (this.wordCloudChart) {
            this.wordCloudChart.dispose();
            this.wordCloudChart = null;
        }
        // 移除事件监听
        window.removeEventListener("resize", this.handleResize);
        this.eventBus.off("task:completed", this.updateWordCloud);
        Logger.info('WordcloudService', '文字云服务已销毁');
    }

    async getWordCloudData() {
        const playerId = this.playerService.getPlayerId();
        // ... 使用 playerId 的代码
    }
}

export default WordcloudService;
