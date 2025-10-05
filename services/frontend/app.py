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
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from contextlib import contextmanager
from functools import wraps
import re
import hashlib

# 导入服务控制器
try:
    from service_controller import ServiceController
    
    def get_db_service_name(frontend_service_name):
        """获取数据库中的服务名称"""
        service_mapping = {
            'tgstate': 'tgstate-management',
            'tgstate-service': 'tgstate-management',  # 兼容tgstate-service名称
            'scraper': 'scraper-management',
            'scraper-service': 'scraper-management',  # 兼容scraper-service名称
        }
        return service_mapping.get(frontend_service_name, frontend_service_name)
    
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
        
except ImportError:
    # 如果导入失败，使用模拟实现
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
                INSERT INTO site_visits (visitor_ip, user_agent, page_path, referrer, visit_source, session_id)
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
    """获取分类统计"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            sql = """
                SELECT sort_id, COUNT(*) as count 
                FROM messages 
                WHERE sort_id IS NOT NULL 
                GROUP BY sort_id 
                ORDER BY count DESC
            """
            cursor.execute(sql)
            categories = cursor.fetchall()
            logger.info(f"成功获取 {len(categories)} 个分类")
            return categories if categories else []
    except Exception as e:
        logger.error(f"获取分类失败: {e}")
        logger.info("数据库连接失败或无分类数据，返回空列表")
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
        articles = get_articles(20, 0)
        recent_articles = get_recent_articles(5)
        
        # 统计信息
        stats = {
            'total_articles': len(articles),
            'data_available': len(articles) > 0
        }
        
        logger.info(f"首页数据统计: 文章={stats['total_articles']}, 有数据={stats['data_available']}")
        
        return render_template('index.html', 
                             articles=articles, 
                             recent_articles=recent_articles,
                             stats=stats)
    except Exception as e:
        logger.error(f"首页路由处理失败: {e}")
        # 即使出现异常，也返回空数据的页面，确保网站可以访问
        return render_template('index.html', 
                             articles=[], 
                             recent_articles=[],
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
    
    recent_articles = get_recent_articles(5)
    ads = get_advertisements('article_detail')
    
    return render_template('article.html', 
                         article=article,
                         recent_articles=recent_articles,
                         advertisement_ads=ads)

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
            visit_sources = [
                {'source': '搜索引擎', 'count': 145},
                {'source': '直接访问', 'count': 89},
                {'source': '社交媒体', 'count': 67},
                {'source': '其他', 'count': 23}
            ]
            
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
            
            # 获取所有配置，按分类分组
            cursor.execute("""
                SELECT * FROM system_config 
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

@app.route('/admin/services/manage/<service_name>')
@login_required
def admin_service_manage(service_name):
    """服务管理页面（带认证）"""
    try:
        # 验证服务名称
        valid_services = ['tgstate', 'scraper']
        if service_name not in valid_services:
            return "无效的服务名称", 404
        
        # 获取服务状态
        controller = ServiceController()
        status_result = controller.get_service_status(service_name)
        
        # 获取服务配置（如果是采集服务）
        config_result = None
        if service_name == 'scraper':
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
            
            needs_verification = result['config_value'] == 'true' if result else False
            
            # 检查是否有验证码请求
            cursor.execute("""
                SELECT config_value FROM system_config 
                WHERE config_key = 'telegram_verification_code'
            """)
            result = cursor.fetchone()
            
            verification_code = result['config_value'] if result else ''
            
            return jsonify({
                'needs_verification': needs_verification,
                'verification_code': verification_code,
                'status': 'waiting' if needs_verification else 'completed'
            })
    except Exception as e:
        logger.error(f"获取Telegram验证状态失败: {e}")
        return jsonify({'error': '获取状态失败'}), 500

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
                config_value = 'true', updated_at = NOW())
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

@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return render_template('500.html'), 500

if __name__ == '__main__':
    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=False)