-- 修复favicon路径问题
-- 删除可能存在的错误favicon配置

-- 删除错误的favicon配置
DELETE FROM system_config WHERE config_key = 'site_favicon';

-- 删除可能存在的其他错误favicon相关配置
DELETE FROM system_config WHERE config_key LIKE '%favicon%';

-- 检查并清理可能影响favicon路径的配置
-- 确保public_url不会影响favicon路径
UPDATE system_config 
SET config_value = 'https://237890.xyz' 
WHERE config_key = 'public_url' AND config_value = 'https://img.237890.xyz';

-- 如果需要，可以添加正确的favicon配置
-- INSERT INTO system_config (config_key, config_value, config_type, description, category) 
-- VALUES ('site_favicon', '/static/img/icon.ico', 'string', '网站图标路径', 'seo');
