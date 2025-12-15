// 表单管理模块
class FormManager {
  // 打开任务表单
  openTaskForm(title, data = {}, submitCallback) {
    layer.open({
      type: 1,
      title: title,
      area: ["500px", "480px"],
      content: $("#taskFormTpl").html(),
      success: function (layero) {
        const $form = $(layero).find(".layui-form");

        // 填充表单数据
        $form.find("input[name=name]").val(data.name || "");
        $form.find("textarea[name=description]").val(data.description || "");

        // 渲染颜色选项
        const $colorOptions = $form.find("#colorOptions");
        $colorOptions.empty().addClass("color-options");

        // 添加颜色选择器容器
        const $colorContainer = $(`<div class="color-picker-container"></div>`);
        $colorOptions.append($colorContainer);

        // 渲染颜色选项
        const colors = themeManager.getCurrentThemeColors();
        Object.entries(colors).forEach(([className, color]) => {
          const $colorBox = $(`
                        <div class="color-option ${className} ${data.color === color ? "selected" : ""}" 
                             data-color="${color}"
                             title="${color}">
                            <div class="color-preview"></div>
                            ${data.color === color ? '<i class="layui-icon layui-icon-ok"></i>' : ""}
                        </div>
                    `);

          $colorContainer.append($colorBox);
        });

        // 添加隐藏的颜色输入
        $colorOptions.append(`
                    <input type="hidden" name="color" value="${data.color || "#ffffff"}">
                `);

        // 颜色选择事件
        $colorOptions.on("click", ".color-option", function () {
          const $this = $(this);
          const color = $this.data("color");

          // 更新隐藏输入值
          $form.find("input[name=color]").val(color);

          // 更新选中状态
          $colorOptions.find(".color-option").removeClass("selected").find(".layui-icon").remove();
          $this.addClass("selected").append('<i class="layui-icon layui-icon-ok"></i>');
        });

        // 周期任务配置初始化
        const $isCycleTask = $form.find("input[name=is_cycle_task]");
        const $cycleDurationRow = $form.find(".cycle-duration-row");
        
        // 填充初始数据
        $isCycleTask.prop("checked", data.is_cycle_task === 1);
        $form.find("input[name=cycle_duration]").val(data.cycle_duration || "");
        
        // 控制周期时长输入框的显示/隐藏
        if (data.is_cycle_task === 1) {
          $cycleDurationRow.show();
        } else {
          $cycleDurationRow.hide();
        }
        
        // 监听周期任务开关变化 - 使用layui的form.on事件
        form.on('switch(is_cycle_task)', function(data) {
          if (data.elem.checked) {
            $cycleDurationRow.show();
          } else {
            $cycleDurationRow.hide();
          }
        });

        form.render();
      },
    });

    // 表单提交
    form.on("submit(submitTask)", function (formData) {
      const $form = $(this).closest(".layui-form");
      const isCycleTask = $form.find("input[name=is_cycle_task]").is(":checked");
      formData.field.is_cycle_task = isCycleTask ? 1 : 0;
      
      // 如果不是周期任务，清空周期时长
      if (!isCycleTask) {
        formData.field.cycle_duration = null;
      } else if (formData.field.cycle_duration) {
        // 确保周期时长是数字类型
        formData.field.cycle_duration = parseInt(formData.field.cycle_duration);
      }
      
      submitCallback(formData.field);
      return false;
    });
  }
}
