#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Telegram频道ID验证工具
专门用于验证频道ID是否正确，以及机器人是否有权限访问
"""

import asyncio
import logging
import os
import sys
from telethon import TelegramClient
from telethon.errors import (
    ChannelInvalidError, 
    ChannelPrivateError, 
    ChatAdminRequiredError,
    FloodWaitError,
    AuthKeyUnregisteredError
)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def verify_channel_id(api_id, api_hash, phone_number, channel_id):
    """验证频道ID"""
    
    # 创建客户端
    client = TelegramClient('channel_verify', api_id, api_hash)
    
    try:
        # 启动客户端
        await client.start(phone=lambda: phone_number)
        logger.info("✅ Telegram客户端启动成功")
        
        # 获取当前用户信息
        me = await client.get_me()
        logger.info(f"📱 当前用户: {me.username or me.first_name} (ID: {me.id})")
        
        # 验证频道ID格式
        logger.info(f"🔍 验证频道ID: {channel_id}")
        
        if not isinstance(channel_id, int):
            try:
                channel_id = int(channel_id)
            except ValueError:
                logger.error("❌ 频道ID必须是数字")
                return False
        
        if channel_id > 0:
            logger.warning("⚠️ 频道ID是正数，这通常是群组ID而不是频道ID")
            logger.info("💡 频道ID通常是负数，如 -1002726412745")
        
        # 尝试获取频道信息
        try:
            channel = await client.get_entity(channel_id)
            logger.info(f"✅ 成功获取频道信息:")
            logger.info(f"   - 频道名称: {channel.title}")
            logger.info(f"   - 频道ID: {channel.id}")
            logger.info(f"   - 频道类型: {type(channel).__name__}")
            
            # 检查频道类型
            if hasattr(channel, 'broadcast') and channel.broadcast:
                logger.info("   - 这是一个广播频道")
            elif hasattr(channel, 'megagroup') and channel.megagroup:
                logger.info("   - 这是一个超级群组")
            else:
                logger.info("   - 这是一个普通群组")
            
            # 检查是否是公开频道
            if hasattr(channel, 'username') and channel.username:
                logger.info(f"   - 频道用户名: @{channel.username}")
                logger.info(f"   - 频道链接: https://t.me/{channel.username}")
            else:
                logger.info("   - 这是一个私有频道")
            
            # 尝试获取频道成员数量
            try:
                participants_count = await client.get_participants_count(channel)
                logger.info(f"   - 成员数量: {participants_count}")
            except Exception as e:
                logger.warning(f"   - 无法获取成员数量: {e}")
            
            # 尝试获取最近的消息
            try:
                messages = []
                async for message in client.iter_messages(channel, limit=5):
                    messages.append(message)
                
                if messages:
                    logger.info(f"   - 最近消息数量: {len(messages)}")
                    for i, msg in enumerate(messages, 1):
                        text_preview = msg.text[:100] if msg.text else "无文本"
                        logger.info(f"     消息{i}: {text_preview}...")
                else:
                    logger.warning("   - 没有找到任何消息")
                    
            except Exception as e:
                logger.warning(f"   - 无法获取消息: {e}")
            
            # 测试消息迭代器
            try:
                message_count = 0
                async for message in client.iter_messages(channel, limit=1):
                    message_count += 1
                    break
                
                if message_count > 0:
                    logger.info("✅ 消息迭代器测试成功，可以正常采集消息")
                else:
                    logger.warning("⚠️ 消息迭代器测试失败，可能无法采集消息")
                    
            except Exception as e:
                logger.error(f"❌ 消息迭代器测试失败: {e}")
                return False
            
            return True
            
        except ChannelInvalidError:
            logger.error("❌ 频道ID无效或不存在")
            logger.info("💡 可能的原因:")
            logger.info("   1. 频道ID输入错误")
            logger.info("   2. 频道已被删除")
            logger.info("   3. 频道被Telegram官方封禁")
            return False
            
        except ChannelPrivateError:
            logger.error("❌ 频道是私有的，机器人没有加入该频道")
            logger.info("💡 解决方案:")
            logger.info("   1. 将机器人添加到频道中")
            logger.info("   2. 给机器人管理员权限")
            logger.info("   3. 或者使用公开频道")
            return False
            
        except ChatAdminRequiredError:
            logger.error("❌ 需要管理员权限才能访问该频道")
            logger.info("💡 解决方案:")
            logger.info("   1. 给机器人管理员权限")
            logger.info("   2. 或者使用公开频道")
            return False
            
        except FloodWaitError as e:
            logger.error(f"❌ 请求过于频繁，需要等待 {e.seconds} 秒")
            return False
            
        except AuthKeyUnregisteredError:
            logger.error("❌ 认证密钥未注册，请重新登录")
            return False
            
        except Exception as e:
            logger.error(f"❌ 获取频道信息失败: {e}")
            logger.info("💡 可能的原因:")
            logger.info("   1. 网络连接问题")
            logger.info("   2. Telegram API限制")
            logger.info("   3. 频道访问权限问题")
            return False
            
    except Exception as e:
        logger.error(f"❌ Telegram客户端启动失败: {e}")
        return False
        
    finally:
        await client.disconnect()

async def main():
    """主函数"""
    if len(sys.argv) != 5:
        print("用法: python verify_channel_id.py <API_ID> <API_HASH> <PHONE_NUMBER> <CHANNEL_ID>")
        print("示例: python verify_channel_id.py 123456 your_api_hash +1234567890 -1002726412745")
        sys.exit(1)
    
    api_id = int(sys.argv[1])
    api_hash = sys.argv[2]
    phone_number = sys.argv[3]
    channel_id = int(sys.argv[4])
    
    logger.info("🔍 Telegram频道ID验证工具")
    logger.info("=" * 50)
    
    success = await verify_channel_id(api_id, api_hash, phone_number, channel_id)
    
    if success:
        logger.info("✅ 频道ID验证成功，可以正常使用")
        logger.info("💡 建议:")
        logger.info("   1. 在配置管理页面添加此频道ID")
        logger.info("   2. 设置合适的采集数量限制")
        logger.info("   3. 定期检查采集状态")
    else:
        logger.info("❌ 频道ID验证失败，请检查配置")
        logger.info("💡 常见解决方案:")
        logger.info("   1. 检查频道ID是否正确")
        logger.info("   2. 确保机器人已加入频道")
        logger.info("   3. 给机器人管理员权限")
        logger.info("   4. 检查频道是否仍然存在")

if __name__ == "__main__":
    asyncio.run(main())
