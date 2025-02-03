layui.use(["table", "form", "layer"], function () {
  var table = layui.table;
  var form = layui.form;
  var layer = layui.layer;

  // 初始化表格
  table.render({
    elem: "#itemTable",
    url: "/api/shop/items",
    cols: [
      [
        { field: "id", title: "ID", width: 80, sort: true },
        { field: "name", title: "商品名称" },
        { field: "description", title: "描述" },
        { field: "price", title: "价格", width: 100, sort: true },
        { field: "stock", title: "库存", width: 100, sort: true },
        {
          field: "is_enabled",
          title: "状态",
          width: 100,
          templet: function (d) {
            return d.is_enabled ? "启用" : "禁用";
          },
        },
        { title: "操作", toolbar: "#itemTableBar", width: 150 },
      ],
    ],
    page: true,
  });

  // 监听工具条
  table.on("tool(itemTable)", function (obj) {
    var data = obj.data;
    if (obj.event === "edit") {
      showItemForm("edit", data);
    } else if (obj.event === "del") {
      layer.confirm("确定删除此商品？", function (index) {
        deleteItem(data.id, obj);
        layer.close(index);
      });
    }
  });

  // 监听表单提交
  form.on("submit(itemForm)", function (data) {
    var formData = data.field;
    var url = "/api/shop/items";
    var method = "POST";

    if (formData.id) {
      url += "/" + formData.id;
      method = "PUT";
    }

    // 处理复选框
    formData.is_enabled = formData.is_enabled === "on";

    fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(formData),
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.code === 0) {
          layer.closeAll("page");
          table.reload("itemTable");
          layer.msg("操作成功");
        } else {
          layer.msg("操作失败：" + result.msg);
        }
      })
      .catch((error) => {
        layer.msg("请求失败：" + error);
      });

    return false;
  });

  // 显示商品表单
  function showItemForm(mode, data) {
    var title = mode === "edit" ? "编辑商品" : "添加商品";

    layer.open({
      type: 1,
      title: title,
      area: ["500px", "600px"],
      content: $("#itemFormTpl").html(),
      success: function (layero, index) {
        var form = layui.form;

        // 编辑模式下填充表单
        if (mode === "edit" && data) {
          layero.find("[name=id]").val(data.id);
          layero.find("[name=name]").val(data.name);
          layero.find("[name=description]").val(data.description);
          layero.find("[name=price]").val(data.price);
          layero.find("[name=stock]").val(data.stock);
          layero.find("[name=image_url]").val(data.image_url);
          layero.find("[name=is_enabled]").prop("checked", data.is_enabled);
        }

        form.render();
      },
    });
  }

  // 删除商品
  function deleteItem(id, obj) {
    fetch("/api/shop/items/" + id, {
      method: "DELETE",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json())
      .then((result) => {
        if (result.code === 0) {
          obj.del();
          layer.msg("删除成功");
        } else {
          layer.msg("删除失败：" + result.msg);
        }
      })
      .catch((error) => {
        layer.msg("请求失败：" + error);
      });
  }
});
