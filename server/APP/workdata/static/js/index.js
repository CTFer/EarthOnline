// 确保在DOM加载完成后初始化

layui.use(["table", "form", "layer", "jquery"], function () {
  // 重命名变量以避免冲突
  var layTable = layui.table;
  var form = layui.form;
  var layer = layui.layer;
  var $ = layui.jquery;

  console.log("Layui模块加载成功:", { table: layTable, form: form, layer: layer, jquery: $ });

  // 当前选中的数据库和表格
  var currentDb = "";
  var currentTable = "";

  // 初始化数据库列表
  function initDatabases() {
    $.ajax({
      url: "/workdata/api/databases",
      type: "GET",
      success: function (data) {
        if (data.code === 0) {
          var dbSelect = $("#db-select");
          dbSelect.empty();
          dbSelect.append('<option value="">请选择数据库</option>');

          data.data.forEach(function (db) {
            dbSelect.append('<option value="' + db + '">' + db + "</option>");
          });

          form.render("select");
        } else {
          layer.msg("加载数据库列表失败: " + data.msg, { icon: 5 });
        }
      },
      error: function () {
        layer.msg("请求失败，请稍后重试", { icon: 5 });
      },
    });
  }

  // 显示加载遮罩 - 添加延迟显示机制
  var loadingTimer = null;
  function showLoading(text) {
    // 清除之前的计时器
    if (loadingTimer) clearTimeout(loadingTimer);
    
    // 延迟300ms显示遮罩，避免快速操作时的闪烁
    loadingTimer = setTimeout(function() {
      $("#loading-text").text(text || "加载中...");
      $("#loading-mask").show();
    }, 300);
  }

  // 隐藏加载遮罩
  function hideLoading() {
    // 清除计时器
    if (loadingTimer) {
      clearTimeout(loadingTimer);
      loadingTimer = null;
    }
    $("#loading-mask").hide();
  }

  // 更新状态栏信息
  function updateStatusBar(db, table, count) {
    $("#current-path").text("当前路径: " + (db ? db + "/" + table : "未选择"));
    $("#data-count").text("数据统计: " + (count || 0) + " 条");
    $("#last-update").text("最后更新: " + new Date().toLocaleString());
  }

  // 初始化表格列表
  function initTables(db) {
    showLoading("加载表格列表...");
    $.ajax({
      url: "/workdata/api/tables",
      type: "GET",
      data: { db: db },
      success: function (data) {
        if (data.code === 0) {
          var tableSelect = $("#table-select");
          tableSelect.empty();

          if (data.data.length > 0) {
            data.data.forEach(function (table) {
              tableSelect.append('<option value="' + table + '">' + table + "</option>");
            });
          } else {
            tableSelect.append('<option value="">该数据库中没有表格</option>');
          }

          form.render("select");
        } else {
          layer.msg("加载表格列表失败: " + data.msg, { icon: 5 });
        }
      },
      error: function () {
        layer.msg("请求失败，请稍后重试", { icon: 5 });
      },
      complete: function () {
        hideLoading();
      },
    });
  }

  // 加载表格数据
  function loadTableData(db, table) {
    if (!db || !table) {
      layer.msg("请选择数据库和表格", { icon: 5 });
      return;
    }

    currentDb = db;
    currentTable = table;
    $("#table-title").text(db + " - " + table);

    // 先获取表格结构
    showLoading("加载表格结构...");
    $.ajax({
      url: "/workdata/api/table_structure",
      type: "GET",
      data: {
        db: db,
        table: table,
      },
      success: function (structData) {
        if (structData.code === 0) {
          // 根据表格结构生成列定义
          var cols = [];
          var hasIdField = false;

          structData.data.forEach(function (field) {
            if (field.name === "id") {
              hasIdField = true;
              cols.push({ field: field.name, title: field.name, width: 80, fixed: "left", sort: true });
            } else {
              // 动态计算列宽，对于文本类型的字段给更大的宽度
              var width = field.type.includes("TEXT") || field.type.includes("VARCHAR") ? 180 : 120;
              cols.push({
                field: field.name,
                title: field.name,
                width: width,
                sort: true,
                // 处理特殊数据类型的显示
                templet: function (d) {
                  var value = d[field.name];
                  // 如果是null或undefined，显示为'-'
                  if (value === null || value === undefined) {
                    return '<span class="layui-badge layui-bg-gray">-</span>';
                  }
                  // 如果是长文本，截断显示
                  if (typeof value === "string" && value.length > 50) {
                    return value.substring(0, 50) + "...";
                  }
                  return value;
                },
              });
            }
          });

          // 如果没有id字段，添加一个默认的索引列
          if (!hasIdField) {
            cols.unshift({ type: "numbers", title: "序号", width: 80, fixed: "left" });
          }

          // 添加操作列
          cols.push({
            fixed: "right",
            title: "操作",
            width: 150,
            align: "center",
            toolbar: "#action-col",
          });

          // 更新状态栏信息
          updateStatusBar(db, table, 0);

          // 动态加载表格数据
          showLoading("加载表格数据...");
          layTable.render({
            elem: "#data-table",
            url: "/workdata/api/table_data",
            where: {
              db: db,
              table: table,
            },
            page: true,
            limit: 20,
            limits: [10, 20, 50, 100],
            cellMinWidth: 80,
            toolbar: false,
            defaultToolbar: ["filter"],
            id: "dataTableId",
            cols: [cols],
            // 表格渲染完成后的回调
            done: function (res, curr, count) {
              hideLoading();
              // 更新状态栏数据统计
              updateStatusBar(db, table, res.count);

              // 为长文本单元格添加tooltip
              $(".layui-table-main td").each(function () {
                var text = $(this).text();
                if (text.length > 50) {
                  $(this).attr("title", text);
                  $(this).css("cursor", "pointer");
                }
              });
            },
            // 请求异常处理
            error: function () {
              hideLoading();
              layer.msg("表格数据加载失败", { icon: 5 });
            },
          });
        } else {
          hideLoading();
          layer.msg("获取表格结构失败: " + structData.msg, { icon: 5 });
        }
      },
      error: function () {
        hideLoading();
        layer.msg("获取表格结构失败", { icon: 5 });
      },
    });
  }

  // 数据库选择事件
  form.on("select(db-select)", function (data) {
    var db = data.value;
    if (db) {
      initTables(db);
    } else {
      $("#table-select").empty().append('<option value="">请先选择数据库</option>');
      form.render("select");
      // 清空状态栏
      updateStatusBar("", "", 0);
    }
  });

  // 表格选择事件
  form.on("select(table-select)", function (data) {
    var table = data.value;
    if (table && currentDb) {
      // 自动加载表格数据
      loadTableData(currentDb, table);
    }
  });

  // 加载数据按钮点击事件
  $("#load-data-btn").on("click", function () {
    var db = $("#db-select").val();
    var table = $("#table-select").val();
    loadTableData(db, table);
  });

  // 刷新表格按钮点击事件
  $("#refresh-table-btn").on("click", function () {
    if (currentDb && currentTable) {
      showLoading("刷新数据...");
      layTable.reload("dataTableId", {
        done: function () {
          hideLoading();
        },
      });
    }
  });

  // 搜索按钮点击事件
  $("#search-btn").on("click", function () {
    var keyword = $("#search-input").val();
    if (currentDb && currentTable) {
      showLoading("搜索中...");
      layTable.reload("dataTableId", {
        where: {
          db: currentDb,
          table: currentTable,
          keyword: keyword,
        },
        page: { curr: 1 },
        done: function () {
          hideLoading();
        },
      });
    }
  });

  // 重置搜索按钮点击事件
  $("#reset-search-btn").on("click", function () {
    $("#search-input").val("");
    if (currentDb && currentTable) {
      showLoading("重置搜索...");
      layTable.reload("dataTableId", {
        where: {
          db: currentDb,
          table: currentTable,
        },
        page: { curr: 1 },
        done: function () {
          hideLoading();
        },
      });
    }
  });

  // 导出数据按钮点击事件
  $("#export-data-btn").on("click", function () {
    if (!currentDb || !currentTable) {
      layer.msg("请先选择数据库和表格", { icon: 5 });
      return;
    }

    // 在新窗口中打开导出API，直接触发文件下载
    const exportUrl = `/workdata/api/export_data?db=${encodeURIComponent(currentDb)}&table=${encodeURIComponent(currentTable)}&format=excel`;
    window.open(exportUrl, '_blank');
  });

  // 构建表单内容
  function buildFormFields(structData, existingData) {
    var formHtml = "";

    structData.data.forEach(function (field) {
      // 跳过id字段（自动生成）
      if (field.name === "id" && !existingData) return;

      formHtml += '<div class="layui-form-item">';
      formHtml += '<label class="layui-form-label">' + field.name + "</label>";
      formHtml += '<div class="layui-input-block">';

      // 根据字段类型生成不同的输入控件
      var value = existingData ? existingData[field.name] : "";

      if (field.type.includes("TEXT")) {
        // 长文本使用textarea
        formHtml += '<textarea name="' + field.name + '" class="layui-textarea" placeholder="请输入' + field.name + '">' + (value || "") + "</textarea>";
      } else if (field.type.includes("INT") || field.type.includes("REAL")) {
        // 数字类型
        formHtml += '<input type="number" name="' + field.name + '" value="' + (value || "") + '" placeholder="请输入数字" class="layui-input">';
      } else {
        // 默认使用普通文本输入
        formHtml += '<input type="text" name="' + field.name + '" value="' + (value || "") + '" placeholder="请输入' + field.name + '" class="layui-input">';
      }

      formHtml += "</div>";
      formHtml += "</div>";
    });

    return formHtml;
  }

  // 添加数据按钮点击事件
  $("#add-data-btn").on("click", function () {
    if (!currentDb || !currentTable) {
      layer.msg("请先选择数据库和表格", { icon: 5 });
      return;
    }

    showLoading("获取表格结构...");
    // 获取表格结构来生成表单
    $.ajax({
      url: "/workdata/api/table_structure",
      type: "GET",
      data: {
        db: currentDb,
        table: currentTable,
      },
      success: function (structData) {
        hideLoading();
        if (structData.code === 0) {
          var formHtml = buildFormFields(structData, null);

          layer.open({
            type: 1,
            title: "添加数据",
            area: ["600px", "auto"],
            content: '<div class="layui-form" style="padding: 20px;">' + formHtml + "</div>",
            btn: ["确定", "取消"],
            btn1: function (index, layero) {
              var formData = {};
              layero.find("input, textarea").each(function () {
                var name = $(this).attr("name");
                var value = $(this).val();
                // 转换数字类型
                if ($(this).attr("type") === "number" && value !== "") {
                  value = parseFloat(value);
                }
                formData[name] = value === "" ? null : value;
              });

              showLoading("保存数据中...");
              $.ajax({
                url: "/workdata/api/insert",
                type: "POST",
                contentType: "application/json",
                data: JSON.stringify({
                  db: currentDb,
                  table: currentTable,
                  data: formData,
                }),
                success: function (data) {
                  hideLoading();
                  if (data.code === 0) {
                    layer.msg("添加成功", { icon: 6 });
                    layer.close(index);
                    // 刷新表格
                    layTable.reload("dataTableId");
                  } else {
                    layer.msg("添加失败: " + data.msg, { icon: 5 });
                  }
                },
                error: function () {
                  hideLoading();
                  layer.msg("保存请求失败", { icon: 5 });
                },
              });
              return false; // 阻止关闭弹窗
            },
          });

          // 重新渲染表单
          form.render();
        } else {
          layer.msg("获取表格结构失败: " + structData.msg, { icon: 5 });
        }
      },
      error: function () {
        hideLoading();
        layer.msg("获取表格结构失败", { icon: 5 });
      },
    });
  });

  // 表格行工具事件
  layTable.on("tool(data-table)", function (obj) {
    var data = obj.data;

    if (obj.event === "edit") {
      // 编辑数据
      showLoading("获取表格结构...");
      $.ajax({
        url: "/workdata/api/table_structure",
        type: "GET",
        data: {
          db: currentDb,
          table: currentTable,
        },
        success: function (structData) {
          hideLoading();
          if (structData.code === 0) {
            var formHtml = buildFormFields(structData, data);

            layer.open({
              type: 1,
              title: "编辑数据",
              area: ["600px", "auto"],
              content: '<div class="layui-form" style="padding: 20px;">' + formHtml + "</div>",
              btn: ["确定", "取消"],
              btn1: function (index, layero) {
                var formData = {};
                layero.find("input, textarea").each(function () {
                  var name = $(this).attr("name");
                  var value = $(this).val();
                  // 转换数字类型
                  if ($(this).attr("type") === "number" && value !== "") {
                    value = parseFloat(value);
                  }
                  formData[name] = value === "" ? null : value;
                });

                // 确保包含id
                formData.id = data.id;

                showLoading("更新数据中...");
                $.ajax({
                  url: "/workdata/api/update",
                  type: "POST",
                  contentType: "application/json",
                  data: JSON.stringify({
                    db: currentDb,
                    table: currentTable,
                    data: formData,
                  }),
                  success: function (updateData) {
                    hideLoading();
                    if (updateData.code === 0) {
                      layer.msg("更新成功", { icon: 6 });
                      layer.close(index);
                      // 刷新表格
                      layTable.reload("dataTableId");
                    } else {
                      layer.msg("更新失败: " + updateData.msg, { icon: 5 });
                    }
                  },
                  error: function () {
                    hideLoading();
                    layer.msg("更新请求失败", { icon: 5 });
                  },
                });
                return false; // 阻止关闭弹窗
              },
            });

            // 重新渲染表单
            form.render();
          } else {
            layer.msg("获取表格结构失败: " + structData.msg, { icon: 5 });
          }
        },
        error: function () {
          hideLoading();
          layer.msg("获取表格结构失败", { icon: 5 });
        },
      });
    } else if (obj.event === "delete") {
      // 删除数据
      layer.confirm(
        "确定要删除这条数据吗？",
        {
          btn: ["确定", "取消"],
        },
        function () {
          showLoading("删除数据中...");
          $.ajax({
            url: "/workdata/api/delete",
            type: "POST",
            contentType: "application/json",
            data: JSON.stringify({
              db: currentDb,
              table: currentTable,
              id: data.id,
            }),
            success: function (deleteData) {
              hideLoading();
              if (deleteData.code === 0) {
                layer.msg("删除成功", { icon: 6 });
                // 刷新表格
                layTable.reload("dataTableId");
              } else {
                layer.msg("删除失败: " + deleteData.msg, { icon: 5 });
              }
            },
            error: function () {
              hideLoading();
              layer.msg("删除请求失败", { icon: 5 });
            },
          });
        }
      );
    }
  });

  // 添加回车键搜索支持
  $("#search-input").on("keypress", function (e) {
    if (e.which === 13) {
      // Enter键
      $("#search-btn").click();
    }
  });

  // 定期检查登录状态
  function checkLoginStatus() {
    $.ajax({
      url: "/workdata/api/check_login",
      type: "GET",
      success: function (data) {
        if (data.code !== 0) {
          // 未登录，跳转到登录页
          window.location.href = "/workdata/login";
        }
      },
      error: function () {
        // 请求失败，可能是网络问题，不做处理
      },
    });
  }

  // 每分钟检查一次登录状态
  setInterval(checkLoginStatus, 60000);

  // 初始化页面
  initDatabases();
});
