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
import builtins

# 限制并发数为 5
semaphore = asyncio.Semaphore(5)

# 确保open函数可用
if not hasattr(builtins, 'open'):
    builtins.open = open

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

def get_image_directory(date_str, image_config=None):
    """生成图片保存目录，从数据库配置或配置文件读取根路径"""
    if image_config:
        upload_dir = image_config.upload_dir
    else:
        upload_dir = config["image"]["upload_dir"]
    
    directory = os.path.join(upload_dir, date_str)
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

async def compress_image(input_path, output_path, image_config=None):
    """压缩图片，确保文件大小变小"""
    try:
        # 使用数据库配置或默认配置
        if image_config:
            compression_quality = image_config.compression_quality
            compression_format = image_config.compression_format
        else:
            compression_quality = await get_tgstate_config('image_compression_quality') or 50
            compression_format = await get_tgstate_config('image_compression_format') or 'webp'
        
        original_size_bytes = os.path.getsize(input_path)
        img = Image.open(input_path)

        max_size = (1024, 1024)
        # 使用兼容的重采样方法
        try:
            img.thumbnail(max_size, Image.Resampling.LANCAZOS)
        except AttributeError:
            # 对于较老版本的Pillow，使用旧的方法
            img.thumbnail(max_size, Image.LANCZOS)

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

async def upload_image(image_path, image_config=None):
    """上传图片到图床"""
    async with semaphore:
        try:
            # 使用数据库配置或默认配置
            if image_config:
                tgstate_port = image_config.tgstate_port
                tgstate_url = image_config.tgstate_url
                tgstate_pass = image_config.tgstate_pass
            else:
                tgstate_port = await get_tgstate_config('tgstate_port') or '8088'
                tgstate_url = await get_tgstate_config('tgstate_url') or 'http://localhost:8088'
                tgstate_pass = await get_tgstate_config('tgstate_pass') or 'none'
            
            # 容器内网络调用地址（用于API调用）
            container_api_url = f"http://tgstate:{tgstate_port}/api"
            
            # 配置的基础URL（用于返回给用户）
            base_url = tgstate_url.rstrip('/')
            
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

async def download_image_from_message(message, date_str, image_config=None):
    """下载消息中的图片并上传到图床"""
    try:
        if message.media and hasattr(message.media, 'photo'):
            directory = get_image_directory(date_str, image_config)
            local_path = await client.download_media(message, directory)
            if not os.path.exists(local_path):
                logging.error(f"文件不存在: {local_path}")
                return None
            
            # 使用数据库配置或默认配置
            if image_config:
                compression_format = image_config.compression_format
            else:
                compression_format = await get_tgstate_config('image_compression_format') or 'webp'
            
            compressed_path = local_path.replace(".jpg", f"_compressed.{compression_format}")
            await compress_image(local_path, compressed_path, image_config)
            
            # 尝试上传图片
            image_url = await upload_image(compressed_path, image_config)
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

class DatabaseConfigManager:
    """数据库配置管理器 - 统一管理所有配置项"""
    
    def __init__(self):
        self.config_cache = {}
        self.cache_time = None
        self.cache_duration = 30  # 缓存30秒，减少缓存时间
        
    async def get_config(self, config_key, default_value=None, config_type="string"):
        """从数据库获取单个配置项"""
        try:
            # 检查缓存
            if self._is_cache_valid():
                return self.config_cache.get(config_key, default_value)
            
            # 从数据库获取
            value = await get_config_from_db(config_key)
            if value is not None:
                # 类型转换
                if config_type == "int":
                    value = int(value)
                elif config_type == "bool":
                    value = value.lower() in ('true', '1', 'yes', 'on')
                elif config_type == "list":
                    value = [item.strip() for item in value.split(',') if item.strip()]
                
                # 更新缓存
                self.config_cache[config_key] = value
                return value
            
            return default_value
            
        except Exception as e:
            logging.error(f"❌ 获取配置失败 {config_key}: {e}")
            return default_value
    
    async def get_all_configs(self):
        """获取所有配置项"""
        try:
            if self._is_cache_valid():
                return self.config_cache
            
            # 从数据库批量获取配置
            async with MySQLConnectionManager() as conn:
                cursor = await conn.cursor(aiomysql.DictCursor)
                await cursor.execute("SELECT config_key, config_value FROM system_config")
                results = await cursor.fetchall()
                
                # 构建配置字典
                configs = {}
                for result in results:
                    configs[result['config_key']] = result['config_value']
                
                # 更新缓存
                self.config_cache = configs
                self.cache_time = datetime.now()
                
                return configs
                
        except Exception as e:
            logging.error(f"❌ 获取所有配置失败: {e}")
            return {}
    
    def _is_cache_valid(self):
        """检查缓存是否有效"""
        if not self.cache_time:
            return False
        return (datetime.now() - self.cache_time).seconds < self.cache_duration
    
    def clear_cache(self):
        """清除配置缓存"""
        self.config_cache = {}
        self.cache_time = None
        logging.info("🔄 已清除配置缓存")
    
    async def force_refresh(self):
        """强制刷新配置缓存"""
        self.clear_cache()
        await self.get_all_configs()
        logging.info("🔄 已强制刷新配置缓存")

class TelegramConfig:
    """Telegram配置管理类"""
    
    def __init__(self, db_config_manager=None):
        self.api_id = None
        self.api_hash = None
        self.phone_number = None
        self.session_name = None
        self.two_factor_password = None
        self.db_config = db_config_manager or DatabaseConfigManager()
        
    async def load_from_db(self):
        """从数据库加载配置"""
        try:
            self.api_id = await self.db_config.get_config("telegram_api_id", config["telegram"]["api_id"])
            self.api_hash = await self.db_config.get_config("telegram_api_hash", config["telegram"]["api_hash"])
            self.phone_number = await self.db_config.get_config("telegram_phone", config["telegram"]["phone_number"])
            self.session_name = await self.db_config.get_config("telegram_session_name", config["telegram"].get("session_name", "tg2em_scraper"))
            self.two_factor_password = await self.db_config.get_config("telegram_two_factor_password", config["telegram"].get("two_factor_password"))
            
            logging.info("✅ 已从数据库加载Telegram配置")
            return True
        except Exception as e:
            logging.error(f"❌ 从数据库加载配置失败: {e}")
            return False
    
    def validate(self):
        """验证配置完整性"""
        missing = []
        if not self.api_id:
            missing.append("API ID")
        if not self.api_hash:
            missing.append("API Hash")
        if not self.phone_number:
            missing.append("手机号")
        
        if missing:
            logging.error(f"❌ Telegram配置不完整，缺少: {', '.join(missing)}")
            return False
        
        logging.info("✅ Telegram配置验证通过")
        return True

class ScrapeConfig:
    """采集配置管理类"""
    
    def __init__(self, db_config_manager=None):
        self.blocked_tags = []
        self.retention_days = 7
        self.default_limit = 25
        self.interval_minutes = 5
        self.scrape_channels = []
        self.scrape_limit = 25
        self.db_config = db_config_manager or DatabaseConfigManager()
        
    async def load_from_db(self):
        """从数据库加载配置"""
        try:
            # 基础配置
            self.retention_days = await self.db_config.get_config("retention_days", config["task"]["collect"].get("retention_days", 7), "int")
            self.default_limit = await self.db_config.get_config("default_limit", config["task"]["collect"].get("default_limit", 25), "int")
            self.interval_minutes = await self.db_config.get_config("interval_minutes", config["task"]["collect"].get("interval_minutes", 5), "int")
            self.scrape_limit = await self.db_config.get_config("scrape_limit", config["task"]["collect"].get("default_limit", 25), "int")
            
            # 屏蔽标签
            blocked_tags_str = await self.db_config.get_config("blocked_tags", ",".join(config["task"]["collect"].get("blocked_tags", [])))
            self.blocked_tags = [tag.strip() for tag in blocked_tags_str.split(',') if tag.strip()]
            
            # 采集频道
            channels_str = await self.db_config.get_config("scrape_channels", "")
            if channels_str:
                self.scrape_channels = self._parse_channels_config(channels_str)
            else:
                # 从配置文件获取默认频道
                self.scrape_channels = config["telegram"].get("channel_urls", [])
            
            logging.info("✅ 已从数据库加载采集配置")
            return True
        except Exception as e:
            logging.error(f"❌ 从数据库加载采集配置失败: {e}")
            return False
    
    def _parse_channels_config(self, channels_str):
        """解析频道配置字符串"""
        channels = []
        for line in channels_str.strip().split('\n'):
            line = line.strip()
            if line:
                if line.startswith('http'):
                    channels.append({"url": line, "limit": self.scrape_limit})
                elif line.startswith('@') or line.startswith('-'):
                    channels.append({"id": line, "limit": self.scrape_limit})
                else:
                    try:
                        channel_id = int(line)
                        channels.append({"id": channel_id, "limit": self.scrape_limit})
                    except ValueError:
                        channels.append({"id": f"@{line}", "limit": self.scrape_limit})
        return channels

class ImageConfig:
    """图片配置管理类"""
    
    def __init__(self, db_config_manager=None):
        self.upload_dir = "./upload"
        self.compression_quality = 50
        self.compression_format = "webp"
        self.tgstate_url = "http://tgstate:8001"
        self.tgstate_port = "8088"
        self.tgstate_pass = "none"
        self.db_config = db_config_manager or DatabaseConfigManager()
        
    async def load_from_db(self):
        """从数据库加载配置"""
        try:
            self.upload_dir = await self.db_config.get_config("image_upload_dir", config["image"].get("upload_dir", "./upload"))
            self.compression_quality = await self.db_config.get_config("image_compression_quality", config["image_compression"].get("quality", 50), "int")
            self.compression_format = await self.db_config.get_config("image_compression_format", config["image_compression"].get("format", "webp"))
            self.tgstate_url = await self.db_config.get_config("tgstate_url", "http://tgstate:8001")
            self.tgstate_port = await self.db_config.get_config("tgstate_port", "8088")
            self.tgstate_pass = await self.db_config.get_config("tgstate_pass", "none")
            
            logging.info("✅ 已从数据库加载图片配置")
            return True
        except Exception as e:
            logging.error(f"❌ 从数据库加载图片配置失败: {e}")
            return False

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
    """初始化并登录 Telegram 客户端（简化版本 - 参考原脚本）"""
    global client
    
    try:
        # 第一步：检查现有连接
        if client is not None and client.is_connected():
            try:
                me = await client.get_me()
                logging.info(f"✅ Telegram客户端已连接 (用户: {me.username or me.first_name})")
                return True
            except Exception as e:
                logging.info(f"⚠️ 现有连接已失效: {e}")
                try:
                    await client.disconnect()
                except:
                    pass
                client = None
        
        # 第二步：加载配置
        tg_config = TelegramConfig()
        if not await tg_config.load_from_db():
            raise Exception("配置加载失败")
        
        if not tg_config.validate():
            raise Exception("配置验证失败")
        
        # 第三步：确保sessions目录存在
        sessions_dir = "/app/sessions"
        os.makedirs(sessions_dir, exist_ok=True)
        session_file = os.path.join(sessions_dir, f'{tg_config.session_name}.session')
        
        # 第四步：创建客户端（参考原脚本的简单方式）
        client = TelegramClient(session_file, tg_config.api_id, tg_config.api_hash)
        
        # 第五步：直接启动（参考原脚本的方式）
        logging.info("🔐 开始Telegram登录流程...")
        
        try:
            # 直接使用交互式启动，让Telegram客户端处理验证码
            await client.start(
                phone=lambda: tg_config.phone_number,
                code_callback=get_code_input,
                password=lambda: tg_config.two_factor_password if tg_config.two_factor_password else get_password_input()
            )
            logging.info("✅ Telegram客户端启动成功")
            
        except Exception as auth_error:
            logging.error(f"❌ Telegram验证失败: {auth_error}")
            
            # 检查是否是验证码重发限制错误
            if "ResendCodeRequest" in str(auth_error) or "all available options" in str(auth_error):
                logging.warning("⚠️ 检测到验证码重发限制")
                logging.info("💡 建议：等待24小时后重新尝试，或使用不同的手机号")
                
                # 删除会话文件
                try:
                    if os.path.exists(session_file):
                        os.remove(session_file)
                        logging.info("🗑️ 已删除会话文件")
                except Exception as clear_error:
                    logging.error(f"❌ 清理会话文件失败: {clear_error}")
                
                raise Exception("验证码重发限制：请等待24小时后重新尝试，或使用不同的手机号")
            
            raise Exception(f"Telegram登录失败: {auth_error}")
        
        # 验证登录成功
        me = await client.get_me()
        logging.info(f"✅ Telegram登录成功！当前用户: {me.username or me.first_name}")
        logging.info(f"📁 会话已保存至: {session_file}")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ 初始化Telegram客户端失败: {e}")
        raise

async def scrape_channel():
    """抓取 Telegram 频道消息（使用数据库配置）"""
    global client
    
    # 确保 Telegram 客户端已初始化和登录
    if client is None or not client.is_connected():
        logging.info("🔄 Telegram客户端未连接，开始初始化和登录...")
        await init_telegram_client()
    
    try:
        logging.info("Telegram 客户端启动成功")
        collect_start_time = datetime.now()
        stats = {"total": 0, "duplicate": 0, "new": 0, "blocked_tags_removed": 0}

        # 加载配置
        db_config_manager = DatabaseConfigManager()
        scrape_config = ScrapeConfig(db_config_manager)
        image_config = ImageConfig(db_config_manager)
        
        # 强制刷新配置，确保获取最新配置
        await db_config_manager.force_refresh()
        await scrape_config.load_from_db()
        await image_config.load_from_db()
        
        # 使用数据库配置
        blocked_tags = set(scrape_config.blocked_tags)
        retention_days = scrape_config.retention_days
        default_limit = scrape_config.default_limit
        channel_urls = scrape_config.scrape_channels
        
        await clean_processed_messages(retention_days)
        
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
                image_url = await download_image_from_message(message, date_str, image_config)
                if image_url:
                    content = f"{image_url}\n\n{content}"

                await save_message(title, content, filtered_tags, sort_id, image_url)
                stats["new"] += 1
                await mark_message_processed(channel_id, message.id)

        elapsed_time = datetime.now() - collect_start_time
        logging.info(f"本次采集完成，耗时: {elapsed_time}, 总消息数={stats['total']}, 重复={stats['duplicate']}, 新增={stats['new']}, 移除屏蔽标签数={stats['blocked_tags_removed']}")
        next_run = datetime.now() + timedelta(minutes=scrape_config.interval_minutes)
        logging.info(f"下次采集时间: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        logging.error(f"抓取频道消息时发生错误: {e}")

async def run_periodic_scraper():
    """定时抓取任务（使用数据库配置）"""
    global shutdown_requested
    
    # 加载配置
    db_config_manager = DatabaseConfigManager()
    scrape_config = ScrapeConfig(db_config_manager)
    await scrape_config.load_from_db()
    
    interval_minutes = scrape_config.interval_minutes
    logging.info(f"🔄 启动定时采集任务，间隔: {interval_minutes} 分钟")
    
    while not shutdown_requested:
        try:
            logging.info("⏰ 开始定时采集任务...")
            
            # 强制刷新配置缓存，确保获取最新的频道配置
            await db_config_manager.force_refresh()
            
            await scrape_channel()
            logging.info("✅ 定时采集任务完成")
            
            # 可中断的等待
            wait_seconds = interval_minutes * 60
            logging.info(f"⏳ 等待 {interval_minutes} 分钟后进行下次采集...")
            
            for i in range(wait_seconds):
                if shutdown_requested:
                    logging.info("收到退出请求，停止等待")
                    break
                # 每30秒显示一次倒计时
                if i % 30 == 0 and i > 0:
                    remaining_minutes = (wait_seconds - i) // 60
                    logging.info(f"⏳ 距离下次采集还有 {remaining_minutes} 分钟...")
                await asyncio.sleep(1)
                
        except Exception as e:
            logging.error(f"定时采集中出现错误: {e}")
            if not shutdown_requested:
                logging.info(f"错误后等待 {interval_minutes} 分钟后重试...")
                await asyncio.sleep(interval_minutes * 60)
    
    logging.info("🛑 定时采集任务已停止")

def get_code_input():
    """获取验证码输入的交互函数（Docker容器兼容版本）"""
    import sys
    
    print("\n" + "="*50)
    print("🔔 Telegram 需要验证码验证")
    print("📱 请检查手机短信，输入5位数字验证码")
    print("="*50)
    
    # 检查stdin是否可用
    if not sys.stdin.isatty():
        print("⚠️ 检测到非交互式环境，请使用以下方式输入验证码：")
        print("1. 使用 docker attach tg2em-scrape 连接到容器")
        print("2. 或者重启容器时添加 -it 参数")
        print("3. 或者通过环境变量传递验证码")
        
        # 尝试从环境变量获取验证码
        import os
        code = os.environ.get('TELEGRAM_CODE')
        if code and len(code) == 5 and code.isdigit():
            print(f"✅ 从环境变量获取验证码: {code}")
            logging.info(f"从环境变量获取验证码: {code}")
            return code
        else:
            raise Exception("无法在非交互式环境中获取验证码，请使用 docker attach 或设置 TELEGRAM_CODE 环境变量")
    
    # 交互式输入
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            print(f"请输入验证码 (尝试 {attempt + 1}/{max_attempts}): ", end='', flush=True)
            code = input().strip()
            
            if len(code) == 5 and code.isdigit():
                print(f"✅ 收到验证码: {code}")
                logging.info(f"用户输入验证码: {code}")
                return code
            else:
                print("❌ 验证码格式错误，请输入5位数字")
                
        except EOFError:
            print("\n❌ 输入流结束，无法读取验证码")
            print("💡 请使用以下方式重新启动：")
            print("   docker-compose down")
            print("   docker-compose up -d")
            print("   docker attach tg2em-scrape")
            raise Exception("无法读取验证码输入")
            
        except KeyboardInterrupt:
            print("\n❌ 用户取消输入")
            raise Exception("用户取消验证码输入")
            
        except Exception as e:
            print(f"❌ 输入错误: {e}")
            if attempt == max_attempts - 1:
                raise Exception(f"验证码输入失败: {e}")
            continue
    
    raise Exception("验证码输入尝试次数过多")

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
    """主函数（优化版本）"""
    global client
    logging.info("🚀 采集脚本启动")
    
    try:
        # 初始化数据库连接池
        await init_mysql_pool()
        logging.info("✅ 数据库连接池初始化完成")
        
        # 初始化并登录 Telegram 客户端
        await init_telegram_client()
        logging.info("✅ Telegram客户端初始化完成")
        
        # 开始执行定时采集任务
        logging.info("🔄 开始执行定时采集任务...")
        await run_periodic_scraper()
        
    except KeyboardInterrupt:
        logging.info("⏹️ 采集脚本被用户中断")
    except Exception as e:
        logging.error(f"❌ 主函数运行出错: {e}")
        raise
    finally:
        # 清理资源
        if client:
            try:
                await client.disconnect()
                logging.info("📱 Telegram 客户端已断开连接")
            except Exception as e:
                logging.warning(f"⚠️ 断开Telegram连接时出错: {e}")
        
        try:
            await close_mysql_pool()
            logging.info("🗄️ 数据库连接池已关闭")
        except Exception as e:
            logging.warning(f"⚠️ 关闭数据库连接池时出错: {e}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("采集脚本已手动停止")
    finally:
        loop.close()
