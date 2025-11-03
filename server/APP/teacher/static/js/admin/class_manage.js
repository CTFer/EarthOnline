/**
 * 班级管理JavaScript
 */
layui.use(['table', 'form', 'layer', 'laydate'], function(){
    var table = layui.table;
    var form = layui.form;
    var layer = layui.layer;
    var laydate = layui.laydate;
    
    // 初始化表格
    var classTable = table.render({
        elem: '#classTable',
        url: '/teacher/api/classes',
        page: true,
        cols: [[
            {field: 'id', width: 80, title: 'ID'},
            {field: 'name', width: 200, title: '班级名称'},
            {field: 'class_code', width: 150, title: '班级代码'},
            {field: 'description', width: 300, title: '描述'},
            {field: 'student_count', width: 100, title: '学生数'},
            {field: 'create_time', width: 150, title: '创建时间'},
            {field: 'status', width: 80, title: '状态', templet: '#statusTpl'},
            {fixed: 'right', width: 200, align:'center', toolbar: '#barDemo', title: '操作'}
        ]],
        response: {
            statusName: 'success',
            statusCode: true,
            msgName: 'message',
            countName: 'total',
            dataName: 'data'
        }
    });
    
    // 监听工具条
    table.on('tool(classTable)', function(obj){
        var data = obj.data;
        if(obj.event === 'edit'){
            editClass(data);
        } else if(obj.event === 'students'){
            viewStudents(data);
        } else if(obj.event === 'del'){
            deleteClass(data);
        }
    });
    
    // 新增班级
    window.addClass = function(){
        layer.open({
            type: 1,
            title: '新增班级',
            area: ['500px', '400px'],
            content: $('#classForm'),
            success: function(layero, index){
                form.render();
                // 重置表单
                form.val('classForm', {
                    id: '',
                    name: '',
                    description: ''
                });
            }
        });
    };
    
    // 编辑班级
    function editClass(data){
        layer.open({
            type: 1,
            title: '编辑班级',
            area: ['500px', '400px'],
            content: $('#classForm'),
            success: function(layero, index){
                form.render();
                // 填充表单数据
                form.val('classForm', {
                    id: data.id,
                    name: data.name,
                    description: data.description || ''
                });
            }
        });
    };
    
    // 查看班级学生
    function viewStudents(data){
        layer.open({
            type: 2,
            title: '班级学生 - ' + data.name,
            area: ['800px', '600px'],
            content: '/teacher/admin/class/' + data.id + '/students'
        });
    };
    
    // 删除班级
    function deleteClass(data){
        layer.confirm('确定要删除班级"' + data.name + '"吗？', {icon: 3, title: '确认删除'}, function(index){
            fetch('/teacher/api/classes/' + data.id, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(result => {
                if(result.success){
                    layer.msg('删除成功');
                    table.reload('classTable');
                } else {
                    layer.msg(result.message || '删除失败');
                }
            })
            .catch(function(){
                layer.msg('删除失败');
            });
            layer.close(index);
        });
    };
    
    // 监听表单提交
    form.on('submit(submitClass)', function(data){
        var formData = data.field;
        var url = formData.id ? '/teacher/api/classes/' + formData.id : '/teacher/api/classes';
        var method = formData.id ? 'PUT' : 'POST';
        
        fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(result => {
            if(result.success){
                layer.msg(formData.id ? '更新成功' : '创建成功');
                layer.closeAll();
                table.reload('classTable');
            } else {
                layer.msg(result.message || '操作失败');
            }
        })
        .catch(function(){
            layer.msg('操作失败');
        });
        return false;
    });
});
