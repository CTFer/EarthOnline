layui.use(["jquery", "layer", "form", "laytpl"], function () {
  const $ = layui.jquery;
  const layer = layui.layer;
  const form = layui.form;
  const laytpl = layui.laytpl;

  console.log("[Roadmap] Initializing roadmap module");

  // 定义颜色选项 - 明亮模式和暗黑模式
  const colorOptions = {
    light: {
      "layui-bg-blue": "#1e9fff", // 经典蓝
      "layui-bg-green": "#16b777", // 清新绿
      "layui-bg-cyan": "#16baaa", // 蓝绿色
      "layui-bg-orange": "#ffb800", // 警示色
      "layui-bg-red": "#ff5722", // 错误色
      "layui-bg-purple": "#a233c6", // 紫色
      "layui-bg-gray": "#fafafa", // 浅灰
    },
    dark: {
      "layui-bg-blue": "#0d47a1", // 深蓝
      "layui-bg-green": "#1b5e20", // 深绿
      "layui-bg-cyan": "#006064", // 深青
      "layui-bg-orange": "#e65100", // 深橙
      "layui-bg-red": "#b71c1c", // 深红
      "layui-bg-purple": "#4a148c", // 深紫
      "layui-bg-gray": "#424242", // 深灰
    },
  };

  // 获取当前主题的颜色选项
  function getCurrentThemeColors() {
    return document.body.classList.contains("dark-mode") ? colorOptions.dark : colorOptions.light;
  }

  // 更新任务卡片颜色
  function updateTaskCardsColor() {
    console.log("[Roadmap] Updating task cards color");
    const colors = getCurrentThemeColors();
    const lightColors = colorOptions.light;
    const darkColors = colorOptions.dark;

    $(".task-card").each(function () {
      const $card = $(this);
      const currentColor = $card.css("background-color");
      console.log("[Roadmap] Current card color:", currentColor);

      // 检查当前颜色是否匹配任何主题色值
      for (const [className, lightColor] of Object.entries(lightColors)) {
        const lightRGB = getRGBColor(lightColor);
        const darkRGB = getRGBColor(darkColors[className]);

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

  // 将十六进制颜色转换为RGB格式
  function getRGBColor(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgb(${r}, ${g}, ${b})`;
  }

  // 更新颜色选择器的颜色
  function updateColorOptions() {
    const colors = getCurrentThemeColors();
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

  // 初始化主题
  function initTheme() {
    console.log("[Roadmap] Initializing theme");
    const isDarkMode = localStorage.getItem("darkMode") === "true";
    console.log("[Roadmap] Dark mode from localStorage:", isDarkMode);

    if (isDarkMode) {
      document.body.classList.add("dark-mode");
      $("#themeSwitch .layui-icon").removeClass("layui-icon-circle-dot").addClass("layui-icon-light");
      updateTaskCardsColor();
      updateColorOptions();
    } else {
      $("#themeSwitch .layui-icon").addClass("layui-icon-circle-dot").removeClass("layui-icon-light");
    }
  }

  // 切换主题
  function toggleTheme() {
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
    updateColorOptions();
    updateTaskCardsColor();
  }

  // 绑定主题切换事件
  $("#themeSwitch").on("click", function () {
    toggleTheme();
  });

  // 检查登录状态
  function checkLogin() {
    console.log("[Roadmap] Checking login status");
    $.get("/api/roadmap/check_login", function (res) {
      try {
        const data = typeof res === "string" ? JSON.parse(res) : res;
        if (data.code === 1 && data.data) {
          // 已登录
          $("#currentUser").text(data.data.username);
          loadTasks();
        } else {
          // 未登录，显示登录框
          showLoginForm();
        }
      } catch (e) {
        console.error("[Roadmap] Error checking login status:", e);
        layer.msg("检查登录状态失败", { icon: 2 });
      }
    });
  }

  // 显示登录表单
  function showLoginForm() {
    console.log("[Roadmap] Showing login form");
    layer.open({
      type: 1,
      title: "用户登录",
      content: $("#loginFormTpl").html(),
      closeBtn: 0,
      area: ["600px", "500px"],
    });
  }

  // 登录表单提交
  form.on("submit(loginSubmit)", function (data) {
    console.log("[Roadmap] Submitting login form");
    $.ajax({
      url: "/api/roadmap/login",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(data.field),
      success: function (res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code === 0) {
            layer.closeAll();
            $("#currentUser").text(data.data.username);
            loadTasks();
            layer.msg("登录成功", { icon: 1 });
            localStorage.setItem("Roadmap_PlayerId", data.data.user_id);
          } else {
            layer.msg("登录失败: " + data.msg, { icon: 2 });
          }
        } catch (e) {
          console.error("[Roadmap] Error parsing login response:", e);
          layer.msg("数据解析错误", { icon: 2 });
        }
      },
    });
    return false;
  });

  // 退出登录
  $(".logout-btn").on("click", function () {
    console.log("[Roadmap] Logging out");
    layer.confirm("确定要退出登录吗？", { icon: 3, title: "提示" }, function (index) {
      $.get("/api/roadmap/logout", function (res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code === 0) {
            layer.msg("已退出登录", { icon: 1 });
            setTimeout(() => {
              window.location.reload();
            }, 1000);
          } else {
            layer.msg("退出失败: " + data.msg, { icon: 2 });
          }
        } catch (e) {
          console.error("[Roadmap] Error logging out:", e);
          layer.msg("数据解析错误", { icon: 2 });
        }
      });
      layer.close(index);
    });
  });

  // 初始化数据
  function loadTasks() {
    console.log("[Roadmap] Loading tasks");
    $.get("/api/roadmap", function (res) {
      try {
        const data = typeof res === "string" ? JSON.parse(res) : res;
        if (data.code === 0) {
          renderTasks(data.data);
          initTheme();
        } else {
          layer.msg("加载任务失败: " + data.msg, { icon: 2 });
        }
      } catch (e) {
        console.error("[Roadmap] Error parsing response:", e);
        layer.msg("数据解析错误", { icon: 2 });
      }
    });
  }

  // 渲染任务卡片
  function renderTasks(tasks) {
    console.log("[Roadmap] Rendering tasks:", tasks);
    $(".task-list").empty();

    const taskGroups = {
      PLANNED: [],
      WORKING: [],
      COMPLETED: [],
    };

    // 按状态分组并按order排序
    tasks.forEach((task) => {
      if (taskGroups[task.status]) {
        taskGroups[task.status].push(task);
      }
    });

    // 对每个状态的任务按order排序
    Object.keys(taskGroups).forEach((status) => {
      taskGroups[status].sort((a, b) => (a.order || 0) - (b.order || 0));
      const listId = `#${status.toLowerCase()}-list`;
      taskGroups[status].forEach((task) => {
        $(listId).append(createTaskCard(task));
      });
    });

    initDragAndDrop();
    updateTaskCounts();
  }

  // 创建任务卡片
  function createTaskCard(task) {
    console.log("[Roadmap] Creating task card:", task);

    // 根据任务状态决定是否显示完成按钮和按钮图标
    let completeButton = "";
    if (task.status !== "COMPLETED") {
      const nextStatus = task.status === "PLANNED" ? "WORKING" : "COMPLETED";
      const buttonIcon = task.status === "PLANNED" ? "&#xe63c;" : "&#xe605;"; // 工具: &#xe63c;, 对勾: &#xe605;
      completeButton = `
                <button class="layui-btn layui-btn-xs layui-btn-normal complete-task" 
                        data-next-status="${nextStatus}" 
                        title="${task.status === "PLANNED" ? "开始工作" : "标记完成"}">
                    <i class="layui-icon">${buttonIcon}</i>
                </button>
            `;
    }

    return $(`
            <div class="task-card" 
                 data-id="${task.id}" 
                 data-order="${task.order || 0}"
                 data-task='${JSON.stringify(task)}'
                 style="background-color: ${task.color || "#ffffff"}"
                 draggable="true">
                <div class="task-content">
                    <h3>${task.name}</h3>
                    <p>${task.description || ""}</p>
                    <div class="task-actions">
                        ${completeButton}
                        <button class="layui-btn layui-btn-xs edit-task">
                            <i class="layui-icon">&#xe642;</i>
                        </button>
                        <button class="layui-btn layui-btn-xs layui-btn-danger delete-task">
                            <i class="layui-icon">&#xe640;</i>
                        </button>
                    </div>
                </div>
            </div>
        `);
  }

  // 打开任务表单
  function openTaskForm(title, data = {}, submitCallback) {
    console.log("[Roadmap] Opening task form:", { title, data });

    layer.open({
      type: 1,
      title: title,
      area: ["500px", "400px"],
      content: $("#taskFormTpl").html(),
      success: function (layero) {
        const $form = $(layero).find(".layui-form");

        // 填充表单数据
        $form.find("input[name=name]").val(data.name || "");
        $form.find("textarea[name=description]").val(data.description || "");

        // 渲染颜色选项
        const $colorOptions = $form.find("#colorOptions");
        $colorOptions.empty().addClass("color-options");

        // 添加颜色选择器容器
        const $colorContainer = $('<div class="color-picker-container"></div>');
        $colorOptions.append($colorContainer);

        // 渲染颜色选项
        const colors = getCurrentThemeColors();
        Object.entries(colors).forEach(([className, color]) => {
          const $colorBox = $(`
                        <div class="color-option ${className} ${data.color === color ? "selected" : ""}" 
                             data-color="${color}"
                             title="${color}">
                            <div class="color-preview"></div>
                            ${data.color === color ? '<i class="layui-icon layui-icon-ok"></i>' : ""}
                        </div>
                    `);

          $colorContainer.append($colorBox);
        });

        // 添加隐藏的颜色输入
        $colorOptions.append(`
                    <input type="hidden" name="color" value="${data.color || "#ffffff"}">
                `);

        // 颜色选择事件
        $colorOptions.on("click", ".color-option", function () {
          const $this = $(this);
          const color = $this.data("color");
          console.log("[Roadmap] Color selected:", color);

          // 更新隐藏输入值
          $form.find("input[name=color]").val(color);

          // 更新选中状态
          $colorOptions.find(".color-option").removeClass("selected").find(".layui-icon").remove();
          $this.addClass("selected").append('<i class="layui-icon layui-icon-ok"></i>');
        });

        form.render();
      },
    });

    // 表单提交
    form.on("submit(submitTask)", function (formData) {
      console.log("[Roadmap] Submitting task form:", formData.field);
      submitCallback(formData.field);
      return false;
    });
  }

  // 初始化拖拽
  function initDragAndDrop() {
    console.log("[Roadmap] Initializing drag and drop");

    const taskCards = document.querySelectorAll(".task-card");
    const taskLists = document.querySelectorAll(".task-list");

    taskCards.forEach((card) => {
      card.addEventListener("dragstart", handleDragStart);
      card.addEventListener("dragend", handleDragEnd);
    });

    taskLists.forEach((list) => {
      list.addEventListener("dragover", handleDragOver);
      list.addEventListener("dragleave", handleDragLeave);
      list.addEventListener("drop", handleDrop);
    });
  }

  function handleDragStart(e) {
    console.log("[Roadmap] Drag start");
    e.dataTransfer.setData("text/plain", e.target.dataset.id);
    e.target.classList.add("dragging");
  }

  function handleDragEnd(e) {
    console.log("[Roadmap] Drag end");
    e.target.classList.remove("dragging");
    document.querySelectorAll(".task-list").forEach((list) => {
      list.classList.remove("drag-over");
    });
  }

  function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add("drag-over");

    const draggingCard = document.querySelector(".dragging");
    const list = e.currentTarget;
    const cards = [...list.querySelectorAll(".task-card:not(.dragging)")];

    const afterCard = cards.find((card) => {
      const rect = card.getBoundingClientRect();
      const cardVerticalCenter = rect.top + rect.height / 2;
      return e.clientY < cardVerticalCenter;
    });

    if (afterCard) {
      list.insertBefore(draggingCard, afterCard);
    } else {
      list.appendChild(draggingCard);
    }
  }

  function handleDragLeave(e) {
    e.currentTarget.classList.remove("drag-over");
  }

  function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");

    const taskId = e.dataTransfer.getData("text/plain");
    const newStatus = e.currentTarget.parentElement.dataset.status;

    // 修改排序逻辑：获取所有同状态的卡片，计算新的顺序
    const allCards = [...e.currentTarget.querySelectorAll(".task-card")];
    const droppedCard = allCards.find((card) => card.dataset.id === taskId);
    const newOrder = allCards.indexOf(droppedCard);

    console.log("[Roadmap] Dropping task:", {
      taskId,
      newStatus,
      newOrder,
      allCards: allCards.map((card) => card.dataset.id),
    });

    // 更新所有受影响卡片的顺序
    allCards.forEach((card, index) => {
      const cardId = card.dataset.id;
      if (cardId !== taskId && index !== parseInt(card.dataset.order)) {
        updateTaskOrder(cardId, index);
      }
    });

    // 更新拖动卡片的状态和顺序
    updateTaskStatus(taskId, newStatus, newOrder);
  }

  // 添加新函数：仅更新任务顺序
  function updateTaskOrder(taskId, order) {
    console.log("[Roadmap] Updating task order:", { taskId, order });
    $.ajax({
      url: `/api/roadmap/${taskId}`,
      method: "PUT",
      contentType: "application/json",
      data: JSON.stringify({ order: order }),
      success: function (res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code !== 0) {
            console.error("[Roadmap] Error updating task order:", data.msg);
          }
        } catch (e) {
          console.error("[Roadmap] Error parsing response:", e);
        }
      },
    });
  }

  // 更新任务状态
  function updateTaskStatus(taskId, status, order) {
    console.log("[Roadmap] Updating task status:", { taskId, status, order });
    $.ajax({
      url: `/api/roadmap/${taskId}`,
      method: "PUT",
      contentType: "application/json",
      data: JSON.stringify({
        status: status,
        order: order,
      }),
      success: function (res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code === 0) {
            // 不再立即刷新,让用户看到拖拽效果
            setTimeout(loadTasks, 500);
          } else {
            layer.msg("更新失败: " + data.msg, { icon: 2 });
            loadTasks(); // 失败时立即刷新
          }
        } catch (e) {
          console.error("[Roadmap] Error parsing response:", e);
          layer.msg("数据解析错误", { icon: 2 });
          loadTasks();
        }
      },
    });
  }

  // 添加任务
  $(".add-task-btn").on("click", function () {
    const status = $(this).data("status");
    console.log("[Roadmap] Opening add task dialog for status:", status);

    openTaskForm("添加任务", { status }, function (formData) {
      formData.status = status;
      formData.playerId = localStorage.getItem("Roadmap_PlayerId");
      $.ajax({
        url: "/api/roadmap/add",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify(formData),
        success: function (res) {
          try {
            const data = typeof res === "string" ? JSON.parse(res) : res;
            if (data.code === 0) {
              layer.closeAll();
              loadTasks();
              layer.msg("添加成功", { icon: 1 });
            } else {
              layer.msg("添加失败: " + data.msg, { icon: 2 });
            }
          } catch (e) {
            console.error("[Roadmap] Error parsing response:", e);
            layer.msg("数据解析错误", { icon: 2 });
          }
        },
      });
    });
  });

  // 编辑任务
  $(document).on("click", ".edit-task", function (e) {
    e.stopPropagation();
    const taskCard = $(this).closest(".task-card");
    const taskData = taskCard.data("task");
    const taskId = taskData.id;

    console.log("[Roadmap] Edit task:", taskData);

    openTaskForm("编辑任务", taskData, function (formData) {
      $.ajax({
        url: `/api/roadmap/${taskId}`,
        method: "PUT",
        contentType: "application/json",
        data: JSON.stringify(formData),
        success: function (res) {
          try {
            const data = typeof res === "string" ? JSON.parse(res) : res;
            if (data.code === 0) {
              layer.closeAll();
              loadTasks();
              layer.msg("更新成功", { icon: 1 });
            } else {
              layer.msg("更新失败: " + data.msg, { icon: 2 });
            }
          } catch (e) {
            console.error("[Roadmap] Error parsing response:", e);
            layer.msg("数据解析错误", { icon: 2 });
          }
        },
      });
    });
  });

  // 删除任务
  $(document).on("click", ".delete-task", function (e) {
    e.stopPropagation();
    const taskCard = $(this).closest(".task-card");
    const taskId = taskCard.data("id");

    console.log("[Roadmap] Deleting task:", taskId);

    layer.confirm("确定要删除这个任务吗？", { icon: 3, title: "提示" }, function (index) {
      $.ajax({
        url: `/api/roadmap/${taskId}`,
        method: "DELETE",
        success: function (res) {
          try {
            const data = typeof res === "string" ? JSON.parse(res) : res;
            if (data.code === 0) {
              loadTasks();
              layer.msg("删除成功", { icon: 1 });
            } else {
              layer.msg("删除失败: " + data.msg, { icon: 2 });
            }
          } catch (e) {
            console.error("[Roadmap] Error parsing response:", e);
            layer.msg("数据解析错误", { icon: 2 });
          }
        },
      });
      layer.close(index);
    });
  });

  // 绑定任务状态切换事件
  $(document).on("click", ".complete-task", function (e) {
    e.stopPropagation();
    const $btn = $(this);
    const $card = $btn.closest(".task-card");
    const taskId = $card.data("id");
    const nextStatus = $btn.data("next-status");

    console.log("[Roadmap] Complete task clicked:", { taskId, nextStatus });

    // 确认对话框
    layer.confirm("确定要更新任务状态吗？", { icon: 3, title: "提示" }, function (index) {
      updateTaskStatus(taskId, nextStatus);
      layer.close(index);
    });
  });

  // 更新任务数量显示
  function updateTaskCounts() {
    console.log("[Roadmap] Updating task counts");
    
    // 获取每个状态的任务数量
    const statusCounts = {
        PLANNED: $("#planned-list .task-card").length,
        WORKING: $("#working-list .task-card").length,
        COMPLETED: $("#completed-list .task-card").length
    };
    
    // 更新显示
    Object.entries(statusCounts).forEach(([status, count]) => {
        $(`.task-column[data-status="${status}"] .task-count`).text(`(${count})`);
    });
    
    console.log("[Roadmap] Task counts updated:", statusCounts);
  }

  // 修改初始化逻辑
  checkLogin(); // 替换原来的 loadTasks()
});
