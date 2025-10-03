-- 修复配置描述乱码问题
-- 更新系统配置表中的描述字段

USE tg2em;

UPDATE system_config SET description = 'tgState 图床上传服务的 Telegram Bot Token' WHERE config_key = 'tgstate_token';
UPDATE system_config SET description = 'tgState 图床上传的目标频道（@channel_name）' WHERE config_key = 'tgstate_target';
UPDATE system_config SET description = 'tgState 图床访问密码（设置访问保护）' WHERE config_key = 'tgstate_pass';
UPDATE system_config SET description = 'tgState 运行模式（p=API模式，m=文件服务模式）' WHERE config_key = 'tgstate_mode';
UPDATE system_config SET description = 'tgState 服务基础URL' WHERE config_key = 'tgstate_url';

UPDATE system_config SET description = 'Telegram API ID（从 https://my.telegram.org 获取）' WHERE config_key = 'telegram_api_id';
UPDATE system_config SET description = 'Telegram API Hash（从 https://my.telegram.org 获取）' WHERE config_key = 'telegram_api_hash';
UPDATE system_config SET description = 'Telegram 会话文件名' WHERE config_key = 'telegram_session_name';
UPDATE system_config SET description = '要采集的目标频道列表（JSON格式）' WHERE config_key = 'scrape_channels';
UPDATE system_config SET description = '每次采集的消息数量' WHERE config_key = 'scrape_limit';
UPDATE system_config SET description = '采集间隔时间（秒）' WHERE config_key = 'scrape_interval';
