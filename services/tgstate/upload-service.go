package main

import (
	"bytes"
	"encoding/json"
	"flag"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"csz.net/tgstate/conf"
	"csz.net/tgstate/utils"
)

// UploadService 上传服务结构
type UploadService struct {
	config ServiceConfig
	port   string
}

// ServiceConfig 服务配置
type ServiceConfig struct {
	Token  string `json:"token"`
	Target string `json:"target"`
	Pass   string `json:"pass"`
	Mode   string `json:"mode"`
	URL    string `json:"url"`
	Port   string `json:"port"`
}

// UploadResponse 上传响应
type UploadResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	ImgUrl  string `json:"imgUrl"`
}

func main() {
	// 解析命令行参数
	var config ServiceConfig
	flag.StringVar(&config.Token, "token", "", "Telegram Bot Token")
	flag.StringVar(&config.Target, "target", "", "Target Channel")
	flag.StringVar(&config.Pass, "pass", "none", "Access Password")
	flag.StringVar(&config.Mode, "mode", "p", "Service Mode")
	flag.StringVar(&config.URL, "url", "http://localhost:6001", "Base URL")
	flag.StringVar(&config.Port, "port", "6002", "Service Port")
	flag.Parse()
	
	// 从环境变量获取配置（优先级更高）
	if token := os.Getenv("TOKEN"); token != "" {
		config.Token = token
	}
	if target := os.Getenv("TARGET"); target != "" {
		config.Target = target
	}
	if pass := os.Getenv("PASS"); pass != "" {
		config.Pass = pass
	}
	if mode := os.Getenv("MODE"); mode != "" {
		config.Mode = mode
	}
	if url := os.Getenv("URL"); url != "" {
		config.URL = url
	}
	if port := os.Getenv("PORT"); port != "" {
		config.Port = port
	}
	
	// 验证必需配置
	if config.Token == "" || config.Target == "" {
		log.Fatal("❌ 缺少必需配置: TOKEN 和 TARGET")
	}
	
	// 初始化全局配置
	conf.BotToken = config.Token
	conf.ChannelName = config.Target
	conf.Pass = config.Pass
	conf.Mode = config.Mode
	conf.BaseUrl = config.URL
	
	log.Printf("🚀 tgState上传服务启动中...")
	log.Printf("📊 配置信息:")
	log.Printf("   Token: %s", maskToken(config.Token))
	log.Printf("   Target: %s", config.Target)
	log.Printf("   Mode: %s", config.Mode)
	log.Printf("   Base URL: %s", config.URL)
	log.Printf("   Port: %s", config.Port)
	
	// 创建上传服务实例
	service := &UploadService{
		config: config,
		port:   config.Port,
	}
	
	// 设置路由
	mux := http.NewServeMux()
	mux.HandleFunc("/api", service.handleImageUpload)
	mux.HandleFunc("/health", service.handleHealth)
	mux.HandleFunc("/status", service.handleStatus)
	
	// 创建HTTP服务器
	server := &http.Server{
		Addr:    ":" + config.Port,
		Handler: mux,
	}
	
	// 优雅关闭
	go func() {
		c := make(chan os.Signal, 1)
		signal.Notify(c, os.Interrupt, syscall.SIGTERM)
		<-c
		
		log.Println("🛑 上传服务正在关闭...")
		server.Shutdown(nil)
	}()
	
	log.Printf("✅ tgState上传服务已启动，监听端口: %s", config.Port)
	log.Printf("📊 上传服务PID: %d", os.Getpid())
	
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("❌ 上传服务启动失败: %v", err)
	}
}

// handleImageUpload 处理图片上传
func (us *UploadService) handleImageUpload(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	
	if r.Method == "OPTIONS" {
		w.WriteHeader(http.StatusOK)
		return
	}
	
	if r.Method != http.MethodPost {
		us.sendErrorResponse(w, "Method not allowed", 405)
		return
	}
	
	// 检查密码验证
	if us.config.Pass != "none" && us.config.Pass != "" {
		cookie, err := r.Cookie("p")
		if err != nil || cookie.Value != us.config.Pass {
			us.sendErrorResponse(w, "Unauthorized", 401)
			return
		}
	}
	
	// 获取上传的文件
	file, header, err := r.FormFile("image")
	if err != nil {
		us.sendErrorResponse(w, "Unable to get file", 400)
		return
	}
	defer file.Close()
	
	// 检查文件大小
	if r.ContentLength > 20*1024*1024 {
		us.sendErrorResponse(w, "File size exceeds 20MB limit", 400)
		return
	}
	
	// 检查文件类型
	allowedExts := []string{".jpg", ".jpeg", ".png", ".gif", ".webp"}
	filename := header.Filename
	ext := strings.ToLower(filepath.Ext(filename))
	valid := false
	for _, allowedExt := range allowedExts {
		if ext == allowedExt {
			valid = true
			break
		}
	}
	
	if !valid {
		us.sendErrorResponse(w, "Invalid file type. Only .jpg, .jpeg, .png, .gif, .webp are allowed.", 400)
		return
	}
	
	// 上传到Telegram
	log.Printf("📤 开始上传图片: %s", filename)
	
	// 读取文件内容
	fileData, err := io.ReadAll(file)
	if err != nil {
		us.sendErrorResponse(w, "Failed to read file", 500)
		return
	}
	
	// 上传到Telegram频道
	imgPath := utils.UpDocument(utils.TgFileData(filename, bytes.NewReader(fileData)))
	if imgPath == "" || imgPath == conf.FileRoute {
		us.sendErrorResponse(w, "Failed to upload to Telegram", 500)
		return
	}
	
	// 构建完整的图片URL
	baseUrl := strings.TrimSuffix(us.config.URL, "/")
	imgUrl := baseUrl + imgPath
	
	log.Printf("✅ 图片上传成功: %s", imgUrl)
	
	// 返回成功响应
	response := UploadResponse{
		Code:    1,
		Message: imgPath,
		ImgUrl:  imgUrl,
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleHealth 健康检查
func (us *UploadService) handleHealth(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":    "healthy",
		"service":   "tgstate-upload",
		"timestamp": time.Now().Unix(),
		"pid":       os.Getpid(),
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleStatus 状态检查
func (us *UploadService) handleStatus(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":     "running",
		"service":    "tgstate-upload",
		"pid":        os.Getpid(),
		"port":       us.port,
		"config":     us.config,
		"start_time": time.Now().Format("2006-01-02 15:04:05"),
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// sendErrorResponse 发送错误响应
func (us *UploadService) sendErrorResponse(w http.ResponseWriter, message string, code int) {
	response := UploadResponse{
		Code:    0,
		Message: message,
		ImgUrl:  "",
	}
	
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(response)
}

// maskToken 掩码Token
func maskToken(token string) string {
	if len(token) < 8 {
		return "***"
	}
	return token[:4] + "***" + token[len(token)-4:]
}
