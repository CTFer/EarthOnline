layui.use(["layer", "form", "element", "table"], function () {
  var layer = layui.layer;
  var form = layui.form;
  var element = layui.element;
  var table = layui.table;

  // MD5加密函数
  function md5(string) {
    return CryptoJS.MD5(string).toString();
  }

  // 获取当前登录用户信息
  let currentUsername = "";

  // 页面加载完成后执行
  $(document).ready(function () {
    console.log("[Admin] 初始化管理界面");

    // 从页面元素获取用户名
    currentUsername = $(".admin-name").text().trim();
    console.log("[Admin] 当前用户:", currentUsername);

    // 初始化其他功能
    loadUsers();
    loadPlayers();
    loadSkills();
    loadMedals();
    loadApiDocs();
    initTaskPanel();
    initNFCOperations();
    initNFCStatusPanel();

    // 绑定NFC操作按钮事件
    $('.nfc-operations .layui-btn').each(function() {
        const $btn = $(this);
        if ($btn.text().includes('写入')) {
            $btn.on('click', showNFCWriteForm);
        } else if ($btn.text().includes('读取')) {
            $btn.on('click', readNFCCardData);
        }
    });
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
                    <td>${player.sex === 1 ? "男" : "女"}</td>
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
    console.log("[NFC] 打开添加卡片表单");

    // 先获取下一个可用的card_id
    $.ajax({
      url: "/admin/api/nfc/cards",
      type: "GET",
      success: function (res) {
        if (res.code === 0) {
          const nextId = (res.data.next_card_id || 0) + 1;
          console.log("[NFC] 获取到下一个card_id:", nextId);

          // 重置表单
          const form = $("#nfcCardForm form")[0];
          if (form) {
            form.reset();
          }

          // 打开表单并填充数据
          layer.open({
            type: 1,
            title: "添加NFC卡片",
            content: $("#nfcCardForm"),
            area: ["500px", "600px"],
            btn: ["确定", "取消"],
            success: function () {
              // 设置并禁用card_id输入
              const cardIdInput = $('input[name="card_id"]');
              cardIdInput.val(nextId);
              cardIdInput.prop("readonly", true);

              // 设置默认状态为UNLINK
              $('select[name="nfc_form_status"]').val("UNLINK");

              // 设置device为当前管理员用户名
              $('input[name="nfc_form_device"]').val(currentUsername);

              // 重新渲染表单
              layui.form.render();
            },
            yes: function (index) {
              const formData = {
                type: $('select[name="nfc_form_type"]').val(),
                id: $('input[name="nfc_form_id"]').val(),
                value: $('input[name="nfc_form_value"]').val(),
                description: $('textarea[name="nfc_form_description"]').val(),
                device: $('input[name="nfc_form_device"]').val(),
              };

              console.log("[NFC] 提交表单数据:", formData);

              $.ajax({
                url: "/admin/api/nfc/cards",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify(formData),
                success: function (res) {
                  if (res.code === 0) {
                    if (res.data.card_id === nextId) {
                      layer.msg("添加成功");
                      layer.close(index);
                      table.reload("nfcCardTable");
                    } else {
                      layer.msg("添加成功但ID不匹配，请检查");
                    }
                  } else {
                    layer.msg(res.msg || "添加失败");
                  }
                },
              });
            },
          });
        } else {
          layer.msg("获取卡片ID失败");
        }
      },
    });
  };

  // 打开NFC卡片表单
  window.openNFCCardForm = function (nextCardId) {
    layer.open({
      type: 1,
      title: "添加NFC卡片",
      area: ["500px", "600px"],
      content: $("#nfcCardForm"),
      success: function () {
        // 设置card_id并禁用
        const cardIdInput = $('input[name="card_id"]');
        cardIdInput.val(nextCardId);
        cardIdInput.prop("readonly", true);

        // 设置device为当前用户名
        $('input[name="nfc_form_device"]').val(currentUsername);

        // 重新渲染表单
        layui.form.render();
      },
    });
  };

  // 提交NFC卡片表单（数据库操作）
  window.submitNFCCardForm = function (data) {
    console.log("[NFC DB] 提交卡片数据:", data);

    // 构建数据库数据
    const dbData = {
      type: data.type,
      player_id: parseInt(data.player_id) || 0,
      id: parseInt(data.id),
      value: parseInt(data.value),
      description: data.description,
      device: currentUsername,
      status: "UNLINK", // 初始状态
    };

    console.log("[NFC DB] 准备写入数据库:", dbData);

    $.ajax({
      url: "/admin/api/nfc/cards",
      type: "POST",
      contentType: "application/json",
      data: JSON.stringify(dbData),
      success: function (res) {
        if (res.code === 0) {
          layer.msg("添加成功");
          layer.closeAll("page");
          table.reload("nfcCardTable");
        } else {
          layer.msg(res.msg || "添加失败");
        }
      },
    });
  };

  // 显示写入确认对话框
  function showWriteConfirmDialog(data, currentStatus) {
    // 格式化数据显示
    const formattedData = formatNFCData(data);
    const rawData = generateNFCDataString(data);

    layer.confirm(
      `<div class="write-confirm-dialog">
            <p>警告：当前卡片状态为 ${currentStatus}，是否继续写入？</p>
            <div class="data-preview">
                <h4>原始数据格式：</h4>
                <pre>${rawData}</pre>
                <h4>格式化数据：</h4>
                <pre>${formattedData}</pre>
            </div>
        </div>`,
      {
        title: "确认写入",
        area: ["500px", "400px"],
        btn: ["确认写入", "取消"],
      },
      function (index) {
        writeCardData(data);
        layer.close(index);
      }
    );
  }

  // 格式化NFC数据显示
  function formatNFCData(data) {
    return JSON.stringify(
      {
        卡片ID: data.card_id,
        类型: data.type,
        玩家ID: data.player_id,
        关联ID: data.id,
        数值: data.value,
        设备: data.device,
      },
      null,
      2
    );
  }

  // 生成NFC数据字符串
  function generateNFCDataString(data) {
    console.log("[NFC] 生成数据字符串:", data);
    return `http://${VAR_DEVSERVER}/api/nfc_post|card_id=${data.card_id};type=${data.type};player_id=${data.player_id || 0};id=${data.id};value=${data.value};device=${data.device};`;
  }

  // 写入卡片数据
  function writeCardData(data) {
    console.log("[NFC] 准备写入数据:", data);

    // 检查设备状态并写入
    checkDeviceAndWrite(data)
      .then(() => {
        const nfcData = generateNFCDataString(data);
        return writeNFCCard(nfcData);
      })
      .then((success) => {
        if (success) {
          // 写入成功后更新列表
          loadNFCCards();
          layer.closeAll();
        }
      });
  }

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

  // NFC设备状态管理
  function initNFCOperations() {
    console.log("[NFC] 初始化NFC操作面板");

    // 初始化NFC卡片表格
    table.render({
      elem: "#nfcCardTable",
      url: "/admin/api/nfc/cards",
      page: true,
      cols: [
        [
          { field: "card_id", title: "卡片ID", width: 100, sort: true },
          {
            field: "type",
            title: "类型",
            width: 120,
            templet: function (d) {
              const types = {
                ID: "身份卡",
                TASK: "任务卡",
                MEDAL: "成就卡",
                Points: "积分卡",
                CARD: "道具卡",
              };
              return types[d.type] || d.type;
            },
          },
          { field: "id", title: "关联ID", width: 100 },
          { field: "value", title: "数值", width: 100 },
          {
            field: "status",
            title: "状态",
            width: 120,
            templet: function (d) {
              const status = {
                UNLINK: "未关联",
                BAN: "未启用",
                INACTIVE: "待激活",
                ACTIVE: "已激活",
                USED: "已使用",
              };
              return status[d.status] || d.status;
            },
          },
          { field: "description", title: "描述" },
          { field: "device", title: "设备标识", width: 120 },
          {
            field: "addtime",
            title: "添加时间",
            width: 160,
            templet: function (d) {
              return d.addtime ? new Date(d.addtime * 1000).toLocaleString() : "";
            },
          },
          { title: "操作", width: 200, toolbar: "#nfcCardTableBar" },
        ],
      ],
      response: {
        statusCode: 0,
      },
      parseData: function (res) {
        return {
          code: res.code,
          msg: res.msg,
          count: res.data.cards.length,
          data: res.data.cards,
        };
      },
    });

    // 监听工具条事件
    table.on("tool(nfcCardTable)", function (obj) {
      const data = obj.data;
      if (obj.event === "write") {
        writeNFCHardware(data);
      } else if (obj.event === "edit") {
        editNFCCard(data);
      } else if (obj.event === "del") {
        deleteNFCCard(data.card_id);
      }
    });
  }

  // 写入NFC实体卡片（硬件操作）
  function writeNFCHardware(cardData) {
    console.log("[NFC Hardware] 准备写入实体卡片:", cardData);
    
    // 检查卡片状态并调用checkNFCHardwareAndWrite
    if (cardData.status !== "UNLINK") {
        layer.confirm(
            `
                <div class="write-confirm-dialog">
                    <p>警告：当前卡片状态为 ${cardData.status}，是否继续写入？</p>
                    <div class="data-preview">
                        <h4>写入数据预览：</h4>
                        <pre>${formatNFCHardwareData(cardData)}</pre>
                        <h4>原始数据格式：</h4>
                        <pre>${generateNFCHardwareString(cardData)}</pre>
                    </div>
                </div>
            `,
            {
                title: "确认写入实体卡片",
                area: ["500px", "400px"],
                btn: ["确认写入", "取消"],
            },
            function (index) {
                checkNFCHardwareAndWrite(cardData);
                layer.close(index);
            }
        );
    } else {
        checkNFCHardwareAndWrite(cardData);
    }
  }

  // 检查NFC设备状态并写入
  function checkNFCHardwareAndWrite(cardData) {
    console.log("[NFC Hardware] 检查设备状态");
    $.ajax({
        url: "/admin/api/nfc/hardware/status",
        type: "GET",
        success: function(res) {
            console.log("[NFC Hardware] 设备状态检查结果:", res); // 添加日志
            
            // 修正属性名称
            if (res.code === 0 && res.data.device_connected && res.data.card_present) {
                console.log("[NFC Hardware] 设备就绪，开始写入");
                executeNFCHardwareWrite(cardData);
            } else {
                // 添加更详细的错误信息
                let errorMsg = "NFC设备未就绪或未检测到卡片: ";
                if (!res.data.device_connected) {
                    errorMsg += "设备未连接";
                } else if (!res.data.card_present) {
                    errorMsg += "未检测到卡片";
                }
                layer.msg(errorMsg);
                console.log("[NFC Hardware] 状态检查失败:", res.data);
            }
        },
        error: function(xhr, status, error) {
            console.error("[NFC Hardware] 状态检查请求失败:", error);
            layer.msg("设备状态检查失败: " + error);
        }
    });
  }

  // 执行NFC硬件写入操作
  function executeNFCHardwareWrite(cardData) {
    console.log("[NFC Hardware] 执行写入操作");
    const writeData = {
        CARD_ID: cardData.card_id,
        TYPE: cardData.type,
        PLAYER_ID: cardData.player_id || 0,
        ID: cardData.id,
        VALUE: cardData.value,
        TIMESTAMP: Math.floor(Date.now() / 1000),
        DEVICE: currentUsername,
    };

    // 添加数据格式检查和日志
    console.log("[NFC Hardware] 写入数据:", writeData);
    
    // 验证必要字段
    const requiredFields = ['CARD_ID', 'TYPE', 'ID', 'VALUE'];
    const missingFields = requiredFields.filter(field => !writeData[field]);
    
    if (missingFields.length > 0) {
        console.error("[NFC Hardware] 缺少必要字段:", missingFields);
        layer.msg('写入数据不完整，请检查必要字段');
        return;
    }

    // 生成URL格式的数据字符串
    const urlData = `http://{VAR_DEVSERVER}/api/nfc_post|CARD_ID=${writeData.CARD_ID};TYPE=${writeData.TYPE};PLAYER_ID=${writeData.PLAYER_ID};ID=${writeData.ID};VALUE=${writeData.VALUE};TIMESTAMP=${writeData.TIMESTAMP};DEVICE=${writeData.DEVICE};`;
    
    console.log("[NFC Hardware] 生成的URL数据:", urlData);

    $.ajax({
        url: "/admin/api/nfc/hardware/write",
        type: "POST",
        contentType: "application/json",
        data: JSON.stringify({
            data: urlData
        }),
        success: function(res) {
            if (res.code === 0) {
                layer.msg("实体卡片写入成功");
                updateCardStatus(cardData.card_id, "ACTIVE");
            } else {
                layer.msg(res.msg || "实体卡片写入失败");
                console.error("[NFC Hardware] 写入失败:", res.msg);
            }
        },
        error: function(xhr, error) {
            console.error("[NFC Hardware] 写入请求失败:", error);
            layer.msg("写入请求失败: " + error);
        }
    });
  }

  // 格式化NFC硬件数据显示
  function formatNFCHardwareData(data) {
    return JSON.stringify(
      {
        卡片ID: data.card_id,
        类型: data.type,
        玩家ID: data.player_id || 0,
        关联ID: data.id,
        数值: data.value,
        时间戳: new Date().toLocaleString(),
        设备标识: currentUsername,
      },
      null,
      2
    );
  }

  // 生成NFC硬件数据字符串
  function generateNFCHardwareString(data) {
    console.log("[NFC Hardware] 生成数据字符串:", data);
    const timestamp = Math.floor(Date.now() / 1000);
    return `http://{VAR_DEVSERVER}/api/nfc_post|CARD_ID=${data.card_id};TYPE=${data.type};PLAYER_ID=${data.player_id || 0};ID=${data.id};VALUE=${data.value};TIMESTAMP=${timestamp};DEVICE=${currentUsername};`;
  }

  // 更新卡片状态
  function updateCardStatus(cardId, status) {
    console.log("[NFC] 更新卡片状态:", cardId, status);
    $.ajax({
      url: "/admin/api/nfc/cards/" + cardId,
      type: "PUT",
      contentType: "application/json",
      data: JSON.stringify({
        status: status,
      }),
      success: function (res) {
        if (res.code === 0) {
          table.reload("nfcCardTable");
        } else {
          console.error("[NFC] 更新卡片状态失败:", res.msg);
        }
      },
    });
  }

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
          table.reload("nfcCardTable");
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
              table.reload("nfcCardTable");
            } else {
              layer.msg(res.msg || "更新失败");
            }
          },
        });
      },
    });
  }

  // 页面加载完成后初始化NFC操作
  $(document).ready(function () {
    console.log("[NFC] 初始化NFC功能");
    initNFCOperations();
  });

  // NFC状态检查功能
  function initNFCStatusPanel() {
    console.log("[NFC] 初始化状态检查面板");
    
    // 绑定状态检查按钮事件
    $("#checkNFCStatus").on("click", function() {
        checkNFCStatus();
    });

    // 初始检查
    checkNFCStatus();
  }

  // 检查NFC状态
  function checkNFCStatus() {
    console.log("[NFC] 开始检查设备状态");
    
    // 更新最后检查时间
    $("#lastCheckTime").text("检查时间: " + new Date().toLocaleString());
    
    // 更新状态为检查中
    updateDeviceStatus("checking", "检查中...");
    updateCardStatus("checking", "检查中...");
    
    $.ajax({
        url: "/admin/api/nfc/hardware/status",
        type: "GET",
        success: function(res) {
            console.log("[NFC] 状态检查结果:", res);
            
            if (res.code === 0) {
                // 更新设备状态
                if (res.data.device_connected) {
                    updateDeviceStatus("connected", "已连接");
                    // 显示端口信息
                    $("#portInfo").text(res.data.port || "");
                } else {
                    updateDeviceStatus("disconnected", "未连接");
                    $("#portInfo").text("");
                }
                
                // 更新卡片状态
                if (res.data.card_present) {
                    updateCardStatus("card-present", "已放置");
                } else {
                    updateCardStatus("no-card", "未检测到卡片");
                }
            } else {
                updateDeviceStatus("disconnected", "检查失败");
                updateCardStatus("disconnected", "检查失败");
                console.error("[NFC] 状态检查失败:", res.data);
            }
        },
        error: function(xhr, status, error) {
            console.error("[NFC] 状态检查请求失败:", error);
            updateDeviceStatus("disconnected", "请求失败");
            updateCardStatus("disconnected", "请求失败");
        }
    });
  }

  // 更新设备状态显示
  function updateDeviceStatus(status, text) {
    const deviceStatus = $("#deviceStatus");
    deviceStatus.removeClass("connected disconnected checking")
                .addClass(status)
                .text(text);
  }

  // 更新卡片状态显示
  function updateCardStatus(status, text) {
    const cardStatus = $("#cardStatus");
    cardStatus.removeClass("connected disconnected card-present no-card checking")
              .addClass(status)
              .text(text);
  }

  // NFC卡片操作相关函数
  async function checkNFCDeviceStatus() {
    console.log("[NFC] 检查设备状态");
    try {
        const response = await fetch('/admin/api/nfc/hardware/status');
        const result = await response.json();
        
        if (result.code === 0) {
            console.log("[NFC] 设备状态:", result.data);
            return result.data;
        } else {
            throw new Error(result.msg || '获取设备状态失败');
        }
    } catch (error) {
        console.error("[NFC] 设备状态检查失败:", error);
        layer.msg('设备状态检查失败: ' + error.message);
        return null;
    }
  }

  // 显示NFC卡片写入表单
  async function showNFCWriteForm() {
    console.log("[NFC] 打开写入表单");
    
    // 检查设备状态
    const deviceStatus = await checkNFCDeviceStatus();
    if (!deviceStatus || !deviceStatus.device_connected) {
        layer.msg('NFC设备未连接，请先检查设备状态');
        return;
    }
    
    try {
        // 获取下一个可用卡片ID
        const response = await fetch('/admin/api/nfc/next_card_id');
        const result = await response.json();
        
        if (result.code === 0) {
            console.log("[NFC] 获取到下一个卡片ID:", result.data.next_id);
            showAddNFCCardForm(result.data.next_id); // 使用现有的表单显示函数
        } else {
            throw new Error(result.msg || '获取卡片ID失败');
        }
    } catch (error) {
        console.error("[NFC] 获取卡片ID失败:", error);
        layer.msg('获取卡片ID失败: ' + error.message);
    }
  }

  // 读取NFC卡片数据
  async function readNFCCardData() {
    console.log("[NFC] 开始读取卡片");
    
    // 检查设备状态
    const deviceStatus = await checkNFCDeviceStatus();
    if (!deviceStatus || !deviceStatus.device_connected) {
        layer.msg('NFC设备未连接，请先检查设备状态');
        return;
    }
    
    // 显示等待提示
    const loadingIndex = layer.msg('请将卡片放置在读卡器上...', {
        icon: 16,
        time: 0,
        shade: 0.3
    });
    // const loadingIndex = layer.load(1, {
    //   shade: [0.3, '#fff']
    // });
    
    try {
        const response = await fetch('/admin/api/nfc/hardware/read', {
            method: 'POST'
        });
        const result = await response.json();
        layer.close(loadingIndex);
        
        if (result.code === 0 && result.data) {
            console.log("[NFC] 读取结果:", result.data);
            
            // 构建显示内容
            let content = `
                <div class="layui-card">
                    <div class="layui-card-header">卡片数据</div>
                    <div class="layui-card-body">
                        <div class="layui-form">
                            <div class="layui-form-item">
                                <label class="layui-form-label">类型</label>
                                <div class="layui-input-block">
                                    <input type="text" class="layui-input" value="${result.data.params.type || ''}" readonly>
                                </div>
                            </div>
                            <div class="layui-form-item">
                                <label class="layui-form-label">玩家ID</label>
                                <div class="layui-input-block">
                                    <input type="text" class="layui-input" value="${result.data.params.player_id || ''}" readonly>
                                </div>
                            </div>
                            <div class="layui-form-item">
                                <label class="layui-form-label">关联ID</label>
                                <div class="layui-input-block">
                                    <input type="text" class="layui-input" value="${result.data.params.id || ''}" readonly>
                                </div>
                            </div>
                            <div class="layui-form-item">
                                <label class="layui-form-label">数值</label>
                                <div class="layui-input-block">
                                    <input type="text" class="layui-input" value="${result.data.params.value || '0'}" readonly>
                                </div>
                            </div>
                            <div class="layui-form-item">
                                <label class="layui-form-label">设备标识</label>
                                <div class="layui-input-block">
                                    <input type="text" class="layui-input" value="${result.data.params.device || ''}" readonly>
                                </div>
                            </div>
                            <div class="layui-form-item">
                                <label class="layui-form-label">原始数据</label>
                                <div class="layui-input-block">
                                    <textarea class="layui-textarea" readonly style="height: 100px">${result.data.raw_data}</textarea>
                                </div>
                            </div>
                        </div>
                        <div class="layui-btn-container" style="margin-top: 15px">
                            <button class="layui-btn" onclick="fillWriteForm(${JSON.stringify(result.data.params).replace(/"/g, '&quot;')})">
                                填充到写卡表单
                            </button>
                        </div>
                    </div>
                </div>`;
                
            layer.open({
                type: 1,
                title: 'NFC卡片数据',
                content: content,
                area: ['600px', '700px'],
                shadeClose: true
            });
        } else {
            layer.msg(result.msg || '读取失败');
        }
    } catch (error) {
        layer.close(loadingIndex);
        console.error("[NFC] 读取失败:", error);
        layer.msg('读取失败: ' + error.message);
    }
  }

  // 填充写卡表单
  window.fillWriteForm = function(params) {
    console.log("[NFC] 填充表单数据:", params);
    
    try {
        // 获取写卡表单
        const form = $('#nfcWriteForm');
        if (!form.length) {
            console.error("[NFC] 未找到写卡表单");
            return;
        }
        
        // 填充表单字段
        form.find('select[name="type"]').val(params.type);
        form.find('input[name="player_id"]').val(params.player_id);
        form.find('input[name="id"]').val(params.id);
        form.find('input[name="value"]').val(params.value);
        form.find('input[name="device"]').val(params.device);
        
        // 如果使用了layui表单，需要更新渲染
        if (window.layui && layui.form) {
            layui.form.render('select');
        }
        
        layer.msg('表单数据已填充');
        
    } catch (error) {
        console.error("[NFC] 填充表单失败:", error);
        layer.msg('填充表单失败: ' + error.message);
    }
  }
});
