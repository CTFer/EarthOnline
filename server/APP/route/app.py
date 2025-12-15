# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2023-11-14 13:28:31
# LastEditTime: 2025-11-27 16:09:10
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2023 迷舍

"""
轨迹系统蓝图创建
"""
import os
import hashlib
from flask import Blueprint, render_template, request, jsonify, send_from_directory, session, redirect, url_for
import json
import sqlite3
import datetime

def create_route_blueprint():
    """创建轨迹系统蓝图"""
    # 创建主蓝图，指定模板文件夹和静态文件夹
    current_dir = os.path.dirname(os.path.abspath(__file__))
    route_bp = Blueprint('route', __name__, 
                        url_prefix='/route',
                        template_folder=os.path.join(current_dir, 'templates'),
                        static_folder=os.path.join(current_dir, 'static'))
    
    # 根路由重定向

    @route_bp.route('/', methods=['GET'])
    def route_index():
        from flask import redirect, url_for
        return redirect(url_for('route.index'))
    
    # 使用Flask默认的静态文件处理机制，不需要自定义路由
    
    # 错误处理
    @route_bp.errorhandler(404)
    def not_found(error):
        """404错误处理"""
        return render_template('error.html', 
                             message='页面不存在',
                             error_code=404), 404
    
    @route_bp.errorhandler(500)
    def internal_error(error):
        """500错误处理"""
        return render_template('error.html', 
                             message='服务器内部错误',
                             error_code=500), 500
    
    return route_bp

# 创建蓝图实例
route_bp = create_route_blueprint()

# 数据库连接
def get_db_connection():
    """获取数据库连接"""
    db_path = os.path.join(os.path.dirname(__file__), 'data.sqlite3')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

def get_cursor():
    """获取数据库游标"""
    conn = get_db_connection()
    return conn.cursor(), conn


# 认证相关函数
def login_required(f):
    """登录检查装饰器"""
    def decorator(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('route.login'))
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

def authenticate(username, password):
    """验证用户"""
    cursor, conn = get_cursor()
    try:
        # 计算密码的MD5哈希
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        cursor.execute("SELECT * FROM user WHERE user = ? AND password = ?", (username, md5_hash))
        user = cursor.fetchone()
        return user is not None
    finally:
        conn.close()
# 登录页面
@route_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if authenticate(username, password):
            session['user'] = username
            return redirect(url_for('route.admin'))  # 登录成功后跳转到管理页面
        else:
            return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')

# 登出
@route_bp.route('/logout')
def logout():
    """登出"""
    session.pop('user', None)
    return redirect(url_for('route.login'))

# 实际的首页视图 - 只显示地图
@route_bp.route('/index')
def index():
    """轨迹图首页（只显示地图）"""
    # 添加调试信息，确保这个函数被调用
    print("轨迹图模块的index函数被调用")
    
    # 直接使用蓝图自己的模板目录，确保加载的是轨迹系统自己的模板
    # 获取蓝图模板目录的绝对路径
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'map.html')
    print(f"尝试加载地图模板: {template_path}")
    
    try:
        # 检查模板是否存在
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            # 使用当前蓝图的上下文渲染模板
            from flask import current_app
            template = current_app.jinja_env.from_string(template_content)
            return template.render()
        else:
            # 如果新模板不存在，使用旧的index.html并在前端通过JS隐藏表单
            old_template_path = os.path.join(os.path.dirname(__file__), 'templates', 'index.html')
            if os.path.exists(old_template_path):
                with open(old_template_path, 'r', encoding='utf-8') as f:
                    template_content = f.read()
                
                # 在模板内容中添加隐藏表单的脚本
                template_content = template_content.replace('</body>', '''
                <script>
                    // 隐藏表单和其他元素，只显示地图
                    document.querySelector('.header').style.display = 'none';
                    document.querySelector('#list-table').style.display = 'none';
                </script>
                </body>
                ''')
                
                from flask import current_app
                template = current_app.jinja_env.from_string(template_content)
                return template.render()
            else:
                return "模板文件不存在", 500
    except Exception as e:
        print(f"加载模板失败: {e}")
        return f"加载模板失败: {str(e)}", 500

# CRUD页面 - 需要登录
@route_bp.route('/admin')
@login_required
def admin():
    """增删改查管理页面"""
    return render_template('admin.html', username=session.get('user'))

@route_bp.route('/getCityList')
def get_city_list():
    """获取城市列表（包含省份信息）"""
    cursor, conn = get_cursor()
    try:
        # 查询城市名称、省份信息和坐标
        city = cursor.execute('select name, province, x, y from city').fetchall()
        result = []
        for eachone in city:
            # 返回包含城市名称、省份信息和坐标的对象
            result.append({
                'name': eachone[0],
                'province': eachone[1] if eachone[1] else '',
                'x': eachone[2],
                'y': eachone[3]
            })
        print(f"返回城市列表数据，共{len(result)}条记录")
        return jsonify(result)
    except Exception as e:
        print(f"获取城市列表失败: {e}")
        return jsonify([])
    finally:
        conn.close()

@route_bp.route('/getCity')
def get_city():
    """返回到达过的城市列表，带坐标和省份信息"""
    cursor, conn = get_cursor()
    try:
        # 先获取所有路线数据
        route = cursor.execute(
            'select date,method,start,end,start_x,start_y,end_x,end_y,remark from route order by date asc').fetchall()
        
        # 创建城市集合，避免重复
        city_set = set()
        result = []
        
        # 处理每个路线的起点和终点
        for eachone in route:
            start_city = eachone[2]
            end_city = eachone[3]
            
            # 处理起点城市
            if start_city and (start_city,) not in city_set:
                city_set.add((start_city,))
                # 查询起点城市的省份信息
                cursor.execute('select province from city where name = ?', (start_city,))
                province_result = cursor.fetchone()
                province = province_result[0] if province_result and province_result[0] else ''
                result.append({
                    'name': start_city,
                    'x': eachone[4],
                    'y': eachone[5],
                    'province': province
                })
            
            # 处理终点城市
            if end_city and (end_city,) not in city_set:
                city_set.add((end_city,))
                # 查询终点城市的省份信息
                cursor.execute('select province from city where name = ?', (end_city,))
                province_result = cursor.fetchone()
                province = province_result[0] if province_result and province_result[0] else ''
                result.append({
                    'name': end_city,
                    'x': eachone[6],
                    'y': eachone[7],
                    'province': province
                })
        
        print(f"返回城市数据，共{len(result)}个城市")
        return jsonify(result)
    except Exception as e:
        print(f"获取城市数据失败: {e}")
        return jsonify([])
    finally:
        conn.close()

@route_bp.route('/getRoute')
def get_route():
    """获取路线数据，包含省份信息"""
    cursor, conn = get_cursor()
    try:
        route = cursor.execute(
            'select id, date, method, start, end, start_x, start_y, end_x, end_y, remark from route order by date asc').fetchall()
        result = []
        
        for eachone in route:
            route_id = eachone[0]
            date = eachone[1]
            method = eachone[2]
            start_city = eachone[3]
            end_city = eachone[4]
            start_x = eachone[5]
            start_y = eachone[6]
            end_x = eachone[7]
            end_y = eachone[8]
            remark = eachone[9]
            
            # 查询起点城市的省份信息
            cursor.execute('select province from city where name = ?', (start_city,))
            start_province_result = cursor.fetchone()
            start_province = start_province_result[0] if start_province_result and start_province_result[0] else ''
            
            # 查询终点城市的省份信息
            cursor.execute('select province from city where name = ?', (end_city,))
            end_province_result = cursor.fetchone()
            end_province = end_province_result[0] if end_province_result and end_province_result[0] else ''
            
            # 返回包含省份信息的路线对象
            result.append({
                'id': route_id,
                'date': date,
                'method': method,
                'start': start_city,
                'end': end_city,
                'start_x': start_x,
                'start_y': start_y,
                'end_x': end_x,
                'end_y': end_y,
                'remark': remark,
                'start_province': start_province,
                'end_province': end_province
            })
        
        print(f"返回路线数据，共{len(result)}条记录")
        return jsonify(result)
    except Exception as e:
        print(f"获取路线数据失败: {e}")
        return jsonify([])
    finally:
        conn.close()

@route_bp.route('/add', methods=['POST', 'GET'])
@login_required
def add_route():
    """添加路线"""
    cursor, conn = get_cursor()
    try:
        data = request.values
        start = data.get('start')
        end = data.get('end')
        method = data.get('method')
        date_str = data.get('date')
        remark = data.get('remark')
        muti = data.get('muti', 0)
        
        if not start or not end or not method or not date_str:
            return jsonify({'success': False, 'error': '缺少必要参数'})
        
        # 获取起点坐标
        start_str = 'select x,y from city where name="' + start + '"'
        start_position = cursor.execute(start_str).fetchall()
        if not start_position:
            return jsonify({'success': False, 'error': '起点城市不存在'})
        start_x = start_position[0][0]
        start_y = start_position[0][1]
        
        # 获取终点坐标
        end_str = 'select x,y from city where name="' + end + '"'
        end_position = cursor.execute(end_str).fetchall()
        if not end_position:
            return jsonify({'success': False, 'error': '终点城市不存在'})
        end_x = end_position[0][0]
        end_y = end_position[0][1]
        
        # 获取当前时间戳
        current_time = int(datetime.datetime.now().timestamp())
        
        # 添加数据
        sql = 'INSERT INTO route (date,method,start,end,start_x,start_y,end_x,end_y,remark,muti, addtime, edittime) values (?,?,?,?,?,?,?,?,?,?,?,?)'
        cursor.execute(sql, (date_str, method, start, end, start_x, start_y, end_x, end_y, remark, muti, current_time, current_time))
        conn.commit()
        
        result = {
            "start": start, 
            "end": end, 
            'start_x': start_x,
            "start_y": start_y, 
            "end_x": end_x, 
            "end_y": end_y,
            "success": True
        }
        return jsonify(result)
    except Exception as e:
        print(f"添加失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@route_bp.route('/list')
def list_route():
    """获取路线列表"""
    cursor, conn = get_cursor()
    try:
        # 包含id字段以便进行编辑和删除操作
        route = cursor.execute(
            'select id, date, method, start, end, start_x, start_y, end_x, end_y, remark from route order by date desc').fetchall()
        return jsonify(route)
    finally:
        conn.close()

@route_bp.route('/edit', methods=['POST', 'GET'])
@login_required
def edit_route():
    """修改路径数据"""
    if request.method == 'POST':
        # 处理更新操作
        cursor, conn = get_cursor()
        try:
            data = request.values
            route_id = data.get('id')
            date = data.get('date')
            method = data.get('method')
            start = data.get('start')
            end = data.get('end')
            remark = data.get('remark')
            
            # 获取起点坐标
            start_str = 'select x,y from city where name="' + start + '"'
            start_position = cursor.execute(start_str).fetchall()
            if not start_position:
                return jsonify({'success': False, 'error': '起点城市不存在'})
            start_x = start_position[0][0]
            start_y = start_position[0][1]
            
            # 获取终点坐标
            end_str = 'select x,y from city where name="' + end + '"'
            end_position = cursor.execute(end_str).fetchall()
            if not end_position:
                return jsonify({'success': False, 'error': '终点城市不存在'})
            end_x = end_position[0][0]
            end_y = end_position[0][1]
            
            # 更新数据
            sql = '''
            UPDATE route 
            SET date = ?, method = ?, start = ?, end = ?, 
                start_x = ?, start_y = ?, end_x = ?, end_y = ?, 
                remark = ?, edittime = ? 
            WHERE id = ?
            '''
            current_time = int(datetime.datetime.now().timestamp())
            cursor.execute(sql, (date, method, start, end, start_x, start_y, end_x, end_y, remark, current_time, route_id))
            conn.commit()
            
            return jsonify({'success': True})
        except Exception as e:
            print(f"更新失败: {e}")
            return jsonify({'success': False, 'error': str(e)})
        finally:
            conn.close()
    else:
        # 获取单个路线数据用于编辑
        route_id = request.args.get('id')
        cursor, conn = get_cursor()
        try:
            route = cursor.execute(
                'select id, date, method, start, end, remark from route where id = ?', (route_id,)).fetchone()
            if route:
                return jsonify(route)
            else:
                return jsonify({'error': '记录不存在'})
        finally:
            conn.close()

@route_bp.route('/delete', methods=['POST'])
@login_required
def delete_route():
    """删除路径数据"""
    cursor, conn = get_cursor()
    try:
        data = request.values
        route_id = data.get('id')
        
        # 删除数据
        sql = 'DELETE FROM route WHERE id = ?'
        cursor.execute(sql, (route_id,))
        conn.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"删除失败: {e}")
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

@route_bp.route('/test', methods=['POST', 'GET'])
def test():
    """测试接口"""
    data = request.values
    return jsonify(dict(data))

# 独立运行支持
if __name__ == '__main__':
    from flask import Flask
    from flask_cors import CORS
    
    # 创建独立应用
    app = Flask(__name__, template_folder="templates", static_folder="static")
    CORS(app)
    
    # 注册蓝图
    app.register_blueprint(route_bp)
    
    print("轨迹图模块独立运行模式")
    print("访问地址: http://localhost:5000/route/")
    print("按 Ctrl+C 停止服务")
    
    app.debug = True
    # flask 不支持中文名称的电脑
    app.run(host='127.0.0.1', port=5000)
