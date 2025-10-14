# tg2emall API 文档

## 概述

tg2emall 是一个基于 Flask 的博客展示系统，提供完整的文章管理、搜索、分类等功能。本文档详细描述了所有可用的 API 接口，供第三方开发者集成使用。

## 基础信息

- **基础URL**: `http://your-domain.com`
- **API版本**: v1
- **数据格式**: JSON
- **字符编码**: UTF-8

## 认证方式

### 管理员认证
管理员接口需要登录认证，使用 Session 方式：
1. 先调用 `/dm` 接口登录获取 Session
2. 后续请求会自动携带 Session Cookie

## 公共接口

### 1. 首页数据

#### 获取首页内容
```
GET /
```

**响应示例**:
```json
{
  "articles": [...],
  "recent_articles": [...],
  "popular_articles": [...],
  "popular_searches": [...],
  "categories": [...],
  "stats": {
    "total_articles": 100,
    "data_available": true
  }
}
```

### 2. 文章相关接口

#### 获取文章列表
```
GET /api/articles?page=1&limit=10
```

**参数**:
- `page` (int, 可选): 页码，默认 1
- `limit` (int, 可选): 每页数量，默认 10，最大 100

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "title": "文章标题",
      "content": "文章内容",
      "summary": "文章摘要",
      "author": "作者",
      "author_id": 1,
      "created_at": "2025-10-14 10:00:00",
      "updated_at": "2025-10-14 10:00:00",
      "sort_id": 1,
      "tags": ["标签1", "标签2"],
      "view_count": 100,
      "is_published": 1
    }
  ],
  "page": 1,
  "limit": 10
}
```

#### 获取文章详情
```
GET /api/article/{article_id}
```

**参数**:
- `article_id` (int): 文章ID

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "文章标题",
    "content": "文章内容",
    "summary": "文章摘要",
    "author": "作者",
    "author_id": 1,
    "created_at": "2025-10-14 10:00:00",
    "updated_at": "2025-10-14 10:00:00",
    "sort_id": 1,
    "tags": ["标签1", "标签2"],
    "view_count": 100,
    "is_published": 1
  }
}
```

#### 文章详情页
```
GET /article/{article_id}
GET /article/{article_id}.html
```

**响应**: HTML 页面

#### 兼容旧版URL
```
GET /post-{article_id}.html
```

**响应**: 重定向到新URL

### 3. 搜索功能

#### 搜索页面
```
GET /search?q=关键词&page=1
```

**参数**:
- `q` (string): 搜索关键词
- `page` (int, 可选): 页码，默认 1

**响应**: HTML 页面

### 4. 标签功能

#### 标签页面
```
GET /tag/{tag}
```

**参数**:
- `tag` (string): 标签名称

**响应**: HTML 页面

### 5. 作者页面

#### 作者文章列表
```
GET /author/{author_id}
GET /author/{author_id}/page/{page}
```

**参数**:
- `author_id` (int): 作者ID
- `page` (int, 可选): 页码，默认 1

**响应**: HTML 页面

### 6. 瀑布流加载

#### 加载更多内容
```
GET /api/waterfall/load?page=2&limit=12
```

**参数**:
- `page` (int): 页码
- `limit` (int, 可选): 每页数量，默认 12

**响应示例**:
```json
{
  "success": true,
  "data": {
    "articles": [...],
    "advertisements": [...],
    "has_more": true,
    "next_page": 3
  }
}
```

### 7. 统计信息

#### 获取网站统计
```
GET /api/stats
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_articles": 1000,
    "today_articles": 10,
    "total_categories": 5
  }
}
```

### 8. 广告相关

#### Google Ads.txt
```
GET /ads.txt
```

**响应**: 纯文本格式的 ads.txt 内容

## 管理员接口

### 认证相关

#### 管理员登录
```
POST /dm
```

**请求参数**:
```json
{
  "username": "admin",
  "password": "password",
  "captcha": "2025"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "登录成功",
  "redirect": "/admin"
}
```

#### 管理员登出
```
GET /dm/logout
```

**响应**: 重定向到登录页

### 文章管理

#### 获取文章管理页面
```
GET /admin/articles
```

**响应**: HTML 页面

#### 获取文章数据
```
GET /admin/articles/{article_id}/data
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "文章标题",
    "content": "文章内容",
    "summary": "文章摘要",
    "author": "作者",
    "author_id": 1,
    "sort_id": 1,
    "tags": "标签1,标签2",
    "is_published": 1
  }
}
```

#### 更新文章
```
POST /admin/articles/{article_id}
```

**请求参数**:
```json
{
  "title": "新标题",
  "content": "新内容",
  "summary": "新摘要",
  "author": "作者",
  "author_id": 1,
  "sort_id": 1,
  "tags": "标签1,标签2",
  "is_published": 1
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "文章更新成功"
}
```

#### 删除文章
```
POST /admin/articles/{article_id}/delete
```

**响应示例**:
```json
{
  "success": true,
  "message": "文章删除成功"
}
```

### 配置管理

#### 获取配置页面
```
GET /admin/config
```

**响应**: HTML 页面

#### 更新配置
```
POST /admin/config/update
```

**请求参数**:
```json
{
  "config_key": "site_name",
  "config_value": "新网站名称"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "配置更新成功"
}
```

### 服务管理

#### 获取服务管理页面
```
GET /admin/services
```

**响应**: HTML 页面

#### 启动服务
```
POST /admin/services/{service_name}/start
```

**参数**:
- `service_name`: 服务名称 (mysql, frontend, scraper, tgstate)

**响应示例**:
```json
{
  "success": true,
  "message": "服务启动成功"
}
```

#### 停止服务
```
POST /admin/services/{service_name}/stop
```

**响应示例**:
```json
{
  "success": true,
  "message": "服务停止成功"
}
```

#### 重启服务
```
POST /admin/services/{service_name}/restart
```

**响应示例**:
```json
{
  "success": true,
  "message": "服务重启成功"
}
```

#### 获取服务状态
```
GET /admin/services/{service_name}/status
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "status": "running",
    "pid": 1234,
    "uptime": "2h 30m",
    "memory_usage": "50MB"
  }
}
```

#### 启动采集任务
```
POST /admin/services/{service_name}/scrape/start
```

**响应示例**:
```json
{
  "success": true,
  "message": "采集任务启动成功"
}
```

#### 初始化Telegram
```
POST /admin/services/{service_name}/telegram/init
```

**响应示例**:
```json
{
  "success": true,
  "message": "Telegram初始化成功"
}
```

### 密码管理

#### 修改管理员密码
```
POST /admin/password/change
```

**请求参数**:
```json
{
  "current_password": "当前密码",
  "new_password": "新密码",
  "confirm_password": "确认密码"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "密码修改成功"
}
```

#### 修改验证码
```
POST /admin/captcha/change
```

**请求参数**:
```json
{
  "new_captcha": "新验证码"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "验证码修改成功"
}
```

### 广告管理

#### 获取广告列表
```
GET /api/admin/ads
```

**响应示例**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "广告名称",
      "position": "homepage-middle",
      "is_active": 1,
      "created_at": "2025-10-14 10:00:00"
    }
  ]
}
```

#### 创建广告
```
POST /admin/ads/create
```

**请求参数**:
```json
{
  "name": "广告名称",
  "position": "homepage-middle",
  "is_active": 1
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "广告创建成功"
}
```

#### 编辑广告
```
POST /admin/ads/{ad_id}/edit
```

**请求参数**:
```json
{
  "name": "新广告名称",
  "position": "homepage-resources",
  "is_active": 0
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "广告更新成功"
}
```

#### 删除广告
```
POST /admin/ads/{ad_id}/delete
```

**响应示例**:
```json
{
  "success": true,
  "message": "广告删除成功"
}
```

#### 切换广告状态
```
POST /admin/ads/{ad_id}/toggle
```

**响应示例**:
```json
{
  "success": true,
  "message": "广告状态切换成功"
}
```

### 缓存管理

#### 获取缓存管理页面
```
GET /admin/cache
```

**响应**: HTML 页面

#### 清空所有缓存
```
POST /admin/cache/clear
```

**响应示例**:
```json
{
  "success": true,
  "message": "缓存清空成功"
}
```

#### 清空指定模式缓存
```
POST /admin/cache/clear-pattern
```

**请求参数**:
```json
{
  "pattern": "articles:*"
}
```

**响应示例**:
```json
{
  "success": true,
  "message": "指定模式缓存清空成功"
}
```

#### 获取缓存统计
```
GET /admin/cache/stats
```

**响应示例**:
```json
{
  "success": true,
  "data": {
    "total_keys": 100,
    "memory_usage": "10MB",
    "hit_rate": 0.85
  }
}
```

## 错误处理

### 标准错误响应格式

```json
{
  "success": false,
  "message": "错误描述",
  "error_code": "ERROR_CODE"
}
```

### 常见HTTP状态码

- `200`: 成功
- `400`: 请求参数错误
- `401`: 未授权（需要登录）
- `403`: 禁止访问
- `404`: 资源不存在
- `500`: 服务器内部错误

## 数据模型

### 文章 (Article)

```json
{
  "id": 1,
  "title": "文章标题",
  "content": "文章内容（Markdown格式）",
  "summary": "文章摘要",
  "author": "作者名称",
  "author_id": 1,
  "created_at": "2025-10-14 10:00:00",
  "updated_at": "2025-10-14 10:00:00",
  "sort_id": 1,
  "tags": ["标签1", "标签2"],
  "view_count": 100,
  "is_published": 1,
  "is_deleted": 0
}
```

### 配置 (Config)

```json
{
  "config_key": "site_name",
  "config_value": "网站名称",
  "config_type": "string",
  "description": "网站名称配置",
  "category": "basic",
  "created_at": "2025-10-14 10:00:00",
  "updated_at": "2025-10-14 10:00:00"
}
```

### 广告 (Advertisement)

```json
{
  "id": 1,
  "name": "广告名称",
  "position": "homepage-middle",
  "is_active": 1,
  "created_at": "2025-10-14 10:00:00",
  "updated_at": "2025-10-14 10:00:00"
}
```

## 使用示例

### JavaScript 示例

```javascript
// 获取文章列表
async function getArticles(page = 1, limit = 10) {
  const response = await fetch(`/api/articles?page=${page}&limit=${limit}`);
  const data = await response.json();
  return data;
}

// 获取文章详情
async function getArticleDetail(articleId) {
  const response = await fetch(`/api/article/${articleId}`);
  const data = await response.json();
  return data;
}

// 搜索文章
async function searchArticles(keyword, page = 1) {
  const response = await fetch(`/search?q=${encodeURIComponent(keyword)}&page=${page}`);
  return response.text(); // 返回HTML页面
}

// 管理员登录
async function adminLogin(username, password, captcha) {
  const formData = new FormData();
  formData.append('username', username);
  formData.append('password', password);
  formData.append('captcha', captcha);
  
  const response = await fetch('/dm', {
    method: 'POST',
    body: formData
  });
  
  return response.json();
}
```

### Python 示例

```python
import requests
import json

class Tg2emallAPI:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_articles(self, page=1, limit=10):
        """获取文章列表"""
        response = self.session.get(f"{self.base_url}/api/articles", 
                                  params={'page': page, 'limit': limit})
        return response.json()
    
    def get_article_detail(self, article_id):
        """获取文章详情"""
        response = self.session.get(f"{self.base_url}/api/article/{article_id}")
        return response.json()
    
    def search_articles(self, keyword, page=1):
        """搜索文章"""
        response = self.session.get(f"{self.base_url}/search", 
                                  params={'q': keyword, 'page': page})
        return response.text
    
    def admin_login(self, username, password, captcha):
        """管理员登录"""
        data = {
            'username': username,
            'password': password,
            'captcha': captcha
        }
        response = self.session.post(f"{self.base_url}/dm", data=data)
        return response.json()

# 使用示例
api = Tg2emallAPI("http://your-domain.com")

# 获取文章列表
articles = api.get_articles(page=1, limit=10)
print(articles)

# 获取文章详情
article = api.get_article_detail(1)
print(article)
```

## 注意事项

1. **请求频率限制**: API 有简单的频率限制，避免过于频繁的请求
2. **分页限制**: 单次请求最多返回 100 条记录
3. **缓存机制**: 部分接口有缓存，数据可能不是实时的
4. **管理员权限**: 管理员接口需要先登录获取 Session
5. **错误处理**: 请妥善处理各种错误情况
6. **字符编码**: 所有接口都使用 UTF-8 编码

## 更新日志

- **v1.0.0** (2025-10-14): 初始版本，包含基础的文章、搜索、管理功能
- 支持文章 CRUD 操作
- 支持搜索和分类功能
- 支持管理员后台管理
- 支持广告管理
- 支持缓存管理

---

如有问题或建议，请联系开发团队。
