#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
采集服务管理服务 - 负责控制采集服务的启停和配置管理
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from typing import Dict, Any, Optional

app = Flask(__name__)

class ScraperManagementService:
    """采集服务管理服务"""
    
    def __init__(self):
        self.scraper_process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.start_time = None
        self.pid = os.getpid()
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """从环境变量和数据库加载配置"""
        # 基础配置从环境变量获取
        config = {
            'api_id': os.getenv('API_ID', ''),
            'api_hash': os.getenv('API_HASH', ''),
            'phone_number': os.getenv('PHONE_NUMBER', ''),
            'mysql_host': os.getenv('MYSQL_HOST', 'mysql'),
            'mysql_database': os.getenv('MYSQL_DATABASE', 'tg2em'),
            'mysql_user': os.getenv('MYSQL_USER', 'tg2emall'),
            'mysql_password': os.getenv('MYSQL_PASSWORD', 'tg2emall'),
            'scraper_port': os.getenv('SCRAPER_PORT', '5002'),
            'management_port': os.getenv('MANAGEMENT_PORT', '2003'),
        }
        
        # 尝试从数据库获取Telegram配置
        try:
            import pymysql
            conn = pymysql.connect(
                host=config['mysql_host'],
                port=3306,
                user=config['mysql_user'],
                password=config['mysql_password'],
                database=config['mysql_database'],
                charset='utf8mb4'
            )
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 获取Telegram配置
            cursor.execute("""
                SELECT config_key, config_value FROM system_config 
                WHERE config_key IN ('telegram_api_id', 'telegram_api_hash', 'telegram_phone')
            """)
            results = cursor.fetchall()
            
            for result in results:
                if result['config_key'] == 'telegram_api_id':
                    config['api_id'] = result['config_value']
                elif result['config_key'] == 'telegram_api_hash':
                    config['api_hash'] = result['config_value']
                elif result['config_key'] == 'telegram_phone':
                    config['phone_number'] = result['config_value']
            
            conn.close()
            print(f"✅ 从数据库获取Telegram配置: API_ID={config['api_id'][:4]}***, Phone={config['phone_number']}")
            
        except Exception as e:
            print(f"⚠️ 从数据库获取配置失败，使用环境变量: {e}")
        
        return config
    
    def reload_config(self) -> Dict[str, Any]:
        """重新加载配置"""
        self.config = self.load_config()
        return self.config
    
    def start_scraper_service(self) -> Dict[str, Any]:
        """启动采集服务"""
        try:
            if self.is_running and self.scraper_process:
                return {
                    'success': False,
                    'message': '采集服务已在运行中'
                }
            
            # 验证配置完整性
            if not self.config['api_id'] or not self.config['api_hash']:
                print(f"❌ Telegram配置不完整:")
                print(f"   - API_ID: {'已配置' if self.config['api_id'] else '未配置'}")
                print(f"   - API_Hash: {'已配置' if self.config['api_hash'] else '未配置'}")
                print(f"   - Phone: {'已配置' if self.config['phone_number'] else '未配置'}")
                return {
                    'success': False,
                    'message': 'Telegram配置不完整，请在管理后台配置API ID和API Hash'
                }
            
            if not self.config['phone_number']:
                print(f"⚠️ 警告: 未配置手机号码，首次运行时需要验证")
            
            print(f"📋 准备启动采集服务，配置信息:")
            print(f"   - API_ID: {self.config['api_id'][:4]}***")
            print(f"   - API_Hash: {self.config['api_hash'][:4]}***")
            print(f"   - Phone: {self.config['phone_number'] or '未配置'}")
            print(f"   - MySQL: {self.config['mysql_host']}:{self.config['mysql_database']}")
            
            # 构建采集服务启动命令
            cmd = [
                'python3', 'scraper-service.py',
                '--api-id', self.config['api_id'],
                '--api-hash', self.config['api_hash'],
                '--phone', self.config['phone_number'],
                '--mysql-host', self.config['mysql_host'],
                '--mysql-database', self.config['mysql_database'],
                '--mysql-user', self.config['mysql_user'],
                '--mysql-password', self.config['mysql_password'],
                '--port', self.config['scraper_port']
            ]
            
            # 设置环境变量
            env = os.environ.copy()
            env.update({
                'API_ID': self.config['api_id'],
                'API_HASH': self.config['api_hash'],
                'PHONE_NUMBER': self.config['phone_number'],
                'MYSQL_HOST': self.config['mysql_host'],
                'MYSQL_DATABASE': self.config['mysql_database'],
                'MYSQL_USER': self.config['mysql_user'],
                'MYSQL_PASSWORD': self.config['mysql_password'],
                'SCRAPER_PORT': self.config['scraper_port']
            })
            
            # 启动采集服务（不捕获输出，让日志直接显示）
            self.scraper_process = subprocess.Popen(
                cmd,
                env=env,
                stdout=None,  # 让stdout直接输出到容器日志
                stderr=None,  # 让stderr直接输出到容器日志
                cwd='/app'
            )
            
            self.is_running = True
            self.start_time = datetime.now()
            
            print(f"✅ 采集服务启动成功，PID: {self.scraper_process.pid}")
            
            return {
                'success': True,
                'message': '采集服务启动成功',
                'pid': self.scraper_process.pid
            }
            
        except Exception as e:
            print(f"❌ 启动采集服务失败: {e}")
            return {
                'success': False,
                'message': f'启动采集服务失败: {str(e)}'
            }
    
    def stop_scraper_service(self) -> Dict[str, Any]:
        """停止采集服务"""
        try:
            if not self.is_running or not self.scraper_process:
                return {
                    'success': False,
                    'message': '采集服务未运行'
                }
            
            print("🛑 停止采集服务...")
            
            # 发送SIGTERM信号
            self.scraper_process.terminate()
            
            # 等待进程结束
            try:
                self.scraper_process.wait(timeout=10)
                print("✅ 采集服务已停止")
            except subprocess.TimeoutExpired:
                print("⚠️ 强制终止采集服务")
                self.scraper_process.kill()
                self.scraper_process.wait()
            
            self.scraper_process = None
            self.is_running = False
            self.start_time = None
            
            return {
                'success': True,
                'message': '采集服务停止成功'
            }
            
        except Exception as e:
            print(f"❌ 停止采集服务失败: {e}")
            return {
                'success': False,
                'message': f'停止采集服务失败: {str(e)}'
            }
    
    def restart_scraper_service(self) -> Dict[str, Any]:
        """重启采集服务"""
        try:
            # 先停止
            if self.is_running:
                stop_result = self.stop_scraper_service()
                if not stop_result['success']:
                    return stop_result
                time.sleep(2)  # 等待进程完全停止
            
            # 再启动
            return self.start_scraper_service()
            
        except Exception as e:
            return {
                'success': False,
                'message': f'重启采集服务失败: {str(e)}'
            }
    
    def get_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        status = 'stopped'
        pid = None
        uptime = '0s'
        
        if self.is_running and self.scraper_process:
            status = 'running'
            pid = self.scraper_process.pid
            if self.start_time:
                uptime = str(datetime.now() - self.start_time).split('.')[0]
        
        return {
            'success': True,
            'data': {
                'status': status,
                'pid': pid,
                'uptime': uptime,
                'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
                'management_pid': self.pid
            }
        }
    
    def get_config(self) -> Dict[str, Any]:
        """获取配置信息"""
        return {
            'success': True,
            'data': self.config
        }
    
    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        """更新配置"""
        try:
            # 重新从数据库加载配置
            self.config = self.load_config()
            
            # 如果采集服务正在运行，重启以应用新配置
            if self.is_running:
                print("🔄 配置已更新，重启采集服务以应用新配置...")
                threading.Timer(1.0, self.restart_scraper_service).start()
            
            return {
                'success': True,
                'message': '配置更新成功'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'配置更新失败: {str(e)}'
            }

# 创建全局管理服务实例
management_service = ScraperManagementService()

@app.route('/api/management/status', methods=['GET'])
def handle_status():
    """处理状态查询"""
    return jsonify(management_service.get_status())

@app.route('/api/management/start', methods=['POST'])
def handle_start():
    """处理启动请求"""
    return jsonify(management_service.start_scraper_service())

@app.route('/api/management/stop', methods=['POST'])
def handle_stop():
    """处理停止请求"""
    return jsonify(management_service.stop_scraper_service())

@app.route('/api/management/restart', methods=['POST'])
def handle_restart():
    """处理重启请求"""
    return jsonify(management_service.restart_scraper_service())

@app.route('/api/management/config', methods=['GET', 'POST'])
def handle_config():
    """处理配置请求"""
    if request.method == 'GET':
        return jsonify(management_service.get_config())
    elif request.method == 'POST':
        new_config = request.get_json()
        return jsonify(management_service.update_config(new_config))

@app.route('/api/management/info', methods=['GET'])
def handle_info():
    """处理信息请求"""
    info = {
        'service_name': 'tg2em Scraper Management Service',
        'version': '2.0.0',
        'management_pid': management_service.pid,
        'scraper_port': management_service.config['scraper_port'],
        'management_port': management_service.config['management_port'],
        'architecture': 'dual-service'
    }
    
    return jsonify({
        'success': True,
        'data': info
    })

@app.route('/api/scrape/start', methods=['POST'])
def handle_scrape_start():
    """处理采集任务启动请求（代理到采集服务）"""
    if not management_service.is_running:
        return jsonify({
            'success': False,
            'message': '采集服务未运行'
        })
    
    try:
        # 向采集服务发送启动请求
        import requests
        scraper_url = f"http://localhost:{management_service.config['scraper_port']}/api/scraper/start"
        
        response = requests.post(scraper_url, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'message': f'采集服务响应错误: {response.status_code}'
            })
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'message': '无法连接到采集服务'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'启动采集任务失败: {str(e)}'
        })

@app.route('/api/scrape/status', methods=['GET'])
def handle_scrape_status():
    """处理采集任务状态查询（代理到采集服务）"""
    if not management_service.is_running:
        return jsonify({
            'success': False,
            'message': '采集服务未运行'
        })
    
    try:
        # 向采集服务发送状态查询请求
        import requests
        scraper_url = f"http://localhost:{management_service.config['scraper_port']}/api/scraper/status"
        
        response = requests.get(scraper_url, timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            return jsonify(result)
        else:
            return jsonify({
                'success': False,
                'message': f'采集服务响应错误: {response.status_code}'
            })
            
    except requests.exceptions.ConnectionError:
        return jsonify({
            'success': False,
            'message': '无法连接到采集服务'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'查询采集状态失败: {str(e)}'
        })

@app.route('/')
def index():
    """管理页面"""
    return '''
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>tg2em 采集服务管理</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .status { padding: 15px; margin: 10px 0; border-radius: 5px; }
            .status.running { background: #d4edda; border: 1px solid #c3e6cb; color: #155724; }
            .status.stopped { background: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }
            .btn { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; }
            .btn-success { background: #28a745; color: white; }
            .btn-danger { background: #dc3545; color: white; }
            .btn-warning { background: #ffc107; color: black; }
            .btn-info { background: #17a2b8; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔄 tg2em 采集服务管理</h1>
            <div id="status" class="status">检查状态中...</div>
            <div>
                <button class="btn btn-success" onclick="startService()">启动采集服务</button>
                <button class="btn btn-danger" onclick="stopService()">停止采集服务</button>
                <button class="btn btn-warning" onclick="restartService()">重启采集服务</button>
                <button class="btn btn-info" onclick="refreshStatus()">刷新状态</button>
            </div>
        </div>
        
        <script>
            function refreshStatus() {
                fetch('/api/management/status')
                    .then(response => response.json())
                    .then(data => {
                        const statusDiv = document.getElementById('status');
                        if (data.success) {
                            const status = data.data.status;
                            statusDiv.className = 'status ' + status;
                            statusDiv.innerHTML = `
                                <strong>采集服务状态:</strong> ${status === 'running' ? '运行中' : '已停止'}<br>
                                ${data.data.pid ? '<strong>PID:</strong> ' + data.data.pid + '<br>' : ''}
                                ${data.data.uptime ? '<strong>运行时间:</strong> ' + data.data.uptime + '<br>' : ''}
                                <strong>管理服务PID:</strong> ${data.data.management_pid}
                            `;
                        } else {
                            statusDiv.className = 'status stopped';
                            statusDiv.innerHTML = '无法获取状态';
                        }
                    });
            }
            
            function startService() {
                fetch('/api/management/start', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        setTimeout(refreshStatus, 2000);
                    });
            }
            
            function stopService() {
                fetch('/api/management/stop', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        setTimeout(refreshStatus, 2000);
                    });
            }
            
            function restartService() {
                fetch('/api/management/restart', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        alert(data.message);
                        setTimeout(refreshStatus, 3000);
                    });
            }
            
            // 页面加载时获取状态
            window.onload = refreshStatus;
        </script>
    </body>
    </html>
    '''

def signal_handler(signum, frame):
    """信号处理器"""
    print("🛑 管理服务正在关闭...")
    management_service.stop_scraper_service()
    sys.exit(0)

if __name__ == '__main__':
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🚀 tg2em采集服务管理服务启动中...")
    print(f"📊 管理服务PID: {management_service.pid}")
    print(f"🔧 管理端口: {management_service.config['management_port']}")
    print(f"📡 采集服务端口: {management_service.config['scraper_port']}")
    
    app.run(host='0.0.0.0', port=int(management_service.config['management_port']), debug=False)
