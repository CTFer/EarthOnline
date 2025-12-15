// 用户认证模块
class AuthManager {
  // 初始化认证
  init() {
    console.log("[Roadmap] Initializing authentication");
    this.checkLogin();
  }
  
  // 检查登录状态
  checkLogin() {
    console.log("[Roadmap] Checking login status");
    $.get("/roadmap/api/check_login", function (res) {
      try {
        const data = typeof res === "string" ? JSON.parse(res) : res;
        if (data.code == 0 && data.data) {
          // 已登录
          $("#currentUser").text(data.data.username);
          taskManager.loadTasks();
        } else {
          // 未登录，显示登录框
          this.showLoginForm();
        }
      } catch (e) {
        console.error("[Roadmap] Error checking login status:", e);
        layer.msg("检查登录状态失败", { icon: 2 });
      }
    }.bind(this));
  }
  
  // 显示登录表单
  showLoginForm() {
    console.log("[Roadmap] Showing login form");
    layer.open({
      type: 1,
      title: "用户登录",
      content: $("#loginFormTpl").html(),
      closeBtn: 0,
      area: ["600px", "500px"],
    });
  }
  
  // 登录表单提交
  loginSubmit(data) {
    console.log("[Roadmap] Submitting login form");
    $.ajax({
      url: "/roadmap/api/login",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(data.field),
      success: function (res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code === 0) {
            layer.closeAll();
            $("#currentUser").text(data.data.username);
            taskManager.loadTasks();
            layer.msg("登录成功", { icon: 1 });
            localStorage.setItem("Roadmap_PlayerId", data.data.user_id);
          } else {
            layer.msg("登录失败: " + data.msg, { icon: 2 });
          }
        } catch (e) {
          console.error("[Roadmap] Error parsing login response:", e);
          layer.msg("数据解析错误", { icon: 2 });
        }
      },
    });
  }
  
  // 退出登录
  logout() {
    console.log("[Roadmap] Logging out");
    layer.confirm("确定要退出登录吗？", { icon: 3, title: "提示" }, function (index) {
      $.get("/roadmap/api/logout", function (res) {
        try {
          const data = typeof res === "string" ? JSON.parse(res) : res;
          if (data.code === 0) {
            layer.msg("已退出登录", { icon: 1 });
            setTimeout(() => {
              window.location.reload();
            }, 1000);
          } else {
            layer.msg("退出失败: " + data.msg, { icon: 2 });
          }
        } catch (e) {
          console.error("[Roadmap] Error logging out:", e);
          layer.msg("数据解析错误", { icon: 2 });
        }
      });
      layer.close(index);
    });
  }
}