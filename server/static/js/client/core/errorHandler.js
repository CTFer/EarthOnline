/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-12 20:30:07
 * @LastEditTime: 2025-02-12 20:30:15
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import Logger from '../../utils/logger.js';

export class ErrorHandler {
    static handle(error, context = '') {
        Logger.error(`错误[${context}]`, error);
        
        // 统一的错误提示
        layer.msg(error.message || '操作失败，请重试', {icon: 2});
        
        // 错误上报
        this.report(error, context);
    }

    static report(error, context) {
        Logger.error('错误上报', 'Reporting error:', {
            context,
            message: error.message,
            stack: error.stack
        });
    }
} 