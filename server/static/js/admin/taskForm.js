// 导入配置
import { TASK_TYPE_MAP, TASK_STATUS_MAP } from '../config/config.js';

// 确保函数在全局作用域可用
(function (window) {
  console.log("TaskForm.js loading");

  // 确保 layui 已加载
  if (typeof layui === "undefined") {
    console.error("Layui is not loaded!");
    return;
  }

  // 修改任务状态常量
  const TASK_STATUS = TASK_STATUS_MAP;

  // 获取表单内容
  function getTaskFormContent() {
    // 生成任务类型单选框HTML
    const taskTypeRadios = Object.entries(TASK_TYPE_MAP)
      .filter(([key]) => key !== 'UNDEFINED') // 排除未定义类型
      .map(([value, config]) => `
        <input type="radio" name="task_type" value="${value}" lay-skin="none">
        <div lay-radio class="lay-skin-taskcard">
            <div class="lay-skin-taskcard-detail">
                <div class="lay-skin-taskcard-header">${config.text}</div>
            </div>
        </div>
      `).join('');

    // 生成任务状态单选框HTML
    const taskStatusRadios = Object.entries(TASK_STATUS)
      .map(([value, config]) => `
        <input type="radio" name="task_status" value="${value}" lay-skin="none" ${value === 'LOCKED' ? 'checked' : ''}>
        <div lay-radio class="lay-skin-taskcard">
            <div class="lay-skin-taskcard-detail">
                <div class="lay-skin-taskcard-header">${config.text}</div>
                <div class="lay-skin-taskcard-description" style="color: ${config.color}">
                    ${config.text}
                </div>
            </div>
        </div>
      `).join('');

    return `
        <div class="task-form-scroll" id="taskForm">
            <form class="layui-form" lay-filter="taskForm">
                <div class="layui-form-item">
                <label class="layui-form-label">任务ID</label>
                <div class="layui-input-block">
                    <input type="text" name="id" class="layui-input" value="" readonly style="background: transparent; color: #fff;border:none">
                </div>
                </div>
                <div class="layui-form-item">
                    <label class="layui-form-label">任务名称</label>
                    <div class="layui-input-block">
                        <input type="text" name="name" required lay-verify="required" 
                               placeholder="请输入任务名称" class="layui-input">
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">任务链ID</label>
                    <div class="layui-input-block">
                        <input type="number" name="task_chain_id" required lay-verify="required|number" 
                               placeholder="0表示独立任务" class="layui-input" value="0">
                    </div>
                </div>
                <div class="layui-form-item">
                    <label class="layui-form-label">父任务ID</label>
                    <div class="layui-input-block">
                        <input type="number" name="parent_task_id" required lay-verify="required|number" 
                               placeholder="0表示独立任务" class="layui-input" value="0">
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">任务类型</label>
                    <div class="layui-input-block" id="taskTypeRadios">
                        ${taskTypeRadios}
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">任务状态</label>
                    <div class="layui-input-block" id="taskStatusRadios">
                        ${taskStatusRadios}
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">任务描述</label>
                    <div class="layui-input-block">
                        <textarea name="description" placeholder="请输入任务描述" 
                                  class="layui-textarea"></textarea>
                    </div>
                </div>
                
                <style>
                    /* 卡片风格的单选框样式 */
                    .layui-form-radio>.lay-skin-taskcard {
                        display: flex;
                        padding: 12px;
                        border-radius: 4px;
                        border: 1px solid #e5e5e5;
                        color: #000;
                        background-color: #fff;
                        transition: all .3s;
                        cursor: pointer;
                        position: relative; /* 添加相对定位 */
                    }
                    .layui-form-radio:hover>.lay-skin-taskcard {
                        border-color: #16b777;
                    }
                    .layui-form-radioed[lay-skin="none"]>.lay-skin-taskcard {
                        color: #fff;
                        border-color: #16b777;
                        background-color: rgb(22 183 119 / 10%);
                    }
                    /* 添加选中状态的角标样式 */
                    .layui-form-radioed[lay-skin="none"]>.lay-skin-taskcard:after {
                        position: absolute;
                        content: "";
                        bottom: 2px;
                        right: 2px;
                        width: 0;
                        height: 0;
                        display: inline-block;
                        vertical-align: middle;
                        border-width: 10px;
                        border-style: dashed;
                        border-color: transparent;
                        border-top-left-radius: 6px;
                        border-top-right-radius: 0px;
                        border-bottom-right-radius: 6px;
                        border-bottom-left-radius: 0px;
                        border-right-color: #16b777;
                        border-right-style: solid;
                        border-bottom-color: #16b777;
                        border-bottom-style: solid;
                        overflow: hidden;
                    }
                    .lay-skin-taskcard-detail {
                        width: 100%;
                    }
                    .lay-skin-taskcard-header {
                        font-weight: 500;
                        font-size: 14px;
                        margin-bottom: 4px;
                    }
                    .lay-skin-taskcard-description {
                        font-size: 12px;
                        color: #666;
                    }
                </style>

                <div class="layui-form-item">
                    <label class="layui-form-label">任务范围</label>
                    <div class="layui-input-block" id="taskScopeRadios">
                        <!-- 所有玩家选项 -->
                        <input type="radio" name="task_scope" value="0" lay-skin="none" checked>
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">所有玩家</div>
                                <div class="lay-skin-taskcard-description">任务对所有玩家可见</div>
                            </div>
                        </div>
                        <!-- 玩家列表将通过 AJAX 动态加载 -->
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">需要确认</label>
                    <div class="layui-input-block">
                        <input type="checkbox" name="need_check" lay-skin="switch" lay-text="是|否">
                    </div>
                </div>

                <!-- 数值奖励 -->
                <div class="layui-form-item" id="pointsRewardsContainer">
                    <label class="layui-form-label">数值奖励</label>
                    <div class="layui-input-block">
                        <div class="rewards-list">
                            <div class="reward-item">
                                <div class="layui-input-inline" style="width: 120px;">
                                    <select name="points_rewards[0].type">
                                        <option value="exp">经验值</option>
                                        <option value="points">积分</option>
                                    </select>
                                </div>
                                <div class="layui-input-inline" style="width: 120px;">
                                    <input type="number" name="points_rewards[0].number" 
                                           placeholder="数量" class="layui-input">
                                </div>
                            </div>
                        </div>
                        <div class="layui-btn layui-btn-xs" onclick="addRewardItem('points')">
                            <i class="layui-icon">&#xe654;</i> 添加数值奖励
                        </div>
                    </div>
                </div>

                <!-- 卡片奖励 -->
                <div class="layui-form-item" id="cardRewardsContainer">
                    <label class="layui-form-label">卡片奖励</label>
                    <div class="layui-input-block">
                        <div class="rewards-list">
                            <div class="reward-item">
                                <div class="layui-input-inline" style="width: 120px;">
                                    <input type="number" name="card_rewards[0].id" 
                                           placeholder="卡片ID" class="layui-input">
                                </div>
                                <div class="layui-input-inline" style="width: 120px;">
                                    <input type="number" name="card_rewards[0].number" 
                                           placeholder="数量" class="layui-input">
                                </div>
                            </div>
                        </div>
                        <div class="layui-btn layui-btn-xs" onclick="addRewardItem('card')">
                            <i class="layui-icon">&#xe654;</i> 添加卡片奖励
                        </div>
                    </div>
                </div>

                <!-- 成就奖励 -->
                <div class="layui-form-item" id="medalRewardsContainer">
                    <label class="layui-form-label">成就奖励</label>
                    <div class="layui-input-block">
                        <div class="rewards-list">
                            <div class="reward-item">
                                <div class="layui-input-inline" style="width: 120px;">
                                    <input type="number" name="medal_rewards[0].id" 
                                           placeholder="成就ID" class="layui-input">
                                </div>
                                <div class="layui-btn layui-btn-xs layui-btn-normal" onclick="showMedalList(this)">
                                    <i class="layui-icon">&#xe615;</i> 选择勋章
                                </div>
                                <div class="layui-btn layui-btn-xs layui-btn-danger" onclick="removeRewardItem(this)">
                                    <i class="layui-icon">&#xe640;</i>
                                </div>
                            </div>
                        </div>
                        <div class="layui-btn layui-btn-xs" onclick="addRewardItem('medal')">
                            <i class="layui-icon">&#xe654;</i> 添加成就奖励
                        </div>
                    </div>
                </div>

                <!-- 实物奖励 -->
                <div class="layui-form-item" id="realRewardsContainer">
                    <label class="layui-form-label">实物奖励</label>
                    <div class="layui-input-block">
                        <div class="rewards-list">
                            <div class="reward-item">
                                <div class="layui-input-inline" style="width: 120px;">
                                    <input type="text" name="real_rewards[0].name" 
                                           placeholder="奖品名称" class="layui-input">
                                </div>
                                <div class="layui-input-inline" style="width: 120px;">
                                    <input type="number" name="real_rewards[0].number" 
                                           placeholder="数量" class="layui-input">
                                </div>
                            </div>
                        </div>
                        <div class="layui-btn layui-btn-xs" onclick="addRewardItem('real')">
                            <i class="layui-icon">&#xe654;</i> 添加实物奖励
                        </div>
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">体力消耗</label>
                    <div class="layui-input-block">
                        <input type="number" name="stamina_cost" required lay-verify="required|number" 
                               placeholder="请输入体力消耗" class="layui-input" value="0">
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">时间限制</label>
                    <div class="layui-input-block">
                        <input type="number" name="limit_time" required lay-verify="required|number" 
                               placeholder="请输入时间限制(分钟)" class="layui-input" value="0">
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">重复次数</label>
                    <div class="layui-input-block">
                        <input type="number" name="repeat_time" required lay-verify="required|number" 
                               placeholder="请输入重复次数" class="layui-input" value="1">
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">是否启用</label>
                    <div class="layui-input-block">
                        <input type="checkbox" name="is_enabled" lay-skin="switch" lay-text="启用|禁用" checked>
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">可重复完成</label>
                    <div class="layui-input-block">
                        <input type="checkbox" name="repeatable" lay-skin="switch" lay-text="是|否">
                    </div>
                </div>
                
                <div class="layui-form-item form-actions">
                    <div class="layui-input-block">
                        <button type="button" class="layui-btn" lay-submit lay-filter="taskSubmit">提交</button>
                        <button type="reset" class="layui-btn layui-btn-primary">重置</button>
                    </div>
                </div>
            </form>
        </div>
        
        <style>
            .task-form-scroll {
                height: calc(100% - 40px);
                padding: 20px 20px 0;
                overflow-y: auto;
            }
            
            .task-form-scroll::-webkit-scrollbar {
                width: 6px;
            }
            
            .task-form-scroll::-webkit-scrollbar-thumb {
                background: rgba(0,0,0,.1);
                border-radius: 3px;
            }
            
            .task-form-scroll::-webkit-scrollbar-track {
                background: transparent;
            }
            
            .lay-skin-taskcard {
                padding: 8px 15px !important;
                margin: 4px 0 !important;
                min-width: 100px;
            }
            
            .lay-skin-taskcard-header {
                font-size: 13px !important;
                text-align: center;
            }
            
            .layui-form-item {
                margin-bottom: 15px;
            }
            
            .form-actions {
                margin: 20px 0;
                padding-bottom: 20px;
            }
            
            #taskTypeRadios .layui-input-block,
            #taskStatusRadios .layui-input-block {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }
            
            .lay-skin-taskcard-detail {
                width: 100%;
                display: flex;
                justify-content: center;
            }

            .rewards-list {
                margin-bottom: 10px;
            }
            .reward-item {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
                gap: 10px;
            }
            .reward-item .layui-btn-danger {
                margin-left: 10px;
            }
        </style>
    `;
  }

  // 使用新的函数名
  window.showTaskFormDialog = function (mode = "add", taskData = null) {
    console.log(`showTaskFormDialog called in ${mode} mode with data:`, taskData);

    layui.use(["layer", "form"], function () {
      var layer = layui.layer,
        form = layui.form;

      layer.open({
        type: 1,
        title: mode === "add" ? "添加任务" : "编辑任务",
        area: ["800px", "700px"],
        content: getTaskFormContent(),
        shadeClose: true,
        success: function (layero, index) {
          console.log("Dialog opened successfully");

          // 获取任务范围容器
          const taskScopeContainer = layero.find("#taskScopeRadios")[0];

          // 加载玩家列表
          loadPlayerList(taskScopeContainer);

          // 如果是编辑模式，填充表单数据
          if (mode === "edit" && taskData) {
            console.log("Filling form with data:", taskData);
            form.val("taskForm", {
              id: taskData.id,
              name: taskData.name,
              task_chain_id: taskData.task_chain_id || "0",
              parent_task_id: taskData.parent_task_id || "0",
              task_type: taskData.task_type,
              task_status: taskData.task_status,
              description: taskData.description,
              task_scope: taskData.task_scope,
              stamina_cost: taskData.stamina_cost,
              limit_time: taskData.limit_time,
              repeat_time: taskData.repeat_time,
              is_enabled: taskData.is_enabled,
              repeatable: taskData.repeatable,
            });

            // 解析 task_rewards
            const taskRewards = typeof taskData.task_rewards === 'string' 
                ? JSON.parse(taskData.task_rewards) 
                : taskData.task_rewards;

            // 填充数值奖励
            if (taskRewards.points_rewards) {
              taskRewards.points_rewards.forEach((reward, index) => {
                if (index === 0) {
                  document.querySelector(`select[name="points_rewards[0].type"]`).value = reward.type;
                  document.querySelector(`input[name="points_rewards[0].number"]`).value = reward.number;
                } else {
                  addRewardItem('points'); // 添加新的奖励项
                  document.querySelector(`select[name="points_rewards[${index}].type"]`).value = reward.type;
                  document.querySelector(`input[name="points_rewards[${index}].number"]`).value = reward.number;
                }
              });
            }

            // 填充卡片奖励
            if (taskRewards.card_rewards) {
              taskRewards.card_rewards.forEach((reward, index) => {
                if (index === 0) {
                  document.querySelector(`input[name="card_rewards[0].id"]`).value = reward.id;
                  document.querySelector(`input[name="card_rewards[0].number"]`).value = reward.number;
                } else {
                  addRewardItem('card'); // 添加新的奖励项
                  document.querySelector(`input[name="card_rewards[${index}].id"]`).value = reward.id;
                  document.querySelector(`input[name="card_rewards[${index}].number"]`).value = reward.number;
                }
              });
            }

            // 填充成就奖励
            if (taskRewards.medal_rewards) {
              taskRewards.medal_rewards.forEach((reward, index) => {
                if (index === 0) {
                  document.querySelector(`input[name="medal_rewards[0].id"]`).value = reward.id;
                } else {
                  addRewardItem('medal'); // 添加新的奖励项
                  document.querySelector(`input[name="medal_rewards[${index}].id"]`).value = reward.id;
                }
              });
            }

            // 填充实物奖励
            if (taskRewards.real_rewards) {
              taskRewards.real_rewards.forEach((reward, index) => {
                if (index === 0) {
                  document.querySelector(`input[name="real_rewards[0].name"]`).value = reward.name;
                  document.querySelector(`input[name="real_rewards[0].number"]`).value = reward.number;
                } else {
                  addRewardItem('real'); // 添加新的奖励项
                  document.querySelector(`input[name="real_rewards[${index}].name"]`).value = reward.name;
                  document.querySelector(`input[name="real_rewards[${index}].number"]`).value = reward.number;
                }
              });
            }
          }

          form.render(null, "taskForm");

          // 修改表单提交监听
          form.on("submit(taskSubmit)", function (data) {
            console.log("Form submitted with data:", data.field);
            // 直接传递 data.field 对象
            handleTaskSubmit(data.field, mode, taskData?.id);
            layer.close(index);
            return false;
          });
        },
      });
    });
  };

  // 修改处理提交的函数
  function handleTaskSubmit(formData, mode, taskId = null) {
    console.log("handleTaskSubmit called with:", { formData, mode, taskId });

    try {
      // 构建任务数据对象
      const taskDataObj = {
        name: formData.name,
        task_chain_id: parseInt(formData.task_chain_id) || 0,
        parent_task_id: parseInt(formData.parent_task_id) || 0,
        task_type: formData.task_type,
        task_status: formData.task_status,
        description: formData.description || "",
        task_scope: parseInt(formData.task_scope),
        stamina_cost: parseInt(formData.stamina_cost) || 0,
        limit_time: parseInt(formData.limit_time) || 0,
        repeat_time: parseInt(formData.repeat_time) || 1,
        is_enabled: formData.is_enabled === "on",
        repeatable: formData.repeatable === "on",
        task_rewards: {
          points_rewards: [
            { type: "exp", number: parseInt(formData["points_rewards[0].number"]) || 0 },
            { type: "points", number: parseInt(formData["points_rewards[1].number"]) || 0 },
          ],
          card_rewards: [
            {
              id: parseInt(formData["card_rewards[0].id"]) || 0,
              number: parseInt(formData["card_rewards[0].number"]) || 0,
            },
          ],
          medal_rewards: [
            {
              id: parseInt(formData["medal_rewards[0].id"]) || 0,
              number: parseInt(formData["medal_rewards[0].number"]) || 0,
            },
          ],
          real_rewards: [
            {
              name: formData["real_rewards[0].name"] || "",
              number: parseInt(formData["real_rewards[0].number"]) || 0,
            },
          ],
        },
      };

      console.log("Processed task data:", taskDataObj);

      // 发送到服务器
      const url = mode === "add" ? "/admin/api/tasks" : `/admin/api/tasks/${taskId}`;
      const method = mode === "add" ? "POST" : "PUT";

      fetch(url, {
        method: method,
        headers: {
          "Content-Type": "application/json",
          "X-Requested-With": "XMLHttpRequest",
        },
        body: JSON.stringify(taskDataObj),
      })
        .then((response) => response.json())
        .then((result) => {
          if (result.error) {
            throw new Error(result.error);
          }
          layer.msg("操作成功");
          if (typeof loadTaskData === "function") {
            loadTaskData();
          }
        })
        .catch((error) => {
          console.error("Submit error:", error);
          layer.msg("操作失败: " + error.message);
        });
    } catch (error) {
      console.error("handleTaskSubmit error:", error);
      layer.msg("处理表单数据时出错: " + error.message);
    }
  }

  // 添加加载玩家列表的函数
  function loadPlayerList(container) {
    fetch("/api/get_players", {
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.code === 0) {
          // 添加玩家列表单选框
          let html = "";
          result.data.forEach((player) => {
            html += `
                        <input type="radio" name="task_scope" value="${player.id}" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">${player.name}</div>
                                <div class="lay-skin-taskcard-description">ID: ${player.id}</div>
                            </div>
                        </div>
                    `;
          });

          // 将新的单选框添加到容器中
          container.innerHTML += html;

          // 重新渲染表单，确保单选框正确显示
          layui.form.render("radio");
        } else {
          console.error("加载玩家列表失败:", result.msg);
        }
      })
      .catch((error) => {
        console.error("加载玩家列表错误:", error);
      });
  }

  // 将 addRewardItem 函数定义为全局函数
  window.addRewardItem = function(type) {
    const container = document.querySelector(`#${type}RewardsContainer .rewards-list`);
    const items = container.querySelectorAll('.reward-item');
    const index = items.length;

    let newItemHtml = '';
    switch(type) {
        case 'points':
            newItemHtml = `
                <div class="reward-item">
                    <div class="layui-input-inline" style="width: 120px;">
                        <select name="points_rewards[${index}].type">
                            <option value="exp">经验值</option>
                            <option value="points">积分</option>
                        </select>
                    </div>
                    <div class="layui-input-inline" style="width: 120px;">
                        <input type="number" name="points_rewards[${index}].number" 
                               placeholder="数量" class="layui-input">
                    </div>
                    <div class="layui-btn layui-btn-xs layui-btn-danger" onclick="removeRewardItem(this)">
                        <i class="layui-icon">&#xe640;</i>
                    </div>
                </div>`;
            break;
        case 'card':
            newItemHtml = `
                <div class="reward-item">
                    <div class="layui-input-inline" style="width: 120px;">
                        <input type="number" name="card_rewards[${index}].id" 
                               placeholder="卡片ID" class="layui-input">
                    </div>
                    <div class="layui-input-inline" style="width: 120px;">
                        <input type="number" name="card_rewards[${index}].number" 
                               placeholder="数量" class="layui-input">
                    </div>
                    <div class="layui-btn layui-btn-xs layui-btn-danger" onclick="removeRewardItem(this)">
                        <i class="layui-icon">&#xe640;</i>
                    </div>
                </div>`;
            break;
        case 'medal':
            newItemHtml = `
                <div class="reward-item">
                    <div class="layui-input-inline" style="width: 120px;">
                        <input type="number" name="medal_rewards[${index}].id" 
                               placeholder="成就ID" class="layui-input">
                    </div>
                    <div class="layui-btn layui-btn-xs layui-btn-normal" onclick="showMedalList(this)">
                        <i class="layui-icon">&#xe615;</i> 选择勋章
                    </div>
                    <div class="layui-btn layui-btn-xs layui-btn-danger" onclick="removeRewardItem(this)">
                        <i class="layui-icon">&#xe640;</i>
                    </div>
                </div>`;
            break;
        case 'real':
            newItemHtml = `
                <div class="reward-item">
                    <div class="layui-input-inline" style="width: 120px;">
                        <input type="text" name="real_rewards[${index}].name" 
                               placeholder="奖品名称" class="layui-input">
                    </div>
                    <div class="layui-input-inline" style="width: 120px;">
                        <input type="number" name="real_rewards[${index}].number" 
                               placeholder="数量" class="layui-input">
                    </div>
                    <div class="layui-btn layui-btn-xs layui-btn-danger" onclick="removeRewardItem(this)">
                        <i class="layui-icon">&#xe640;</i>
                    </div>
                </div>`;
            break;
    }

    container.insertAdjacentHTML('beforeend', newItemHtml);
    
    // 重新渲染表单元素
    layui.use(['form'], function(){
        var form = layui.form;
        form.render();
    });
  };

  // 添加删除奖励项的全局函数
  window.removeRewardItem = function(btn) {
    const rewardItem = btn.closest('.reward-item');
    if (rewardItem) {
        rewardItem.remove();
    }
  };

  // 修改 showMedalList 函数，存储弹窗索引
  window.showMedalList = function(btn) {
    layui.use(['layer', 'jquery'], function(){
        var layer = layui.layer;
        var $ = layui.jquery;

        fetch('/admin/api/medals')
            .then(response => response.json())
            .then(result => {
                if (result.code === 0) {
                    let content = `
                        <div class="medal-list-container" style="padding: 15px;">
                            <table class="layui-table">
                                <thead>
                                    <tr>
                                        <th>ID</th>
                                        <th>勋章名称</th>
                                        <th>描述</th>
                                        <th>操作</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;

                    result.data.forEach(medal => {
                        content += `
                            <tr>
                                <td>${medal.id}</td>
                                <td>${medal.name}</td>
                                <td>${medal.description}</td>
                                <td>
                                    <button class="layui-btn layui-btn-xs" 
                                            onclick="selectMedal(${medal.id}, this)">
                                        选择
                                    </button>
                                </td>
                            </tr>
                        `;
                    });

                    content += `
                                </tbody>
                            </table>
                        </div>
                    `;

                    // 打开弹窗并存储索引
                    const medalListIndex = layer.open({
                        type: 1,
                        title: '选择勋章',
                        area: ['800px', '600px'],
                        content: content,
                        success: function(layero, index) {
                            const inputElement = $(btn).siblings('.layui-input-inline').find('input')[0];
                            // 同时存储输入框引用和弹窗索引
                            layero.find('.layui-table').data('targetInput', inputElement);
                            layero.find('.layui-table').data('layerIndex', index);
                        }
                    });
                } else {
                    layer.msg('获取勋章列表失败：' + result.msg);
                }
            })
            .catch(error => {
                console.error('获取勋章列表错误:', error);
                layer.msg('获取勋章列表失败');
            });
    });
  };

  // 修改 selectMedal 函数，只关闭当前弹窗
  window.selectMedal = function(medalId, btn) {
    layui.use(['layer', 'jquery'], function(){
        var layer = layui.layer;
        var $ = layui.jquery;

        const $table = $(btn).closest('.layui-table');
        const targetInput = $table.data('targetInput');
        const layerIndex = $table.data('layerIndex');

        if (targetInput) {
            targetInput.value = medalId;
            // 只关闭当前勋章选择弹窗
            layer.close(layerIndex);
            layer.msg('已选择勋章');
        } else {
            layer.msg('操作失败：未找到目标输入框');
        }
    });
  };

  // 添加样式
  const style = `
    <style>
        .medal-list-container {
            max-height: 500px;
            overflow-y: auto;
        }
        .medal-list-container .layui-table {
            margin: 0;
        }
        .reward-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        .reward-item .layui-btn {
            margin-right: 5px;
        }
    </style>
  `;
  document.head.insertAdjacentHTML('beforeend', style);

  console.log("TaskForm.js loaded, showTaskFormDialog:", typeof window.showTaskFormDialog);
})(window);
