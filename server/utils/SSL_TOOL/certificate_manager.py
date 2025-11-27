"""
Let's Encrypt 证书管理脚本
用于快速启动、配置和管理证书服务
"""
import os
import sys
import json
import argparse
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入证书服务
from CertificateService import certificate_service

def setup_logger():
    """设置日志记录"""
    import logging
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'certificate_manager.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger('CertificateManager')

def load_config(config_file=None):
    """加载配置文件"""
    if config_file is None:
        # 默认配置文件路径
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificate_config.json')
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
    
    # 默认配置
    return {
        "domain": "duonline.top",
        "email": "775639471@qq.com",
        "webroot_path": os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'),
        "nginx_config_path": os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'resource', 'Tools', 'nginx.conf'),
        "auto_restart_nginx": True
    }

def save_config(config, config_file=None):
    """保存配置到文件"""
    if config_file is None:
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'certificate_config.json')
    
    try:
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        logger.info(f"配置已保存到: {config_file}")
        return True
    except Exception as e:
        logger.error(f"保存配置失败: {str(e)}")
        return False

def configure_service(args):
    """配置证书服务"""
    # 加载现有配置
    config = load_config(args.config)
    
    # 更新配置
    if args.domain:
        config['domain'] = args.domain
        config['domains'] = [args.domain, f'www.{args.domain}']
    
    if args.email:
        config['email'] = args.email
    
    if args.webroot:
        config['webroot_path'] = args.webroot
    
    if args.nginx_config:
        config['nginx_config_path'] = args.nginx_config
    
    if args.auto_restart is not None:
        config['auto_restart_nginx'] = args.auto_restart
    
    # 保存配置
    save_config(config, args.config)
    
    # 应用配置到服务
    certificate_service.configure(**config)
    logger.info("证书服务配置已更新")
    
    # 显示当前配置
    print("当前配置:")
    for key, value in config.items():
        # 邮箱显示部分隐藏
        if key == 'email' and '@' in value:
            username, domain = value.split('@')
            hidden_email = username[:2] + '*' * (len(username) - 2) + '@' + domain
            print(f"  {key}: {hidden_email}")
        else:
            print(f"  {key}: {value}")

def request_certificate(args):
    """申请新证书"""
    # 如果提供了参数，先配置
    if args.domain or args.email:
        configure_service(args)
    
    # 检查必要配置
    if not certificate_service.config['domain'] or not certificate_service.config['email']:
        logger.error("缺少必要的域名或邮箱配置")
        print("错误: 请先配置域名和邮箱")
        print("使用 'python certificate_manager.py configure --domain yourdomain.com --email youremail@example.com'")
        return False
    
    print(f"开始为域名申请证书: {certificate_service.config['domain']}")
    print(f"验证方式: webroot (路径: {certificate_service.config['webroot_path']})")
    print("正在执行certbot命令...")
    
    success = certificate_service.request_certificate()
    
    if success:
        print("\n✅ 证书申请成功!")
        print("证书已自动部署到nginx配置中")
    else:
        print("\n❌ 证书申请失败!")
        print("请查看日志了解详细错误信息")
    
    return success

def renew_certificate(args):
    """续签证书"""
    print("正在检查并续签证书...")
    
    success = certificate_service.renew_certificate()
    
    if success:
        print("\n✅ 证书续签成功!")
        print("证书已自动部署到nginx配置中")
    else:
        print("\n❌ 证书续签失败!")
        print("请查看日志了解详细错误信息")
    
    return success

def check_certificate(args):
    """检查证书状态"""
    print("正在检查证书状态...")
    
    status = certificate_service.check_certificate_status()
    
    if status:
        print("\n📋 证书状态信息:")
        print(f"  域名: {status['domain']}")
        print(f"  到期日期: {status['expiry_date']}")
        print(f"  剩余天数: {status['days_until_expiry']} 天")
        print(f"  证书有效: {'是' if status['valid'] else '否'}")
        print(f"  需要续签: {'是' if status['needs_renewal'] else '否'}")
        
        if status['days_until_expiry'] < 7:
            print("\n⚠️  警告: 证书将在7天内到期，建议尽快续签!")
        elif status['days_until_expiry'] < 30:
            print("\nℹ️  提示: 证书将在30天内到期，可以考虑续签")
        
        return True
    else:
        print("\n❌ 未找到有效证书")
        print("请使用 'python certificate_manager.py request' 命令申请新证书")
        return False

def install_as_service(args):
    """安装为Windows服务（简化版）"""
    print("此功能将创建一个批处理文件，可用于启动证书管理服务")
    
    batch_content = f'''
@echo off
set PYTHONPATH={os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))}
python "{os.path.abspath(__file__)}" start
pause
'''
    
    batch_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'start_certificate_service.bat')
    
    try:
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write(batch_content)
        
        print(f"\n✅ 启动脚本已创建: {batch_file}")
        print("使用方法:")
        print(f"1. 双击运行 '{os.path.basename(batch_file)}' 启动证书服务")
        print("2. 可以将此脚本添加到Windows任务计划程序，设置为系统启动时自动运行")
        print("\n任务计划程序设置指南:")
        print("- 打开任务计划程序 > 创建基本任务")
        print("- 触发器选择'计算机启动时'")
        print("- 操作选择'启动程序'")
        print(f"- 程序/脚本选择: {batch_file}")
        print("- 完成后，右键任务 > 属性 > 选择'使用最高权限运行'")
        return True
    except Exception as e:
        logger.error(f"创建启动脚本失败: {str(e)}")
        print(f"\n❌ 创建启动脚本失败: {str(e)}")
        return False

def start_service(args):
    """启动证书服务（作为守护进程运行）"""
    print("启动证书管理服务...")
    print("按 Ctrl+C 停止服务")
    
    # 运行一次证书检查
    success = certificate_service.run_once()
    
    # 如果证书检查/申请失败，不启动服务
    if not success:
        print("\n❌ 证书检查/申请失败，服务启动终止")
        print("请解决证书问题后再启动服务")
        return
    
    # 证书检查成功，启动定时任务
    certificate_service._start_scheduler()
    
    print("\n证书服务已启动，将定期检查证书状态")
    print(f"检查间隔: {certificate_service.config['check_interval_hours']} 小时")
    print(f"到期前 {certificate_service.config['renew_days_before_expiry']} 天自动续签")
    
    # 保持服务运行
    try:
        while True:
            import time
            time.sleep(60)  # 每分钟检查一次调度器
    except KeyboardInterrupt:
        print("\n证书服务已停止")

def main():
    """主函数"""
    global logger
    logger = setup_logger()
    
    # 加载配置
    config = load_config()
    certificate_service.configure(**config)
    
    parser = argparse.ArgumentParser(description='Let\'s Encrypt 证书管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 配置命令
    configure_parser = subparsers.add_parser('configure', help='配置证书服务')
    configure_parser.add_argument('--domain', help='主域名')
    configure_parser.add_argument('--email', help='联系邮箱')
    configure_parser.add_argument('--webroot', help='Webroot路径')
    configure_parser.add_argument('--nginx-config', help='nginx配置文件路径')
    configure_parser.add_argument('--auto-restart', action='store_true', default=None, help='启用自动重启nginx')
    configure_parser.add_argument('--no-auto-restart', dest='auto_restart', action='store_false', help='禁用自动重启nginx')
    configure_parser.add_argument('--config', help='配置文件路径')
    configure_parser.set_defaults(func=configure_service)
    
    # 申请证书命令
    request_parser = subparsers.add_parser('request', help='申请新证书')
    request_parser.add_argument('--domain', help='主域名')
    request_parser.add_argument('--email', help='联系邮箱')
    request_parser.add_argument('--webroot', help='Webroot路径')
    request_parser.add_argument('--config', help='配置文件路径')
    request_parser.set_defaults(func=request_certificate)
    
    # 续签证书命令
    renew_parser = subparsers.add_parser('renew', help='续签现有证书')
    renew_parser.set_defaults(func=renew_certificate)
    
    # 检查证书命令
    check_parser = subparsers.add_parser('check', help='检查证书状态')
    check_parser.set_defaults(func=check_certificate)
    
    # 安装服务命令
    install_parser = subparsers.add_parser('install-service', help='安装为Windows服务')
    install_parser.set_defaults(func=install_as_service)
    
    # 启动服务命令
    start_parser = subparsers.add_parser('start', help='启动证书服务')
    start_parser.set_defaults(func=start_service)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        args.func(args)
    except Exception as e:
        logger.error(f"执行命令时发生错误: {str(e)}", exc_info=True)
        print(f"\n错误: {str(e)}")
        print("请查看日志获取详细信息")

if __name__ == "__main__":
    main()