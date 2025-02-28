/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-01-10 17:02:48
 * @LastEditTime: 2025-02-18 12:41:09
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import { TASK_TYPE_MAP } from "../config/config.js";
import Logger from "./logger.js";

// 工具函数
export const gameUtils = {
  // 格式化剩余时间
  formatTimeRemaining(milliseconds) {
    Logger.debug("Utils", "Formatting time:", milliseconds);
    if (milliseconds <= 0) {
      return "已结束";
    }

    const seconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;

    if (hours > 0) {
      return `${hours}小时${minutes}分钟`;
    } else if (minutes > 0) {
      return `${minutes}分钟${remainingSeconds}秒`;
    } else {
      return `${remainingSeconds}秒`;
    }
  },

  // 获取任务类型信息
  getTaskTypeInfo(taskType, icon = "") {
    Logger.debug("Utils", "Getting task type info:", taskType);
    const defaultIcon = "layui-icon-flag"; // 默认图标

    const typeInfo = {
      DAILY: {
        text: "日常任务",
        color: "#4CAF50",
        icon: icon || defaultIcon,
      },
      MAIN: {
        text: "主线任务",
        color: "#2196F3",
        icon: icon || defaultIcon,
      },
      BRANCH: {
        text: "支线任务",
        color: "#9C27B0",
        icon: icon || defaultIcon,
      },
      SPECIAL: {
        text: "特殊任务",
        color: "#FF9800",
        icon: icon || defaultIcon,
      },
    };

    return (
      typeInfo[taskType] || {
        text: "未知任务",
        color: "#607D8B",
        icon: defaultIcon,
      }
    );
  },

  // 计算任务结束时间
  calculateTaskEndTime(task) {
    const now = new Date();
    if (task.task_type === "4") {
      // 每日任务
      const endTime = new Date();
      endTime.setHours(22, 0, 0, 0);
      return endTime;
    }
    return new Date(parseInt(task.endtime) * 1000);
  },

  // 格式化日期时间
  formatDate: function (timestamp) {
    if (!timestamp) return "永久";

    const date = new Date(timestamp * 1000);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hour = String(date.getHours()).padStart(2, "0");
    const minute = String(date.getMinutes()).padStart(2, "0");

    return `${year}-${month}-${day} ${hour}:${minute}`;
  },
  // 更新任务时间
  updateTaskTime(taskElement, endtime) {
    const now = Math.floor(Date.now() / 1000);
    const timeLeft = endtime - now;

    if (timeLeft <= 0) {
      taskElement.querySelector(".task-time").textContent = "已过期";
      return false;
    }

    const hours = Math.floor(timeLeft / 3600);
    const minutes = Math.floor((timeLeft % 3600) / 60);
    const seconds = timeLeft % 60;

    const timeString = `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`;
    taskElement.querySelector(".task-time").textContent = `剩余时间：${timeString}`;
    Logger.debug("Utils", "更新任务时间:", timeString);
    return true;

  },

  // 格式化时间戳
  formatTimestamp(timestamp) {
    if (!timestamp) return "无效时间";

    const date = new Date(timestamp * 1000);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hour = String(date.getHours()).padStart(2, "0");
    const minute = String(date.getMinutes()).padStart(2, "0");

    return `${year}-${month}-${day} ${hour}:${minute}`;
  },
  // 设置ICP备案号
  setICP(icp) {
    const icpElement = document.getElementById("icp");
    if (icpElement) {
      icpElement.textContent = icp;
    }
  },
};
