#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tg2emall 前端展示系统
基于 Flask 的简单博客展示系统
"""

import os
import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, g
import aiomysql
import asyncio
from functools import wraps
import yaml
import threading

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tg2emall-secret-key')

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

# 全局数据库连接池
mysql_pool = None
event_loop = None
loop_thread = None

def get_or_create_event_loop():
    """获取或创建事件循环"""
    global event_loop, loop_thread
    
    if event_loop is None or event_loop.is_closed():
        # 在单独线程中创建事件循环
        def run_loop():
            global event_loop
            event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(event_loop)
            return event_loop
        
        loop_thread = threading.Thread(target=run_loop)
        loop_thread.start()
        loop_thread.join(timeout=1)  # 等待线程启动
        
        # 初始化连接池
        import asyncio
        import threading
        
        def init_pool():
            global event_loop
            if event_loop:
                asyncio.run_coroutine_threadsafe(init_mysql_pool(), event_loop)
        
        init_thread = threading.Thread(target=init_pool)
        init_thread.start()
        init_thread.join(timeout=5)
    
    return event_loop

def async_db_operation(func):
    """异步数据库操作装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        loop = get_or_create_event_loop()
        if loop and not loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(func(*args, **kwargs), loop)
            try:
                return future.result(timeout=30)  # 30秒超时
            except Exception as e:
                logger.error(f"异步操作失败: {e}")
                return None
        else:
            logger.error("事件循环不可用")
            return None
    return wrapper

async def init_mysql_pool():
    """初始化 MySQL 连接池"""
    global mysql_pool
    try:
        mysql_pool = await aiomysql.create_pool(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            db=DB_CONFIG['database'],
            charset=DB_CONFIG['charset'],
            minsize=1,
            maxsize=10,
            autocommit=True
        )
        logger.info("MySQL 连接池初始化成功")
    except Exception as e:
        logger.error(f"MySQL 连接池初始化失败: {e}")

async def get_articles(limit=20, offset=0, category=None):
    """获取文章"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                if category:
                    sql = """
                        SELECT * FROM messages 
                        WHERE sort_id = %s 
                        ORDER BY created_at DESC 
                        LIMIT %s OFFSET %s
                    """
                    await cursor.execute(sql, (category, limit, offset))
                else:
                    sql = """
                        SELECT * FROM messages 
                        ORDER BY created_at DESC 
                        LIMIT %s OFFSET %s
                    """
                    await cursor.execute(sql, (limit, offset))
                
                articles = await cursor.fetchall()
                return articles
    except Exception as e:
        logger.error(f"获取文章失败: {e}")
        return []

async def get_article_by_id(article_id):
    """根据ID获取文章"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT * FROM messages WHERE id = %s"
                await cursor.execute(sql, (article_id,))
                article = await cursor.fetchone()
                return article
    except Exception as e:
        logger.error(f"获取文章失败: {e}")
        return None

async def get_categories():
    """获取分类统计"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT sort_id, COUNT(*) as count 
                    FROM messages 
                    WHERE sort_id IS NOT NULL 
                    GROUP BY sort_id 
                    ORDER BY count DESC
                """
                await cursor.execute(sql)
                categories = await cursor.fetchall()
                return categories
    except Exception as e:
        logger.error(f"获取分类失败: {e}")
        return []

async def get_recent_articles(limit=5):
    """获取最新文章"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT id, title, created_at 
                    FROM messages 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """
                await cursor.execute(sql, (limit,))
                articles = await cursor.fetchall()
                return articles
    except Exception as e:
        logger.error(f"获取最新文章失败: {e}")
        return []

async def get_published_articles(limit=10, offset=0):
    """获取已发布的文章"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT * FROM messages 
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """
                await cursor.execute(sql, (limit, offset))
                articles = await cursor.fetchall()
                return articles
    except Exception as e:
        logger.error(f"获取已发布文章失败: {e}")
        return []

async def search_articles(query, limit=10, offset=0):
    """搜索文章"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT * FROM messages 
                    WHERE (title LIKE %s OR content LIKE %s OR tags LIKE %s)
                    ORDER BY created_at DESC 
                    LIMIT %s OFFSET %s
                """
                search_term = f"%{query}%"
                await cursor.execute(sql, (search_term, search_term, search_term, limit, offset))
                articles = await cursor.fetchall()
                return articles
    except Exception as e:
        logger.error(f"搜索文章失败: {e}")
        return []

async def count_search_results(query):
    """统计搜索结果数量"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT COUNT(*) as count FROM messages 
                    WHERE (title LIKE %s OR content LIKE %s OR tags LIKE %s)
                """
                search_term = f"%{query}%"
                await cursor.execute(sql, (search_term, search_term, search_term))
                result = await cursor.fetchone()
                return result['count']
    except Exception as e:
        logger.error(f"统计搜索结果失败: {e}")
        return 0

async def count_articles():
    """统计文章数量"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT COUNT(*) as count FROM messages"
                await cursor.execute(sql)
                result = await cursor.fetchone()
                return result['count']
    except Exception as e:
        logger.error(f"统计文章数量失败: {e}")
        return 0

@app.route('/')
@async_db_operation
async def index():
    """首页"""
    # 获取最近20条数据
    articles = await get_articles(20, 0)
    categories = await get_categories()
    recent_articles = await get_recent_articles(5)
    
    return render_template('index.html', 
                         articles=articles, 
                         categories=categories,
                         recent_articles=recent_articles)

@app.route('/search')
@async_db_operation
async def search():
    """搜索页面"""
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    
    if query:
        # 执行搜索
        articles = await search_articles(query, per_page, offset)
        total_count = await count_search_results(query)
    else:
        # 显示所有文章
        articles = await get_articles(per_page, offset)
        total_count = await count_articles()
    
    categories = await get_categories()
    recent_articles = await get_recent_articles(5)
    ads = await get_advertisements('search_list')
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
@async_db_operation
async def article_detail(article_id):
    """文章详情页"""
    article = await get_article_by_id(article_id)
    if not article:
        return "文章不存在", 404
    
    recent_articles = await get_recent_articles(5)
    categories = await get_categories()
    ads = await get_advertisements('article_detail')
    
    return render_template('article.html', 
                         article=article,
                         recent_articles=recent_articles,
                         categories=categories,
                         advertisement_ads=ads)

@app.route('/api/articles')
@async_db_operation
async def api_articles():
    """API: 获取文章列表"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    offset = (page - 1) * limit
    
    articles = await get_published_articles(limit, offset)
    
    return jsonify({
        'success': True,
        'data': articles,
        'page': page,
        'limit': limit
    })

@app.route('/api/article/<int:article_id>')
@async_db_operation
async def api_article_detail(article_id):
    """API: 获取文章详情"""
    article = await get_article_by_id(article_id)
    if not article:
        return jsonify({'success': False, 'message': '文章不存在'}), 404
    
    return jsonify({
        'success': True,
        'data': article
    })

@app.route('/api/categories')
@async_db_operation
async def api_categories():
    """API: 获取分类列表"""
    categories = await get_categories()
    return jsonify({
        'success': True,
        'data': categories
    })

@app.route('/api/stats')
@async_db_operation
async def api_stats():
    """API: 获取统计信息"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 总文章数
                await cursor.execute("SELECT COUNT(*) as total FROM messages")
                total_articles = (await cursor.fetchone())['total']
                
                # 今日文章数
                today = datetime.now().date()
                await cursor.execute(
                    "SELECT COUNT(*) as today FROM messages WHERE DATE(created_at) = %s",
                    (today,)
                )
                today_articles = (await cursor.fetchone())['today']
                
                # 分类数
                await cursor.execute("SELECT COUNT(DISTINCT sort_id) as categories FROM messages WHERE sort_id IS NOT NULL")
                total_categories = (await cursor.fetchone())['categories']
                
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

@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    return render_template('500.html'), 500

async def get_advertisements(position):
    """获取指定位置的广告"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = """
                    SELECT * FROM advertisements 
                    WHERE (position = %s OR position = 'both') AND is_active = 1 
                    ORDER BY sort_order DESC, created_at DESC
                """
                await cursor.execute(sql, (position,))
                ads = await cursor.fetchall()
                return ads
    except Exception as e:
        logger.error(f"获取广告失败: {e}")
        return []

if __name__ == '__main__':
    # 启动应用
    app.run(host='0.0.0.0', port=5000, debug=False)
