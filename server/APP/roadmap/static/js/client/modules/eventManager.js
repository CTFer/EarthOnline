// 事件管理模块
class EventManager {
  // 初始化所有事件绑定
  init() {
    // 绑定添加任务的处理逻辑
    this.bindAddTaskEvent();
    
    // 绑定任务状态切换事件
    this.bindTaskStatusEvent();
    
    // 绑定编辑任务事件
    this.bindEditTaskEvent();
    
    // 绑定删除任务事件
    this.bindDeleteTaskEvent();
    
    // 绑定主题切换事件
    this.bindThemeSwitchEvent();
    
    // 绑定退出登录事件
    this.bindLogoutEvent();
    
    // 绑定登录表单提交事件
    this.bindLoginSubmitEvent();
  }
  
  // 绑定添加任务事件
  bindAddTaskEvent() {
    $(document).on("click", ".add-task-btn", utils.throttle(function() {
      const status = $(this).data("status");
      
      formManager.openTaskForm("添加任务", { status }, function(formData) {
        formData.status = status;
        formData.playerId = localStorage.getItem("Roadmap_PlayerId");
        
        // 生成临时ID
        const tempId = 'temp_' + Date.now();
        
        // 创建临时任务卡片并立即显示
        const tempTask = {
          id: tempId,
          name: formData.name,
          description: formData.description,
          color: formData.color,
          status: status,
          order: $(`#${status.toLowerCase()}-list .task-card`).length
        };
        
        // 关闭表单
        layer.closeAll();
        
        // 立即在界面上添加任务卡片
        const $tempCard = taskManager.createTaskCard(tempTask);
        $tempCard.addClass('task-card-pending');
        $(`#${status.toLowerCase()}-list`).append($tempCard);
        taskManager.updateTaskCounts();

        // 发送异步请求
        $.ajax({
          url: "/roadmap/api",
          method: "POST",
          contentType: "application/json",
          data: JSON.stringify(formData),
          success: function(res) {
            try {
              const data = typeof res === "string" ? JSON.parse(res) : res;
              if (data.code === 0) {
                // 更新临时卡片的ID和其他服务器返回的数据
                $tempCard
                  .removeClass('task-card-pending')
                  .attr('data-id', data.data.id)
                  .data('task', data.data);
                
                layer.msg("添加成功", { icon: 1 });
              } else {
                // 添加失败，移除临时卡片
                $tempCard.remove();
                taskManager.updateTaskCounts();
                layer.msg("添加失败: " + data.msg, { icon: 2 });
              }
            } catch (e) {
              console.error("[Roadmap] Error parsing response:", e);
              // 添加失败，移除临时卡片
              $tempCard.remove();
              taskManager.updateTaskCounts();
              layer.msg("数据解析错误", { icon: 2 });
            }
          },
          error: function() {
            // 请求失败，移除临时卡片
            $tempCard.remove();
            taskManager.updateTaskCounts();
            layer.msg("网络请求失败", { icon: 2 });
          }
        });
      });
    }, 1000));
  }
  
  // 绑定任务状态切换事件
  bindTaskStatusEvent() {
    $(document).on("click", ".complete-task", (e) => {
      e.stopPropagation();
      const $btn = $(e.target).closest(".complete-task");
      const $card = $btn.closest(".task-card");
      const taskId = $card.data("id");
      const nextStatus = $btn.data("next-status");
      
      // 获取任务数据
      const taskData = $card.data("task");
      
      // 保留当前顺序
      const currentOrder = taskData.order;

      // 确认对话框
      layer.confirm("确定要更新任务状态吗？", { icon: 3, title: "提示" }, function (index) {
        dragManager.updateTaskStatus(taskId, nextStatus, currentOrder, taskData);
        layer.close(index);
      });
    });
  }
  
  // 绑定编辑任务事件
  bindEditTaskEvent() {
    $(document).on("click", ".edit-task", (e) => {
      e.stopPropagation();
      const taskCard = $(e.target).closest(".task-card");
      const taskData = taskCard.data("task");
      const taskId = taskData.id;

      formManager.openTaskForm("编辑任务", taskData, function (formData) {
        $.ajax({
          url: `/roadmap/api/${taskId}`,
          method: "PUT",
          contentType: "application/json",
          data: JSON.stringify(formData),
          success: function (res) {
            try {
              const data = typeof res === "string" ? JSON.parse(res) : res;
              if (data.code === 0) {
                layer.closeAll();
                taskManager.loadTasks();
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
  }
  
  // 绑定删除任务事件
  bindDeleteTaskEvent() {
    $(document).on("click", ".delete-task", (e) => {
      e.stopPropagation();
      const taskCard = $(e.target).closest(".task-card");
      const taskId = taskCard.data("id");

      layer.confirm("确定要删除这个任务吗？", { icon: 3, title: "提示" }, function (index) {
        $.ajax({
          url: `/roadmap/api/${taskId}`,
          method: "DELETE",
          success: function (res) {
            try {
              const data = typeof res === "string" ? JSON.parse(res) : res;
              if (data.code === 0) {
                taskManager.loadTasks();
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
  }
  
  // 绑定主题切换事件
  bindThemeSwitchEvent() {
    $("#themeSwitch").on("click", () => themeManager.toggleTheme());
  }
  
  // 绑定退出登录事件
  bindLogoutEvent() {
    $(document).on("click", ".logout-btn", () => authManager.logout());
  }
  
  // 绑定登录表单提交事件
  bindLoginSubmitEvent() {
    form.on("submit(loginSubmit)", function (data) {
      authManager.loginSubmit(data);
      return false;
    });
  }
}
