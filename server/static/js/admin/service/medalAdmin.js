/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @Date: 2025-02-25 11:17:32
 * @LastEditTime: 2025-02-25 13:53:35
 * @LastEditors: 一根鱼骨棒
 * @Description: 本开源代码使用GPL 3.0协议
 * Software: VScode
 * Copyright 2025 迷舍
 */
import { gameUtils } from '../../utils/utils.js';
class MedalAdmin {
  constructor() {
    this.layer = layui.layer;
    this.$ = layui.jquery;
  }

  // 加载勋章列表
  async loadMedals() {
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
                        <td>${gameUtils.formatTimestamp(medal.addtime)}</td>
                        <td>${medal.icon ? `<img src="${medal.icon}" alt="图标" style="width:30px;height:30px;">` : ""}</td>
                        <td>${medal.conditions || ""}</td>
                        <td>
                            <button class="layui-btn layui-btn-sm edit-medal-btn" data-id="${medal.id}">编辑</button>
                            <button class="layui-btn layui-btn-sm layui-btn-danger delete-medal-btn" data-id="${medal.id}">删除</button>
                        </td>
                    </tr>
                `
        )
        .join("");

      // 绑定按钮事件
      this.bindEvents();
    } catch (error) {
      console.error("加载勋章失败:", error);
      this.layer.msg("加载勋章失败: " + error.message);
    }
  }

  // 绑定事件
  bindEvents() {
    // 编辑按钮事件
    this.$("#medalTable").on("click", ".edit-medal-btn", (e) => {
      const medalId = this.$(e.currentTarget).data("id");
      this.editMedal(medalId);
    });

    // 删除按钮事件
    this.$("#medalTable").on("click", ".delete-medal-btn", (e) => {
      const medalId = this.$(e.currentTarget).data("id");
      this.deleteMedal(medalId);
    });

    // 添加勋章按钮事件
    this.$("#addMedalBtn").on("click", () => this.showAddMedalForm());
    // 选择图标按钮事件
    this.$("#selectIconBtn").on("click", () => this.selectIcon());
  }

  // 显示添加勋章表单
  showAddMedalForm() {
    this.layer.open({
      type: 1,
      title: "添加勋章",
      content: this.$("#medalForm"),
      area: ["500px", "600px"],
      btn: ["确定", "取消"],
      yes: (index) => {
        const formData = {
          name: this.$('input[name="medal-name"]').val(),
          description: this.$('textarea[name="medal-description"]').val(),
          icon: this.$('input[name="medal-icon"]').val(),
          conditions: this.$('textarea[name="medal-conditions"]').val(),
        };

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
              this.layer.close(index);
              this.layer.msg("添加成功");
              this.loadMedals();
            } else {
              throw new Error(result.msg);
            }
          })
          .catch((error) => {
            this.layer.msg("添加失败: " + error.message);
          });
      },
    });
  }

  // 编辑勋章
  editMedal(id) {
    fetch(`/admin/api/medals/${id}`)
      .then((response) => response.json())
      .then((result) => {
        if (result.code === 0) {
          const medal = result.data;

          // 清空表单
          this.$("#medalForm form")[0].reset();

          // 填充表单数据
          const form = this.$("#medalForm form");
          form.find('input[name="medal-name"]').val(medal.name);
          form.find('textarea[name="medal-description"]').val(medal.description);
          form.find('input[name="medal-icon"]').val(medal.icon);
          form.find('textarea[name="medal-conditions"]').val(medal.conditions);

          this.layer.open({
            type: 1,
            title: "编辑勋章",
            content: this.$("#medalForm"),
            area: ["500px", "600px"],
            btn: ["确定", "取消"],
            yes: (index) => {
              const formData = {
                name: form.find('input[name="medal-name"]').val(),
                description: form.find('textarea[name="medal-description"]').val(),
                icon: form.find('input[name="medal-icon"]').val(),
                conditions: form.find('textarea[name="medal-conditions"]').val(),
              };

              fetch(`/admin/api/medals/${id}`, {
                method: "PUT",
                headers: {
                  "Content-Type": "application/json",
                },
                body: JSON.stringify(formData),
              })
                .then((response) => response.json())
                .then((result) => {
                  if (result.code === 0) {
                    this.layer.close(index);
                    this.layer.msg("更新成功");
                    this.loadMedals();
                  } else {
                    throw new Error(result.msg);
                  }
                })
                .catch((error) => {
                  this.layer.msg("更新失败: " + error.message);
                });
            },
          });
        } else {
          throw new Error(result.msg);
        }
      })
      .catch((error) => {
        this.layer.msg("获取勋章数据失败: " + error.message);
      });
  }

  // 删除勋章
  deleteMedal(id) {
    this.layer.confirm(
      "确定要删除这个勋章吗？",
      {
        btn: ["确定", "取消"],
      },
      () => {
        fetch(`/admin/api/medals/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.code === 0) {
              this.layer.msg("删除成功");
              this.loadMedals();
            } else {
              throw new Error(result.msg);
            }
          })
          .catch((error) => {
            this.layer.msg("删除失败: " + error.message);
          });
      }
    );
  }

  // 选择图标
  selectIcon() {
    const layerIndex = this.layer.open({
        type: 1,
        title: '选择图标',
        area: ['800px', '600px'],
        content: '<div id="iconList" class="layui-row" style="padding: 20px;"></div>', // 动态生成内容
        btn: ['确定', '取消'],
        yes: (index) => {
            const selectedIcon = this.$('input[name="medal-icon"]').val();
            if (selectedIcon) {
                this.layer.close(index);
            } else {
                this.layer.msg('请先选择一个图标');
            }
        }
    });

    // 发起请求获取图标列表
    fetch('/admin/api/medal_img')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应不正常');
            }
            return response.json();
        })
        .then(result => {
            if (result.code !== 0) {
                throw new Error(result.msg || '获取图标列表失败');
            }
            const icons = result.data;
            const iconList = document.getElementById('iconList');
            iconList.innerHTML = ''; // 清空列表

            icons.forEach(icon => {
                const iconItem = document.createElement('div');
                iconItem.className = 'layui-col-xs4 layui-col-sm3 layui-col-md2';
                iconItem.style.textAlign = 'center';
                iconItem.style.padding = '10px';
                iconItem.innerHTML = `
                    <div class="icon-item" style="border: 1px solid #e6e6e6; padding: 10px; margin-bottom: 10px; cursor: pointer;" onclick="window.selectMedalIcon('${icon}')">
                        <img src="/static/img/medal/${icon}" alt="${icon}" style="width: 100%; max-width: 64px; height: auto;">
                        <p style="margin-top: 5px; font-size: 12px; color: #666;">${icon}</p>
                    </div>
                `;
                iconList.appendChild(iconItem);
            });

            // 添加全局函数用于选择图标
            window.selectMedalIcon = (icon) => {
                this.$('input[name="medal-icon"]').val('/static/img/medal/' + icon);
                this.layer.close(layerIndex);
            };
        })
        .catch(error => {
            console.error("加载图标失败:", error);
            this.layer.msg("加载图标失败: " + error.message);
        });
  }

  // 选择图标的辅助函数
  // selectIcon(icon) {
  //   const inputField = window.parent.document.querySelector('input[name="medal-icon"]');
  //   if (inputField) {
  //       inputField.value = icon; // 设置选中的图标
  //   }
  //   window.parent.layer.closeAll(); // 关闭选择窗口
  // }
}

// 导出模块
export default MedalAdmin; 