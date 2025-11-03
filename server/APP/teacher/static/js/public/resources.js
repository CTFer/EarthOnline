/**
 * 公开资源JavaScript
 */
layui.use(['layer', 'form'], function(){
    var layer = layui.layer;
    var form = layui.form;
    
    // 页面加载时获取资源列表
    $(document).ready(function(){
        loadResources();
    });
    
    // 加载资源列表
    function loadResources(){
        $.ajax({
            url: '/teacher/api/public/resources',
            type: 'GET',
            success: function(result){
                if(result.success){
                    renderResources(result.data);
                } else {
                    $('#resourcesList').html('<div class="layui-empty">暂无资源数据</div>');
                }
            },
            error: function(){
                $('#resourcesList').html('<div class="layui-empty">加载失败</div>');
            }
        });
    };
    
    // 渲染资源列表
    function renderResources(resources){
        var html = '';
        resources.forEach(function(resource){
            html += '<div class="layui-col-md6">';
            html += '<div class="layui-card">';
            html += '<div class="layui-card-header">';
            html += '<h3>' + resource.title + '</h3>';
            html += '<span class="layui-badge ' + getResourceTypeClass(resource.type) + '">' + getResourceTypeText(resource.type) + '</span>';
            html += '</div>';
            html += '<div class="layui-card-body">';
            html += '<p><strong>文件大小：</strong>' + formatFileSize(resource.file_size) + '</p>';
            if(resource.file_duration){
                html += '<p><strong>时长：</strong>' + formatDuration(resource.file_duration) + '</p>';
            }
            html += '<p><strong>创建时间：</strong>' + formatDateTime(resource.create_time) + '</p>';
            if(resource.description){
                html += '<p>' + resource.description.substring(0, 100) + (resource.description.length > 100 ? '...' : '') + '</p>';
            }
            html += '<div style="margin-top: 15px;">';
            html += '<button class="layui-btn layui-btn-sm" onclick="viewResourceDetail(' + resource.id + ')">查看详情</button>';
            if(resource.type === 'video' || resource.type === 'audio'){
                html += '<button class="layui-btn layui-btn-sm layui-btn-normal" onclick="playResource(' + resource.id + ')">在线播放</button>';
            } else {
                html += '<button class="layui-btn layui-btn-sm layui-btn-warm" onclick="downloadResource(' + resource.id + ')">下载资源</button>';
            }
            html += '</div>';
            html += '</div>';
            html += '</div>';
            html += '</div>';
        });
        
        $('#resourcesList').html(html);
    };
    
    // 查看资源详情
    window.viewResourceDetail = function(resourceId){
        $.ajax({
            url: '/teacher/api/public/resources/' + resourceId,
            type: 'GET',
            success: function(result){
                if(result.success){
                    var resource = result.data;
                    $('#resourceTitle').text(resource.title);
                    $('#resourceType').text(getResourceTypeText(resource.type));
                    $('#resourceSize').text(formatFileSize(resource.file_size));
                    $('#resourceTime').text(formatDateTime(resource.create_time));
                    $('#resourceDuration').text(resource.file_duration ? formatDuration(resource.file_duration) : '-');
                    $('#resourceDownloads').text(resource.download_count || 0);
                    $('#resourceDescription').html(resource.description || '暂无描述');
                    
                    // 显示相应的操作按钮
                    if(resource.type === 'video' || resource.type === 'audio'){
                        $('#playBtn').show().attr('onclick', 'playResource(' + resourceId + ')');
                        $('#downloadBtn').hide();
                    } else {
                        $('#playBtn').hide();
                        $('#downloadBtn').show().attr('onclick', 'downloadResource(' + resourceId + ')');
                    }
                    
                    layer.open({
                        type: 1,
                        title: '资源详情',
                        area: ['800px', '600px'],
                        content: $('#resourceDetail')
                    });
                } else {
                    layer.msg(result.message || '获取资源详情失败');
                }
            },
            error: function(){
                layer.msg('获取资源详情失败');
            }
        });
    };
    
    // 播放资源
    window.playResource = function(resourceId){
        $.ajax({
            url: '/teacher/api/public/resources/' + resourceId,
            type: 'GET',
            success: function(result){
                if(result.success){
                    var resource = result.data;
                    $('#playerTitle').text(resource.title);
                    
                    // 根据资源类型显示不同的播放器
                    if(resource.type === 'video'){
                        $('#videoPlayer').show();
                        $('#audioPlayer').hide();
                        $('#documentViewer').hide();
                        $('#videoElement source').attr('src', resource.file_url);
                        $('#videoElement')[0].load();
                    } else if(resource.type === 'audio'){
                        $('#videoPlayer').hide();
                        $('#audioPlayer').show();
                        $('#documentViewer').hide();
                        $('#audioElement source').attr('src', resource.file_url);
                        $('#audioElement')[0].load();
                    } else if(resource.type === 'document'){
                        $('#videoPlayer').hide();
                        $('#audioPlayer').hide();
                        $('#documentViewer').show();
                        $('#documentFrame').attr('src', resource.file_url);
                    }
                    
                    layer.open({
                        type: 1,
                        title: '资源播放',
                        area: ['900px', '700px'],
                        content: $('#resourcePlayer')
                    });
                } else {
                    layer.msg(result.message || '获取资源失败');
                }
            },
            error: function(){
                layer.msg('获取资源失败');
            }
        });
    };
    
    // 下载资源
    window.downloadResource = function(resourceId){
        // 记录下载次数
        $.ajax({
            url: '/teacher/api/public/resources/' + resourceId + '/download',
            type: 'POST',
            success: function(result){
                if(result.success){
                    // 直接下载文件
                    window.open(result.data.download_url);
                } else {
                    layer.msg(result.message || '下载失败');
                }
            },
            error: function(){
                layer.msg('下载失败');
            }
        });
    };
    
    // 关闭播放器
    window.closePlayer = function(){
        layer.closeAll();
    };
    
    // 搜索资源
    window.searchResources = function(){
        var type = $('select[name="type"]').val();
        var keyword = $('input[name="keyword"]').val();
        
        $.ajax({
            url: '/teacher/api/public/resources',
            type: 'GET',
            data: {
                type: type,
                keyword: keyword
            },
            success: function(result){
                if(result.success){
                    renderResources(result.data);
                } else {
                    $('#resourcesList').html('<div class="layui-empty">暂无符合条件的资源</div>');
                }
            },
            error: function(){
                $('#resourcesList').html('<div class="layui-empty">搜索失败</div>');
            }
        });
    };
    
    // 获取资源类型样式类
    function getResourceTypeClass(type){
        var classMap = {
            'video': 'layui-bg-red',
            'audio': 'layui-bg-orange',
            'document': 'layui-bg-blue'
        };
        return classMap[type] || 'layui-bg-gray';
    };
    
    // 获取资源类型文本
    function getResourceTypeText(type){
        var textMap = {
            'video': '视频',
            'audio': '音频',
            'document': '文档'
        };
        return textMap[type] || '未知';
    };
    
    // 格式化文件大小
    function formatFileSize(size){
        if(!size) return '-';
        if(size < 1024){
            return size + 'B';
        } else if(size < 1024 * 1024){
            return Math.floor(size / 1024) + 'KB';
        } else {
            return Math.floor(size / (1024 * 1024)) + 'MB';
        }
    };
    
    // 格式化时长
    function formatDuration(seconds){
        var hours = Math.floor(seconds / 3600);
        var minutes = Math.floor((seconds % 3600) / 60);
        var secs = seconds % 60;
        
        if(hours > 0){
            return hours + ':' + String(minutes).padStart(2, '0') + ':' + String(secs).padStart(2, '0');
        } else {
            return minutes + ':' + String(secs).padStart(2, '0');
        }
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
