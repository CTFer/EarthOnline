/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-15 14:10:21
 * @LastEditors: 一根鱼骨棒
 * @Description: 音频服务
 */
import { AUDIO_CONFIG } from '../../config/config.js';
import Logger from "../../utils/logger.js";
import { 
    AUDIO_EVENTS,
    UI_EVENTS 
} from "../config/events.js";

class AudioService {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.loadedSounds = new Map();  // 已加载的音效
    this.loading = new Map();       // 正在加载的音效
    this.initialized = false;
    this.volume = parseFloat(localStorage.getItem('audioVolume') || '1.0');
    this.muted = localStorage.getItem('audioMuted') === 'true';
    
    // 检查音频是否启用
    if (!AUDIO_CONFIG.enabled) {
      Logger.info("AudioService", "音频服务已禁用");
      return;
    }

    // 初始化事件监听
    this.setupEventListeners();
    
    Logger.info("AudioService", "初始化音频服务");
  }

  setupEventListeners() {
    Logger.debug("AudioService", "设置事件监听");
    
    // 音频播放事件
    this.eventBus.on(AUDIO_EVENTS.PLAY, this.handlePlaySound.bind(this));
    
    // 音频停止事件
    this.eventBus.on(AUDIO_EVENTS.STOP, this.handleStopSound.bind(this));
    
    // 音量变更事件
    this.eventBus.on(AUDIO_EVENTS.VOLUME_CHANGED, this.handleVolumeChange.bind(this));
    
    Logger.info("AudioService", "事件监听设置完成");
  }

  async init() {
    if (!AUDIO_CONFIG.enabled) return;
    
    try {
      // 根据加载策略决定是否预加载
      if (AUDIO_CONFIG.preloadStrategy === 'IMMEDIATE') {
        await this.preloadSounds();
      }
      this.initialized = true;
      this.applyVolumeSettings();
    } catch (error) {
      Logger.error("AudioService", "音频服务初始化失败:", error);
      this.eventBus.emit(UI_EVENTS.NOTIFICATION_SHOW, {
        type: 'WARNING',
        message: '音频初始化失败，将以无声模式运行'
      });
    }
  }

  async preloadSounds() {
    const soundsToPreload = Object.entries(AUDIO_CONFIG.sounds)
      .filter(([_, config]) => config.preload);
      
    Logger.info("AudioService", `开始预加载 ${soundsToPreload.length} 个音效`);
    
    const results = await Promise.allSettled(
      soundsToPreload.map(([id, config]) => this.loadSound(id, config.path))
    );

    const failedCount = results.filter(r => r.status === 'rejected').length;
    Logger.info("AudioService", `音频预加载完成: ${results.length - failedCount} 成功, ${failedCount} 失败`);
  }

  async loadSound(id, url) {
    // 检查是否已经加载或正在加载
    if (this.loadedSounds.has(id)) {
      return this.loadedSounds.get(id);
    }
    
    if (this.loading.has(id)) {
      return this.loading.get(id);
    }

    const loadPromise = new Promise((resolve, reject) => {
      try {
        const audio = new Audio(url);
        audio.preload = 'auto';
        
        // 设置音量
        audio.volume = this.muted ? 0 : this.volume;
        
        const loadTimeout = setTimeout(() => {
          reject(new Error(`加载超时: ${id}`));
        }, 5000);
        
        const handleSuccess = () => {
          clearTimeout(loadTimeout);
          this.loadedSounds.set(id, audio);
          this.loading.delete(id);
          Logger.debug("AudioService", `音效 ${id} 加载成功`);
          resolve(audio);
        };
        
        const handleError = (error) => {
          clearTimeout(loadTimeout);
          this.loading.delete(id);
          reject(new Error(`加载失败: ${error.message}`));
        };
        
        audio.addEventListener('canplaythrough', handleSuccess, { once: true });
        audio.addEventListener('error', handleError, { once: true });
        
        audio.load();
      } catch (error) {
        this.loading.delete(id);
        reject(new Error(`初始化失败: ${error.message}`));
      }
    });

    this.loading.set(id, loadPromise);
    return loadPromise;
  }

  async handlePlaySound(soundId) {
    // 检查音频服务是否启用和初始化
    if (!AUDIO_CONFIG.enabled || !this.initialized) {
      Logger.debug("AudioService", `音频服务未启用或未初始化，跳过播放: ${soundId}`);
      return;
    }
    
    try {
      const soundConfig = AUDIO_CONFIG.sounds[soundId];
      if (!soundConfig) {
        throw new Error(`未找到音效配置: ${soundId}`);
      }

      let sound = this.loadedSounds.get(soundId);
      if (!sound) {
        sound = await this.loadSound(soundId, soundConfig.path);
      }

      sound.currentTime = 0;
      const playPromise = sound.play();
      
      if (playPromise) {
        playPromise.catch((error) => {
          Logger.error("AudioService", `播放音效 ${soundId} 失败:`, error);
        });
      }
    } catch (error) {
      Logger.error("AudioService", `播放音效失败: ${soundId}`, error);
    }
  }

  handleStopSound(soundId) {
    Logger.debug("AudioService", `处理停止音效请求: ${soundId}`);
    try {
      if (!this.initialized) {
        Logger.warn("AudioService", "音频服务未初始化");
        return;
      }

      const sound = this.loadedSounds.get(soundId);
      if (sound) {
        sound.pause();
        sound.currentTime = 0;
      }
    } catch (error) {
      Logger.error("AudioService", `停止音效失败: ${soundId}`, error);
    }
  }

  handleVolumeChange(data) {
    Logger.debug("AudioService", "处理音量变更:", data);
    try {
      const { volume, muted } = data;
      
      if (typeof volume === 'number') {
        this.volume = Math.max(0, Math.min(1, volume));
        localStorage.setItem('audioVolume', this.volume.toString());
      }
      
      if (typeof muted === 'boolean') {
        this.muted = muted;
        localStorage.setItem('audioMuted', muted.toString());
      }
      
      this.applyVolumeSettings();
    } catch (error) {
      Logger.error("AudioService", "处理音量变更失败:", error);
    }
  }

  applyVolumeSettings() {
    this.loadedSounds.forEach((sound) => {
      sound.volume = this.muted ? 0 : this.volume;
    });
  }

  setVolume(volume) {
    this.eventBus.emit(AUDIO_EVENTS.VOLUME_CHANGED, {
      volume: Math.max(0, Math.min(1, volume))
    });
  }

  setMuted(muted) {
    this.eventBus.emit(AUDIO_EVENTS.VOLUME_CHANGED, { muted });
  }

  destroy() {
    try {
      // 停止所有正在播放的音频
      this.loadedSounds.forEach((sound) => {
        sound.pause();
        sound.currentTime = 0;
        sound.src = "";
        
        // 移除所有事件监听器
        sound.removeEventListener('canplaythrough', null);
        sound.removeEventListener('error', null);
      });

      // 清理加载中的音频
      this.loading.clear();
      
      // 清理已加载的音频
      this.loadedSounds.clear();
      
      // 重置状态
      this.initialized = false;
      
      Logger.info("AudioService", "音频服务已销毁");
    } catch (error) {
      Logger.error("AudioService", "销毁音频服务失败:", error);
    }
  }
}

export default AudioService;
