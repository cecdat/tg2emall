# 数据库补丁文件

## ads.txt配置项补丁

- `add_ads_txt_config.sql` - 完整版本，包含存在性检查和验证
- `add_ads_txt_simple.sql` - 简单版本，直接插入配置项

## 广告位position字段补丁

- `update_advertisement_positions.sql` - 完整版本，包含验证查询
- `update_advertisement_positions_simple.sql` - 简单版本，直接修改字段

## 执行方法

### 方法1：使用Docker执行（推荐）

```bash
# 进入MySQL容器
docker exec -it tg2em-mysql mysql -u tg2emall -p tg2em

# 在MySQL中执行
source /docker-entrypoint-initdb.d/add_ads_txt_config.sql;
```

### 方法2：直接执行SQL文件

```bash
# 将SQL文件复制到容器中
docker cp sql/add_ads_txt_config.sql tg2em-mysql:/tmp/

# 在容器中执行
docker exec -it tg2em-mysql mysql -u tg2emall -p tg2em -e "source /tmp/add_ads_txt_config.sql"
```

### 方法3：手动执行SQL

```sql
-- 连接到MySQL数据库
mysql -u tg2emall -p tg2em

-- 执行以下SQL
INSERT INTO system_config (config_key, config_value, config_type, description, category) 
SELECT 'ads_txt_content', '', 'text', 'ads.txt文件内容，用于Google广告授权', 'ads'
WHERE NOT EXISTS (
    SELECT 1 FROM system_config WHERE config_key = 'ads_txt_content'
);
```

## 验证

执行后可以通过以下SQL验证：

```sql
SELECT * FROM system_config WHERE config_key = 'ads_txt_content';
```

## 配置ads.txt内容

配置项添加后，可以通过以下方式设置ads.txt内容：

1. 访问管理后台：`https://your-domain.com/dm`
2. 进入"配置管理"页面
3. 找到"ads.txt文件内容"配置项
4. 编辑并保存内容

## ads.txt内容示例

```
# ads.txt file for tg2emall
# This file is used to authorize digital sellers to sell your inventory

# Google AdSense (请替换为您的实际Publisher ID)
google.com, pub-YOUR_PUBLISHER_ID, DIRECT, f08c47fec0942fa0

# Facebook Audience Network (请替换为您的实际Placement ID)
# facebook.com, YOUR_FACEBOOK_PLACEMENT_ID, DIRECT, c3e20eee3f780d68
```

## 访问ads.txt

配置完成后，访问 `https://your-domain.com/ads.txt` 即可查看ads.txt文件内容。

## 广告位position字段补丁

### 问题说明

创建广告位时出现错误：`Data truncated for column 'position' at row 1`

**原因：** `advertisements`表的`position`字段是`enum`类型，只包含`'search_list','article_detail','both'`，但代码中使用了更多位置值。

### 执行广告位补丁

```bash
# 执行广告位补丁
docker cp sql/update_advertisement_positions.sql tg2em-mysql:/tmp/
docker exec -it tg2em-mysql mysql -u tg2emall -p tg2em -e "source /tmp/update_advertisement_positions.sql"
```

### 验证广告位补丁

```sql
-- 查看position字段的enum值
SHOW COLUMNS FROM `advertisements` LIKE 'position';
```

### 支持的广告位置

补丁后支持以下广告位置：
- `search_list` - 搜索结果页
- `article_detail` - 文章详情页
- `both` - 两个位置都显示
- `homepage-middle` - 首页中间
- `homepage-resources` - 首页资源区
- `article-middle` - 文章中间
- `article-sidebar` - 文章侧边栏
- `home-banner` - 首页横幅
- `sidebar` - 侧边栏
