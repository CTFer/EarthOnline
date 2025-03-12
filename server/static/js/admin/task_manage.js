// 全局变量
let treeChart = null;
let taskData = null;

// 导入配置
import { TASK_TYPE_MAP } from '../config/config.js';

// 初始化
layui.use(["layer", "form", "jquery"], function () {
  var layer = layui.layer,
    form = layui.form,
    $ = layui.jquery; // 引入 jquery

  // 初始化页面数据
  loadTaskData();

  // 监听窗口大小变化
  window.onresize = function () {
    if (treeChart) {
      treeChart.resize();
    }
  };

  // JSON 弹窗函数 - 移到 layui.use 内部
  window.showJsonDialog = function () {
    layer.open({
      type: 1,
      title: "JSON 数据",
      area: ["800px", "80%"], // 设置宽度和高度（相对于窗口高度的百分比）
      maxmin: true, // 开启最大化最小化按钮
      shadeClose: true,
      content: $("#taskJson"),
      btn: ["编辑", "关闭"],
      btnAlign: "c",
      success: function (layero, index) {
        // 设置弹窗内容的样式
        const content = layero.find(".layui-layer-content");
        content.css({
          padding: "0",
          background: "#1e1e1e",
        });

        // 更新 JSON 内容
        $("#taskJson").val(JSON.stringify(taskData, null, 2));
      },
      yes: function (index, layero) {
        const textarea = layero.find("#taskJson");
        textarea.removeAttr("readonly");

        const buttons = layero.find(".layui-layer-btn").children();
        buttons.eq(0).html("保存");

        buttons.eq(0).one("click", function () {
          try {
            const newData = JSON.parse(textarea.val());
            taskData = newData;
            const treeData = processTaskData(newData.data);
            initTaskTree(treeData);
            layer.msg("保存成功");
            layer.close(index);
          } catch (e) {
            layer.msg("JSON格式错误，请检查");
            return false;
          }
        });
      },
    });
  };
});

// 修改 loadTaskData 函数
function loadTaskData() {
  fetch("/admin/api/tasks", {
    method: "GET",
    headers: {
      "X-Requested-With": "XMLHttpRequest",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      // 保存到全局变量
      taskData = data;
      // 更新JSON展示
      updateJsonDisplay();
      // 构建树图数据
      const treeData = processTaskData(data.data);
      console.log(treeData);
      initTaskTree(treeData);
    })
    .catch((error) => {
      layer.msg("加载数据失败：" + error);
    });
}

// 更新JSON显示
function updateJsonDisplay() {
  document.getElementById("taskJson").value = JSON.stringify(taskData, null, 2);
}

// 修改处理任务数据为树形结构的函数
function processTaskData(tasks) {
  if (!Array.isArray(tasks)) {
    return {
      name: "任务系统",
      isGroup: true,
      children: [],
    };
  }

  // 创建任务节点映射
  const taskMap = new Map();
  tasks.forEach((task) => {
    taskMap.set(task.id, {
      name: task.name || "未命名任务",
      value: task.id,
      task_type: task.task_type,
      stamina_cost: task.stamina_cost,
      task_chain_id: task.task_chain_id,
      parent_task_id: task.parent_task_id,
      children: [],
    });
  });

  // 构建树结构
  const chains = new Map(); // 用于存储不同任务链的根节点

  taskMap.forEach((node, taskId) => {
    if (node.parent_task_id) {
      const parentNode = taskMap.get(node.parent_task_id);
      if (parentNode) {
        // 如果父节点存在，直接添加为子节点
        parentNode.children.push(node);
      } else {
        // 如果父节点不存在，作为任务链的根节点
        const chainId = node.task_chain_id || 0;
        if (!chains.has(chainId)) {
          chains.set(chainId, []);
        }
        chains.get(chainId).push(node);
      }
    } else {
      // 没有父节点的任务作为任务链的根节点
      const chainId = node.task_chain_id || 0;
      if (!chains.has(chainId)) {
        chains.set(chainId, []);
      }
      chains.get(chainId).push(node);
    }
  });

  // 构建最终的树结构
  return {
    name: "任务系统",
    isGroup: true,
    children: Array.from(chains.entries()).map(([chainId, nodes]) => ({
      name: `任务链 ${chainId}`,
      value: `chain_${chainId}`,
      isGroup: true,
      children: nodes,
    })),
  };
}

// 修改 getTaskTypeColor 函数
function getTaskTypeColor(type) {
  return TASK_TYPE_MAP[type]?.color || "#607D8B"; // 使用可选链操作符，默认为灰色
}

let currentZoom = 1;

// 修改 initTaskTree 函数，添加 renderItem 配置
function initTaskTree(data) {
  if (!treeChart) {
    treeChart = echarts.init(document.getElementById("taskTree"));
  }

  const option = {
    series: [
      {
        type: "tree",
        data: [data],
        orient: "TB",
        layout: "orthogonal",
        left: "20%",
        right: "20%",
        top: "10%",
        bottom: "10%",

        symbol: "rect",
        symbolSize: [120, 40],

        // 保持原有的配置
        lineStyle: {
          color: "#78909c",
          width: 1,
          curveness: 0.1,
        },

        label: {
          position: "inside",
          formatter: function (params) {
            // 根据节点类型设置颜色
            let color;
            if (params.data.task_type && TASK_TYPE_MAP[params.data.task_type]) {
              color = TASK_TYPE_MAP[params.data.task_type].color;
            } else if (params.data.isGroup) {
              color = params.data.name === "任务系统" ? "#2c3e50" : "#455a64";
            } else {
              color = "#95a5a6";
            }

            // 设置节点样式
            params.data.itemStyle = {
              color: color,
              borderColor: "#fff",
              borderWidth: 1,
              shadowColor: "rgba(0, 0, 0, 0.3)",
              shadowBlur: 5,
            };

            // 返回节点文本
            let text = params.data.name;
            if (!params.data.isGroup && params.data.stamina_cost) {
              text += `\n体力: ${params.data.stamina_cost}`;
            }
            return text;
          },
          color: "#fff",
          fontSize: 12,
          lineHeight: 16,
        },

        // 开启拖拽和缩放
        roam: "move", // 只允许移动，缩放通过自定义控制
        expandAndCollapse: false,
        // 连线样式
        lineStyle: {
          color: "#78909c",
          width: 2,
        }, // 优化节点间距
        nodeGap: 36,
        layerPadding: 150,

        initialTreeDepth: -1, //-1表示展开所有节点
        animationDuration: 550,
        animationDurationUpdate: 750,

        // 禁用默认的展开收起行为
        expandAndCollapse: false,
      },
    ],
  };

  treeChart.setOption(option);

  // 保持原有的初始缩放设置
  setTimeout(() => {
    treeChart.setOption({
      series: [
        {
          zoom: 1.5,
        },
      ],
    });
  }, 100);

  // 监听容器大小变化
  window.addEventListener("resize", function () {
    treeChart.resize();
  });

  // 重新绑定点击事件
  treeChart.off("click");
  treeChart.on("click", function (params) {
    if (!params.data || params.componentType !== "series") return;

    if (params.data.isGroup) {
      // 只允许分组节点展开/收起
      params.data.collapsed = !params.data.collapsed;
      // 使用完整的 option 重新设置
      const currentOption = treeChart.getOption();
      treeChart.setOption(currentOption);
    } else if (params.data.value) {
      // 任务节点只处理编辑
      const task = taskData.data.find((t) => t.id === params.data.value);
      if (task) {
        showTaskFormDialog("edit", task);
      }
    }
  });

  // 添加鼠标悬停效果
  treeChart.on("mouseover", function (params) {
    if (params.data) {
      treeChart.getDom().style.cursor = params.data.isGroup ? "pointer" : "default";
    }
  });

  treeChart.on("mouseout", function () {
    treeChart.getDom().style.cursor = "default";
  });

  // 鼠标滚轮缩放
  treeChart.getZr().on("mousewheel", function (e) {
    if (e.event) {
      const delta = e.event.wheelDelta / 120;
      const zoom = treeChart.getOption().series[0].zoom || 1;
      const newZoom = zoom * (delta > 0 ? 1.1 : 0.9);

      treeChart.setOption({
        series: [
          {
            zoom: Math.max(0.3, Math.min(2, newZoom)),
          },
        ],
      });

      e.event.preventDefault();
    }
  });
}

// 重置缩放和位置
function resetTreeZoom() {
  if (!treeChart) return;

  // 获取当前完整配置
  const currentOption = treeChart.getOption();

  // 只更新缩放和位置相关的配置，保持其他配置不变
  currentOption.series[0].zoom = 0.8;
  currentOption.series[0].center = ["50%", "50%"];

  // 应用更新后的配置
  treeChart.setOption(currentOption, {
    replaceMerge: ["series"],
  });
}

// 修改缩放范围
function zoomTree(scale) {
  if (!treeChart) return;

  currentZoom *= scale;
  // 扩大缩放范围
  currentZoom = Math.min(Math.max(0.2, currentZoom), 2.5);

  treeChart.setOption({
    series: [
      {
        zoom: currentZoom,
      },
    ],
  });
}

// 修改任务编辑表单函数
function showTaskEditForm(taskId) {
  // 从全局数据中查找任务
  const task = taskData.data.find((t) => t.id === taskId);
  if (!task) {
    layer.msg("未找到任务数据");
    return;
  }

  // 使用 showTaskFormDialog 函数，传入编辑模式和任务数据
  window.showTaskFormDialog("edit", task);
}

// 修改添加任务按钮的点击事件
document.querySelector('[onclick="showTaskFormDialog()"]').onclick = function () {
  window.showTaskFormDialog("add");
};

// 修改 addTask 函数为通用的提交处理函数
function handleTaskSubmit(formData, mode, taskId = null) {
  const taskData = {
    ...Object.fromEntries(formData),
    is_enabled: formData.get("is_enabled") === "on",
    repeatable: formData.get("repeatable") === "on",
  };

  if (mode === "add") {
    // 添加新任务
    taskData.id = Date.now(); // 临时ID
    taskData.created_at = new Date().toISOString();
    taskData.data.push(taskData);
  } else {
    // 更新现有任务
    const taskIndex = taskData.data.findIndex((t) => t.id === taskId);
    if (taskIndex !== -1) {
      taskData.data[taskIndex] = {
        ...taskData.data[taskIndex],
        ...taskData,
      };
    }
  }

  // 更新显示
  updateJsonDisplay();
  const treeData = processTaskData(taskData.data);
  initTaskTree(treeData);

  layer.msg(`任务已${mode === "add" ? "添加" : "更新"}到JSON，请点击"保存所有更改"提交到服务器`);
}

// 更新任务数据到JSON
function updateTask(taskId) {
  const form = document.getElementById("editTaskForm");
  const formData = new FormData(form);
  const updatedData = Object.fromEntries(formData);

  // 更新全局数据
  const taskIndex = taskData.data.findIndex((t) => t.id === taskId);
  if (taskIndex !== -1) {
    taskData.data[taskIndex] = {
      ...taskData.data[taskIndex],
      ...updatedData,
    };

    // 更新JSON显示
    updateJsonDisplay();

    // 更新树图
    const treeData = processTaskData(taskData.data);
    initTaskTree(treeData);

    layer.msg('JSON已更新，请点击"保存所有更改"提交到服务器');
  }
}

// 从JSON中删除任务
function deleteTask(taskId) {
  layer.confirm("确定要删除这个任务吗？", function (index) {
    // 从全局数据中删除
    taskData.data = taskData.data.filter((t) => t.id !== taskId);

    // 更新JSON显示
    updateJsonDisplay();

    // 更新树图
    const treeData = processTaskData(taskData.data);
    initTaskTree(treeData);

    layer.msg('任务已从JSON中删除，请点击"保存所有更改"提交到服务器');
    layer.close(index);
  });
}

// 保存所有更改到服务器
function saveChanges() {
  layer.confirm("确定要保存所有更改吗？", function (index) {
    fetch("/admin/api/tasks/batch", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(taskData),
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.success) {
          layer.msg("所有更改已保存");
          loadTaskData(); // 重新加载数据
        } else {
          layer.msg("保存失败：" + result.message);
        }
      });
    layer.close(index);
  });
}

// 添加JSON编辑器功能
document.getElementById("taskJson").addEventListener("input", function () {
  try {
    const newData = JSON.parse(this.value);
    taskData = newData;
    const treeData = processTaskData(newData.data);
    initTaskTree(treeData);
  } catch (e) {
    console.error("JSON格式错误:", e);
  }
});

// 在页面加载完成后初始化玩家列表
layui.use(["form", "jquery"], function () {
  var form = layui.form;
  var $ = layui.jquery;

  // 监听任务范围选择变化
  form.on("select(taskScope)", function (data) {
    console.log("选择的任务范围:", data.value);
  });
});
