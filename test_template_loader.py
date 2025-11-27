import os
import sys
sys.path.append('d:\\code\\EarthOnline\\server')

from function.AppIntegrationService import AppIntegrationService
from flask import Flask
from jinja2 import FileSystemLoader

def test_template_loader():
    """测试模板加载器的优先级设置"""
    app = Flask(__name__)
    app.config['DEBUG'] = True
    
    # 创建AppIntegrationService实例
    app_integration = AppIntegrationService()
    
    # 测试route模块的模板目录
    route_template_path = 'd:\\code\\EarthOnline\\server\\APP\\route\\templates'
    
    print(f"测试集成route模块的模板目录: {route_template_path}")
    # 手动调用_update_template_loader方法
    app_integration._update_template_loader(app, route_template_path)
    
    # 打印当前模板搜索路径
    if hasattr(app, 'jinja_loader') and hasattr(app.jinja_loader, 'searchpath'):
        print("\n当前模板搜索顺序:")
        for i, path in enumerate(app.jinja_loader.searchpath, 1):
            print(f"{i}. {path}")
    else:
        print("\n未找到有效的模板加载器")
    
    # 测试car_park模块的模板目录
    print(f"\n测试集成car_park模块的模板目录")
    car_park_template_path = 'd:\\code\\EarthOnline\\server\\APP\\car_park\\templates'
    app_integration._update_template_loader(app, car_park_template_path)
    
    # 再次打印模板搜索路径
    if hasattr(app, 'jinja_loader') and hasattr(app.jinja_loader, 'searchpath'):
        print("\n集成后的模板搜索顺序:")
        for i, path in enumerate(app.jinja_loader.searchpath, 1):
            print(f"{i}. {path}")
    
    print("\n测试完成。现在route模块集成时应该优先加载自己的模板目录")

if __name__ == "__main__":
    test_template_loader()