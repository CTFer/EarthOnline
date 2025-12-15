// 拖拽管理模块
class DragManager {
  // 初始化拖拽和放置功能
  initDragAndDrop() {
    console.log("[Roadmap] Initializing drag and drop");

    const taskCards = document.querySelectorAll(".task-card");
    const taskLists = document.querySelectorAll(".task-list");

      // 存储当前拖拽的卡片信息
    this.draggingElement = null;
    this.draggingOffset = { x: 0, y: 0 };
    this.dragClone = null; // 拖拽克隆元素
    this.insertionMarker = null; // 插入位置标记
    this.originalRect = null; // 原元素位置信息
    this.currentTaskList = null; // 当前任务列表

    // 移除所有现有事件监听器，避免重复绑定
    taskCards.forEach((card) => {
      // 先移除可能存在的事件监听器
      card.removeEventListener("dragstart", this.handleDragStart);
      card.removeEventListener("dragend", this.handleDragEnd);
      card.removeEventListener("touchstart", this.handleTouchStart);
      card.removeEventListener("touchmove", this.handleTouchMove);
      card.removeEventListener("touchend", this.handleTouchEnd);
      
      // 重新绑定鼠标事件监听器
      card.addEventListener("dragstart", (e) => this.handleDragStart(e));
      card.addEventListener("dragend", (e) => this.handleDragEnd(e));
      
      // 绑定触摸屏事件监听器
      card.addEventListener("touchstart", (e) => this.handleTouchStart(e));
      card.addEventListener("touchmove", (e) => this.handleTouchMove(e), { passive: false });
      card.addEventListener("touchend", (e) => this.handleTouchEnd(e));
      
      // 添加可触摸样式
      card.style.touchAction = "none";
      card.style.cursor = "grab";
    });

    taskLists.forEach((list) => {
      // 先移除可能存在的事件监听器
      list.removeEventListener("dragover", this.handleDragOver);
      list.removeEventListener("dragleave", this.handleDragLeave);
      list.removeEventListener("drop", this.handleDrop);
      list.removeEventListener("touchmove", this.handleTouchMove);
      list.removeEventListener("touchend", this.handleTouchEnd);
      
      // 重新绑定鼠标事件监听器
      list.addEventListener("dragover", (e) => this.handleDragOver(e));
      list.addEventListener("dragleave", (e) => this.handleDragLeave(e));
      list.addEventListener("drop", (e) => this.handleDrop(e));
      
      // 绑定触摸屏事件监听器
      list.addEventListener("touchmove", (e) => this.handleTouchMove(e), { passive: false });
      list.addEventListener("touchend", (e) => this.handleTouchEnd(e));
    });
    
    // 创建插入位置标记
    this.insertionMarker = document.createElement('div');
    this.insertionMarker.className = 'insertion-marker';
    this.insertionMarker.style.cssText = `
      height: 4px;
      background-color: #1e9fff;
      margin: 4px 0;
      border-radius: 2px;
      opacity: 0;
      transition: opacity 0.2s ease;
      width: 95%;
      margin-left: 2.5%;
    `;
    document.body.appendChild(this.insertionMarker);
  }
  
  // 处理触摸屏开始事件
  handleTouchStart(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const card = e.currentTarget;
    
    // 存储拖拽信息
    this.draggingElement = card;
    this.currentTaskList = card.closest(".task-list");
    
    // 获取原元素位置
    this.originalRect = card.getBoundingClientRect();
    this.draggingOffset = {
      x: touch.clientX - this.originalRect.left,
      y: touch.clientY - this.originalRect.top
    };
    
    // 创建拖拽克隆元素
    this.createDragClone();
    
    // 添加拖拽样式到原元素
    card.classList.add("dragging");
    card.style.opacity = "0.5";
    card.style.cursor = "grabbing";
  }
  
  // 创建拖拽克隆元素
  createDragClone() {
    const card = this.draggingElement;
    
    // 创建克隆
    this.dragClone = card.cloneNode(true);
    
    // 设置克隆样式
    this.dragClone.style.cssText = `
      position: absolute;
      top: ${this.originalRect.top}px;
      left: ${this.originalRect.left}px;
      width: ${this.originalRect.width}px;
      z-index: 9999;
      cursor: grabbing;
      pointer-events: none;
      opacity: 1;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      transform: translateZ(0);
      transition: none;
    `;
    
    // 添加到文档
    document.body.appendChild(this.dragClone);
  }
  
  // 处理触摸屏移动事件
  handleTouchMove(e) {
    e.preventDefault();
    if (!this.draggingElement || !this.dragClone) return;
    
    const touch = e.touches[0];
    
    // 更新克隆元素位置
    const newLeft = touch.clientX - this.draggingOffset.x;
    const newTop = touch.clientY - this.draggingOffset.y;
    this.dragClone.style.left = `${newLeft}px`;
    this.dragClone.style.top = `${newTop}px`;
    
    // 查找当前触摸点下的任务列表
    const touchElement = document.elementFromPoint(touch.clientX, touch.clientY);
    const taskList = touchElement.closest(".task-list");
    
    // 处理任务列表切换
    if (taskList) {
      // 更新当前任务列表
      this.currentTaskList = taskList;
      
      // 高亮显示当前任务列表
      document.querySelectorAll(".task-list").forEach(list => {
        list.classList.remove("drag-over");
      });
      taskList.classList.add("drag-over");
      
      // 计算插入位置
      this.updateInsertionMarker(taskList, touch.clientY);
    } else {
      // 移除高亮和插入标记
      document.querySelectorAll(".task-list").forEach(list => {
        list.classList.remove("drag-over");
      });
      this.hideInsertionMarker();
    }
  }
  
  // 更新插入位置标记
  updateInsertionMarker(taskList, y) {
    const cards = [...taskList.querySelectorAll(".task-card:not(.dragging)")];
    let insertionIndex = this.findInsertionIndex(taskList, y);
    
    // 显示插入标记
    this.insertionMarker.style.opacity = "1";
    
    // 获取插入位置
    if (insertionIndex === cards.length) {
      // 插入到末尾
      if (cards.length === 0) {
        // 列表为空，直接插入到顶部
        taskList.appendChild(this.insertionMarker);
      } else {
        // 插入到最后一个卡片后面
        cards[cards.length - 1].after(this.insertionMarker);
      }
    } else {
      // 插入到指定索引位置
      cards[insertionIndex].before(this.insertionMarker);
    }
  }
  
  // 隐藏插入位置标记
  hideInsertionMarker() {
    this.insertionMarker.style.opacity = "0";
    // 从文档中移除
    if (this.insertionMarker.parentElement) {
      this.insertionMarker.parentElement.removeChild(this.insertionMarker);
    }
  }
  
  // 查找插入位置
  findInsertionIndex(taskList, y) {
    const cards = [...taskList.querySelectorAll(".task-card:not(.dragging)")];
    for (let i = 0; i < cards.length; i++) {
      const card = cards[i];
      const rect = card.getBoundingClientRect();
      const cardCenter = rect.top + rect.height / 2;
      if (y < cardCenter) {
        return i;
      }
    }
    return cards.length;
  }
  
  // 处理触摸屏结束事件
  handleTouchEnd(e) {
    e.preventDefault();
    if (!this.draggingElement || !this.dragClone) return;
    
    const card = this.draggingElement;
    const touch = e.changedTouches[0];
    
    // 清理拖拽状态
    this.cleanupDrag();
    
    // 查找触摸结束位置的任务列表
    const touchElement = document.elementFromPoint(touch.clientX, touch.clientY);
    const taskList = touchElement.closest(".task-list");
    
    // 如果拖到了任务列表中，执行放置逻辑
    if (taskList) {
      // 获取任务信息
      const taskId = card.dataset.id;
      const newStatus = taskList.parentElement.dataset.status;
      
      // 计算插入位置
      const insertionIndex = this.findInsertionIndex(taskList, touch.clientY);
      let newOrder = insertionIndex;
      
      // 获取所有同状态的卡片
      const allCards = [...taskList.querySelectorAll(".task-card:not(.dragging)")];
      
      // 将卡片移动到新位置
      if (insertionIndex === allCards.length) {
        // 插入到末尾
        taskList.appendChild(card);
      } else {
        // 插入到指定位置
        allCards[insertionIndex].before(card);
      }
      
      // 分离置顶卡片和普通卡片
      const updatedCards = [...taskList.querySelectorAll(".task-card")];
      const pinnedCards = updatedCards.filter(card => parseInt(card.dataset.order) === -1);
      const normalCards = updatedCards.filter(card => parseInt(card.dataset.order) !== -1);
      
      // 检查被拖动的卡片是否是置顶卡片
      const isDroppedCardPinned = parseInt(card.dataset.order) === -1;
      
      // 更新所有普通卡片的顺序
      normalCards.forEach((card, index) => {
        const cardId = card.dataset.id;
        if (cardId !== taskId && index !== parseInt(card.dataset.order)) {
          this.updateTaskOrder(cardId, index);
        }
      });
      
      try {
        // 获取被拖动卡片的任务数据
        const droppedTask = JSON.parse(card.getAttribute('data-task'));
        
        // 检查是否是周期任务且目标状态是已完成
        if (droppedTask.is_cycle_task && newStatus === 'COMPLETED') {
          layer.msg('周期任务不能标记为已完成，请使用"完成本次任务"按钮', { icon: 2 });
          // 重新加载任务列表，恢复原始状态
          taskManager.loadTasks();
          return;
        }
        
        // 更新拖动卡片的状态和顺序
        // 如果是置顶卡片，保持其order=-1
        if (isDroppedCardPinned) {
          this.updateTaskStatus(taskId, newStatus, -1, droppedTask);
        } else {
          this.updateTaskStatus(taskId, newStatus, newOrder, droppedTask);
        }
      } catch (e) {
        console.error("[Roadmap Drag] Error handling touch end:", e);
        layer.msg("拖拽处理失败，请重试", { icon: 2 });
        taskManager.loadTasks();
      }
    } else {
      // 没有拖到任务列表，恢复原始位置
      card.closest(".task-list").appendChild(card);
    }
    
    // 重置拖拽信息
    this.draggingElement = null;
    this.draggingOffset = { x: 0, y: 0 };
    this.currentTaskList = null;
  }
  
  // 清理拖拽状态
  cleanupDrag() {
    // 移除拖拽样式
    if (this.draggingElement) {
      this.draggingElement.classList.remove("dragging");
      this.draggingElement.style.opacity = "1";
      this.draggingElement.style.cursor = "grab";
    }
    
    // 移除拖拽克隆
    if (this.dragClone && this.dragClone.parentElement) {
      this.dragClone.parentElement.removeChild(this.dragClone);
      this.dragClone = null;
    }
    
    // 隐藏插入标记
    this.hideInsertionMarker();
    
    // 移除任务列表高亮
    document.querySelectorAll(".task-list").forEach(list => {
      list.classList.remove("drag-over");
    });
  }
  
  // 处理拖拽开始事件
  handleDragStart(e) {
    e.dataTransfer.setData("text/plain", e.target.dataset.id);
    e.target.classList.add("dragging");
  }
  
  // 处理拖拽结束事件
  handleDragEnd(e) {
    e.target.classList.remove("dragging");
    document.querySelectorAll(".task-list").forEach((list) => {
      list.classList.remove("drag-over");
    });
  }
  
  // 处理拖拽经过事件
  handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add("drag-over");

    const draggingCard = document.querySelector(".dragging");
    if (!draggingCard) return; // 防止拖拽过程中卡片被移除导致的错误
    
    const list = e.currentTarget;
    const cards = [...list.querySelectorAll(".task-card:not(.dragging)")];
    
    // 分离置顶卡片和普通卡片
    const pinnedCards = cards.filter(card => parseInt(card.dataset.order) === -1);
    const normalCards = cards.filter(card => parseInt(card.dataset.order) !== -1);
    
    // 检查拖动的卡片是否是置顶卡片
    const isDraggingPinned = parseInt(draggingCard.dataset.order) === -1;
    
    // 找到合适的插入位置
    const afterCard = cards.find((card) => {
      const rect = card.getBoundingClientRect();
      const cardVerticalCenter = rect.top + rect.height / 2;
      return e.clientY < cardVerticalCenter;
    });
    
    // 如果拖动的是置顶卡片，只能放在其他置顶卡片之间或所有置顶卡片之后
    if (isDraggingPinned) {
      if (afterCard && parseInt(afterCard.dataset.order) === -1) {
        // 放在另一个置顶卡片之前
        list.insertBefore(draggingCard, afterCard);
      } else if (pinnedCards.length > 0) {
        // 放在所有置顶卡片之后
        const lastPinnedCard = pinnedCards[pinnedCards.length - 1];
        list.insertBefore(draggingCard, lastPinnedCard.nextSibling);
      } else {
        // 没有其他置顶卡片，放在列表开头
        list.insertBefore(draggingCard, list.firstChild);
      }
    } else {
      // 拖动的是普通卡片，只能放在普通卡片之间或所有普通卡片之后
      if (afterCard && parseInt(afterCard.dataset.order) !== -1) {
        // 放在另一个普通卡片之前
        list.insertBefore(draggingCard, afterCard);
      } else if (normalCards.length > 0) {
        // 放在所有普通卡片之后
        const lastNormalCard = normalCards[normalCards.length - 1];
        list.insertBefore(draggingCard, lastNormalCard.nextSibling);
      } else if (pinnedCards.length > 0) {
        // 没有普通卡片，放在所有置顶卡片之后
        const lastPinnedCard = pinnedCards[pinnedCards.length - 1];
        list.insertBefore(draggingCard, lastPinnedCard.nextSibling);
      } else {
        // 列表为空，直接添加
        list.appendChild(draggingCard);
      }
    }
  }
  
  // 处理拖拽离开事件
  handleDragLeave(e) {
    e.currentTarget.classList.remove("drag-over");
  }
  
  // 处理拖拽放置事件
  handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove("drag-over");

    const taskId = e.dataTransfer.getData("text/plain");
    if (!taskId) return; // 防止无效拖拽
    
    const newStatus = e.currentTarget.parentElement.dataset.status;
    if (!newStatus) return; // 防止无效目标状态

    // 修改排序逻辑：获取所有同状态的卡片
    const allCards = [...e.currentTarget.querySelectorAll(".task-card")];
    const droppedCard = allCards.find((card) => card.dataset.id === taskId);
    if (!droppedCard) return; // 防止卡片丢失
    
    // 分离置顶卡片和普通卡片
    const pinnedCards = allCards.filter(card => parseInt(card.dataset.order) === -1);
    const normalCards = allCards.filter(card => parseInt(card.dataset.order) !== -1);
    
    // 检查被拖动的卡片是否是置顶卡片
    const isDroppedCardPinned = parseInt(droppedCard.dataset.order) === -1;
    
    // 计算新的顺序，只处理普通卡片
    const normalCardIndex = normalCards.indexOf(droppedCard);
    let newOrder = normalCardIndex;

    // 更新所有普通卡片的顺序
    normalCards.forEach((card, index) => {
      const cardId = card.dataset.id;
      if (cardId !== taskId && index !== parseInt(card.dataset.order)) {
        this.updateTaskOrder(cardId, index);
      }
    });

    try {
      // 获取被拖动卡片的任务数据
      const droppedTask = JSON.parse(droppedCard.getAttribute('data-task'));
      
      // 检查是否是周期任务且目标状态是已完成
      if (droppedTask.is_cycle_task && newStatus === 'COMPLETED') {
        layer.msg('周期任务不能标记为已完成，请使用"完成本次任务"按钮', { icon: 2 });
        // 重新加载任务列表，恢复原始状态
        taskManager.loadTasks();
        return;
      }
      
      // 更新拖动卡片的状态和顺序
      // 如果是置顶卡片，保持其order=-1
      if (isDroppedCardPinned) {
        this.updateTaskStatus(taskId, newStatus, -1, droppedTask);
      } else {
        this.updateTaskStatus(taskId, newStatus, newOrder, droppedTask);
      }
    } catch (e) {
      console.error("[Roadmap Drag] Error handling drop:", e);
      layer.msg("拖拽处理失败，请重试", { icon: 2 });
      taskManager.loadTasks();
    }
  }
  
  // 更新任务顺序
  updateTaskOrder(taskId, order) {
    $.ajax({
      url: `/roadmap/api/${taskId}`,
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
  updateTaskStatus(taskId, status, order, task) {
    // 检查是否是周期任务且目标状态是已完成
    if (task.is_cycle_task && status === 'COMPLETED') {
      layer.msg('周期任务不能标记为已完成，请使用"完成本次任务"按钮', { icon: 2 });
      taskManager.loadTasks();
      return;
    }
    
    // 不是周期任务或目标状态不是已完成，继续更新
    $.ajax({
      url: `/roadmap/api/${taskId}`,
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
            setTimeout(() => taskManager.loadTasks(), 500);
          } else {
            layer.msg("更新失败: " + data.msg, { icon: 2 });
            taskManager.loadTasks(); // 失败时立即刷新
          }
        } catch (e) {
          console.error("[Roadmap] Error parsing response:", e);
          layer.msg("数据解析错误", { icon: 2 });
          taskManager.loadTasks();
        }
      },
      error: function(xhr, status, error) {
        console.error("[Roadmap] Error updating task:", error);
        layer.msg("更新任务失败", { icon: 2 });
        taskManager.loadTasks();
      }
    });
  }
}
