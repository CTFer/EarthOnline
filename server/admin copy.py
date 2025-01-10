from flask import Blueprint, request, jsonify, render_template_string, session, redirect, url_for
from functools import wraps
import sqlite3
import os
from api import api_registry

# 创建蓝图
admin_bp = Blueprint('admin', __name__)

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(__file__), 'database', 'game.db')

# 管理员认证装饰器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_db_connection():
    """创建数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 登录页面模板
LOGIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>管理员登录</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/layui@2.9.21/dist/css/layui.css">
    <style>
        body {
            background: #0a192f;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .login-container {
            background: rgba(27, 39, 53, 0.5);
            padding: 30px;
            border-radius: 8px;
            width: 300px;
        }
        .login-title {
            color: #57CAFF;
            text-align: center;
            margin-bottom: 20px;
        }
        .layui-input {
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(87, 202, 255, 0.2);
            color: #fff;
        }
        .layui-input:focus {
            border-color: #57CAFF;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h2 class="login-title">管理员登录</h2>
        <form class="layui-form" method="post">
            <div class="layui-form-item">
                <input type="text" name="username" required lay-verify="required" 
                       placeholder="用户名" class="layui-input">
            </div>
            <div class="layui-form-item">
                <input type="password" name="password" required lay-verify="required" 
                       placeholder="密码" class="layui-input">
            </div>
            <div class="layui-form-item">
                <button class="layui-btn layui-btn-fluid" lay-submit>登录</button>
            </div>
        </form>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/layui@2.9.21/dist/layui.js"></script>
</body>
</html>
"""

# 管理页面模板
ADMIN_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>游戏管理后台</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/layui@2.9.21/dist/css/layui.css">
    <style>
        body {
            margin: 0;
            padding: 20px;
            background: #0a192f;
            color: #fff;
            font-family: Arial, sans-serif;
        }
        .admin-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .panel {
            margin-bottom: 30px;
            padding: 20px;
            background: rgba(27, 39, 53, 0.5);
            border: 1px solid rgba(87, 202, 255, 0.2);
            border-radius: 8px;
        }
        h1, h2 {
            color: #57CAFF;
        }
        .layui-table {
            background: rgba(27, 39, 53, 0.5);
            color: #fff;
        }
        .layui-table th {
            background: rgba(87, 202, 255, 0.1);
            color: #57CAFF;
        }
        .control-panel {
            margin-bottom: 20px;
        }
        .popup-form {
            padding: 20px;
            display: none;
        }
        .popup-form .layui-form-item {
            margin-bottom: 15px;
        }
        .popup-form .layui-input {
            background: rgba(27, 39, 53, 0.5);
            border: 1px solid rgba(87, 202, 255, 0.2);
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="admin-container">
        <h1>游戏管理后台</h1>
        
        <!-- 用户管理面板 -->
        <div class="panel">
            <h2>用户管理</h2>
            <div class="control-panel">
                <button class="layui-btn" onclick="showAddUserForm()">添加用户</button>
            </div>
            <table class="layui-table" id="userTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>用户名</th>
                        <th>创建时间</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- 技能管理面板 -->
        <div class="panel">
            <h2>技能管理</h2>
            <div class="control-panel">
                <button class="layui-btn" onclick="showAddSkillForm()">添加技能</button>
            </div>
            <table class="layui-table" id="skillTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>技能名称</th>
                        <th>熟练度</th>
                        <th>描述</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>
        
        <!-- 任务管理面板 -->
        <div class="panel">
            <h2>任务管理</h2>
            <div class="control-panel">
                <button class="layui-btn" onclick="showAddTaskForm()">添加任务</button>
            </div>
            <table class="layui-table" id="taskTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>任务名称</th>
                        <th>描述</th>
                        <th>经验值</th>
                        <th>金币</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <!-- API文档面板 -->
        <div class="panel">
            <h2>API文档</h2>
            <div class="layui-tab">
                <ul class="layui-tab-title">
                    <li class="layui-this">管理API</li>
                    <li>游戏API</li>
                </ul>
                <div class="layui-tab-content">
                    <div class="layui-tab-item layui-show" id="adminApiList"></div>
                    <div class="layui-tab-item" id="gameApiList"></div>
                </div>
            </div>
        </div>

        <button class="layui-btn layui-btn-danger" onclick="location.href='/admin/logout'">退出登录</button>
    </div>

    <!-- 用户表单模板 -->
    <div id="userForm" class="popup-form">
        <form class="layui-form">
            <div class="layui-form-item">
                <label class="layui-form-label">用户名</label>
                <div class="layui-input-block">
                    <input type="text" name="username" required lay-verify="required" class="layui-input">
                </div>
            </div>
            <div class="layui-form-item">
                <label class="layui-form-label">密码</label>
                <div class="layui-input-block">
                    <input type="password" name="password" required lay-verify="required" class="layui-input">
                </div>
            </div>
        </form>
    </div>

    <!-- 技能表单模板 -->
    <div id="skillForm" class="popup-form">
        <form class="layui-form">
            <div class="layui-form-item">
                <label class="layui-form-label">技能名称</label>
                <div class="layui-input-block">
                    <input type="text" name="name" required lay-verify="required" class="layui-input">
                </div>
            </div>
            <div class="layui-form-item">
                <label class="layui-form-label">熟练度</label>
                <div class="layui-input-block">
                    <input type="number" name="proficiency" required lay-verify="required|number" class="layui-input">
                </div>
            </div>
            <div class="layui-form-item">
                <label class="layui-form-label">描述</label>
                <div class="layui-input-block">
                    <textarea name="description" class="layui-textarea"></textarea>
                </div>
            </div>
        </form>
    </div>

    <!-- 任务表单模板 -->
    <div id="taskForm" class="popup-form">
        <form class="layui-form">
            <div class="layui-form-item">
                <label class="layui-form-label">任务名称</label>
                <div class="layui-input-block">
                    <input type="text" name="name" required lay-verify="required" class="layui-input">
                </div>
            </div>
            <div class="layui-form-item">
                <label class="layui-form-label">描述</label>
                <div class="layui-input-block">
                    <textarea name="description" class="layui-textarea"></textarea>
                </div>
            </div>
            <div class="layui-form-item">
                <label class="layui-form-label">经验值</label>
                <div class="layui-input-block">
                    <input type="number" name="exp_reward" required lay-verify="required|number" class="layui-input">
                </div>
            </div>
            <div class="layui-form-item">
                <label class="layui-form-label">金币</label>
                <div class="layui-input-block">
                    <input type="number" name="gold_reward" required lay-verify="required|number" class="layui-input">
                </div>
            </div>
        </form>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/layui@2.9.21/dist/layui.js"></script>
    <script>
        layui.use(['layer', 'form', 'element'], function(){
            var layer = layui.layer;
            var form = layui.form;
            var element = layui.element;
            var $ = layui.jquery;

            // 页面加载完成后执行
            $(document).ready(function() {
                loadUsers();
                loadSkills();
                loadTasks();
                loadApiDocs();
            });

            // 加载用户列表
            async function loadUsers() {
                try {
                    const response = await fetch('/admin/api/users');
                    const result = await response.json();
                    
                    if (result.error) {
                        throw new Error(result.error);
                    }

                    const users = result.data || [];
                    const tbody = document.querySelector('#userTable tbody');
                    
                    tbody.innerHTML = users.map(user => `
                        <tr>
                            <td>${user.id}</td>
                            <td>${user.username}</td>
                            <td>${user.created_at}</td>
                            <td>
                                <button class="layui-btn layui-btn-sm" onclick="editUser(${user.id})">编辑</button>
                                <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="deleteUser(${user.id})">删除</button>
                            </td>
                        </tr>
                    `).join('');
                } catch (error) {
                    console.error('加载用户失败:', error);
                    layer.msg('加载用户失败: ' + error.message);
                }
            }

            // 加载技能列表
            async function loadSkills() {
                try {
                    const response = await fetch('/admin/api/skills');
                    const result = await response.json();
                    
                    if (result.error) {
                        throw new Error(result.error);
                    }

                    const skills = result.data || [];
                    const tbody = document.querySelector('#skillTable tbody');
                    
                    tbody.innerHTML = skills.map(skill => `
                        <tr>
                            <td>${skill.id}</td>
                            <td>${skill.name}</td>
                            <td>${skill.proficiency}</td>
                            <td>${skill.description || ''}</td>
                            <td>
                                <button class="layui-btn layui-btn-sm" onclick="editSkill(${skill.id})">编辑</button>
                                <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="deleteSkill(${skill.id})">删除</button>
                            </td>
                        </tr>
                    `).join('');
                } catch (error) {
                    console.error('加载技能失败:', error);
                    layer.msg('加载技能失败: ' + error.message);
                }
            }

            // 加载任务列表
            async function loadTasks() {
                try {
                    const response = await fetch('/admin/api/tasks');
                    const result = await response.json();
                    
                    if (result.error) {
                        throw new Error(result.error);
                    }

                    const tasks = result.data || [];
                    const tbody = document.querySelector('#taskTable tbody');
                    
                    tbody.innerHTML = tasks.map(task => `
                        <tr>
                            <td>${task.id}</td>
                            <td>${task.name}</td>
                            <td>${task.description || ''}</td>
                            <td>${task.exp_reward}</td>
                            <td>${task.gold_reward}</td>
                            <td>
                                <button class="layui-btn layui-btn-sm" onclick="editTask(${task.id})">编辑</button>
                                <button class="layui-btn layui-btn-sm layui-btn-danger" onclick="deleteTask(${task.id})">删除</button>
                            </td>
                        </tr>
                    `).join('');
                } catch (error) {
                    console.error('加载任务失败:', error);
                    layer.msg('加载任务失败: ' + error.message);
                }
            }

            // 加载API文档
            async function loadApiDocs() {
                try {
                    const response = await fetch('/admin/api/docs');
                    const result = await response.json();
                    
                    if (result.error) {
                        throw new Error(result.error);
                    }

                    const adminApis = result.data.filter(api => api.path.startsWith('/admin'));
                    const gameApis = result.data.filter(api => !api.path.startsWith('/admin'));

                    // 渲染管理API
                    document.getElementById('adminApiList').innerHTML = renderApiList(adminApis);
                    
                    // 渲染游戏API
                    document.getElementById('gameApiList').innerHTML = renderApiList(gameApis);
                    
                } catch (error) {
                    console.error('加载API文档失败:', error);
                    layer.msg('加载API文档失败: ' + error.message);
                }
            }

            function renderApiList(apis) {
                return apis.map(api => `
                    <div class="layui-card">
                        <div class="layui-card-header">
                            <span class="layui-badge layui-bg-blue">${api.method}</span>
                            ${api.path}
                            ${api.auth_required ? '<span class="layui-badge">需要认证</span>' : ''}
                        </div>
                        <div class="layui-card-body">
                            <p>${api.description}</p>
                            ${api.parameters ? renderParameters(api.parameters) : ''}
                            ${api.response ? renderResponse(api.response) : ''}
                        </div>
                    </div>
                `).join('');
            }

            function renderParameters(parameters) {
                return `
                    <div class="layui-collapse">
                        <div class="layui-colla-item">
                            <h2 class="layui-colla-title">请求参数</h2>
                            <div class="layui-colla-content">
                                <table class="layui-table">
                                    <thead>
                                        <tr>
                                            <th>参数名</th>
                                            <th>类型</th>
                                            <th>是否必须</th>
                                            <th>描述</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${parameters.map(param => `
                                            <tr>
                                                <td>${param.name}</td>
                                                <td>${param.type}</td>
                                                <td>${param.required ? '是' : '否'}</td>
                                                <td>${param.description}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                `;
            }

            function renderResponse(response) {
                return `
                    <div class="layui-collapse">
                        <div class="layui-colla-item">
                            <h2 class="layui-colla-title">响应数据</h2>
                            <div class="layui-colla-content">
                                <pre class="layui-code">${JSON.stringify(response, null, 2)}</pre>
                            </div>
                        </div>
                    </div>
                `;
            }

            // 显示添加用户表单
            window.showAddUserForm = function() {
                layer.open({
                    type: 1,
                    title: '添加用户',
                    content: $('#userForm'),
                    area: ['500px', '300px'],
                    btn: ['确定', '取消'],
                    yes: function(index) {
                        const formData = {
                            username: $('input[name="username"]').val(),
                            password: $('input[name="password"]').val()
                        };
                        
                        fetch('/admin/api/users', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(formData)
                        })
                        .then(response => response.json())
                        .then(result => {
                            if (result.error) {
                                throw new Error(result.error);
                            }
                            layer.close(index);
                            layer.msg('添加成功');
                            loadUsers();
                        })
                        .catch(error => {
                            layer.msg('添加失败: ' + error.message);
                        });
                    }
                });
            };

            // 显示添加技能表单
            window.showAddSkillForm = function() {
                layer.open({
                    type: 1,
                    title: '添加技能',
                    content: $('#skillForm'),
                    area: ['500px', '400px'],
                    btn: ['确定', '取消'],
                    yes: function(index) {
                        const formData = {
                            name: $('input[name="name"]').val(),
                            proficiency: parseInt($('input[name="proficiency"]').val()),
                            description: $('textarea[name="description"]').val()
                        };
                        
                        fetch('/admin/api/skills', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(formData)
                        })
                        .then(response => response.json())
                        .then(result => {
                            if (result.error) {
                                throw new Error(result.error);
                            }
                            layer.close(index);
                            layer.msg('添加成功');
                            loadSkills();
                        })
                        .catch(error => {
                            layer.msg('添加失败: ' + error.message);
                        });
                    }
                });
            };

            // 显示添加任务表单
            window.showAddTaskForm = function() {
                layer.open({
                    type: 1,
                    title: '添加任务',
                    content: $('#taskForm'),
                    area: ['500px', '500px'],
                    btn: ['确定', '取消'],
                    yes: function(index) {
                        const formData = {
                            name: $('input[name="name"]').val(),
                            description: $('textarea[name="description"]').val(),
                            exp_reward: parseInt($('input[name="exp_reward"]').val()),
                            gold_reward: parseInt($('input[name="gold_reward"]').val())
                        };
                        
                        fetch('/admin/api/tasks', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify(formData)
                        })
                        .then(response => response.json())
                        .then(result => {
                            if (result.error) {
                                throw new Error(result.error);
                            }
                            layer.close(index);
                            layer.msg('添加成功');
                            loadTasks();
                        })
                        .catch(error => {
                            layer.msg('添加失败: ' + error.message);
                        });
                    }
                });
            };

            // 编辑用户
            window.editUser = function(id) {
                fetch(`/admin/api/users/${id}`)
                .then(response => response.json())
                .then(user => {
                    $('input[name="username"]').val(user.username);
                    $('input[name="password"]').val('');
                    
                    layer.open({
                        type: 1,
                        title: '编辑用户',
                        content: $('#userForm'),
                        area: ['500px', '300px'],
                        btn: ['确定', '取消'],
                        yes: function(index) {
                            const formData = {
                                username: $('input[name="username"]').val(),
                                password: $('input[name="password"]').val()
                            };
                            
                            fetch(`/admin/api/users/${id}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(formData)
                            })
                            .then(response => response.json())
                            .then(result => {
                                if (result.error) {
                                    throw new Error(result.error);
                                }
                                layer.close(index);
                                layer.msg('更新成功');
                                loadUsers();
                            })
                            .catch(error => {
                                layer.msg('更新失败: ' + error.message);
                            });
                        }
                    });
                });
            };

            // 删除用户
            window.deleteUser = function(id) {
                layer.confirm('确定要删除这个用户吗？', {
                    btn: ['确定','取消']
                }, function(){
                    fetch(`/admin/api/users/${id}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(result => {
                        if (result.error) {
                            throw new Error(result.error);
                        }
                        layer.msg('删除成功');
                        loadUsers();
                    })
                    .catch(error => {
                        layer.msg('删除失败: ' + error.message);
                    });
                });
            };

            // 编辑技能
            window.editSkill = function(id) {
                fetch(`/admin/api/skills/${id}`)
                .then(response => response.json())
                .then(skill => {
                    $('input[name="name"]').val(skill.name);
                    $('input[name="proficiency"]').val(skill.proficiency);
                    $('textarea[name="description"]').val(skill.description);
                    
                    layer.open({
                        type: 1,
                        title: '编辑技能',
                        content: $('#skillForm'),
                        area: ['500px', '400px'],
                        btn: ['确定', '取消'],
                        yes: function(index) {
                            const formData = {
                                name: $('input[name="name"]').val(),
                                proficiency: parseInt($('input[name="proficiency"]').val()),
                                description: $('textarea[name="description"]').val()
                            };
                            
                            fetch(`/admin/api/skills/${id}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(formData)
                            })
                            .then(response => response.json())
                            .then(result => {
                                if (result.error) {
                                    throw new Error(result.error);
                                }
                                layer.close(index);
                                layer.msg('更新成功');
                                loadSkills();
                            })
                            .catch(error => {
                                layer.msg('更新失败: ' + error.message);
                            });
                        }
                    });
                });
            };

            // 删除技能
            window.deleteSkill = function(id) {
                layer.confirm('确定要删除这个技能吗？', {
                    btn: ['确定','取消']
                }, function(){
                    fetch(`/admin/api/skills/${id}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(result => {
                        if (result.error) {
                            throw new Error(result.error);
                        }
                        layer.msg('删除成功');
                        loadSkills();
                    })
                    .catch(error => {
                        layer.msg('删除失败: ' + error.message);
                    });
                });
            };

            // 编辑任务
            window.editTask = function(id) {
                fetch(`/admin/api/tasks/${id}`)
                .then(response => response.json())
                .then(task => {
                    $('input[name="name"]').val(task.name);
                    $('textarea[name="description"]').val(task.description);
                    $('input[name="exp_reward"]').val(task.exp_reward);
                    $('input[name="gold_reward"]').val(task.gold_reward);
                    
                    layer.open({
                        type: 1,
                        title: '编辑任务',
                        content: $('#taskForm'),
                        area: ['500px', '500px'],
                        btn: ['确定', '取消'],
                        yes: function(index) {
                            const formData = {
                                name: $('input[name="name"]').val(),
                                description: $('textarea[name="description"]').val(),
                                exp_reward: parseInt($('input[name="exp_reward"]').val()),
                                gold_reward: parseInt($('input[name="gold_reward"]').val())
                            };
                            
                            fetch(`/admin/api/tasks/${id}`, {
                                method: 'PUT',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(formData)
                            })
                            .then(response => response.json())
                            .then(result => {
                                if (result.error) {
                                    throw new Error(result.error);
                                }
                                layer.close(index);
                                layer.msg('更新成功');
                                loadTasks();
                            })
                            .catch(error => {
                                layer.msg('更新失败: ' + error.message);
                            });
                        }
                    });
                });
            };

            // 删除任务
            window.deleteTask = function(id) {
                layer.confirm('确定要删除这个任务吗？', {
                    btn: ['确定','取消']
                }, function(){
                    fetch(`/admin/api/tasks/${id}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(result => {
                        if (result.error) {
                            throw new Error(result.error);
                        }
                        layer.msg('删除成功');
                        loadTasks();
                    })
                    .catch(error => {
                        layer.msg('删除失败: ' + error.message);
                    });
                });
            };
        });
    </script>
</body>
</html>
"""

# 路由处理
@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 这里简化了验证逻辑，实际应用中应该使用更安全的方式
        if username == 'admin' and password == 'admin123':
            session['is_admin'] = True
            return redirect(url_for('admin.index'))
        
    return render_template_string(LOGIN_PAGE)

@admin_bp.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@admin_required
def index():
    return render_template_string(ADMIN_PAGE)

# API路由
@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    """获取所有用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at FROM users')
        users = [dict(row) for row in cursor.fetchall()]
        return jsonify({"data": users})
    except Exception as e:
        print(f"Error in get_users: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/users', methods=['POST'])
@admin_required
def add_user():
    """添加新用户"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (username, password_hash, created_at)
            VALUES (?, ?, datetime('now'))
        ''', (data['username'], data['password']))  # 实际应用中应该对密码进行哈希处理
        
        user_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({"id": user_id}), 201
    except Exception as e:
        print(f"Error in add_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/users/<int:user_id>', methods=['GET'])
@admin_required
def get_user(user_id):
    """获取指定用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, username, created_at FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        
        if user is None:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify(dict(user))
    except Exception as e:
        print(f"Error in get_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """更新用户信息"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if data.get('password'):
            cursor.execute('''
                UPDATE users 
                SET username = ?, password_hash = ?
                WHERE id = ?
            ''', (data['username'], data['password'], user_id))  # 实际应用中应该对密码进行哈希处理
        else:
            cursor.execute('''
                UPDATE users 
                SET username = ?
                WHERE id = ?
            ''', (data['username'], user_id))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 删除用户相关的任务
        cursor.execute('DELETE FROM tasks WHERE user_id = ?', (user_id,))
        
        # 删除用户
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in delete_user: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/skills', methods=['GET'])
@admin_required
def get_skills():
    """获取所有技能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, proficiency, description FROM skills')
        skills = [dict(row) for row in cursor.fetchall()]
        return jsonify({"data": skills})
    except Exception as e:
        print(f"Error in get_skills: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/skills', methods=['POST'])
@admin_required
def add_skill():
    """添加新技能"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO skills (name, proficiency, description)
            VALUES (?, ?, ?)
        ''', (data['name'], data['proficiency'], data.get('description', '')))
        
        skill_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({"id": skill_id}), 201
    except Exception as e:
        print(f"Error in add_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/skills/<int:skill_id>', methods=['GET'])
@admin_required
def get_skill(skill_id):
    """获取指定技能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name, proficiency, description FROM skills WHERE id = ?', (skill_id,))
        skill = cursor.fetchone()
        
        if skill is None:
            return jsonify({'error': 'Skill not found'}), 404
            
        return jsonify(dict(skill))
    except Exception as e:
        print(f"Error in get_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/skills/<int:skill_id>', methods=['PUT'])
@admin_required
def update_skill(skill_id):
    """更新技能"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE skills 
            SET name = ?, proficiency = ?, description = ?
            WHERE id = ?
        ''', (data['name'], data['proficiency'], data.get('description', ''), skill_id))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in update_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/skills/<int:skill_id>', methods=['DELETE'])
@admin_required
def delete_skill(skill_id):
    """删除技能"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 首先删除相关的技能关系
        cursor.execute('DELETE FROM skill_relations WHERE parent_skill_id = ? OR child_skill_id = ?', 
                      (skill_id, skill_id))
        
        # 然后删除技能
        cursor.execute('DELETE FROM skills WHERE id = ?', (skill_id,))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in delete_skill: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks', methods=['GET'])
@admin_required
def get_tasks():
    """获取所有任务"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM tasks')
        tasks = [dict(row) for row in cursor.fetchall()]
        return jsonify({"data": tasks})
    except Exception as e:
        print(f"Error in get_tasks: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks', methods=['POST'])
@admin_required
def add_task():
    """添加新任务"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (name, description, exp_reward, gold_reward, created_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        ''', (data['name'], data['description'], data['exp_reward'], data['gold_reward']))
        
        task_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({"id": task_id}), 201
    except Exception as e:
        print(f"Error in add_task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
@admin_required
def update_task(task_id):
    """更新任务"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET name = ?, description = ?, exp_reward = ?, gold_reward = ?
            WHERE id = ?
        ''', (data['name'], data['description'], data['exp_reward'], data['gold_reward'], task_id))
        
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in update_task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@admin_required
def delete_task(task_id):
    """删除任务"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error in delete_task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# 添加API文档路由
@admin_bp.route('/api/docs', methods=['GET'])
@admin_required
def get_api_docs():
    """获取API文档"""
    try:
        endpoints = api_registry.get_all_endpoints()
        return jsonify({
            "data": [
                {
                    "path": endpoint.path,
                    "method": endpoint.method,
                    "description": endpoint.description,
                    "auth_required": endpoint.auth_required,
                    "parameters": endpoint.parameters,
                    "response": endpoint.response
                }
                for endpoint in endpoints
            ]
        })
    except Exception as e:
        print(f"Error in get_api_docs: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)