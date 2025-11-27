# -*- coding: utf-8 -*-

# Author: 一根鱼骨棒 Email 775639471@qq.com
# Date: 2025-10-30 22:00:00
# LastEditTime: 2025-11-05 08:54:17
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
        # 确保模板加载器相关属性已初始化
        if not hasattr(app, '_blueprint_template_loaders'):
            app._blueprint_template_loaders = {}
        if not hasattr(app, '_blueprint_template_dirs'):
            app._blueprint_template_dirs = {}
        # 保存集成应用信息到app对象，供动态加载器使用
        if not hasattr(app, '_integrated_apps'):
            app._integrated_apps = {}
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
                self._update_template_loader(app, blueprint, template_path)
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
            
            # 同时保存到app对象，供动态加载器使用
            if hasattr(app, '_integrated_apps'):
                app._integrated_apps[blueprint.name] = self.integrated_apps[blueprint.name]
            
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
    
    def _update_template_loader(self, app: Flask, blueprint, template_path: str):
        """
        更新Flask应用的模板加载器，实现严格的蓝图模板隔离
        确保每个蓝图只加载自己的模板目录，不加载其他蓝图或主应用的模板
        
        Args:
            app: 主Flask应用实例
            blueprint: 当前集成的蓝图对象
            template_path: 模板目录路径
        """
        # 获取当前正在集成的蓝图名称
        current_blueprint_name = blueprint.name
        
        # 为每个蓝图创建独立的模板目录映射
        if not hasattr(app, '_blueprint_template_dirs'):
            app._blueprint_template_dirs = {}
        
        # 将当前蓝图的模板目录添加到映射中
        if os.path.exists(template_path):
            app._blueprint_template_dirs[current_blueprint_name] = template_path
            self.log(f"为蓝图 '{current_blueprint_name}' 设置专属模板目录: {template_path}")
        
        # 为当前蓝图创建只包含自己模板目录的加载器
        if not hasattr(app, '_blueprint_template_loaders'):
            app._blueprint_template_loaders = {}
        
        if os.path.exists(template_path):
            # 为当前蓝图创建专属的文件系统加载器，只包含自己的模板目录
            app._blueprint_template_loaders[current_blueprint_name] = FileSystemLoader([template_path])
            self.log(f"为蓝图 '{current_blueprint_name}' 创建专属模板加载器，仅包含自己的模板目录")
        
        # 实现一个动态的模板加载器，根据当前蓝图返回对应的模板加载器
        # 这是实现严格模板隔离的关键
        if not hasattr(app, '_original_jinja_loader'):
            # 保存原始加载器以备后用
            app._original_jinja_loader = app.jinja_loader
            
            # 创建一个新的动态加载器类
            class DynamicBlueprintTemplateLoader:
                def __init__(self, app_instance, integration_service):
                    self.app = app_instance
                    self.integration_service = integration_service  # 存储对集成服务的引用
                    
                def get_source(self, environment, template):
                    from flask import request, current_app
                    import jinja2
                    
                    # 尝试从请求上下文确定当前蓝图
                    blueprint_name = None
                    if request and hasattr(request, 'blueprint') and request.blueprint:
                        blueprint_name = request.blueprint
                        self.log(f"【模板加载】从请求上下文识别蓝图: {blueprint_name}")
                    else:
                        # 如果无法从请求上下文确定，尝试通过URL路径判断
                        path = request.path if request else ''
                        for name, info in self.app._integrated_apps.items():
                            if info['url_prefix'] and path.startswith(info['url_prefix']):
                                blueprint_name = name
                                self.log(f"【模板加载】通过URL路径识别蓝图: {blueprint_name} (路径: {path})")
                                break
                    
                    # 如果找到蓝图且有对应的专属加载器
                    if blueprint_name and hasattr(self.app, '_blueprint_template_loaders'):
                        blueprint_loader = self.app._blueprint_template_loaders.get(blueprint_name)
                        if blueprint_loader:
                            try:
                                self.log(f"【模板加载】使用蓝图 '{blueprint_name}' 的专属加载器加载模板: {template}")
                                return blueprint_loader.get_source(environment, template)
                            except jinja2.TemplateNotFound:
                                self.log(f"【模板加载】错误 - 模板 '{template}' 在蓝图 '{blueprint_name}' 的模板目录中未找到")
                                # 只在当前蓝图的模板目录中查找，不回退到其他目录
                                raise jinja2.TemplateNotFound(f"模板 '{template}' 不存在于蓝图 '{blueprint_name}' 的模板目录中")
                    
                    # 如果没有找到蓝图，使用原始加载器
                    if self.app._original_jinja_loader:
                        return self.app._original_jinja_loader.get_source(environment, template)
                    
                    raise jinja2.TemplateNotFound(template)
                
                def list_templates(self):
                    # 返回一个空列表，因为我们不想让Flask扫描所有模板目录
                    return []
                
                def log(self, message):
                    # 使用AppIntegrationService的日志记录
                    if self.integration_service:
                        self.integration_service.log(message)
            
            # 创建动态加载器实例时传递当前AppIntegrationService实例
            
            # 将动态加载器设置为应用的jinja_loader
            app.jinja_loader = DynamicBlueprintTemplateLoader(app, self)
            self.log("已设置动态蓝图模板加载器，实现严格的模板隔离")
        
        # 启用模板自动重载和调试
        app.config['TEMPLATES_AUTO_RELOAD'] = True
        app.config['EXPLAIN_TEMPLATE_LOADING'] = True
        
        self.log(f"更新模板加载器 - 蓝图 '{current_blueprint_name}' 的专属模板加载已配置")
        
    def _create_blueprint_template_link(self, blueprint, template_path):
        """
        为蓝图创建模板目录链接，确保蓝图可以正确加载自己的模板
        """
        # 保存蓝图的名称和模板目录路径
        blueprint_name = blueprint.name
        
        # 不设置蓝图的template_folder，避免Flask默认的模板查找机制
        # 我们将完全依赖自定义的DynamicBlueprintTemplateLoader来处理模板加载
        
        # 添加一个自定义的模板渲染函数，确保每个蓝图只使用自己的模板
        def custom_render_template(*args, **kwargs):
            """
            增强版模板渲染函数，确保每个蓝图只使用自己的模板目录
            不会尝试加载其他蓝图或主应用的模板
            """
            from flask import current_app
            from jinja2 import TemplateNotFound
            
            # 获取模板名称
            template_name = args[0]
            self.log(f"【模板渲染】蓝图 '{blueprint_name}' 尝试渲染模板: {template_name}")
            
            # 只从当前蓝图的专属模板目录中查找模板
            try:
                # 获取当前蓝图的专属加载器
                if hasattr(current_app, '_blueprint_template_loaders'):
                    blueprint_loader = current_app._blueprint_template_loaders.get(blueprint_name)
                    
                    if blueprint_loader:
                        # 尝试加载模板
                        source, filename, uptodate = blueprint_loader.get_source(current_app.jinja_env, template_name)
                        
                        # 编译并渲染模板
                        template = current_app.jinja_env.from_string(source)
                        self.log(f"【模板渲染】成功 - 从蓝图 '{blueprint_name}' 的专属模板目录加载: {template_name}")
                        return template.render(**kwargs)
                
                # 如果专属加载器不存在，抛出明确的错误
                raise TemplateNotFound(f"模板 '{template_name}' 不存在于蓝图 '{blueprint_name}' 的模板目录中")
                
            except TemplateNotFound as e:
                # 明确记录只查找了当前蓝图的模板
                self.log(f"【模板渲染】失败 - 模板 '{template_name}' 不存在于蓝图 '{blueprint_name}' 的模板目录中", 'error')
                raise
            except Exception as e:
                self.log(f"【模板渲染】失败 - 渲染模板 '{template_name}' 时出错: {str(e)}", 'error')
                raise
        
        # 替换蓝图的render_template方法
        blueprint.render_template = custom_render_template
    
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