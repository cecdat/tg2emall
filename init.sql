-- tg2emall 数据库初始化脚本
-- 用于 Telegram 频道采集和发布系统

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS `tg2em` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `tg2em`;

-- --------------------------------------------------------
-- 表的结构 `system_config` - 系统配置表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `system_config` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `config_key` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '配置键',
  `config_value` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '配置值',
  `config_type` enum('string','number','boolean','json') NOT NULL DEFAULT 'string' COMMENT '配置类型',
  `description` varchar(200) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '配置描述',
  `category` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'general' COMMENT '配置分类',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `config_key` (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO `system_config` (`config_key`, `config_value`, `config_type`, `description`, `category`) VALUES
-- tgState 图床配置
('tgstate_token', '', 'string', 'tgState 图床上传服务的 Telegram Bot Token', 'tgstate'),
('tgstate_target', '', 'string', 'tgState 图床上传的目标频道（@channel_name）', 'tgstate'),
('tgstate_pass', 'none', 'string', 'tgState 图床访问密码（设置访问保护）', 'tgstate'),
('tgstate_mode', 'p', 'string', 'tgState 运行模式（p=API模式，m=文件服务模式）', 'tgstate'),
('tgstate_url', 'https://img.237890.xyz', 'string', 'tgState 基础URL地址', 'tgstate'),
('public_url', 'https://img.237890.xyz', 'string', '公网访问地址（用于图片URL生成）', 'tgstate'),

-- Telegram 采集配置
('telegram_api_id', '', 'string', 'Telegram API ID（从 https://my.telegram.org 获取）', 'telegram'),
('telegram_api_hash', '', 'string', 'Telegram API Hash（从 https://my.telegram.org 获取）', 'telegram'),
('telegram_phone', '', 'string', 'Telegram绑定手机号码（带国家代码）', 'telegram'),
('telegram_session_name', 'tg2em_scraper', 'string', 'Telegram 会话文件名', 'telegram'),
('scrape_channels', '', 'string', '要采集的目标频道列表（每行一个，支持URL或频道ID）', 'telegram'),
('scrape_limit', '10', 'number', '每次采集的消息数量', 'telegram'),
('scrape_interval', '300', 'number', '采集间隔时间（秒）', 'telegram'),

-- 图片配置
('image_compression_quality', '50', 'number', '图片压缩质量（1-95）', 'image'),
('image_compression_format', 'webp', 'string', '图片压缩格式（webp或jpeg）', 'image'),

-- 双服务架构配置
('scraper_management_port', '2003', 'number', '采集服务管理端口', 'scraper'),
('scraper_service_port', '5002', 'number', '采集服务业务端口', 'scraper'),
('tgstate_management_port', '8001', 'number', '图片服务管理端口', 'tgstate'),
('tgstate_upload_port', '8002', 'number', '图片上传服务端口', 'tgstate'),

-- 管理员配置
('admin_password', 'admin', 'string', '管理员密码', 'admin'),
('admin_captcha', '2025', 'string', '管理员验证码', 'admin');

-- --------------------------------------------------------
-- 表的结构 `services_status` - 服务状态表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `services_status` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `service_name` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '服务名称',
  `status` enum('running','stopped','error','unknown') NOT NULL DEFAULT 'unknown' COMMENT '服务状态',
  `last_check` timestamp NULL DEFAULT NULL COMMENT '最后检查时间',
  `last_start` timestamp NULL DEFAULT NULL COMMENT '最后启动时间',
  `last_stop` timestamp NULL DEFAULT NULL COMMENT '最后停止时间',
  `pid` int(11) DEFAULT NULL COMMENT '进程ID',
  `port` int(11) DEFAULT NULL COMMENT '服务端口',
  `message` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '状态信息',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `service_name` (`service_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='服务状态表';

-- 初始化服务状态
INSERT INTO `services_status` (`service_name`, `status`) VALUES
('tgstate-management', 'running'),
('tgstate-service', 'stopped'),
('scraper-management', 'running'),
('scraper-service', 'stopped'),
('mysql', 'running'),
('frontend', 'running');

-- --------------------------------------------------------
-- 表的结构 `messages` - 消息表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `messages` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` text COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息标题',
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '消息内容',
  `tags` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '标签，逗号分隔',
  `sort_id` int(11) DEFAULT NULL COMMENT '分类ID，用于前端展示',
  `image_url` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '图片URL',
  `source_channel` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源频道',
  `is_pinned` tinyint(1) DEFAULT 0 COMMENT '是否置顶',
  `is_deleted` tinyint(1) DEFAULT 0 COMMENT '是否删除',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_sort_id` (`sort_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_is_pinned` (`is_pinned`),
  KEY `idx_is_deleted` (`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息表';

-- --------------------------------------------------------
-- 表的结构 `processed_messages` - 已处理消息表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `processed_messages` (
  `channel_id` bigint(20) NOT NULL COMMENT '频道ID',
  `message_id` bigint(20) NOT NULL COMMENT '消息ID',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '处理时间',
  PRIMARY KEY (`channel_id`,`message_id`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='已处理消息表，防止重复采集';

-- --------------------------------------------------------
-- 表的结构 `search_logs` - 搜索日志表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `search_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `search_keyword` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '搜索关键字',
  `visitor_ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '搜索者IP',
  `user_agent` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户代理字符串',
  `results_count` int(11) DEFAULT 0 COMMENT '搜索结果数量',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '搜索时间',
  PRIMARY KEY (`id`),
  KEY `idx_search_keyword` (`search_keyword`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_visitor_ip` (`visitor_ip`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='搜索日志表';

-- --------------------------------------------------------
-- 表的结构 `visit_logs` - 访问日志表（重命名site_visits）
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `visit_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `visitor_ip` varchar(45) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '访问者IP',
  `user_agent` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户代理字符串',
  `page_path` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '访问页面路径',
  `referrer` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源页面',
  `visit_source` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '访问来源类型',
  `session_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '会话ID',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '访问时间',
  PRIMARY KEY (`id`),
  KEY `idx_visitor_ip` (`visitor_ip`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_visit_source` (`visit_source`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='访问日志表';

-- --------------------------------------------------------
-- 表的结构 `channels` - 频道信息表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `channels` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `channel_id` bigint(20) NOT NULL COMMENT 'Telegram频道ID',
  `channel_url` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '频道URL',
  `channel_name` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '频道名称',
  `is_active` tinyint(1) DEFAULT 1 COMMENT '是否启用',
  `collect_limit` int(11) DEFAULT 25 COMMENT '采集数量限制',
  `last_collected_at` timestamp NULL DEFAULT NULL COMMENT '最后采集时间',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_channel_id` (`channel_id`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_last_collected_at` (`last_collected_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='频道信息表';


-- --------------------------------------------------------
-- 表的结构 `admin_users` - 管理员用户表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `admin_users` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `username` varchar(50) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '用户名',
  `password` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '密码哈希',
  `is_active` tinyint(1) DEFAULT 1 COMMENT '是否启用',
  `last_login` timestamp NULL DEFAULT NULL COMMENT '最后登录时间',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='管理员用户表';

-- --------------------------------------------------------
-- 表的结构 `advertisements` - 广告表
-- --------------------------------------------------------

CREATE TABLE IF NOT EXISTS `advertisements` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `name` varchar(100) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '广告名称',
  `position` enum('search_list','article_detail','both') COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '广告位置',
  `ad_code` longtext COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '广告代码',
  `is_active` tinyint(1) DEFAULT 1 COMMENT '是否启用',
  `sort_order` int(11) DEFAULT 0 COMMENT '排序',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_position` (`position`),
  KEY `idx_is_active` (`is_active`),
  KEY `idx_sort_order` (`sort_order`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='广告表';

-- --------------------------------------------------------
-- 插入默认管理员用户
-- --------------------------------------------------------

INSERT IGNORE INTO `admin_users` (`username`, `password`, `is_active`) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LQ4bCOYz1rnHxS57.LhiaqHc5JXgfqkjyOuUO', 1);

-- --------------------------------------------------------
-- 创建视图：统计信息视图
-- --------------------------------------------------------

CREATE OR REPLACE VIEW `v_statistics` AS
SELECT 
    (SELECT COUNT(*) FROM `messages` WHERE `is_deleted` = 0) AS `total_messages`,
    (SELECT COUNT(*) FROM `messages` WHERE DATE(`created_at`) = CURDATE() AND `is_deleted` = 0) AS `today_count`,
    (SELECT COUNT(*) FROM `channels` WHERE `is_active` = 1) AS `active_channels`,
    (SELECT COUNT(DISTINCT `sort_id`) FROM `messages` WHERE `sort_id` IS NOT NULL AND `is_deleted` = 0) AS `total_categories`,
    (SELECT COUNT(*) FROM `messages` WHERE `is_pinned` = 1 AND `is_deleted` = 0) AS `pinned_messages`,
    (SELECT COUNT(*) FROM `advertisements` WHERE `is_active` = 1) AS `active_ads`;

COMMIT;

