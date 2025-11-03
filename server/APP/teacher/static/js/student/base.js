// 学生端基础JS

// 全局配置
window.StudentSystem = {
    // API基础URL
    apiBase: '/teacher/api',
    
    // 当前学生信息
    student: {
        id: null,
        name: null,
        class_name: null
    },
    
    // 初始化
    init: function() {
        this.initStudentInfo();
        this.initEventListeners();
        this.initComponents();
    },
    
    // 初始化学生信息
    initStudentInfo: function() {
        this.student.id = window.sessionStorage.getItem('student_id');
        this.student.name = window.sessionStorage.getItem('student_name');
        this.student.class_name = window.sessionStorage.getItem('class_name');
    },
    
    // 初始化事件监听
    initEventListeners: function() {
        // 全局错误处理
        window.addEventListener('error', this.handleError.bind(this));
        
        // 网络状态监听
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));
        
        // 页面可见性变化
        document.addEventListener('visibilitychange', this.handleVisibilityChange.bind(this));
    },
    
    // 初始化组件
    initComponents: function() {
        // 初始化Layui组件
        layui.use(['element', 'layer', 'form'], function(){
            var element = layui.element;
            var layer = layui.layer;
            var form = layui.form;
        });
    },
    
    // 错误处理
    handleError: function(event) {
        console.error('页面错误:', event.error);
        this.showMessage('页面出现错误，请刷新重试', 'error');
    },
    
    // 网络在线
    handleOnline: function() {
        this.showMessage('网络连接已恢复', 'success');
    },
    
    // 网络离线
    handleOffline: function() {
        this.showMessage('网络连接已断开', 'warning');
    },
    
    // 页面可见性变化
    handleVisibilityChange: function() {
        if (document.hidden) {
            // 页面隐藏时暂停媒体播放
            this.pauseAllMedia();
        }
    },
    
    // 暂停所有媒体
    pauseAllMedia: function() {
        var videos = document.querySelectorAll('video');
        var audios = document.querySelectorAll('audio');
        
        videos.forEach(function(video) {
            if (!video.paused) {
                video.pause();
            }
        });
        
        audios.forEach(function(audio) {
            if (!audio.paused) {
                audio.pause();
            }
        });
    },
    
    // 显示消息
    showMessage: function(message, type) {
        layui.use('layer', function(){
            var layer = layui.layer;
            var icon = type === 'success' ? 1 : type === 'error' ? 2 : type === 'warning' ? 3 : 0;
            layer.msg(message, {icon: icon});
        });
    },
    
    // API请求封装
    request: function(url, options) {
        var defaultOptions = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        };
        
        var finalOptions = Object.assign({}, defaultOptions, options);
        
        return fetch(this.apiBase + url, finalOptions)
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络请求失败');
                }
                return response.json();
            })
            .catch(error => {
                console.error('API请求错误:', error);
                this.showMessage('请求失败，请重试', 'error');
                throw error;
            });
    },
    
    // GET请求
    get: function(url, params) {
        var queryString = '';
        if (params) {
            queryString = '?' + Object.keys(params)
                .map(key => encodeURIComponent(key) + '=' + encodeURIComponent(params[key]))
                .join('&');
        }
        return this.request(url + queryString);
    },
    
    // POST请求
    post: function(url, data) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    // 更新学习进度
    updateProgress: function(materialId, progress, lastPosition) {
        return this.post('/student/completion/' + materialId, {
            status: 0,
            progress: progress,
            last_position: lastPosition
        });
    },
    
    // 标记完成
    markComplete: function(materialId) {
        return this.post('/student/completion/' + materialId, {
            status: 1,
            progress: 100
        });
    },
    
    // 获取作业列表
    getMaterials: function() {
        return this.get('/student/materials');
    },
    
    // 确认对话框
    confirm: function(message, callback) {
        layui.use('layer', function(){
            var layer = layui.layer;
            layer.confirm(message, {
                icon: 3,
                title: '确认操作'
            }, function(index){
                if (callback) callback();
                layer.close(index);
            });
        });
    },
    
    // 加载中
    loading: function(message) {
        layui.use('layer', function(){
            var layer = layui.layer;
            return layer.load(1, {
                shade: [0.1, '#fff'],
                content: message || '加载中...'
            });
        });
    },
    
    // 关闭加载
    closeLoading: function(index) {
        layui.use('layer', function(){
            var layer = layui.layer;
            layer.close(index);
        });
    },
    
    // 格式化时间
    formatTime: function(timestamp) {
        var date = new Date(timestamp);
        var year = date.getFullYear();
        var month = (date.getMonth() + 1).toString().padStart(2, '0');
        var day = date.getDate().toString().padStart(2, '0');
        var hours = date.getHours().toString().padStart(2, '0');
        var minutes = date.getMinutes().toString().padStart(2, '0');
        
        return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes;
    },
    
    // 格式化时长
    formatDuration: function(seconds) {
        var hours = Math.floor(seconds / 3600);
        var minutes = Math.floor((seconds % 3600) / 60);
        var secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return hours + ':' + minutes.toString().padStart(2, '0') + ':' + secs.toString().padStart(2, '0');
        } else {
            return minutes + ':' + secs.toString().padStart(2, '0');
        }
    },
    
    // 检查是否过期
    isExpired: function(deadline) {
        if (!deadline) return false;
        return new Date(deadline) < new Date();
    },
    
    // 获取剩余时间
    getRemainingTime: function(deadline) {
        if (!deadline) return null;
        
        var now = new Date();
        var deadlineDate = new Date(deadline);
        var diff = deadlineDate - now;
        
        if (diff <= 0) return '已过期';
        
        var days = Math.floor(diff / (1000 * 60 * 60 * 24));
        var hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        var minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        
        if (days > 0) {
            return days + '天' + hours + '小时';
        } else if (hours > 0) {
            return hours + '小时' + minutes + '分钟';
        } else {
            return minutes + '分钟';
        }
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    StudentSystem.init();
});
