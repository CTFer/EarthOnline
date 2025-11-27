# -*- coding: utf-8 -*-

"""
workdata应用 - 数据库管理工具
支持SQLite数据库的表格管理，包括增删改查功能
"""
import os
import sqlite3
import hashlib
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, current_app, after_this_request
from .database import SQLiteDatabase, DatabaseManager
from .age_statistics import get_age_distribution

# 创建workdata蓝图
def create_workdata_blueprint():
    """创建workdata应用蓝图"""
    # 创建蓝图，指定模板文件夹和静态文件夹
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 不在这里设置url_prefix，让主应用在注册蓝图时统一设置
    workdata_bp = Blueprint('workdata', __name__, 
                          template_folder=os.path.join(current_dir, 'templates'),
                          static_folder=os.path.join(current_dir, 'static'))
    
    return workdata_bp

# 创建蓝图实例
workdata_bp = create_workdata_blueprint()

# 获取用户数据库连接
def get_user_db_connection():
    """获取用户数据库连接"""
    db_path = os.path.join('d:/code/EarthOnline/server/database', 'user.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    # 启用外键约束
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# 会话超时设置
def set_session_timeout():
    """设置会话超时时间"""
    # 设置会话最大持续时间为2小时
    session.permanent = True
    # Flask默认使用permanent_session_lifetime作为会话有效期

# 认证相关函数
def login_required(f):
    """登录检查装饰器"""
    def decorator(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('workdata.login'))
        return f(*args, **kwargs)
    decorator.__name__ = f.__name__
    return decorator

def authenticate(username, password):
    """验证用户"""
    conn = get_user_db_connection()
    try:
        # 计算密码的MD5哈希
        md5_hash = hashlib.md5(password.encode()).hexdigest()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user WHERE username = ? AND password = ?", (username, md5_hash))
        user = cursor.fetchone()
        return user
    finally:
        conn.close()

# 登录页面
@workdata_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    # 如果已登录，直接跳转到首页
    if 'user' in session:
        return redirect(url_for('workdata.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = authenticate(username, password)
        if user:
            # 登录成功，保存用户信息到session
            session['user'] = {
                'id': user[0],
                'username': user[1],
                'role': user[3],
                'remark': user[4]
            }
            # 设置会话超时
            set_session_timeout()
            return redirect(url_for('workdata.index'))
        else:
            # 登录失败
            return render_template('login.html', error='用户名或密码错误')
    
    # GET请求，显示登录页面
    return render_template('login.html')

# 登出功能
@workdata_bp.route('/logout')
def logout():
    """登出功能"""
    # 清除session中的用户信息
    session.pop('user', None)
    # 清除整个session
    session.clear()
    # 重定向到登录页面
    return redirect(url_for('workdata.login'))

# API - 检查登录状态
@workdata_bp.route('/api/check_login')
def check_login():
    """检查登录状态API"""
    if 'user' in session:
        return jsonify({
            'code': 0,
            'data': session['user'],
            'msg': '已登录'
        })
    else:
        return jsonify({
            'code': 401,
            'data': None,
            'msg': '未登录'
        })

# API - 获取用户信息
@workdata_bp.route('/api/user_info')
@login_required
def user_info():
    """获取当前用户信息API"""
    return jsonify({
        'code': 0,
        'data': session['user'],
        'msg': 'success'
    })

# API - 获取数据库列表
@workdata_bp.route('/api/databases')
@login_required
def get_databases():
    """获取数据库列表API"""
    try:
        databases = DatabaseManager.get_database_list()
        return jsonify({
            'code': 0,
            'data': databases,
            'msg': 'success'
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'获取数据库列表失败: {str(e)}'
        })

# API - 获取表格列表
@workdata_bp.route('/api/tables')
@login_required
def get_tables():
    """获取表格列表API"""
    try:
        db_name = request.args.get('db')
        if not db_name:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称不能为空'
            })
        
        # 验证数据库是否有效
        if not DatabaseManager.validate_database(db_name):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '数据库不存在或无效'
            })
        
        db_path = DatabaseManager.get_database_path(db_name)
        with SQLiteDatabase(db_path) as db:
            tables = db.get_tables()
            return jsonify({
                'code': 0,
                'data': tables,
                'msg': 'success'
            })
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'获取表格列表失败: {str(e)}'
        })

# API - 获取表格数据
@workdata_bp.route('/api/table_data')
@login_required
def get_table_data():
    """获取表格数据API"""
    try:
        # 获取请求参数
        db_name = request.args.get('db')
        table_name = request.args.get('table')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        keyword = request.args.get('keyword')
        order_by = request.args.get('order_by')
        order_dir = request.args.get('order_dir', 'ASC')
        
        # 验证参数
        if not db_name or not table_name:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称和表格名称不能为空'
            })
        
        # 验证数据库
        if not DatabaseManager.validate_database(db_name):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '数据库不存在或无效'
            })
        
        # 获取数据库路径
        db_path = DatabaseManager.get_database_path(db_name)
        
        with SQLiteDatabase(db_path) as db:
            # 检查表格是否存在
            tables = db.get_tables()
            if table_name not in tables:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格不存在'
                })
            
            # 获取数据
            result = db.get_table_data(
                table_name=table_name,
                page=page,
                limit=limit,
                keyword=keyword,
                order_by=order_by,
                order_dir=order_dir
            )
            
            # 转换为layui表格需要的格式
            return jsonify({
                'code': 0,
                'data': result['data'],
                'count': result['total'],
                'msg': 'success'
            })
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': [],
            'count': 0,
            'msg': f'获取数据失败: {str(e)}'
        })

# API - 获取表格结构
@workdata_bp.route('/api/table_structure')
@login_required
def get_table_structure():
    """获取表格结构API"""
    try:
        db_name = request.args.get('db')
        table_name = request.args.get('table')
        
        if not db_name or not table_name:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称和表格名称不能为空'
            })
        
        if not DatabaseManager.validate_database(db_name):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '数据库不存在或无效'
            })
        
        db_path = DatabaseManager.get_database_path(db_name)
        with SQLiteDatabase(db_path) as db:
            tables = db.get_tables()
            if table_name not in tables:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格不存在'
                })
            
            structure = db.get_table_structure(table_name)
            return jsonify({
                'code': 0,
                'data': structure,
                'msg': 'success'
            })
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'获取表格结构失败: {str(e)}'
        })

# API - 插入数据
@workdata_bp.route('/api/insert', methods=['POST'])
@login_required
def insert_data():
    """插入数据API"""
    try:
        data = request.get_json()
        db_name = data.get('db')
        table_name = data.get('table')
        record = data.get('record')
        
        if not db_name or not table_name or not record:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称、表格名称和数据不能为空'
            })
        
        if not DatabaseManager.validate_database(db_name):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '数据库不存在或无效'
            })
        
        db_path = DatabaseManager.get_database_path(db_name)
        with SQLiteDatabase(db_path) as db:
            tables = db.get_tables()
            if table_name not in tables:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格不存在'
                })
            
            # 插入数据
            new_id = db.insert_data(table_name, record)
            return jsonify({
                'code': 0,
                'data': {'id': new_id},
                'msg': '插入成功'
            })
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'插入失败: {str(e)}'
        })

# API - 更新数据
@workdata_bp.route('/api/update', methods=['POST'])
@login_required
def update_data():
    """更新数据API"""
    try:
        data = request.get_json()
        db_name = data.get('db')
        table_name = data.get('table')
        pk_value = data.get('pk_value')
        record = data.get('record')
        
        if not db_name or not table_name or pk_value is None or not record:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称、表格名称、主键值和数据不能为空'
            })
        
        if not DatabaseManager.validate_database(db_name):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '数据库不存在或无效'
            })
        
        db_path = DatabaseManager.get_database_path(db_name)
        with SQLiteDatabase(db_path) as db:
            tables = db.get_tables()
            if table_name not in tables:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格不存在'
                })
            
            # 更新数据
            row_count = db.update_data(table_name, pk_value, record)
            if row_count > 0:
                return jsonify({
                    'code': 0,
                    'data': {'row_count': row_count},
                    'msg': '更新成功'
                })
            else:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '未找到要更新的记录'
                })
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'更新失败: {str(e)}'
        })

# API - 删除数据
@workdata_bp.route('/api/delete', methods=['POST'])
@login_required
def delete_data():
    """删除数据API"""
    try:
        data = request.get_json()
        db_name = data.get('db')
        table_name = data.get('table')
        pk_value = data.get('pk_value')
        
        if not db_name or not table_name or pk_value is None:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称、表格名称和主键值不能为空'
            })
        
        if not DatabaseManager.validate_database(db_name):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '数据库不存在或无效'
            })
        
        db_path = DatabaseManager.get_database_path(db_name)
        with SQLiteDatabase(db_path) as db:
            tables = db.get_tables()
            if table_name not in tables:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格不存在'
                })
            
            # 删除数据
            row_count = db.delete_data(table_name, pk_value)
            if row_count > 0:
                return jsonify({
                    'code': 0,
                    'data': {'row_count': row_count},
                    'msg': '删除成功'
                })
            else:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '未找到要删除的记录'
                })
    except Exception as e:
        return jsonify({
            'code': 500,
            'data': None,
            'msg': f'删除失败: {str(e)}'
        })

def parse_filter_conditions(filter_json):
    """
    解析筛选条件JSON，转换为SQL WHERE子句和参数
    支持的操作符: =, !=, >, <, >=, <=, LIKE, IN, BETWEEN
    支持的逻辑操作: AND, OR, NOT
    格式示例: {"field": "age", "operator": ">", "value": 18}
    复合条件: {"logic": "AND", "conditions": [{...}, {...}]}
    """
    if not filter_json:
        return "", []
    
    try:
        # 解析JSON字符串
        import json
        conditions = json.loads(filter_json)
        
        def build_where_clause(condition_dict, params=None):
            if params is None:
                params = []
            
            # 复合条件
            if "logic" in condition_dict and "conditions" in condition_dict:
                logic = condition_dict["logic"].upper()
                if logic not in ["AND", "OR"]:
                    raise ValueError(f"不支持的逻辑操作符: {logic}")
                
                clauses = []
                for sub_condition in condition_dict["conditions"]:
                    clause, sub_params = build_where_clause(sub_condition, params)
                    if clause:
                        clauses.append(clause)
                
                if clauses:
                    return f"({f' {logic} '.join(clauses)})", params
                return "", params
            
            # NOT条件
            elif "not" in condition_dict:
                clause, sub_params = build_where_clause(condition_dict["not"], params)
                if clause:
                    return f"NOT ({clause})", params
                return "", params
            
            # 简单条件
            elif "field" in condition_dict and "operator" in condition_dict and "value" in condition_dict:
                field = condition_dict["field"]
                # 防止SQL注入，验证字段名
                if not field.isalnum() and '_' not in field:
                    raise ValueError(f"无效的字段名: {field}")
                
                operator = condition_dict["operator"].upper()
                value = condition_dict["value"]
                
                # 处理不同的操作符
                if operator == "=":
                    params.append(value)
                    return f"{field} = ?", params
                elif operator == "!=":
                    params.append(value)
                    return f"{field} != ?", params
                elif operator == ">":
                    params.append(value)
                    return f"{field} > ?", params
                elif operator == "<":
                    params.append(value)
                    return f"{field} < ?", params
                elif operator == ">=":
                    params.append(value)
                    return f"{field} >= ?", params
                elif operator == "<=":
                    params.append(value)
                    return f"{field} <= ?", params
                elif operator == "LIKE":
                    params.append(value)
                    return f"{field} LIKE ?", params
                elif operator == "IN":
                    if isinstance(value, list):
                        placeholders = ", ".join(["?"] * len(value))
                        params.extend(value)
                        return f"{field} IN ({placeholders})", params
                    else:
                        raise ValueError("IN操作符需要值为列表")
                elif operator == "BETWEEN":
                    if isinstance(value, list) and len(value) == 2:
                        params.extend(value)
                        return f"{field} BETWEEN ? AND ?", params
                    else:
                        raise ValueError("BETWEEN操作符需要两个值的列表")
                else:
                    raise ValueError(f"不支持的操作符: {operator}")
            
            raise ValueError("无效的条件格式")
        
        where_clause, params = build_where_clause(conditions)
        return where_clause, params
    except json.JSONDecodeError:
        raise ValueError("筛选条件JSON格式无效")
    except Exception as e:
        raise ValueError(f"解析筛选条件失败: {str(e)}")

@workdata_bp.route('/api/export_data', methods=['GET', 'POST'])
@login_required
def export_data():
    """导出数据API，支持Excel、JSON和CSV格式，支持灵活的条件筛选"""
    try:
        # 获取请求参数
        db_name = request.args.get('db') or request.form.get('db')
        table_name = request.args.get('table') or request.form.get('table')
        export_format = request.args.get('format', 'excel')  # 默认导出为Excel格式
        
        # 获取筛选条件（支持GET和POST）
        filter_conditions = request.args.get('filter') or request.form.get('filter')
        
        if not db_name or not table_name:
            return jsonify({
                'code': 400,
                'data': None,
                'msg': '数据库名称和表格名称不能为空'
            })
        
        # 验证数据库
        if not DatabaseManager.validate_database(db_name):
            return jsonify({
                'code': 404,
                'data': None,
                'msg': '数据库不存在或无效'
            })
        
        # 获取数据库路径
        db_path = DatabaseManager.get_database_path(db_name)
        
        with SQLiteDatabase(db_path) as db:
            # 检查表格是否存在
            tables = db.get_tables()
            if table_name not in tables:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格不存在'
                })
            
            # 解析筛选条件
            where_clause = ""
            params = []
            if filter_conditions:
                try:
                    where_clause, params = parse_filter_conditions(filter_conditions)
                except ValueError as e:
                    return jsonify({
                        'code': 400,
                        'data': None,
                        'msg': str(e)
                    })
            
            # 构建自定义查询以支持条件筛选
            if where_clause:
                # 获取表结构以确定所有列
                table_info = db.execute_query(f"PRAGMA table_info({table_name})")
                columns = [col['name'] for col in table_info]
                columns_str = ", ".join(columns)
                
                # 构建查询语句
                query = f"SELECT {columns_str} FROM {table_name} WHERE {where_clause}"
                
                # 执行查询
                data = db.execute_query(query, params)
                result = {'data': data}
            else:
                # 获取所有数据（不分页）
                result = db.get_table_data(
                    table_name=table_name,
                    page=1,
                    limit=100000,  # 设置一个较大的值以获取所有数据
                    order_by=None,
                    order_dir='ASC'
                )
            
            # 根据请求格式导出数据
            if not result['data']:
                return jsonify({
                    'code': 404,
                    'data': None,
                    'msg': '表格中没有数据'
                })
                
            if export_format.lower() == 'excel' or export_format.lower() == 'xlsx':
                # Excel格式导出
                import pandas as pd
                from io import BytesIO
                
                # 创建DataFrame
                df = pd.DataFrame(result['data'])
                
                # 创建Excel文件
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 写入数据，设置工作表名称
                    df.to_excel(writer, sheet_name=table_name[:31], index=False)  # Excel工作表名称最多31个字符
                    
                    # 获取工作表
                    worksheet = writer.sheets[table_name[:31]]
                    
                    # 自动调整列宽
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter  # 获取列字母
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 50)  # 最大宽度限制为50
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                
                output.seek(0)
                
                # 返回Excel响应
                # 导入URL编码模块（使用Python标准库）
                from urllib.parse import quote
                
                @after_this_request
                def add_headers(response):
                    # 只使用ASCII安全的文件名，避免任何编码问题
                    response.headers['Content-Disposition'] = 'attachment; filename="data_export.xlsx"'
                    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    return response
                return output.getvalue()
            elif export_format.lower() == 'json':
                # JSON格式导出
                # 使用URL编码处理文件名（使用Python标准库）
                from urllib.parse import quote
                
                @after_this_request
                def add_headers(response):
                    # 只使用ASCII安全的文件名，避免任何编码问题
                    response.headers['Content-Disposition'] = 'attachment; filename="data_export.json"'
                    response.headers['Content-Type'] = 'application/json; charset=utf-8'
                    return response
                return jsonify(result['data'])
            elif export_format.lower() == 'csv':
                # CSV格式导出
                import csv
                from io import StringIO
                
                # 创建CSV内容
                output = StringIO()
                writer = csv.writer(output, encoding='utf-8')
                
                # 写入表头
                headers = list(result['data'][0].keys())
                writer.writerow(headers)
                
                # 写入数据
                for row in result['data']:
                    writer.writerow([row[header] for header in headers])
                
                # 返回CSV响应
                # 使用URL编码处理文件名（使用Python标准库）
                from urllib.parse import quote
                
                @after_this_request
                def add_headers(response):
                    # 只使用ASCII安全的文件名，避免任何编码问题
                    response.headers['Content-Disposition'] = 'attachment; filename="data_export.csv"'
                    response.headers['Content-Type'] = 'text/csv; charset=utf-8'
                    return response
                return output.getvalue()
            else:
                return jsonify({
                    'code': 400,
                    'data': None,
                    'msg': '不支持的导出格式，请使用excel、json或csv'
                })
    except Exception as e:
        # 返回错误页面而不是JSON，因为这是在新窗口中打开的
        import traceback
        error_info = traceback.format_exc()
        return render_template('error.html', 
                            message=f'导出失败: {str(e)}',
                            error_code=500,
                            error_details=error_info), 500

@workdata_bp.route('/api/age_distribution')
@login_required
def age_distribution_api():
    """
    获取年龄区间分布统计API
    """
    # 获取请求参数，提供默认值
    db_name = request.args.get('db', '通讯录.db')
    # 为表格名称和生日字段提供默认值
    table_name = request.args.get('table', '通讯录')
    birthday_field = request.args.get('birthday_field', 'date')
    
    # 调用独立的年龄统计模块，传递所有必要参数
    return get_age_distribution(db_name=db_name, table_name=table_name, birthday_field=birthday_field)

# 年龄统计页面路由
@workdata_bp.route('/age_statistics')
@login_required
def age_statistics_page():
    """年龄分布统计页面"""
    return render_template('age_statistics.html', user=session['user'])

# 根路由 - 添加多种形式以避免重定向问题
@workdata_bp.route('/')
@workdata_bp.route('/index')
@login_required
def index():
    """首页 - 显示数据库表格列表"""
    return render_template('index.html', user=session['user'])

# 错误处理
@workdata_bp.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return render_template('error.html', 
                         message='页面不存在',
                         error_code=404), 404

@workdata_bp.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('error.html', 
                         message='服务器内部错误',
                         error_code=500), 500

# 如果直接运行此文件
if __name__ == '__main__':
    from flask import Flask
    
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config['SECRET_KEY'] = 'workdata_secret_key'
    # 添加url_prefix以确保路由正确匹配访问提示
    app.register_blueprint(workdata_bp, url_prefix='/workdata')
    
    print("WorkData应用独立运行模式")
    print("访问地址: http://localhost:5000/workdata/")
    print("按 Ctrl+C 停止服务")
    
    app.run(host='127.0.0.1', port=5000, debug=True)