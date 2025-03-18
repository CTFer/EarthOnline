layui.use(['table', 'form', 'layer'], function () {
  var table = layui.table;
  var form = layui.form;
  var layer = layui.layer;

  // 状态映射
  const STATUS_MAP = {
    'IN_PROGRESS': { text: '进行中', color: 'layui-bg-blue' },
    'CHECK': { text: '待审核', color: 'layui-bg-orange' },
    'COMPLETED': { text: '已完成', color: 'layui-bg-green' },
    'REJECT': { text: '已驳回', color: 'layui-bg-red' },
    'ABANDONED': { text: '已放弃', color: 'layui-bg-gray' }
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

  // 生成状态标签HTML
  function generateStatusHtml(status) {
    const statusInfo = STATUS_MAP[status] || { text: status, color: 'layui-bg-gray' };
    return `<span class="layui-badge ${statusInfo.color}">${statusInfo.text}</span>`;
  }

  // 初始化表格
  function initTable(where = {}) {
    table.render({
      elem: "#taskHistoryTable",
      url: "/api/tasks/history",
      where: where,
      page: true,
      cols: [
        [
          { field: "id", title: "ID", width: 80, sort: true },
          { field: "task_name", title: "任务名称", width: 150 },
          { field: "player_name", title: "玩家", width: 120 },
          { field: "task_description", title: "任务描述", width: 200 },
          { 
            field: "status", 
            title: "状态", 
            width: 100, 
            templet: function(d) {
              return generateStatusHtml(d.status);
            }
          },
          { 
            field: "starttime", 
            title: "开始时间", 
            width: 160, 
            sort: true, 
            templet: function(d) {
              return formatDateTime(d.starttime);
            }
          },
          { 
            field: "submit_time", 
            title: "提交时间", 
            width: 160, 
            sort: true, 
            templet: function(d) {
              return formatDateTime(d.submit_time);
            }
          },
          { 
            field: "complete_time", 
            title: "完成时间", 
            width: 160, 
            sort: true, 
            templet: function(d) {
              return formatDateTime(d.complete_time);
            }
          },
          { 
            title: "操作", 
            width: 100, 
            templet: function(d) {
              return `<button class="layui-btn layui-btn-sm" onclick="showTaskDetail(${JSON.stringify(d)})">
                <i class="layui-icon">&#xe63c;</i> 详情
              </button>`;
            }
          },
        ],
      ],
      response: {
        statusCode: 0
      },
      parseData: function (res) {
        return {
          "code": res.code,
          "msg": res.msg,
          "count": res.data.total,
          "data": res.data.tasks
        };
      }
    });
  }

  // 初始化表格
  initTable();

  // 刷新表格
  window.refreshTable = function() {
    table.reload('taskHistoryTable');
  }

  // 显示任务详情
  window.showTaskDetail = function(data) {
    layer.open({
      type: 1,
      title: '任务详情',
      area: ['600px', '800px'],
      content: $('#taskDetailTpl').html(),
      success: function(layero, index) {
        form.val('taskDetailForm', {
          'task_name': data.task_name,
          'description': data.task_description,
          'player_info': `${data.player_name}(ID: ${data.player_id})`,
          'status': STATUS_MAP[data.status]?.text || data.status,
          'starttime': formatDateTime(data.starttime),
          'submit_time': formatDateTime(data.submit_time),
          'complete_time': formatDateTime(data.complete_time),
          'comment': data.comment || '',
          'reject_reason': data.reject_reason || ''
        });
      }
    });
  }

  // 监听搜索表单提交
  form.on('submit(searchSubmit)', function(data) {
    // 移除空值
    Object.keys(data.field).forEach(key => {
      if (!data.field[key]) {
        delete data.field[key];
      }
    });
    
    table.reload('taskHistoryTable', {
      where: data.field,
      page: {
        curr: 1
      }
    });
    return false;
  });
}); 