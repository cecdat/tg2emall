#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务控制器 - 通过HTTP API管理服务
"""

import requests
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class ServiceController:
    """服务控制器（HTTP API模式）"""
    
    def __init__(self, compose_dir: str = "/app/data"):
        # 服务名称映射：前端使用的名称 -> 实际的服务名称
        self.service_name_mapping = {
            'tgstate': 'tgstate-management',  # 前端使用tgstate，实际管理tgstate-management
            'tgstate-service': 'tgstate-service',  # 直接使用tgstate-service
            'tgstate-management': 'tgstate-management',  # 直接使用tgstate-management
            'scraper': 'scraper-management',  # 前端使用scraper，实际管理scraper-management
            'scraper-service': 'scraper-service',  # 直接使用scraper-service
            'scraper-management': 'scraper-management',  # 直接使用scraper-management
        }
        
        self.service_urls = {
            'scraper': 'http://tg2em-scrape:2003',  # 管理服务端口
            'scraper-service': 'http://tg2em-scrape:5002',  # 采集服务端口
            'scraper-management': 'http://tg2em-scrape:2003',  # 采集管理服务端口
            'tgstate': 'http://tgstate:8001',
            'tgstate-service': 'http://tgstate:8002',  # 图片上传服务端口
            'tgstate-management': 'http://tgstate:8001',  # 图片管理服务端口
            'mysql': 'http://mysql:3306',  # 外部服务，通过端口检查
            'nginx-proxy-manager': 'http://nginx-proxy-manager:80'  # 外部服务，通过端口检查
        }
            
    def get_service_status(self, service_name: str) -> Dict[str, Any]:
        """获取服务状态"""
        if service_name not in self.service_urls:
            return {
                'success': False,
                'status': 'error',
                'pid': None,
                'port': None,
                'message': f'未知服务: {service_name}'
            }
        
        # 获取数据库中的实际服务名称
        db_service_name = self.service_name_mapping.get(service_name, service_name)
        
        try:
            # 业务服务通过管理接口获取状态
            if service_name in ['scraper', 'scraper-service', 'scraper-management', 'tgstate', 'tgstate-service', 'tgstate-management']:
                # 统一通过管理服务获取状态
                if service_name in ['scraper', 'scraper-service', 'scraper-management']:
                    # 采集服务相关，都通过管理服务获取状态
                    url = f"{self.service_urls['scraper-management']}/api/management/status"
                elif service_name in ['tgstate', 'tgstate-service', 'tgstate-management']:
                    # 图片服务相关，都通过管理服务获取状态
                    url = f"{self.service_urls['tgstate-management']}/api/management/status"
                
                response = requests.get(url, timeout=5)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        status_data = data.get('data', {})
                        return {
                            'success': True,
                            'status': status_data.get('status', 'unknown'),
                            'pid': status_data.get('pid'),
                            'port': status_data.get('port'),
                            'message': status_data.get('message', f'服务 {service_name} 状态正常')
                        }
                
                return {
                    'success': False,
                    'status': 'error',
                    'pid': None,
                    'port': None,
                    'message': f'无法连接到 {service_name} 管理接口'
                }
            
            # 外部服务通过端口检查
            else:
                return {
                    'success': True,
                    'status': 'running',  # 假设外部服务运行中
                    'pid': None,
                    'port': None,
                    'message': f'服务 {service_name} 运行中'
                }
                    
        except Exception as e:
            logger.error(f"获取服务状态失败: {service_name}, 错误: {e}")
            return {
                'success': False,
                'status': 'error',
                'pid': None,
                'port': None,
                'message': f'状态检查失败: {str(e)}'
            }
    
    def start_service(self, service_name: str) -> Dict[str, Any]:
        """启动服务"""
        if service_name not in self.service_urls:
            return {'success': False, 'message': f'未知服务: {service_name}'}
        
        try:
            # 业务服务通过管理接口启动
            if service_name in ['scraper', 'scraper-service', 'scraper-management', 'tgstate', 'tgstate-service', 'tgstate-management']:
                # 统一通过管理服务启动
                if service_name in ['scraper', 'scraper-service', 'scraper-management']:
                    # 采集服务相关，都通过管理服务启动
                    url = f"{self.service_urls['scraper-management']}/api/management/start"
                elif service_name in ['tgstate', 'tgstate-service', 'tgstate-management']:
                    # 图片服务相关，都通过管理服务启动
                    url = f"{self.service_urls['tgstate-management']}/api/management/start"
                
                response = requests.post(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': data.get('success', False),
                        'message': data.get('message', '启动请求已发送'),
                        'pid': data.get('pid')
                    }
                
                return {
                    'success': False,
                    'message': f'无法连接到 {service_name} 管理接口'
                }
            else:
                return {
                    'success': False,
                    'message': f'无法启动外部服务 {service_name}'
                }
                
        except Exception as e:
            logger.error(f"启动服务失败: {service_name}, 错误: {e}")
            return {
                'success': False,
                'message': f'启动失败: {str(e)}'
            }
    
    def stop_service(self, service_name: str) -> Dict[str, Any]:
        """停止服务"""
        if service_name not in self.service_urls:
            return {'success': False, 'message': f'未知服务: {service_name}'}
        
        try:
            # 业务服务通过管理接口停止
            if service_name in ['scraper', 'scraper-service', 'scraper-management', 'tgstate', 'tgstate-service', 'tgstate-management']:
                # 统一通过管理服务停止
                if service_name in ['scraper', 'scraper-service', 'scraper-management']:
                    # 采集服务相关，都通过管理服务停止
                    url = f"{self.service_urls['scraper-management']}/api/management/stop"
                elif service_name in ['tgstate', 'tgstate-service', 'tgstate-management']:
                    # 图片服务相关，都通过管理服务停止
                    url = f"{self.service_urls['tgstate-management']}/api/management/stop"
                
                response = requests.post(url, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': data.get('success', False),
                        'message': data.get('message', '停止请求已发送')
                    }
                
                return {
                    'success': False,
                    'message': f'无法连接到 {service_name} 管理接口'
                }
            else:
                return {
                    'success': False,
                    'message': f'无法停止外部服务 {service_name}'
                }
                
        except Exception as e:
            logger.error(f"停止服务失败: {service_name}, 错误: {e}")
            return {
                'success': False,
                'message': f'停止失败: {str(e)}'
            }
    
    def restart_service(self, service_name: str) -> Dict[str, Any]:
        """重启服务"""
        if service_name not in self.service_urls:
            return {'success': False, 'message': f'未知服务: {service_name}'}
        
        try:
            # 业务服务通过管理接口重启
            if service_name in ['scraper', 'scraper-service', 'scraper-management', 'tgstate', 'tgstate-service', 'tgstate-management']:
                # 统一通过管理服务重启
                if service_name in ['scraper', 'scraper-service', 'scraper-management']:
                    # 采集服务相关，都通过管理服务重启
                    url = f"{self.service_urls['scraper-management']}/api/management/restart"
                elif service_name in ['tgstate', 'tgstate-service', 'tgstate-management']:
                    # 图片服务相关，都通过管理服务重启
                    url = f"{self.service_urls['tgstate-management']}/api/management/restart"
                
                response = requests.post(url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': data.get('success', False),
                        'message': data.get('message', '重启请求已发送'),
                        'pid': data.get('pid')
                    }
                
                return {
                    'success': False,
                    'message': f'无法连接到 {service_name} 管理接口'
                }
            else:
                return {
                    'success': False,
                    'message': f'无法重启外部服务 {service_name}'
                }
                
        except Exception as e:
            logger.error(f"重启服务失败: {service_name}, 错误: {e}")
            return {
                'success': False,
                'message': f'重启失败: {str(e)}'
            }

# 创建全局服务控制器实例
service_controller = ServiceController()

def start_service_via_docker_real(service_name: str) -> Dict[str, Any]:
    """通过进程控制启动服务"""
    return service_controller.start_service(service_name)

def stop_service_via_docker_real(service_name: str) -> Dict[str, Any]:
    """通过进程控制停止服务"""
    return service_controller.stop_service(service_name)

def check_service_status_via_docker_real(service_name: str) -> Dict[str, Any]:
    """检查服务状态"""
    return service_controller.get_service_status(service_name)

def restart_service_via_docker_real(service_name: str) -> Dict[str, Any]:
    """重启服务"""
    return service_controller.restart_service(service_name)

# 保持向后兼容性的别名
def start_service_via_docker(service_name: str) -> Dict[str, Any]:
    return start_service_via_docker_real(service_name)

def stop_service_via_docker(service_name: str) -> Dict[str, Any]:
    return stop_service_via_docker_real(service_name)

def check_service_status_via_docker(service_name: str) -> Dict[str, Any]:
    return check_service_status_via_docker_real(service_name)