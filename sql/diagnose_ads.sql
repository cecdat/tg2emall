-- 诊断广告位相关问题的SQL脚本
-- 执行时间：2025-01-13

-- 1. 检查advertisements表结构
DESCRIBE advertisements;

-- 2. 检查position字段的enum值
SHOW COLUMNS FROM advertisements LIKE 'position';

-- 3. 检查当前广告位数据
SELECT COUNT(*) as total_ads FROM advertisements;
SELECT * FROM advertisements ORDER BY created_at DESC LIMIT 5;

-- 4. 检查是否有失败的插入记录（通过日志表或其他方式）
-- 注意：这个查询可能不会返回结果，因为失败的插入通常不会留下记录

-- 5. 测试插入一个简单的广告位（用于测试）
-- 注意：这个插入可能会失败，如果position字段的enum值不完整
-- INSERT INTO advertisements (name, position, ad_code, is_active) 
-- VALUES ('测试广告', 'search_list', '测试代码', 1);

-- 6. 检查数据库连接和权限
SELECT USER(), DATABASE();
