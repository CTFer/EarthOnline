// 通用工具函数
const utils = {
  // 节流函数
  throttle: function(func, wait) {
    let timeout = null;
    let previous = 0;
    
    return function(...args) {
      const now = Date.now();
      const remaining = wait - (now - previous);
      
      if (remaining <= 0 || remaining > wait) {
        if (timeout) {
          clearTimeout(timeout);
          timeout = null;
        }
        previous = now;
        func.apply(this, args);
      } else if (!timeout) {
        timeout = setTimeout(() => {
          previous = Date.now();
          timeout = null;
          func.apply(this, args);
        }, remaining);
      }
    };
  },
  
  // API请求封装
  apiRequest: function(url, method, data) {
    return new Promise((resolve, reject) => {
      $.ajax({
        url: url,
        method: method,
        contentType: "application/json",
        data: data ? JSON.stringify(data) : null,
        success: function(res) {
          try {
            const result = typeof res === "string" ? JSON.parse(res) : res;
            resolve(result);
          } catch (e) {
            console.error("[Roadmap API] Error parsing response:", e);
            reject(new Error("数据解析错误: " + e.message));
          }
        },
        error: function(xhr, status, error) {
          console.error("[Roadmap API] Request failed:", error);
          reject(new Error("网络请求失败: " + error));
        }
      });
    });
  },
  
  // 将十六进制颜色转换为RGB格式
  getRGBColor: function(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgb(${r}, ${g}, ${b})`;
  }
};
