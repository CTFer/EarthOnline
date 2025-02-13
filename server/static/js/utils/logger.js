/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-13 19:10:14
 * @LastEditTime: 2025-02-13 19:52:29
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import { LOG_CONFIG } from '../config/config.js';

// 日志级别映射
const LOG_LEVELS = {
    debug: 1,
    info: 2,
    warn: 3,
    error: 4
};

class Logger {
    static getTimeString() {
        if (!LOG_CONFIG.timeFormat) return '';
        
        const now = new Date();
        return `[${now.toLocaleTimeString('zh-CN', { hour12: false })}:${now.getMilliseconds().toString().padStart(3, '0')}]`;
    }

    static formatMessage(module, level, ...args) {
        const timeStr = this.getTimeString();
        const moduleStr = `[${module}]`;
        const levelStr = `[${level.toUpperCase()}]`;
        
        if (LOG_CONFIG.styleOutput) {
            const style = LOG_CONFIG.styles[level];
            return [`${timeStr}${moduleStr}${levelStr}`, style, ...args];
        }
        
        return [`${timeStr}${moduleStr}${levelStr}`, ...args];
    }

    static log(module, level, ...args) {
        if (!LOG_CONFIG.enableConsoleLog) return;

        // 检查日志级别
        const currentLevel = LOG_LEVELS[level];
        const configLevel = LOG_LEVELS[LOG_CONFIG.logLevel];
        if (currentLevel < configLevel) return;

        // 检查模块白名单
        if (!LOG_CONFIG.allowedModules.includes(module)) return;

        const formattedArgs = this.formatMessage(module, level, ...args);
        
        if (LOG_CONFIG.styleOutput) {
            console.log(`%c${formattedArgs[0]}`, formattedArgs[1], ...formattedArgs.slice(2));
        } else {
            console.log(...formattedArgs);
        }
    }

    static debug(module, ...args) {
        this.log(module, 'debug', ...args);
    }

    static info(module, ...args) {
        this.log(module, 'info', ...args);
    }

    static warn(module, ...args) {
        this.log(module, 'warn', ...args);
    }

    static error(module, ...args) {
        this.log(module, 'error', ...args);
    }
}

export default Logger; 