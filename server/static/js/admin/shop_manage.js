layui.use(["table", "form", "layer", "laydate"], function () {
  var table = layui.table;
  var form = layui.form;
  var layer = layui.layer;
  var laydate = layui.laydate;

  // 商品类型常量
  const PRODUCT_TYPES = {
    GAME_CARD: { name: "游戏卡片", color: "#2196F3" },
    REAL_REWARD: { name: "实物奖励", color: "#4CAF50" }
  };

  // 格式化时间戳
  function formatDateTime(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(/\//g, '-');
  }

  // 初始化表格
  table.render({
    elem: "#itemTable",
    url: "/api/shop/items",
    page: true,
    cols: [
      [
        { field: "id", title: "ID", width: 80, sort: true },
        { field: "name", title: "商品名称", width: 150 },
        { field: "description", title: "商品描述", width: 200 },
        { field: "price", title: "价格", width: 100, sort: true },
        { field: "stock", title: "库存", width: 100, sort: true },
        { field: "product_type", title: "类型", width: 100, sort: true },
        { field: "image_url", title: "图片", width: 150, templet: function (d) {
          return '<img src="' + d.image_url + '" style="max-width:50px;">';
        } },
        { field: "online_time", title: "上架时间", width: 160, sort: true, templet: function(d){
          return formatDateTime(d.online_time);
        }},
        { field: "offline_time", title: "下架时间", width: 160, sort: true, templet: function(d){
          return formatDateTime(d.offline_time);
        }},
        { field: "create_time", title: "创建时间", width: 160, sort: true, templet: function(d){
          return formatDateTime(d.create_time);
        }},
        { title: "操作", width: 150, toolbar: "#itemTableBar", fixed: "right" },
      ],
    ],
    response: {
      statusCode: 0
    },
    parseData: function (res) {
      return {
        "code": res.code,
        "msg": res.msg,
        "count": res.data.length,
        "data": res.data
      };
    }
  });

  // 监听工具条
  table.on("tool(itemTable)", function (obj) {
    var data = obj.data;
    if (obj.event === "del") {
      layer.confirm("确认删除此商品？", function (index) {
        deleteItem(data.id, obj);
        layer.close(index);
      });
    } else if (obj.event === "edit") {
      showItemForm(data);
    }
  });

  // 显示商品表单
  window.showItemForm = function (data = null) {
    var title = data ? '编辑商品' : '添加商品';
    console.log('打开表单:', title, data);
    
    layer.open({
        type: 1,
        title: title,
        area: ['500px', '700px'],
        content: $('#shopForm').html(),
        success: function(layero, index){
            // 初始化日期选择器
            laydate.render({
                elem: '#onlineTime',
                type: 'datetime',
                value: data ? formatDateTime(data.online_time) : new Date().toLocaleString('zh-CN'),
                btns: ['now', 'confirm']
            });
            laydate.render({
                elem: '#offlineTime',
                type: 'datetime',
                value: data ? formatDateTime(data.offline_time) : '',
                btns: ['now', 'confirm']
            });

            // 初始化商品类型选择
            const typeContainer = layero.find('.product-type-container');
            initProductTypes(typeContainer, data);
            
            if(data){
                console.log('填充表单数据:', data);
                // 填充表单数据
                layero.find('[name=name]').val(data.name);
                layero.find('[name=description]').val(data.description);
                layero.find('[name=price]').val(data.price);
                layero.find('[name=stock]').val(data.stock);
                layero.find('[name=image_url]').val(data.image_url);
            }

            // 监听表单提交
            form.on('submit(itemForm)', function(formData) {
                handleItemSubmit(formData.field, data ? 'edit' : 'add', data?.id);
                layer.close(index);
                return false;
            });
            
            form.render();
        }
    });
  };

  // 初始化商品类型选择
  function initProductTypes(container, data = null) {
    let html = '';
    Object.entries(PRODUCT_TYPES).forEach(([value, type]) => {
      html += `
        <input type="radio" name="product_type" value="${type.name}" lay-skin="none">
        <div lay-radio class="lay-skin-taskcard" style="border-color: ${type.color}">
          <div class="lay-skin-taskcard-detail">
            <div class="lay-skin-taskcard-header" style="color: ${type.color}">${type.name}</div>
          </div>
        </div>
      `;
    });

    container.html(html);

    // 绑定点击事件
    container.find('[lay-radio]').on('click', function() {
      const input = $(this).prev('input[type=radio]');
      
      // 移除所有选中样式
      container.find('[lay-radio]').removeClass('selected');
      container.find('input[type=radio]').prop('checked', false);
      
      // 添加选中样式并选中radio
      $(this).addClass('selected');
      input.prop('checked', true);
    });

    // 如果是编辑模式，设置选中状态
    if (data && data.product_type) {
      const targetType = Object.values(PRODUCT_TYPES)
        .find(type => type.name === data.product_type);
      if (targetType) {
        container.find(`input[value="${targetType.name}"]`)
          .prop('checked', true)
          .next('[lay-radio]')
          .addClass('selected');
      }
    } else {
      // 默认选中第一个选项
      container.find('input[type=radio]').first()
        .prop('checked', true)
        .next('[lay-radio]')
        .addClass('selected');
    }
  }

  // 处理表单提交
  function handleItemSubmit(formData, mode, itemId = null) {
    const url = mode === 'add' ? '/api/shop/items' : `/api/shop/items/${itemId}`;
    const method = mode === 'add' ? 'POST' : 'PUT';

    // 处理时间戳
    if (formData.online_time) {
      formData.online_time = Math.floor(new Date(formData.online_time).getTime() / 1000);
    }
    if (formData.offline_time) {
      formData.offline_time = Math.floor(new Date(formData.offline_time).getTime() / 1000);
    }

    fetch(url, {
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify(formData)
    })
    .then(response => response.json())
    .then(result => {
      if (result.code === 0) {
        layer.msg('保存成功');
        table.reload('itemTable');
      } else {
        layer.msg('保存失败：' + result.msg);
      }
    })
    .catch(error => {
      console.error('请求错误:', error);
      layer.msg('保存失败：' + error);
    });
  }

  // 删除商品
  function deleteItem(id, obj) {
    fetch(`/api/shop/items/${id}`, {
      method: "DELETE",
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      }
    })
      .then(response => response.json())
      .then(result => {
        if (result.code === 0) {
          obj.del();
          layer.msg("删除成功");
        } else {
          layer.msg("删除失败：" + result.msg);
        }
      })
      .catch(error => {
        layer.msg("删除失败：" + error);
      });
  }
});
