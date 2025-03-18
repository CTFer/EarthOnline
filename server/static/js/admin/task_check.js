layui.use(['table', 'form', 'layer'], function () {
  var table = layui.table;
  var form = layui.form;
  var layer = layui.layer;

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

  // 生成操作按钮HTML
  function generateOperationHtml(data) {
    return `
      <div class="layui-btn-group">
        <button class="layui-btn layui-btn-sm layui-btn-normal" onclick="approveTask(${data.id})">
          <i class="layui-icon">&#xe605;</i> 通过
        </button>
        <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="showRejectForm(${JSON.stringify(data)})">
          <i class="layui-icon">&#x1006;</i> 驳回
        </button>
        <button class="layui-btn layui-btn-sm" onclick="showTaskDetail(${JSON.stringify(data)})">
          <i class="layui-icon">&#xe63c;</i> 详情
        </button>
      </div>
    `;
  }

  // 初始化表格
  function initTable() {
    table.render({
      elem: "#taskCheckTable",
      url: "/api/tasks/check",
      page: true,
      cols: [
        [
          { field: "id", title: "ID", width: 80, sort: true },
          { field: "task_name", title: "任务名称", width: 150 },
          { field: "player_name", title: "玩家", width: 120 },
          { field: "task_description", title: "任务描述", width: 200 },
          { field: "comment", title: "提交说明", width: 200 },
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
            title: "操作", 
            width: 250, 
            templet: function(d) {
              return generateOperationHtml(d);
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
    table.reload('taskCheckTable');
  }

  // 显示任务详情
  window.showTaskDetail = function(data) {
    layer.open({
      type: 1,
      title: '任务详情',
      area: ['600px', '500px'],
      content: $('#taskDetailTpl').html(),
      success: function(layero, index) {
        form.val('taskDetailForm', {
          'task_name': data.task_name,
          'description': data.task_description,
          'comment': data.comment,
          'submit_time': formatDateTime(data.submit_time),
          'player_info': `${data.player_name}(ID: ${data.player_id})`
        });
      }
    });
  }

  // 显示驳回表单
  window.showRejectForm = function(data) {
    layer.open({
      type: 1,
      title: '驳回任务',
      area: ['500px', '400px'],
      content: $('#rejectFormTpl').html(),
      success: function() {
        form.on('submit(rejectSubmit)', function(formData) {
          rejectTask(data.id, formData.field.reject_reason);
          return false;
        });
      }
    });
  }

  // 通过任务
  window.approveTask = function(taskId) {
    layer.confirm('确认通过该任务？', function(index) {
      fetch(`/api/tasks/${taskId}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.json())
      .then(result => {
        if (result.code === 0) {
          layer.msg('任务已通过');
          table.reload('taskCheckTable');
        } else {
          layer.msg('操作失败：' + result.msg);
        }
      })
      .catch(error => {
        console.error('请求错误:', error);
        layer.msg('操作失败：' + error);
      });
      layer.close(index);
    });
  }

  // 驳回任务
  window.rejectTask = function(taskId, rejectReason) {
    fetch(`/api/tasks/${taskId}/reject`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
      },
      body: JSON.stringify({
        reject_reason: rejectReason
      })
    })
    .then(response => response.json())
    .then(result => {
      if (result.code === 0) {
        layer.msg('任务已驳回');
        layer.closeAll('page');
        table.reload('taskCheckTable');
      } else {
        layer.msg('操作失败：' + result.msg);
      }
    })
    .catch(error => {
      console.error('请求错误:', error);
      layer.msg('操作失败：' + error);
    });
  }
});