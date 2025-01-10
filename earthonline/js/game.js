// 后端服务器地址配置
const SERVER = 'http://192.168.1.8:5000';

// WebSocket连接
const socket = io('http://192.168.1.8:5000');
const statusDot = document.querySelector('.status-dot');
const statusText = document.querySelector('.status-text');

// WebSocket事件处理
socket.on('connect', () => {
    statusDot.classList.add('connected');
    statusText.textContent = 'WebSocket已连接';
});

socket.on('disconnect', () => {
    statusDot.classList.remove('connected');
    statusText.textContent = 'WebSocket已断开';
});

// 获取并显示可用任务
async function loadTasks() {
    try {
        const taskList = document.getElementById('taskList');
        if (!taskList) {
            console.error('找不到taskList元素');
            return;
        }

        const userId = localStorage.getItem('userId') || '1';
        const response = await fetch(`${SERVER}/api/tasks/available/${userId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const availableData = await response.json();

        if (!availableData || !Array.isArray(availableData)) {
            taskList.innerHTML = '<div class="empty-tip">暂无可用任务</div>';
            return;
        }

        // 生成任务卡片
        const taskCards = availableData.map(task => {
            const typeInfo = getTaskTypeInfo(task.task_type);
            return `
                <div class="task-card">
                    <div class="task-icon-container" style="color: ${typeInfo.color}">
                        <i class="layui-icon ${typeInfo.icon}"></i>
                    </div>
                    <div class="task-main-content">
                        <div class="task-header">
                            <span class="task-type" style="background: ${typeInfo.color}20; color: ${typeInfo.color}">
                                ${typeInfo.text}
                            </span>
                        </div>
                        <div class="task-content">
                            <h3>${task.name}</h3>
                            <p>${task.description}</p>
                        </div>
                        <div class="task-footer">
                            <button class="layui-btn layui-btn-normal layui-btn-sm" onclick="acceptTask(${task.id})">
                                <i class="layui-icon layui-icon-ok"></i>
                                接受任务
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        taskList.innerHTML = taskCards.length > 0 ? taskCards : '<div class="empty-tip">暂无可用任务</div>';
    } catch (error) {
        console.error('加载任务失败:', error);
        const taskList = document.getElementById('taskList');
        if (taskList) {
            taskList.innerHTML = '<div class="empty-tip">加载任务失败</div>';
        }
    }
}

// 创建任务卡片（用于进行中的任务）
function createTaskCard(task) {
    const typeInfo = getTaskTypeInfo(task.task_type);
    const div = document.createElement('div');
    div.className = 'task-card';
    
    // 计算任务剩余时间
    const now = new Date();
    const endTime = new Date(task.endtime * 1000); // 假设endtime是时间戳
    const timeRemaining = endTime - now;
    
    let timeDisplay = formatTimeRemaining(timeRemaining);
    
    div.innerHTML = `
        <div class="task-icon-container" style="color: ${typeInfo.color}">
            <i class="layui-icon ${typeInfo.icon}"></i>
        </div>
        <div class="task-main-content">
            <div class="task-header">
                <span class="task-type" style="background: ${typeInfo.color}20; color: ${typeInfo.color}">
                    ${typeInfo.text}
                </span>
                <span class="task-time">剩余 ${timeDisplay}</span>
            </div>
            <div class="task-content">
                <h3>${task.name}</h3>
                <p>${task.description}</p>
            </div>
            <div class="task-footer">
                <span class="task-reward">
                    <i class="layui-icon layui-icon-diamond"></i>
                    奖励: ${task.reward || '无'}
                </span>
                <button class="layui-btn layui-btn-danger layui-btn-sm" onclick="abandonTask(${task.id})">
                    <i class="layui-icon layui-icon-close"></i>
                    放弃任务
                </button>
            </div>
        </div>
    `;
    return div;
}

// 获取任务状态
function getTaskStatus(task) {
    console.log(task);
    
    return task.task_status ? 'available' : 'available';
}

// 获取状态文本
function getStatusText(status) {
    if (!status) return '可接取';
    const statusMap = {
        'AVAILABLE': '可接取',
        'IN_PROGRESS': '进行中',
        'COMPLETED': '已完成',
        'ABANDONED': '已放弃'
    };
    return statusMap[status] || status;
}

// 处理任务点击
function handleTaskClick(task) {
    if (!task.task_status) {
        layer.confirm('是否接受该任务？', {
            btn: ['接受','取消']
        }, function(){
            acceptTask(task.id);
        });
    } else {
        layer.msg(`任务状态: ${getStatusText(task.task_status)}`);
    }
}

// 接受任务
async function acceptTask(taskId) {
    try {
        const response = await fetch(`${SERVER}/api/tasks/${taskId}/accept`, {
            method: 'POST'
        });
        
        if (response.ok) {
            layer.msg('成功接受任务', {icon: 1});
            loadTasks();
        } else {
            throw new Error('接受任务失败');
        }
    } catch (error) {
        console.error('接受任务失败:', error);
        layer.msg('接受任务失败', {icon: 2});
    }
}

// 加载角色信息
async function loadPlayerInfo() {
    try {
        const response = await fetch(`${SERVER}/api/player`);
        const character = await response.json();
        
        if (response.ok) {
            updateCharacterUI(character);
        } else {
            throw new Error(character.error || '加载角色信息失败');
        }
    } catch (error) {
        console.error('加载角色信息失败:', error);
        layer.msg('加载角色信息失败: ' + error.message);
    }
}

// 更新角色UI
function updateCharacterUI(character) {
    // 更新经验值和等级
    const expBar = document.querySelector('.exp-bar-inner');
    const levelSpan = document.querySelector('.level');
    const expSpan = document.querySelector('.exp');
    
    const level = parseInt(character.level) || 66;
    const currentExp = parseInt(character.experience) || 75666;
    const maxExp = level * 100; // 每级所需经验为等级数x100
    
    // 计算经验值百分比
    const expPercentage = (currentExp % maxExp) / maxExp * 100;
    expBar.style.width = `${expPercentage}%`;
    
    // 更新等级和经验值显示
    levelSpan.textContent = `${level}/100`;
    expSpan.textContent = `${currentExp % maxExp}/${maxExp}`;
}

// 获取任务类型信息
function getTaskTypeInfo(typeId) {
    const typeMap = {
        '1': {  // 主线任务
            text: '主线任务',
            color: '#FFC107',  // 金色
            icon: 'layui-icon-star'
        },
        '2': {  // 支线任务
            text: '支线任务',
            color: '#2196F3',  // 蓝色
            icon: 'layui-icon-note'
        },
        '3': {  // 特殊任务
            text: '特殊任务',
            color: '#9C27B0',  // 紫色
            icon: 'layui-icon-gift'
        },
        '4': {  // 每日任务
            text: '每日任务',
            color: '#4CAF50',  // 绿色
            icon: 'layui-icon-date'
        }
    };
    return typeMap[typeId] || {
        text: '未知类型',
        color: '#757575',
        icon: 'layui-icon-help'
    };
}

// 更新任务卡片渲染函数
function renderTaskCard(task) {
    const typeInfo = getTaskTypeInfo(task.task_type); // 使用task_type字段
    return `
        <div class="task-card" data-task-id="${task.id}">
            <div class="task-header" style="color: ${typeInfo.color}">
                <i class="layui-icon ${typeInfo.icon}"></i>
                <span class="task-type">${typeInfo.text}</span>
            </div>
            <div class="task-content">
                <h3>${task.name}</h3>
                <p>${task.description}</p>
            </div>
            <div class="task-footer">
                <span class="task-reward">奖励: ${task.reward || '无'}</span>
                ${task.status === 'IN_PROGRESS' ? 
                    `<button class="layui-btn layui-btn-danger layui-btn-sm" onclick="abandonTask(${task.id})">放弃</button>` :
                    `<button class="layui-btn layui-btn-normal layui-btn-sm" onclick="acceptTask(${task.id})">接受</button>`
                }
            </div>
        </div>
    `;
}

// 更新任务通知弹窗
socket.on('nfc_task_update', function(data) {
    const typeInfo = getTaskTypeInfo(data.task_type); // 使用task_type字段
    layer.open({
        type: 1,
        title: false,
        closeBtn: true,
        shadeClose: true,
        area: ['500px', 'auto'],
        skin: 'layui-layer-nobg',
        content: `
            <div class="task-notification">
                <div class="task-header">
                    <div class="task-icon" style="color: ${typeInfo.color}">
                        <i class="layui-icon ${typeInfo.icon}"></i>
                    </div>
                    <div class="task-title">
                        <h3>${data.task_name}</h3>
                        <small>${typeInfo.text}</small>
                    </div>
                </div>
                <div class="task-description">${data.task_description}</div>
                <div class="task-time">打卡时间: ${data.timestamp}</div>
            </div>
        `
    });
    
    loadTasks();
});

// 确保在DOM完全加载后再执行
document.addEventListener('DOMContentLoaded', () => {
    // 初始化所有需要的功能
    loadPlayerInfo();
    loadTasks();
    loadCurrentTasks();
});

// 创建进行中的任务卡片
function createActiveTaskCard(task) {
    const div = document.createElement('div');
    div.className = 'task-card';
    
    // 计算任务剩余时间
    const now = new Date();
    const endTime = new Date(task.endtime);
    const timeRemaining = endTime - now;
    
    let timeDisplay;
    if (timeRemaining <= 0) {
        timeDisplay = '已超时';
    } else {
        timeDisplay = formatTimeRemaining(timeRemaining);
    }
    
    div.innerHTML = `
        <div class="task-icon-container">
            <i class="layui-icon layui-icon-loading layui-anim layui-anim-rotate layui-anim-loop"></i>
        </div>
        <div class="task-main-content">
            <div class="task-header">
                <span class="task-type">进行中</span>
                <span class="task-time">剩余 ${timeDisplay}</span>
            </div>
            <div class="task-content">
                <h3>${task.name}</h3>
                <p>${task.description}</p>
            </div>
            <div class="task-footer">
                <span class="task-reward">
                    <i class="layui-icon layui-icon-diamond"></i>
                    奖励: ${task.rewards}
                </span>
                <button class="layui-btn layui-btn-danger layui-btn-sm" onclick="abandonTask(${task.id})">
                    <i class="layui-icon layui-icon-close"></i>
                    放弃任务
                </button>
            </div>
        </div>
    `;
    return div;
}

// 格式化剩余时间
function formatTimeRemaining(milliseconds) {
    if (milliseconds <= 0) {
        return '已结束';
    }
    
    const seconds = Math.floor(milliseconds / 1000);
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const remainingSeconds = seconds % 60;
    
    if (hours > 0) {
        return `${hours}小时${minutes}分钟`;
    } else if (minutes > 0) {
        return `${minutes}分钟${remainingSeconds}秒`;
    } else {
        return `${remainingSeconds}秒`;
    }
}

// 定时更新任务时间显示
function startTaskTimeUpdater() {
    setInterval(() => {
        document.querySelectorAll('.task-card').forEach(card => {
            const timeSpan = card.querySelector('.task-time');
            if (!timeSpan) return;
            
            const isDaily = card.classList.contains('daily');
            const now = new Date();
            let endTime;
            
            if (isDaily) {
                // 每日任务结束时间为当天晚上10点
                endTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 22, 0, 0);
            } else {
                // 普通任务从data属性获取结束时间
                const taskEndTime = card.dataset.endTime;
                if (!taskEndTime) return;
                endTime = new Date(taskEndTime);
            }
            
            const timeRemaining = endTime - now;
            timeSpan.textContent = '剩余 ' + formatTimeRemaining(timeRemaining);
        });
    }, 1000);
}

// 在页面加载完成后启动时间更新器
document.addEventListener('DOMContentLoaded', () => {
    startTaskTimeUpdater();
    // ... 其他初始化代码 ...
});

// 创建每日任务卡片
function createDailyTaskCard(task) {
    const div = document.createElement('div');
    div.className = 'task-card daily';
    
    // 计算今天晚上10点的时间
    const now = new Date();
    const endTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 22, 0, 0);
    
    // 如果当前时间超过了今天的晚上10点，显示"已结束"
    const timeRemaining = endTime - now;
    let timeDisplay;
    
    if (timeRemaining <= 0) {
        timeDisplay = '已结束';
    } else {
        timeDisplay = formatTimeRemaining(timeRemaining);
    }
    
    div.innerHTML = `
        <div class="task-icon-container">
            <i class="layui-icon layui-icon-date"></i>
        </div>
        <div class="task-main-content">
            <div class="task-header">
                <span class="task-type daily">每日任务</span>
                <span class="task-time">剩余 ${timeDisplay}</span>
            </div>
            <div class="task-content">
                <h3>${task.name}</h3>
                <p>${task.description}</p>
            </div>
            <div class="task-footer">
                <span class="task-reward">
                    <i class="layui-icon layui-icon-diamond"></i>
                    奖励: ${task.rewards}
                </span>
            </div>
        </div>
    `;
    return div;
}

// 放弃任务
async function abandonTask(taskId) {
    // 使用 layui 的确认框
    layer.confirm('确定要放弃这个任务吗？', {
        icon: 3,
        title: '提示',
        btn: ['确定放弃', '继续任务'],
        skin: 'layui-layer-molv', // 使用墨绿色主题
        anim: 1, // 弹出动画
        btnAlign: 'c', // 按钮居中
        shade: 0.6 // 遮罩透明度
    }, async function(index) { // 点击确认按钮的回调
        try {
            const response = await fetch(`${SERVER}/api/tasks/abandon`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    task_id: taskId,
                    user_id: localStorage.getItem('userId')
                })
            });

            const result = await response.json();
            if (response.ok) {
                layer.msg('任务已放弃', {icon: 1});
                loadCurrentTasks(); // 重新加载任务列表
                loadAvailableTasks(); // 刷新可用任务列表
            } else {
                layer.msg(result.error || '放弃任务失败', {icon: 2});
            }
        } catch (error) {
            console.error('放弃任务失败:', error);
            layer.msg('操作失败，请稍后重试', {icon: 2});
        }
        layer.close(index);
    });
}

// 初始化Swiper实例
let activeTasksSwiper = null;

// 初始化Swiper
function initActiveTasksSwiper() {
    if (activeTasksSwiper) {
        activeTasksSwiper.destroy(true, true);
    }
    
    activeTasksSwiper = new Swiper('.active-tasks-swiper', {
        slidesPerView: 1,
        spaceBetween: 30,
        mousewheel: true,
        pagination: {
            el: '.swiper-pagination',
            clickable: true
        },
        autoplay: {
            delay: 5000,
            disableOnInteraction: false
        }
    });
}

// 获取并显示当前任务
async function loadCurrentTasks() {
    try {
        const userId = localStorage.getItem('userId') || '1';
        
        // 获取所有进行中的任务（包括每日任务和普通任务）
        const response = await fetch(`${SERVER}/api/tasks/current/${userId}`);
        const tasks = await response.json();
        
        // 处理任务显示
        const tasksContainer = document.querySelector('.active-tasks-swiper .swiper-wrapper');
        tasksContainer.innerHTML = '';

        if (tasks.length > 0) {
            // 将任务分组，每组3个
            const taskGroups = [];
            for (let i = 0; i < tasks.length; i += 3) {
                taskGroups.push(tasks.slice(i, i + 3));
            }

            // 为每组任务创建一个slide
            taskGroups.forEach(group => {
                const slide = document.createElement('div');
                slide.className = 'swiper-slide';
                
                const taskRow = document.createElement('div');
                taskRow.className = 'active-tasks-row';
                
                group.forEach(task => {
                    const taskCard = createTaskCard(task);
                    taskRow.appendChild(taskCard);
                });
                
                slide.appendChild(taskRow);
                tasksContainer.appendChild(slide);
            });

            // 初始化Swiper
            setTimeout(() => {
                initActiveTasksSwiper();
            }, 0);
        } else {
            tasksContainer.innerHTML = '<div class="swiper-slide"><div class="empty-tip">暂无进行中的任务</div></div>';
        }
    } catch (error) {
        console.error('加载任务失败:', error);
        layer.msg('加载任务失败', {icon: 2});
    }
}

// 在页面加载完成后执行
document.addEventListener('DOMContentLoaded', () => {
    loadCurrentTasks();
});

// 在页面卸载时销毁Swiper实例
window.addEventListener('beforeunload', () => {
    if (activeTasksSwiper) {
        activeTasksSwiper.destroy(true, true);
    }
});

// 添加自动刷新任务列表的功能
function startTaskRefresh() {
    setInterval(() => {
        loadTasks();
        loadCurrentTasks();
    }, 30000); // 每30秒刷新一次
}

// 在页面加载完成后启动自动刷新
document.addEventListener('DOMContentLoaded', () => {
    startTaskRefresh();
});     