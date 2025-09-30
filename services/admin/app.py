#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
tg2em 后台管理系统
提供内容管理、广告配置、用户管理等功能
"""

import os
import json
import logging
import aiomysql
import asyncio
import secrets
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import quote, unquote

import bcrypt
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash, abort
from werkzeug.utils import secure_filename

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tg2emall-admin-secret-key-2024')

@app.context_processor
def inject_template_vars():
    """注入模板变量"""
    return {
        'current_time': datetime.now()
    }

# MySQL 连接池
mysql_pool = None

# 异步数据库操作装饰器
def async_db_operation(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper

async def init_mysql_pool():
    """初始化 MySQL 连接池"""
    global mysql_pool
    try:
        mysql_pool = await aiomysql.create_pool(
            host=os.environ.get('MYSQL_HOST', 'mysql'),
            port=int(os.environ.get('MYSQL_PORT', 3306)),
            user=os.environ.get('MYSQL_USER', 'tg2em'),
            password=os.environ.get('MYSQL_PASSWORD', 'tg2em2025'),
            db=os.environ.get('MYSQL_DATABASE', 'tg2em'),
            minsize=1,
            maxsize=10,
            autocommit=False
        )
        logger.info("MySQL 连接池初始化成功")
    except Exception as e:
        logger.error(f"MySQL 连接池初始化失败: {e}")

# 认证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# 数据库操作函数
async def verify_admin_user(username, password):
    """验证管理员用户"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT * FROM admin_users WHERE username = %s AND is_active = 1"
                await cursor.execute(sql, (username,))
                user = await cursor.fetchone()
                
                if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
                    # 更新最后登录时间
                    await cursor.execute(
                        "UPDATE admin_users SET last_login = NOW() WHERE id = %s",
                        (user['id'],)
                    )
                    await conn.commit()
                    return user
                return None
    except Exception as e:
        logger.error(f"验证用户失败: {e}")
        return None

async def get_messages(page=1, per_page=20, search=''):
    """获取消息列表"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                offset = (page - 1) * per_page
                
                if search:
                    sql = """
                        SELECT * FROM messages 
                        WHERE (title LIKE %s OR content LIKE %s OR tags LIKE %s)
                        ORDER BY is_pinned DESC, created_at DESC 
                        LIMIT %s OFFSET %s
                    """
                    search_term = f"%{search}%"
                    await cursor.execute(sql, (search_term, search_term, search_term, per_page, offset))
                else:
                    sql = """
                        SELECT * FROM messages 
                        ORDER BY is_pinned DESC, created_at DESC 
                        LIMIT %s OFFSET %s
                    """
                    await cursor.execute(sql, (per_page, offset))
                
                messages = await cursor.fetchall()
                
                # 统计总数
                if search:
                    count_sql = """
                        SELECT COUNT(*) as count FROM messages 
                        WHERE (title LIKE %s OR content LIKE %s OR tags LIKE %s)
                    """
                    await cursor.execute(count_sql, (search_term, search_term, search_term))
                else:
                    count_sql = "SELECT COUNT(*) as count FROM messages"
                    await cursor.execute(count_sql)
                
                result = await cursor.fetchone()
                total = result['count']
                
                return messages, total
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}")
        return [], 0

async def get_message_by_id(message_id):
    """根据ID获取消息"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT * FROM messages WHERE id = %s"
                await cursor.execute(sql, (message_id,))
                message = await cursor.fetchone()
                return message
    except Exception as e:
        logger.error(f"获取消息失败: {e}")
        return None

async def update_message(message_id, title, content, tags, sort_id, is_pinned):
    """更新消息"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    UPDATE messages 
                    SET title = %s, content = %s, tags = %s, sort_id = %s, is_pinned = %s, updated_at = NOW()
                    WHERE id = %s
                """
                await cursor.execute(sql, (title, content, tags, sort_id, is_pinned, message_id))
                await conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"更新消息失败: {e}")
        return False

async def delete_message(message_id):
    """软删除消息"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "UPDATE messages SET is_deleted = 1, updated_at = NOW() WHERE id = %s"
                await cursor.execute(sql, (message_id,))
                await conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"删除消息失败: {e}")
        return False

async def toggle_pin_message(message_id, is_pinned):
    """切换消息置顶状态"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "UPDATE messages SET is_pinned = %s, updated_at = NOW() WHERE id = %s"
                await cursor.execute(sql, (is_pinned, message_id))
                await conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"切换置顶状态失败: {e}")
        return False

async def get_advertisements():
    """获取广告列表"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT * FROM advertisements ORDER BY sort_order DESC, created_at DESC"
                await cursor.execute(sql)
                ads = await cursor.fetchall()
                return ads
    except Exception as e:
        logger.error(f"获取广告列表失败: {e}")
        return []

async def get_advertisement_by_id(ad_id):
    """根据ID获取广告"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                sql = "SELECT * FROM advertisements WHERE id = %s"
                await cursor.execute(sql, (ad_id,))
                ad = await cursor.fetchone()
                return ad
    except Exception as e:
        logger.error(f"获取广告失败: {e}")
        return None

async def create_advertisement(name, position, ad_code, sort_order):
    """创建广告"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    INSERT INTO advertisements (name, position, ad_code, sort_order, is_active)
                    VALUES (%s, %s, %s, %s, 1)
                """
                await cursor.execute(sql, (name, position, ad_code, sort_order))
                await conn.commit()
                return cursor.lastrowid
    except Exception as e:
        logger.error(f"创建广告失败: {e}")
        return None

async def update_advertisement(ad_id, name, position, ad_code, sort_order, is_active):
    """更新广告"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = """
                    UPDATE advertisements 
                    SET name = %s, position = %s, ad_code = %s, sort_order = %s, is_active = %s, updated_at = NOW()
                    WHERE id = %s
                """
                await cursor.execute(sql, (name, position, ad_code, sort_order, is_active, ad_id))
                await conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"更新广告失败: {e}")
        return False

async def delete_advertisement(ad_id):
    """删除广告"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "DELETE FROM advertisements WHERE id = %s"
                await cursor.execute(sql, (ad_id,))
                await conn.commit()
                return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"删除广告失败: {e}")
        return False

async def get_statistics():
    """获取统计数据"""
    try:
        async with mysql_pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute("SELECT * FROM v_statistics")
                stats = await cursor.fetchone()
                return stats or {}
    except Exception as e:
        logger.error(f"获取统计数据失败: {e}")
        return {}

# 路由
@app.route('/admin')
def admin_index():
    """后台首页重定向"""
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/login', methods=['GET', 'POST'])
@async_db_operation
async def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if username and password:
            user = await verify_admin_user(username, password)
            if user:
                session['admin_user'] = {
                    'id': user['id'],
                    'username': user['username']
                }
                flash('登录成功！', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('用户名或密码错误！', 'error')
        else:
            flash('请输入用户名和密码！', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def logout():
    """退出登录"""
    session.pop('admin_user', None)
    flash('已退出登录！', 'info')
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
@async_db_operation
async def admin_dashboard():
    """后台仪表盘"""
    stats = await get_statistics()
    recent_messages, _ = await get_messages(page=1, per_page=10)
    return render_template('admin/dashboard.html', stats=stats, recent_messages=recent_messages)

@app.route('/admin/messages')
@login_required
@async_db_operation
async def admin_messages():
    """消息管理页面"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    
    if page < 1:
        page = 1
    
    messages, total = await get_messages(page=page, search=search)
    total_pages = (total + 19) // 20  # per_page = 20
    
    return render_template('admin/messages.html', 
                         messages=messages, 
                         current_page=page,
                         total_pages=total_pages,
                         total=total,
                         search=search)

@app.route('/admin/messages/<int:message_id>')
@login_required
@async_db_operation
async def admin_message_detail(message_id):
    """消息详情页面"""
    message = await get_message_by_id(message_id)
    if not message:
        abort(404)
    
    return render_template('admin/message_detail.html', message=message)

@app.route('/admin/messages/<int:message_id>/edit', methods=['POST'])
@login_required
@async_db_operation
async def admin_message_edit(message_id):
    """编辑消息"""
    message = await get_message_by_id(message_id)
    if not message:
        return jsonify({'success': False, 'message': '消息不存在'})
    
    title = request.form.get('title', '').strip()
    content = request.form.get('content', '').strip()
    tags = request.form.get('tags', '').strip()
    sort_id = request.form.get('sort_id', type=int) or None
    is_pinned = request.form.get('is_pinned', type=bool) or False
    
    if not title or not content:
        return jsonify({'success': False, 'message': '标题和内容不能为空'})
    
    success = await update_message(message_id, title, content, tags, sort_id, is_pinned)
    
    if success:
        return jsonify({'success': True, 'message': '更新成功'})
    else:
        return jsonify({'success': False, 'message': '更新失败'})

@app.route('/admin/messages/<int:message_id>/delete', methods=['POST'])
@login_required
@async_db_operation
async def admin_message_delete(message_id):
    """删除消息"""
    success = await delete_message(message_id)
    
    if success:
        return jsonify({'success': True, 'message': '删除成功'})
    else:
        return jsonify({'success': False, 'message': '删除失败'})

@app.route('/admin/messages/<int:message_id>/toggle_pin', methods=['POST'])
@login_required
@async_db_operation
async def admin_message_toggle_pin(message_id):
    """切换置顶状态"""
    message = await get_message_by_id(message_id)
    if not message:
        return jsonify({'success': False, 'message': '消息不存在'})
    
    new_pin_status = not message['is_pinned']
    success = await toggle_pin_message(message_id, new_pin_status)
    
    if success:
        return jsonify({'success': True, 'message': '置顶状态更新成功', 'is_pinned': new_pin_status})
    else:
        return jsonify({'success': False, 'message': '置顶状态更新失败'})

@app.route('/admin/advertisements')
@login_required
@async_db_operation
async def admin_advertisements():
    """广告管理页面"""
    ads = await get_advertisements()
    return render_template('admin/advertisements.html', advertisements=ads)

@app.route('/admin/advertisements/create', methods=['POST'])
@login_required
@async_db_operation
async def admin_advertisement_create():
    """创建广告"""
    name = request.form.get('name', '').strip()
    position = request.form.get('position', '').strip()
    ad_code = request.form.get('ad_code', '').strip()
    sort_order = request.form.get('sort_order', type=int) or 0
    
    if not name or not position or not ad_code:
        return jsonify({'success': False, 'message': '请填写所有必需字段'})
    
    if position not in ['search_list', 'article_detail', 'both']:
        return jsonify({'success': False, 'message': '请选择有效的广告位置'})
    
    ad_id = await create_advertisement(name, position, ad_code, sort_order)
    
    if ad_id:
        return jsonify({'success': True, 'message': '广告创建成功', 'ad_id': ad_id})
    else:
        return jsonify({'success': False, 'message': '广告创建失败'})

@app.route('/admin/advertisements/<int:ad_id>/edit', methods=['POST'])
@login_required
@async_db_operation  
async def admin_advertisement_edit(ad_id):
    """编辑广告"""
    advertisement = await get_advertisement_by_id(ad_id)
    if not advertisement:
        return jsonify({'success': False, 'message': '广告不存在'})
    
    name = request.form.get('name', '').strip()
    position = request.form.get('position', '').strip()
    ad_code = request.form.get('ad_code', '').strip()
    sort_order = request.form.get('sort_order', type=int) or 0
    is_active = request.form.get('is_active', type=bool) or False
    
    if not name or not position or not ad_code:
        return jsonify({'success': False, 'message': '请填写所有必需字段'})
    
    if position not in ['search_list', 'article_detail', 'both']:
        return jsonify({'success': False, 'message': '请选择有效的广告位置'})
    
    success = await update_advertisement(ad_id, name, position, ad_code, sort_order, is_active)
    
    if success:
        return jsonify({'success': True, 'message': '广告更新成功'})
    else:
        return jsonify({'success': False, 'message': '广告更新失败'})

@app.route('/admin/advertisements/<int:ad_id>/delete', methods=['POST'])
@login_required
@async_db_operation
async def admin_advertisement_delete(ad_id):
    """删除广告"""
    success = await delete_advertisement(ad_id)
    
    if success:
        return jsonify({'success': True, 'message': '广告删除成功'})
    else:
        return jsonify({'success': False, 'message': '广告删除失败'})

@app.route('/admin/profile')
@login_required
def admin_profile():
    """个人资料页面"""
    return render_template('admin/profile.html', user=session['admin_user'])

@app.route('/admin/change_password', methods=['POST'])
@login_required 
@async_db_operation
async def admin_change_password():
    """修改密码"""
    current_password = request.form.get('current_password', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': '请填写所有字段'})
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': '新密码两次输入不一致'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密码长度至少6位'})
    
    # 验证当前密码
    user = await verify_admin_user(session['admin_user']['username'], current_password)
    if not user:
        return jsonify({'success': False, 'message': '当前密码错误'})
    
    # 更新密码
    try:
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        async with mysql_pool.acquire() as conn:
            async with conn.cursor() as cursor:
                sql = "UPDATE admin_users SET password = %s, updated_at = NOW() WHERE id = %s"
                await cursor.execute(sql, (password_hash, user['id']))
                await conn.commit()
        
        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return jsonify({'success': False, 'message': '密码修改失败'})

# API 接口
@app.route('/api/admin/statistics')
@login_required
@async_db_operation
async def api_admin_statistics():
    """API: 获取统计数据"""
    stats = await get_statistics()
    return jsonify({'success': True, 'data': stats})

@app.route('/api/admin/messages/<int:message_id>/toggle_pin', methods=['POST'])
@login_required
@async_db_operation
async def api_admin_toggle_pin(message_id):
    """API: 切换置顶状态"""
    message = await get_message_by_id(message_id)
    if not message:
        return jsonify({'success': False, 'message': '消息不存在'})
    
    new_pin_status = not message['is_pinned']
    success = await toggle_pin_message(message_id, new_pin_status)
    
    if success:
        return jsonify({'success': True, 'is_pinned': new_pin_status})
    else:
        return jsonify({'success': False, 'message': '操作失败'})

# 错误处理
@app.errorhandler(404)
def page_not_found(error):
    return render_template('admin/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('admin/500.html'), 500

# 应用启动
if __name__ == '__main__':
    # 初始化数据库连接
    asyncio.run(init_mysql_pool())
    
    # 启动应用
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    app.run(host='0.0.0.0', port=port, debug=debug)
