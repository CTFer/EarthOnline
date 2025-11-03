/**
 * 活动展示JavaScript
 */
layui.use(['layer', 'form'], function(){
    var layer = layui.layer;
    var form = layui.form;
    
    // 页面加载时获取活动列表
    $(document).ready(function(){
        loadActivities();
    });
    
    // 加载活动列表
    function loadActivities(){
        $.ajax({
            url: '/teacher/api/public/activities',
            type: 'GET',
            success: function(result){
                if(result.success){
                    renderActivities(result.data);
                } else {
                    $('#activitiesList').html('<div class="layui-empty">暂无活动数据</div>');
                }
            },
            error: function(){
                $('#activitiesList').html('<div class="layui-empty">加载失败</div>');
            }
        });
    };
    
    // 渲染活动列表
    function renderActivities(activities){
        var html = '';
        activities.forEach(function(activity){
            var statusClass = getActivityStatusClass(activity);
            var statusText = getActivityStatusText(activity);
            
            html += '<div class="layui-col-md6">';
            html += '<div class="layui-card">';
            html += '<div class="layui-card-header">';
            html += '<h3>' + activity.title + '</h3>';
            html += '<span class="layui-badge ' + statusClass + '">' + statusText + '</span>';
            html += '</div>';
            html += '<div class="layui-card-body">';
            html += '<p><strong>活动时间：</strong>' + formatDateTime(activity.start_time) + ' - ' + formatDateTime(activity.end_time) + '</p>';
            html += '<p><strong>活动地点：</strong>' + activity.location + '</p>';
            html += '<p><strong>活动类型：</strong>' + getActivityTypeText(activity.location_type) + '</p>';
            if(activity.description){
                html += '<p>' + activity.description.substring(0, 100) + (activity.description.length > 100 ? '...' : '') + '</p>';
            }
            html += '<div style="margin-top: 15px;">';
            html += '<button class="layui-btn layui-btn-sm" onclick="viewActivityDetail(' + activity.id + ')">查看详情</button>';
            if(activity.registration_required){
                html += '<button class="layui-btn layui-btn-sm layui-btn-normal" onclick="registerActivity(' + activity.id + ')">立即报名</button>';
            }
            html += '</div>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
        });
        
        $('#activitiesList').html(html);
    };
    
    // 查看活动详情
    window.viewActivityDetail = function(activityId){
        $.ajax({
            url: '/teacher/api/public/activities/' + activityId,
            type: 'GET',
            success: function(result){
                if(result.success){
                    var activity = result.data;
                    $('#activityTitle').text(activity.title);
                    $('#activityTime').text(formatDateTime(activity.start_time) + ' - ' + formatDateTime(activity.end_time));
                    $('#activityLocation').text(activity.location);
                    $('#activityType').text(getActivityTypeText(activity.location_type));
                    $('#activityParticipants').text(activity.current_participants + '/' + (activity.max_participants || '不限'));
                    $('#activityRegistration').text(activity.registration_required ? '是' : '否');
                    $('#activityDescription').html(activity.description || '暂无描述');
                    
                    // 显示报名按钮
                    if(activity.registration_required){
                        $('#registerBtn').show().attr('onclick', 'registerActivity(' + activityId + ')');
                    } else {
                        $('#registerBtn').hide();
                    }
                    
                    layer.open({
                        type: 1,
                        title: '活动详情',
                        area: ['800px', '600px'],
                        content: $('#activityDetail')
                    });
                } else {
                    layer.msg(result.message || '获取活动详情失败');
                }
            },
            error: function(){
                layer.msg('获取活动详情失败');
            }
        });
    };
    
    // 报名活动
    window.registerActivity = function(activityId){
        layer.open({
            type: 1,
            title: '活动报名',
            area: ['500px', '400px'],
            content: $('#registrationForm'),
            success: function(layero, index){
                form.render();
                // 设置活动ID
                $('input[name="activity_id"]').val(activityId);
            }
        });
    };
    
    // 监听报名表单提交
    form.on('submit(submitRegistration)', function(data){
        var formData = data.field;
        
        $.ajax({
            url: '/teacher/api/public/activities/register',
            type: 'POST',
            data: formData,
            success: function(result){
                if(result.success){
                    layer.msg('报名成功');
                    layer.closeAll();
                } else {
                    layer.msg(result.message || '报名失败');
                }
            },
            error: function(){
                layer.msg('报名失败');
            }
        });
        return false;
    });
    
    // 获取活动状态样式类
    function getActivityStatusClass(activity){
        var now = new Date();
        var startTime = new Date(activity.start_time);
        var endTime = new Date(activity.end_time);
        
        if(now < startTime){
            return 'layui-bg-blue'; // 未开始
        } else if(now >= startTime && now <= endTime){
            return 'layui-bg-green'; // 进行中
        } else {
            return 'layui-bg-gray'; // 已结束
        }
    };
    
    // 获取活动状态文本
    function getActivityStatusText(activity){
        var now = new Date();
        var startTime = new Date(activity.start_time);
        var endTime = new Date(activity.end_time);
        
        if(now < startTime){
            return '未开始';
        } else if(now >= startTime && now <= endTime){
            return '进行中';
        } else {
            return '已结束';
        }
    };
    
    // 获取活动类型文本
    function getActivityTypeText(locationType){
        var typeMap = {
            'online': '线上活动',
            'offline': '线下活动'
        };
        return typeMap[locationType] || '未知';
    };
    
    // 格式化日期时间
    function formatDateTime(dateTimeStr){
        var date = new Date(dateTimeStr);
        return date.getFullYear() + '-' + 
               String(date.getMonth() + 1).padStart(2, '0') + '-' + 
               String(date.getDate()).padStart(2, '0') + ' ' + 
               String(date.getHours()).padStart(2, '0') + ':' + 
               String(date.getMinutes()).padStart(2, '0');
    };
});
