# 快速修复：采集模块导入错误

## 🔴 错误信息
```
ERROR - ❌ 采集模块导入失败: cannot import name 'get_config_from_db' from 'scrape' (/app/scrape.py)
```

## ⚡ 快速修复步骤

### 方法1：完整重新构建（推荐）

```bash
cd ~/tg2emall

# 1. 拉取最新代码
git pull origin main

# 2. 停止采集服务
docker-compose stop tg2em-scrape

# 3. 删除旧的容器和镜像
docker-compose rm -f tg2em-scrape
docker rmi tg2emall_tg2em-scrape 2>/dev/null || true

# 4. 重新构建（不使用缓存）
docker-compose build --no-cache tg2em-scrape

# 5. 启动服务
docker-compose up -d tg2em-scrape

# 6. 查看日志
docker logs -f tg2em-scrape
```

### 方法2：直接修复容器内的文件（临时方案）

如果重新构建太慢，可以直接在容器内修复：

```bash
# 1. 进入容器
docker exec -it tg2em-scrape bash

# 2. 检查函数是否存在
grep -n "async def get_config_from_db" /app/scrape.py

# 3. 如果没有输出，说明函数缺失，添加函数
cat >> /tmp/fix.py << 'EOF'

async def get_config_from_db(config_key):
    """从数据库获取配置（通用函数）"""
    try:
        async with MySQLConnectionManager() as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            await cursor.execute("SELECT config_value FROM system_config WHERE config_key = %s", (config_key,))
            result = await cursor.fetchone()
            return result['config_value'] if result else None
    except Exception as e:
        logging.error(f"获取配置失败 {config_key}: {e}")
        return None

EOF

# 4. 在 get_tgstate_config 函数前插入新函数
# 找到 get_tgstate_config 的行号
LINE=$(grep -n "async def get_tgstate_config" /app/scrape.py | cut -d: -f1)

# 在该行之前插入新函数
if [ ! -z "$LINE" ]; then
    sed -i "${LINE}i\\
async def get_config_from_db(config_key):\\
    \"\"\"从数据库获取配置（通用函数）\"\"\"\\
    try:\\
        async with MySQLConnectionManager() as conn:\\
            cursor = await conn.cursor(aiomysql.DictCursor)\\
            await cursor.execute(\"SELECT config_value FROM system_config WHERE config_key = %s\", (config_key,))\\
            result = await cursor.fetchone()\\
            return result['config_value'] if result else None\\
    except Exception as e:\\
        logging.error(f\"获取配置失败 {config_key}: {e}\")\\
        return None\\
\\
" /app/scrape.py
fi

# 5. 验证修改
grep -A 5 "async def get_config_from_db" /app/scrape.py

# 6. 退出容器
exit

# 7. 重启采集服务
docker-compose restart tg2em-scrape

# 8. 查看日志
docker logs -f tg2em-scrape
```

### 方法3：使用Python直接修复（最简单）

```bash
# 1. 创建修复脚本
cat > /tmp/fix_scrape.py << 'PYTHON_EOF'
#!/usr/bin/env python3
import re

# 读取文件
with open('/app/scrape.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 检查函数是否已存在
if 'async def get_config_from_db' in content:
    print("✅ 函数已存在，无需修复")
    exit(0)

# 定义要插入的函数
new_function = '''async def get_config_from_db(config_key):
    """从数据库获取配置（通用函数）"""
    try:
        async with MySQLConnectionManager() as conn:
            cursor = await conn.cursor(aiomysql.DictCursor)
            await cursor.execute("SELECT config_value FROM system_config WHERE config_key = %s", (config_key,))
            result = await cursor.fetchone()
            return result['config_value'] if result else None
    except Exception as e:
        logging.error(f"获取配置失败 {config_key}: {e}")
        return None

'''

# 找到 get_tgstate_config 函数的位置并在其前面插入
pattern = r'(async def get_tgstate_config\(config_key\):)'
replacement = new_function + r'\1'
new_content = re.sub(pattern, replacement, content, count=1)

# 写回文件
with open('/app/scrape.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ 修复完成")
PYTHON_EOF

# 2. 复制到容器并执行
docker cp /tmp/fix_scrape.py tg2em-scrape:/tmp/fix_scrape.py
docker exec tg2em-scrape python3 /tmp/fix_scrape.py

# 3. 验证修复
docker exec tg2em-scrape grep -A 5 "async def get_config_from_db" /app/scrape.py

# 4. 重启服务
docker-compose restart tg2em-scrape

# 5. 查看日志
docker logs -f tg2em-scrape
```

---

## 🔍 诊断步骤

### 检查代码是否更新

```bash
# 1. 检查本地代码版本
cd ~/tg2emall
git log --oneline -3

# 应该看到：
# 3b2ffef fix:add-missing-get_config_from_db-function
# adf75e6 docs:add-scraper-troubleshooting-guide
# 426daa6 fix:show-scraper-service-logs-and-add-config-validation

# 2. 检查容器内的代码
docker exec tg2em-scrape grep -c "async def get_config_from_db" /app/scrape.py

# 如果输出是 0，说明容器内代码未更新
# 如果输出是 1 或更多，说明函数存在
```

### 检查镜像构建时间

```bash
# 查看镜像创建时间
docker images | grep tg2emall_tg2em-scrape

# 查看容器启动时间
docker ps | grep tg2em-scrape
```

---

## ✅ 验证修复成功

修复后，日志应该显示：

```bash
✅ 采集模块导入成功  # ← 这行应该是 ✅ 不是 ❌
🚀 tg2em采集服务启动中...
📊 采集服务PID: 10
📡 服务端口: 5002
```

---

## 🚨 如果仍然失败

### 检查Git状态

```bash
cd ~/tg2emall
git status
git log --oneline -1

# 如果不是最新提交，执行：
git fetch origin
git reset --hard origin/main
```

### 完全清理并重新部署

```bash
cd ~/tg2emall

# 1. 停止所有服务
docker-compose down

# 2. 删除所有相关镜像
docker images | grep tg2emall | awk '{print $3}' | xargs docker rmi -f

# 3. 清理构建缓存
docker builder prune -af

# 4. 重新构建
docker-compose build

# 5. 启动服务
docker-compose up -d

# 6. 查看日志
docker logs -f tg2em-scrape
```

---

## 📝 常见问题

### Q: 为什么拉取代码后还是报错？

**A**: Docker镜像使用了构建缓存，需要重新构建镜像。

### Q: 重新构建要多久？

**A**: 通常 2-5 分钟，取决于网络速度。

### Q: 可以只修复这一个文件吗？

**A**: 可以，使用方法2或方法3直接在容器内修复。

---

## 📞 需要帮助？

如果以上方法都不行，请提供：

1. Git日志：
   ```bash
   git log --oneline -5
   ```

2. 容器内文件检查：
   ```bash
   docker exec tg2em-scrape head -n 250 /app/scrape.py | tail -n 30
   ```

3. 完整错误日志：
   ```bash
   docker logs tg2em-scrape 2>&1 | tail -n 50
   ```

---

**快速命令（复制粘贴执行）**：

```bash
cd ~/tg2emall && \
git pull origin main && \
docker-compose stop tg2em-scrape && \
docker-compose rm -f tg2em-scrape && \
docker-compose build --no-cache tg2em-scrape && \
docker-compose up -d tg2em-scrape && \
echo "等待5秒..." && sleep 5 && \
docker logs -f tg2em-scrape
```

