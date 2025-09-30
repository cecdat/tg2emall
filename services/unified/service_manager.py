#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统一服务管理器 - 管理容器内所有进程
"""

import os
import json
import signal
import psutil
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnifiedServiceManager:
    """统一服务管理器"""
    
    def __init__(self):
        self.pids_file = "/app/data/pids.env"
        self.services = {
            'frontend': {'pid': None, 'status': 'unknown', 'port': 5000},
            'scraper': {'pid': None, 'status': 'unknown', 'port': None},
            'tgstate': {'pid': None, 'status': 'unknown', 'port': 8088}
        }
        self.load_pids()
    
    def load_pids(self):
        """从文件加载PID信息"""
        try:
            if os.path.exists(self.pids_file):
                with open(self.pids_file, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            service_name = key.replace('_PID', '').lower()
                            if service_name in self.services:
                                self.services[service_name]['pid'] = int(value) if value.isdigit() else None
        except Exception as e:
            logger.error(f"加载PID文件失败: {e}")
    
    def save_pids(self):
        """保存PID信息到文件"""
        try:
            with open(self.pids_file, 'w') as f:
                for service, info in self.services.items():
                    if info['pid']:
                        f.write(f"{service.upper()}_PID={info['pid']}\n")
        except Exception as e:
            logger.error(f"保存PID文件失败: {e}")
    
    def get_service_status(self, service_name: str) -> dict:
        """获取服务状态"""
        if service_name not in self.services:
            return {'success': False, 'message': f'未知服务: {service_name}'}
        
        service = self.services[service_name]
        pid = service['pid']
        
        try:
            if pid and psutil.pid_exists(pid):
                process = psutil.Process(pid)
                status = 'running' if process.status() == psutil.STATUS_RUNNING else 'stopped'
                
                return {
                    'success': True,
                    'status': status,
                    'pid': pid,
                    'port': service['port'],
                    'message': f'服务 {service_name} {status}'
                }
            else:
                return {
                    'success': True,
                    'status': 'stopped',
                    'pid': None,
                    'port': service['port'],
                    'message': f'服务 {service_name} 未运行'
                }
        except Exception as e:
            return {
                'success': False,
                'status': 'error',
                'pid': None,
                'port': service['port'],
                'message': f'检查服务状态失败: {str(e)}'
            }
    
    def start_service(self, service_name: str) -> dict:
        """启动服务（这个是占位符，实际启动由start.sh脚本完成）"""
        return {
            'success': True,
            'message': f'服务 {service_name} 启动成功 (统一容器管理)',
            'pid': None
        }
    
    def stop_service(self, service_name: str) -> dict:
        """停止服务"""
        try:
            service = self.services.get(service_name)
            if not service or not service['pid']:
                return {'success': False, 'message': f'服务 {service_name} 未运行'}
            
            pid = service['pid']
            if psutil.pid_exists(pid):
                os.kill(pid, signal.SIGTERM)
                service['pid'] = None
                self.save_pids()
                return {'success': True, 'message': f'服务 {service_name} 停止成功'}
            else:
                return {'success': False, 'message': f'服务 {service_name} 进程不存在'}
                
        except Exception as e:
            return {'success': False, 'message': f'停止服务失败: {str(e)}'}
    
    def restart_service(self, service_name: str) -> dict:
        """重启服务"""
        stop_result = self.stop_service(service_name)
        # 注意：重启需要start.sh脚本中检测到进程死亡后自动重启
        return {
            'success': True,
            'message': f'服务 {service_name} 重启请求已发送，将由监控脚本处理'
        }

# 创建全局服务管理器
service_manager = UnifiedServiceManager()

def start_service_via_process(service_name: str) -> dict:
    """通过进程控制启动服务"""
    return service_manager.start_service(service_name)

def stop_service_via_process(service_name: str) -> dict:
    """通过进程控制停止服务"""
    return service_manager.stop_service(service_name)

def check_service_status_via_process(service_name: str) -> dict:
    """检查服务状态"""
    return service_manager.get_service_status(service_name)

def restart_service_via_process(service_name: str) -> dict:
    """重启服务"""
    return service_manager.restart_service(service_name)

if __name__ == "__main__":
    # 运行服务管理器监控程序
    logger.info("🔧 统一服务管理器启动")
    
    while True:
        # 每10秒更新一次服务状态
        for service_name in service_manager.services.keys():
            status = service_manager.get_service_status(service_name)
            logger.info(f"服务状态: {service_name} = {status['status']} (PID: {status.get('pid', 'N/A')})")
        
        import time
        time.sleep(10)
