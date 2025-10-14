-- 完整修复广告位功能的SQL脚本
-- 执行时间：2025-01-13

-- 1. 首先更新position字段的enum值
ALTER TABLE `advertisements` 
MODIFY COLUMN `position` enum(
    'search_list',
    'article_detail', 
    'both',
    'homepage-middle',
    'homepage-resources',
    'article-middle',
    'article-sidebar',
    'home-banner',
    'sidebar'
) COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '广告位置';

-- 2. 验证position字段修改
SHOW COLUMNS FROM advertisements LIKE 'position';

-- 3. 检查当前广告位数量
SELECT COUNT(*) as current_ads_count FROM advertisements;

-- 4. 测试插入一个广告位（可选，用于验证）
-- 取消注释下面的代码来测试插入
/*
INSERT INTO advertisements (name, position, ad_code, is_active, sort_order) 
VALUES (
    '测试广告位', 
    'home-banner', 
    '<div>测试广告代码</div>', 
    1, 
    0
);
*/

-- 5. 最终验证
SELECT 
    id, 
    name, 
    position, 
    is_active, 
    created_at 
FROM advertisements 
ORDER BY created_at DESC 
LIMIT 10;
