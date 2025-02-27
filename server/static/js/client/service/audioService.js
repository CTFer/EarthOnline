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
  constructor(eventBus, store) {
    this.eventBus = eventBus;
    this.store = store;  // store可以是可选的
    this.componentId = 'audioService';
    this.loadedSounds = new Map();  // 已加载的音效
    this.loading = new Map();       // 正在加载的音效
    
    // 初始化默认状态
    const defaultState = {
      initialized: false,
      volume: parseFloat(localStorage.getItem('audioVolume') || '1.0'),
      muted: localStorage.getItem('audioMuted') === 'true',
      activeAudios: new Set()
    };
    
    // 如果有store，尝试从store获取状态
    let savedState = {};
    if (this.store) {
      try {
        savedState = this.store.getComponentState(this.componentId) || {};
      } catch (error) {
        Logger.warn("AudioService", "从Store获取状态失败，使用默认状态", error);
      }
    }
    
    // 合并默认状态和保存的状态
    this.state = {
      ...defaultState,
      ...savedState
    };
    
    // 检查音频是否启用
    if (!AUDIO_CONFIG.enabled) {
      Logger.info("AudioService", "音频服务已禁用");
      return;
    }
    
    // 如果有store，订阅状态变更
    if (this.store) {
      try {
        this.unsubscribe = this.store.subscribe('component', this.componentId, this.handleStateChange.bind(this));
      } catch (error) {
        Logger.warn("AudioService", "状态订阅失败", error);
      }
    }
    
    Logger.info("AudioService", "初始化音频服务");
  }

  // 状态变更处理
  handleStateChange(newState, oldState) {
    Logger.debug("AudioService", "状态变更:", { old: oldState, new: newState });
    
    // 处理音量变更
    if (newState.volume !== oldState.volume || newState.muted !== oldState.muted) {
      this.applyVolumeSettings();
    }
  }

  // 更新组件状态
  updateState(partialState) {
    this.state = { ...this.state, ...partialState };
    
    // 如果有store，更新store中的状态
    if (this.store) {
      try {
        this.store.setComponentState(this.componentId, this.state);
      } catch (error) {
        Logger.warn("AudioService", "更新Store状态失败", error);
      }
    }
  }

  // 检查服务状态
  isReady() {
    return AUDIO_CONFIG.enabled && this.state.initialized;
  }

  // 获取音效配置
  getSoundConfig(soundId) {
    return AUDIO_CONFIG.sounds[soundId];
  }

  // 获取音效实例
  getSound(soundId) {
    return this.loadedSounds.get(soundId);
  }

  // 检查音效是否正在播放
  isPlaying(soundId) {
    return this.state.activeAudios.has(soundId);
  }

  // 播放音频的底层实现
  async play(soundId) {
    if (!this.isReady()) {
      throw new Error("音频服务未就绪");
    }

    let sound = this.getSound(soundId);
    if (!sound) {
      const config = this.getSoundConfig(soundId);
      if (!config) {
        throw new Error(`未找到音效配置: ${soundId}`);
      }
      sound = await this.loadSound(soundId, config.path);
    }

    sound.currentTime = 0;
    await sound.play();
    
    // 更新活动音频列表
    this.state.activeAudios.add(soundId);
    this.updateState({ activeAudios: this.state.activeAudios });
  }

  // 停止音频的底层实现
  stop(soundId) {
    if (!this.isReady()) {
      throw new Error("音频服务未就绪");
    }

    const sound = this.getSound(soundId);
    if (sound) {
      sound.pause();
      sound.currentTime = 0;
      
      // 更新活动音频列表
      this.state.activeAudios.delete(soundId);
      this.updateState({ activeAudios: this.state.activeAudios });
    }
  }

  // 设置音量的底层实现
  setAudioVolume(volume, muted) {
    const newState = { ...this.state };
    
    if (typeof volume === 'number') {
      newState.volume = Math.max(0, Math.min(1, volume));
      localStorage.setItem('audioVolume', newState.volume.toString());
    }
    
    if (typeof muted === 'boolean') {
      newState.muted = muted;
      localStorage.setItem('audioMuted', muted.toString());
    }
    
    this.updateState(newState);
    this.applyVolumeSettings();
  }

  async init() {
    if (!AUDIO_CONFIG.enabled) return;
    
    try {
      // 根据加载策略决定是否预加载
      if (AUDIO_CONFIG.preloadStrategy === 'IMMEDIATE') {
        await this.preloadSounds();
      }
      
      this.updateState({ initialized: true });
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
        audio.volume = this.state.muted ? 0 : this.state.volume;
        
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

  applyVolumeSettings() {
    const volume = this.state.muted ? 0 : this.state.volume;
    this.loadedSounds.forEach((sound) => {
      sound.volume = volume;
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

  // 保存状态快照
  saveState() {
    return this.store.saveComponentSnapshot(this.componentId);
  }

  // 恢复状态快照
  restoreState(snapshot) {
    this.store.restoreComponentSnapshot(this.componentId, snapshot);
  }

  destroy() {
    try {
      // 停止所有正在播放的音频
      this.state.activeAudios.forEach(soundId => {
        this.stop(soundId);
      });
      
      // 取消状态订阅
      if (this.unsubscribe) {
        this.unsubscribe();
      }

      this.loadedSounds.forEach((sound) => {
        sound.pause();
        sound.currentTime = 0;
        sound.src = "";
        sound.removeEventListener('canplaythrough', null);
        sound.removeEventListener('error', null);
      });

      // 清理资源
      this.loading.clear();
      this.loadedSounds.clear();
      this.state.activeAudios.clear();
      
      // 更新状态
      this.updateState({
        initialized: false,
        activeAudios: new Set()
      });
      
      Logger.info("AudioService", "音频服务已销毁");
    } catch (error) {
      Logger.error("AudioService", "销毁音频服务失败:", error);
    }
  }
}

export default AudioService;
