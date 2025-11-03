/**
 * 课程展示JavaScript
 */
layui.use(['layer', 'form'], function(){
    var layer = layui.layer;
    var form = layui.form;
    
    // 页面加载时获取课程列表
    $(document).ready(function(){
        loadCourses();
    });
    
    // 加载课程列表
    function loadCourses(){
        $.ajax({
            url: '/teacher/api/public/courses',
            type: 'GET',
            success: function(result){
                if(result.success){
                    renderCourses(result.data);
                } else {
                    $('#coursesList').html('<div class="layui-empty">暂无课程数据</div>');
                }
            },
            error: function(){
                $('#coursesList').html('<div class="layui-empty">加载失败</div>');
            }
        });
    };
    
    // 渲染课程列表
    function renderCourses(courses){
        var html = '';
        courses.forEach(function(course){
            html += '<div class="layui-col-md6">';
            html += '<div class="layui-card">';
            html += '<div class="layui-card-header">';
            html += '<h3>' + course.name + '</h3>';
            html += '<span class="layui-badge layui-bg-blue">' + getCourseTypeText(course.is_online) + '</span>';
            html += '</div>';
            html += '<div class="layui-card-body">';
            html += '<p><strong>适合年龄段：</strong>' + getAgeGroupText(course.target_age) + '</p>';
            html += '<p><strong>难度等级：</strong>' + getDifficultyText(course.difficulty) + '</p>';
            html += '<p><strong>课时数：</strong>' + course.duration + '课时</p>';
            if(course.price){
                html += '<p><strong>收费标准：</strong>¥' + course.price + '</p>';
            }
            if(course.description){
                html += '<p>' + course.description.substring(0, 100) + (course.description.length > 100 ? '...' : '') + '</p>';
            }
            html += '<div style="margin-top: 15px;">';
            html += '<button class="layui-btn layui-btn-sm" onclick="viewCourseDetail(' + course.id + ')">查看详情</button>';
            html += '<button class="layui-btn layui-btn-sm layui-btn-normal" onclick="contactCourse(' + course.id + ')">联系咨询</button>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
        });
        
        $('#coursesList').html(html);
    };
    
    // 查看课程详情
    window.viewCourseDetail = function(courseId){
        $.ajax({
            url: '/teacher/api/public/courses/' + courseId,
            type: 'GET',
            success: function(result){
                if(result.success){
                    var course = result.data;
                    $('#courseTitle').text(course.name);
                    $('#courseAge').text(getAgeGroupText(course.target_age));
                    $('#courseDifficulty').text(getDifficultyText(course.difficulty));
                    $('#courseType').text(getCourseTypeText(course.is_online));
                    $('#courseDuration').text(course.duration + '课时');
                    $('#coursePrice').text(course.price ? '¥' + course.price : '面议');
                    $('#courseDescription').html(course.description || '暂无描述');
                    
                    layer.open({
                        type: 1,
                        title: '课程详情',
                        area: ['800px', '600px'],
                        content: $('#courseDetail')
                    });
                } else {
                    layer.msg(result.message || '获取课程详情失败');
                }
            },
            error: function(){
                layer.msg('获取课程详情失败');
            }
        });
    };
    
    // 联系课程
    window.contactCourse = function(courseId){
        layer.open({
            type: 1,
            title: '课程咨询',
            area: ['500px', '400px'],
            content: $('#contactForm'),
            success: function(layero, index){
                form.render();
                // 设置课程ID
                $('input[name="course_id"]').val(courseId);
            }
        });
    };
    
    // 搜索课程
    window.searchCourses = function(){
        var targetAge = $('select[name="target_age"]').val();
        var difficulty = $('select[name="difficulty"]').val();
        var isOnline = $('select[name="is_online"]').val();
        
        $.ajax({
            url: '/teacher/api/public/courses',
            type: 'GET',
            data: {
                target_age: targetAge,
                difficulty: difficulty,
                is_online: isOnline
            },
            success: function(result){
                if(result.success){
                    renderCourses(result.data);
                } else {
                    $('#coursesList').html('<div class="layui-empty">暂无符合条件的课程</div>');
                }
            },
            error: function(){
                $('#coursesList').html('<div class="layui-empty">搜索失败</div>');
            }
        });
    };
    
    // 监听咨询表单提交
    form.on('submit(submitContact)', function(data){
        var formData = data.field;
        
        $.ajax({
            url: '/teacher/api/public/courses/contact',
            type: 'POST',
            data: formData,
            success: function(result){
                if(result.success){
                    layer.msg('咨询提交成功，我们会尽快联系您');
                    layer.closeAll();
                } else {
                    layer.msg(result.message || '提交失败');
                }
            },
            error: function(){
                layer.msg('提交失败');
            }
        });
        return false;
    });
    
    // 获取课程类型文本
    function getCourseTypeText(isOnline){
        return isOnline == 1 ? '线上课程' : '线下课程';
    };
    
    // 获取年龄段文本
    function getAgeGroupText(targetAge){
        var ageMap = {
            'preschool': '学前班',
            'elementary': '小学',
            'middle': '中学',
            'high': '高中',
            'adult': '成人'
        };
        return ageMap[targetAge] || '不限';
    };
    
    // 获取难度文本
    function getDifficultyText(difficulty){
        var difficultyMap = {
            'beginner': '初级',
            'intermediate': '中级',
            'advanced': '高级'
        };
        return difficultyMap[difficulty] || '不限';
    };
});
