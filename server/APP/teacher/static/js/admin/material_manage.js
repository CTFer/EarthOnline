/**
 * 材料管理JavaScript
 */
layui.use(['table', 'form', 'layer', 'upload', 'laydate'], function(){
    var table = layui.table;
    var form = layui.form;
    var layer = layui.layer;
    var upload = layui.upload;
    var laydate = layui.laydate;
    
    // 初始化日期选择器
    laydate.render({
        elem: '#deadline',
        type: 'datetime'
    });
    
    laydate.render({
        elem: '#editDeadline',
        type: 'datetime'
    });
    
    // 初始化表格
    var materialTable = table.render({
        elem: '#materialTable',
        url: '/teacher/api/materials',
        page: true,
        cols: [[
            {field: 'id', width: 80, title: 'ID'},
            {field: 'title', width: 200, title: '材料标题'},
            {field: 'type', width: 80, title: '类型', templet: '#typeTpl'},
            {field: 'file_size', width: 100, title: '大小', templet: '#sizeTpl'},
            {field: 'targets', width: 200, title: '分发对象', templet: '#targetTpl'},
            {field: 'completion_rate', width: 100, title: '完成率', templet: '#rateTpl'},
            {field: 'deadline', width: 150, title: '截止时间'},
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
    
    // 加载班级选项
    loadClassOptions();
    
    // 监听工具条
    table.on('tool(materialTable)', function(obj){
        var data = obj.data;
        if(obj.event === 'edit'){
            editMaterial(data);
        } else if(obj.event === 'distribute'){
            distributeMaterial(data);
        } else if(obj.event === 'stats'){
            viewStats(data);
        } else if(obj.event === 'del'){
            deleteMaterial(data);
        }
    });
    
    // 上传材料
    window.uploadMaterial = function(){
        layer.open({
            type: 1,
            title: '上传材料',
            area: ['600px', '600px'],
            content: $('#materialUploadForm'),
            success: function(layero, index){
                form.render();
                // 重置表单
                form.val('materialUploadForm', {
                    title: '',
                    type: '',
                    description: '',
                    deadline: ''
                });
                // 加载分发对象选项
                loadTargetOptions();
            }
        });
    };
    
    // 编辑材料
    function editMaterial(data){
        layer.open({
            type: 1,
            title: '编辑材料',
            area: ['500px', '400px'],
            content: $('#materialEditForm'),
            success: function(layero, index){
                form.render();
                // 填充表单数据
                form.val('materialEditForm', {
                    id: data.id,
                    title: data.title,
                    description: data.description || '',
                    deadline: data.deadline || ''
                });
            }
        });
    };
    
    // 分发材料
    function distributeMaterial(data){
        layer.open({
            type: 1,
            title: '分发材料 - ' + data.title,
            area: ['500px', '400px'],
            content: '<div style="padding: 20px;"><form class="layui-form" lay-filter="distributeForm"><div class="layui-form-item"><label class="layui-form-label">选择分发对象</label><div class="layui-input-block" id="distributeTargets"></div></div><div class="layui-form-item"><div class="layui-input-block"><button class="layui-btn" lay-submit lay-filter="submitDistribute">确定分发</button></div></div></form></div>',
            success: function(layero, index){
                form.render();
                // 加载分发对象选项
                loadDistributeOptions(data.id);
            }
        });
    };
    
    // 查看统计
    function viewStats(data){
        layer.open({
            type: 2,
            title: '材料统计 - ' + data.title,
            area: ['800px', '600px'],
            content: '/teacher/admin/material/' + data.id + '/stats'
        });
    };
    
    // 删除材料
    function deleteMaterial(data){
        layer.confirm('确定要删除材料"' + data.title + '"吗？', {icon: 3, title: '确认删除'}, function(index){
            fetch('/teacher/api/materials/' + data.id, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(result => {
                if(result.success){
                    layer.msg('删除成功');
                    table.reload('materialTable');
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
    
    // 搜索材料
    window.searchMaterials = function(){
        var type = $('select[name="type"]').val();
        var classId = $('select[name="class_id"]').val();
        var keyword = $('input[name="keyword"]').val();
        
        table.reload('materialTable', {
            where: {
                type: type,
                class_id: classId,
                keyword: keyword
            }
        });
    };
    
    // 加载班级选项
    function loadClassOptions(){
        fetch('/teacher/api/classes')
            .then(response => response.json())
            .then(result => {
                if(result.success){
                    var options = '<option value="">选择班级</option>';
                    result.data.forEach(function(item){
                        options += '<option value="' + item.id + '">' + item.name + '</option>';
                    });
                    $('select[name="class_id"]').html(options);
                    form.render('select');
                }
            });
    };
    
    // 加载分发对象选项
    function loadTargetOptions(){
        fetch('/teacher/api/classes')
            .then(response => response.json())
            .then(result => {
                if(result.success){
                    var checkboxes = '<h4>班级：</h4>';
                    result.data.forEach(function(item){
                        checkboxes += '<input type="checkbox" name="targets" value="class_' + item.id + '" title="' + item.name + '">';
                    });
                    $('#targetCheckboxes').html(checkboxes);
                    form.render('checkbox');
                }
            });
    };
    
    // 加载分发选项
    function loadDistributeOptions(materialId){
        fetch('/teacher/api/classes')
            .then(response => response.json())
            .then(result => {
                if(result.success){
                    var checkboxes = '<h4>班级：</h4>';
                    result.data.forEach(function(item){
                        checkboxes += '<input type="checkbox" name="targets" value="class_' + item.id + '" title="' + item.name + '">';
                    });
                    $('#distributeTargets').html(checkboxes);
                    form.render('checkbox');
                }
            });
    };
    
    // 初始化文件上传
    upload.render({
        elem: '#uploadBtn',
        url: '/teacher/api/materials/upload',
        accept: 'file',
        acceptMime: 'video/*,audio/*,.pdf,.doc,.docx',
        done: function(res){
            if(res.success){
                $('#fileInfo').html('<div class="layui-alert layui-alert-success">文件上传成功：' + res.data.filename + '</div>');
                // 设置隐藏字段
                $('input[name="file_path"]').val(res.data.file_path);
                $('input[name="file_name"]').val(res.data.filename);
            } else {
                $('#fileInfo').html('<div class="layui-alert layui-alert-danger">文件上传失败：' + res.message + '</div>');
            }
        },
        error: function(){
            $('#fileInfo').html('<div class="layui-alert layui-alert-danger">文件上传失败</div>');
        }
    });
    
    // 监听表单提交
    form.on('submit(submitMaterial)', function(data){
        var formData = data.field;
        var targets = [];
        $('input[name="targets"]:checked').each(function(){
            targets.push($(this).val());
        });
        
        fetch('/teacher/api/materials', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: formData.title,
                type: formData.type,
                description: formData.description,
                deadline: formData.deadline,
                file_path: formData.file_path,
                file_name: formData.file_name,
                targets: targets
            })
        })
        .then(response => response.json())
        .then(result => {
            if(result.success){
                layer.msg('材料创建成功');
                layer.closeAll();
                table.reload('materialTable');
            } else {
                layer.msg(result.message || '创建失败');
            }
        })
        .catch(function(){
            layer.msg('创建失败');
        });
        return false;
    });
    
    // 监听编辑表单提交
    form.on('submit(submitEdit)', function(data){
        var formData = data.field;
        
        fetch('/teacher/api/materials/' + formData.id, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        })
        .then(response => response.json())
        .then(result => {
            if(result.success){
                layer.msg('更新成功');
                layer.closeAll();
                table.reload('materialTable');
            } else {
                layer.msg(result.message || '更新失败');
            }
        })
        .catch(function(){
            layer.msg('更新失败');
        });
        return false;
    });
    
    // 监听分发表单提交
    form.on('submit(submitDistribute)', function(data){
        var targets = [];
        $('input[name="targets"]:checked').each(function(){
            targets.push($(this).val());
        });
        
        fetch('/teacher/api/materials/distribute', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({targets: targets})
        })
        .then(response => response.json())
        .then(result => {
            if(result.success){
                layer.msg('分发成功');
                layer.closeAll();
                table.reload('materialTable');
            } else {
                layer.msg(result.message || '分发失败');
            }
        })
        .catch(function(){
            layer.msg('分发失败');
        });
        return false;
    });
});
