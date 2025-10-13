-- tg2emall 数据库升级脚本 - 添加文章点击统计功能
-- 版本: v2.3

USE `tg2em`;

-- 为 messages 表添加点击统计字段
ALTER TABLE `messages` 
ADD COLUMN `click_count` int(11) DEFAULT 0 COMMENT '点击次数' AFTER `is_deleted`,
ADD COLUMN `last_clicked_at` timestamp NULL DEFAULT NULL COMMENT '最后点击时间' AFTER `click_count`;

-- 添加索引优化查询性能
ALTER TABLE `messages` 
ADD KEY `idx_click_count` (`click_count`),
ADD KEY `idx_last_clicked_at` (`last_clicked_at`);

-- 创建文章点击日志表
CREATE TABLE IF NOT EXISTS `article_click_logs` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `article_id` int(11) NOT NULL COMMENT '文章ID',
  `visitor_ip` varchar(45) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '访问者IP',
  `user_agent` text COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '用户代理字符串',
  `referrer` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '来源页面',
  `session_id` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '会话ID',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '点击时间',
  PRIMARY KEY (`id`),
  KEY `idx_article_id` (`article_id`),
  KEY `idx_created_at` (`created_at`),
  KEY `idx_visitor_ip` (`visitor_ip`),
  CONSTRAINT `fk_article_click_logs_article` FOREIGN KEY (`article_id`) REFERENCES `messages` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章点击日志表';

-- 更新统计信息视图，包含点击统计
CREATE OR REPLACE VIEW `v_statistics` AS
SELECT 
    (SELECT COUNT(*) FROM `messages` WHERE `is_deleted` = 0) AS `total_messages`,
    (SELECT COUNT(*) FROM `messages` WHERE DATE(`created_at`) = CURDATE() AND `is_deleted` = 0) AS `today_count`,
    (SELECT COUNT(*) FROM `channels` WHERE `is_active` = 1) AS `active_channels`,
    (SELECT COUNT(DISTINCT `sort_id`) FROM `messages` WHERE `sort_id` IS NOT NULL AND `is_deleted` = 0) AS `total_categories`,
    (SELECT COUNT(*) FROM `messages` WHERE `is_pinned` = 1 AND `is_deleted` = 0) AS `pinned_messages`,
    (SELECT COUNT(*) FROM `advertisements` WHERE `is_active` = 1) AS `active_ads`,
    (SELECT SUM(`click_count`) FROM `messages` WHERE `is_deleted` = 0) AS `total_clicks`,
    (SELECT COUNT(*) FROM `article_click_logs` WHERE DATE(`created_at`) = CURDATE()) AS `today_clicks`;

COMMIT;
