// 任务管理模块
class TaskManager {
  // 初始化任务管理
  init() {
    console.log("[Roadmap] Initializing task manager");
  }
  
  // 加载任务
  loadTasks() {
    console.log("[Roadmap] Loading tasks");
    $.get("/roadmap/api", function (res) {
      try {
        const data = typeof res === "string" ? JSON.parse(res) : res;
        if (data.code === 0) {
          this.renderTasks(data.data);
          themeManager.init();
        } else {
          layer.msg("加载任务失败: " + data.msg, { icon: 2 });
        }
      } catch (e) {
        console.error("[Roadmap] Error parsing response:", e);
        layer.msg("数据解析错误", { icon: 2 });
      }
    }.bind(this));
  }
  
  // 渲染任务卡片
  renderTasks(tasks) {
    console.log("[Roadmap] Rendering tasks:", tasks);
    $(".task-list").empty();

    const taskGroups = {
      PLANNED: [],
      WORKING: [],
      COMPLETED: [],
    };

    // 按状态分组
    tasks.forEach((task) => {
      if (taskGroups[task.status]) {
        taskGroups[task.status].push(task);
      }
    });

    // 对每个状态的任务排序
    Object.keys(taskGroups).forEach((status) => {
      // 自定义排序逻辑：
      // 1. 置顶任务（order=-1）排在前面
      // 2. 置顶任务按edittime倒序排序（最新置顶的在最前面）
      // 3. 普通任务按order正序排序
      taskGroups[status].sort((a, b) => {
        // 处理置顶任务
        if (a.order === -1 && b.order !== -1) {
          return -1; // a是置顶，排在前面
        }
        if (a.order !== -1 && b.order === -1) {
          return 1; // b是置顶，排在前面
        }
        if (a.order === -1 && b.order === -1) {
          // 两个都是置顶，按edittime倒序排序
          return b.edittime - a.edittime;
        }
        // 普通任务按order正序排序
        return (a.order || 0) - (b.order || 0);
      });
      
      const listId = `#${status.toLowerCase()}-list`;
      taskGroups[status].forEach((task) => {
        $(listId).append(this.createTaskCard(task));
      });
    });

    dragManager.initDragAndDrop();
    this.updateTaskCounts();
  }
  
  // 创建任务卡片
  createTaskCard(task) {
    console.log("[Roadmap] Creating task card:", task);

    // 检查周期任务是否过期
    const currentTime = Math.floor(Date.now() / 1000);
    const isOverdue = task.is_cycle_task && task.next_reminder_time && task.next_reminder_time <= currentTime;
    
    // 根据任务状态决定是否显示完成按钮和按钮图标
    let completeButton = "";
    if (task.status !== "COMPLETED") {
      if (task.is_cycle_task) {
        // 周期任务，显示"完成本次任务"按钮
        completeButton = `
                <button class="layui-btn layui-btn-xs layui-btn-normal complete-cycle-task" 
                        data-task-id="${task.id}" 
                        title="完成本次任务">
                    <i class="layui-icon">&#xe605;</i>
                </button>
            `;
      } else {
        // 普通任务
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
    }

    // 添加置顶按钮，仅在工作中状态显示
    let pinButton = "";
    if (task.status === "WORKING" || task.status === "PLANNED") {
      const isPinned = task.order === -1;
      pinButton = `
                <button class="layui-btn layui-btn-xs layui-bg-blue pin-task" 
                        data-pinned="${isPinned}" 
                        title="${isPinned ? "取消置顶" : "置顶"}">
                    <i class="layui-icon">${isPinned ? "&#xe61a;" : "&#xe619;"}</i>
                </button>
            `;
    }

    // 周期任务标记
    let cycleTaskBadge = "";
    if (task.is_cycle_task) {
      // 过期任务使用红色标记
      const badgeStyle = isOverdue ? 
        "background-color: #ff5722; color: white;" : 
        "background-color: #ffb800; color: white;";
      cycleTaskBadge = `
                <span class="cycle-task-badge" style="${badgeStyle} padding: 2px 6px; border-radius: 10px; font-size: 12px; margin-left: 8px;">
                    周期: ${task.cycle_duration || 0}天${isOverdue ? ' (已过期)' : ''}
                </span>
            `;
    }
    
    // 任务卡片额外类名
    const extraClasses = isOverdue ? "task-card-overdue" : "";
    
    return $(`
            <div class="task-card ${extraClasses}" 
                 data-id="${task.id}" 
                 data-order="${task.order || 0}"
                 data-task='${JSON.stringify(task)}'
                 style="background-color: ${task.color || "#ffffff"}"
                 draggable="true">
                <div class="task-content">
                    <h3>${task.name}${cycleTaskBadge}</h3>
                    <p>${task.description || ""}</p>
                    ${task.is_cycle_task && task.next_reminder_time ? `<p style="font-size: 12px; color: ${isOverdue ? '#ff5722' : '#999'};">下次提醒: ${new Date(task.next_reminder_time * 1000).toLocaleString()}</p>` : ""}
                    <div class="task-actions">
                        ${completeButton}
                        ${pinButton}
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
  
  // 更新任务数量显示
  updateTaskCounts() {
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
}