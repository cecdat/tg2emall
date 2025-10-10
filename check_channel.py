#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram频道诊断工具
用于检查频道ID是否正确，以及机器人是否有权限访问
"""

import asyncio
import logging
import os
import sys
from telethon import TelegramClient
from telethon.errors import ChannelInvalidError, ChannelPrivateError, ChatAdminRequiredError

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def check_channel_access(api_id, api_hash, phone_number, channel_id):
    """检查频道访问权限"""
    
    # 创建客户端
    client = TelegramClient('channel_check', api_id, api_hash)
    
    try:
        # 启动客户端
        await client.start(phone=lambda: phone_number)
        logger.info("✅ Telegram客户端启动成功")
        
        # 获取当前用户信息
        me = await client.get_me()
        logger.info(f"📱 当前用户: {me.username or me.first_name}")
        
        # 尝试获取频道信息
        logger.info(f"🔍 检查频道ID: {channel_id}")
        
        try:
            # 尝试获取频道实体
            channel = await client.get_entity(channel_id)
            logger.info(f"✅ 成功获取频道信息:")
            logger.info(f"   - 频道名称: {channel.title}")
            logger.info(f"   - 频道ID: {channel.id}")
            logger.info(f"   - 频道类型: {type(channel).__name__}")
            
            # 检查是否是公开频道
            if hasattr(channel, 'username') and channel.username:
                logger.info(f"   - 频道用户名: @{channel.username}")
                logger.info(f"   - 频道链接: https://t.me/{channel.username}")
            
            # 尝试获取频道成员数量
            try:
                participants_count = await client.get_participants_count(channel)
                logger.info(f"   - 成员数量: {participants_count}")
            except Exception as e:
                logger.warning(f"   - 无法获取成员数量: {e}")
            
            # 尝试获取最近的消息
            try:
                messages = []
                async for message in client.iter_messages(channel, limit=3):
                    messages.append(message)
                
                if messages:
                    logger.info(f"   - 最近消息数量: {len(messages)}")
                    for i, msg in enumerate(messages, 1):
                        logger.info(f"     消息{i}: {msg.text[:50] if msg.text else '无文本'}...")
                else:
                    logger.warning("   - 没有找到任何消息")
                    
            except Exception as e:
                logger.warning(f"   - 无法获取消息: {e}")
            
            return True
            
        except ChannelInvalidError:
            logger.error("❌ 频道ID无效或不存在")
            return False
            
        except ChannelPrivateError:
            logger.error("❌ 频道是私有的，机器人没有加入该频道")
            logger.info("💡 解决方案:")
            logger.info("   1. 确保机器人已加入该频道")
            logger.info("   2. 或者使用公开频道的用户名（如 @channel_name）")
            return False
            
        except ChatAdminRequiredError:
            logger.error("❌ 需要管理员权限才能访问该频道")
            return False
            
        except Exception as e:
            logger.error(f"❌ 获取频道信息失败: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Telegram客户端启动失败: {e}")
        return False
        
    finally:
        await client.disconnect()

async def main():
    """主函数"""
    if len(sys.argv) != 5:
        print("用法: python check_channel.py <API_ID> <API_HASH> <PHONE_NUMBER> <CHANNEL_ID>")
        print("示例: python check_channel.py 123456 your_api_hash +1234567890 -1002726412745")
        sys.exit(1)
    
    api_id = int(sys.argv[1])
    api_hash = sys.argv[2]
    phone_number = sys.argv[3]
    channel_id = int(sys.argv[4])
    
    logger.info("🔍 Telegram频道诊断工具")
    logger.info("=" * 50)
    
    success = await check_channel_access(api_id, api_hash, phone_number, channel_id)
    
    if success:
        logger.info("✅ 频道检查完成，可以正常使用")
    else:
        logger.info("❌ 频道检查失败，请检查配置")
        logger.info("💡 常见解决方案:")
        logger.info("   1. 检查频道ID是否正确")
        logger.info("   2. 确保机器人已加入频道")
        logger.info("   3. 使用公开频道的用户名代替ID")
        logger.info("   4. 检查频道是否仍然存在")

if __name__ == "__main__":
    asyncio.run(main())
