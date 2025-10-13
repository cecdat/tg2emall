#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志配置模块 - 提供统一的日志轮转配置
"""

import os
import logging
import logging.handlers
from datetime import datetime

def setup_logging(service_name, log_level=logging.INFO, max_bytes=10*1024*1024, backup_count=7):
    """
    设置日志配置，支持日志轮转
    
    Args:
        service_name: 服务名称
        log_level: 日志级别
        max_bytes: 单个日志文件最大大小（字节），默认10MB
        backup_count: 保留的日志文件数量，默认7个
    """
    
    # 创建日志目录
    log_dir = '/app/logs'
    try:
        os.makedirs(log_dir, exist_ok=True)
        # 设置目录权限
        os.chmod(log_dir, 0o755)
    except PermissionError:
        # 如果无法创建目录，使用临时目录
        log_dir = '/tmp/logs'
        os.makedirs(log_dir, exist_ok=True)
        print(f"警告: 无法访问 /app/logs，使用临时目录 {log_dir}")
    
    # 日志文件路径
    log_file = os.path.join(log_dir, f'{service_name}.log')
    
    # 创建logger
    logger = logging.getLogger(service_name)
    logger.setLevel(log_level)
    
    # 清除已有的处理器
    logger.handlers.clear()
    
    # 创建格式器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（支持轮转）
    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # 错误日志单独记录
        error_log_file = os.path.join(log_dir, f'{service_name}_error.log')
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    except PermissionError:
        print(f"警告: 无法写入日志文件 {log_file}，仅使用控制台输出")
        # 如果无法写入文件，只使用控制台输出
    
    return logger

def get_logger(service_name):
    """获取指定服务的logger"""
    return logging.getLogger(service_name)

def cleanup_old_logs(log_dir, days=30):
    """
    清理超过指定天数的旧日志文件
    
    Args:
        log_dir: 日志目录
        days: 保留天数
    """
    import glob
    import time
    
    if not os.path.exists(log_dir):
        return
    
    # 计算过期时间戳
    expire_time = time.time() - (days * 24 * 60 * 60)
    
    # 查找所有日志文件
    log_patterns = [
        os.path.join(log_dir, '*.log'),
        os.path.join(log_dir, '*.log.*'),
    ]
    
    for pattern in log_patterns:
        for log_file in glob.glob(pattern):
            try:
                if os.path.getmtime(log_file) < expire_time:
                    os.remove(log_file)
                    print(f"已删除过期日志文件: {log_file}")
            except OSError as e:
                print(f"删除日志文件失败 {log_file}: {e}")

# 预定义的服务日志配置
SERVICE_CONFIGS = {
    'frontend': {
        'log_level': logging.WARNING,
        'max_bytes': 10 * 1024 * 1024,  # 10MB
        'backup_count': 7
    },
    'scraper': {
        'log_level': logging.INFO,
        'max_bytes': 20 * 1024 * 1024,  # 20MB
        'backup_count': 7
    },
    'tgstate': {
        'log_level': logging.INFO,
        'max_bytes': 5 * 1024 * 1024,   # 5MB
        'backup_count': 7
    },
    'admin': {
        'log_level': logging.INFO,
        'max_bytes': 5 * 1024 * 1024,   # 5MB
        'backup_count': 7
    },
    'unified': {
        'log_level': logging.INFO,
        'max_bytes': 5 * 1024 * 1024,   # 5MB
        'backup_count': 7
    }
}

def setup_service_logging(service_name):
    """为指定服务设置日志配置"""
    config = SERVICE_CONFIGS.get(service_name, SERVICE_CONFIGS['frontend'])
    return setup_logging(service_name, **config)
