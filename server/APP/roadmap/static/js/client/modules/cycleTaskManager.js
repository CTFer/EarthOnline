// 周期任务管理模块
class CycleTaskManager {
  // 初始化周期任务功能
  init() {
    console.log("[Roadmap] Initializing cycle task manager");
    
    // 绑定周期任务完成事件
    this.bindCompleteCycleTaskEvent();
    
    // 初始化SSE连接
    this.initSSEConnection();
  }
  
  // 更新SSE连接状态
  updateSSEStatus(status) {
    console.log(`[Roadmap SSE] 连接状态更新为: ${status}`);
    
    // 获取状态元素
    const sseStatusElement = document.getElementById('sseStatus');
    const statusDot = sseStatusElement.querySelector('.status-dot');
    const statusValue = sseStatusElement.querySelector('.status-value');
    
    // 移除所有状态类
    sseStatusElement.classList.remove('disconnected', 'connecting', 'connected', 'error');
    statusDot.classList.remove('disconnected', 'connecting', 'connected', 'error');
    
    // 根据状态更新UI
    switch (status) {
      case 'connecting':
        sseStatusElement.classList.add('connecting');
        statusDot.classList.add('connecting');
        statusValue.textContent = '连接中';
        break;
      case 'connected':
        sseStatusElement.classList.add('connected');
        statusDot.classList.add('connected');
        statusValue.textContent = '已连接';
        break;
      case 'error':
        sseStatusElement.classList.add('error');
        statusDot.classList.add('error');
        statusValue.textContent = '连接错误';
        break;
      case 'disconnected':
      default:
        sseStatusElement.classList.add('disconnected');
        statusDot.classList.add('disconnected');
        statusValue.textContent = '未连接';
        break;
    }
  }
  
  // 绑定周期任务完成事件
  bindCompleteCycleTaskEvent() {
    $(document).on("click", ".complete-cycle-task", (e) => this.handleCompleteCycleTask(e));
  }
  
  // 处理周期任务完成点击事件
  handleCompleteCycleTask(e) {
    e.stopPropagation();
    const taskCard = $(e.target).closest(".task-card");
    const taskId = taskCard.data("id");

    layer.confirm("确定要完成本次周期任务吗？系统将自动计算下次提醒时间。", { icon: 3, title: "提示" }, function (index) {
      $.ajax({
        url: `/roadmap/api/${taskId}/complete_cycle`,
        method: "POST",
        success: function (res) {
          try {
            const data = typeof res === "string" ? JSON.parse(res) : res;
            if (data.code === 0) {
              layer.msg(data.msg, { icon: 1 });
              taskManager.loadTasks(); // 刷新任务列表，更新下次提醒时间
            } else {
              layer.msg("操作失败: " + data.msg, { icon: 2 });
            }
          } catch (e) {
            console.error("[Roadmap] Error parsing response:", e);
            layer.msg("数据解析错误", { icon: 2 });
          }
        },
      });
      layer.close(index);
    });
  }
  
  // 初始化SSE连接
  initSSEConnection() {
    console.log("[Roadmap] Initializing SSE connection");
    
    // 更新状态为连接中
    this.updateSSEStatus('connecting');
    
    // 检查浏览器是否支持SSE
    if (typeof EventSource !== "undefined") {
      try {
        // 清除之前的事件源
        if (this.eventSource) {
          this.eventSource.close();
          this.eventSource = null;
        }
        
        // 使用Roadmap模块自己的SSE连接
        const url = `/roadmap/api/sse`;
        console.log("[Roadmap SSE] 连接到: ", url);
        this.eventSource = new EventSource(url);
        
        // 设置事件处理器
        this.setupEventHandlers();
      } catch (error) {
        console.error("[Roadmap SSE] 创建连接失败:", error);
        this.updateSSEStatus('error');
        
        // 降级方案：使用轮询
        console.log("[Roadmap SSE] 降级为轮询模式");
        this.initFallbackPolling();
      }
    } else {
      console.log("[Roadmap SSE] 浏览器不支持SSE，使用轮询模式");
      this.updateSSEStatus('disconnected');
      
      // 降级方案：使用轮询
      this.initFallbackPolling();
    }
  }
  
  // 处理SSE消息
  handleSSEMessage(data) {
    console.log("[Roadmap SSE] 收到消息:", data);
    
    // 根据消息类型处理
    switch (data.type) {
      case "cycle_task_reminder":
        // 周期任务提醒
        this.handleCycleTaskReminder(data.task);
        break;
      case "heartbeat":
      case "ping":
        // 心跳消息，保持连接活跃
        break;
      case "connected":
        // 连接建立消息
        console.log("[Roadmap SSE] 连接已建立");
        this.updateSSEStatus('connected');
        break;
      default:
        console.log("[Roadmap SSE] 未知消息类型:", data.type);
        break;
    }
  }
  
  // 初始化SSE连接事件处理器
  setupEventHandlers() {
    // 连接打开事件
    this.eventSource.onopen = (e) => {
      console.log("[Roadmap SSE] 连接已建立");
      this.updateSSEStatus('connected');
    };
    
    // 连接错误事件
    this.eventSource.onerror = (e) => {
      console.error("[Roadmap SSE] 连接错误:", e);
      this.updateSSEStatus('error');
      
      // 尝试重新连接
      this.eventSource.close();
      setTimeout(() => {
        this.initSSEConnection();
      }, 5000);
    };
    
    // 消息事件（处理没有指定event字段的消息）
    this.eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        this.handleSSEMessage(data);
      } catch (error) {
        console.error("[Roadmap SSE] 解析消息失败:", error);
      }
    };
    
    // 连接确认事件
    this.eventSource.addEventListener('connected', (e) => {
      try {
        const data = JSON.parse(e.data);
        console.log("[Roadmap SSE] 连接确认:", data);
        this.updateSSEStatus('connected');
      } catch (error) {
        console.error("[Roadmap SSE] 解析连接确认失败:", error);
      }
    });
    
    // 心跳事件
    this.eventSource.addEventListener('ping', (e) => {
      try {
        const data = JSON.parse(e.data);
        console.log("[Roadmap SSE] 收到心跳:", data);
      } catch (error) {
        console.error("[Roadmap SSE] 解析心跳失败:", error);
      }
    });
  }
  
  // 处理周期任务提醒
  handleCycleTaskReminder(task) {
    console.log("[Roadmap] Handling cycle task reminder:", task);
    
    // 显示提醒
    this.showCycleTaskReminder(task);
    
    // 刷新任务列表，确保状态已更新
    taskManager.loadTasks();
  }
  
  // 显示周期任务提醒
  showCycleTaskReminder(task) {
    console.log("[Roadmap] Showing cycle task reminder:", task);
    
    // 使用layer显示提醒
    layer.msg(`周期任务提醒: ${task.name} 需要执行了！`, {
      icon: 7,
      time: 3000,
      btn: ['知道了', '查看任务'],
      yes: function(index) {
        layer.close(index);
      },
      btn2: function(index) {
        layer.close(index);
        // 可以添加查看任务的逻辑
        taskManager.loadTasks();
      }
    });
  }
  
  // 初始化降级轮询
  initFallbackPolling() {
    console.log("[Roadmap] Initializing fallback polling");
    
    // 立即检查一次周期任务
    this.checkCycleTasks();
    
    // 每隔5分钟检查一次周期任务
    this.pollingInterval = setInterval(() => {
      this.checkCycleTasks();
    }, 5 * 60 * 1000); // 5分钟
  }
  
  // 检查周期任务是否需要提醒和状态切换（降级方案）
  checkCycleTasks() {
    console.log("[Roadmap] Checking cycle tasks (fallback)");
    
    // 获取当前时间戳
    const currentTime = Math.floor(Date.now() / 1000);
    
    // 遍历所有任务卡片
    const taskCards = document.querySelectorAll(".task-card");
    taskCards.forEach(card => {
      const $card = $(card);
      const task = $card.data("task");
      
      // 检查是否是周期任务
      if (task && task.is_cycle_task && task.next_reminder_time) {
        // 检查是否到达提醒时间
        if (task.next_reminder_time <= currentTime) {
          // 显示提醒
          this.showCycleTaskReminder(task);
          
          // 如果任务状态不是工作中，自动切换到工作中
          if (task.status !== "WORKING") {
            this.updateTaskStatus(task.id, "WORKING");
          }
        }
      }
    });
  }
  
  // 更新任务状态
  updateTaskStatus(taskId, status) {
    console.log("[Roadmap] Updating cycle task status:", taskId, status);
    
    // 发送请求更新任务状态
    $.ajax({
      url: `/roadmap/api/${taskId}`,
      method: "PUT",
      contentType: "application/json",
      data: JSON.stringify({ status: status }),
      success: function(res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code === 0) {
            // 更新成功，刷新任务列表
            taskManager.loadTasks();
          } else {
            console.error("[Roadmap] Error updating cycle task status:", data.msg);
          }
        } catch (e) {
          console.error("[Roadmap] Error parsing response:", e);
        }
      },
      error: function(xhr, status, error) {
        console.error("[Roadmap] Error updating cycle task status:", error);
      }
    });
  }
}
