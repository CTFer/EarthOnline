# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-10-30 22:00:00
# LastEditTime: 2025-10-31 15:54:59
# LastEditors: 一根鱼骨棒
# Description: 本开源代码使用GPL 3.0协议
# Software: VScode
# Copyright 2025 迷舍

# -*- coding: utf-8 -*-
"""
应用集成服务
提供统一的方式来集成不同的应用模块到主Flask应用中
"""
import os
import sys
import importlib
import traceback
from typing import Dict, List, Tuple, Optional
from jinja2 import FileSystemLoader
from flask import Flask


class AppIntegrationService:
    """应用集成服务类"""
    
    def __init__(self):
        self.logger = None
        self.integrated_apps = {}
    
    def set_logger(self, logger):
        """设置日志记录器"""
        self.logger = logger
    
    def log(self, message, level='info'):
        """统一的日志记录方法"""
        if self.logger:
            log_func = getattr(self.logger, level, self.logger.info)
            log_func(message)
        else:
            print(message)
    
    def integrate_app(self, 
                     app: Flask,
                     app_name: str,
                     app_path: str,
                     module_name: str = 'app',
                     blueprint_name: str = 'bp',
                     url_prefix: str = None,
                     template_dir: str = 'templates',
                     static_dir: str = 'static',
                     app_config: Dict = None) -> bool:
        """
        集成单个应用模块到主Flask应用
        
        Args:
            app: 主Flask应用实例
            app_name: 应用名称，用于标识和日志
            app_path: 应用的相对路径或绝对路径
            module_name: 应用的主模块名称，默认为'app'
            blueprint_name: 蓝图对象的变量名，默认为'bp'
            url_prefix: 蓝图的URL前缀，如果为None则尝试从蓝图中获取
            template_dir: 应用的模板目录名，默认为'templates'
            static_dir: 应用的静态文件目录名，默认为'static'
            app_config: 应用的配置字典
            
        Returns:
            bool: 是否集成成功
        """
        try:
            self.log(f"开始集成应用: {app_name}")
            
            # 确保app_path是绝对路径
            if not os.path.isabs(app_path):
                current_dir = os.path.dirname(os.path.abspath(__file__))
                app_path = os.path.normpath(os.path.join(current_dir, '..', app_path))
            
            # 验证应用目录是否存在
            if not os.path.exists(app_path):
                self.log(f"应用目录不存在: {app_path}", 'error')
                return False
            
            # 添加应用路径到Python路径
            app_parent_dir = os.path.dirname(app_path)
            if app_parent_dir not in sys.path:
                sys.path.insert(0, app_parent_dir)
            
            # 构建模块导入路径
            module_path = os.path.join(app_path, f"{module_name}.py")
            if not os.path.exists(module_path):
                self.log(f"应用模块文件不存在: {module_path}", 'error')
                return False
            
            # 导入应用模块
            app_name_from_path = os.path.basename(app_path)
            import_path = f"APP.{app_name_from_path}.{module_name}"
            
            self.log(f"正在导入应用模块: {import_path}")
            app_module = importlib.import_module(import_path)
            
            # 获取蓝图对象
            if not hasattr(app_module, blueprint_name):
                self.log(f"蓝图对象 '{blueprint_name}' 在模块中不存在", 'error')
                return False
            
            blueprint = getattr(app_module, blueprint_name)
            self.log(f"成功获取蓝图: {blueprint.name}")
            
            # 配置URL前缀
            if url_prefix and not blueprint.url_prefix:
                blueprint.url_prefix = url_prefix
            
            # 配置模板路径
            template_path = os.path.join(app_path, template_dir)
            if os.path.exists(template_path):
                # 创建蓝图模板链接，确保模板目录正确配置
                self._create_blueprint_template_link(blueprint, template_path)
                # 更新应用的模板加载器
                self._update_template_loader(app, template_path)
                self.log(f"添加模板目录: {template_path}")
            
            # 配置静态文件路径
            static_path = os.path.join(app_path, static_dir)
            if os.path.exists(static_path):
                # 强制设置蓝图的静态文件夹和URL路径，确保蓝图可以正确访问自己的静态资源
                blueprint.static_folder = static_path
                
                # 正确设置静态URL路径，避免与蓝图url_prefix重复
                # 由于蓝图已经有url_prefix，静态URL应该只使用'/static'
                # 这样Flask会自动将蓝图的url_prefix添加到前面
                blueprint.static_url_path = '/static'
                
                self.log(f"配置静态文件目录: {static_path}")
                self.log(f"静态资源URL路径: {blueprint.static_url_path}")
            
            # 注册蓝图
            app.register_blueprint(blueprint)
            self.log(f"成功注册蓝图: {blueprint.name}")
            
            # 保存集成信息
            self.integrated_apps[blueprint.name] = {
                'app_name': app_name,
                'blueprint': blueprint,
                'path': app_path,
                'url_prefix': blueprint.url_prefix or '',
                'template_dir': template_path if os.path.exists(template_path) else None,
                'static_dir': static_path if os.path.exists(static_path) else None
            }
            
            # 打印集成信息
            self._print_integration_info(app_name, blueprint)
            
            return True
            
        except ImportError as e:
            self.log(f"导入错误: {str(e)}", 'error')
            self.log(traceback.format_exc(), 'error')
            return False
        except Exception as e:
            self.log(f"集成应用 '{app_name}' 失败: {str(e)}", 'error')
            self.log(traceback.format_exc(), 'error')
            return False
    
    def _update_template_loader(self, app: Flask, template_path: str):
        """
        更新Flask应用的模板加载器，添加新的模板目录，并确保支持蓝图命名空间
        """
        # 1. 收集所有需要的模板目录
        all_template_dirs = []
        
        # 添加主应用的模板目录
        if app.template_folder:
            if os.path.isabs(app.template_folder):
                main_template_dir = app.template_folder
            else:
                main_template_dir = os.path.join(app.root_path, app.template_folder)
            if os.path.exists(main_template_dir) and main_template_dir not in all_template_dirs:
                all_template_dirs.append(main_template_dir)
        
        # 添加新应用的模板目录
        if os.path.exists(template_path) and template_path not in all_template_dirs:
            all_template_dirs.append(template_path)
        
        # 添加蓝图命名空间目录
        # 对于蓝图命名空间 'route/index.html'，需要确保其存在于 'templates/route/index.html'
        blueprint_name = os.path.basename(os.path.dirname(template_path))  # 获取蓝图名
        parent_templates_dir = os.path.dirname(template_path)  # 父目录
        namespace_dir = os.path.join(parent_templates_dir, 'templates', blueprint_name)
        if os.path.exists(namespace_dir) and namespace_dir not in all_template_dirs:
            all_template_dirs.append(namespace_dir)
        
        # 2. 确保目录列表包含所有已有的模板目录
        if hasattr(app, 'jinja_loader') and isinstance(app.jinja_loader, FileSystemLoader):
            for existing_dir in app.jinja_loader.searchpath:
                if os.path.exists(existing_dir) and existing_dir not in all_template_dirs:
                    all_template_dirs.append(existing_dir)
        
        # 3. 只在有变化时更新加载器
        if all_template_dirs:
            # 排序目录，确保主应用模板目录优先
            main_template_dir = None
            for i, dir_path in enumerate(all_template_dirs):
                if app.template_folder and app.template_folder in dir_path:
                    main_template_dir = all_template_dirs.pop(i)
                    break
            if main_template_dir:
                all_template_dirs.insert(0, main_template_dir)
            
            current_dirs = set(app.jinja_loader.searchpath) if hasattr(app, 'jinja_loader') and isinstance(app.jinja_loader, FileSystemLoader) else set()
            new_dirs = set(all_template_dirs)
            
            if current_dirs != new_dirs:
                app.jinja_loader = FileSystemLoader(all_template_dirs)
                
                # 启用模板自动重载（开发环境）
                app.config['TEMPLATES_AUTO_RELOAD'] = True
                app.config['EXPLAIN_TEMPLATE_LOADING'] = True  # 启用模板加载调试
                
                self.log(f"更新模板加载器 - 已添加 {len(all_template_dirs)} 个模板目录")
                self.log(f"模板搜索顺序: {all_template_dirs}")
        else:
            self.log(f"警告: 未找到有效的模板目录")
    
    def _create_blueprint_template_link(self, blueprint, template_path):
        """
        为蓝图创建模板目录链接，确保蓝图能正确加载自己的模板
        这是一个辅助方法，用于确保蓝图的命名空间模板加载正常工作
        """
        # 强制设置蓝图的template_folder为绝对路径
        if os.path.exists(template_path):
            # 设置绝对路径的模板目录
            blueprint.template_folder = template_path
            
            # 确保蓝图的import_name是正确的模块路径
            if not hasattr(blueprint, '_got_first_request'):
                blueprint._got_first_request = False
                
            self.log(f"蓝图 '{blueprint.name}' 使用绝对路径模板目录: {blueprint.template_folder}")
            
            # 创建命名空间目录结构，确保模板可以通过命名空间加载
            namespace_template_dir = os.path.join(os.path.dirname(template_path), 'templates', blueprint.name)
            if not os.path.exists(namespace_template_dir) and os.path.exists(template_path):
                try:
                    # 如果命名空间目录不存在，创建符号链接或确保文件存在于正确位置
                    # 检查是否存在与蓝图同名的子目录
                    if not os.path.exists(namespace_template_dir):
                        self.log(f"警告: 命名空间模板目录不存在: {namespace_template_dir}")
                        # 但不创建实际目录，因为这可能会导致权限问题
                except Exception as e:
                    self.log(f"创建命名空间模板目录失败: {str(e)}", 'error')
        else:
            self.log(f"警告: 蓝图 '{blueprint.name}' 的模板目录不存在: {template_path}")
    
    def _print_integration_info(self, app_name: str, blueprint):
        """
        打印应用集成信息
        """
        url_prefix = blueprint.url_prefix or ''
        info = [
            f"\n{'=' * 60}",
            f"应用 '{app_name}' 集成信息:",
            f"  蓝图名称: {blueprint.name}",
            f"  URL前缀: {url_prefix}",
            f"  模板目录: {blueprint.template_folder or '未设置'}",
            f"  静态目录: {blueprint.static_folder or '未设置'}",
            f"  默认URL: http://localhost:8000{url_prefix}",
            f"{'=' * 60}\n"
        ]
        
        for line in info:
            self.log(line)
    
    def integrate_multiple_apps(self, app: Flask, app_configs: List[Dict]) -> Tuple[int, int]:
        """
        批量集成多个应用
        
        Args:
            app: 主Flask应用实例
            app_configs: 应用配置列表，每个配置是一个字典
            
        Returns:
            Tuple[int, int]: (成功数量, 失败数量)
        """
        success_count = 0
        fail_count = 0
        
        for config in app_configs:
            if self.integrate_app(app, **config):
                success_count += 1
            else:
                fail_count += 1
        
        self.log(f"批量集成完成 - 成功: {success_count}, 失败: {fail_count}")
        return success_count, fail_count
    
    def get_integrated_apps(self) -> Dict:
        """
        获取已集成的应用列表
        
        Returns:
            Dict: 已集成应用的信息字典
        """
        return self.integrated_apps


# 创建全局应用集成服务实例
app_integration_service = AppIntegrationService()