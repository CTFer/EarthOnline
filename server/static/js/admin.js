layui.use(["layer", "form", "element"], function () {
  var layer = layui.layer;
  var form = layui.form;
  var element = layui.element;
  var $ = layui.jquery;

  // MD5加密函数
  function md5(string) {
    return CryptoJS.MD5(string).toString();
  }

  // 页面加载完成后执行
  $(document).ready(function () {
    loadUsers();
    loadPlayers();
    loadSkills();
    loadMedals();
    loadApiDocs();
    initTaskPanel();
  });

  // 加载用户列表
  async function loadUsers() {
    try {
      const response = await fetch("/admin/api/users");
      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      const users = result.data || [];
      const tbody = document.querySelector("#userTable tbody");

      tbody.innerHTML = users
        .map(
          (user) => `
                <tr>
                    <td>${user.id}</td>
                    <td>${user.username}</td>
                    <td>${user.created_at}</td>
                    <td>
                        <button class="layui-btn layui-btn-sm" onclick="editUser(${user.id})">编辑</button>
                        <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="deleteUser(${user.id})">删除</button>
                    </td>
                </tr>
            `
        )
        .join("");
    } catch (error) {
      console.error("加载用户失败:", error);
      layer.msg("加载用户失败: " + error.message);
    }
  }
  // 加载玩家列表
  async function loadPlayers() {
    try {
      const response = await fetch("/admin/api/players");
      const result = await response.json();
      console.log(result);
      if (result.code) {
        throw new Error(result.msg);
      }

      const players = result.data || [];
      const tbody = document.querySelector("#playerTable tbody");

      tbody.innerHTML = players
        .map(
          (player) => `
                <tr>
                    <td>${player.player_id}</td>
                    <td>${player.player_name}</td>
                    <td>${player.level}</td>
                    <td>${player.experience}</td>
                    <td>${player.points}</td>
                    <td>${player.create_time}</td>
                    <td>
                        <button class="layui-btn layui-btn-sm" onclick="editPlayer(${player.player_id})">编辑</button>
                        <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="deletePlayer(${player.player_id})">删除</button>
                    </td>
                </tr>
            `
        )
        .join("");
    } catch (error) {
      console.error("加载玩家失败:", error);
      layer.msg("加载玩家失败: " + error.message);
    }
  }

  // 加载技能列表
  async function loadSkills() {
    try {
      const response = await fetch("/admin/api/skills");
      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      const skills = result.data || [];
      const tbody = document.querySelector("#skillTable tbody");

      tbody.innerHTML = skills
        .map(
          (skill) => `
                <tr>
                    <td>${skill.id}</td>
                    <td>${skill.name}</td>
                    <td>${skill.proficiency}</td>
                    <td>${skill.description || ""}</td>
                    <td>
                        <button class="layui-btn layui-btn-sm" onclick="editSkill(${skill.id})">编辑</button>
                        <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="deleteSkill(${skill.id})">删除</button>
                    </td>
                </tr>
            `
        )
        .join("");
    } catch (error) {
      console.error("加载技能失败:", error);
      layer.msg("加载技能失败: " + error.message);
    }
  }


  // 加载勋章列表
  async function loadMedals() {
    try {
      const response = await fetch("/admin/api/medals");
      const result = await response.json();

      if (result.code !== 0) {
        throw new Error(result.msg);
      }

      const medals = result.data || [];
      const tbody = document.querySelector("#medalTable tbody");

      tbody.innerHTML = medals
        .map(
          (medal) => `
                    <tr>
                        <td>${medal.id}</td>
                        <td>${medal.name}</td>
                        <td>${medal.description || ''}</td>
                        <td>${new Date(medal.addtime * 1000).toLocaleString()}</td>
                        <td>${medal.icon ? `<img src="${medal.icon}" alt="图标" style="width:30px;height:30px;">` : ''}</td>
                        <td>${medal.conditions || ''}</td>
                        <td>
                            <button class="layui-btn layui-btn-sm" onclick="editMedal(${medal.id})">编辑</button>
                            <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="deleteMedal(${medal.id})">删除</button>
                        </td>
                    </tr>
                `
        )
        .join("");
    } catch (error) {
      console.error("加载勋章失败:", error);
      layer.msg("加载勋章失败: " + error.message);
    }
  }

  // 加载API文档
  async function loadApiDocs() {
    try {
      const response = await fetch("/admin/api/docs");
      const result = await response.json();

      if (result.error) {
        throw new Error(result.error);
      }

      const adminApis = result.data.filter((api) => api.path.startsWith("/admin"));
      const gameApis = result.data.filter((api) => !api.path.startsWith("/admin"));

      // 渲染管理API
      document.getElementById("adminApiList").innerHTML = renderApiList(adminApis);

      // 渲染游戏API
      document.getElementById("gameApiList").innerHTML = renderApiList(gameApis);
    } catch (error) {
      console.error("加载API文档失败:", error);
      layer.msg("加载API文档失败: " + error.message);
    }
  }

  function renderApiList(apis) {
    return apis
      .map(
        (api) => `
            <div class="layui-card">
                <div class="layui-card-header">
                    <span class="layui-badge layui-bg-blue">${api.method}</span>
                    ${api.path}
                    ${api.auth_required ? '<span class="layui-badge">需要认证</span>' : ""}
                </div>
                <div class="layui-card-body">
                    <p>${api.description}</p>
                    ${api.parameters ? renderParameters(api.parameters) : ""}
                    ${api.response ? renderResponse(api.response) : ""}
                </div>
            </div>
        `
      )
      .join("");
  }

  function renderParameters(parameters) {
    return `
            <div class="layui-collapse">
                <div class="layui-colla-item">
                    <h2 class="layui-colla-title">请求参数</h2>
                    <div class="layui-colla-content">
                        <table class="layui-table">
                            <thead>
                                <tr>
                                    <th>参数名</th>
                                    <th>类型</th>
                                    <th>是否必须</th>
                                    <th>描述</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${parameters
                                  .map(
                                    (param) => `
                                    <tr>
                                        <td>${param.name}</td>
                                        <td>${param.type}</td>
                                        <td>${param.required ? "是" : "否"}</td>
                                        <td>${param.description}</td>
                                    </tr>
                                `
                                  )
                                  .join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
  }

  function renderResponse(response) {
    return `
            <div class="layui-collapse">
                <div class="layui-colla-item">
                    <h2 class="layui-colla-title">响应数据</h2>
                    <div class="layui-colla-content">
                        <pre class="layui-code">${JSON.stringify(response, null, 2)}</pre>
                    </div>
                </div>
            </div>
        `;
  }

  // 显示添加用户表单
  window.showAddUserForm = function () {
    layer.open({
      type: 1,
      title: "添加用户",
      content: $("#userForm"),
      area: ["500px", "300px"],
      btn: ["确定", "取消"],
      yes: function (index) {
        // 获取表单数据
        const username = $('input[name="username"]').val();
        const password = $('input[name="password"]').val();

        // 验证表单
        if (!username || !password) {
          layer.msg("请填写完整信息");
          return;
        }

        // 发送请求
        fetch("/admin/api/adduser", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            username: username,
            password: md5(password), // 密码MD5加密
          }),
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.error) {
              throw new Error(result.error);
            }
            layer.msg("添加成功");
            layer.close(index);
            loadUsers(); // 重新加载用户列表
          })
          .catch((error) => {
            console.error("添加用户失败:", error);
            layer.msg("添加用户失败: " + error.message);
          });
      },
    });
  };
  // 显示添加玩家表单
  window.showAddPlayerForm = function () {
    layer.open({
      type: 1,
      title: "添加玩家",
      content: $("#playerForm"),
      area: ["500px", "500px"],
      btn: ["确定", "取消"],
      yes: function (index) {
        // 获取表单数据
        const player_name = $('input[name="player_name"]').val();
        const player_en_name = $('input[name="player_en_name"]').val();
        const level = $('input[name="level"]').val();
        const points = $('input[name="points"]').val();

        // 验证表单
        if (!player_name) {
          layer.msg("请填写完整信息");
          return;
        }

        // 发送请求
        fetch("/admin/api/addplayer", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            player_name: player_name,
            english_name: player_en_name,
            level: level,
            points: points
          }),
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.error) {
              throw new Error(result.error);
            }
            layer.msg("添加成功");
            layer.close(index);
            loadUsers(); // 重新加载用户列表
          })
          .catch((error) => {
            console.error("添加用户失败:", error);
            layer.msg("添加用户失败: " + error.message);
          });
      },
    });
  };
  // 显示添加技能表单
  window.showAddSkillForm = function () {
    layer.open({
      type: 1,
      title: "添加技能",
      content: $("#skillForm"),
      area: ["500px", "400px"],
      btn: ["确定", "取消"],
      yes: function (index) {
        const formData = {
          name: $('input[name="name"]').val(),
          proficiency: parseInt($('input[name="proficiency"]').val()),
          description: $('textarea[name="description"]').val(),
        };

        fetch("/admin/api/skills", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.error) {
              throw new Error(result.error);
            }
            layer.close(index);
            layer.msg("添加成功");
            loadSkills();
          })
          .catch((error) => {
            layer.msg("添加失败: " + error.message);
          });
      },
    });
  };

  // 编辑用户
  window.editUser = function (id) {
    fetch(`/admin/api/users/${id}`)
      .then((response) => response.json())
      .then((user) => {
        $('input[name="username"]').val(user.username);
        $('input[name="password"]').val("");

        layer.open({
          type: 1,
          title: "编辑用户",
          content: $("#userForm"),
          area: ["500px", "300px"],
          btn: ["确定", "取消"],
          yes: function (index) {
            const formData = {
              username: $('input[name="username"]').val(),
              password: $('input[name="password"]').val(),
            };

            fetch(`/admin/api/users/${id}`, {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(formData),
            })
              .then((response) => response.json())
              .then((result) => {
                if (result.error) {
                  throw new Error(result.error);
                }
                layer.close(index);
                layer.msg("更新成功");
                loadUsers();
              })
              .catch((error) => {
                layer.msg("更新失败: " + error.message);
              });
          },
        });
      });
  };

  // 删除用户
  window.deleteUser = function (id) {
    layer.confirm(
      "确定要删除这个用户吗？",
      {
        btn: ["确定", "取消"],
      },
      function () {
        fetch(`/admin/api/users/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.error) {
              throw new Error(result.error);
            }
            layer.msg("删除成功");
            loadUsers();
          })
          .catch((error) => {
            layer.msg("删除失败: " + error.message);
          });
      }
    );
  };
  // 删除玩家
  window.deletePlayer = function (id) {
    layer.confirm(
      "确定要删除这个玩家吗？",
      {
        btn: ["确定", "取消"],
      },
      function () {
        fetch(`/admin/api/players/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.error) {
              throw new Error(result.error);
            }
            layer.msg("删除成功");
            loadUsers();
          })
          .catch((error) => {
            layer.msg("删除失败: " + error.message);
          });
      }
    );
  };
  // 编辑玩家
  window.editPlayer = function (id) {
    fetch(`/admin/api/players/${id}`)
      .then((response) => response.json())
      .then((player) => {
        $('input[name="player_name"]').val(player.player_name);
        $('input[name="points"]').val(player.points);
        $('input[name="level"]').val(player.level);
        console.log(player);

        layer.open({
          type: 1,
          title: "编辑玩家",
          content: $("#playerForm"),
          area: ["500px", "400px"],
          btn: ["确定", "取消"],
          yes: function (index) {
            const formData = {
              player_id: player.player_id,
              player_name: $('input[name="player_name"]').val(),
              points: $('input[name="points"]').val(),
              level: $('input[name="level"]').val(),
            };

            fetch(`/admin/api/players/${id}`, {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(formData),
            })
              .then((response) => response.json())
              .then((result) => {
                if (result.error) {
                  throw new Error(result.error);
                }
                layer.close(index);
                layer.msg("更新成功");
                loadPlayers();
              })
              .catch((error) => {
                layer.msg("更新失败: " + error.message);
              });
          },
        });
      });
  };
  // 编辑技能
  window.editSkill = function (id) {
    fetch(`/admin/api/skills/${id}`)
      .then((response) => response.json())
      .then((skill) => {
        $('input[name="name"]').val(skill.name);
        $('input[name="proficiency"]').val(skill.proficiency);
        $('textarea[name="description"]').val(skill.description);

        layer.open({
          type: 1,
          title: "编辑技能",
          content: $("#skillForm"),
          area: ["500px", "400px"],
          btn: ["确定", "取消"],
          yes: function (index) {
            const formData = {
              name: $('input[name="name"]').val(),
              proficiency: parseInt($('input[name="proficiency"]').val()),
              description: $('textarea[name="description"]').val(),
            };

            fetch(`/admin/api/skills/${id}`, {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(formData),
            })
              .then((response) => response.json())
              .then((result) => {
                if (result.error) {
                  throw new Error(result.error);
                }
                layer.close(index);
                layer.msg("更新成功");
                loadSkills();
              })
              .catch((error) => {
                layer.msg("更新失败: " + error.message);
              });
          },
        });
      });
  };

  // 删除技能
  window.deleteSkill = function (id) {
    layer.confirm(
      "确定要删除这个技能吗？",
      {
        btn: ["确定", "取消"],
      },
      function () {
        fetch(`/admin/api/skills/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.error) {
              throw new Error(result.error);
            }
            layer.msg("删除成功");
            loadSkills();
          })
          .catch((error) => {
            layer.msg("删除失败: " + error.message);
          });
      }
    );
  };

  // 编辑任务
  window.editTask = function (id) {
    fetch(`/admin/api/tasks/${id}`)
      .then((response) => response.json())
      .then((task) => {
        if (task.code == 0) {
          // 使用 taskForm.js 中定义的 showTaskFormDialog
          window.showTaskFormDialog('edit', task.data);
        } else {
          layer.msg(task.msg);
        }
      })
      .catch((error) => {
        layer.msg("获取任务数据失败: " + error.message);
      });
  };

  // 删除任务
  window.deleteTask = function (id) {
    layer.confirm("确定要删除这个任务吗？", {
      btn: ["确定", "取消"],
    }, function() {
      fetch(`/admin/api/tasks/${id}`, {
        method: "DELETE",
      })
      .then((response) => response.json())
      .then((result) => {
        if (result.code === 0 || result.success) {
          layer.msg("删除成功");
          // 刷新表格
          layui.table.reload('taskTable');
        } else {
          throw new Error(result.msg || result.error);
        }
      })
      .catch((error) => {
        layer.msg("删除失败: " + error.message);
      });
    });
  };

  // 显示添加勋章表单
  window.showAddMedalForm = function() {
    layer.open({
      type: 1,
      title: "添加勋章",
      content: $("#medalForm"),
      area: ["500px", "600px"],
      btn: ["确定", "取消"],
      yes: function(index) {
        const formData = {
          name: $('input[name="medal-name"]').val(),
          description: $('textarea[name="medal-description"]').val(),
          icon: $('input[name="medal-icon"]').val(),
          conditions: $('textarea[name="medal-conditions"]').val()
        };
        console.log(formData);
        

        fetch("/admin/api/medals", {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(result => {
          if (result.code === 0) {
            layer.close(index);
            layer.msg("添加成功");
            loadMedals();
          } else {
            throw new Error(result.msg);
          }
        })
        .catch(error => {
          layer.msg("添加失败: " + error.message);
        });
      }
    });
  };

  // 编辑勋章
  window.editMedal = function(id) {
    fetch(`/admin/api/medals/${id}`)
        .then(response => response.json())
        .then(result => {
            if (result.code === 0) {
                const medal = result.data;
                console.log("Retrieved medal data:", medal);  // 添加调试信息

                // 清空表单
                $('#medalForm form')[0].reset();

                // 填充表单数据
                const form = $('#medalForm form');
                form.find('input[name="medal-name"]').val(medal.name);
                form.find('textarea[name="medal-description"]').val(medal.description);
                form.find('input[name="medal-icon"]').val(medal.icon);
                form.find('textarea[name="medal-conditions"]').val(medal.conditions);

                console.log("Form values after setting:", {  // 添加调试信息
                    name: form.find('input[name="medal-name"]').val(),
                    description: form.find('textarea[name="medal-description"]').val(),
                    icon: form.find('input[name="medal-icon"]').val(),
                    conditions: form.find('textarea[name="medal-conditions"]').val()
                });

                layer.open({
                    type: 1,
                    title: "编辑勋章",
                    content: $("#medalForm"),
                    area: ["500px", "600px"],
                    btn: ["确定", "取消"],
                    yes: function(index) {
                        const formData = {
                            name: form.find('input[name="medal-name"]').val(),
                            description: form.find('textarea[name="medal-description"]').val(),
                            icon: form.find('input[name="medal-icon"]').val(),
                            conditions: form.find('textarea[name="medal-conditions"]').val()
                        };

                        console.log("Submitting medal data:", formData);  // 添加调试信息

                        fetch(`/admin/api/medals/${id}`, {
                            method: "PUT",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify(formData)
                        })
                        .then(response => response.json())
                        .then(result => {
                            console.log("Update result:", result);  // 添加调试信息
                            if (result.code === 0) {
                                layer.close(index);
                                layer.msg("更新成功");
                                loadMedals();
                            } else {
                                throw new Error(result.msg);
                            }
                        })
                        .catch(error => {
                            console.error("Update error:", error);  // 添加调试信息
                            layer.msg("更新失败: " + error.message);
                        });
                    }
                });
            } else {
                throw new Error(result.msg);
            }
        })
        .catch(error => {
            console.error("Failed to get medal data:", error);  // 添加调试信息
            layer.msg("获取勋章数据失败: " + error.message);
        });
  };

  // 删除勋章
  window.deleteMedal = function(id) {
    layer.confirm(
      "确定要删除这个勋章吗？",
      {
        btn: ["确定", "取消"]
      },
      function() {
        fetch(`/admin/api/medals/${id}`, {
          method: "DELETE"
        })
        .then(response => response.json())
        .then(result => {
          if (result.code === 0) {
            layer.msg("删除成功");
            loadMedals();
          } else {
            throw new Error(result.msg);
          }
        })
        .catch(error => {
          layer.msg("删除失败: " + error.message);
        });
      }
    );
  };

  // 初始化任务列表
  function initTaskPanel() {
    layui.use(['table', 'layer'], function(){
        var table = layui.table;
        var layer = layui.layer;
        
        // 渲染表格
        table.render({
            elem: '#taskTable'
            ,url: '/admin/api/tasks'
            ,page: true
            ,limit: 10
            ,limits: [10, 20, 50, 100]
            ,cols: [[
                {field: 'id', title: 'ID', width: 60, sort: true, fixed: 'left'}
                ,{field: 'name', title: '任务名称', width: 120}
                ,{field: 'description', title: '描述', width: 200}
                ,{field: 'task_chain_id', title: '任务链ID', width: 90}
                ,{field: 'parent_task_id', title: '父任务ID', width: 90}
                ,{field: 'task_type', title: '类型', width: 90, templet: function(d){
                    const type = {
                        DAILY: { name: "日常任务", color: "#4CAF50" },
                        MAIN: { name: "主线任务", color: "#2196F3" },
                        BRANCH: { name: "支线任务", color: "#9C27B0" },
                        SPECIAL: { name: "特殊任务", color: "#FF9800" }
                    }[d.task_type] || { name: d.task_type, color: "#999" };
                    return `<span style="color: ${type.color}">${type.name}</span>`;
                }}
                ,{field: 'task_status', title: '状态', width: 90, templet: function(d){
                    const status = {
                        LOCKED: { name: "未解锁", color: "#9e9e9e" },
                        AVAIL: { name: "可接受", color: "#2196F3" },
                        ACCEPT: { name: "已接受", color: "#FF9800" },
                        COMPLETED: { name: "已完成", color: "#4CAF50" }
                    }[d.task_status] || { name: d.task_status, color: "#999" };
                    return `<span style="color: ${status.color}">${status.name}</span>`;
                }}
                ,{field: 'task_scope', title: '任务范围', width: 90}
                ,{field: 'stamina_cost', title: '体力消耗', width: 90}
                ,{field: 'limit_time', title: '时间限制', width: 90}
                ,{field: 'repeat_time', title: '重复次数', width: 90}
                ,{field: 'is_enabled', title: '是否启用', width: 90, templet: function(d){
                    return d.is_enabled ? 
                        '<span class="layui-badge layui-bg-green">是</span>' : 
                        '<span class="layui-badge layui-bg-gray">否</span>';
                }}
                ,{field: 'repeatable', title: '可重复', width: 90, templet: function(d){
                    return d.repeatable ? 
                        '<span class="layui-badge layui-bg-blue">是</span>' : 
                        '<span class="layui-badge layui-bg-red">否</span>';
                }}
                ,{field: 'task_rewards', title: '奖励', width: 200, templet: function(d){
                    let rewards = [];
                    if (d.task_rewards) {
                        const tr = typeof d.task_rewards === 'string' ? 
                            JSON.parse(d.task_rewards) : d.task_rewards;
                        
                        if (tr.points_rewards?.length) {
                            rewards.push(`经验:${tr.points_rewards[0]?.number || 0}`);
                            rewards.push(`积分:${tr.points_rewards[1]?.number || 0}`);
                        }
                        if (tr.card_rewards?.length) {
                            rewards.push(`卡片ID:${tr.card_rewards[0]?.id || 0}`);
                        }
                        if (tr.medal_rewards?.length) {
                            rewards.push(`勋章ID:${tr.medal_rewards[0]?.id || 0}`);
                        }
                    }
                    return rewards.join(' | ');
                }}
                ,{title: '操作', width: 160, fixed: 'right', align:'center', toolbar: '#taskTableBar'}
            ]]
            ,parseData: function(res){
                return {
                    "code": res.code,
                    "msg": res.msg,
                    "count": res.count,
                    "data": res.data
                };
            }
            ,done: function(){
                // 表格加载完成后的回调
                console.log('Task table rendered');
            }
        });

        // 监听工具条事件
        table.on('tool(taskTable)', function(obj){
            var data = obj.data;
            if(obj.event === 'edit'){
                window.showTaskFormDialog('edit', data);
            } else if(obj.event === 'del'){
                // 使用全局的 deleteTask 函数
                window.deleteTask(data.id);
            }
        });
    });
  }

  // 在页面加载完成后初始化所有面板
  document.addEventListener('DOMContentLoaded', function() {
    // ... existing initialization code ...
    
    // 初始化任务面板
    initTaskPanel();
  });

  // 添加刷新任务列表的全局函数
  window.reloadTasks = function() {
    layui.table.reload('taskTable');
  };
});

// 添加工具条模板到页面
document.body.insertAdjacentHTML('beforeend', `
    <script type="text/html" id="taskTableBar">
        <a class="layui-btn layui-btn-xs" lay-event="edit">编辑</a>
        <a class="layui-btn layui-btn-danger layui-btn-xs" lay-event="del">删除</a>
    </script>
`);
