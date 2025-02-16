/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:10:21
 * @LastEditors: 一根鱼骨棒
 * @Description: 音频服务
 */
import Logger from '../../utils/logger.js';

class AudioService {
    constructor() {
        this.sounds = new Map();
        this.initialized = false;
        Logger.info('AudioService', '初始化音频服务');
    }

    async init() {
        try {
            // 预加载音效
            await this.loadSound('COMPLETE', '/static/audio/complete.mp3');
            await this.loadSound('ACCEPT', '/static/audio/accept.mp3');
            await this.loadSound('ERROR', '/static/audio/error.mp3');
            
            this.initialized = true;
            Logger.info('AudioService', '音频服务初始化完成');
        } catch (error) {
            Logger.error('AudioService', '音频服务初始化失败:', error);
            throw error;
        }
    }

    async loadSound(id, url) {
        try {
            const audio = new Audio(url);
            await audio.load();
            this.sounds.set(id, audio);
            Logger.debug('AudioService', `加载音效 ${id} 成功`);
        } catch (error) {
            Logger.error('AudioService', `加载音效 ${id} 失败:`, error);
            throw error;
        }
    }

    playSound(id) {
        if (!this.initialized) {
            Logger.warn('AudioService', '音频服务未初始化');
            return;
        }

        const sound = this.sounds.get(id);
        if (sound) {
            Logger.debug('AudioService', `播放音效: ${id}`);
            sound.currentTime = 0;
            sound.play().catch(error => {
                Logger.error('AudioService', `播放音效 ${id} 失败:`, error);
            });
        } else {
            Logger.warn('AudioService', `未找到音效: ${id}`);
        }
    }

    destroy() {
        this.sounds.forEach(sound => {
            sound.pause();
            sound.src = '';
        });
        this.sounds.clear();
        this.initialized = false;
        Logger.info('AudioService', '音频服务已销毁');
    }
}

export default AudioService; 