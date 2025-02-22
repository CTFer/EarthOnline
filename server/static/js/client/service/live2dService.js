/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 11:24:25
 * @LastEditTime: 2025-02-22 17:33:12
 * @LastEditors: 一根鱼骨棒
 * @Description: Live2D服务
 */
import Logger from "../../utils/logger.js";
import { Live2D_MODE, Character_image } from "../../config/config.js";
import { UI_EVENTS } from '../config/events.js';

class Live2DService {
    constructor(eventBus) {
        // 基础属性初始化
        this.app = null;
        this.model = null;
        this.motionInterval = null;
        this.resizeHandler = null;
        this.live2dContainer = null;
        this.initialized = false;
        
        // 确保eventBus被正确传入和保存
        if (!eventBus) {
            Logger.error('Live2DService', '初始化失败: eventBus 未提供');
            throw new Error('EventBus is required for Live2DService');
        }
        this.eventBus = eventBus;
        
        Logger.info('Live2DService', '初始化Live2D服务');
    }

    /**
     * 初始化Live2D服务
     */
    async initialize() {
        Logger.info('Live2DService', '开始初始化Live2D模型');
        try {
            // 获取容器
            const container = document.getElementById('live2dContainer');
            if (!container) {
                Logger.error('Live2DService', '找不到Live2D容器');
                throw new Error('Live2D container not found');
            }
            this.live2dContainer = container;

            // 清理旧的内容
            this.cleanupOldCanvas();

            // 根据模式选择初始化方法
            if (Live2D_MODE) {
                // Live2D模式
                // 加载Live2D资源
                await this.loadLive2DResources();
                
                // 检查必要的库是否加载
                await this.checkLibrariesLoaded();
                
                // 初始化Live2D
                await this.initializeLive2D();
            } else {
                // 图片模式
                await this.initializeImage();
            }

            this.initialized = true;
            Logger.info('Live2DService', `${Live2D_MODE ? 'Live2D模型' : '图片模式'}初始化完成`);
            
            // 发送初始化成功事件
            if (this.eventBus) {
                this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                    type: 'SUCCESS',
                    message: `${Live2D_MODE ? 'Live2D模型' : '图片'}加载成功`
                });
            }
        } catch (error) {
            Logger.error('Live2DService', '初始化失败:', error);
            if (this.eventBus) {
                this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                    type: 'ERROR',
                    message: `${Live2D_MODE ? 'Live2D模型' : '图片'}加载失败: ${error.message}`
                });
            }
            throw error;
        }
    }

    /**
     * 检查必要的库是否加载
     */
    async checkLibrariesLoaded() {
        Logger.debug('Live2DService', '开始检查库加载状态');
        
        // 增加等待时间，确保脚本完全初始化
        for (let i = 0; i < 3; i++) {
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            try {
                if (typeof PIXI === 'undefined') {
                    Logger.warn('Live2DService', `第${i + 1}次检查: PIXI库未加载`);
                    continue;
                }
                
                if (typeof Live2DModel === 'undefined') {
                    Logger.warn('Live2DService', `第${i + 1}次检查: Live2DModel未加载`);
                    continue;
                }
                
                // 如果都加载成功，立即返回
                Logger.debug('Live2DService', '所有必要的库加载成功');
                return;
            } catch (error) {
                Logger.warn('Live2DService', `第${i + 1}次检查失败:`, error);
            }
        }
        
        // 如果经过多次尝试后仍未加载成功，抛出错误
        if (typeof PIXI === 'undefined') {
            Logger.error('Live2DService', 'PIXI库未加载');
            throw new Error('PIXI库未加载');
        }
        
        if (typeof Live2DModel === 'undefined') {
            Logger.error('Live2DService', 'Live2DModel未加载');
            throw new Error('Live2DModel未加载');
        }
    }

    /**
     * 初始化Live2D模型
     */
    async initializeLive2D() {
        Logger.info('Live2DService', '初始化Live2D模型');

        try {
            // 初始化PIXI应用
            const app = new PIXI.Application({
                width: 280,
                height: 250,
                transparent: true,
                autoStart: true
            });

            this.live2dContainer.appendChild(app.view);

            // 加载模型
            Logger.debug('Live2DService', '开始加载模型文件');
            const model = await Live2DModel.from('/static/models/boy/boy.model3.json');
            // const model = await PIXI.live2d.Live2DModel.from("/static/models/boy/boy.model3.json");
            Logger.debug('Live2DService', '模型文件加载成功');
            
            app.stage.addChild(model);

            // 设置模型位置和缩放
            model.scale.set(0.2);
            model.position.set(140, 225);

            this.model = model;
            this.app = app;

            // 设置模型交互
            this.setupInteractions();
            // 设置随机动作
            this.setupRandomMotions();
            // 设置窗口大小变化处理
            this.setupResizeHandler();

            Logger.info('Live2DService', 'Live2D模型初始化完成');
        } catch (error) {
            Logger.error('Live2DService', 'Live2D模型加载失败:', error);
            throw error;
        }
    }

    /**
     * 初始化图片模式
     */
    async initializeImage() {
        Logger.info('Live2DService', '初始化图片模式');
        try {
            const playerId = localStorage.getItem('playerId');
            if (!playerId || !Character_image[playerId]) {
                Logger.error('Live2DService', '找不到角色图片配置');
                return;
            }

            const img = new Image();
            img.src = Character_image[playerId];

            // 等待图片加载完成
            await new Promise((resolve, reject) => {
                img.onload = resolve;
                img.onerror = reject;
            });

            // 清理容器
            this.live2dContainer.innerHTML = '';
            
            // 设置图片样式
            img.style.width = '100%';
            img.style.height = 'auto';
            img.style.objectFit = 'contain';
            img.style.display = 'block';
            
            this.live2dContainer.appendChild(img);

            this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
                type: 'SUCCESS',
                message: '角色图片加载成功'
            });
        } catch (error) {
            Logger.error('Live2DService', '图片加载失败:', error);
            throw error;
        }
    }

    /**
     * 清理旧的Canvas
     */
    cleanupOldCanvas() {
        const oldCanvas = document.querySelector("#live2dContainer canvas");
        if (oldCanvas) {
            oldCanvas.remove();
        }
    }

    /**
     * 加载Live2D脚本
     */
    async loadLive2DResources() {
        Logger.info('Live2DService', '开始加载Live2D资源');
        const live2dScripts = [
            "/static/js/live2d/live2d.min.js",
            "/static/js/live2d/live2dcubismcore.min.js",
            "/static/js/live2d/pixi.min.js",
            "/static/js/live2d/utils.min.js",
            "/static/js/live2d/math.min.js",
            "/static/js/live2d/index.min.js"
        ];

        try {
            // 检查是否已经加载了所需的库
            if (typeof PIXI !== 'undefined' && typeof Live2DModel !== 'undefined') {
                Logger.debug('Live2DService', '所需库已加载，跳过脚本加载');
                return;
            }

            // 按顺序加载脚本
            for (const script of live2dScripts) {
                Logger.debug('Live2DService', `正在加载脚本: ${script}`);
                await this.loadScript(script);
                Logger.debug('Live2DService', `脚本加载成功: ${script}`);
            }

            // 等待一段时间确保脚本完全初始化
            await new Promise(resolve => setTimeout(resolve, 500));

            // 检查库是否加载成功
            await this.checkLibrariesLoaded();
            Logger.info("Live2DService", "Live2D脚本加载完成");
        } catch (error) {
            Logger.error("Live2DService", "Live2D脚本加载失败:", error);
            throw error;
        }
    }

    /**
     * 加载单个脚本
     */
    loadScript(src) {
        return new Promise((resolve, reject) => {
            try {
                // 检查脚本是否已经加载
                const existingScript = document.querySelector(`script[src="${src}"]`);
                if (existingScript) {
                    Logger.debug('Live2DService', `脚本已存在: ${src}`);
                    resolve();
                    return;
                }

                const script = document.createElement("script");
                script.src = src;
                script.async = false; // 确保按顺序加载
                
                script.onload = () => {
                    Logger.debug('Live2DService', `脚本加载成功: ${src}`);
                    resolve();
                };
                
                script.onerror = (error) => {
                    Logger.error('Live2DService', `脚本加载失败: ${src}`, error);
                    reject(new Error(`Failed to load script: ${src}`));
                };
                
                document.head.appendChild(script);
            } catch (error) {
                Logger.error('Live2DService', `创建脚本标签失败: ${src}`, error);
                reject(error);
            }
        });
    }

    /**
     * 设置模型位置和大小
     */
    setupModel(containerWidth, containerHeight) {
        const scaleX = containerWidth / this.model.width;
        const scaleY = containerHeight / this.model.height;
        const scale = Math.min(scaleX, scaleY) * 0.9;

        this.model.anchor.set(0.5, 0.5);
        this.model.scale.set(scale);
        this.model.x = containerWidth / 2;
        this.model.y = containerHeight / 2;

        this.app.stage.removeChildren();
        this.app.stage.addChild(this.model);
    }

    /**
     * 设置模型交互
     */
    setupInteractions() {
        this.model.on("hit", (hitAreas) => {
            if (hitAreas.includes("body")) {
                this.model.motion("tap_body");
            }
        });
    }

    /**
     * 设置随机动作
     */
    setupRandomMotions() {
        this.motionInterval = setInterval(() => {
            const motions = ["idle", "tap_body", "flick_head"];
            const randomMotion = motions[Math.floor(Math.random() * motions.length)];
            this.model.motion(randomMotion);
        }, 5000);
    }

    /**
     * 设置窗口大小变化处理
     */
    setupResizeHandler() {
        this.resizeHandler = () => {
            const newRect = this.live2dContainer.getBoundingClientRect();
            const newWidth = newRect.width;
            const newHeight = newRect.height;

            this.app.renderer.resize(newWidth, newHeight);
            this.setupModel(newWidth, newHeight);
        };

        window.addEventListener("resize", this.resizeHandler);
    }

    /**
     * 清理资源
     */
    cleanup() {
        Logger.info('Live2DService', '开始清理资源');
        
        if (this.resizeHandler) {
            window.removeEventListener("resize", this.resizeHandler);
            this.resizeHandler = null;
        }

        if (this.motionInterval) {
            clearInterval(this.motionInterval);
            this.motionInterval = null;
        }

        if (this.app) {
            this.app.destroy(true, {
                children: true,
                texture: true,
                baseTexture: true,
            });
            this.app = null;
        }

        if (this.live2dContainer) {
            this.live2dContainer.innerHTML = '';
        }

        this.model = null;
        Logger.info('Live2DService', '资源清理完成');
    }

    destroy() {
        Logger.info('Live2DService', '销毁Live2D服务');
        this.cleanup();
        this.initialized = false;
    }
}

export default Live2DService; 