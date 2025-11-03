// 教师系统后台管理基础JS

// 全局配置
window.TeacherAdmin = {
    // API基础URL
    apiBase: '/teacher/api',
    
    // 当前用户信息
    user: {
        id: null,
        name: null
    },
    
    // 初始化
    init: function() {
        this.initUserInfo();
        this.initEventListeners();
        this.initComponents();
    },
    
    // 初始化用户信息
    initUserInfo: function() {
        // 从session或其他地方获取用户信息
        this.user.id = window.sessionStorage.getItem('teacher_id');
        this.user.name = window.sessionStorage.getItem('teacher_name');
    },
    
    // 初始化事件监听
    initEventListeners: function() {
        // 全局错误处理
        window.addEventListener('error', this.handleError.bind(this));
        
        // 网络状态监听
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));
    },
    
    // 初始化组件
    initComponents: function() {
        // 初始化Layui组件
        layui.use(['element', 'layer', 'form', 'table'], function(){
            var element = layui.element;
            var layer = layui.layer;
            var form = layui.form;
            var table = layui.table;
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
    
    // PUT请求
    put: function(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    // DELETE请求
    delete: function(url) {
        return this.request(url, {
            method: 'DELETE'
        });
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
        var seconds = date.getSeconds().toString().padStart(2, '0');
        
        return year + '-' + month + '-' + day + ' ' + hours + ':' + minutes + ':' + seconds;
    },
    
    // 格式化文件大小
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 B';
        
        var k = 1024;
        var sizes = ['B', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // 验证手机号
    validatePhone: function(phone) {
        var reg = /^1[3-9]\d{9}$/;
        return reg.test(phone);
    },
    
    // 验证邮箱
    validateEmail: function(email) {
        var reg = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return reg.test(email);
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    TeacherAdmin.init();
});
