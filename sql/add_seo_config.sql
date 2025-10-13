-- 添加SEO优化相关配置参数
-- 执行时间：2025-01-13

-- 网站基本信息
INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
('site_name', 'tg2emall', 'string', '网站的名称，用于页面标题和SEO', 'seo'),
('site_description', '专业的Telegram资源采集与分享平台', 'string', '网站的简短描述，用于meta description', 'seo'),
('site_keywords', 'telegram,资源,采集,分享,网盘,下载', 'string', '网站的关键词，用逗号分隔，用于SEO优化', 'seo'),
('site_author', 'tg2emall团队', 'string', '网站的作者信息', 'seo'),
('site_url', 'https://your-domain.com', 'string', '网站的完整URL地址，用于生成绝对链接', 'seo');

-- SEO优化设置
INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
('seo_title_template', '{title} - {site_name}', 'string', '页面标题的模板格式，{title}为页面标题，{site_name}为网站名称', 'seo'),
('seo_description_length', '160', 'number', 'meta description的最大字符数', 'seo'),
('seo_keywords_length', '200', 'number', 'meta keywords的最大字符数', 'seo'),
('seo_enable_og_tags', 'true', 'boolean', '是否启用Open Graph标签用于社交媒体分享', 'seo'),
('seo_enable_twitter_cards', 'true', 'boolean', '是否启用Twitter卡片用于Twitter分享', 'seo');

-- 社交媒体信息
INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
('social_facebook', '', 'string', 'Facebook官方页面URL', 'seo'),
('social_twitter', '', 'string', 'Twitter官方账号', 'seo'),
('social_telegram', '', 'string', 'Telegram官方频道链接', 'seo'),
('social_github', '', 'string', 'GitHub项目仓库链接', 'seo');

-- 网站图标和Logo
INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
('site_favicon', '/static/images/favicon.ico', 'string', '网站favicon图标路径', 'seo'),
('site_logo', '/static/images/logo.png', 'string', '网站Logo图片路径', 'seo'),
('site_logo_alt', 'tg2emall Logo', 'string', 'Logo图片的alt属性文本', 'seo');

-- 统计和分析
INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
('google_analytics', '', 'string', 'Google Analytics跟踪ID', 'seo'),
('google_search_console', '', 'string', 'Google Search Console验证码', 'seo'),
('baidu_tongji', '', 'string', '百度统计跟踪ID', 'seo'),
('cnzz_tongji', '', 'string', 'CNZZ统计跟踪ID', 'seo');

-- 结构化数据
INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
('structured_data_organization', '{"@context": "https://schema.org", "@type": "Organization", "name": "tg2emall", "url": "https://your-domain.com"}', 'json', '网站组织的结构化数据JSON-LD格式', 'seo'),
('structured_data_website', '{"@context": "https://schema.org", "@type": "WebSite", "name": "tg2emall", "url": "https://your-domain.com"}', 'json', '网站的结构化数据JSON-LD格式', 'seo'),
('enable_structured_data', 'true', 'boolean', '是否在页面中输出结构化数据', 'seo');

-- 更新现有配置的分类（如果有的话）
UPDATE system_config SET category = 'seo' WHERE config_key IN ('site_name', 'site_description', 'site_keywords') AND category != 'seo';
