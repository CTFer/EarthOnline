/*
 * @Author: 一根鱼骨棒 Email 775639471@qq.com
 * @LastEditTime: 2025-02-25 11:27:32
 * @LastEditors: 一根鱼骨棒
 * @Description: 技能管理模块
 */

class SkillAdmin {
  constructor() {
    this.layer = layui.layer;
    this.$ = layui.jquery;
  }

  // 加载技能列表
  async loadSkills() {
    try {
      const response = await fetch("/admin/api/skills");
      const result = await response.json();

      if (result.code !== 0) {
        throw new Error(result.msg);
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
                        <button class="layui-btn layui-btn-sm edit-skill-btn" data-id="${skill.id}">编辑</button>
                        <button class="layui-btn layui-btn-sm layui-btn-danger delete-skill-btn" data-id="${skill.id}">删除</button>
                    </td>
                </tr>
            `
        )
        .join("");

      // 绑定按钮事件
      this.bindEvents();
    } catch (error) {
      console.error("加载技能失败:", error);
      this.layer.msg("加载技能失败: " + error.message);
    }
  }

  // 绑定事件
  bindEvents() {
    // 编辑按钮事件
    this.$("#skillTable").on("click", ".edit-skill-btn", (e) => {
      const skillId = this.$(e.currentTarget).data("id");
      this.editSkill(skillId);
    });

    // 删除按钮事件
    this.$("#skillTable").on("click", ".delete-skill-btn", (e) => {
      const skillId = this.$(e.currentTarget).data("id");
      this.deleteSkill(skillId);
    });

    // 添加技能按钮事件
    this.$("#addSkillBtn").on("click", () => this.showAddSkillForm());
  }

  // 显示添加技能表单
  showAddSkillForm() {
    this.layer.open({
      type: 1,
      title: "添加技能",
      content: this.$("#skillForm"),
      area: ["500px", "500px"],
      btn: ["确定", "取消"],
      yes: (index) => {
        const formData = {
          name: this.$('input[name="name"]').val(),
          proficiency: parseInt(this.$('input[name="proficiency"]').val()),
          description: this.$('textarea[name="description"]').val(),
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
            if (result.code === 0) {
              this.layer.close(index);
              this.layer.msg(result.msg || "添加成功");
              this.loadSkills();
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

  // 编辑技能
  editSkill(id) {
    fetch(`/admin/api/skills/${id}`)
      .then((response) => response.json())
      .then((result) => {
        console.log("获取技能数据成功:", result);
        if (result.code === 0) {
          const skill = result.data;

          // 清空表单
          this.$("#skillForm form")[0].reset();

          // 填充表单数据
          const form = this.$("#skillForm form");
          form.find('input[name="name"]').val(skill.name);
          form.find('input[name="proficiency"]').val(skill.proficiency);
          form.find('textarea[name="description"]').val(skill.description);

          this.layer.open({
            type: 1,
            title: "编辑技能",
            content: this.$("#skillForm"),
            area: ["500px", "500px"],
            btn: ["确定", "取消"],
            yes: (index) => {
              const formData = {
                name: form.find('input[name="name"]').val(),
                proficiency: parseInt(form.find('input[name="proficiency"]').val()),
                description: form.find('textarea[name="description"]').val(),
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
                  if (result.code === 0) {
                    this.layer.close(index);
                    this.layer.msg(result.msg || "更新成功");
                    this.loadSkills();
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
          this.layer.msg("获取技能数据失败: " + result.msg);
        }
      })
      .catch((error) => {
        this.layer.msg("获取技能数据失败: " + error.message);
      });
  }

  // 删除技能
  deleteSkill(id) {
    this.layer.confirm(
      "确定要删除这个技能吗？",
      {
        btn: ["确定", "取消"],
      },
      () => {
        fetch(`/admin/api/skills/${id}`, {
          method: "DELETE",
        })
          .then((response) => response.json())
          .then((result) => {
            if (result.code === 0) {
              this.layer.msg(result.msg || "删除成功");
              this.loadSkills();
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
}

// 导出模块
export default SkillAdmin; 