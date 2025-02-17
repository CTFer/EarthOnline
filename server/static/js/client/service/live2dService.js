/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 11:24:25
 * @LastEditTime: 2025-02-17 15:00:20
 * @LastEditors: 一根鱼骨棒
 * @Description: Live2D服务
 */
import Logger from "../../utils/logger.js";
import { Live2D_MODE, Character_image } from "../../config/config.js";

class Live2DService {
    constructor() {
        this.app = null;
        this.model = null;
        this.motionInterval = null;
        this.resizeHandler = null;
        this.live2dContainer = null;
        Logger.info('Live2DService', '初始化Live2D服务');
    }

    /**
     * 初始化Live2D服务
     */
    async initialize() {
        try {
            // 清理之前的WebGL上下文
            this.cleanupOldCanvas();

            // 等待确保所有依赖项都已加载
            await new Promise((resolve) => setTimeout(resolve, 1000));

            this.live2dContainer = document.getElementById("live2dContainer");
            if (!this.live2dContainer) {
                throw new Error("找不到Live2D容器");
            }

            const containerRect = this.live2dContainer.getBoundingClientRect();
            const containerWidth = containerRect.width;
            const containerHeight = containerRect.height;

            if (Live2D_MODE) {
                await this.initializeLive2D(containerWidth, containerHeight);
            } else {
                await this.initializeImage(containerWidth, containerHeight);
            }

            Logger.info('Live2DService', '初始化成功');
        } catch (error) {
            Logger.error('Live2DService', '初始化失败:', error);
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
        const live2dScripts = [
            "/static/js/live2d/live2d.min.js",
            "/static/js/live2d/live2dcubismcore.min.js",
            "/static/js/live2d/pixi.min.js",
            "/static/js/live2d/utils.min.js",
            "/static/js/live2d/math.min.js",
            "/static/js/live2d/index.min.js"
        ];

        try {
            for (const script of live2dScripts) {
                await this.loadScript(script);
            }
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
            const script = document.createElement("script");
            script.src = src;
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    /**
     * 初始化Live2D模式
     */
    async initializeLive2D(containerWidth, containerHeight) {
        await this.loadLive2DResources();

        if (!window.PIXI || !window.Live2D) {
            throw new Error('Live2D依赖项未加载完成');
        }

        // 创建PIXI应用
        this.app = new PIXI.Application({
            width: containerWidth,
            height: containerHeight,
            transparent: true,
            antialias: true,
            preserveDrawingBuffer: true,
            powerPreference: "high-performance",
            backgroundColor: 0x00000000,
        });

        // 清理容器并添加canvas
        this.live2dContainer.innerHTML = "";
        this.live2dContainer.appendChild(this.app.view);

        // 加载模型
        this.model = await PIXI.live2d.Live2DModel.from("/static/models/boy/boy.model3.json");

        // 设置模型位置和大小
        this.setupModel(containerWidth, containerHeight);

        // 设置交互和动画
        this.setupInteractions();
        this.setupRandomMotions();
        this.setupResizeHandler();

        // 设置清理事件
        window.addEventListener("unload", this.cleanup.bind(this));
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
     * 初始化图片模式
     */
    async initializeImage(containerWidth, containerHeight) {
        const img = new Image();
        img.src = Character_image[localStorage.getItem("playerId")];
        
        await new Promise((resolve, reject) => {
            img.onload = resolve;
            img.onerror = reject;
        });

        this.live2dContainer.innerHTML = "";
        
        // 设置图片样式
        img.style.width = '100%';
        img.style.height = 'auto';
        img.style.objectFit = 'contain';
        img.style.display = 'block';
        
        this.live2dContainer.appendChild(img);
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

        this.model = null;
        Logger.info('Live2DService', '资源清理完成');
    }
}

export default Live2DService; 