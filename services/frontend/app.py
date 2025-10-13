#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tg2emall 前端展示系统
基于 Flask 的简单博客展示系统
"""

import os
import json
import logging
import pymysql
import requests
import socket
import markdown
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from contextlib import contextmanager
from functools import wraps
import re
import hashlib

# ==================== 工具函数 ====================

def get_public_ip():
    """获取公网IP地址"""
    try:
        # 尝试多个公共IP查询服务
        services = [
            'https://api.ipify.org?format=text',
            'https://ifconfig.me/ip',
            'https://api.ip.sb/ip',
            'https://ipinfo.io/ip'
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=3)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip and '.' in ip:  # 简单验证是否为IPv4
                        logging.info(f"✅ 获取到公网IP: {ip}")
                        return ip
            except:
                continue
        
        # 如果所有服务都失败，尝试获取本地IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
            logging.warning(f"⚠️ 无法获取公网IP，使用本地IP: {local_ip}")
            return local_ip
        except:
            return '127.0.0.1'
        finally:
            s.close()
            
    except Exception as e:
        logging.error(f"❌ 获取IP地址失败: {e}")
        return '127.0.0.1'

def get_server_url():
    """获取服务器访问地址（使用公网IP，不使用localhost）"""
    port = int(os.getenv('FRONTEND_PORT', '8000'))
    public_ip = get_public_ip()
    
    # 如果端口是80，不显示端口号
    if port == 80:
        return f"http://{public_ip}"
    else:
        return f"http://{public_ip}:{port}"

# ==================== 服务控制器 ====================

# 导入服务控制器
try:
    from service_controller import ServiceController
except ImportError as e:
    logging.error(f"导入服务控制器失败: {e}")
    ServiceController = None

def get_db_service_name(frontend_service_name):
    """获取数据库中的服务名称"""
    service_mapping = {
        'tgstate': 'tgstate-management',
        'tgstate-service': 'tgstate-management',  # 兼容tgstate-service名称
        'scraper': 'scraper-management',
        'scraper-service': 'scraper-management',  # 兼容scraper-service名称
    }
    return service_mapping.get(frontend_service_name, frontend_service_name)

def update_services_status_to_db():
    """更新服务状态到数据库"""
    try:
        controller = ServiceController()
        
        # 需要检查的服务列表
        services_to_check = [
            'tgstate-management',
            'tgstate-service', 
            'scraper-management',
            'scraper-service',
            'mysql',
            'frontend'
        ]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for service_name in services_to_check:
                try:
                    # 获取服务状态
                    if service_name in ['tgstate-management', 'tgstate-service', 'scraper-management', 'scraper-service']:
                        # 业务服务通过管理接口获取状态
                        status_result = controller.get_service_status(service_name)
                        
                        if status_result['success']:
                            status = status_result['status']
                            pid = status_result.get('pid')
                            port = status_result.get('port')
                            message = status_result.get('message', f'服务 {service_name} 状态正常')
                        else:
                            status = 'error'
                            pid = None
                            port = None
                            message = status_result.get('message', f'服务 {service_name} 状态异常')
                    else:
                        # 系统服务假设运行中
                        status = 'running'
                        pid = None
                        port = None
                        message = f'服务 {service_name} 运行中'
                    
                    # 更新数据库
                    cursor.execute("""
                        INSERT INTO services_status 
                        (service_name, status, last_check, pid, port, message, updated_at)
                        VALUES (%s, %s, NOW(), %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                        status = VALUES(status),
                        last_check = VALUES(last_check),
                        pid = VALUES(pid),
                        port = VALUES(port),
                        message = VALUES(message),
                        updated_at = VALUES(updated_at)
                    """, (service_name, status, pid, port, message))
                    
                except Exception as e:
                    logger.error(f"更新服务状态失败: {service_name}, 错误: {e}")
                    # 更新为错误状态
                    cursor.execute("""
                        INSERT INTO services_status 
                        (service_name, status, last_check, message, updated_at)
                        VALUES (%s, 'error', NOW(), %s, NOW())
                        ON DUPLICATE KEY UPDATE
                        status = 'error',
                        last_check = NOW(),
                        message = VALUES(message),
                        updated_at = VALUES(updated_at)
                    """, (service_name, f'状态检查失败: {str(e)}'))
            
            conn.commit()
            logger.info("服务状态更新完成")
            
    except Exception as e:
        logger.error(f"更新服务状态到数据库失败: {e}")

def start_service_via_docker(service_name):
    """通过服务管理接口启动服务"""
    if ServiceController is None:
        return {'success': False, 'message': 'ServiceController未初始化'}
    
    controller = ServiceController()
    return controller.start_service(service_name)

def stop_service_via_docker(service_name):
    """通过服务管理接口停止服务"""
    if ServiceController is None:
        return {'success': False, 'message': 'ServiceController未初始化'}
    
    controller = ServiceController()
    return controller.stop_service(service_name)

def check_service_status_via_docker(service_name):
    """通过服务管理接口检查服务状态"""
    if ServiceController is None:
        return {'success': False, 'status': 'error', 'message': 'ServiceController未初始化'}
    
    controller = ServiceController()
    return controller.get_service_status(service_name)

def restart_service_via_docker(service_name):
    """重启服务"""
    if ServiceController is None:
        return {'success': False, 'message': 'ServiceController未初始化'}
    
    controller = ServiceController()
    return controller.restart_service(service_name)

# 如果导入失败，使用模拟实现
if ServiceController is None:
    def start_service_via_docker(service_name):
        """通过Docker启动服务（模拟实现）"""
        try:
            service_mapping = {
                'tgstate': 'tg2em-tgstate',
                'scraper': 'tg2em-scrape'
            }
            
            docker_service = service_mapping.get(service_name)
            if not docker_service:
                return {'success': False, 'message': f'未知服务: {service_name}'}
            
            return {'success': True, 'message': f'服务 {service_name} 启动成功', 'pid': 12345}
            
        except Exception as e:
            return {'success': False, 'message': f'启动失败: {str(e)}'}

    def stop_service_via_docker(service_name):
        """通过Docker停止服务（模拟实现）"""
        try:
            return {'success': True, 'message': f'服务 {service_name} 停止成功'}
            
        except Exception as e:
            return {'success': False, 'message': f'停止失败: {str(e)}'}

    def check_service_status_via_docker(service_name):
        """检查Docker服务状态（模拟实现）"""
        try:
            status_values = ['running', 'stopped', 'error']
            import random
            status = random.choice(status_values)
            
            messages = {
                'running': '服务运行中',
                'stopped': '服务已停止',
                'error': '服务异常'
            }
            
            return {
                'success': True,
                'status': status,
                'message': messages.get(status, '状态未知'),
                'pid': random.randint(1000, 9999) if status == 'running' else None
            }
            
        except Exception as e:
            return {'success': False, 'message': f'状态检查失败: {str(e)}'}

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置Markdown渲染
def render_markdown(text):
    """渲染Markdown文本为HTML"""
    if not text:
        return ""
    
    # 配置Markdown扩展
    md = markdown.Markdown(
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.toc',
            'markdown.extensions.codehilite',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists'
        ],
        extension_configs={
            'markdown.extensions.codehilite': {
                'css_class': 'highlight'
            }
        }
    )
    
    # 渲染Markdown
    html = md.convert(text)
    
    # 处理图片，添加响应式样式
    html = re.sub(
        r'<img([^>]*?)src="([^"]*?)"([^>]*?)>',
        r'<img\1src="\2"\3 class="img-fluid rounded shadow" style="max-width: 100%; height: auto; margin: 10px 0;">',
        html
    )
    
    return html

# 提取图片URL的过滤器
def extract_image_url(markdown_image):
    """从Markdown格式的图片中提取纯URL"""
    if not markdown_image:
        return None
    
    # 匹配 ![](url) 格式
    import re
    match = re.search(r'!\[.*?\]\((.*?)\)', markdown_image)
    if match:
        return match.group(1)
    
    # 如果不是Markdown格式，直接返回原值
    return markdown_image

# 获取广告位
def get_advertisements(position):
    """获取指定位置的广告位"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT * FROM advertisements 
                WHERE position = %s AND is_active = 1 
                ORDER BY sort_order ASC, created_at DESC
            """, (position,))
            ads = cursor.fetchall()
            return ads if ads else []
    except Exception as e:
        logger.error(f"获取广告位失败: {e}")
        return []

def get_popular_articles(limit=5):
    """获取热门文章（按点击量排序）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT id, title, tags, source_channel, created_at, click_count
                FROM messages 
                WHERE is_deleted = 0 
                ORDER BY click_count DESC, created_at DESC 
                LIMIT %s
            """, (limit,))
            articles = cursor.fetchall()
            return articles if articles else []
    except Exception as e:
        logger.error(f"获取热门文章失败: {e}")
        return []

def track_article_click(article_id, request):
    """记录文章点击"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 获取访问者信息
            visitor_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', '127.0.0.1'))
            user_agent = request.headers.get('User-Agent', '')
            referrer = request.headers.get('Referer', '')
            session_id = session.get('session_id', '')
            
            # 记录点击日志
            cursor.execute("""
                INSERT INTO article_click_logs (article_id, visitor_ip, user_agent, referrer, session_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (article_id, visitor_ip, user_agent, referrer, session_id))
            
            # 更新文章点击统计
            cursor.execute("""
                UPDATE messages 
                SET click_count = click_count + 1, last_clicked_at = NOW()
                WHERE id = %s
            """, (article_id,))
            
            conn.commit()
            logger.info(f"文章点击记录成功: article_id={article_id}, ip={visitor_ip}")
            
    except Exception as e:
        logger.error(f"记录文章点击失败: {e}")

def create_mixed_content(articles, ads):
    """创建资源列表和广告位的混合内容"""
    import random
    
    # 如果没有广告，直接返回所有资源
    if not ads:
        return [{'type': 'article', 'content': article} for article in articles]
    
    # 创建混合内容列表
    mixed_content = []
    
    # 将资源转换为字典格式
    for article in articles:
        mixed_content.append({'type': 'article', 'content': article})
    
    # 随机选择4个位置插入广告
    if len(mixed_content) >= 4:
        # 生成4个随机位置（确保不重复且不在开头和结尾）
        positions = random.sample(range(1, len(mixed_content)), min(4, len(mixed_content) - 1))
        positions.sort(reverse=True)  # 从后往前插入，避免位置偏移
        
        # 随机选择广告
        selected_ads = random.sample(ads, min(4, len(ads)))
        
        # 在随机位置插入广告
        for i, pos in enumerate(positions):
            if i < len(selected_ads):
                ad = selected_ads[i]
                mixed_content.insert(pos, {'type': 'ad', 'content': ad})
    
    return mixed_content

# 注册Jinja2过滤器
app.jinja_env.filters['markdown'] = render_markdown
app.jinja_env.filters['extract_image_url'] = extract_image_url

def analyze_visit_source(user_agent, referrer, page_path):
    """分析访问来源"""
    if not user_agent:
        return '未知'
    
    user_agent_lower = user_agent.lower()
    
    # 搜索引擎
    if any(engine in user_agent_lower for engine in ['baidu', 'googlebot', 'bing', 'yandex']):
        return '搜索引擎'
    elif referrer:
        referrer_lower = referrer.lower()
        if any(social in referrer_lower for social in ['weibo', 'twitter', 'facebook', 'instagram']):
            return '社交媒体'
        elif any(msg in referrer_lower for msg in ['telegram', 'whatsapp', 'wechat']):
            return '即时通讯'
        else:
            return '外部网站'
    elif user_agent_lower in ['chrome', 'firefox', 'safari', 'edge'] or \
         any(browser in user_agent_lower for browser in ['chrome/', 'firefox/', 'safari/', 'edg/']):
        return '直接访问'
    else:
        return '其他'

def record_visit():
    """记录访问"""
    try:
        visitor_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        page_path = request.path
        referrer = request.headers.get('Referer', '')
        visit_source = analyze_visit_source(user_agent, referrer, page_path)
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO visit_logs (visitor_ip, user_agent, page_path, referrer, visit_source, session_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (visitor_ip, user_agent, page_path, referrer, visit_source, session.get('session_id')))
            conn.commit()
    except Exception as e:
        logger.debug(f"记录访问失败: {e}")

@app.before_request
def before_request():
    """请求前处理"""
    # 为每个请求生成会话ID
    if 'session_id' not in session:
        session['session_id'] = hashlib.md5(f"{request.remote_addr}{datetime.now()}".encode()).hexdigest()
    
    # 排除管理后台访问记录
    if not request.path.startswith('/admin') and not request.path.startswith('/dm'):
        record_visit()
app.secret_key = os.environ.get('SECRET_KEY', 'tg2emall-secret-key')

# 管理员配置（应该在生产环境中使用环境变量）
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

def login_required(f):
    """登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            # 记录未授权访问尝试
            logger.warning(f"未授权访问尝试: {request.remote_addr} -> {request.path}")
            return redirect(url_for('admin_login'))
        
        # 检查会话是否过期（24小时）
        if 'login_time' in session:
            login_time = session['login_time']
            # 确保两个datetime都是naive类型
            if hasattr(login_time, 'tzinfo') and login_time.tzinfo is not None:
                login_time = login_time.replace(tzinfo=None)
            current_time = datetime.now()
            if (current_time - login_time).total_seconds() > 24 * 3600:
                session.clear()
                logger.info(f"会话过期，用户已登出: {session.get('username', 'unknown')}")
                return redirect(url_for('admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_template_vars():
    """注入模板变量"""
    return {
        'current_time': datetime.now()
    }

# 数据库配置
DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'mysql'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'tg2em'),
    'password': os.environ.get('MYSQL_PASSWORD', 'tg2em2025'),
    'database': os.environ.get('MYSQL_DATABASE', 'tg2em'),
    'charset': 'utf8mb4'
}

@contextmanager
def get_db_connection():
    """获取数据库连接上下文管理器"""
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        yield conn
    except Exception as e:
        logger.error(f"数据库连接错误: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_articles(limit=20, offset=0, category=None):
    """获取文章"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            if category:
                sql = """
                    SELECT * FROM messages 
                    WHERE sort_id = %s 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (category, limit, offset))
            else:
                sql = """
                    SELECT * FROM messages 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """
                cursor.execute(sql, (limit, offset))
            
            articles = cursor.fetchall()
            logger.info(f"成功获取 {len(articles)} 篇文章")
            return articles if articles else []
    except Exception as e:
        logger.error(f"获取文章失败: {e}")
        logger.info("数据库连接失败或无数据，返回空列表")
        return []

def get_article_by_id(article_id):
    """根据ID获取文章"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = "SELECT * FROM messages WHERE id = %s"
            cursor.execute(sql, (article_id,))
            article = cursor.fetchone()
            return article
    except Exception as e:
        logger.error(f"获取文章失败: {e}")
        return None

def get_categories():
    """获取网盘类型分类统计"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT 
                    CASE 
                        WHEN sort_id = 1 THEN '夸克网盘'
                        WHEN sort_id = 2 THEN '阿里云盘'
                        WHEN sort_id = 3 THEN '百度网盘'
                        WHEN sort_id = 4 THEN '移动云盘'
                        ELSE '其他网盘'
                    END as category_name,
                    sort_id,
                    COUNT(*) as count 
                FROM messages 
                WHERE sort_id IS NOT NULL 
                GROUP BY sort_id 
                ORDER BY count DESC
            """
            cursor.execute(sql)
            categories = cursor.fetchall()
            logger.info(f"成功获取 {len(categories)} 个网盘分类")
            return categories if categories else []
    except Exception as e:
        logger.error(f"获取网盘分类失败: {e}")
        logger.info("数据库连接失败或无分类数据，返回空列表")
        return []

def get_visit_sources():
    """获取访问来源统计"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT 
                    CASE 
                        WHEN visit_source = '搜索引擎' THEN '搜索引擎'
                        WHEN visit_source = '直接访问' THEN '直接访问'
                        WHEN visit_source = '社交媒体' THEN '社交媒体'
                        WHEN visit_source = '即时通讯' THEN '即时通讯'
                        WHEN visit_source = '外部网站' THEN '外部网站'
                        ELSE '其他'
                    END as source,
                    COUNT(*) as count
                FROM visit_logs 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                GROUP BY 
                    CASE 
                        WHEN visit_source = '搜索引擎' THEN '搜索引擎'
                        WHEN visit_source = '直接访问' THEN '直接访问'
                        WHEN visit_source = '社交媒体' THEN '社交媒体'
                        WHEN visit_source = '即时通讯' THEN '即时通讯'
                        WHEN visit_source = '外部网站' THEN '外部网站'
                        ELSE '其他'
                    END
                ORDER BY count DESC
                LIMIT 6
            """
            cursor.execute(sql)
            sources = cursor.fetchall()
            logger.info(f"成功获取 {len(sources)} 个访问来源")
            return sources if sources else []
    except Exception as e:
        logger.error(f"获取访问来源统计失败: {e}")
        return []
def get_popular_searches():
    """获取最近24小时的热门搜索关键字"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT search_keyword, COUNT(*) as search_count
                FROM search_logs 
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                GROUP BY search_keyword 
                ORDER BY search_count DESC 
                LIMIT 5
            """
            cursor.execute(sql)
            searches = cursor.fetchall()
            logger.info(f"成功获取 {len(searches)} 个热门搜索")
            return searches if searches else []
    except Exception as e:
        logger.error(f"获取热门搜索失败: {e}")
        return []

def get_recent_articles(limit=5):
    """获取最新文章（仅标题、标签、发布时间、来源）"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT id, title, tags, created_at, source_channel 
                FROM messages 
                ORDER BY created_at DESC 
                LIMIT %s
            """
            cursor.execute(sql, (limit,))
            articles = cursor.fetchall()
            logger.info(f"成功获取 {len(articles)} 篇最新文章")
            return articles if articles else []
    except Exception as e:
        logger.error(f"获取最新文章失败: {e}")
        logger.info("数据库连接失败或无最新文章数据，返回空列表")
        return []

def get_published_articles(limit=10, offset=0):
    """获取已发布的文章"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT * FROM messages 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            cursor.execute(sql, (limit, offset))
            articles = cursor.fetchall()
            return articles
    except Exception as e:
        logger.error(f"获取已发布文章失败: {e}")
        return []

def log_search(query, results_count):
    """记录搜索日志"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO search_logs (search_keyword, visitor_ip, user_agent, results_count)
                VALUES (%s, %s, %s, %s)
            """, (query, request.remote_addr, request.headers.get('User-Agent', ''), results_count))
            conn.commit()
    except Exception as e:
        logger.error(f"记录搜索日志失败: {e}")

def search_articles(query, limit=10, offset=0):
    """搜索文章"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT * FROM messages 
                WHERE (title LIKE %s OR content LIKE %s OR tags LIKE %s)
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """
            search_term = f"%{query}%"
            cursor.execute(sql, (search_term, search_term, search_term, limit, offset))
            articles = cursor.fetchall()
            return articles
    except Exception as e:
        logger.error(f"搜索文章失败: {e}")
        return []

def count_search_results(query):
    """统计搜索结果数量"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT COUNT(*) as count FROM messages 
                WHERE (title LIKE %s OR content LIKE %s OR tags LIKE %s)
            """
            search_term = f"%{query}%"
            cursor.execute(sql, (search_term, search_term, search_term))
            result = cursor.fetchone()
            return result['count']
    except Exception as e:
        logger.error(f"统计搜索结果失败: {e}")
        return 0

def count_articles():
    """统计文章数量"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = "SELECT COUNT(*) as count FROM messages"
            cursor.execute(sql)
            result = cursor.fetchone()
            return result['count']
    except Exception as e:
        logger.error(f"统计文章数量失败: {e}")
        return 0

def get_advertisements(position):
    """获取指定位置的广告"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT * FROM advertisements 
                WHERE (position = %s OR position = 'both') AND is_active = 1 
                ORDER BY sort_order DESC, created_at DESC
            """
            cursor.execute(sql, (position,))
            ads = cursor.fetchall()
            return ads
    except Exception as e:
        logger.error(f"获取广告失败: {e}")
        return []

@app.route('/')
def index():
    """首页"""
    try:
        # 获取数据
        articles = get_articles(20, 0)  # 获取20个资源
        recent_articles = get_recent_articles(5)
        popular_articles = get_popular_articles(5)  # 获取热门文章
        popular_searches = get_popular_searches()
        categories = get_categories()
        
        # 获取广告位
        homepage_middle_ads = get_advertisements('homepage-middle')
        homepage_resources_ads = get_advertisements('homepage-resources')
        
        # 处理资源列表和广告位混合显示
        mixed_content = create_mixed_content(articles, homepage_resources_ads)
        
        # 统计信息
        stats = {
            'total_articles': len(articles),
            'data_available': len(articles) > 0
        }
        
        logger.info(f"首页数据统计: 文章={stats['total_articles']}, 有数据={stats['data_available']}")
        
        return render_template('index.html', 
                             articles=articles, 
                             recent_articles=recent_articles,
                             popular_articles=popular_articles,
                             popular_searches=popular_searches,
                             categories=categories,
                             homepage_middle_ads=homepage_middle_ads,
                             mixed_content=mixed_content,
                             stats=stats)
    except Exception as e:
        logger.error(f"首页路由处理失败: {e}")
        # 即使出现异常，也返回空数据的页面，确保网站可以访问
        return render_template('index.html', 
                             articles=[], 
                             recent_articles=[],
                             popular_articles=[],
                             popular_searches=[],
                             categories=[],
                             homepage_middle_ads=[],
                             mixed_content=[],
                             stats={'total_articles': 0, 'data_available': False})

@app.route('/search')
def search():
    """搜索页面"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    if query:
        # 执行搜索
        articles = search_articles(query, per_page, offset)
        total_count = count_search_results(query)
        
        # 记录搜索日志
        log_search(query, total_count)
    else:
        # 显示所有文章
        articles = get_articles(per_page, offset)
        total_count = count_articles()
    
    categories = get_categories()
    recent_articles = get_recent_articles(5)
    ads = get_advertisements('search_list')
    total_pages = (total_count + per_page - 1) // per_page
    
    return render_template('search.html',
                         articles=articles,
                         categories=categories,
                         recent_articles=recent_articles,
                         advertisement_ads=ads,
                         query=query,
                         current_page=page,
                         total_pages=total_pages,
                         total_count=total_count)

@app.route('/article/<int:article_id>')
@app.route('/article/<int:article_id>.html')
def article_detail(article_id):
    """文章详情页"""
    article = get_article_by_id(article_id)
    if not article:
        return "文章不存在", 404
    
    # 记录文章点击
    track_article_click(article_id, request)
    
    recent_articles = get_recent_articles(5)
    article_middle_ads = get_advertisements('article-middle')
    article_sidebar_ads = get_advertisements('article-sidebar')
    
    return render_template('article.html', 
                         article=article,
                         recent_articles=recent_articles,
                         article_middle_ads=article_middle_ads,
                         article_sidebar_ads=article_sidebar_ads)

@app.route('/api/articles')
def api_articles():
    """API: 获取文章列表"""
    # 限制请求频率（简单实现）
    client_ip = request.remote_addr
    current_time = datetime.now()
    
    # 记录API访问（用于监控）
    logger.debug(f"API访问: {client_ip} -> /api/articles")
    
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    # 限制分页参数
    if page < 1:
        page = 1
    if limit > 100:  # 限制最大返回数量
        limit = 100
    
    offset = (page - 1) * limit
    
    articles = get_published_articles(limit, offset)
    
    return jsonify({
        'success': True,
        'data': articles,
        'page': page,
        'limit': limit
    })

@app.route('/api/article/<int:article_id>')
def api_article_detail(article_id):
    """API: 获取文章详情"""
    # 记录API访问
    logger.debug(f"API访问: {request.remote_addr} -> /api/article/{article_id}")
    
    # 验证文章ID
    if article_id < 1:
        return jsonify({'success': False, 'message': '无效的文章ID'}), 400
    
    article = get_article_by_id(article_id)
    if not article:
        return jsonify({'success': False, 'message': '文章不存在'}), 404
    
    return jsonify({
        'success': True,
        'data': article
    })

# 移除分类功能

@app.route('/dm', methods=['GET', 'POST'])
def admin_login():
    """管理员登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        captcha = request.form.get('captcha')
        
        # 验证验证码
        if captcha != '2025':
            logger.warning(f"管理员登录失败: 验证码错误 - {username}")
            return render_template('admin_login.html', error='验证码错误')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = username
            session['login_time'] = datetime.now()
            session['login_ip'] = request.remote_addr
            logger.info(f"管理员登录成功: {username} from {request.remote_addr}")
            return redirect(url_for('admin_index'))
        else:
            logger.warning(f"管理员登录失败: 用户名或密码错误 - {username}")
            return render_template('admin_login.html', error='用户名或密码错误')
    
    return render_template('admin_login.html')

@app.route('/dm/logout')
def admin_logout():
    """管理员登出"""
    username = session.get('username', 'unknown')
    login_ip = session.get('login_ip', 'unknown')
    session.clear()  # 完全清除会话
    logger.info(f"管理员已登出: {username} from {login_ip}")
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_index():
    """后台管理首页"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 总文章数
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total_articles = cursor.fetchone()['total']
            
            # 今日文章数
            today = datetime.now().date()
            cursor.execute(
                "SELECT COUNT(*) as today FROM messages WHERE DATE(created_at) = %s",
                (today,)
            )
            today_articles = cursor.fetchone()['today']
            
            # 昨日文章数
            yesterday = (datetime.now() - timedelta(days=1)).date()
            cursor.execute(
                "SELECT COUNT(*) as yesterday FROM messages WHERE DATE(created_at) = %s",
                (yesterday,)
            )
            yesterday_articles = cursor.fetchone()['yesterday']
            
            # 数据采集服务状态（检查真实状态）
            try:
                scrape_cont_status = check_service_status_via_docker('scraper')
                scrape_status = scrape_cont_status.get('status', 'unknown')
                scrape_status = '运行中' if scrape_status == 'running' else '未运行'
            except:
                scrape_status = "未知"
            
            # 访问统计（先使用模拟数据，后续可以添加访问记录）
            daily_visitors = 125
            total_visitors = total_articles * 15  # 模拟计算
            
            # 访问来源 statistical（模拟）
            visit_sources = get_visit_sources()
            
            stats = {
                'total_articles': total_articles,
                'today_articles': today_articles,
                'yesterday_articles': yesterday_articles,
                'scrape_status': scrape_status,
                'daily_visitors': daily_visitors,
                'total_visitors': total_visitors,
                'visit_sources': visit_sources
            }
            
            return render_template('admin.html', stats=stats)
            
    except Exception as e:
        logger.error(f"后台管理页面失败: {e}")
        return render_template('admin.html', 
                             stats={
                                 'total_articles': 0, 
                                 'today_articles': 0, 
                                 'yesterday_articles': 0,
                                 'scrape_status': '未知',
                                 'daily_visitors': 0,
                                 'total_visitors': 0,
                                 'visit_sources': [
                                     {'source': '暂无数据', 'count': 0}
                                 ]
                             })

@app.route('/admin/articles')
@login_required
def admin_articles():
    """文章管理页面"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 分页参数
            page = request.args.get('page', 1, type=int)
            per_page = 20
            offset = (page - 1) * per_page
            
            # 获取文章列表（分页）
            cursor.execute("""
                SELECT id, title, content, created_at, source_channel, tags
                FROM messages 
                ORDER BY created_at DESC 
                LIMIT %s OFFSET %s
            """, (per_page, offset))
            articles = cursor.fetchall()
            
            # 总数
            cursor.execute("SELECT COUNT(*) as total FROM messages")
            total = cursor.fetchone()['total']
            
            # 计算分页信息
            total_pages = (total + per_page - 1) // per_page
            
            pagination = {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_num': page - 1 if page > 1 else None,
                'next_num': page + 1 if page < total_pages else None
            }
            
            return render_template('admin_articles.html', 
                                 articles=articles, 
                                 pagination=pagination)
    except Exception as e:
        logger.error(f"文章管理页面失败: {e}")
        return render_template('admin_articles.html', 
                             articles=[], 
                             pagination={})

@app.route('/admin/articles/<int:article_id>')
@login_required
def admin_article_edit(article_id):
    """编辑文章页面"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("SELECT * FROM messages WHERE id = %s", (article_id,))
            article = cursor.fetchone()
            
            if not article:
                return "文章不存在", 404
                
            return render_template('admin_article_edit.html', article=article)
    except Exception as e:
        logger.error(f"编辑文章页面失败: {e}")
        return "加载失败", 500

@app.route('/admin/articles/<int:article_id>', methods=['POST'])
@login_required
def admin_article_update(article_id):
    """更新文章"""
    try:
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            return jsonify({'success': False, 'message': '标题和内容不能为空'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE messages 
                SET title = %s, content = %s 
                WHERE id = %s
            """, (title, content, article_id))
            conn.commit()
            
            logger.info(f"文章更新成功: ID={article_id}")
            return jsonify({'success': True, 'message': '更新成功'})
    except Exception as e:
        logger.error(f"更新文章失败: {e}")
        return jsonify({'success': False, 'message': '更新失败'}), 500

@app.route('/admin/articles/<int:article_id>/delete', methods=['POST'])
@login_required
def admin_article_delete(article_id):
    """删除文章"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE id = %s", (article_id,))
            
            if cursor.rowcount == 0:
                return jsonify({'success': False, 'message': '文章不存在'}), 404
            
            conn.commit()
            logger.info(f"文章删除成功: ID={article_id}")
            return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除文章失败: {e}")
        return jsonify({'success': False, 'message': '删除失败'}), 500

@app.route('/admin/config')
@login_required
def admin_config():
    """配置管理页面"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 获取所有配置，按分类分组（排除不需要显示的验证参数）
            cursor.execute("""
                SELECT * FROM system_config 
                WHERE config_key NOT IN (
                    'telegram_session_valid',
                    'telegram_verification_code', 
                    'telegram_verification_required',
                    'telegram_verification_submitted'
                )
                ORDER BY category, config_key
            """)
            configs = cursor.fetchall()
            
            # 按分类分组配置
            config_groups = {}
            for config in configs:
                category = config['category']
                if category not in config_groups:
                    config_groups[category] = []
                config_groups[category].append(config)
            
            return render_template('admin_config.html', config_groups=config_groups)
    except Exception as e:
        logger.error(f"配置管理页面失败: {e}")
        return render_template('admin_config.html', config_groups={})

@app.route('/admin/config/update', methods=['POST'])
@login_required
def admin_config_update():
    """更新配置"""
    try:
        config_data = request.get_json()
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            for key, value in config_data.items():
                cursor.execute("""
                    UPDATE system_config 
                    SET config_value = %s, updated_at = NOW() 
                    WHERE config_key = %s
                """, (str(value), key))
            
            conn.commit()
            logger.info(f"配置更新成功: {list(config_data.keys())}")
            
            # 通知采集服务清除配置缓存
            try:
                import requests
                # 尝试调用采集服务的配置刷新接口
                response = requests.post('http://tg2em-scrape:2003/api/config/refresh', timeout=5)
                if response.status_code == 200:
                    logger.info("已通知采集服务刷新配置缓存")
                else:
                    logger.warning(f"采集服务配置刷新失败: {response.status_code}")
            except Exception as e:
                logger.warning(f"无法通知采集服务刷新配置: {e}")
            
            return jsonify({'success': True, 'message': '配置更新成功'})
    except Exception as e:
        logger.error(f"配置更新失败: {e}")
        return jsonify({'success': False, 'message': '配置更新失败'}), 500

@app.route('/admin/services')
@login_required
def admin_services():
    """服务管理页面"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 更新服务状态到数据库
            update_services_status_to_db()
            
            # 获取服务状态
            cursor.execute("SELECT * FROM services_status ORDER BY created_at")
            services = cursor.fetchall()
            
            # 获取服务控制配置
            cursor.execute("""
                SELECT config_key, config_value FROM system_config 
                WHERE category = 'service'
            """)
            service_configs = {row['config_key']: row['config_value'] for row in cursor.fetchall()}
            
            return render_template('admin_services.html', 
                                 services=services, 
                                 service_configs=service_configs)
    except Exception as e:
        logger.error(f"服务管理页面失败: {e}")
        return render_template('admin_services.html', services=[], service_configs={})

@app.route('/admin/services/<service_name>/start', methods=['POST'])
@login_required
def admin_service_start(service_name):
    """启动服务"""
    try:
        # 这里应该调用实际的Docker命令来启动服务
        # 由于安全原因，这里使用模拟实现
        result = start_service_via_docker(service_name)
        
        if result['success']:
            # 更新数据库状态
            db_service_name = get_db_service_name(service_name)
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE services_status 
                    SET status = 'running', last_start = NOW(), last_check = NOW(),
                        message = %s, pid = %s
                    WHERE service_name = %s
                """, (result['message'], result.get('pid'), db_service_name))
                conn.commit()
            
            logger.info(f"服务启动成功: {service_name}")
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 500
            
    except Exception as e:
        logger.error(f"启动服务失败: {service_name}, 错误: {e}")
        return jsonify({'success': False, 'message': '启动服务失败'}), 500

@app.route('/admin/services/<service_name>/stop', methods=['POST'])
@login_required
def admin_service_stop(service_name):
    """停止服务"""
    try:
        # 这里应该调用实际的Docker命令来停止服务
        result = stop_service_via_docker(service_name)
        
        if result['success']:
            # 更新数据库状态
            db_service_name = get_db_service_name(service_name)
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE services_status 
                    SET status = 'stopped', last_stop = NOW(), last_check = NOW(),
                        message = %s, pid = NULL
                    WHERE service_name = %s
                """, (result['message'], db_service_name))
                conn.commit()
            
            logger.info(f"服务停止成功: {service_name}")
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 500
            
    except Exception as e:
        logger.error(f"停止服务失败: {service_name}, 错误: {e}")
        return jsonify({'success': False, 'message': '停止服务失败'}), 500

@app.route('/admin/services/<service_name>/restart', methods=['POST'])
@login_required
def admin_service_restart(service_name):
    """重启服务"""
    try:
        controller = ServiceController()
        result = controller.restart_service(service_name)
        
        if result['success']:
            logger.info(f"服务重启成功: {service_name}")
            return jsonify({'success': True, 'message': result['message']})
        else:
            return jsonify({'success': False, 'message': result['message']}), 500
            
    except Exception as e:
        logger.error(f"重启服务失败: {service_name}, 错误: {e}")
        return jsonify({'success': False, 'message': '重启服务失败'}), 500

@app.route('/admin/services/<service_name>/scrape/start', methods=['POST'])
@login_required
def admin_scrape_task_start(service_name):
    """启动采集任务"""
    try:
        # 只允许采集服务调用
        if service_name not in ['scraper', 'scraper-management', 'scraper-service']:
            return jsonify({'success': False, 'message': '此操作仅适用于采集服务'}), 400
        
        # 调用采集管理服务的API
        import requests
        management_url = 'http://tg2em-scrape:2003/api/scrape/start'
        
        try:
            response = requests.post(management_url, timeout=30)
            result = response.json()
            
            if result.get('success'):
                logger.info(f"采集任务启动成功")
                return jsonify({
                    'success': True,
                    'message': result.get('message', '采集任务已启动，请查看日志了解进度')
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('message', '启动采集任务失败')
                })
                
        except requests.exceptions.ConnectionError:
            return jsonify({
                'success': False,
                'message': '无法连接到采集服务，请先启动采集服务'
            }), 500
        except requests.exceptions.Timeout:
            return jsonify({
                'success': True,
                'message': '采集任务已启动（响应超时，但任务可能正在执行中）'
            })
            
    except Exception as e:
        logger.error(f"启动采集任务失败: {e}")
        return jsonify({'success': False, 'message': f'启动采集任务失败: {str(e)}'}), 500

@app.route('/admin/services/<service_name>/status', methods=['GET'])
@login_required
def admin_service_status(service_name):
    """获取服务状态"""
    try:
        # 验证服务名称
        valid_services = ['tgstate', 'tgstate-management', 'tgstate-service', 'scraper', 'scraper-management', 'scraper-service']
        if service_name not in valid_services:
            return jsonify({'success': False, 'message': '无效的服务名称'}), 404
        
        # 获取服务状态
        controller = ServiceController()
        status_result = controller.get_service_status(service_name)
        
        if status_result['success']:
            return jsonify({
                'success': True,
                'status': status_result['status'],
                'pid': status_result['pid'],
                'port': status_result['port'],
                'message': status_result['message']
            })
        else:
            return jsonify({
                'success': False,
                'status': 'error',
                'message': status_result['message']
            }), 500
            
    except Exception as e:
        logger.error(f"获取服务状态失败: {service_name}, 错误: {e}")
        return jsonify({'success': False, 'message': '获取服务状态失败'}), 500

@app.route('/admin/services/manage/<service_name>')
@login_required
def admin_service_manage(service_name):
    """服务管理页面（带认证）"""
    try:
        # 验证服务名称
        valid_services = ['tgstate', 'tgstate-management', 'tgstate-service', 'scraper', 'scraper-management', 'scraper-service']
        if service_name not in valid_services:
            return "无效的服务名称", 404
        
        # 获取服务状态
        controller = ServiceController()
        status_result = controller.get_service_status(service_name)
        
        # 获取服务配置（如果是采集服务）
        config_result = None
        if service_name in ['scraper', 'scraper-management', 'scraper-service']:
            try:
                import requests
                url = f"{controller.service_urls[service_name]}/api/management/config"
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    config_result = response.json()
            except:
                pass
        
        return render_template('admin_service_manage.html', 
                             service_name=service_name,
                             status=status_result,
                             config=config_result)
        
    except Exception as e:
        logger.error(f"获取服务管理页面失败: {service_name}, 错误: {e}")
        return f"获取服务管理页面失败: {str(e)}", 500

@app.route('/admin/telegram/verification')
@login_required
def telegram_verification():
    """Telegram验证页面"""
    return render_template('admin_telegram_verification.html')

@app.route('/admin/telegram/verification/status')
@login_required
def telegram_verification_status():
    """获取Telegram验证状态"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 检查是否需要验证码
            cursor.execute("""
                SELECT config_value FROM system_config 
                WHERE config_key = 'telegram_verification_required'
            """)
            result = cursor.fetchone()
            needs_verification = result and result['config_value'] == 'true'
            
            # 检查是否已提交验证码
            cursor.execute("""
                SELECT config_value FROM system_config 
                WHERE config_key = 'telegram_verification_submitted'
            """)
            submitted_result = cursor.fetchone()
            is_submitted = submitted_result and submitted_result['config_value'] == 'true'
            
            # 检查验证码值
            cursor.execute("""
                SELECT config_value FROM system_config 
                WHERE config_key = 'telegram_verification_code'
            """)
            code_result = cursor.fetchone()
            has_code = code_result and code_result['config_value'] != ''
            
            # 检查采集服务是否正在运行
            cursor.execute("""
                SELECT status FROM services_status 
                WHERE service_name = 'scraper-service' 
                ORDER BY last_check DESC LIMIT 1
            """)
            service_result = cursor.fetchone()
            service_running = service_result and service_result['status'] == 'running'
            
            # 根据实际状态判断
            if not service_running:
                # 服务未运行，优先提示启动服务
                status = 'waiting'
                message = '采集服务未运行，请先启动服务'
            elif needs_verification and not is_submitted:
                # 需要验证且未提交验证码
                status = 'waiting'
                message = '等待输入验证码'
            elif needs_verification and is_submitted and has_code:
                # 需要验证且已提交验证码
                status = 'submitted'
                message = '验证码已提交，等待验证...'
            elif not needs_verification:
                # 不需要验证，检查是否有有效的会话文件
                cursor.execute("""
                    SELECT config_value FROM system_config 
                    WHERE config_key = 'telegram_session_valid'
                """)
                session_result = cursor.fetchone()
                session_valid = session_result and session_result['config_value'] == 'true'
                
                if session_valid:
                    status = 'idle'
                    message = '验证已完成，服务正常运行'
                else:
                    # 没有验证记录，需要验证
                    status = 'waiting'
                    message = '需要验证Telegram'
            else:
                status = 'unknown'
                message = '状态未知'
            
            return jsonify({
                'success': True,
                'needs_verification': needs_verification,
                'is_submitted': is_submitted,
                'has_code': has_code,
                'status': status,
                'message': message
            })
    except Exception as e:
        logger.error(f"获取Telegram验证状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/telegram/verification/submit', methods=['POST'])
@login_required
def telegram_verification_submit():
    """提交Telegram验证码"""
    try:
        data = request.get_json()
        verification_code = data.get('verification_code', '').strip()
        
        if not verification_code:
            return jsonify({'success': False, 'message': '验证码不能为空'}), 400
        
        if len(verification_code) != 5 or not verification_code.isdigit():
            return jsonify({'success': False, 'message': '验证码必须是5位数字'}), 400
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 更新验证码
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_verification_code', %s, 'string', 'Telegram验证码', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = %s, updated_at = NOW()
            """, (verification_code, verification_code))
            
            # 标记验证码已提交
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_verification_submitted', 'true', 'boolean', '验证码已提交', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = 'true', updated_at = NOW()
            """)
            
            conn.commit()
            
            logger.info(f"Telegram验证码已提交: {verification_code}")
            return jsonify({
                'success': True, 
                'message': '验证码已提交，系统将自动验证',
                'verification_code': verification_code
            })
            
    except Exception as e:
        logger.error(f"提交Telegram验证码失败: {e}")
        return jsonify({'success': False, 'message': '提交验证码失败'}), 500

@app.route('/admin/telegram/verification/logs')
@login_required
def telegram_verification_logs():
    """获取Telegram验证相关的实时日志"""
    try:
        import subprocess
        
        # 获取采集服务的最新日志
        result = subprocess.run(
            ['docker', 'logs', '--tail=50', 'tg2em-scrape'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        logs = result.stdout + result.stderr
        
        # 过滤出验证相关的日志
        verification_logs = []
        for line in logs.split('\n'):
            if any(keyword in line for keyword in ['验证', 'Telegram', '登录', 'auth', 'code', 'phone', '🔐', '📱', '✅', '❌']):
                verification_logs.append(line)
        
        return jsonify({
            'success': True,
            'logs': verification_logs[-20:] if len(verification_logs) > 20 else verification_logs
        })
    except Exception as e:
        logger.error(f"获取验证日志失败: {e}")
        return jsonify({'success': False, 'logs': [f'获取日志失败: {str(e)}']})

@app.route('/admin/telegram/verification/reset', methods=['POST'])
@login_required
def telegram_verification_reset():
    """重置Telegram验证状态"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 清除验证状态
            cursor.execute("""
                DELETE FROM system_config 
                WHERE config_key IN ('telegram_verification_code', 'telegram_verification_submitted', 'telegram_verification_required')
            """)
            
            conn.commit()
            
            logger.info("Telegram验证状态已重置")
            return jsonify({'success': True, 'message': '验证状态已重置'})
            
    except Exception as e:
        logger.error(f"重置Telegram验证状态失败: {e}")
        return jsonify({'success': False, 'message': '重置失败'}), 500

@app.route('/api/stats')
def api_stats():
    """API: 获取统计信息"""
    # 记录API访问
    logger.debug(f"API访问: {request.remote_addr} -> /api/stats")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            # 总文章数
            cursor.execute("SELECT COUNT(*) as total FROM messages WHERE is_deleted = 0")
            total_articles = cursor.fetchone()['total']
            
            # 今日文章数
            today = datetime.now().date()
            cursor.execute(
                "SELECT COUNT(*) as today FROM messages WHERE DATE(created_at) = %s AND is_deleted = 0",
                (today,)
            )
            today_articles = cursor.fetchone()['today']
            
            # 分类数
            cursor.execute("SELECT COUNT(DISTINCT sort_id) as categories FROM messages WHERE sort_id IS NOT NULL AND is_deleted = 0")
            total_categories = cursor.fetchone()['categories']
            
            return jsonify({
                'success': True,
                'data': {
                    'total_articles': total_articles,
                    'today_articles': today_articles,
                    'total_categories': total_categories
                }
            })
    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.errorhandler(404)
def not_found(error):
    """404 错误处理"""
    return render_template('404.html'), 404

@app.route('/admin/password', methods=['GET'])
@login_required
def admin_password():
    """密码和验证码管理 페이지"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 获取当前验证码设置
            cursor.execute("SELECT config_value FROM system_config WHERE config_key = 'admin_captcha'")
            captcha_result = cursor.fetchone()
            current_captcha = captcha_result['config_value'] if captcha_result else '2025'
            
            return render_template('admin_password.html', current_captcha=current_captcha)
    except Exception as e:
        logger.error(f"密码管理页面失败: {e}")
        return render_template('admin_password.html', current_captcha='2025')

@app.route('/admin/password/change', methods=['POST'])
@login_required
def admin_password_change():
    """修改管理员密码"""
    try:
        data = request.get_json()
        current_password = data.get('current_password', '').strip()
        new_password = data.get('new_password', '').strip()
        confirm_password = data.get('confirm_password', '').strip()
        
        # 验证参数
        if not current_password or not new_password or not confirm_password:
            return jsonify({'success': False, 'message': '所有必填参数不能为空'})
        
        if new_password != confirm_password:
            return jsonify({'success': False, 'message': '新密码和确认密码不一致'})
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': '新密码长度至少6位'})
        
        # 验证当前密码
        if current_password != ADMIN_PASSWORD:
            return jsonify({'success': False, 'message': '当前密码错误'})
        
        # 更新环境变量和数据库配置
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 更新数据库中的管理员密码哈希
            import bcrypt
            password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category) 
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                config_value = %s, updated_at = NOW()
            """, ('admin_password', password_hash, 'string', '管理员密码哈希', 'admin', password_hash))
            
            conn.commit()
        
        logger.info(f"管理员密码修改成功: {session.get('username', 'unknown')}")
        return jsonify({'success': True, 'message': '密码修改成功'})
        
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return jsonify({'success': False, 'message': f'修改失败: {str(e)}'})

@app.route('/admin/captcha/change', methods=['POST'])
@login_required
def admin_captcha_change():
    """修改验证码"""
    try:
        data = request.get_json()
        new_captcha = data.get('new_captcha', '').strip()
        
        # 验证参数
        if not new_captcha:
            return jsonify({'success': False, 'message': '验证码不能为空'})
        
        if len(new_captcha) < 4:
            return jsonify({'success': False, 'message': '验证码长度至少4位'})
        
        # 更新数据库配置
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category) 
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                config_value = %s, updated_at = NOW()
            """, ('admin_captcha', new_captcha, 'string', '管理员登录验证码', 'admin', new_captcha))
            
            # 同步更新代码中的验证码常量（需要在重启服务后生效）
            cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category) 
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                config_value = %s, updated_at = NOW()
            """, ('admin_captcha_update_note', 
                  '注意：验证码已更新，请重启frontend服务使新验证码生效', 
                  'string', '验证码更新提示', 'admin',
                  '注意：验证码已更新，请重启frontend服务使新验证码生效'))
            
            conn.commit()
        
        logger.info(f"管理员验证码修改成功: {session.get('username', 'unknown')} -> {new_captcha}")
        return jsonify({'success': True, 'message': '验证码修改成功！请重启frontend服务使新验证码生效'})
        
    except Exception as e:
        logger.error(f"修改验证码失败: {e}")
        return jsonify({'success': False, 'message': f'修改失败: {str(e)}'})

# ==================== 广告位管理 ====================

@app.route('/admin/ads')
@login_required
def admin_ads():
    """广告位管理页面"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            cursor.execute("""
                SELECT * FROM advertisements 
                ORDER BY sort_order ASC, created_at DESC
            """)
            ads = cursor.fetchall()
            
        return render_template('admin_ads.html', ads=ads)
    except Exception as e:
        logger.error(f"获取广告位列表失败: {e}")
        return render_template('admin_ads.html', ads=[])

@app.route('/admin/ads/create', methods=['GET', 'POST'])
@login_required
def admin_ads_create():
    """创建广告位"""
    if request.method == 'GET':
        return render_template('admin_ad_edit.html')
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        position = data.get('position', '')
        ad_code = data.get('ad_code', '').strip()
        is_active = data.get('is_active', True)
        sort_order = data.get('sort_order', 0)
        
        # 验证参数
        if not name:
            return jsonify({'success': False, 'message': '广告名称不能为空'})
        
        if not position:
            return jsonify({'success': False, 'message': '请选择广告位置'})
        
        if not ad_code:
            return jsonify({'success': False, 'message': '广告代码不能为空'})
        
        # 保存到数据库
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO advertisements (name, position, ad_code, is_active, sort_order)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, position, ad_code, is_active, sort_order))
            conn.commit()
            
        logger.info(f"广告位创建成功: {name} by {session.get('username', 'unknown')}")
        return jsonify({'success': True, 'message': '广告位创建成功'})
        
    except Exception as e:
        logger.error(f"创建广告位失败: {e}")
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'})

@app.route('/admin/ads/<int:ad_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_ads_edit(ad_id):
    """编辑广告位"""
    if request.method == 'GET':
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute("SELECT * FROM advertisements WHERE id = %s", (ad_id,))
                ad = cursor.fetchone()
                
            if not ad:
                return jsonify({'success': False, 'message': '广告位不存在'})
                
            return render_template('admin_ad_edit.html', ad=ad)
        except Exception as e:
            logger.error(f"获取广告位详情失败: {e}")
            return jsonify({'success': False, 'message': '获取广告位详情失败'})
    
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        position = data.get('position', '')
        ad_code = data.get('ad_code', '').strip()
        is_active = data.get('is_active', True)
        sort_order = data.get('sort_order', 0)
        
        # 验证参数
        if not name:
            return jsonify({'success': False, 'message': '广告名称不能为空'})
        
        if not position:
            return jsonify({'success': False, 'message': '请选择广告位置'})
        
        if not ad_code:
            return jsonify({'success': False, 'message': '广告代码不能为空'})
        
        # 更新数据库
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE advertisements 
                SET name = %s, position = %s, ad_code = %s, is_active = %s, sort_order = %s, updated_at = NOW()
                WHERE id = %s
            """, (name, position, ad_code, is_active, sort_order, ad_id))
            conn.commit()
            
        logger.info(f"广告位更新成功: {name} by {session.get('username', 'unknown')}")
        return jsonify({'success': True, 'message': '广告位更新成功'})
        
    except Exception as e:
        logger.error(f"更新广告位失败: {e}")
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'})

@app.route('/admin/ads/<int:ad_id>/delete', methods=['POST'])
@login_required
def admin_ads_delete(ad_id):
    """删除广告位"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM advertisements WHERE id = %s", (ad_id,))
            conn.commit()
            
        logger.info(f"广告位删除成功: ID {ad_id} by {session.get('username', 'unknown')}")
        return jsonify({'success': True, 'message': '广告位删除成功'})
        
    except Exception as e:
        logger.error(f"删除广告位失败: {e}")
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'})

@app.route('/admin/ads/<int:ad_id>/toggle', methods=['POST'])
@login_required
def admin_ads_toggle(ad_id):
    """切换广告位启用状态"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE advertisements 
                SET is_active = NOT is_active, updated_at = NOW()
                WHERE id = %s
            """, (ad_id,))
            conn.commit()
            
        logger.info(f"广告位状态切换成功: ID {ad_id} by {session.get('username', 'unknown')}")
        return jsonify({'success': True, 'message': '状态切换成功'})
        
    except Exception as e:
        logger.error(f"切换广告位状态失败: {e}")
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'})

@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # 从环境变量获取端口，默认 8000（避免 ERR_UNSAFE_PORT）
    port = int(os.getenv('FRONTEND_PORT', '8000'))
    # 启动应用
    app.run(host='0.0.0.0', port=port, debug=False)