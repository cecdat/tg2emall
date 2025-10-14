-- 更新广告位position字段的enum值
-- 执行时间：2025-01-13
-- 用途：添加代码中使用的所有广告位置

-- 修改advertisements表的position字段，添加新的广告位置
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

-- 验证修改结果
SHOW COLUMNS FROM `advertisements` LIKE 'position';
