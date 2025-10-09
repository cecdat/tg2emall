import os
import logging
from logging.handlers import RotatingFileHandler
import asyncio
import yaml
from telethon import TelegramClient
from datetime import datetime, timedelta
import aiomysql
from urllib.parse import quote
import aiohttp
from PIL import Image
import signal
import sys

# 限制并发数为 5
semaphore = asyncio.Semaphore(5)

# 日志函数
def setup_logging(config):
    """配置日志"""
    logging_config = config["logging"]["scrape"]
    os.makedirs(os.path.dirname(logging_config["filename"]), exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, logging_config["level"]),
        format=logging_config["format"],
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                logging_config["filename"],
                maxBytes=logging_config["max_bytes"],
                backupCount=logging_config["backup_count"]
            )
        ]
    )

# 加载配置文件
try:
    with open("config.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    logging.error("配置文件 config.yaml 未找到")
    exit(1)
except yaml.YAMLError as e:
    logging.error(f"配置文件解析错误: {e}")
    exit(1)

# 配置日志
setup_logging(config)

# 全局变量
client = None
mysql_pool = None
shutdown_requested = False

def signal_handler(signum, frame):
    """处理退出信号"""
    global shutdown_requested
    logging.info(f"收到退出信号 {signum}，准备优雅退出...")
    shutdown_requested = True
    if client:
        asyncio.create_task(client.disconnect())

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def init_mysql_pool():
    """初始化 MySQL 连接池"""
    global mysql_pool
    mysql_config = config["mysql"]
    mysql_pool = await aiomysql.create_pool(
        host=mysql_config["host"],
        port=mysql_config["port"],
        user=mysql_config["user"],
        password=mysql_config["password"],
        db=mysql_config["database"],
        autocommit=True,
        minsize=1,
        maxsize=10
    )
    logging.info("MySQL 连接池初始化成功")

class MySQLConnectionManager:
    """异步上下文管理器，用于管理 MySQL 连接"""
    def __init__(self):
        self.conn = None

    async def __aenter__(self):
        global mysql_pool
        if mysql_pool is None:
            await init_mysql_pool()
        self.conn = await mysql_pool.acquire()
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        global mysql_pool
        if self.conn:
            await mysql_pool.release(self.conn)

async def close_mysql_pool():
    """关闭 MySQL 连接池"""
    global mysql_pool
    if mysql_pool is not None:
        mysql_pool.close()
        await mysql_pool.wait_closed()
        logging.info("MySQL 连接池已关闭")

async def is_message_processed(channel_id, message_id):
    """检查消息是否已被处理（基于 channel_id 和 message_id）"""
    try:
        async with MySQLConnectionManager() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "SELECT 1 FROM processed_messages WHERE channel_id = %s AND message_id = %s",
                    (channel_id, message_id)
                )
                result = await cursor.fetchone()
                return result is not None
    except Exception as e:
        logging.error(f"检查消息是否已处理时发生错误: {e}")
        return False

async def mark_message_processed(channel_id, message_id):
    """将消息 ID 标记为已处理（基于 channel_id 和 message_id）"""
    try:
        async with MySQLConnectionManager() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO processed_messages (channel_id, message_id, created_at) VALUES (%s, %s, NOW())",
                    (channel_id, message_id)
                )
    except Exception as e:
        logging.error(f"标记消息为已处理时发生错误: {e}")

async def save_message(title, content, tags, sort_id=None, image_url=None):
    """将消息保存到 MySQL 数据库"""
    try:
        async with MySQLConnectionManager() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "INSERT INTO messages (title, content, tags, sort_id, image_url) VALUES (%s, %s, %s, %s, %s)",
                    (title, content, ', '.join(tags), sort_id, image_url)
                )
                logging.info(f"消息已保存到数据库: title={title}")
    except Exception as e:
        logging.error(f"保存消息到数据库时发生错误: {e}")

async def clean_processed_messages(retention_days=7):
    """清理超过指定天数的记录"""
    try:
        async with MySQLConnectionManager() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "DELETE FROM processed_messages WHERE created_at < NOW() - INTERVAL %s DAY",
                    (retention_days,)
                )
                deleted_rows = cursor.rowcount
                logging.info(f"清理 processed_messages 表，删除 {deleted_rows} 条过期记录")
    except Exception as e:
        logging.error(f"清理 processed_messages 表时发生错误: {e}")

def get_image_directory(date_str):
    """生成图片保存目录，从配置文件读取根路径"""
    directory = os.path.join(config["image"]["upload_dir"], date_str)
    os.makedirs(directory, exist_ok=True)
    return directory

def format_size(size_bytes):
    """将字节数转换为友好的单位（KB、MB、GB）"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

async def compress_image(input_path, output_path):
    """压缩图片，确保文件大小变小"""
    try:
        # 从数据库动态获取图片压缩配置
        compression_quality = await get_tgstate_config('image_compression_quality') or '50'
        compression_format = await get_tgstate_config('image_compression_format') or 'webp'
        
        original_size_bytes = os.path.getsize(input_path)
        img = Image.open(input_path)

        max_size = (1024, 1024)
        img.thumbnail(max_size, Image.Resampling.LANCAZOS)

        quality = int(compression_quality)
        format_type = compression_format.lower()
        
        if format_type == "webp":
            img.save(output_path, "WEBP", quality=quality, lossless=False)
        else:
            img.save(output_path, "JPEG", quality=quality)

        compressed_size_bytes = os.path.getsize(output_path)
        compression_ratio = (1 - compressed_size_bytes / original_size_bytes) * 100

        if compressed_size_bytes > original_size_bytes:
            logging.warning(f"初次压缩后文件变大: {format_size(original_size_bytes)} -> {format_size(compressed_size_bytes)}")
            quality = max(10, quality - 20)
            if format_type == "webp":
                img.save(output_path, "WEBP", quality=quality, lossless=False)
            else:
                img.save(output_path, "JPEG", quality=quality)
            compressed_size_bytes = os.path.getsize(output_path)
            compression_ratio = (1 - compressed_size_bytes / original_size_bytes) * 100

        logging.info(
            f"图片压缩完成: {input_path} -> {output_path}\n"
            f"原始大小: {format_size(original_size_bytes)}\n"
            f"压缩后大小: {format_size(compressed_size_bytes)}\n"
            f"压缩率: {compression_ratio:.2f}%"
        )

        if compressed_size_bytes > original_size_bytes:
            logging.warning(f"压缩后文件仍大于原始大小，请调整 quality 或 format 参数")
    except Exception as e:
        logging.error(f"压缩图片时出错: {e}")

async def get_config_from_db(config_key):
    """从数据库获取配置（通用函数）"""
    try:
        async with MySQLConnectionManager() as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            await cursor.execute("SELECT config_value FROM system_config WHERE config_key = %s", (config_key,))
            result = await cursor.fetchone()
            return result['config_value'] if result else None
    except Exception as e:
        logging.error(f"获取配置失败 {config_key}: {e}")
        return None

async def get_tgstate_config(config_key):
    """从数据库获取配置（保留兼容性）"""
    return await get_config_from_db(config_key)

async def mark_verification_completed():
    """标记Telegram验证完成"""
    try:
        async with MySQLConnectionManager() as conn:
            cursor = await conn.cursor()
            
            # 标记验证完成
            await cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_verification_required', 'false', 'boolean', '需要验证码', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = 'false', updated_at = NOW()
            """)
            
            # 标记会话有效
            await cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_session_valid', 'true', 'boolean', 'Telegram会话有效', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = 'true', updated_at = NOW()
            """)
            
            # 清除验证码
            await cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_verification_code', '', 'string', 'Telegram验证码', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = '', updated_at = NOW()
            """)
            
            await conn.commit()
            logging.info("✅ 已标记Telegram验证完成")
            
    except Exception as e:
        logging.error(f"❌ 标记验证完成失败: {e}")

async def clear_verification_status():
    """清除验证状态"""
    try:
        async with MySQLConnectionManager() as conn:
            cursor = await conn.cursor()
            
            # 清除验证状态
            await cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_verification_required', 'false', 'boolean', '需要验证码', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = 'false', updated_at = NOW()
            """)
            
            # 清除会话有效状态
            await cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_session_valid', 'false', 'boolean', 'Telegram会话有效', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = 'false', updated_at = NOW()
            """)
            
            # 清除验证码
            await cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_verification_code', '', 'string', 'Telegram验证码', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = '', updated_at = NOW()
            """)
            
            # 清除提交状态
            await cursor.execute("""
                INSERT INTO system_config (config_key, config_value, config_type, description, category)
                VALUES ('telegram_verification_submitted', 'false', 'boolean', '验证码已提交', 'telegram')
                ON DUPLICATE KEY UPDATE 
                config_value = 'false', updated_at = NOW()
            """)
            
            await conn.commit()
            logging.info("✅ 已清除验证状态")
            
    except Exception as e:
        logging.error(f"❌ 清除验证状态失败: {e}")

async def upload_image(image_path):
    """上传图片到图床"""
    async with semaphore:
        try:
            # 从数据库动态获取tgState配置
            tgstate_port = await get_tgstate_config('tgstate_port') or '8088'
            tgstate_url = await get_tgstate_config('tgstate_url') or 'http://localhost:8088'
            
            # 容器内网络调用地址（用于API调用）
            container_api_url = f"http://tgstate:{tgstate_port}/api"
            
            # 配置的基础URL（用于返回给用户）
            base_url = tgstate_url.rstrip('/')
            
            # 从数据库动态获取tgstate_pass配置
            tgstate_pass = await get_tgstate_config('tgstate_pass') or 'none'
            cookies = {"p": tgstate_pass} if tgstate_pass != "none" else {}
            
            async with aiohttp.ClientSession(cookies=cookies) as session:
                with open(image_path, "rb") as file:
                    form_data = aiohttp.FormData()
                    form_data.add_field("image", file, filename=os.path.basename(image_path))
                    async with session.post(container_api_url, data=form_data) as response:
                        result = await response.json()
                        if result.get("code") == 1:
                            # 使用配置的基础URL构建返回地址
                            img_path = result.get('message', '')
                            if img_path.startswith('/'):
                                img_path = img_path[1:]  # 移除开头的斜杠
                            image_url = f"{base_url}/{img_path}"
                            os.remove(image_path)
                            logging.info(f"图片上传成功并删除本地文件: {image_url}")
                            return image_url
                        else:
                            logging.error(f"图片上传失败: {result.get('message')}")
                            return None
        except Exception as e:
            logging.error(f"上传图片时发生错误: {e}")
            return None

async def download_image_from_message(message, date_str):
    """下载消息中的图片并上传到图床"""
    try:
        if message.media and hasattr(message.media, 'photo'):
            directory = get_image_directory(date_str)
            local_path = await client.download_media(message, directory)
            if not os.path.exists(local_path):
                logging.error(f"文件不存在: {local_path}")
                return None
            
            # 动态获取压缩格式
            compression_format = await get_tgstate_config('image_compression_format') or 'webp'
            compressed_path = local_path.replace(".jpg", f"_compressed.{compression_format}")
            await compress_image(local_path, compressed_path)
            
            # 尝试上传图片
            image_url = await upload_image(compressed_path)
            if image_url:
                # 上传成功，删除本地文件
                os.remove(local_path)
                return f"![]({image_url})"
            else:
                # 上传失败，保留本地文件，使用相对路径
                logging.warning(f"图片上传失败，使用本地文件: {compressed_path}")
                local_url = compressed_path.replace("./", "")
                return f"![]({local_url})"
        return None
    except Exception as e:
        logging.error(f"下载或上传图片时发生错误: {e}")
        return None

async def parse_log(message):
    """解析消息文本"""
    try:
        text = message.text or ""
        title_end = text.find("描述：") if "描述：" in text else len(text)
        title = text[:title_end].replace("名称：", "").strip()[:24]
        description_start = text.find("描述：") + 3
        description_end = text.find("链接：", description_start)
        description = text[description_start:description_end].strip() if description_start != 2 else "无描述"
        link_start = text.find("链接：") + 3
        link = text[link_start:text.find("\n", link_start)].strip() if link_start != 2 else "无链接"
        size_start = text.find("📁 大小：")
        size = text[size_start + 5:text.find("\n", size_start)].strip() if size_start != -1 else "未知大小"
        tags_start = text.find("🏷 标签：") + 5
        tags = text[tags_start:text.find("\n", tags_start)].strip() if tags_start != 4 else "无标签"
        formatted_tags = tags.replace(" ", "").replace("，", ",").replace("#", ",").split(',')

        link_text = link
        sort_id = None
        for domain, display_text in config["link_mapping"].items():
            if domain in link:
                link_text = f'<a href="{link}" target="_blank">{display_text}</a>'
                sort_id = config["category_mapping"].get(domain)
                break

        content = f"**描述**: {description}\n\n**📁 大小**: {size}\n\n**链接**: {link_text}"
        return title or "未知标题", content, formatted_tags, sort_id
    except Exception as e:
        logging.error(f"解析日志时发生错误: {e}")
        return "未知标题", "无法解析内容", [], None

async def check_session_validity(session_file, api_id, api_hash):
    """检查会话文件是否存在且有效"""
    if not os.path.exists(session_file):
        logging.info("📄 会话文件不存在，需要首次登录")
        return False
    
    logging.info(f"📄 发现会话文件: {session_file}")
    logging.info("🔍 检查会话有效性...")
    
    try:
        # 创建临时客户端测试会话
        test_client = TelegramClient(session_file, api_id, api_hash)
        await test_client.connect()
        
        # 检查是否已授权
        if not await test_client.is_user_authorized():
            logging.warning("⚠️ 会话文件存在但未授权，需要重新登录")
            await test_client.disconnect()
            return False
        
        # 测试实际连接
        try:
            me = await test_client.get_me()
            logging.info(f"✅ 会话有效！当前用户: {me.username or me.first_name} (ID: {me.id})")
            await test_client.disconnect()
            return True
        except Exception as e:
            logging.warning(f"⚠️ 会话测试失败: {e}")
            await test_client.disconnect()
            return False
            
    except Exception as e:
        logging.warning(f"⚠️ 会话检查失败: {e}")
        return False

async def init_telegram_client():
    """初始化并登录 Telegram 客户端"""
    global client
    
    try:
        # 第一步：检查内存中的client是否存在且连接正常
        if client is not None and client.is_connected():
            try:
                me = await client.get_me()
                logging.info(f"✅ Telegram客户端已连接，无需重新登录 (用户: {me.username or me.first_name})")
                return True
            except Exception as e:
                logging.info(f"⚠️ 现有连接已失效: {e}")
                try:
                    await client.disconnect()
                except:
                    pass
                client = None
        
        # 第二步：从数据库获取配置
        api_id = await get_config_from_db("telegram_api_id") or config["telegram"]["api_id"]
        api_hash = await get_config_from_db("telegram_api_hash") or config["telegram"]["api_hash"]
        phone_number = await get_config_from_db("telegram_phone") or config["telegram"]["phone_number"]
        
        if not api_id or not api_hash or not phone_number:
            logging.error("❌ Telegram配置不完整，请在后台管理页面配置API ID、API Hash和手机号")
            logging.error("必需的配置:")
            logging.error(f"  - API ID: {'已配置' if api_id else '未配置'}")
            logging.error(f"  - API Hash: {'已配置' if api_hash else '未配置'}")  
            logging.error(f"  - 手机号: {'已配置' if phone_number else '未配置'}")
            raise Exception("Telegram配置不完整")
        
        logging.info("✅ 已从数据库获取Telegram配置")
        
        # 确保sessions目录存在
        sessions_dir = "/app/sessions"
        os.makedirs(sessions_dir, exist_ok=True)
        
        # 使用映射的sessions目录
        session_file = os.path.join(sessions_dir, 'tg2em_scraper.session')
        
        # 第三步：检查会话文件是否存在且有效
        session_valid = await check_session_validity(session_file, api_id, api_hash)
        
        # 第四步：创建客户端
        client = TelegramClient(session_file, api_id, api_hash)
        
        # 使用的手机号
        phone = phone_number
        two_factor_password = config["telegram"].get("two_factor_password")
        
        # 第五步：根据会话有效性决定登录方式
        if session_valid:
            # 会话有效，直接连接
            logging.info("🔄 使用已保存的有效会话，直接连接...")
            try:
                await client.connect()
                if await client.is_user_authorized():
                    me = await client.get_me()
                    logging.info(f"✅ Telegram客户端启动成功 (用户: {me.username or me.first_name})")
                    return True
                else:
                    logging.warning("⚠️ 连接成功但未授权，需要重新登录")
                    # 删除无效会话文件
                    if os.path.exists(session_file):
                        os.remove(session_file)
                        logging.info("🗑️ 已删除无效会话文件")
            except Exception as e:
                logging.warning(f"⚠️ 使用已保存会话连接失败: {e}")
                # 删除无效会话文件
                if os.path.exists(session_file):
                    os.remove(session_file)
                    logging.info("🗑️ 已删除无效会话文件")
        
        # 第六步：会话无效或不存在，执行完整登录流程
        logging.info("🔐 开始Telegram登录流程...")
        
        try:
            # 尝试使用手机号登录（会自动检测是否需要验证码）
            await client.start(phone=lambda: phone)
            
            # 验证连接
            me = await client.get_me()
            logging.info(f"✅ Telegram登录成功！当前用户: {me.username or me.first_name}")
            logging.info(f"📁 会话已保存至: {session_file}")
            
            # 标记验证完成和会话有效
            await mark_verification_completed()
            return True
            
        except Exception as start_error:
            logging.warning(f"自动登录失败: {start_error}")
            logging.info("📱 需要验证码，等待Web界面输入...")
            
            # 需要验证码的情况
            try:
                await client.start(
                    phone=lambda: phone,
                    code_callback=get_code_input,
                    password=lambda: two_factor_password if two_factor_password else get_password_input()
                )
                
                # 验证登录成功
                me = await client.get_me()
                logging.info(f"✅ Telegram验证成功！当前用户: {me.username or me.first_name}")
                logging.info(f"📁 会话已保存至: {session_file}")
                
                # 标记验证完成和会话有效
                await mark_verification_completed()
                return True
                
            except Exception as auth_error:
                error_msg = str(auth_error)
                logging.error(f"❌ Telegram验证失败: {auth_error}")
                
                # 检查是否是验证码重发限制错误
                if "ResendCodeRequest" in error_msg or "all available options" in error_msg:
                    logging.warning("⚠️ 检测到验证码重发限制，删除会话文件重新开始...")
                    try:
                        # 删除会话文件
                        if os.path.exists(session_file):
                            os.remove(session_file)
                            logging.info("🗑️ 已删除会话文件，请等待24小时后重新尝试")
                        
                        # 清除数据库中的验证状态
                        await clear_verification_status()
                        
                        raise Exception("验证码重发限制：请等待24小时后重新尝试，或联系管理员删除会话文件")
                    except Exception as clear_error:
                        logging.error(f"❌ 清理会话文件失败: {clear_error}")
                
                raise Exception(f"Telegram登录失败: {auth_error}")
    
    except Exception as e:
        logging.error(f"❌ 初始化Telegram客户端失败: {e}")
        raise

async def scrape_channel():
    """抓取 Telegram 频道消息"""
    global client
    
    # 确保 Telegram 客户端已初始化和登录
    if client is None or not client.is_connected():
        logging.info("🔄 Telegram客户端未连接，开始初始化和登录...")
        await init_telegram_client()
    
    try:
        logging.info("Telegram 客户端启动成功")
        collect_start_time = datetime.now()
        stats = {"total": 0, "duplicate": 0, "new": 0, "blocked_tags_removed": 0}

        blocked_tags = set(config["task"]["collect"]["blocked_tags"])
        retention_days = config["task"]["collect"].get("retention_days", 7)
        default_limit = config["task"]["collect"].get("default_limit", 25)
        await clean_processed_messages(retention_days)

        # 从数据库获取频道配置
        channels_config = await get_config_from_db("scrape_channels") or ""
        scrape_limit = int(await get_config_from_db("scrape_limit") or config["task"]["collect"]["default_limit"])
        
        # 解析频道配置
        channel_urls = []
        if channels_config:
            for line in channels_config.strip().split('\n'):
                line = line.strip()
                if line:
                    if line.startswith('http'):
                        channel_urls.append({"url": line, "limit": scrape_limit})
                    elif line.startswith('@') or line.startswith('-'):
                        channel_urls.append({"id": line, "limit": scrape_limit})
                    else:
                        # 尝试作为频道ID处理
                        try:
                            channel_id = int(line)
                            channel_urls.append({"id": channel_id, "limit": scrape_limit})
                        except ValueError:
                            channel_urls.append({"id": f"@{line}", "limit": scrape_limit})
        
        if not channel_urls:
            logging.error("❌ 未配置采集频道，请在后台管理页面配置scrape_channels参数")
            return
        
        logging.info(f"✅ 已配置 {len(channel_urls)} 个采集频道")
        
        for channel_config in channel_urls:
            limit = channel_config.get("limit", default_limit)
            
            # 支持频道URL和频道ID两种方式
            if "url" in channel_config:
                channel_url = channel_config["url"]
                logging.info(f"开始抓取频道: {channel_url} (limit={limit})")
                try:
                    channel = await client.get_entity(channel_url)
                    channel_id = channel.id
                except Exception as e:
                    logging.error(f"获取频道实体失败: {e}")
                    continue
            elif "id" in channel_config:
                channel_id = channel_config["id"]
                logging.info(f"开始抓取频道ID: {channel_id} (limit={limit})")
                try:
                    channel = await client.get_entity(channel_id)
                except Exception as e:
                    logging.error(f"获取频道实体失败: {e}")
                    continue
            else:
                logging.error("频道配置必须包含 'url' 或 'id' 字段")
                continue

            async for message in client.iter_messages(channel, limit=limit):
                stats["total"] += 1
                if await is_message_processed(channel_id, message.id):
                    stats["duplicate"] += 1
                    continue

                title, content, tags, sort_id = await parse_log(message)
                message_tags = set(tags)

                blocked_in_message = message_tags & blocked_tags
                if blocked_in_message:
                    filtered_tags = [tag for tag in tags if tag not in blocked_tags]
                    stats["blocked_tags_removed"] += len(blocked_in_message)
                    logging.info(f"从消息中移除屏蔽标签: {blocked_in_message}, 剩余标签: {filtered_tags}, title={title}")
                    tags = filtered_tags
                else:
                    filtered_tags = tags

                date_str = datetime.now().strftime('%Y%m%d')
                image_url = await download_image_from_message(message, date_str)
                if image_url:
                    content = f"{image_url}\n\n{content}"

                await save_message(title, content, filtered_tags, sort_id, image_url)
                stats["new"] += 1
                await mark_message_processed(channel_id, message.id)

        elapsed_time = datetime.now() - collect_start_time
        logging.info(f"本次采集完成，耗时: {elapsed_time}, 总消息数={stats['total']}, 重复={stats['duplicate']}, 新增={stats['new']}, 移除屏蔽标签数={stats['blocked_tags_removed']}")
        next_run = datetime.now() + timedelta(minutes=config["task"]["collect"]["interval_minutes"])
        logging.info(f"下次采集时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logging.error(f"抓取频道消息时发生错误: {e}")

async def run_periodic_scraper():
    """定时抓取任务"""
    global shutdown_requested
    interval_minutes = config["task"]["collect"]["interval_minutes"]
    
    while not shutdown_requested:
        try:
            await scrape_channel()
            
            # 可中断的等待
            wait_seconds = interval_minutes * 60
            for _ in range(wait_seconds):
                if shutdown_requested:
                    logging.info("收到退出请求，停止等待")
                    break
                await asyncio.sleep(1)
                
        except Exception as e:
            logging.error(f"采集中出现错误: {e}")
            if not shutdown_requested:
                logging.info(f"错误后等待 {interval_minutes} 分钟后重试...")
                await asyncio.sleep(interval_minutes * 60)

def get_code_input():
    """获取验证码输入的交互函数"""
    import time
    import pymysql
    
    print("\n" + "="*50)
    print("🔔 Telegram 需要验证码验证")
    print("📱 请前往管理后台输入验证码")
    print("🌐 访问地址: http://localhost:5000/dm")
    print("="*50)
    
    # 数据库配置
    DB_CONFIG = {
        'host': os.environ.get('MYSQL_HOST', 'mysql'),
        'port': int(os.environ.get('MYSQL_PORT', 3306)),
        'user': os.environ.get('MYSQL_USER', 'tg2em'),
        'password': os.environ.get('MYSQL_PASSWORD', 'tg2em2025'),
        'database': os.environ.get('MYSQL_DATABASE', 'tg2em'),
        'charset': 'utf8mb4'
    }
    
    # 标记需要验证码
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 插入验证状态
        cursor.execute("""
            INSERT INTO system_config (config_key, config_value, config_type, description, category)
            VALUES ('telegram_verification_required', 'true', 'boolean', '需要验证码', 'telegram')
            ON DUPLICATE KEY UPDATE 
            config_value = 'true', updated_at = NOW()
        """)
        
        # 清除之前的验证码
        cursor.execute("""
            INSERT INTO system_config (config_key, config_value, config_type, description, category)
            VALUES ('telegram_verification_code', '', 'string', 'Telegram验证码', 'telegram')
            ON DUPLICATE KEY UPDATE 
            config_value = '', updated_at = NOW()
        """)
        
        # 清除提交状态
        cursor.execute("""
            INSERT INTO system_config (config_key, config_value, config_type, description, category)
            VALUES ('telegram_verification_submitted', 'false', 'boolean', '验证码已提交', 'telegram')
            ON DUPLICATE KEY UPDATE 
            config_value = 'false', updated_at = NOW()
        """)
        
        conn.commit()
        conn.close()
        
        logging.info("✅ 已在数据库中标记需要验证码")
        
    except Exception as e:
        logging.error(f"❌ 数据库操作失败: {e}")
    
    # 等待Web界面输入验证码
    max_wait_time = 300  # 最多等待5分钟
    check_interval = 2    # 每2秒检查一次
    waited_time = 0
    
    while waited_time < max_wait_time:
        try:
            conn = pymysql.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            # 检查是否有验证码
            cursor.execute("""
                SELECT config_value FROM system_config 
                WHERE config_key = 'telegram_verification_code'
            """)
            result = cursor.fetchone()
            
            # 检查是否已提交
            cursor.execute("""
                SELECT config_value FROM system_config 
                WHERE config_key = 'telegram_verification_submitted'
            """)
            submitted_result = cursor.fetchone()
            
            conn.close()
            
            if submitted_result and submitted_result[0] == 'true' and result and result[0].strip():
                verification_code = result[0].strip()
                
                if len(verification_code) == 5 and verification_code.isdigit():
                    print(f"✅ 收到Web界面验证码: {verification_code}")
                    logging.info(f"从Web界面获取到验证码: {verification_code}")
                    
                    # 清除验证状态
                    try:
                        conn = pymysql.connect(**DB_CONFIG)
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM system_config WHERE config_key = 'telegram_verification_required'")
                        cursor.execute("DELETE FROM system_config WHERE config_key = 'telegram_verification_submitted'")
                        conn.commit()
                        conn.close()
                    except:
                        pass
                    
                    return verification_code
                else:
                    print(f"❌ 验证码格式错误: {verification_code}")
            
            print(f"⏳ 等待验证码输入... ({waited_time}s/{max_wait_time}s)")
            time.sleep(check_interval)
            waited_time += check_interval
            
        except Exception as e:
            logging.error(f"❌ 检查验证码时发生错误: {e}")
            time.sleep(check_interval)
            waited_time += check_interval
    
    # 超时处理
    logging.error("❌ 验证码输入超时")
    raise Exception("验证码输入超时，请重新启动服务")

def get_password_input():
    """获取两步验证密码的交互函数"""
    import getpass
    print("\n" + "="*50)
    print("Telegram 需要两步验证密码")
    print("="*50)
    
    password = getpass.getpass("请输入两步验证密码: ").strip()
    print("✅ 密码已输入")
    return password

async def main():
    """主函数"""
    global client
    logging.info("采集脚本启动")
    
    try:
        await init_mysql_pool()
        
        # 从数据库动态获取 Telegram 配置
        api_id = await get_config_from_db("telegram_api_id") or config["telegram"]["api_id"]
        api_hash = await get_config_from_db("telegram_api_hash") or config["telegram"]["api_hash"]
        phone_number = await get_config_from_db("telegram_phone") or config["telegram"]["phone_number"]
        
        if not api_id or not api_hash or not phone_number:
            logging.error("❌ Telegram配置不完整，请在后台管理页面配置API ID、API Hash和手机号")
            logging.error("必需的配置:")
            logging.error(f"  - API ID: {'已配置' if api_id else '未配置'}")
            logging.error(f"  - API Hash: {'已配置' if api_hash else '未配置'}")  
            logging.error(f"  - 手机号: {'已配置' if phone_number else '未配置'}")
            return
        
        logging.info("✅ 已从数据库获取Telegram配置")
        
        # 确保sessions目录存在
        sessions_dir = "/app/sessions"
        os.makedirs(sessions_dir, exist_ok=True)
        
        # 使用映射的sessions目录
        session_file = os.path.join(sessions_dir, 'tg2em_scraper.session')
        client = TelegramClient(session_file, api_id, api_hash)
        
        # 改进的 Telegram 客户端启动方式
        phone = phone_number  # 使用从数据库获取的手机号
        two_factor_password = config["telegram"].get("two_factor_password")
        
        # 检查是否存在会话文件
        if os.path.exists(session_file):
            logging.info(f"发现已存在的Telegram会话文件: {session_file}")
            logging.info("尝试使用已保存的会话，无需重新验证")
        else:
            logging.info("首次启动，需要验证码验证")
        
        try:
            # 先尝试不需要验证的方式启动
            await client.start(phone=lambda: phone)
            if os.path.exists(session_file):
                logging.info("✅ Telegram 客户端启动成功，使用已保存的会话")
                
                # 测试连接是否仍然有效
                try:
                    me = await client.get_me()
                    logging.info(f"✅ Telegram连接验证成功，当前用户: {me.username or me.first_name}")
                except Exception as test_error:
                    logging.warning(f"会话可能已过期，需要重新验证: {test_error}")
                    # 删除过期会话文件
                    if os.path.exists(session_file):
                        os.remove(session_file)
                        logging.info("已删除过期会话文件")
                    raise Exception("会话已过期，需要重新验证")
            else:
                logging.info("✅ Telegram 客户端启动成功，首次验证完成")
        except Exception as start_error:
            logging.warning(f"自动启动失败: {start_error}")
            logging.info("需要手动验证，请按提示输入验证码...")
            
            # 需要验证码的情况
            try:
                await client.start(
                    phone=lambda: phone,
                    code_callback=get_code_input,
                    password=lambda: two_factor_password if two_factor_password else get_password_input()
                )
                logging.info("✅ Telegram 验证成功！会话已保存")
                logging.info(f"📁 会话文件位置: {session_file}")
            except Exception as auth_error:
                logging.error(f"Telegram 验证失败: {auth_error}")
                logging.error("请检查手机号和验证码是否正确，然后重启脚本")
                return
        
        logging.info("开始执行定时采集任务...")
        await run_periodic_scraper()
        
    except KeyboardInterrupt:
        logging.info("采集脚本被用户中断")
    except Exception as e:
        logging.error(f"主函数运行出错: {e}")
        raise
    finally:
        if client:
            await client.disconnect()
            logging.info("Telegram 客户端已断开连接")
        await close_mysql_pool()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("采集脚本已手动停止")
    finally:
        loop.close()
