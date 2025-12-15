// 置顶管理模块
class PinManager {
  // 初始化置顶功能
  init() {
    $(document).on("click", ".pin-task", (e) => this.handlePinTask(e));
  }
  
  // 处理置顶/取消置顶点击事件
  handlePinTask(e) {
    e.stopPropagation();
    const $btn = $(e.target).closest(".pin-task");
    const $card = $btn.closest(".task-card");
    const taskId = $card.data("id");
    const isPinned = $btn.data("pinned");

    layer.confirm(isPinned ? "确定要取消置顶吗？" : "确定要置顶吗？", { icon: 3, title: "提示" }, function (index) {
      pinManager.togglePinTask(taskId, isPinned);
      layer.close(index);
    });
  }
  
  // 切换任务置顶状态
  togglePinTask(taskId, isPinned) {
    const newOrder = isPinned ? 0 : -1;
    const currentTime = Math.floor(Date.now() / 1000);
    
    $.ajax({
      url: `/roadmap/api/${taskId}`,
      method: "PUT",
      contentType: "application/json",
      data: JSON.stringify({
        order: newOrder,
        edittime: currentTime
      }),
      success: function (res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code === 0) {
            layer.msg(isPinned ? "取消置顶成功" : "置顶成功", { icon: 1 });
            
            // 直接更新页面上的卡片排序，而不是重新加载
            const $pinnedCard = $(`.task-card[data-id="${taskId}"]`);
            if (!$pinnedCard.length) return;
            
            const $taskList = $pinnedCard.closest(".task-list");
            let taskData = $pinnedCard.data("task");
            if (!taskData) {
              taskData = JSON.parse($pinnedCard.attr("data-task"));
            }
            
            // 更新任务数据
            taskData.order = newOrder;
            taskData.edittime = currentTime;
            $pinnedCard.data("task", taskData);
            $pinnedCard.attr("data-task", JSON.stringify(taskData));
            $pinnedCard.attr("data-order", newOrder);
            
            // 获取当前列表中的所有卡片
            const $allCards = $taskList.find(".task-card");
            
            // 将卡片转换为数组并排序
            const sortedCards = $allCards.toArray().sort((a, b) => {
              const aTask = JSON.parse($(a).attr("data-task"));
              const bTask = JSON.parse($(b).attr("data-task"));
              
              // 自定义排序逻辑
              if (aTask.order === -1 && bTask.order !== -1) {
                return -1; // a是置顶，排在前面
              }
              if (aTask.order !== -1 && bTask.order === -1) {
                return 1; // b是置顶，排在前面
              }
              if (aTask.order === -1 && bTask.order === -1) {
                return bTask.edittime - aTask.edittime;
              }
              return (aTask.order || 0) - (bTask.order || 0);
            });
            
            // 重新排列DOM中的卡片
            sortedCards.forEach(card => {
              $taskList.append(card);
            });
            
            // 重新初始化拖拽功能
            dragManager.initDragAndDrop();
            
            // 更新置顶按钮的状态
            const $pinBtn = $pinnedCard.find(".pin-task");
            if ($pinBtn.length) {
              $pinBtn.data("pinned", !isPinned);
              $pinBtn.attr("data-pinned", !isPinned);
              $pinBtn.attr("title", !isPinned ? "取消置顶" : "置顶");
              $pinBtn.find(".layui-icon").html(!isPinned ? "&#xe61a;" : "&#xe619;");
            }
          } else {
            layer.msg("操作失败: " + data.msg, { icon: 2 });
          }
        } catch (e) {
          console.error("[Roadmap] Error parsing response:", e);
          layer.msg("数据解析错误", { icon: 2 });
        }
      },
    });
  }
}
