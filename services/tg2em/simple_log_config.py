#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
简化日志配置模块 - 当文件日志不可用时的备用方案
"""

import os
import logging
import sys

def setup_simple_logging(service_name, log_level=logging.INFO):
    """
    设置简化日志配置，仅使用控制台输出
    
    Args:
        service_name: 服务名称
        log_level: 日志级别
    """
    
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
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

def get_simple_logger(service_name):
    """获取指定服务的简化logger"""
    return logging.getLogger(service_name)
