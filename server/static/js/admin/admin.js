layui.use(["layer", "form", "element", "table"], function () {
  var layer = layui.layer;
  var form = layui.form;
  var element = layui.element;
  var table = layui.table;
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
                        <td>${medal.description || ""}</td>
                        <td>${new Date(medal.addtime * 1000).toLocaleString()}</td>
                        <td>${medal.icon ? `<img src="${medal.icon}" alt="图标" style="width:30px;height:30px;">` : ""}</td>
                        <td>${medal.conditions || ""}</td>
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
            points: points,
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
          description: $('textarea[name="description"]').val(), //todo 修改标记
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
          window.showTaskFormDialog("edit", task.data);
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
    layer.confirm(
      "确定要删除这个任务吗？",
      {
        btn: ["确定", "取消"],
      },
      function () {
        fetch(`/admin/api/tasks/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.code === 0 || result.success) {
              layer.msg("删除成功");
              // 刷新表格
              layui.table.reload("taskTable");
            } else {
              throw new Error(result.msg || result.error);
            }
          })
          .catch((error) => {
            layer.msg("删除失败: " + error.message);
          });
      }
    );
  };

  // 显示添加勋章表单
  window.showAddMedalForm = function () {
    layer.open({
      type: 1,
      title: "添加勋章",
      content: $("#medalForm"),
      area: ["500px", "600px"],
      btn: ["确定", "取消"],
      yes: function (index) {
        const formData = {
          name: $('input[name="medal-name"]').val(),
          description: $('textarea[name="medal-description"]').val(),
          icon: $('input[name="medal-icon"]').val(),
          conditions: $('textarea[name="medal-conditions"]').val(),
        };
        console.log(formData);

        fetch("/admin/api/medals", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.code === 0) {
              layer.close(index);
              layer.msg("添加成功");
              loadMedals();
            } else {
              throw new Error(result.msg);
            }
          })
          .catch((error) => {
            layer.msg("添加失败: " + error.message);
          });
      },
    });
  };

  // 编辑勋章
  window.editMedal = function (id) {
    fetch(`/admin/api/medals/${id}`)
      .then((response) => response.json())
      .then((result) => {
        if (result.code === 0) {
          const medal = result.data;
          console.log("Retrieved medal data:", medal); // 添加调试信息

          // 清空表单
          $("#medalForm form")[0].reset();

          // 填充表单数据
          const form = $("#medalForm form");
          form.find('input[name="medal-name"]').val(medal.name);
          form.find('textarea[name="medal-description"]').val(medal.description);
          form.find('input[name="medal-icon"]').val(medal.icon);
          form.find('textarea[name="medal-conditions"]').val(medal.conditions);

          console.log("Form values after setting:", {
            // 添加调试信息
            name: form.find('input[name="medal-name"]').val(),
            description: form.find('textarea[name="medal-description"]').val(),
            icon: form.find('input[name="medal-icon"]').val(),
            conditions: form.find('textarea[name="medal-conditions"]').val(),
          });

          layer.open({
            type: 1,
            title: "编辑勋章",
            content: $("#medalForm"),
            area: ["500px", "600px"],
            btn: ["确定", "取消"],
            yes: function (index) {
              const formData = {
                name: form.find('input[name="medal-name"]').val(),
                description: form.find('textarea[name="medal-description"]').val(),
                icon: form.find('input[name="medal-icon"]').val(),
                conditions: form.find('textarea[name="medal-conditions"]').val(),
              };

              console.log("Submitting medal data:", formData); // 添加调试信息

              fetch(`/admin/api/medals/${id}`, {
                method: "PUT",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify(formData),
              })
                .then((response) => response.json())
                .then((result) => {
                  console.log("Update result:", result); // 添加调试信息
                  if (result.code === 0) {
                    layer.close(index);
                    layer.msg("更新成功");
                    loadMedals();
                  } else {
                    throw new Error(result.msg);
                  }
                })
                .catch((error) => {
                  console.error("Update error:", error); // 添加调试信息
                  layer.msg("更新失败: " + error.message);
                });
            },
          });
        } else {
          throw new Error(result.msg);
        }
      })
      .catch((error) => {
        console.error("Failed to get medal data:", error); // 添加调试信息
        layer.msg("获取勋章数据失败: " + error.message);
      });
  };

  // 删除勋章
  window.deleteMedal = function (id) {
    layer.confirm(
      "确定要删除这个勋章吗？",
      {
        btn: ["确定", "取消"],
      },
      function () {
        fetch(`/admin/api/medals/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.code === 0) {
              layer.msg("删除成功");
              loadMedals();
            } else {
              throw new Error(result.msg);
            }
          })
          .catch((error) => {
            layer.msg("删除失败: " + error.message);
          });
      }
    );
  };

  // 初始化任务列表
  function initTaskPanel() {
    // 渲染表格
    table.render({
      elem: "#taskTable",
      url: "/admin/api/tasks",
      page: true,
      limit: 10,
      limits: [10, 20, 50, 100],
      cols: [
        [
          { field: "id", title: "ID", width: 60, sort: true, fixed: "left" },
          { field: "name", title: "任务名称", width: 120 },
          { field: "description", title: "描述", width: 200 },
          { field: "task_chain_id", title: "任务链ID", width: 90 },
          { field: "parent_task_id", title: "父任务ID", width: 90 },
          {
            field: "task_type",
            title: "类型",
            width: 90,
            templet: function (d) {
              const type = {
                DAILY: { name: "日常任务", color: "#4CAF50" },
                MAIN: { name: "主线任务", color: "#2196F3" },
                BRANCH: { name: "支线任务", color: "#9C27B0" },
                SPECIAL: { name: "特殊任务", color: "#FF9800" },
              }[d.task_type] || { name: d.task_type, color: "#999" };
              return `<span style="color: ${type.color}">${type.name}</span>`;
            },
          },
          {
            field: "task_status",
            title: "状态",
            width: 90,
            templet: function (d) {
              const status = {
                LOCKED: { name: "未解锁", color: "#9e9e9e" },
                AVAIL: { name: "可接受", color: "#2196F3" },
                ACCEPT: { name: "已接受", color: "#FF9800" },
                COMPLETED: { name: "已完成", color: "#4CAF50" },
              }[d.task_status] || { name: d.task_status, color: "#999" };
              return `<span style="color: ${status.color}">${status.name}</span>`;
            },
          },
          { field: "task_scope", title: "任务范围", width: 90 },
          { field: "stamina_cost", title: "体力消耗", width: 90 },
          { field: "limit_time", title: "时间限制", width: 90 },
          { field: "repeat_time", title: "重复次数", width: 90 },
          {
            field: "is_enabled",
            title: "是否启用",
            width: 90,
            templet: function (d) {
              return d.is_enabled ? '<span class="layui-badge layui-bg-green">是</span>' : '<span class="layui-badge layui-bg-gray">否</span>';
            },
          },
          {
            field: "repeatable",
            title: "可重复",
            width: 90,
            templet: function (d) {
              return d.repeatable ? '<span class="layui-badge layui-bg-blue">是</span>' : '<span class="layui-badge layui-bg-red">否</span>';
            },
          },
          {
            field: "task_rewards",
            title: "奖励",
            width: 200,
            templet: function (d) {
              let rewards = [];
              if (d.task_rewards) {
                const tr = typeof d.task_rewards === "string" ? JSON.parse(d.task_rewards) : d.task_rewards;

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
              return rewards.join(" | ");
            },
          },
          { title: "操作", width: 160, fixed: "right", align: "center", toolbar: "#taskTableBar" },
        ],
      ],
      parseData: function (res) {
        return {
          code: res.code,
          msg: res.msg,
          count: res.count,
          data: res.data,
        };
      },
      done: function () {
        // 表格加载完成后的回调
        console.log("Task table rendered");
      },
    });

    // 监听工具条事件
    table.on("tool(taskTable)", function (obj) {
      var data = obj.data;
      if (obj.event === "edit") {
        window.showTaskFormDialog("edit", data);
      } else if (obj.event === "del") {
        // 使用全局的 deleteTask 函数
        window.deleteTask(data.id);
      }
    });
  }

  // 在页面加载完成后初始化所有面板
  document.addEventListener("DOMContentLoaded", function () {
    // ... existing initialization code ...

    // 初始化任务面板
    initTaskPanel();
  });

  // 添加刷新任务列表的全局函数
  window.reloadTasks = function () {
    layui.table.reload("taskTable");
  };

  // 显示添加NFC卡片表单
  window.showAddNFCCardForm = function () {
    // 重置表单
    const form = $("#nfcCardForm form")[0];
    if (form) {
      form.reset();
    }

    // 禁用卡片ID输入框，由后端自增生成
    $('input[name="card_id"]').prop("disabled", true);

    // 设置默认数值为1
    $('input[name="value"]').val(1);

    // 隐藏所有选择容器
    $("#taskSelectContainer, #medalSelectContainer, #cardSelectContainer").hide();

    layer.open({
      type: 1,
      title: "添加NFC卡片",
      content: $("#nfcCardForm"),
      area: ["500px", "600px"],
      btn: ["确定", "取消"],
      success: function () {
        // 重新渲染表单
        layui.form.render();
      },
      yes: function (index) {
        const formData = {
          type: $('select[name="nfc_form_type"]').val(),
          id: $('input[name="nfc_form_id"]').val(),
          value: $('input[name="nfc_form_value"]').val() || 1,
          description: $('textarea[name="nfc_form_description"]').val(),
          device: $('input[name="nfc_form_device"]').val(),
          status: "UNLINK", // 默认状态为未关联
        };
        console.log("formData", formData);

        // 验证必填字段
        if (!formData.type) {
          layer.msg("请选择卡片类型");
          return;
        }
        if (!formData.id) {
          layer.msg("请选择关联ID");
          return;
        }

        // 发送请求
        $.ajax({
          url: "/admin/api/nfc/cards",
          type: "POST",
          contentType: "application/json",
          data: JSON.stringify(formData),
          success: function (res) {
            if (res.code === 0) {
              layer.msg("添加成功");
              layer.close(index);
              loadNFCCards();
            } else {
              layer.msg(res.msg || "添加失败");
            }
          },
        });
      },
    });
  };

  // 监听NFC卡片类型选择
  layui.form.on("select(nfcType)", function (data) {
    const taskContainer = $("#taskSelectContainer");
    const medalContainer = $("#medalSelectContainer");
    const cardContainer = $("#cardSelectContainer");
    const idInput = $('input[name="nfc_form_id"]');

    // 隐藏所有选择容器
    taskContainer.hide();
    medalContainer.hide();
    cardContainer.hide();

    // 根据类型显示对应的选择器
    switch (data.value) {
      case "TASK":
        loadTasks();
        taskContainer.show();
        idInput.prop("readonly", true);
        break;
      case "MEDAL":
        loadMedalsForNFC();
        medalContainer.show();
        idInput.prop("readonly", true);
        break;
      case "CARD":
        loadGameCards();
        cardContainer.show();
        idInput.prop("readonly", true);
        break;
      default:
        idInput.prop("readonly", false);
        break;
    }
  });

  // 监听任务选择变化
  layui.form.on("select(taskSelect)", function (data) {
    if (data.value) {
      const option = $(data.elem).find("option:selected");
      const taskInfo = {
        id: option.data("id"),
        name: option.data("name"),
        description: option.data("description"),
      };

      // 自动填充表单
      const form = $("#nfcCardForm form");
      form.find('input[name="nfc_form_id"]').val(taskInfo.id);
      form.find('textarea[name="nfc_form_description"]').val(taskInfo.description);
    }
  });

  // 监听成就选择变化
  layui.form.on("select(medalSelect)", function (data) {
    if (data.value) {
      const option = $(data.elem).find("option:selected");
      const medalInfo = {
        id: option.data("id"),
        name: option.data("name"),
        description: option.data("description"),
      };

      // 自动填充表单
      const form = $("#nfcCardForm form");
      form.find('input[name="nfc_form_id"]').val(medalInfo.id);
      form.find('textarea[name="nfc_form_description"]').val(medalInfo.description);
    }
  });

  // 监听道具卡选择变化
  layui.form.on("select(gameCardSelect)", function (data) {
    if (data.value) {
      const option = $(data.elem).find("option:selected");
      const cardInfo = {
        id: option.data("id"),
        name: option.data("name"),
        description: option.data("description"),
      };

      // 自动填充表单
      const form = $("#nfcCardForm form");
      form.find('input[name="nfc_form_id"]').val(cardInfo.id);
      form.find('textarea[name="nfc_form_description"]').val(cardInfo.description);
    }
  });

  // NFC设备状态检查
  function checkNFCDeviceStatus() {
    $.ajax({
      url: "/admin/api/nfc/device/status",
      type: "GET",
      success: function (res) {
        if (res.code === 0) {
          $("#deviceStatus")
            .text(res.data.connected ? "已连接" : "未连接")
            .removeClass("status-error status-success")
            .addClass(res.data.connected ? "status-success" : "status-error");

          $("#cardStatus")
            .text(res.data.card_present ? "已检测到卡片" : "未检测到卡片")
            .removeClass("status-error status-success")
            .addClass(res.data.card_present ? "status-success" : "status-error");
        }
      },
    });
  }

  // 定期检查NFC设备状态 1分钟
  setInterval(checkNFCDeviceStatus, 60000);

  // 写入NFC卡片
  function writeNFCCard(cardData) {
    return new Promise((resolve, reject) => {
      function checkAndWrite() {
        $.ajax({
          url: "/admin/api/nfc/device/status",
          type: "GET",
          success: function (res) {
            if (res.code === 0) {
              if (!res.data.connected) {
                layer.msg("请先连接NFC读写设备");
                reject("设备未连接");
                return;
              }

              if (!res.data.card_present) {
                layer.msg("请将NFC卡片放置在读写设备上", {
                  time: 0,
                  btn: ["取消"],
                  yes: function (index) {
                    layer.close(index);
                    reject("用户取消操作");
                  },
                });

                // 继续检查卡片是否就位
                setTimeout(checkAndWrite, 1000);
                return;
              }

              // 卡片就位，执行写入
              $.ajax({
                url: "/admin/api/nfc/write",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify(cardData),
                success: function (writeRes) {
                  if (writeRes.code === 0) {
                    layer.msg("写入成功");
                    resolve(writeRes);
                  } else {
                    layer.msg("写入失败：" + writeRes.msg);
                    reject(writeRes.msg);
                  }
                },
                error: function (err) {
                  layer.msg("写入失败");
                  reject(err);
                },
              });
            }
          },
        });
      }

      checkAndWrite();
    });
  }

  // 修改showWriteNFCForm函数
  window.showWriteNFCForm = function () {
    const selectedData = layui.table.checkStatus("nfcCardTable").data[0];
    if (!selectedData) {
      layer.msg("请先选择要写入的NFC卡片");
      return;
    }

    if (selectedData.status !== "UNLINK") {
      layer.msg("该卡片已关联实体NFC卡片");
      return;
    }

    layer.confirm(
      "确认要将数据写入NFC卡片吗？",
      {
        btn: ["确定", "取消"],
      },
      function (index) {
        writeNFCCard(selectedData)
          .then(() => {
            // 更新卡片状态为BAN
            $.ajax({
              url: `/admin/api/nfc/cards/${selectedData.card_id}`,
              type: "PUT",
              contentType: "application/json",
              data: JSON.stringify({ status: "BAN" }),
              success: function (res) {
                if (res.code === 0) {
                  layer.msg("状态更新成功");
                  loadNFCCards();
                }
              },
            });
            layer.close(index);
          })
          .catch(() => {
            layer.close(index);
          });
      }
    );
  };

  // 获取选中的NFC卡片数据
  function getSelectedNFCCard() {
    const selected = layui.table.checkStatus("nfcCardTable");
    return selected.data[0];
  }

  // 加载NFC卡片列表
  function loadNFCCards() {
    $.ajax({
      url: "/admin/api/nfc/cards",
      type: "GET",
      success: function (res) {
        if (res.code === 0) {
          renderNFCCardTable(res.data);
        }
      },
    });
  }

  // 渲染NFC卡片表格
  function renderNFCCardTable(data) {
    const tbody = $("#nfcCardTable tbody");
    tbody.empty();

    data.forEach((card) => {
      tbody.append(`
            <tr>
                <td>${card.card_id}</td>
                <td>${card.type}</td>
                <td>${card.id}</td>
                <td>${card.value}</td>
                <td>${card.status}</td>
                <td>${formatTime(card.addtime)}</td>
                <td>${card.description}</td>
                <td>${card.device}</td>
                <td>
                    <button class="layui-btn layui-btn-xs" onclick="editNFCCard(${card.card_id})">编辑</button>
                    <button class="layui-btn layui-btn-danger layui-btn-xs" onclick="deleteNFCCard(${card.card_id})">删除</button>
                </td>
            </tr>
        `);
    });
    layui.table.reload("nfcCardTable");
  }

  // 加载任务列表
  function loadTasks() {
    $.ajax({
      url: "/admin/api/tasks",
      type: "GET",
      success: function (res) {
        if (res.code === 0) {
          const taskSelect = $('select[name="taskId"]');
          taskSelect.empty();
          taskSelect.append('<option value="">请选择任务</option>');

          res.data.forEach((task) => {
            taskSelect.append(`<option value="${task.id}" 
                        data-id="${task.id}"
                        data-name="${task.name}"
                        data-description="${task.description}"
                    >${task.name}</option>`);
          });

          // 重新渲染select
          layui.form.render("select");
        } else {
          layer.msg("加载任务列表失败：" + res.msg);
        }
      },
      error: function () {
        layer.msg("加载任务列表失败");
      },
    });
  }
  // 加载道具卡列表
  function loadGameCards() {
    $.ajax({
      url: "/admin/api/game_cards",
      type: "GET",
      success: function (res) {
        if (res.code === 0) {
          const cardSelect = $('select[name="gameCardId"]');
          cardSelect.empty();
          cardSelect.append('<option value="">请选择道具卡</option>');

          res.data.forEach((card) => {
            cardSelect.append(`<option value="${card.id}" 
                        data-id="${card.id}"
                        data-name="${card.name}"
                        data-description="${card.description}"
                    >${card.name}</option>`);
          });

          layui.form.render("select");
        } else {
          layer.msg("加载道具卡列表失败：" + res.msg);
        }
      },
      error: function () {
        layer.msg("加载道具卡列表失败");
      },
    });
  }

  // 加载成就列表
  function loadMedalsForNFC() {
    $.ajax({
      url: "/admin/api/medals",
      type: "GET",
      success: function (res) {
        if (res.code === 0) {
          const medalSelect = $('select[name="medalId"]');
          medalSelect.empty();
          medalSelect.append('<option value="">请选择成就</option>');

          res.data.forEach((medal) => {
            medalSelect.append(`<option value="${medal.id}" 
                        data-id="${medal.id}"
                        data-name="${medal.name}"
                        data-description="${medal.description}"
                    >${medal.name}</option>`);
          });

          layui.form.render("select");
        } else {
          layer.msg("加载成就列表失败：" + res.msg);
        }
      },
      error: function () {
        layer.msg("加载成就列表失败");
      },
    });
  }

  // 初始化NFC表格
  function initNFCTable() {
    console.log("开始初始化NFC表格");
    console.log("检查表格元素:", $("#nfcCardTable").length ? "存在" : "不存在");
    console.log("检查layui:", typeof layui !== "undefined" ? "layui已加载" : "layui未加载");

    console.log("layui.table模块加载状态:", layui.table ? "成功" : "失败");

    try {
      const tableIns = layui.table.render({
        elem: "#nfcCardTable",
        url: "/admin/api/nfc/cards",
        page: true,
        cols: [
          [
            { type: "checkbox" },
            { field: "card_id", title: "卡片ID", width: 100 },
            {
              field: "type",
              title: "类型",
              width: 100,
              templet: function (d) {
                console.log("渲染类型字段:", d.type);
                const typeMap = {
                  ID: "身份卡",
                  TASK: "任务卡",
                  MEDAL: "成就卡",
                  POINTS: "积分卡",
                  CARD: "道具卡",
                };
                return typeMap[d.type] || d.type;
              },
            },
            { field: "id", title: "关联ID", width: 100 },
            { field: "value", title: "数值", width: 100 },
            {
              field: "status",
              title: "状态",
              width: 100,
              templet: function (d) {
                console.log("渲染状态字段:", d.status);
                const statusMap = {
                  UNLINK: "未关联",
                  BAN: "未启用",
                  INACTIVE: "待激活",
                  ACTIVE: "已激活",
                  USED: "已使用",
                };
                return statusMap[d.status] || d.status;
              },
            },
            {
              field: "addtime",
              title: "添加时间",
              width: 160,
              templet: function (d) {
                console.log("渲染时间字段:", d.addtime);
                return d.addtime ? new Date(d.addtime * 1000).toLocaleString() : "";
              },
            },
            { field: "description", title: "描述" },
            { field: "device", title: "设备标识", width: 120 },
            { title: "操作", width: 150, toolbar: "#nfcCardTableBar", fixed: "right" },
          ],
        ],
        parseData: function (res) {
          console.log("解析返回数据:", res);
          return {
            code: res.code === 0 ? 0 : 1,
            msg: res.msg,
            count: res.data ? res.data.length : 0,
            data: res.data || [],
          };
        },
        done: function (res, curr, count) {
          console.log("表格渲染完成");
          console.log("数据总数:", count);
          console.log("当前页:", curr);
          console.log("接口返回:", res);
        },
      });

      console.log("表格实例:", tableIns);
    } catch (error) {
      console.error("表格渲染错误:", error);
    }
  }

  // 确保在页面加载完成后初始化表格
  $(document).ready(function () {
    console.log("文档加载完成");
    console.log("检查NFC表格容器:", document.getElementById("nfcCardTable"));

    if ($("#nfcCardTable").length) {
      console.log("找到NFC表格元素，开始初始化");
      // 确保layui完全加载
      if (typeof layui !== "undefined") {
        console.log("Layui加载完成，开始初始化表格");
        initNFCTable();
      } else {
        console.error("Layui未加载完成");
        // 等待layui加载
        const checkLayui = setInterval(function () {
          if (typeof layui !== "undefined") {
            console.log("Layui加载完成，开始初始化表格");
            clearInterval(checkLayui);
            initNFCTable();
          }
        }, 100);
      }
    } else {
      console.error("未找到NFC表格元素");
    }
  });
  // 添加工具栏模板
  $("body").append(`
    <script type="text/html" id="nfcCardTableBar">
        <a class="layui-btn layui-btn-xs" lay-event="edit">编辑</a>
        <a class="layui-btn layui-btn-danger layui-btn-xs" lay-event="del">删除</a>
    </script>
  `);
  // 监听表格工具条事件

  console.log("注册表格工具条事件");
  layui.table.on("tool(nfcCardTable)", function (obj) {
    console.log("触发工具条事件:", obj.event);
    const data = obj.data;
    if (obj.event === "edit") {
      console.log("编辑数据:", data);
      editNFCCard(data);
    } else if (obj.event === "del") {
      console.log("准备删除数据:", data);
      layer.confirm("确认删除此卡片？", function (index) {
        deleteNFCCard(data.card_id);
        layer.close(index);
      });
    }
  });

  // 删除NFC卡片
  function deleteNFCCard(cardId) {
    $.ajax({
      url: "/admin/api/nfc/cards/" + cardId,
      type: "DELETE",
      success: function (res) {
        if (res.code === 0) {
          layer.msg("删除成功");
          layui.table.reload("nfcCardTable");
        } else {
          layer.msg(res.msg || "删除失败");
        }
      },
    });
  }

  // 编辑NFC卡片
  function editNFCCard(data) {
    // 重置表单
    const form = $("#nfcCardForm form")[0];
    if (form) {
      form.reset();
    }

    // 填充表单数据
    $('select[name="nfc_form_type"]').val(data.type);
    $('input[name="nfc_form_id"]').val(data.id);
    $('input[name="nfc_form_value"]').val(data.value);
    $('textarea[name="nfc_form_description"]').val(data.description);
    $('input[name="nfc_form_device"]').val(data.device);

    layer.open({
      type: 1,
      title: "编辑NFC卡片",
      content: $("#nfcCardForm"),
      area: ["500px", "600px"],
      btn: ["确定", "取消"],
      success: function () {
        layui.form.render();
      },
      yes: function (index) {
        // 构建发送到后端的数据，使用原始字段名
        const formData = {
          type: $('select[name="nfc_form_type"]').val(),
          id: $('input[name="nfc_form_id"]').val(),
          value: $('input[name="nfc_form_value"]').val(),
          description: $('textarea[name="nfc_form_description"]').val(),
          device: $('input[name="nfc_form_device"]').val(),
        };

        $.ajax({
          url: "/admin/api/nfc/cards/" + data.card_id,
          type: "PUT",
          contentType: "application/json",
          data: JSON.stringify(formData),
          success: function (res) {
            if (res.code === 0) {
              layer.msg("更新成功");
              layer.close(index);
              layui.table.reload("nfcCardTable");
            } else {
              layer.msg(res.msg || "更新失败");
            }
          },
        });
      },
    });
  }
});
// 添加工具条模板到页面 任务管理面板
document.body.insertAdjacentHTML(
  "beforeend",
  `
  <script type="text/html" id="taskTableBar">
      <a class="layui-btn layui-btn-xs" lay-event="edit">编辑</a>
      <a class="layui-btn layui-btn-danger layui-btn-xs" lay-event="del">删除</a>
  </script>
`
);
