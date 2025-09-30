package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"syscall"
	"time"
)

// ServiceStatus 服务状态
type ServiceStatus struct {
	Status    string `json:"status"`    // running, stopped, error
	PID       int    `json:"pid"`       // 进程ID
	Port      int    `json:"port"`      // 端口
	Message   string `json:"message"`   // 状态信息
	StartTime string `json:"start_time"` // 启动时间
}

// ServiceConfig 服务配置
type ServiceConfig struct {
	Token  string `json:"token"`
	Target string `json:"target"`
	Pass   string `json:"pass"`
	Mode   string `json:"mode"`
	URL    string `json:"url"`
}

// ManagementAPI 管理API
type ManagementAPI struct {
	status     string
	pid        int
	startTime  time.Time
	config     ServiceConfig
	httpServer *http.Server
}

// NewManagementAPI 创建管理API
func NewManagementAPI() *ManagementAPI {
	return &ManagementAPI{
		status: "stopped",
		pid:    0,
		config: ServiceConfig{
			Token:  os.Getenv("TOKEN"),
			Target: os.Getenv("TARGET"),
			Pass:   os.Getenv("PASS"),
			Mode:   os.Getenv("MODE"),
			URL:    os.Getenv("URL"),
		},
	}
}

// StartManagementAPI 启动管理API
func (api *ManagementAPI) StartManagementAPI() {
	mux := http.NewServeMux()
	
	// 管理接口路由
	mux.HandleFunc("/api/management/status", api.handleStatus)
	mux.HandleFunc("/api/management/start", api.handleStart)
	mux.HandleFunc("/api/management/stop", api.handleStop)
	mux.HandleFunc("/api/management/restart", api.handleRestart)
	mux.HandleFunc("/api/management/config", api.handleConfig)
	
	// 静态文件服务
	mux.HandleFunc("/", api.handleStatic)
	
	api.httpServer = &http.Server{
		Addr:    ":8088",
		Handler: mux,
	}
	
	fmt.Println("🔧 tgState 管理API启动在端口 8088")
	
	// 启动HTTP服务器
	go func() {
		if err := api.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			fmt.Printf("❌ 管理API启动失败: %v\n", err)
		}
	}()
	
	// 等待信号
	api.waitForSignal()
}

// handleStatus 处理状态查询
func (api *ManagementAPI) handleStatus(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	
	status := ServiceStatus{
		Status:    api.status,
		PID:       api.pid,
		Port:      8088,
		Message:   fmt.Sprintf("tgState服务状态: %s", api.status),
		StartTime: api.startTime.Format("2006-01-02 15:04:05"),
	}
	
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    status,
	})
}

// handleStart 处理启动请求
func (api *ManagementAPI) handleStart(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	
	if api.status == "running" {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "服务已经在运行中",
		})
		return
	}
	
	// 启动tgState服务
	cmd := exec.Command("./tgstate")
	cmd.Dir = "/app"
	
	if err := cmd.Start(); err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": fmt.Sprintf("启动失败: %v", err),
		})
		return
	}
	
	api.status = "running"
	api.pid = cmd.Process.Pid
	api.startTime = time.Now()
	
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "服务启动成功",
		"pid":     api.pid,
	})
}

// handleStop 处理停止请求
func (api *ManagementAPI) handleStop(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	
	if api.status == "stopped" {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "服务已经停止",
		})
		return
	}
	
	if api.pid > 0 {
		process, err := os.FindProcess(api.pid)
		if err == nil {
			process.Signal(syscall.SIGTERM)
		}
	}
	
	api.status = "stopped"
	api.pid = 0
	
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "服务停止成功",
	})
}

// handleRestart 处理重启请求
func (api *ManagementAPI) handleRestart(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	
	// 先停止
	if api.status == "running" && api.pid > 0 {
		process, err := os.FindProcess(api.pid)
		if err == nil {
			process.Signal(syscall.SIGTERM)
		}
		time.Sleep(2 * time.Second)
	}
	
	// 再启动
	cmd := exec.Command("./tgstate")
	cmd.Dir = "/app"
	
	if err := cmd.Start(); err != nil {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"message": fmt.Sprintf("重启失败: %v", err),
		})
		return
	}
	
	api.status = "running"
	api.pid = cmd.Process.Pid
	api.startTime = time.Now()
	
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "服务重启成功",
		"pid":     api.pid,
	})
}

// handleConfig 处理配置请求
func (api *ManagementAPI) handleConfig(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	
	if r.Method == "GET" {
		// 获取配置
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"data":    api.config,
		})
	} else if r.Method == "POST" {
		// 更新配置
		var newConfig ServiceConfig
		if err := json.NewDecoder(r.Body).Decode(&newConfig); err != nil {
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": false,
				"message": "配置格式错误",
			})
			return
		}
		
		api.config = newConfig
		
		// 更新环境变量
		os.Setenv("TOKEN", newConfig.Token)
		os.Setenv("TARGET", newConfig.Target)
		os.Setenv("PASS", newConfig.Pass)
		os.Setenv("MODE", newConfig.Mode)
		os.Setenv("URL", newConfig.URL)
		
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "配置更新成功",
		})
	}
}

// handleStatic 处理静态文件
func (api *ManagementAPI) handleStatic(w http.ResponseWriter, r *http.Request) {
	// 简单的状态页面
	if r.URL.Path == "/" {
		html := `
<!DOCTYPE html>
<html>
<head>
    <title>tgState 管理界面</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .running { background-color: #d4edda; color: #155724; }
        .stopped { background-color: #f8d7da; color: #721c24; }
        button { padding: 10px 20px; margin: 5px; cursor: pointer; }
    </style>
</head>
<body>
    <h1>🖼️ tgState 图片上传服务</h1>
    <div id="status" class="status">加载中...</div>
    <button onclick="startService()">启动服务</button>
    <button onclick="stopService()">停止服务</button>
    <button onclick="restartService()">重启服务</button>
    <button onclick="getStatus()">刷新状态</button>
    
    <script>
        function getStatus() {
            fetch('/api/management/status')
                .then(response => response.json())
                .then(data => {
                    const statusDiv = document.getElementById('status');
                    if (data.success) {
                        const status = data.data.status;
                        statusDiv.className = 'status ' + status;
                        statusDiv.innerHTML = "状态: " + status + " | PID: " + data.data.pid + " | 启动时间: " + data.data.start_time;
                    }
                });
        }
        
        function startService() {
            fetch('/api/management/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    getStatus();
                });
        }
        
        function stopService() {
            fetch('/api/management/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    getStatus();
                });
        }
        
        function restartService() {
            fetch('/api/management/restart', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    getStatus();
                });
        }
        
        // 页面加载时获取状态
        getStatus();
        // 每5秒刷新状态
        setInterval(getStatus, 5000);
    </script>
</body>
</html>`
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(html))
		return
	}
	
	// 其他请求返回404
	w.WriteHeader(http.StatusNotFound)
	w.Write([]byte("Not Found"))
}

// waitForSignal 等待信号
func (api *ManagementAPI) waitForSignal() {
	c := make(chan os.Signal, 1)
	signal.Notify(c, os.Interrupt, syscall.SIGTERM)
	
	<-c
	fmt.Println("🛑 收到停止信号，正在关闭管理API...")
	
	// 停止tgState服务
	if api.status == "running" && api.pid > 0 {
		process, err := os.FindProcess(api.pid)
		if err == nil {
			process.Signal(syscall.SIGTERM)
		}
	}
	
	// 关闭HTTP服务器
	if api.httpServer != nil {
		api.httpServer.Close()
	}
	
	fmt.Println("✅ 管理API已关闭")
}
