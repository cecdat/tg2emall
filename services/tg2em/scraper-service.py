#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
采集服务 - 专门负责Telegram采集任务
"""

import os
import sys
import json
import time
import signal
import argparse
import asyncio
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from typing import Dict, Any

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/scraper-service.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class ScraperService:
    """采集服务"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pid = os.getpid()
        self.start_time = datetime.now()
        self.is_scraping = False
        self.last_scrape_time = None
        self.scrape_count = 0
        
        # 导入采集相关模块
        try:
            from scrape import (
                init_mysql_pool, close_mysql_pool, 
                scrape_channel, get_config_from_db
            )
            self.scrape_module = sys.modules['scrape']
            logger.info("✅ 采集模块导入成功")
        except ImportError as e:
            logger.error(f"❌ 采集模块导入失败: {e}")
            self.scrape_module = None
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        uptime = str(datetime.now() - self.start_time).split('.')[0]
        
        return {
            'success': True,
            'data': {
                'status': 'running',
                'pid': self.pid,
                'uptime': uptime,
                'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'is_scraping': self.is_scraping,
                'last_scrape_time': self.last_scrape_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_scrape_time else None,
                'scrape_count': self.scrape_count,
                'port': self.config.get('port', '5002')
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            'success': True,
            'data': {
                'api_id': self.config.get('api_id', ''),
                'api_hash': self.config.get('api_hash', ''),
                'phone_number': self.config.get('phone_number', ''),
                'mysql_host': self.config.get('mysql_host', ''),
                'mysql_database': self.config.get('mysql_database', ''),
                'mysql_user': self.config.get('mysql_user', ''),
                'mysql_password': '***',  # 隐藏密码
                'port': self.config.get('port', '5002')
            }
        }
    
    async def start_scraping(self) -> Dict[str, Any]:
        """开始采集任务"""
        try:
            if self.is_scraping:
                return {
                    'success': False,
                    'message': '采集任务已在运行中'
                }
            
            if not self.scrape_module:
                return {
                    'success': False,
                    'message': '采集模块未正确加载'
                }
            
            self.is_scraping = True
            logger.info("🚀 开始采集任务...")
            
            # 初始化数据库连接
            await self.scrape_module.init_mysql_pool()
            
            # 初始化并登录 Telegram 客户端
            logger.info("🔐 初始化 Telegram 客户端...")
            await self.scrape_module.init_telegram_client()
            logger.info("✅ Telegram 客户端初始化成功")
            
            # 执行采集任务
            await self.scrape_module.scrape_channel()
            
            self.last_scrape_time = datetime.now()
            self.scrape_count += 1
            
            logger.info("✅ 采集任务完成")
            
            return {
                'success': True,
                'message': '采集任务完成',
                'scrape_time': self.last_scrape_time.strftime('%Y-%m-%d %H:%M:%S'),
                'scrape_count': self.scrape_count
            }
            
        except Exception as e:
            logger.error(f"❌ 采集任务失败: {e}")
            return {
                'success': False,
                'message': f'采集任务失败: {str(e)}'
            }
        finally:
            self.is_scraping = False
    
    def stop_scraping(self) -> Dict[str, Any]:
        """停止采集任务"""
        try:
            if not self.is_scraping:
                return {
                    'success': False,
                    'message': '采集任务未运行'
                }
            
            self.is_scraping = False
            logger.info("🛑 采集任务已停止")
            
            return {
                'success': True,
                'message': '采集任务已停止'
            }
            
        except Exception as e:
            logger.error(f"❌ 停止采集任务失败: {e}")
            return {
                'success': False,
                'message': f'停止采集任务失败: {str(e)}'
            }

# 全局采集服务实例
scraper_service = None

@app.route('/api/scraper/status', methods=['GET'])
def handle_status():
    """处理状态查询"""
    if not scraper_service:
        return jsonify({
            'success': False,
            'message': '采集服务未初始化'
        })
    
    return jsonify(scraper_service.get_status())

@app.route('/api/scraper/config', methods=['GET'])
def handle_config():
    """处理配置查询"""
    if not scraper_service:
        return jsonify({
            'success': False,
            'message': '采集服务未初始化'
        })
    
    return jsonify(scraper_service.get_config())

@app.route('/api/scraper/start', methods=['POST'])
def handle_start_scraping():
    """处理采集任务启动"""
    if not scraper_service:
        return jsonify({
            'success': False,
            'message': '采集服务未初始化'
        })
    
    # 在后台线程中运行异步采集任务
    import threading
    
    def run_scraping():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(scraper_service.start_scraping())
            logger.info(f"采集任务结果: {result}")
        except Exception as e:
            logger.error(f"采集任务异常: {e}")
        finally:
            loop.close()
    
    thread = threading.Thread(target=run_scraping)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': '采集任务已启动'
    })

@app.route('/api/scraper/stop', methods=['POST'])
def handle_stop_scraping():
    """处理采集任务停止"""
    if not scraper_service:
        return jsonify({
            'success': False,
            'message': '采集服务未初始化'
        })
    
    return jsonify(scraper_service.stop_scraping())

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        'status': 'healthy',
        'service': 'tg2em-scraper',
        'timestamp': datetime.now().isoformat(),
        'pid': os.getpid()
    })

@app.route('/')
def index():
    """服务信息页面"""
    if not scraper_service:
        return jsonify({
            'success': False,
            'message': '采集服务未初始化'
        })
    
    status = scraper_service.get_status()
    config = scraper_service.get_config()
    
    return f'''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>tg2em 采集服务</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .status {{ padding: 15px; margin: 10px 0; border-radius: 5px; background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }}
            .info {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔄 tg2em 采集服务</h1>
            <div class="status">
                <strong>服务状态:</strong> 运行中<br>
                <strong>PID:</strong> {status['data']['pid']}<br>
                <strong>运行时间:</strong> {status['data']['uptime']}<br>
                <strong>采集状态:</strong> {'运行中' if status['data']['is_scraping'] else '空闲'}<br>
                <strong>采集次数:</strong> {status['data']['scrape_count']}
            </div>
            <div class="info">
                <h3>服务信息</h3>
                <p><strong>服务名称:</strong> tg2em Scraper Service</p>
                <p><strong>版本:</strong> 2.0.0</p>
                <p><strong>端口:</strong> {config['data']['port']}</p>
                <p><strong>架构:</strong> 双服务架构 - 采集服务</p>
            </div>
        </div>
    </body>
    </html>
    '''

def signal_handler(signum, frame):
    """信号处理器"""
    logger.info("🛑 采集服务正在关闭...")
    sys.exit(0)

def main():
    """主函数"""
    global scraper_service
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='tg2em 采集服务')
    parser.add_argument('--api-id', default=os.getenv('API_ID', ''), help='Telegram API ID')
    parser.add_argument('--api-hash', default=os.getenv('API_HASH', ''), help='Telegram API Hash')
    parser.add_argument('--phone', default=os.getenv('PHONE_NUMBER', ''), help='Phone Number')
    parser.add_argument('--mysql-host', default=os.getenv('MYSQL_HOST', 'mysql'), help='MySQL Host')
    parser.add_argument('--mysql-database', default=os.getenv('MYSQL_DATABASE', 'tg2em'), help='MySQL Database')
    parser.add_argument('--mysql-user', default=os.getenv('MYSQL_USER', 'tg2emall'), help='MySQL User')
    parser.add_argument('--mysql-password', default=os.getenv('MYSQL_PASSWORD', 'tg2emall'), help='MySQL Password')
    parser.add_argument('--port', default=os.getenv('SCRAPER_PORT', '5002'), help='Service Port')
    
    args = parser.parse_args()
    
    # 验证必需配置
    if not args.api_id or not args.api_hash or not args.phone:
        logger.error("❌ 缺少必需配置: API_ID, API_HASH, PHONE_NUMBER")
        sys.exit(1)
    
    # 创建配置
    config = {
        'api_id': args.api_id,
        'api_hash': args.api_hash,
        'phone_number': args.phone,
        'mysql_host': args.mysql_host,
        'mysql_database': args.mysql_database,
        'mysql_user': args.mysql_user,
        'mysql_password': args.mysql_password,
        'port': args.port
    }
    
    # 创建采集服务实例
    scraper_service = ScraperService(config)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("🚀 tg2em采集服务启动中...")
    logger.info(f"📊 采集服务PID: {scraper_service.pid}")
    logger.info(f"📡 服务端口: {config['port']}")
    logger.info(f"📱 Telegram配置: API_ID={args.api_id[:4]}***, Phone={args.phone}")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=int(config['port']), debug=False)

if __name__ == '__main__':
    main()
