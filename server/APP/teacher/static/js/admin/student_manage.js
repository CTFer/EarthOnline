/**
 * 学生管理JavaScript
 */
layui.use(['table', 'form', 'layer', 'upload'], function(){
    var table = layui.table;
    var form = layui.form;
    var layer = layui.layer;
    var upload = layui.upload;
    
    // 初始化表格
    var studentTable = table.render({
        elem: '#studentTable',
        url: '/teacher/api/students',
        page: true,
        cols: [[
            {field: 'id', width: 80, title: 'ID'},
            {field: 'name', width: 120, title: '学生姓名'},
            {field: 'student_no', width: 120, title: '学号'},
            {field: 'phone', width: 120, title: '联系电话'},
            {field: 'parent_name', width: 120, title: '家长姓名'},
            {field: 'parent_phone', width: 120, title: '家长电话'},
            {field: 'classes', width: 200, title: '所属班级', templet: '#classTpl'},
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
    table.on('tool(studentTable)', function(obj){
        var data = obj.data;
        if(obj.event === 'edit'){
            editStudent(data);
        } else if(obj.event === 'classes'){
            manageStudentClasses(data);
        } else if(obj.event === 'del'){
            deleteStudent(data);
        }
    });
    
    // 新增学生
    window.addStudent = function(){
        layer.open({
            type: 1,
            title: '新增学生',
            area: ['500px', '500px'],
            content: $('#studentForm'),
            success: function(layero, index){
                form.render();
                // 重置表单
                form.val('studentForm', {
                    id: '',
                    name: '',
                    student_no: '',
                    phone: '',
                    parent_name: '',
                    parent_phone: '',
                    notes: ''
                });
            }
        });
    };
    
    // 编辑学生
    function editStudent(data){
        layer.open({
            type: 1,
            title: '编辑学生',
            area: ['500px', '500px'],
            content: $('#studentForm'),
            success: function(layero, index){
                form.render();
                // 填充表单数据
                form.val('studentForm', {
                    id: data.id,
                    name: data.name,
                    student_no: data.student_no || '',
                    phone: data.phone || '',
                    parent_name: data.parent_name || '',
                    parent_phone: data.parent_phone || '',
                    notes: data.notes || ''
                });
            }
        });
    };
    
    // 管理学生班级
    function manageStudentClasses(data){
        layer.open({
            type: 1,
            title: '管理学生班级 - ' + data.name,
            area: ['500px', '400px'],
            content: $('#studentClassForm'),
            success: function(layero, index){
                form.render();
                // 设置学生ID
                form.val('studentClassForm', {
                    student_id: data.id
                });
                // 加载班级选项
                loadClassCheckboxes(data.id);
            }
        });
    };
    
    // 删除学生
    function deleteStudent(data){
        layer.confirm('确定要删除学生"' + data.name + '"吗？', {icon: 3, title: '确认删除'}, function(index){
            fetch('/teacher/api/students/' + data.id, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(result => {
                if(result.success){
                    layer.msg('删除成功');
                    table.reload('studentTable');
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
    
    // 批量导入学生
    window.importStudents = function(){
        layer.open({
            type: 1,
            title: '批量导入学生',
            area: ['600px', '500px'],
            content: $('#studentImportForm'),
            success: function(layero, index){
                form.render();
                // 初始化上传组件
                upload.render({
                    elem: '#uploadBtn',
                    url: '/teacher/api/students/import',
                    accept: 'file',
                    acceptMime: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    done: function(res){
                        if(res.success){
                            $('#fileInfo').html('<div class="layui-alert layui-alert-success">文件上传成功：' + res.data.filename + '</div>');
                        } else {
                            $('#fileInfo').html('<div class="layui-alert layui-alert-danger">文件上传失败：' + res.message + '</div>');
                        }
                    },
                    error: function(){
                        $('#fileInfo').html('<div class="layui-alert layui-alert-danger">文件上传失败</div>');
                    }
                });
            }
        });
    };
    
    // 下载模板
    window.downloadTemplate = function(){
        window.open('/teacher/api/students/template');
    };
    
    // 搜索学生
    window.searchStudents = function(){
        var classId = $('select[name="class_id"]').val();
        var keyword = $('input[name="keyword"]').val();
        
        table.reload('studentTable', {
            where: {
                class_id: classId,
                keyword: keyword
            }
        });
    };
    
    // 加载班级选项
    function loadClassOptions(){
        // 使用fetch替代jQuery
        fetch('/teacher/api/classes')
            .then(response => response.json())
            .then(result => {
                if(result.code === 0){
                    var options = '<option value="">选择班级</option>';
                    result.data.forEach(function(item){
                        options += '<option value="' + item.id + '">' + item.name + '</option>';
                    });
                    $('select[name="class_id"]').html(options);
                    form.render('select');
                }
            });
    };
    
    // 加载班级复选框
    function loadClassCheckboxes(studentId){
        fetch('/teacher/api/classes')
            .then(response => response.json())
            .then(result => {
                if(result.code === 0){
                    var checkboxes = '';
                    result.data.forEach(function(item){
                        checkboxes += '<input type="checkbox" name="class_ids" value="' + item.id + '" title="' + item.name + '">';
                    });
                    $('#classCheckboxes').html(checkboxes);
                    form.render('checkbox');
                }
            });
    };
    
    // 监听表单提交
    form.on('submit(submitStudent)', function(data){
        var formData = data.field;
        var url = formData.id ? '/teacher/api/students/' + formData.id : '/teacher/api/students';
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
                table.reload('studentTable');
            } else {
                layer.msg(result.message || '操作失败');
            }
        })
        .catch(function(){
            layer.msg('操作失败');
        });
        return false;
    });
    
    // 监听学生班级表单提交
    form.on('submit(submitStudentClass)', function(data){
        var formData = data.field;
        var classIds = [];
        $('input[name="class_ids"]:checked').each(function(){
            classIds.push($(this).val());
        });
        
        fetch('/teacher/api/students/' + formData.student_id + '/classes', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({class_ids: classIds})
        })
        .then(response => response.json())
        .then(result => {
            if(result.success){
                layer.msg('更新成功');
                layer.closeAll();
                table.reload('studentTable');
            } else {
                layer.msg(result.message || '操作失败');
            }
        })
        .catch(function(){
            layer.msg('操作失败');
        });
        return false;
    });
    
    // 监听导入表单提交
    form.on('submit(submitImport)', function(data){
        // 这里可以添加导入逻辑
        layer.msg('导入功能开发中...');
        return false;
    });
});
