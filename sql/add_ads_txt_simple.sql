-- 简单版本：直接添加ads.txt配置项
-- 如果配置项已存在会报错，可以忽略

INSERT INTO system_config (config_key, config_value, config_type, description, category) VALUES
('ads_txt_content', '', 'string', 'ads.txt文件内容，用于Google广告授权', 'ads');
