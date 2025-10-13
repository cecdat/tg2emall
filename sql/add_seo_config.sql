-- 添加SEO优化相关配置参数
-- 执行时间：2025-01-13

-- 网站基本信息
INSERT INTO system_config (config_key, config_name, config_value, config_type, config_description, category, created_by, updated_by) VALUES
('site_name', '网站名称', 'tg2emall', 'string', '网站的名称，用于页面标题和SEO', 'seo', 'system', 'system'),
('site_description', '网站描述', '专业的Telegram资源采集与分享平台', 'text', '网站的简短描述，用于meta description', 'seo', 'system', 'system'),
('site_keywords', '网站关键词', 'telegram,资源,采集,分享,网盘,下载', 'text', '网站的关键词，用逗号分隔，用于SEO优化', 'seo', 'system', 'system'),
('site_author', '网站作者', 'tg2emall团队', 'string', '网站的作者信息', 'seo', 'system', 'system'),
('site_url', '网站URL', 'https://your-domain.com', 'string', '网站的完整URL地址，用于生成绝对链接', 'seo', 'system', 'system');

-- SEO优化设置
INSERT INTO system_config (config_key, config_name, config_value, config_type, config_description, category, created_by, updated_by) VALUES
('seo_title_template', '页面标题模板', '{title} - {site_name}', 'string', '页面标题的模板格式，{title}为页面标题，{site_name}为网站名称', 'seo', 'system', 'system'),
('seo_description_length', '描述长度限制', '160', 'integer', 'meta description的最大字符数', 'seo', 'system', 'system'),
('seo_keywords_length', '关键词长度限制', '200', 'integer', 'meta keywords的最大字符数', 'seo', 'system', 'system'),
('seo_enable_og_tags', '启用Open Graph标签', 'true', 'boolean', '是否启用Open Graph标签用于社交媒体分享', 'seo', 'system', 'system'),
('seo_enable_twitter_cards', '启用Twitter卡片', 'true', 'boolean', '是否启用Twitter卡片用于Twitter分享', 'seo', 'system', 'system');

-- 社交媒体信息
INSERT INTO system_config (config_key, config_name, config_value, config_type, config_description, category, created_by, updated_by) VALUES
('social_facebook', 'Facebook页面', '', 'string', 'Facebook官方页面URL', 'seo', 'system', 'system'),
('social_twitter', 'Twitter账号', '', 'string', 'Twitter官方账号', 'seo', 'system', 'system'),
('social_telegram', 'Telegram频道', '', 'string', 'Telegram官方频道链接', 'seo', 'system', 'system'),
('social_github', 'GitHub仓库', '', 'string', 'GitHub项目仓库链接', 'seo', 'system', 'system');

-- 网站图标和Logo
INSERT INTO system_config (config_key, config_name, config_value, config_type, config_description, category, created_by, updated_by) VALUES
('site_favicon', '网站图标', '/static/images/favicon.ico', 'string', '网站favicon图标路径', 'seo', 'system', 'system'),
('site_logo', '网站Logo', '/static/images/logo.png', 'string', '网站Logo图片路径', 'seo', 'system', 'system'),
('site_logo_alt', 'Logo替代文本', 'tg2emall Logo', 'string', 'Logo图片的alt属性文本', 'seo', 'system', 'system');

-- 统计和分析
INSERT INTO system_config (config_key, config_name, config_value, config_type, config_description, category, created_by, updated_by) VALUES
('google_analytics', 'Google Analytics ID', '', 'string', 'Google Analytics跟踪ID', 'seo', 'system', 'system'),
('google_search_console', 'Google Search Console验证码', '', 'string', 'Google Search Console验证码', 'seo', 'system', 'system'),
('baidu_tongji', '百度统计ID', '', 'string', '百度统计跟踪ID', 'seo', 'system', 'system'),
('cnzz_tongji', 'CNZZ统计ID', '', 'string', 'CNZZ统计跟踪ID', 'seo', 'system', 'system');

-- 结构化数据
INSERT INTO system_config (config_key, config_name, config_value, config_type, config_description, category, created_by, updated_by) VALUES
('structured_data_organization', '组织信息JSON-LD', '{"@context": "https://schema.org", "@type": "Organization", "name": "tg2emall", "url": "https://your-domain.com"}', 'text', '网站组织的结构化数据JSON-LD格式', 'seo', 'system', 'system'),
('structured_data_website', '网站信息JSON-LD', '{"@context": "https://schema.org", "@type": "WebSite", "name": "tg2emall", "url": "https://your-domain.com"}', 'text', '网站的结构化数据JSON-LD格式', 'seo', 'system', 'system'),
('enable_structured_data', '启用结构化数据', 'true', 'boolean', '是否在页面中输出结构化数据', 'seo', 'system', 'system');

-- 更新现有配置的分类（如果有的话）
UPDATE system_config SET category = 'seo' WHERE config_key IN ('site_name', 'site_description', 'site_keywords') AND category != 'seo';
