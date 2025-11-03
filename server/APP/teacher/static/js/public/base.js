// 公共展示页面基础JS

// 全局配置
window.PublicSystem = {
    // API基础URL
    apiBase: '/teacher/api',
    
    // 初始化
    init: function() {
        this.initEventListeners();
        this.initComponents();
        this.initAnimations();
    },
    
    // 初始化事件监听
    initEventListeners: function() {
        // 全局错误处理
        window.addEventListener('error', this.handleError.bind(this));
        
        // 网络状态监听
        window.addEventListener('online', this.handleOnline.bind(this));
        window.addEventListener('offline', this.handleOffline.bind(this));
        
        // 滚动事件
        window.addEventListener('scroll', this.handleScroll.bind(this));
    },
    
    // 初始化组件
    initComponents: function() {
        // 初始化Layui组件
        layui.use(['element', 'layer', 'carousel'], function(){
            var element = layui.element;
            var layer = layui.layer;
            var carousel = layui.carousel;
        });
    },
    
    // 初始化动画
    initAnimations: function() {
        // 滚动动画
        this.initScrollAnimations();
        
        // 卡片悬停效果
        this.initCardHover();
    },
    
    // 滚动动画
    initScrollAnimations: function() {
        var observer = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        });
        
        var elements = document.querySelectorAll('.layui-card');
        elements.forEach(function(element) {
            observer.observe(element);
        });
    },
    
    // 卡片悬停效果
    initCardHover: function() {
        var cards = document.querySelectorAll('.layui-card');
        cards.forEach(function(card) {
            card.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-5px)';
                this.style.transition = 'all 0.3s ease';
            });
            
            card.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0)';
            });
        });
    },
    
    // 错误处理
    handleError: function(event) {
        console.error('页面错误:', event.error);
    },
    
    // 网络在线
    handleOnline: function() {
        this.showMessage('网络连接已恢复', 'success');
    },
    
    // 网络离线
    handleOffline: function() {
        this.showMessage('网络连接已断开', 'warning');
    },
    
    // 滚动处理
    handleScroll: function() {
        var scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // 导航栏背景透明度
        var header = document.querySelector('.layui-header');
        if (header) {
            if (scrollTop > 50) {
                header.style.backgroundColor = 'rgba(30, 159, 255, 0.95)';
            } else {
                header.style.backgroundColor = '';
            }
        }
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
    
    // 获取教师列表
    getTeachers: function() {
        return this.get('/teachers');
    },
    
    // 获取活动列表
    getActivities: function() {
        return this.get('/activities');
    },
    
    // 获取课程列表
    getCourses: function() {
        return this.get('/courses');
    },
    
    // 获取材料列表
    getMaterials: function() {
        return this.get('/materials');
    },
    
    // 搜索材料
    searchMaterials: function(keyword, type) {
        return this.get('/materials/search', {
            keyword: keyword,
            type: type
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
    
    // 格式化文件大小
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 B';
        
        var k = 1024;
        var sizes = ['B', 'KB', 'MB', 'GB'];
        var i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },
    
    // 平滑滚动
    smoothScroll: function(target) {
        var element = document.querySelector(target);
        if (element) {
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    },
    
    // 返回顶部
    scrollToTop: function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
};

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    PublicSystem.init();
});

// 添加CSS动画
var style = document.createElement('style');
style.textContent = `
    .layui-card {
        opacity: 0;
        transform: translateY(30px);
        transition: all 0.6s ease;
    }
    
    .layui-card.animate-in {
        opacity: 1;
        transform: translateY(0);
    }
    
    .layui-header {
        transition: background-color 0.3s ease;
    }
`;
document.head.appendChild(style);
