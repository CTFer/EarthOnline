// 确保函数在全局作用域可用
(function (window) {
  console.log("TaskForm.js loading");

  // 确保 layui 已加载
  if (typeof layui === "undefined") {
    console.error("Layui is not loaded!");
    return;
  }

  // 任务类型常量
  const TASK_TYPES = {
    DAILY: { name: "日常任务", color: "#4CAF50" },
    MAIN: { name: "主线任务", color: "#2196F3" },
    BRANCH: { name: "支线任务", color: "#9C27B0" },
    SPECIAL: { name: "特殊任务", color: "#FF9800" },
  };

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
              "points_rewards[0].number": taskData.task_rewards?.points_rewards?.[0]?.number || 0,
              "points_rewards[1].number": taskData.task_rewards?.points_rewards?.[1]?.number || 0,
              "card_rewards[0].id": taskData.task_rewards?.card_rewards?.[0]?.id || 0,
              "card_rewards[0].number": taskData.task_rewards?.card_rewards?.[0]?.number || 0,
              "medal_rewards[0].id": taskData.task_rewards?.medal_rewards?.[0]?.id || 0,
              "medal_rewards[0].number": taskData.task_rewards?.medal_rewards?.[0]?.number || 0,
            });
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

  // 获取表单内容
  function getTaskFormContent() {
    return `
        <div class="task-form-scroll">
            <form class="layui-form" lay-filter="taskForm">
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
                        <input type="radio" name="task_type" value="DAILY" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">日常任务</div>
                            </div>
                        </div>
                        
                        <input type="radio" name="task_type" value="MAIN" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">主线任务</div>
                            </div>
                        </div>
                        
                        <input type="radio" name="task_type" value="BRANCH" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">支线任务</div>
                            </div>
                        </div>
                        
                        <input type="radio" name="task_type" value="SPECIAL" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">特殊任务</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="layui-form-item">
                    <label class="layui-form-label">任务状态</label>
                    <div class="layui-input-block" id="taskStatusRadios">
                        <input type="radio" name="task_status" value="0" lay-skin="none" checked>
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">未开始</div>
                                <div class="lay-skin-taskcard-description" style="color: #9e9e9e">
                                    任务尚未开始
                                </div>
                            </div>
                        </div>
                        
                        <input type="radio" name="task_status" value="1" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">进行中</div>
                                <div class="lay-skin-taskcard-description" style="color: #2196F3">
                                    任务正在进行
                                </div>
                            </div>
                        </div>
                        
                        <input type="radio" name="task_status" value="2" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">已完成</div>
                                <div class="lay-skin-taskcard-description" style="color: #4CAF50">
                                    任务已完成
                                </div>
                            </div>
                        </div>
                        
                        <input type="radio" name="task_status" value="3" lay-skin="none">
                        <div lay-radio class="lay-skin-taskcard">
                            <div class="lay-skin-taskcard-detail">
                                <div class="lay-skin-taskcard-header">已失败</div>
                                <div class="lay-skin-taskcard-description" style="color: #f44336">
                                    任务失败或已过期
                                </div>
                            </div>
                        </div>
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
                    <label class="layui-form-label">积分奖励</label>
                    <div class="layui-input-block">
                        <div class="layui-input-inline" style="width: 120px;">
                            <input type="number" name="points_rewards[0].number" 
                                   placeholder="经验值" class="layui-input" value="100">
                        </div>
                        <div class="layui-input-inline" style="width: 120px;">
                            <input type="number" name="points_rewards[1].number" 
                                   placeholder="积分" class="layui-input" value="10">
                        </div>
                    </div>
                </div>

                <div class="layui-form-item">
                    <label class="layui-form-label">卡片奖励</label>
                    <div class="layui-input-block">
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

                <div class="layui-form-item">
                    <label class="layui-form-label">成就奖励</label>
                    <div class="layui-input-block">
                        <div class="layui-input-inline" style="width: 120px;">
                            <input type="number" name="medal_rewards[0].id" 
                                   placeholder="成就ID" class="layui-input">
                        </div>
                        <div class="layui-input-inline" style="width: 120px;">
                            <input type="number" name="medal_rewards[0].number" 
                                   placeholder="经验值" class="layui-input">
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
        </style>
    `;
  }

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
        task_status: parseInt(formData.task_status),
        description: formData.description || '',
        task_scope: parseInt(formData.task_scope),
        stamina_cost: parseInt(formData.stamina_cost) || 0,
        limit_time: parseInt(formData.limit_time) || 0,
        repeat_time: parseInt(formData.repeat_time) || 1,
        is_enabled: formData.is_enabled === 'on',
        repeatable: formData.repeatable === 'on',
        task_rewards: {
          points_rewards: [
            { type: 'exp', number: parseInt(formData['points_rewards[0].number']) || 0 },
            { type: 'points', number: parseInt(formData['points_rewards[1].number']) || 0 }
          ],
          card_rewards: [
            {
              id: parseInt(formData['card_rewards[0].id']) || 0,
              number: parseInt(formData['card_rewards[0].number']) || 0
            }
          ],
          medal_rewards: [
            {
              id: parseInt(formData['medal_rewards[0].id']) || 0,
              number: parseInt(formData['medal_rewards[0].number']) || 0
            }
          ]
        }
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

  console.log("TaskForm.js loaded, showTaskFormDialog:", typeof window.showTaskFormDialog);
})(window);
