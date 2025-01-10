/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-08 11:24:25
 * @LastEditTime: 2025-01-09 10:43:39
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
// Live2D 模型配置和初始化
window.addEventListener('DOMContentLoaded', async () => {
    try {
        // 清理之前的WebGL上下文
        const oldCanvas = document.querySelector('#live2dContainer canvas');
        if (oldCanvas) {
            oldCanvas.remove();
        }

        // 等待确保所有依赖项都已加载
        await new Promise(resolve => setTimeout(resolve, 1000));

        if (!window.PIXI || !window.Live2D) {
            throw new Error('Live2D依赖项未加载完成');
        }

        // 创建画布容器
        const live2dContainer = document.getElementById('live2dContainer');
        
        // 获取容器尺寸
        const containerRect = live2dContainer.getBoundingClientRect();
        const containerWidth = containerRect.width;
        const containerHeight = containerRect.height;

        // 创建PIXI应用，添加WebGL选项
        const app = new PIXI.Application({
            width: containerWidth,
            height: containerHeight,
            transparent: true,
            antialias: true,
            preserveDrawingBuffer: true,
            powerPreference: 'high-performance',
            backgroundColor: 0x00000000
        });
        
        // 清理容器
        live2dContainer.innerHTML = '';
        live2dContainer.appendChild(app.view);

        // 加载模型
        const model = await PIXI.live2d.Live2DModel.from('models/boy/boy.model3.json');

        // 计算适当的缩放比例
        const scaleX = containerWidth / model.width;
        const scaleY = containerHeight / model.height;
        const scale = Math.min(scaleX, scaleY) * 0.9; // 缩小10%以留出边距

        // 设置模型位置和大小
        model.anchor.set(0.5, 0.5);
        model.scale.set(scale);
        model.x = containerWidth / 2;
        model.y = containerHeight / 2;

        // 添加到舞台前清理
        app.stage.removeChildren();
        app.stage.addChild(model);

        // 添加交互效果
        model.on('hit', (hitAreas) => {
            if (hitAreas.includes('body')) {
                model.motion('tap_body');
            }
        });

        // 随机动作
        let motionInterval = setInterval(() => {
            const motions = ['idle', 'tap_body', 'flick_head'];
            const randomMotion = motions[Math.floor(Math.random() * motions.length)];
            model.motion(randomMotion);
        }, 5000);

        // 响应窗口大小变化
        const resizeHandler = () => {
            const newRect = live2dContainer.getBoundingClientRect();
            const newWidth = newRect.width;
            const newHeight = newRect.height;
            
            app.renderer.resize(newWidth, newHeight);
            
            // 重新计算缩放比例
            const newScaleX = newWidth / model.width;
            const newScaleY = newHeight / model.height;
            const newScale = Math.min(newScaleX, newScaleY) * 0.9;
            
            model.scale.set(newScale);
            model.x = newWidth / 2;
            model.y = newHeight / 2;
        };

        // 添加窗口大小变化监听
        window.addEventListener('resize', resizeHandler);

        // 清理函数
        const cleanup = () => {
            window.removeEventListener('resize', resizeHandler);
            clearInterval(motionInterval);
            app.destroy(true, {
                children: true,
                texture: true,
                baseTexture: true
            });
        };

        // 在页面卸载时清理资源
        window.addEventListener('unload', cleanup);

        console.log('Live2D初始化成功');

    } catch (error) {
        console.error('Live2D初始化失败:', error);
    }
}); 