#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
采集服务管理接口
"""

import os
import sys
import json
import signal
import subprocess
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class ScraperManager:
    """采集服务管理器"""
    
    def __init__(self):
        self.status = "stopped"
        self.pid = None
        self.start_time = None
        self.process = None
        self.config = {
            'api_id': os.environ.get('API_ID', ''),
            'api_hash': os.environ.get('API_HASH', ''),
            'mysql_host': os.environ.get('MYSQL_HOST', 'mysql'),
            'mysql_database': os.environ.get('MYSQL_DATABASE', 'tg2em'),
            'mysql_user': os.environ.get('MYSQL_USER', 'tg2emall'),
            'mysql_password': os.environ.get('MYSQL_PASSWORD', 'tg2emall'),
            'tgstate_url': os.environ.get('TGSTATE_URL', 'http://tgstate:8088')
        }
    
    def get_status(self):
        """获取服务状态"""
        if self.process and self.process.poll() is None:
            self.status = "running"
            self.pid = self.process.pid
        else:
            self.status = "stopped"
            if self.process:
                # 进程已结束但状态未更新
                try:
                    poll_result = self.process.poll()
                    if poll_result is not None:
                        # 进程已退出
                        self.process = None
                        self.pid = None
                        self.start_time = None
                except:
                    pass
        
        return {
            'status': self.status,
            'pid': self.pid,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else None,
            'message': f'采集服务状态: {self.status}'
        }
    
    def start_service(self):
        """启动采集服务"""
        if self.status == "running":
            return {'success': True, 'message': '服务已经在运行中'}
        
        try:
            # 启动采集服务进程
            self.process = subprocess.Popen([
                sys.executable, 'scrape.py'
            ], cwd='/app')
            
            self.pid = self.process.pid
            self.start_time = datetime.now()
            self.status = "running"
            
            return {'success': True, 'message': '服务启动成功', 'pid': self.pid}
            
        except Exception as e:
            return {'success': False, 'message': f'启动失败: {str(e)}'}
    
    def stop_service(self):
        """停止采集服务"""
        if self.status == "stopped":
            return {'success': True, 'message': '服务已经停止'}
        
        try:
            if self.process:
                self.process.terminate()
                # 等待进程结束
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            
            self.status = "stopped"
            self.pid = None
            self.start_time = None
            
            return {'success': True, 'message': '服务停止成功'}
            
        except Exception as e:
            return {'success': False, 'message': f'停止失败: {str(e)}'}
    
    def restart_service(self):
        """重启采集服务"""
        stop_result = self.stop_service()
        if not stop_result['success']:
            return stop_result
        
        time.sleep(2)  # 等待进程完全停止
        return self.start_service()
    
    def get_config_from_db(self):
        """从数据库获取配置"""
        try:
            import aiomysql
            import asyncio
            
            async def fetch_config():
                conn = await aiomysql.connect(
                    host=self.config['mysql_host'],
                    port=3306,
                    user=self.config['mysql_user'],
                    password=self.config['mysql_password'],
                    db=self.config['mysql_database'],
                    charset='utf8mb4'
                )
                
                cursor = await conn.cursor(aiomysql.DictCursor)
                
                # 获取Telegram相关配置
                await cursor.execute("""
                    SELECT config_key, config_value 
                    FROM system_config 
                    WHERE config_key IN ('telegram_api_id', 'telegram_api_hash', 'telegram_phone', 'scrape_channels', 'scrape_limit', 'scrape_interval')
                """)
                
                telegram_configs = await cursor.fetchall()
                
                # 获取tgState相关配置
                await cursor.execute("""
                    SELECT config_key, config_value 
                    FROM system_config 
                    WHERE config_key IN ('tgstate_token', 'tgstate_target', 'tgstate_pass', 'tgstate_mode', 'tgstate_url', 'tgstate_port')
                """)
                
                tgstate_configs = await cursor.fetchall()
                
                await cursor.close()
                conn.close()
                
                # 构建配置字典
                config_dict = {}
                for config in telegram_configs + tgstate_configs:
                    config_dict[config['config_key']] = config['config_value']
                
                return config_dict
            
            # 运行异步函数
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(fetch_config())
            finally:
                loop.close()
                
        except Exception as e:
            print(f"从数据库获取配置失败: {e}")
            return {}
    
    def update_config(self, new_config):
        """更新配置"""
        try:
            self.config.update(new_config)
            
            # 更新环境变量
            for key, value in new_config.items():
                os.environ[key.upper()] = str(value)
            
            return {'success': True, 'message': '配置更新成功'}
            
        except Exception as e:
            return {'success': False, 'message': f'配置更新失败: {str(e)}'}

# 创建全局管理器实例
manager = ScraperManager()

@app.route('/api/management/status', methods=['GET'])
def get_status():
    """获取服务状态"""
    status = manager.get_status()
    return jsonify({
        'success': True,
        'data': status
    })

@app.route('/api/management/start', methods=['POST'])
def start_service():
    """启动服务"""
    result = manager.start_service()
    return jsonify(result)

@app.route('/api/management/stop', methods=['POST'])
def stop_service():
    """停止服务"""
    result = manager.stop_service()
    return jsonify(result)

@app.route('/api/management/restart', methods=['POST'])
def restart_service():
    """重启服务"""
    result = manager.restart_service()
    return jsonify(result)

@app.route('/api/management/config', methods=['GET', 'POST'])
def handle_config():
    """处理配置"""
    if request.method == 'GET':
        # 从数据库获取配置
        db_config = manager.get_config_from_db()
        
        # 合并环境变量配置和数据库配置
        config = {
            'api_id': db_config.get('telegram_api_id', manager.config.get('api_id', '')),
            'api_hash': db_config.get('telegram_api_hash', manager.config.get('api_hash', '')),
            'mysql_host': manager.config.get('mysql_host', 'mysql'),
            'mysql_database': manager.config.get('mysql_database', 'tg2em'),
            'mysql_user': manager.config.get('mysql_user', 'tg2emall'),
            'mysql_password': manager.config.get('mysql_password', 'tg2emall'),
            'tgstate_url': db_config.get('tgstate_url', manager.config.get('tgstate_url', 'http://tgstate:8088')),
            'tgstate_token': db_config.get('tgstate_token', ''),
            'tgstate_target': db_config.get('tgstate_target', ''),
            'tgstate_pass': db_config.get('tgstate_pass', ''),
            'tgstate_mode': db_config.get('tgstate_mode', 'p'),
            'tgstate_port': db_config.get('tgstate_port', '8088'),
            'scrape_channels': db_config.get('scrape_channels', ''),
            'scrape_limit': db_config.get('scrape_limit', '10'),
            'scrape_interval': db_config.get('scrape_interval', '300')
        }
        
        return jsonify({
            'success': True,
            'data': config
        })
    
    elif request.method == 'POST':
        try:
            new_config = request.get_json()
            result = manager.update_config(new_config)
            return jsonify(result)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'配置格式错误: {str(e)}'
            })

@app.route('/', methods=['GET'])
def index():
    """管理界面"""
    html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Telegram 采集服务管理</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .running { background-color: #d4edda; color: #155724; }
        .stopped { background-color: #f8d7da; color: #721c24; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
        .config { margin-top: 20px; }
        .config input { margin: 5px; padding: 5px; width: 200px; }
    </style>
</head>
<body>
    <h1>📱 Telegram 采集服务管理</h1>
    <div id="status" class="status">加载中...</div>
    <button onclick="startService()">启动采集</button>
    <button onclick="stopService()">停止采集</button>
    <button onclick="restartService()">重启采集</button>
    <button onclick="getStatus()">刷新状态</button>
    
    <div class="config">
        <h3>配置管理</h3>
        <div>
            <label>API ID:</label>
            <input type="text" id="api_id" placeholder="API ID">
        </div>
        <div>
            <label>API Hash:</label>
            <input type="text" id="api_hash" placeholder="API Hash">
        </div>
        <div>
            <label>MySQL Host:</label>
            <input type="text" id="mysql_host" placeholder="mysql">
        </div>
        <div>
            <label>MySQL Database:</label>
            <input type="text" id="mysql_database" placeholder="tg2em">
        </div>
        <div>
            <label>MySQL User:</label>
            <input type="text" id="mysql_user" placeholder="tg2em">
        </div>
        <div>
            <label>MySQL Password:</label>
            <input type="password" id="mysql_password" placeholder="password">
        </div>
        <div>
            <label>tgState URL:</label>
            <input type="text" id="tgstate_url" placeholder="http://tgstate:8088">
        </div>
        <button onclick="updateConfig()">更新配置</button>
        <button onclick="loadConfig()">加载配置</button>
    </div>
    
    <script>
        function getStatus() {
            fetch('/api/management/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    if (data.success) {
                        const status = data.data.status;
                        statusDiv.className = 'status ' + status;
                        statusDiv.innerHTML = `状态: ${status} | PID: ${data.data.pid || 'N/A'} | 启动时间: ${data.data.start_time || 'N/A'}`;
                    }
                });
        }
        
        function startService() {
            fetch('/api/management/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    getStatus();
                });
        }
        
        function stopService() {
            fetch('/api/management/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    getStatus();
                });
        }
        
        function restartService() {
            fetch('/api/management/restart', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    getStatus();
                });
        }
        
        function loadConfig() {
            fetch('/api/management/config')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const config = data.data;
                        document.getElementById('api_id').value = config.api_id || '';
                        document.getElementById('api_hash').value = config.api_hash || '';
                        document.getElementById('mysql_host').value = config.mysql_host || '';
                        document.getElementById('mysql_database').value = config.mysql_database || '';
                        document.getElementById('mysql_user').value = config.mysql_user || '';
                        document.getElementById('mysql_password').value = config.mysql_password || '';
                        document.getElementById('tgstate_url').value = config.tgstate_url || '';
                    }
                });
        }
        
        function updateConfig() {
            const config = {
                api_id: document.getElementById('api_id').value,
                api_hash: document.getElementById('api_hash').value,
                mysql_host: document.getElementById('mysql_host').value,
                mysql_database: document.getElementById('mysql_database').value,
                mysql_user: document.getElementById('mysql_user').value,
                mysql_password: document.getElementById('mysql_password').value,
                tgstate_url: document.getElementById('tgstate_url').value
            };
            
            fetch('/api/management/config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(config)
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
            });
        }
        
        // 页面加载时获取状态和配置
        getStatus();
        loadConfig();
        // 每5秒刷新状态
        setInterval(getStatus, 5000);
    </script>
</body>
</html>'''
    return html

def signal_handler(signum, frame):
    """信号处理器"""
    print("🛑 收到停止信号，正在关闭管理接口...")
    manager.stop_service()
    sys.exit(0)

if __name__ == '__main__':
    # 注册信号处理器
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🔧 Telegram 采集服务管理接口启动在端口 5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
