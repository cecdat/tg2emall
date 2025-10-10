-- tg2emall 数据库迁移脚本
-- 添加缺失的表：search_logs 和 visit_logs

USE `tg2em`;

-- --------------------------------------------------------
-- 创建 search_logs 表（如果不存在）
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
-- 创建 visit_logs 表（如果不存在）
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
-- 如果存在 site_visits 表，将数据迁移到 visit_logs
-- --------------------------------------------------------

-- 检查是否存在 site_visits 表
SET @table_exists = (
    SELECT COUNT(*)
    FROM information_schema.tables 
    WHERE table_schema = 'tg2em' 
    AND table_name = 'site_visits'
);

-- 如果存在 site_visits 表，迁移数据
SET @sql = IF(@table_exists > 0, 
    'INSERT INTO visit_logs (visitor_ip, user_agent, page_path, referrer, visit_source, session_id, created_at)
     SELECT visitor_ip, user_agent, page_path, referrer, visit_source, session_id, created_at 
     FROM site_visits 
     WHERE NOT EXISTS (SELECT 1 FROM visit_logs WHERE visit_logs.id = site_visits.id)',
    'SELECT "site_visits table does not exist" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 如果存在 site_visits 表，删除它
SET @sql = IF(@table_exists > 0, 
    'DROP TABLE site_visits',
    'SELECT "site_visits table does not exist" as message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 插入一些示例搜索数据（用于测试）
INSERT IGNORE INTO `search_logs` (`search_keyword`, `visitor_ip`, `results_count`) VALUES
('Baidu Cloud', '127.0.0.1', 15),
('Aliyun Drive', '127.0.0.1', 12),
('Quark Drive', '127.0.0.1', 8),
('Mobile Cloud', '127.0.0.1', 6),
('Cloud Storage', '127.0.0.1', 25);

SELECT 'Database migration completed successfully!' as status;
