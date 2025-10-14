-- 添加ads.txt配置项
-- 执行时间：2025-01-13
-- 用途：支持Google广告ads.txt文件配置

-- 检查配置项是否已存在，如果不存在则添加
INSERT INTO system_config (config_key, config_value, config_type, description, category) 
SELECT 'ads_txt_content', '', 'string', 'ads.txt文件内容，用于Google广告授权', 'ads'
WHERE NOT EXISTS (
    SELECT 1 FROM system_config WHERE config_key = 'ads_txt_content'
);

-- 验证插入结果
SELECT 
    config_key,
    config_value,
    config_type,
    description,
    category,
    created_at
FROM system_config 
WHERE config_key = 'ads_txt_content';
