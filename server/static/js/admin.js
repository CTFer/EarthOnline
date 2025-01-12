layui.use(['layer', 'form', 'element'], function(){
    var layer = layui.layer;
    var form = layui.form;
    var element = layui.element;
    var $ = layui.jquery;

    // MD5加密函数
    function md5(string) {
        return CryptoJS.MD5(string).toString();
    }

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
                // 获取表单数据
                const username = $('input[name="username"]').val();
                const password = $('input[name="password"]').val();
                
                // 验证表单
                if (!username || !password) {
                    layer.msg('请填写完整信息');
                    return;
                }

                // 发送请求
                fetch('/admin/api/adduser', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        username: username,
                        password: md5(password)  // 密码MD5加密
                    })
                })
                .then(response => response.json())
                .then(result => {
                    if (result.error) {
                        throw new Error(result.error);
                    }
                    layer.msg('添加成功');
                    layer.close(index);
                    loadUsers();  // 重新加载用户列表
                })
                .catch(error => {
                    console.error('添加用户失败:', error);
                    layer.msg('添加用户失败: ' + error.message);
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