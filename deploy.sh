#!/bin/bash

# tg2emall 部署脚本
# 用于快速部署 Telegram 到自定义前端一体化解决方案

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 Docker 和 Docker Compose
check_dependencies() {
    log_info "检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建数据目录..."
    
    mkdir -p data/{mysql,npm,letsencrypt,telegram-sessions,logs,upload}
    
    log_success "数据目录创建完成"
}

# 检查配置文件
check_config() {
    log_info "检查配置文件..."
    
    if [ ! -f "env.example" ]; then
        log_error "env.example 文件不存在"
        exit 1
    fi
    
    if [ ! -f "services/tg2em/config.yaml" ]; then
        log_error "tg2em 配置文件不存在"
        exit 1
    fi
    
    if [ ! -f ".env" ]; then
        log_warning ".env 文件不存在，从 env.example 复制"
        cp env.example .env
        log_warning "请编辑 .env 文件配置必要的参数"
    fi
    
    # 询问前端端口配置
    if ! grep -q "FRONTEND_PORT" .env; then
        echo ""
        read -p "请输入前端服务访问端口 (默认: 5000): " frontend_port
        frontend_port=${frontend_port:-5000}
        echo "FRONTEND_PORT=${frontend_port}" >> .env
        log_info "前端端口配置为: ${frontend_port}"
    else
        frontend_port=$(grep "FRONTEND_PORT" .env | cut -d'=' -f2)
        log_info "前端端口已配置为: ${frontend_port}"
    fi
    
    log_success "配置文件检查完成"
}

# 检查数据库数据
check_database() {
    log_info "检查数据库状态..."
    
    if [ -d "data/mysql" ] && [ "$(ls -A data/mysql 2>/dev/null)" ]; then
        log_warning "检测到现有数据库数据"
        echo ""
        echo "数据库目录: ./data/mysql"
        echo "数据大小: $(du -sh data/mysql 2>/dev/null | cut -f1)"
        echo ""
        read -p "是否保留现有数据库数据？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            log_info "将保留现有数据库数据"
            PRESERVE_DB=true
            # 检查是否需要初始化数据库结构
            check_database_structure
        else
            log_warning "将删除现有数据库数据"
            PRESERVE_DB=false
            INIT_DB=true
        fi
    else
        log_info "未检测到现有数据库数据，将创建新数据库"
        PRESERVE_DB=false
        INIT_DB=true
    fi
}

# 检查数据库结构
check_database_structure() {
    log_info "检查数据库结构..."
    
    # 启动 MySQL 容器进行检查
    docker-compose up -d mysql
    
    # 等待 MySQL 启动
    log_info "等待 MySQL 启动..."
    sleep 30
    
    # 检查数据库表是否存在
    local table_check=$(docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "SHOW TABLES LIKE 'messages';" 2>/dev/null | grep -c "messages")
    
    if [ "$table_check" -eq 0 ]; then
        log_warning "检测到数据库表不存在，需要初始化数据库结构"
        read -p "是否初始化数据库结构？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            INIT_DB=true
        else
            INIT_DB=false
        fi
    else
        log_success "数据库结构完整，无需初始化"
        INIT_DB=false
    fi
}

# 构建镜像
build_images() {
    log_info "构建 Docker 镜像..."
    
    # 构建前端镜像
    log_info "构建前端镜像..."
    docker-compose build frontend
    
    # 构建 tg2em 镜像
    log_info "构建 tg2em 镜像..."
    docker-compose build tg2em-scrape
    
    # 构建 tgState 镜像
    log_info "构建 tgState 镜像..."
    docker-compose build tgstate
    
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 如果选择不保留数据库，先清理数据
    if [ "$PRESERVE_DB" = false ]; then
        log_info "清理数据库数据..."
        rm -rf data/mysql/*
    fi
    
    # 启动基础服务
    docker-compose up -d mysql frontend tgstate tg2em-scrape nginx-proxy-manager
    
    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 30
    
    # 如果需要初始化数据库结构
    if [ "$INIT_DB" = true ]; then
        log_info "初始化数据库结构..."
        init_database_structure
    fi
    
    # 启动其他服务
    docker-compose up -d
    
    log_success "服务启动完成"
}

# 初始化数据库结构
init_database_structure() {
    log_info "执行数据库初始化脚本..."
    
    # 执行初始化脚本
    if docker exec tg2em-mysql mysql -u root -ptg2emall -e "source /docker-entrypoint-initdb.d/init.sql" 2>/dev/null; then
        log_success "数据库结构初始化完成"
    else
        log_error "数据库结构初始化失败"
        return 1
    fi
    
    # 验证表是否创建成功
    local table_count=$(docker exec tg2em-mysql mysql -u tg2emall -ptg2emall tg2em -e "SHOW TABLES;" 2>/dev null | grep -c "Tables_in_tg2em")
    
    if [ "$table_count" -ge 4 ]; then
        log_success "数据库表创建成功，共 $table_count 个表"
    else
        log_warning "数据库表数量异常，请检查初始化脚本"
    fi
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    docker-compose ps
    
    echo ""
    log_info "访问地址："
    # 获取前端端口
    local frontend_port=5000
    if [ -f ".env" ] && grep -q "FRONTEND_PORT" .env; then
        frontend_port=$(grep "FRONTEND_PORT" .env | cut -d'=' -f2)
    fi
    
    echo "  - Nginx Proxy Manager: http://localhost:81"
    echo "  - 前端展示系统: http://localhost:${frontend_port}"
    echo "  - 后台管理系统: http://localhost:${frontend_port}/admin"
    echo "  - 图片上传服务: http://localhost:8088"
    echo "  - 采集服务管理: http://localhost:5001"
    
    echo ""
    log_info "查看日志："
    echo "  - 所有服务: docker-compose logs -f"
    echo "  - 前端服务: docker-compose logs -f frontend"
    echo "  - 采集服务: docker-compose logs -f tg2em-scrape"
    echo "  - 图片服务: docker-compose logs -f tgstate"
}

# 首次配置提示
first_time_setup() {
    log_warning "首次配置提示："
    echo ""
    echo "1. 配置 Nginx Proxy Manager:"
    echo "   - 访问 http://localhost:81"
    echo "   - 默认账号: admin@example.com / changeme"
    echo "   - 配置域名和 SSL 证书"
    echo ""
    echo "2. 配置 Telegram 验证:"
    # 获取前端端口
    local frontend_port=5000
    if [ -f ".env" ] && grep -q "FRONTEND_PORT" .env; then
        frontend_port=$(grep "FRONTEND_PORT" .env | cut -d'=' -f2)
    fi
    
    echo "   - 访问管理后台: http://localhost:${frontend_port}/admin"
    echo "   - 用户名: admin, 密码: admin, 验证码: 2025"
    echo "   - 在配置管理页面配置 Telegram API 参数"
    echo "   - 在服务管理页面启动采集服务"
    echo ""
    echo "3. 检查配置文件:"
    echo "   - 编辑 .env 文件配置 tgState 参数"
    echo "   - 访问 http://localhost:5000 查看前端展示"
    echo ""
    echo "4. 重启服务应用配置:"
    echo "   - docker-compose restart"
}

# 主函数
main() {
    echo "=========================================="
    echo "    tg2emall 部署脚本"
    echo "=========================================="
    echo ""
    
    check_dependencies
    create_directories
    check_config
    check_database
    
    # 询问是否构建镜像
    read -p "是否构建 Docker 镜像？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_images
    fi
    
    # 询问是否启动服务
    read -p "是否启动服务？(y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        start_services
        show_status
        first_time_setup
    fi
    
    log_success "部署完成！"
}

# 脚本参数处理
case "${1:-}" in
    "start")
        start_services
        show_status
        ;;
    "stop")
        log_info "停止服务..."
        docker-compose down
        log_success "服务已停止"
        ;;
    "restart")
        log_info "重启服务..."
        docker-compose restart
        log_success "服务已重启"
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        show_status
        ;;
    "build")
        build_images
        ;;
    "clean")
        log_warning "清理所有数据..."
        read -p "确认删除所有数据？(y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            rm -rf data/
            log_success "数据清理完成"
        fi
        ;;
    "backup")
        log_info "备份数据库..."
        if [ -d "data/mysql" ]; then
            timestamp=$(date +"%Y%m%d_%H%M%S")
            backup_name="tg2em_backup_${timestamp}.tar.gz"
            tar -czf "$backup_name" data/mysql
            log_success "数据库备份完成: $backup_name"
        else
            log_error "数据库目录不存在"
        fi
        ;;
    "restore")
        log_info "恢复数据库..."
        read -p "请输入备份文件路径: " backup_file
        if [ -f "$backup_file" ]; then
            docker-compose down
            rm -rf data/mysql
            tar -xzf "$backup_file"
            docker-compose up -d
            log_success "数据库恢复完成"
        else
            log_error "备份文件不存在: $backup_file"
        fi
        ;;
    "init-db")
        log_info "初始化数据库结构..."
        docker-compose up -d mysql
        sleep 30
        init_database_structure
        ;;
    "check-db")
        log_info "检查数据库状态..."
        docker-compose up -d mysql
        sleep 30
        check_database_structure
        ;;
    *)
        main
        ;;
esac
