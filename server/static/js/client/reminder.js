/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-19 20:06:58
 * @LastEditTime: 2025-02-20 13:55:05
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */

/**
 * 提词器功能模块
 * @author 一根鱼骨棒
 * @description 实现提词器的文本滚动和控制功能
 */

layui.use(['layer', 'form', 'jquery'], function() {
    const layer = layui.layer;
    const form = layui.form;
    const $ = layui.jquery;
    
    /**
     * 将十六进制颜色转换为RGB对象
     * @param {string} hex - 十六进制颜色值
     * @returns {Object} RGB颜色对象
     */
    function hexToRgb(hex) {
        // 移除#号
        hex = hex.replace('#', '');
        
        // 将3位颜色转换为6位
        if (hex.length === 3) {
            hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2];
        }
        
        // 解析RGB值
        const r = parseInt(hex.substring(0, 2), 16);
        const g = parseInt(hex.substring(2, 4), 16);
        const b = parseInt(hex.substring(4, 6), 16);
        
        return { r, g, b };
    }

    // 预定义的颜色选项
    const COLOR_OPTIONS = {
        text: [
            { name: '白色', value: '#FFFFFF' },
            { name: '黑色', value: '#000000' },
            { name: '浅灰', value: '#CCCCCC' },
            { name: '深灰', value: '#666666' },
            { name: '黄色', value: '#FFD700' },
            { name: '绿色', value: '#90EE90' }
        ],
        background: [
            { name: '黑色', value: '#000000' },
            { name: '深蓝', value: '#1A1A2E' },
            { name: '深灰', value: '#333333' },
            { name: '深棕', value: '#2C1810' },
            { name: '深绿', value: '#1A2F1A' },
            { name: '深紫', value: '#2E1A2E' }
        ]
    };
    
    // 获取DOM元素
    const textInput = document.getElementById('textInput');
    const scrollSpeed = document.getElementById('scrollSpeed');
    const lineHeight = document.getElementById('lineHeight');
    const letterSpacing = document.getElementById('letterSpacing');
    const textColor = document.getElementById('textColor');
    const fontSize = document.getElementById('fontSize');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const fullscreenDisplay = document.querySelector('.fullscreen-display');
    const scrollText = document.querySelector('.scroll-text');
    const exitFullscreenBtn = document.getElementById('exitFullscreen');
    const saveTextBtn = document.getElementById('saveText');
    const clearHistoryBtn = document.getElementById('clearHistory');
    const historyList = document.getElementById('historyList');
    const textLangRadios = document.getElementsByName('textLang');
    
    // 全屏控制元素
    const fullscreenSettings = document.getElementById('fullscreenSettings');
    const fullscreenSpeed = document.getElementById('fullscreenSpeed');
    const fullscreenFontSize = document.getElementById('fullscreenFontSize');
    const fullscreenLineHeight = document.getElementById('fullscreenLineHeight');
    const fullscreenLetterSpacing = document.getElementById('fullscreenLetterSpacing');
    const speedIndicator = document.getElementById('speedIndicator');
    const fullscreenControls = document.getElementById('fullscreenControls');
    const toggleSettingsBtn = document.getElementById('toggleSettings');
    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    
    // 动画状态
    let isScrolling = false;
    let isPaused = false;
    let animationDuration = 0;
    let scrollStartTime = 0;
    let scrollProgress = 0;
    let currentTransform = 0;
    
    // 本地存储键名
    const STORAGE_KEYS = {
        HISTORY: 'reminder_history',
        CONFIG: 'reminder_config',
        CURRENT_TEXT: 'reminder_current_text'
    };
    
    // 速度描述映射
    const SPEED_DESCRIPTIONS = {
        1: '极慢',
        2: '很慢',
        3: '慢速',
        4: '较慢',
        5: '正常',
        6: '较快',
        7: '快速',
        8: '很快',
        9: '极快',
        10: '最快'
    };
    
    // 新变量
    let countdownTimer = null;
    let focusAreaEnabled = false;
    let focusAreaSize = 3;
    let mirrorMode = false;      // 镜像模式
    let focusAreaUpdateInterval = null;

    // 获取新增的DOM元素
    const bgColor = document.getElementById('bgColor');
    const focusAreaEnabledInput = document.getElementById('focusAreaEnabled');
    const focusAreaSizeInput = document.getElementById('focusAreaSize');
    const focusAreaSettingsDiv = document.getElementById('focusAreaSettings');
    const mirrorTextInput = document.getElementById('mirrorText');
    
    // 获取保存配置按钮
    const saveConfigBtn = document.getElementById('saveConfigBtn');
    
    // 获取全屏设置元素
    const fullscreenFocusAreaEnabled = document.getElementById('fullscreenFocusAreaEnabled');
    const fullscreenFocusAreaSize = document.getElementById('fullscreenFocusAreaSize');
    const fullscreenFocusAreaSettings = document.getElementById('fullscreenFocusAreaSettings');
    const fullscreenMirrorText = document.getElementById('fullscreenMirrorText');
    
    // 获取清空文本按钮
    const clearTextBtn = document.getElementById('clearText');
    
    // 将saveTimeout声明移到全局作用域
    let saveTimeout = null;
    
    // 获取滑动条元素
    const fontSizeSlider = document.getElementById('fontSizeSlider');
    const scrollSpeedSlider = document.getElementById('scrollSpeedSlider');
    const lineHeightSlider = document.getElementById('lineHeightSlider');
    const letterSpacingSlider = document.getElementById('letterSpacingSlider');
    
    /**
     * 调试日志输出
     * @param {string} message - 日志信息
     * @param {any} data - 相关数据
     */
    function debugLog(message, data = null) {
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[提词器] ${timestamp} ${message}`);
        if (data !== null) {
            console.log(data);
        }
    }
    
    /**
     * 更新速度显示
     * @param {number} speed - 速度值
     */
    function updateSpeedValue(speed) {
        try {
            // 获取速度显示元素
            const speedValueEl = fullscreenSettings.querySelector('.speed-value');
            const speedIndicatorEl = document.getElementById('speedIndicator');
            
            // 将0-100的速度映射到0-10的显示范围
            const displaySpeed = (speed / 10).toFixed(1);
            
            // 更新全屏设置面板中的速度值
            if (speedValueEl) {
                speedValueEl.textContent = `${displaySpeed}x`;
            }
            
            // 更新速度指示器
            if (speedIndicatorEl) {
                speedIndicatorEl.textContent = `${displaySpeed}x`;
                speedIndicatorEl.style.display = 'block';
                // 2秒后隐藏速度指示器
                setTimeout(() => {
                    speedIndicatorEl.style.display = 'none';
                }, 2000);
            }
            
            debugLog('更新速度显示', { speed, displaySpeed });
        } catch (error) {
            console.error('更新速度显示失败:', error);
            debugLog('更新速度显示失败', { error });
        }
    }
    
    /**
     * 计算滚动时间
     * @param {number} textLength - 文本长度
     * @param {number} speed - 速度值（0-100）
     * @returns {number} 滚动时间（毫秒）
     */
    function calculateScrollDuration(textLength, speed) {
        // 防止除以零
        if (speed === 0) {
            return Number.MAX_SAFE_INTEGER; // 速度为0时，返回最大值（实际上就是不滚动）
        }
        
        // 基础滚动时间（每个字符的基准时间）
        const baseTimePerChar = 200; // 200ms per character
        
        // 速度系数：将0-100的速度映射到0.1-4的系数范围（原来是0.1-2）
        // 速度越大，系数越大，时间越短
        const speedFactor = 0.1 + (speed / 100) * 5.9;
        
        // 计算总时间
        const duration = (textLength * baseTimePerChar) / speedFactor;
        
        debugLog('计算滚动时间', {
            textLength,
            speed,
            speedFactor,
            duration,
            durationInSeconds: duration / 1000
        });
        
        return duration;
    }
    
    /**
     * 更新进度条
     * @param {number} progress - 进度值（0-1）
     */
    function updateProgressBar(progress) {
        const progressBar = document.querySelector('.progress-bar .progress');
        if (progressBar) {
            progressBar.style.width = `${progress * 100}%`;
        }
    }
    
    /**
     * 更新滚动进度
     * @param {number} progress - 进度值（0-1）
     */
    function updateScrollProgress(progress) {
        if (!isScrolling) return;
        
        try {
            // 确保进度值在0-1之间
            progress = Math.max(0, Math.min(1, progress));
            
            // 暂停当前动画
            scrollText.style.transition = 'none';
            
            // 计算新的位置
            const totalDistance = scrollText.offsetHeight;
            const viewportHeight = window.innerHeight;
            const startPosition = viewportHeight / 2;
            const maxScroll = totalDistance + startPosition;
            
            // 计算目标位置（删除翻转方向相关代码）
            const targetPosition = startPosition - (progress * totalDistance);
            
            // 应用新位置和镜像效果
            const transform = `translateY(${targetPosition}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
            scrollText.style.transform = transform;
            
            // 更新进度条
            updateProgressBar(progress);
            
            // 如果不是暂停状态，继续动画
            if (!isPaused) {
                requestAnimationFrame(() => {
                    // 计算剩余距离和时间
                    const remainingDistance = maxScroll - Math.abs(startPosition - targetPosition);
                    const remainingTime = (remainingDistance / maxScroll) * animationDuration;
                    
                    // 设置过渡动画
                    scrollText.style.transition = `transform ${remainingTime}ms linear`;
                    
                    // 计算最终位置（删除翻转方向相关代码）
                    const finalPosition = -maxScroll + startPosition;
                    const finalTransform = `translateY(${finalPosition}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
                    scrollText.style.transform = finalTransform;
                    
                    // 更新进度条动画
                    let startTime = performance.now();
                    function updateProgress() {
                        if (!isScrolling || isPaused) return;
                        
                        const currentTime = performance.now();
                        const elapsed = currentTime - startTime;
                        const newProgress = Math.min(progress + (elapsed / remainingTime) * (1 - progress), 1);
                        
                        updateProgressBar(newProgress);
                        
                        if (newProgress < 1) {
                            requestAnimationFrame(updateProgress);
                        }
                    }
                    updateProgress();
                });
            }
            
            debugLog('更新滚动进度', { 
                progress, 
                targetPosition,
                mirrorMode
            });
        } catch (error) {
            console.error('更新滚动进度失败:', error);
            debugLog('更新滚动进度失败', { error });
        }
    }
    
    /**
     * 更新滚动速度
     * @param {number} speed - 速度值（0-100）
     */
    function updateScrollSpeed(speed) {
        if (!isScrolling) return;
        debugLog('开始更新滚动速度', { speed });
        
        try {
            // 保存当前进度
            const computedStyle = window.getComputedStyle(scrollText);
            const matrix = new WebKitCSSMatrix(computedStyle.transform);
            const currentY = matrix.m42;
            const viewportHeight = window.innerHeight;
            const startPosition = viewportHeight / 2;
            const totalDistance = scrollText.offsetHeight;
            const maxScroll = totalDistance + startPosition;
            const progress = Math.abs(startPosition - currentY) / maxScroll;
            
            debugLog('当前滚动状态', {
                currentY,
                totalDistance,
                maxScroll,
                progress: progress.toFixed(3)
            });
            
            // 计算新的动画时间
            const textLength = textInput.value.length;
            animationDuration = calculateScrollDuration(textLength, speed);
            
            // 计算剩余时间和距离
            const remainingDistance = maxScroll - Math.abs(startPosition - currentY);
            const remainingTime = (remainingDistance / maxScroll) * animationDuration;
            
            debugLog('更新动画参数', {
                remainingDistance,
                remainingTime,
                animationDuration
            });
            
            // 暂停当前动画
            scrollText.style.transition = 'none';
            scrollText.style.transform = `translateY(${currentY}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
            
            // 重新开始动画
            requestAnimationFrame(() => {
                scrollText.style.transition = `transform ${remainingTime}ms linear`;
                scrollText.style.transform = `translateY(-${maxScroll}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
                
                // 更新进度条动画
                let startTime = performance.now();
                function updateProgress() {
                    if (!isScrolling || isPaused) return;
                    
                    const currentTime = performance.now();
                    const elapsed = currentTime - startTime;
                    const newProgress = Math.min(progress + (elapsed / remainingTime) * (1 - progress), 1);
                    
                    updateProgressBar(newProgress);
                    
                    if (newProgress < 1) {
                        requestAnimationFrame(updateProgress);
                    }
                }
                updateProgress();
                
                debugLog('重新开始动画', {
                    transition: scrollText.style.transition,
                    transform: scrollText.style.transform
                });
            });
            
            // 更新速度显示
            updateSpeedValue(speed);
            
        } catch (error) {
            console.error('更新滚动速度失败:', error);
            debugLog('更新滚动速度失败', { error });
        }
    }
    
    /**
     * 暂停滚动
     */
    function pauseScrolling() {
        if (!isScrolling || isPaused) return;
        
        // 获取当前位置和进度
        const computedStyle = window.getComputedStyle(scrollText);
        currentTransform = new WebKitCSSMatrix(computedStyle.transform).m42;
        
        // 暂停动画
        scrollText.style.transition = 'none';
        scrollText.style.transform = `translateY(${currentTransform}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
        
        // 更新UI
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'inline-block';
        isPaused = true;
    }
    
    /**
     * 继续滚动
     */
    function resumeScrolling() {
        if (!isScrolling || !isPaused) return;
        
        // 计算当前进度
        const viewportHeight = window.innerHeight;
        const startPosition = viewportHeight / 2;
        const totalDistance = scrollText.offsetHeight;
        const maxScroll = totalDistance + startPosition;
        const progress = Math.abs(startPosition - currentTransform) / maxScroll;
        
        // 计算剩余时间和距离
        const remainingDistance = maxScroll - Math.abs(startPosition - currentTransform);
        const remainingTime = (remainingDistance / maxScroll) * animationDuration;
        
        // 继续动画
        scrollText.style.transition = `transform ${remainingTime}ms linear`;
        scrollText.style.transform = `translateY(-${maxScroll}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
        
        // 更新进度条动画
        let startTime = performance.now();
        function updateProgress() {
            if (!isScrolling || isPaused) return;
            
            const currentTime = performance.now();
            const elapsed = currentTime - startTime;
            const newProgress = Math.min(progress + (elapsed / remainingTime) * (1 - progress), 1);
            
            updateProgressBar(newProgress);
            
            if (newProgress < 1) {
                requestAnimationFrame(updateProgress);
            }
        }
        updateProgress();
        
        // 更新UI
        pauseBtn.style.display = 'inline-block';
        resumeBtn.style.display = 'none';
        isPaused = false;
    }

    /**
     * 更新焦点区域
     */
    function updateFocusArea() {
        const focusMask = document.getElementById('focusMask');
        
        if (!isScrolling || !focusAreaEnabled) {
            focusMask.style.display = 'none';
            return;
        }

        // 显示遮罩
        focusMask.style.display = 'block';
        
        // 计算焦点区域的高度
        const fontSize = parseInt(scrollText.style.fontSize);
        const lineHeightValue = parseFloat(scrollText.style.lineHeight) || 1.5;
        const actualLineHeight = fontSize * lineHeightValue;
        const focusSize = parseInt(focusAreaSizeInput.value);
        const focusAreaHeight = actualLineHeight * focusSize;
        
        // 获取视口中心点
        const viewportHeight = window.innerHeight;
        const viewportCenter = viewportHeight / 2;
        
        // 计算遮罩的上下部分高度
        const maskTopHeight = viewportCenter - (focusAreaHeight / 2);
        const maskBottomHeight = viewportHeight - (viewportCenter + (focusAreaHeight / 2));
        
        // 更新遮罩位置
        focusMask.style.setProperty('--mask-top-height', `${maskTopHeight}px`);
        focusMask.style.setProperty('--mask-bottom-height', `${maskBottomHeight}px`);
        
        debugLog('更新焦点区域', {
            fontSize,
            lineHeightValue,
            actualLineHeight,
            focusSize,
            focusAreaHeight,
            viewportCenter,
            maskTopHeight,
            maskBottomHeight
        });
    }

    /**
     * 绑定全屏滚动控制事件
     */
    function bindScrollControls() {
        let lastWheelTime = 0;
        const wheelThrottle = 50; // 滚轮事件节流阈值（毫秒）

        // 滚轮控制
        if (fullscreenDisplay) {
            fullscreenDisplay.addEventListener('wheel', (event) => {
                event.preventDefault();
                
                const now = Date.now();
                if (now - lastWheelTime < wheelThrottle) {
                    return;
                }
                lastWheelTime = now;

                try {
                    // 获取当前位置和总高度
                    const computedStyle = window.getComputedStyle(scrollText);
                    const matrix = new WebKitCSSMatrix(computedStyle.transform);
                    const currentY = matrix.m42;
                    const viewportHeight = window.innerHeight;
                    const startPosition = viewportHeight / 2;
                    const totalDistance = scrollText.offsetHeight;
                    const maxScroll = totalDistance + startPosition;
                    
                    // 计算当前进度（0-1之间）
                    const currentProgress = Math.abs(startPosition - currentY) / totalDistance;
                    
                    // 计算新的进度
                    const progressDelta = 0.05; // 每次滚动改变5%的进度
                    const newProgress = Math.max(0, Math.min(1, 
                        currentProgress + (event.deltaY > 0 ? progressDelta : -progressDelta)
                    ));
                    
                    debugLog('滚轮调整进度', {
                        currentY,
                        startPosition,
                        totalDistance,
                        maxScroll,
                        currentProgress,
                        newProgress,
                        deltaY: event.deltaY
                    });
                    
                    // 计算新的位置
                    const targetPosition = startPosition - (newProgress * totalDistance);
                    
                    // 暂停当前动画
                    scrollText.style.transition = 'none';
                    scrollText.style.transform = `translateY(${targetPosition}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
                    
                    // 更新进度条
                    updateProgressBar(newProgress);
                    
                    // 如果不是暂停状态，继续动画
                    if (!isPaused) {
                        requestAnimationFrame(() => {
                            // 计算剩余时间和距离
                            const remainingDistance = maxScroll - Math.abs(startPosition - targetPosition);
                            const remainingTime = (remainingDistance / maxScroll) * animationDuration;
                            
                            // 继续动画
                            scrollText.style.transition = `transform ${remainingTime}ms linear`;
                            scrollText.style.transform = `translateY(-${maxScroll}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
                            
                            // 更新进度条动画
                            let startTime = performance.now();
                            function updateProgress() {
                                if (!isScrolling || isPaused) return;
                                
                                const currentTime = performance.now();
                                const elapsed = currentTime - startTime;
                                const progress = Math.min(newProgress + (elapsed / remainingTime) * (1 - newProgress), 1);
                                
                                updateProgressBar(progress);
                                
                                if (progress < 1) {
                                    requestAnimationFrame(updateProgress);
                                }
                            }
                            updateProgress();
                        });
                    }
                } catch (error) {
                    console.error('滚轮调整进度失败:', error);
                    debugLog('滚轮调整进度失败', { error });
                }
            });
        }
    }

    /**
     * 保存配置到本地存储
     */
    function saveConfig(showMessage = false) {
        const config = {
            scrollSpeed: scrollSpeed.value,
            lineHeight: lineHeight.value,
            letterSpacing: letterSpacing.value,
            textColor: textColor.value,
            fontSize: fontSize.value,
            textLang: Array.from(textLangRadios).find(radio => radio.checked)?.value || 'zh',
            bgColor: bgColor.value,
            focusAreaEnabled: focusAreaEnabledInput.checked,
            focusAreaSize: focusAreaSizeInput.value,
            mirrorMode: mirrorMode,
            countdownTime: document.getElementById('countdownTime').value,
            fullscreenSettings: {
                fontSize: fullscreenFontSize.value,
                speed: fullscreenSpeed.value,
                lineHeight: fullscreenLineHeight?.value || '2',
                letterSpacing: fullscreenLetterSpacing?.value || '2'
            }
        };
        
        localStorage.setItem(STORAGE_KEYS.CONFIG, JSON.stringify(config));
        debugLog('保存配置', config);
        
        if (showMessage) {
            layer.msg('配置已保存', {
                icon: 1,
                time: 2000
            });
        }
    }
    
    /**
     * 同步滑动条和输入框的值
     * @param {HTMLElement} slider - 滑动条元素
     * @param {HTMLElement} input - 输入框元素
     */
    function syncSliderInput(slider, input) {
        // 滑动条改变时更新输入框
        slider.addEventListener('input', () => {
            input.value = slider.value;
            saveConfig(false);
        });
        
        // 输入框改变时更新滑动条
        input.addEventListener('input', () => {
            slider.value = input.value;
            saveConfig(false);
        });
    }

    // 绑定滑动条和输入框的同步
    function bindSliderInputs() {
        syncSliderInput(fontSizeSlider, fontSize);
        syncSliderInput(scrollSpeedSlider, scrollSpeed);
        syncSliderInput(lineHeightSlider, lineHeight);
        syncSliderInput(letterSpacingSlider, letterSpacing);
    }
    
    /**
     * 加载本地存储的配置
     */
    function loadConfig() {
        try {
            const config = JSON.parse(localStorage.getItem(STORAGE_KEYS.CONFIG));
            if (config) {
                // 加载基本设置
                if (scrollSpeed) scrollSpeed.value = config.scrollSpeed;
                if (scrollSpeedSlider) scrollSpeedSlider.value = config.scrollSpeed;
                if (lineHeight) lineHeight.value = config.lineHeight;
                if (lineHeightSlider) lineHeightSlider.value = config.lineHeight;
                if (letterSpacing) letterSpacing.value = config.letterSpacing;
                if (letterSpacingSlider) letterSpacingSlider.value = config.letterSpacing;
                if (textColor) textColor.value = config.textColor;
                if (fontSize) fontSize.value = config.fontSize;
                if (fontSizeSlider) fontSizeSlider.value = config.fontSize;
                if (bgColor) bgColor.value = config.bgColor || '#000000';
                
                // 加载倒计时设置
                const countdownTimeInput = document.getElementById('countdownTime');
                if (countdownTimeInput) {
                    countdownTimeInput.value = config.countdownTime || '0';
                }
                
                // 加载全屏设置
                if (config.fullscreenSettings) {
                    if (fullscreenFontSize) fullscreenFontSize.value = config.fullscreenSettings.fontSize;
                    if (fullscreenSpeed) fullscreenSpeed.value = config.fullscreenSettings.speed;
                    if (fullscreenLineHeight) {
                        fullscreenLineHeight.value = config.fullscreenSettings.lineHeight;
                    }
                    if (fullscreenLetterSpacing) {
                        fullscreenLetterSpacing.value = config.fullscreenSettings.letterSpacing;
                    }
                }
                
                // 加载语言设置
                if (textLangRadios.length > 0) {
                    const langRadio = Array.from(textLangRadios).find(radio => radio.value === config.textLang);
                    if (langRadio) langRadio.checked = true;
                }
                
                // 更新相关状态
                focusAreaEnabled = config.focusAreaEnabled || false;
                focusAreaSize = parseInt(config.focusAreaSize || 3);
                
                // 更新UI
                if (focusAreaSettingsDiv) {
                    focusAreaSettingsDiv.style.display = focusAreaEnabled ? 'block' : 'none';
                }
                
                // 更新所有显示值
                if (fullscreenFontSize) updateValueDisplay(fullscreenFontSize);
                if (fullscreenSpeed) updateValueDisplay(fullscreenSpeed, 'speed');
                if (fullscreenLineHeight) updateValueDisplay(fullscreenLineHeight);
                if (fullscreenLetterSpacing) updateValueDisplay(fullscreenLetterSpacing);
                
                // 加载镜像模式设置
                mirrorMode = config.mirrorMode || false;
                
                // 更新UI状态
                if (mirrorTextInput) mirrorTextInput.checked = mirrorMode;
                
                // 更新layui表单
                if (form && form.render) {
                    form.render();
                }
            }
        } catch (error) {
            console.error('加载配置失败:', error);
            debugLog('加载配置失败', { error });
        }
    }
    
    /**
     * 保存文本到历史记录
     */
    function saveToHistory() {
        const text = textInput.value.trim();
        if (!text) {
            layer.msg('请先输入文本内容');
            return;
        }
        
        try {
            const history = JSON.parse(localStorage.getItem(STORAGE_KEYS.HISTORY) || '[]');
            // 去重并限制数量
            const newHistory = [
                { id: Date.now(), text, date: new Date().toLocaleString() },
                ...history.filter(item => item.text !== text)
            ].slice(0, 10);
            
            localStorage.setItem(STORAGE_KEYS.HISTORY, JSON.stringify(newHistory));
            layer.msg('保存成功');
            updateHistoryList();
        } catch (error) {
            console.error('保存历史记录失败:', error);
            layer.msg('保存失败');
        }
    }
    
    /**
     * 更新历史记录列表
     */
    function updateHistoryList() {
        try {
            const history = JSON.parse(localStorage.getItem(STORAGE_KEYS.HISTORY) || '[]');
            historyList.innerHTML = history.map(item => `
                <div class="history-item">
                    <div class="layui-text" style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        ${item.text.substring(0, 50)}${item.text.length > 50 ? '...' : ''}
                    </div>
                    <div style="margin-left: 10px;">
                        <button class="layui-btn layui-btn-xs" onclick="loadHistoryText(${item.id})">载入</button>
                        <button class="layui-btn layui-btn-xs layui-btn-danger" onclick="deleteHistoryText(${item.id})">删除</button>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            console.error('更新历史记录列表失败:', error);
        }
    }
    
    /**
     * 更新设置面板中的数值显示
     * @param {HTMLElement} input - 输入元素
     * @param {string} format - 显示格式
     */
    function updateValueDisplay(input, format = '') {
        const display = input.parentElement.querySelector('.value-display');
        if (display) {
            let value = input.value;
            if (format === 'speed') {
                value = (value / 2).toFixed(1);
            } else if (format === '%') {
                value = value + '%';
            }
            display.textContent = value;
        }
    }
    
    /**
     * 开始倒计时
     * @param {number} seconds - 倒计时秒数
     * @returns {Promise} 倒计时完成的Promise
     */
    function startCountdown(seconds) {
        return new Promise((resolve) => {
            if (seconds <= 0) {
                resolve();
                return;
            }

            const countdownEl = document.getElementById('countdown');
            const countdownOverlay = document.getElementById('countdownOverlay');
            let timeLeft = seconds;
            
            // 显示倒计时遮罩和数字
            countdownOverlay.style.display = 'block';
            countdownEl.style.display = 'block';
            countdownEl.textContent = timeLeft;
            
            countdownTimer = setInterval(() => {
                timeLeft--;
                countdownEl.textContent = timeLeft;
                
                if (timeLeft <= 0) {
                    clearInterval(countdownTimer);
                    countdownEl.style.display = 'none';
                    countdownOverlay.style.display = 'none';
                    resolve();
                }
            }, 1000);
        });
    }
    
    /**
     * 开始滚动文本
     */
    async function startScrolling() {
        // 检查文本是否为空
        if (!textInput.value.trim()) {
            layer.msg('请输入要显示的文字内容');
            return;
        }
        
        debugLog('开始滚动文本');
        
        // 更新UI状态
        if (startBtn) startBtn.style.display = 'none';
        if (stopBtn) stopBtn.style.display = 'inline-block';
        if (fullscreenDisplay) fullscreenDisplay.style.display = 'block';
        if (exitFullscreenBtn) exitFullscreenBtn.style.display = 'block';
        if (fullscreenControls) fullscreenControls.style.display = 'flex';
        
        // 请求全屏
        try {
            if (document.documentElement.requestFullscreen) {
                await document.documentElement.requestFullscreen();
            }
        } catch (error) {
            console.error('全屏请求失败:', error);
            debugLog('全屏请求失败', { error });
        }
        
        // 修改速度计算
        const initialSpeed = parseInt(scrollSpeed.value);
        if (fullscreenSpeed) fullscreenSpeed.value = initialSpeed;
        if (fullscreenFontSize) fullscreenFontSize.value = fontSize.value;
        if (fullscreenLineHeight) fullscreenLineHeight.value = lineHeight.value;
        if (fullscreenLetterSpacing) fullscreenLetterSpacing.value = letterSpacing.value;
        
        // 更新焦点区域设置
        if (fullscreenFocusAreaEnabled && focusAreaEnabledInput) {
            fullscreenFocusAreaEnabled.checked = focusAreaEnabledInput.checked;
        }
        if (fullscreenFocusAreaSize && focusAreaSizeInput) {
            fullscreenFocusAreaSize.value = focusAreaSizeInput.value;
        }
        
        // 更新镜像模式设置
        if (mirrorTextInput) {
            mirrorMode = mirrorTextInput.checked;
        }
        if (fullscreenMirrorText) {
            fullscreenMirrorText.checked = mirrorMode;
        }
        
        // 应用样式设置
        const textLang = Array.from(textLangRadios).find(radio => radio.checked)?.value || 'zh';
        scrollText.className = `scroll-text lang-${textLang}`;
        scrollText.style.fontSize = `${fontSize.value}px`;
        
        // 设置背景颜色
        fullscreenDisplay.style.backgroundColor = bgColor.value;
        
        // 设置文本内容
        scrollText.innerHTML = textInput.value.split('\n').map(line => 
            `<div>${line}</div>`
        ).join('');
        
        // 重置滚动位置，使第一行文本位于焦点区域中心
        const viewportHeight = window.innerHeight;
        const viewportCenter = viewportHeight / 2;
        
        // 等待一帧以确保DOM更新完成
        await new Promise(resolve => requestAnimationFrame(resolve));
        
        // 获取实际行高
        const computedStyle = window.getComputedStyle(scrollText.firstElementChild || scrollText);
        const lineHeightValue = parseFloat(computedStyle.lineHeight);
        const actualLineHeight = lineHeightValue || parseInt(fontSize.value);
        
        // 计算起始位置，考虑实际行高
        const startPosition = viewportCenter;
        
        debugLog('计算起始位置', {
            viewportHeight,
            viewportCenter,
            lineHeightValue,
            actualLineHeight,
            startPosition,
            mirrorMode
        });
        
        // 应用起始位置和镜像效果
        scrollText.style.transition = 'none';
        scrollText.style.transform = `translateY(${startPosition}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
        
        // 重置进度条
        updateProgressBar(0);
        
        // 如果启用了焦点区域，开始定期更新
        if (focusAreaEnabled) {
            focusAreaUpdateInterval = setInterval(updateFocusArea, 100);
            updateFocusArea();
        }
        
        // 等待倒计时完成
        const countdownTime = parseInt(document.getElementById('countdownTime')?.value || '0');
        await startCountdown(countdownTime);
        
        // 计算动画时间
        const textLength = textInput.value.length;
        animationDuration = calculateScrollDuration(textLength, initialSpeed);
        
        debugLog('准备开始动画', {
            textLength,
            animationDuration,
            durationInSeconds: animationDuration / 1000,
            mirrorMode
        });
        
        // 开始滚动动画
        requestAnimationFrame(() => {
            const totalDistance = scrollText.offsetHeight;
            const maxScroll = totalDistance + startPosition;
            
            scrollText.style.transition = `transform ${animationDuration}ms linear`;
            scrollText.style.transform = `translateY(-${maxScroll}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
            isScrolling = true;
            isPaused = false;
            
            // 添加动画进度更新
            let startTime = performance.now();
            function updateProgress() {
                if (!isScrolling) return;
                
                const currentTime = performance.now();
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / animationDuration, 1);
                
                updateProgressBar(progress);
                
                if (progress < 1 && !isPaused) {
                    requestAnimationFrame(updateProgress);
                }
            }
            updateProgress();
            
            debugLog('动画已开始', {
                transition: scrollText.style.transition,
                transform: scrollText.style.transform,
                totalHeight: scrollText.offsetHeight,
                maxScroll,
                mirrorMode
            });
        });
        
        // 保存当前配置
        saveConfig(true);
    }
    
    /**
     * 停止滚动文本
     */
    function stopScrolling() {
        // 更新UI状态
        startBtn.style.display = 'inline-block';
        stopBtn.style.display = 'none';
        fullscreenDisplay.style.display = 'none';
        exitFullscreenBtn.style.display = 'none';
        fullscreenControls.style.display = 'none';
        fullscreenSettings.style.display = 'none';
        speedIndicator.style.display = 'none';
        
        // 停止动画
        scrollText.style.transition = 'none';
        isScrolling = false;
        isPaused = false;
        
        // 退出全屏
        try {
            if (document.exitFullscreen) {
                document.exitFullscreen();
            }
        } catch (error) {
            console.error('退出全屏失败:', error);
        }
        
        // 清除焦点区域更新定时器
        if (focusAreaUpdateInterval) {
            clearInterval(focusAreaUpdateInterval);
            focusAreaUpdateInterval = null;
        }
    }
    
    // 修改初始化顺序
    $(function() {
        try {
            debugLog('开始初始化提词器');
            
            // 先初始化layui表单
            form.render();
            
            // 加载配置和历史记录
            loadConfig();
            updateHistoryList();
            loadCurrentText();
            
            // 初始化颜色选择器
            initColorPickers();
            
            // 初始化滑动条
            bindSliderInputs();
            
            // 绑定事件监听器
            bindEventListeners();
            
            debugLog('提词器初始化完成');
        } catch (error) {
            console.error('初始化失败:', error);
            debugLog('初始化失败', { error });
        }
    });

    // 将所有事件监听器绑定封装到一个函数中
    function bindEventListeners() {
        try {
            debugLog('开始绑定事件监听器');
            
            // 绑定基本控制按钮事件
            if (startBtn) startBtn.addEventListener('click', startScrolling);
            if (stopBtn) stopBtn.addEventListener('click', stopScrolling);
            if (exitFullscreenBtn) exitFullscreenBtn.addEventListener('click', stopScrolling);
            if (saveTextBtn) saveTextBtn.addEventListener('click', saveToHistory);
            
            // 绑定清空按钮事件
            if (clearHistoryBtn) {
                clearHistoryBtn.addEventListener('click', () => {
                    layer.confirm('确定要清空所有历史记录吗？', {icon: 3}, function(index) {
                        localStorage.removeItem(STORAGE_KEYS.HISTORY);
                        updateHistoryList();
                        layer.close(index);
                        layer.msg('已清空历史记录');
                    });
                });
            }

            // 全屏控制事件
            if (toggleSettingsBtn) {
                toggleSettingsBtn.addEventListener('click', () => {
                    if (fullscreenSettings) {
                        fullscreenSettings.style.display = 
                            fullscreenSettings.style.display === 'none' ? 'block' : 'none';
                    }
                });
            }

            // 暂停/继续按钮事件
            if (pauseBtn) pauseBtn.addEventListener('click', pauseScrolling);
            if (resumeBtn) resumeBtn.addEventListener('click', resumeScrolling);

            // 全屏设置变化事件
            if (fullscreenSpeed) {
                fullscreenSpeed.addEventListener('input', () => {
                    updateScrollSpeed(parseInt(fullscreenSpeed.value));
                });
            }

            // 文本框内容变化事件
            if (textInput) {
                textInput.addEventListener('input', () => {
                    if (saveTimeout) {
                        clearTimeout(saveTimeout);
                    }
                    saveTimeout = setTimeout(saveCurrentText, 500);
                });
            }

            // 清空文本按钮事件
            if (clearTextBtn) {
                clearTextBtn.addEventListener('click', clearText);
            }

            // 配置变化事件
            const configInputs = [
                scrollSpeed, lineHeight, letterSpacing, textColor, fontSize, 
                bgColor, document.getElementById('countdownTime')
            ];
            
            configInputs.forEach(input => {
                if (input) {
                    input.addEventListener('change', () => saveConfig(false));
                }
            });

            // 复选框事件
            const checkboxes = [focusAreaEnabledInput, mirrorTextInput];
            checkboxes.forEach(checkbox => {
                if (checkbox) {
                    checkbox.addEventListener('change', () => saveConfig(false));
                }
            });

            // 语言选择事件
            if (textLangRadios) {
                textLangRadios.forEach(radio => {
                    if (radio) {
                        radio.addEventListener('change', () => saveConfig(false));
                    }
                });
            }

            // 保存配置按钮事件
            if (saveConfigBtn) {
                saveConfigBtn.addEventListener('click', () => saveConfig(true));
            }

            // 绑定其他事件
            bindFullscreenEvents();
            bindMediaControls();
            bindFocusAreaEvents();
            bindColorPickerEvents();
            
            debugLog('事件监听器绑定完成');
        } catch (error) {
            console.error('绑定事件监听器失败:', error);
            debugLog('绑定事件监听器失败', { error });
        }
    }

    function bindFullscreenEvents() {
        try {
            debugLog('开始绑定全屏事件');
            
            // 全屏点击事件处理
            if (fullscreenDisplay) {
                fullscreenDisplay.addEventListener('click', (event) => {
                    debugLog('全屏点击事件', {
                        target: event.target.className,
                        isScrolling: isScrolling
                    });

                    // 如果点击的是控制按钮，不处理
                    if (event.target.closest('.fullscreen-controls') || 
                        event.target.closest('.fullscreen-settings') ||
                        event.target.closest('.speed-indicator')) {
                        return;
                    }

                    // 切换控制面板显示
                    if (fullscreenControls) {
                        fullscreenControls.style.display = 
                            fullscreenControls.style.display === 'none' ? 'block' : 'none';
                    }
                });
            }

            // 全屏设置面板事件绑定
            if (fullscreenSettings) {
                const settingsInputs = fullscreenSettings.querySelectorAll('input[type="range"]');
                settingsInputs.forEach(input => {
                    const targetId = input.dataset.target;
                    const valueDisplay = input.parentElement.querySelector('.value-display');
                    
                    if (valueDisplay) {
                        input.addEventListener('input', () => {
                            const value = input.value;
                            valueDisplay.textContent = value;
                            
                            // 更新对应的主设置值
                            const mainInput = document.getElementById(targetId);
                            if (mainInput) {
                                mainInput.value = value;
                                
                                // 根据设置类型执行相应的更新
                                switch(targetId) {
                                    case 'fontSize':
                                        if (scrollText) scrollText.style.fontSize = `${value}px`;
                                        break;
                                    case 'scrollSpeed':
                                        updateScrollSpeed(parseInt(value));
                                        break;
                                    case 'lineHeight':
                                        if (scrollText) scrollText.style.lineHeight = value;
                                        break;
                                    case 'letterSpacing':
                                        if (scrollText) scrollText.style.letterSpacing = `${value}px`;
                                        break;
                                }
                                
                                // 保存配置
                                saveConfig(false);
                            }
                        });
                    }
                });
            }

            // 焦点区域开关
            const focusAreaSwitch = fullscreenSettings?.querySelector('#fullscreenFocusAreaEnabled');
            const focusAreaSettings = fullscreenSettings?.querySelector('#fullscreenFocusAreaSettings');
            
            if (focusAreaSwitch && focusAreaSettings) {
                focusAreaSwitch.addEventListener('change', () => {
                    focusAreaEnabled = focusAreaSwitch.checked;
                    const mainSwitch = document.getElementById('focusAreaEnabled');
                    if (mainSwitch) {
                        mainSwitch.checked = focusAreaSwitch.checked;
                    }
                    focusAreaSettings.style.display = focusAreaSwitch.checked ? 'block' : 'none';
                    updateFocusArea();
                    saveConfig(false);
                });
            }

            // 焦点区域大小
            const focusAreaSize = fullscreenSettings?.querySelector('#fullscreenFocusAreaSize');
            if (focusAreaSize) {
                focusAreaSize.addEventListener('input', () => {
                    const mainInput = document.getElementById('focusAreaSize');
                    if (mainInput) {
                        mainInput.value = focusAreaSize.value;
                    }
                    updateFocusArea();
                    saveConfig(false);
                });
            }

            // 镜像模式开关
            const mirrorModeSwitch = fullscreenSettings?.querySelector('#fullscreenMirrorText');
            if (mirrorModeSwitch && scrollText) {
                mirrorModeSwitch.addEventListener('change', () => {
                    try {
                        mirrorMode = mirrorModeSwitch.checked;
                        const mainSwitch = document.getElementById('mirrorText');
                        if (mainSwitch) {
                            mainSwitch.checked = mirrorModeSwitch.checked;
                        }
                        
                        // 获取当前transform中的translateY值
                        const computedStyle = window.getComputedStyle(scrollText);
                        const matrix = new WebKitCSSMatrix(computedStyle.transform);
                        const currentY = matrix.m42;
                        
                        // 保持当前位置不变，只修改镜像状态
                        scrollText.style.transition = 'none';
                        scrollText.style.transform = `translateY(${currentY}px)${mirrorMode ? ' scaleX(-1)' : ''}`;
                        
                        // 恢复滚动动画的过渡效果
                        if (isScrolling && !isPaused) {
                            requestAnimationFrame(() => {
                                scrollText.style.transition = 'transform linear';
                            });
                        }
                        
                        saveConfig(false);
                        
                        debugLog('切换镜像模式', {
                            mirrorMode,
                            currentY,
                            transform: scrollText.style.transform
                        });
                    } catch (error) {
                        console.error('切换镜像模式失败:', error);
                        debugLog('切换镜像模式失败', { error });
                    }
                });
            }
            
            debugLog('全屏事件绑定完成');
        } catch (error) {
            console.error('绑定全屏事件失败:', error);
            debugLog('绑定全屏事件失败', { error });
        }
    }

    function bindMediaControls() {
        try {
            debugLog('开始绑定媒体控制');
            
            // 媒体控制
            if (navigator.mediaSession) {
                navigator.mediaSession.setActionHandler('play', resumeScrolling);
                navigator.mediaSession.setActionHandler('pause', pauseScrolling);
            }

            // 键盘控制
            document.addEventListener('keydown', (event) => {
                if (!isScrolling) return;
                
                if (event.code === 'Space') {
                    event.preventDefault();
                    if (isPaused) {
                        resumeScrolling();
                    } else {
                        pauseScrolling();
                    }
                } else if ((event.code === 'ArrowUp' || event.code === 'VolumeUp') && fullscreenSpeed) {
                    event.preventDefault();
                    const newSpeed = Math.min(parseInt(fullscreenSpeed.value) + 5, 100);
                    fullscreenSpeed.value = newSpeed;
                    updateScrollSpeed(newSpeed);
                    
                    // 更新主设置面板的速度值
                    if (scrollSpeed) {
                        scrollSpeed.value = newSpeed;
                    }
                    if (scrollSpeedSlider) {
                        scrollSpeedSlider.value = newSpeed;
                    }
                    
                    debugLog('增加速度', { newSpeed });
                } else if ((event.code === 'ArrowDown' || event.code === 'VolumeDown') && fullscreenSpeed) {
                    event.preventDefault();
                    const newSpeed = Math.max(parseInt(fullscreenSpeed.value) - 5, 0);
                    fullscreenSpeed.value = newSpeed;
                    updateScrollSpeed(newSpeed);
                    
                    // 更新主设置面板的速度值
                    if (scrollSpeed) {
                        scrollSpeed.value = newSpeed;
                    }
                    if (scrollSpeedSlider) {
                        scrollSpeedSlider.value = newSpeed;
                    }
                    
                    debugLog('减小速度', { newSpeed });
                }
            });

            // 移动端音量键控制
            if ('volumechange' in window) {
                let lastVolume = window.volume || 1;
                window.addEventListener('volumechange', (event) => {
                    if (!isScrolling) return;
                    
                    const currentVolume = window.volume || 1;
                    const volumeChanged = currentVolume !== lastVolume;
                    
                    if (volumeChanged && fullscreenSpeed) {
                        const speedDelta = currentVolume > lastVolume ? 5 : -5;
                        const newSpeed = Math.max(0, Math.min(100, parseInt(fullscreenSpeed.value) + speedDelta));
                        
                        fullscreenSpeed.value = newSpeed;
                        updateScrollSpeed(newSpeed);
                        
                        // 更新主设置面板的速度值
                        if (scrollSpeed) {
                            scrollSpeed.value = newSpeed;
                        }
                        if (scrollSpeedSlider) {
                            scrollSpeedSlider.value = newSpeed;
                        }
                        
                        debugLog('音量键调整速度', { 
                            volumeChange: currentVolume - lastVolume,
                            newSpeed 
                        });
                    }
                    
                    lastVolume = currentVolume;
                });
            }
            
            debugLog('媒体控制绑定完成');
        } catch (error) {
            console.error('绑定媒体控制失败:', error);
            debugLog('绑定媒体控制失败', { error });
        }
    }

    function bindFocusAreaEvents() {
        try {
            debugLog('开始绑定焦点区域事件');
            
            // 焦点区域事件
            if (focusAreaEnabledInput && focusAreaSettingsDiv) {
                focusAreaEnabledInput.addEventListener('change', function() {
                    focusAreaEnabled = this.checked;
                    if (focusAreaEnabledInput) {
                        focusAreaEnabledInput.checked = this.checked;
                    }
                    focusAreaSettingsDiv.style.display = this.checked ? 'block' : 'none';
                    
                    if (isScrolling) {
                        updateFocusArea();
                    }
                    saveConfig(false);
                });
            }

            if (focusAreaSizeInput) {
                focusAreaSizeInput.addEventListener('input', function() {
                    const value = parseInt(this.value);
                    if (value >= 1 && value <= 7) {
                        focusAreaSize = value;
                        if (focusAreaSizeInput) {
                            focusAreaSizeInput.value = value;
                        }
                        updateValueDisplay(this);
                        if (isScrolling && focusAreaEnabled) {
                            updateFocusArea();
                        }
                        saveConfig(false);
                    }
                });
            }
            
            debugLog('焦点区域事件绑定完成');
        } catch (error) {
            console.error('绑定焦点区域事件失败:', error);
            debugLog('绑定焦点区域事件失败', { error });
        }
    }

    function bindColorPickerEvents() {
        try {
            debugLog('开始绑定颜色选择器事件');
            
            // 颜色选择器事件
            if (bgColor && fullscreenDisplay) {
                bgColor.addEventListener('change', function() {
                    const color = this.value;
                    fullscreenDisplay.style.backgroundColor = color;
                    saveConfig(false);
                });
            }
            
            debugLog('颜色选择器事件绑定完成');
        } catch (error) {
            console.error('绑定颜色选择器事件失败:', error);
            debugLog('绑定颜色选择器事件失败', { error });
        }
    }

    /**
     * 保存当前文本内容
     */
    function saveCurrentText() {
        const text = textInput.value;
        localStorage.setItem(STORAGE_KEYS.CURRENT_TEXT, text);
        debugLog('保存当前文本', { length: text.length });
    }

    /**
     * 加载上次保存的文本内容
     */
    function loadCurrentText() {
        const savedText = localStorage.getItem(STORAGE_KEYS.CURRENT_TEXT);
        if (savedText) {
            textInput.value = savedText;
            debugLog('加载保存的文本', { length: savedText.length });
        }
    }

    /**
     * 清空文本框
     */
    function clearText() {
        layer.confirm('确定要清空当前文本吗？', {icon: 3}, function(index) {
            textInput.value = '';
            saveCurrentText();
            layer.close(index);
            layer.msg('已清空文本');
            debugLog('清空文本框');
        });
    }

    // 暴露给全局的函数
    window.loadHistoryText = function(id) {
        try {
            const history = JSON.parse(localStorage.getItem(STORAGE_KEYS.HISTORY) || '[]');
            const item = history.find(item => item.id === id);
            if (item) {
                textInput.value = item.text;
                layer.msg('已载入文本');
            }
        } catch (error) {
            console.error('载入历史文本失败:', error);
            layer.msg('载入失败');
        }
    };
    
    window.deleteHistoryText = function(id) {
        try {
            const history = JSON.parse(localStorage.getItem(STORAGE_KEYS.HISTORY) || '[]');
            const newHistory = history.filter(item => item.id !== id);
            localStorage.setItem(STORAGE_KEYS.HISTORY, JSON.stringify(newHistory));
            updateHistoryList();
            layer.msg('已删除');
        } catch (error) {
            console.error('删除历史文本失败:', error);
            layer.msg('删除失败');
        }
    };
    
    /**
     * 获取当前滚动进度
     * @returns {number} 滚动进度（0-1）
     */
    function getCurrentScrollProgress() {
        const computedStyle = window.getComputedStyle(scrollText);
        const matrix = new WebKitCSSMatrix(computedStyle.transform);
        const currentY = matrix.m42;
        const totalHeight = scrollText.offsetHeight;
        return Math.abs(currentY) / totalHeight;
    }

    // 初始化颜色选择器
    function initColorPickers() {
        // 初始化文字颜色选择器
        const textColorGroup = document.getElementById('textColorGroup');
        COLOR_OPTIONS.text.forEach(color => {
            const colorOption = document.createElement('div');
            colorOption.className = 'color-option';
            colorOption.style.backgroundColor = color.value;
            colorOption.title = color.name;
            if (color.value === textColor.value) {
                colorOption.classList.add('active');
            }
            colorOption.addEventListener('click', () => {
                textColor.value = color.value;
                textColorGroup.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('active'));
                colorOption.classList.add('active');
                saveConfig(false);
            });
            textColorGroup.appendChild(colorOption);
        });

        // 初始化背景颜色选择器
        const bgColorGroup = document.getElementById('bgColorGroup');
        COLOR_OPTIONS.background.forEach(color => {
            const colorOption = document.createElement('div');
            colorOption.className = 'color-option';
            colorOption.style.backgroundColor = color.value;
            colorOption.title = color.name;
            if (color.value === bgColor.value) {
                colorOption.classList.add('active');
            }
            colorOption.addEventListener('click', () => {
                bgColor.value = color.value;
                bgColorGroup.querySelectorAll('.color-option').forEach(opt => opt.classList.remove('active'));
                colorOption.classList.add('active');
                saveConfig(false);
            });
            bgColorGroup.appendChild(colorOption);
        });
    }
});
