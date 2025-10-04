package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"strconv"
	"sync"
	"syscall"
	"time"

	"github.com/gorilla/mux"
)

// ManagementService 管理服务结构
type ManagementService struct {
	uploadService *exec.Cmd
	isRunning     bool
	mutex         sync.RWMutex
	config        ServiceConfig
	pid           int
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

// ServiceStatus 服务状态
type ServiceStatus struct {
	Status    string `json:"status"`
	PID       int    `json:"pid"`
	Uptime    string `json:"uptime"`
	StartTime string `json:"start_time"`
}

// APIResponse API响应结构
type APIResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message"`
	Data    interface{} `json:"data,omitempty"`
}

var (
	managementService *ManagementService
	startTime         time.Time
)

func main() {
	log.Println("🚀 tgState管理服务启动中...")
	
	// 初始化管理服务
	managementService = &ManagementService{
		config: ServiceConfig{
			Token:  os.Getenv("TOKEN"),
			Target: os.Getenv("TARGET"),
			Pass:   os.Getenv("PASS"),
			Mode:   os.Getenv("MODE"),
			URL:    os.Getenv("URL"),
			Port:   os.Getenv("PORT"),
		},
		pid: os.Getpid(),
	}
	
	startTime = time.Now()
	
	// 设置路由
	router := mux.NewRouter()
	
	// 管理API路由
	router.HandleFunc("/api/management/status", handleStatus).Methods("GET")
	router.HandleFunc("/api/management/start", handleStart).Methods("POST")
	router.HandleFunc("/api/management/stop", handleStop).Methods("POST")
	router.HandleFunc("/api/management/restart", handleRestart).Methods("POST")
	router.HandleFunc("/api/management/config", handleConfig).Methods("GET", "POST")
	router.HandleFunc("/api/management/info", handleInfo).Methods("GET")
	
	// 图片上传API路由（代理到上传服务）
	router.HandleFunc("/api", handleImageUpload).Methods("POST")
	
	// 静态文件服务（管理页面）
	router.PathPrefix("/").Handler(http.FileServer(http.Dir("./web/")))
	
	// 启动HTTP服务器
	server := &http.Server{
		Addr:    ":8088",
		Handler: router,
	}
	
	// 优雅关闭
	go func() {
		c := make(chan os.Signal, 1)
		signal.Notify(c, os.Interrupt, syscall.SIGTERM)
		<-c
		
		log.Println("🛑 管理服务正在关闭...")
		managementService.StopUploadService()
		server.Shutdown(nil)
	}()
	
	log.Println("✅ tgState管理服务已启动，监听端口: 8088")
	log.Printf("📊 管理服务PID: %d", managementService.pid)
	
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("❌ 管理服务启动失败: %v", err)
	}
}

// handleStatus 处理状态查询
func handleStatus(w http.ResponseWriter, r *http.Request) {
	managementService.mutex.RLock()
	defer managementService.mutex.RUnlock()
	
	status := "stopped"
	pid := 0
	uptime := "0s"
	
	if managementService.isRunning && managementService.uploadService != nil {
		status = "running"
		pid = managementService.uploadService.Process.Pid
		uptime = time.Since(startTime).String()
	}
	
	response := APIResponse{
		Success: true,
		Data: ServiceStatus{
			Status:    status,
			PID:       pid,
			Uptime:    uptime,
			StartTime: startTime.Format("2006-01-02 15:04:05"),
		},
	}
	
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleStart 处理启动请求
func handleStart(w http.ResponseWriter, r *http.Request) {
	managementService.mutex.Lock()
	defer managementService.mutex.Unlock()
	
	if managementService.isRunning {
		response := APIResponse{
			Success: false,
			Message: "上传服务已在运行中",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}
	
	// 启动上传服务
	if err := managementService.StartUploadService(); err != nil {
		response := APIResponse{
			Success: false,
			Message: fmt.Sprintf("启动上传服务失败: %v", err),
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}
	
	response := APIResponse{
		Success: true,
		Message: "上传服务启动成功",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleStop 处理停止请求
func handleStop(w http.ResponseWriter, r *http.Request) {
	managementService.mutex.Lock()
	defer managementService.mutex.Unlock()
	
	if !managementService.isRunning {
		response := APIResponse{
			Success: false,
			Message: "上传服务未运行",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}
	
	// 停止上传服务
	managementService.StopUploadService()
	
	response := APIResponse{
		Success: true,
		Message: "上传服务停止成功",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleRestart 处理重启请求
func handleRestart(w http.ResponseWriter, r *http.Request) {
	managementService.mutex.Lock()
	defer managementService.mutex.Unlock()
	
	// 先停止
	if managementService.isRunning {
		managementService.StopUploadService()
		time.Sleep(2 * time.Second) // 等待进程完全停止
	}
	
	// 再启动
	if err := managementService.StartUploadService(); err != nil {
		response := APIResponse{
			Success: false,
			Message: fmt.Sprintf("重启上传服务失败: %v", err),
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}
	
	response := APIResponse{
		Success: true,
		Message: "上传服务重启成功",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleConfig 处理配置请求
func handleConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		// 返回当前配置
		response := APIResponse{
			Success: true,
			Data:    managementService.config,
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	} else if r.Method == "POST" {
		// 更新配置
		var newConfig ServiceConfig
		if err := json.NewDecoder(r.Body).Decode(&newConfig); err != nil {
			response := APIResponse{
				Success: false,
				Message: "配置格式错误",
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(response)
			return
		}
		
		managementService.mutex.Lock()
		managementService.config = newConfig
		managementService.mutex.Unlock()
		
		// 如果上传服务正在运行，重启以应用新配置
		if managementService.isRunning {
			go func() {
				time.Sleep(1 * time.Second)
				managementService.mutex.Lock()
				defer managementService.mutex.Unlock()
				
				if managementService.isRunning {
					managementService.StopUploadService()
					time.Sleep(2 * time.Second)
					managementService.StartUploadService()
				}
			}()
		}
		
		response := APIResponse{
			Success: true,
			Message: "配置更新成功",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}
}

// handleInfo 处理信息请求
func handleInfo(w http.ResponseWriter, r *http.Request) {
	info := map[string]interface{}{
		"service_name":    "tgState Management Service",
		"version":         "2.0.0",
		"management_pid":  managementService.pid,
		"upload_port":     "8089",
		"management_port": "8088",
		"architecture":    "dual-service",
	}
	
	response := APIResponse{
		Success: true,
		Data:    info,
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// handleImageUpload 处理图片上传（代理到上传服务）
func handleImageUpload(w http.ResponseWriter, r *http.Request) {
	managementService.mutex.RLock()
	defer managementService.mutex.RUnlock()
	
	if !managementService.isRunning {
		response := APIResponse{
			Success: false,
			Message: "上传服务未运行",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}
	
	// 代理请求到上传服务
	// 这里需要实现HTTP代理逻辑
	// 暂时返回错误，后续实现
	response := APIResponse{
		Success: false,
		Message: "图片上传代理功能开发中",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// StartUploadService 启动上传服务
func (ms *ManagementService) StartUploadService() error {
	log.Println("🚀 启动上传服务...")
	
	// 构建上传服务启动命令
	cmd := exec.Command("./upload-service", 
		"--token", ms.config.Token,
		"--target", ms.config.Target,
		"--pass", ms.config.Pass,
		"--mode", ms.config.Mode,
		"--url", ms.config.URL,
		"--port", "8089",
	)
	
	// 设置环境变量
	cmd.Env = append(os.Environ(),
		"TOKEN="+ms.config.Token,
		"TARGET="+ms.config.Target,
		"PASS="+ms.config.Pass,
		"MODE="+ms.config.Mode,
		"URL="+ms.config.URL,
		"PORT=8089",
	)
	
	// 启动服务
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("启动上传服务失败: %v", err)
	}
	
	ms.uploadService = cmd
	ms.isRunning = true
	
	log.Printf("✅ 上传服务启动成功，PID: %d", cmd.Process.Pid)
	return nil
}

// StopUploadService 停止上传服务
func (ms *ManagementService) StopUploadService() {
	if ms.uploadService != nil && ms.isRunning {
		log.Println("🛑 停止上传服务...")
		
		// 发送SIGTERM信号
		if err := ms.uploadService.Process.Signal(syscall.SIGTERM); err != nil {
			log.Printf("⚠️ 发送SIGTERM失败: %v", err)
		}
		
		// 等待进程结束
		done := make(chan error, 1)
		go func() {
			done <- ms.uploadService.Wait()
		}()
		
		select {
		case <-done:
			log.Println("✅ 上传服务已停止")
		case <-time.After(10 * time.Second):
			log.Println("⚠️ 强制终止上传服务")
			ms.uploadService.Process.Kill()
		}
		
		ms.uploadService = nil
		ms.isRunning = false
	}
}
