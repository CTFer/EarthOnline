/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-03-09 11:19:54
 * @LastEditTime: 2025-03-09 11:20:25
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Description: SSL配置
 */
import { SSL_ENABLED } from './config.js';
export const SSL_CONFIG = {
    // 是否启用SSL
    ENABLED: SSL_ENABLED,
    
    // SSL证书配置
    CERT_OPTIONS: {
        rejectUnauthorized: false, // 开发环境可设置为false
    },
    
    // SSL端口配置 
    PORTS: {
        HTTP: 80,
        HTTPS: 443
    },
    
    // 自动重定向配置
    REDIRECT: {
        enabled: true,  // 是否自动重定向HTTP到HTTPS
        statusCode: 301 // 重定向状态码
    }
};

// SSL状态检测
export function checkSSLStatus() {
    // 检查当前协议
    const isHttps = window.location.protocol === 'https:';
    
    // 检查配置
    const sslEnabled = SSL_CONFIG.ENABLED;
    
    // 返回状态
    return {
        enabled: sslEnabled,
        active: isHttps,
        shouldRedirect: sslEnabled && !isHttps && SSL_CONFIG.REDIRECT.enabled
    };
} 