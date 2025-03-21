/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @LastEditTime: 2025-03-21 11:41:33
 * @LastEditors: 一根鱼骨棒
 * @Description: 用户管理模块
 */
import { gameUtils } from '../../utils/utils.js';
class UserAdmin {
  constructor() {
    this.layer = layui.layer;
    this.form = layui.form;
    this.$ = layui.jquery;

    // 初始化事件监听
    this.initEventListeners();
  }

  /**
   * 初始化事件监听
   */
  initEventListeners() {
    // 绑定按钮点击事件
    this.$("#addUserBtn").on("click", () => this.showAddUserForm());
    this.$("#addPlayerBtn").on("click", () => this.showAddPlayerForm());

    // 绑定用户表格操作事件
    this.$("#userTable").on("click", ".edit-user-btn", (e) => {
      const userId = this.$(e.currentTarget).data("id");
      this.editUser(userId);
    });

    this.$("#userTable").on("click", ".delete-user-btn", (e) => {
      const userId = this.$(e.currentTarget).data("id");
      this.deleteUser(userId);
    });

    // 绑定玩家表格操作事件
    this.$("#playerTable").on("click", ".edit-player-btn", (e) => {
      const playerId = this.$(e.currentTarget).data("id");
      this.editPlayer(playerId);
    });

    this.$("#playerTable").on("click", ".delete-player-btn", (e) => {
      const playerId = this.$(e.currentTarget).data("id");
      this.deletePlayer(playerId);
    });
  }

  /**
   * 加载用户列表
   */
  async loadUsers() {
    try {
      const response = await fetch("/admin/api/users");
      const result = await response.json();

      if (result.code !== 0) {
        throw new Error(result.msg || "加载失败");
      }

      const users = result.data || [];
      const tbody = document.querySelector("#userTable tbody");

      tbody.innerHTML = users
        .map(
          (user) => `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.nickname || '-'}</td>
                <td>${user.isadmin ? '<span class="layui-badge layui-bg-green">是</span>' : '<span class="layui-badge layui-bg-gray">否</span>'}</td>
                <td>${user.wechat_userid || '-'}</td>
                <td>${gameUtils.formatTimestamp(user.created_at)}</td>
                <td>
                    <button class="layui-btn layui-btn-sm edit-user-btn" data-id="${user.id}">编辑</button>
                    ${!user.isadmin ? `<button class="layui-btn layui-btn-sm layui-btn-danger delete-user-btn" data-id="${user.id}">删除</button>` : ''}
                </td>
            </tr>
          `
        )
        .join("");
    } catch (error) {
      console.error("加载用户失败:", error);
      this.layer.msg("加载用户失败: " + error.message);
    }
  }

  /**
   * 加载玩家列表
   */
  async loadPlayers() {
    try {
      const response = await fetch("/admin/api/players");
      const result = await response.json();

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
                            <td>${gameUtils.formatTimestamp(player.create_time)}</td>
                            <td>
                                <button class="layui-btn layui-btn-sm edit-player-btn" data-id="${player.player_id}">编辑</button>
                                <button class="layui-btn layui-btn-sm layui-btn-danger delete-player-btn" data-id="${player.player_id}">删除</button>
                            </td>
                        </tr>
                    `
        )
        .join("");
    } catch (error) {
      console.error("加载玩家失败:", error);
      this.layer.msg("加载玩家失败: " + error.message);
    }
  }

  /**
   * 重置用户表单
   * @private
   */
  _resetUserForm() {
    // 清空所有输入字段
    const formContent = this.$("#userForm");
    formContent.find('input[type="text"], input[type="password"]').val('');
    formContent.find('input[type="checkbox"]').prop('checked', false);
    
    // 重新渲染表单（对于layui的特殊控件）
    this.form.render();
  }

  /**
   * 显示添加用户表单
   */
  showAddUserForm() {
    // 获取表单模板
    const userFormHtml = this.$("#userForm").html();
    
    this.layer.open({
      type: 1,
      title: "添加用户",
      content: userFormHtml,
      area: ["500px", "600px"],
      success: (layero, index) => {
        // 重新渲染layui表单
        this.form.render(null, layero.find('.layui-form'));
      },
      btn: ["确定", "取消"],
      yes: (index, layero) => {
        const formData = {
          username: layero.find('input[name="username"]').val(),
          password: layero.find('input[name="password"]').val(),
          nickname: layero.find('input[name="nickname"]').val(),
          isadmin: layero.find('input[name="isadmin"]').prop('checked') ? 1 : 0,
          wechat_userid: layero.find('input[name="wechat_userid"]').val()
        };

        if (!formData.username || !formData.password) {
          this.layer.msg("用户名和密码不能为空");
          return;
        }

        fetch("/admin/api/adduser", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(formData),
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.code !== 0) {
              throw new Error(result.msg || "添加失败");
            }
            this.layer.msg("添加成功");
            this.layer.close(index);
            this.loadUsers();
          })
          .catch((error) => {
            console.error("添加用户失败:", error);
            this.layer.msg("添加用户失败: " + error.message);
          });
      },
    });
  }

  /**
   * 显示添加玩家表单
   */
  showAddPlayerForm() {
    this.layer.open({
      type: 1,
      title: "添加玩家",
      content: $("#playerForm"),
      area: ["500px", "500px"],
      btn: ["确定", "取消"],
      yes: (index) => {
        const player_name = $('input[name="player_name"]').val();
        const player_en_name = $('input[name="player_en_name"]').val();
        const level = $('input[name="level"]').val();
        const points = $('input[name="points"]').val();

        if (!player_name) {
          this.layer.msg("请填写完整信息");
          return;
        }

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
            this.layer.msg("添加成功");
            this.layer.close(index);
            this.loadPlayers();
          })
          .catch((error) => {
            console.error("添加玩家失败:", error);
            this.layer.msg("添加玩家失败: " + error.message);
          });
      },
    });
  }

  /**
   * 编辑用户
   */
  editUser(id) {
    // 获取表单模板
    const userFormHtml = this.$("#userForm").html();
    
    fetch(`/admin/api/users/${id}`)
      .then((response) => response.json())
      .then((result) => {
        if (result.code !== 0) {
          throw new Error(result.msg || "获取用户信息失败");
        }
        
        const user = result.data;
        
        this.layer.open({
          type: 1,
          title: "编辑用户",
          content: userFormHtml,
          area: ["500px", "600px"],
          success: (layero, index) => {
            // 填充表单数据
            layero.find('input[name="username"]').val(user.username);
            layero.find('input[name="password"]').val(""); // 密码框置空
            layero.find('input[name="nickname"]').val(user.nickname || '');
            layero.find('input[name="isadmin"]').prop('checked', user.isadmin === 1);
            layero.find('input[name="wechat_userid"]').val(user.wechat_userid || '');
            
            // 重新渲染layui表单
            this.form.render(null, layero.find('.layui-form'));
          },
          btn: ["确定", "取消"],
          yes: (index, layero) => {
            const formData = {
              username: layero.find('input[name="username"]').val(),
              nickname: layero.find('input[name="nickname"]').val(),
              isadmin: layero.find('input[name="isadmin"]').prop('checked') ? 1 : 0,
              wechat_userid: layero.find('input[name="wechat_userid"]').val()
            };
            
            // 如果输入了新密码，则添加到请求数据中
            const newPassword = layero.find('input[name="password"]').val();
            if (newPassword) {
              formData.password = newPassword;
            }

            fetch(`/admin/api/users/${id}`, {
              method: "PUT",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify(formData),
            })
              .then((response) => response.json())
              .then((result) => {
                if (result.code !== 0) {
                  throw new Error(result.msg || "更新失败");
                }
                this.layer.close(index);
                this.layer.msg("更新成功");
                this.loadUsers();
              })
              .catch((error) => {
                this.layer.msg("更新失败: " + error.message);
              });
          },
        });
      })
      .catch((error) => {
        this.layer.msg("获取用户信息失败: " + error.message);
      });
  }

  /**
   * 删除用户
   */
  deleteUser(id) {
    this.layer.confirm(
      "确定要删除这个用户吗？此操作不可恢复！",
      {
        btn: ["确定", "取消"],
      },
      () => {
        fetch(`/admin/api/users/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.code !== 0) {
              throw new Error(result.msg || "删除失败");
            }
            this.layer.msg("删除成功");
            this.loadUsers();
          })
          .catch((error) => {
            this.layer.msg("删除失败: " + error.message);
          });
      }
    );
  }

  /**
   * 删除玩家
   */
  deletePlayer(id) {
    this.layer.confirm(
      "确定要删除这个玩家吗？",
      {
        btn: ["确定", "取消"],
      },
      () => {
        fetch(`/admin/api/players/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.error) {
              throw new Error(result.error);
            }
            this.layer.msg("删除成功");
            this.loadPlayers();
          })
          .catch((error) => {
            this.layer.msg("删除失败: " + error.message);
          });
      }
    );
  }

  /**
   * 编辑玩家
   */
  editPlayer(id) {
    fetch(`/admin/api/players/${id}`)
      .then((response) => response.json())
      .then((player) => {
        $('input[name="player_name"]').val(player.player_name);
        $('input[name="points"]').val(player.points);
        $('input[name="level"]').val(player.level);

        this.layer.open({
          type: 1,
          title: "编辑玩家",
          content: $("#playerForm"),
          area: ["500px", "400px"],
          btn: ["确定", "取消"],
          yes: (index) => {
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
                this.layer.close(index);
                this.layer.msg("更新成功");
                this.loadPlayers();
              })
              .catch((error) => {
                this.layer.msg("更新失败: " + error.message);
              });
          },
        });
      });
  }
}

// 导出模块
export default UserAdmin;
