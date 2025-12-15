// 主题管理模块
class ThemeManager {
  constructor() {
    // 定义颜色选项 - 明亮模式和暗黑模式
    this.colorOptions = {
      light: {
        "layui-bg-blue": "#1e9fff", // 经典蓝
        "layui-bg-green": "#16b777", // 清新绿
        "layui-bg-cyan": "#3f51b5", // 深蓝色
        "layui-bg-orange": "#ffb800", // 警示色
        "layui-bg-red": "#ff5722", // 错误色
        "layui-bg-purple": "#a233c6", // 紫色
        "layui-bg-gray": "#fafafa", // 浅灰
      },
      dark: {
        "layui-bg-blue": "#0d47a1", // 深蓝
        "layui-bg-green": "#1b5e20", // 深绿
        "layui-bg-cyan": "#283593", // 深蓝色（暗色版）
        "layui-bg-orange": "#e65100", // 深橙
        "layui-bg-red": "#b71c1c", // 深红
        "layui-bg-purple": "#4a148c", // 深紫
        "layui-bg-gray": "#424242", // 深灰
      },
    };
  }
  
  // 初始化主题
  init() {
    console.log("[Roadmap] Initializing theme");
    const isDarkMode = localStorage.getItem("darkMode") === "true";
    console.log("[Roadmap] Dark mode from localStorage:", isDarkMode);

    if (isDarkMode) {
      document.body.classList.add("dark-mode");
      $("#themeSwitch .layui-icon").removeClass("layui-icon-circle-dot").addClass("layui-icon-light");
      this.updateTaskCardsColor();
      this.updateColorOptions();
    } else {
      $("#themeSwitch .layui-icon").addClass("layui-icon-circle-dot").removeClass("layui-icon-light");
    }
  }
  
  // 切换主题
  toggleTheme() {
    console.log("[Roadmap] Toggling theme");
    const isDarkMode = document.body.classList.toggle("dark-mode");
    console.log("[Roadmap] Setting dark mode to:", isDarkMode);

    // 保存到 localStorage
    localStorage.setItem("darkMode", isDarkMode);

    const $icon = $("#themeSwitch .layui-icon");
    if (isDarkMode) {
      $icon.removeClass("layui-icon-circle-dot").addClass("layui-icon-light");
    } else {
      $icon.removeClass("layui-icon-light").addClass("layui-icon-circle-dot");
    }

    // 更新layer弹窗样式
    if (isDarkMode) {
      layer.style = function (index, options) {
        this.getChildFrame("body", index).addClass("dark-mode");
      };
    } else {
      layer.style = function (index, options) {
        this.getChildFrame("body", index).removeClass("dark-mode");
      };
    }

    // 更新颜色选择器和任务卡片颜色
    this.updateColorOptions();
    this.updateTaskCardsColor();
  }
  
  // 获取当前主题的颜色选项
  getCurrentThemeColors() {
    return document.body.classList.contains("dark-mode") ? this.colorOptions.dark : this.colorOptions.light;
  }
  
  // 更新任务卡片颜色
  updateTaskCardsColor() {
    console.log("[Roadmap] Updating task cards color");
    const colors = this.getCurrentThemeColors();
    const lightColors = this.colorOptions.light;
    const darkColors = this.colorOptions.dark;

    $(".task-card").each(function () {
      const $card = $(this);
      const currentColor = $card.css("background-color");
      console.log("[Roadmap] Current card color:", currentColor);

      // 检查当前颜色是否匹配任何主题色值
      for (const [className, lightColor] of Object.entries(lightColors)) {
        const lightRGB = utils.getRGBColor(lightColor);
        const darkRGB = utils.getRGBColor(darkColors[className]);

        // 如果当前颜色匹配任一主题的颜色，则更新为目标主题的对应颜色
        if (currentColor === lightRGB || currentColor === darkRGB) {
          const newColor = colors[className];
          console.log("[Roadmap] Updating card color to:", newColor);
          $card.css("background-color", newColor).css("border-left-color", newColor);
          break;
        }
      }
    });
  }
  
  // 更新颜色选择器的颜色
  updateColorOptions() {
    const colors = this.getCurrentThemeColors();
    const $colorOptions = $(".color-picker-container");
    if ($colorOptions.length) {
      $colorOptions.empty();
      Object.entries(colors).forEach(([className, color]) => {
        $colorOptions.append(`
                    <div class="color-option ${className}" 
                         data-color="${color}" 
                         style="background-color: ${color}">
                    </div>
                `);
      });
    }
  }
}