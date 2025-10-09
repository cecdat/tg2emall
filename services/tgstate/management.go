package main

import (
	"bytes"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"time"

	"csz.net/tgstate/conf"
	"csz.net/tgstate/utils"
	_ "github.com/go-sql-driver/mysql"
)

// ServiceStatus 服务状态
type ServiceStatus struct {
	Status    string `json:"status"`     // running, stopped, error
	PID       int    `json:"pid"`        // 进程ID
	Port      int    `json:"port"`       // 端口
	Message   string `json:"message"`    // 状态信息
	StartTime string `json:"start_time"` // 启动时间
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

// ManagementAPI 管理API
type ManagementAPI struct {
	status     string
	pid        int
	startTime  time.Time
	config     ServiceConfig
	httpServer *http.Server
	publicURL  string // 公网访问地址
}

// NewManagementAPI 创建管理API
func NewManagementAPI() *ManagementAPI {
	api := &ManagementAPI{
		status: "running",
		pid:    os.Getpid(),
		config: ServiceConfig{
			Token:  os.Getenv("TOKEN"),
			Target: os.Getenv("TARGET"),
			Pass:   os.Getenv("PASS"),
			Mode:   os.Getenv("MODE"),
			URL:    os.Getenv("URL"),
		},
	}

	// 从数据库加载配置
	api.loadConfigFromDB()
	
	// 同步管理API的配置到全局配置
	conf.BotToken = api.config.Token
	conf.ChannelName = api.config.Target
	conf.Pass = api.config.Pass
	conf.Mode = api.config.Mode
	conf.BaseUrl = api.config.URL

	return api
}

// loadConfigFromDB 从数据库加载配置
func (api *ManagementAPI) loadConfigFromDB() {
	// 数据库连接配置
	dbConfig := map[string]string{
		"host":     os.Getenv("MYSQL_HOST"),
		"port":     os.Getenv("MYSQL_PORT"),
		"user":     os.Getenv("MYSQL_USER"),
		"password": os.Getenv("MYSQL_PASSWORD"),
		"database": os.Getenv("MYSQL_DATABASE"),
	}
	
	// 设置默认值
	if dbConfig["host"] == "" {
		dbConfig["host"] = "mysql"
	}
	if dbConfig["port"] == "" {
		dbConfig["port"] = "3306"
	}
	if dbConfig["user"] == "" {
		dbConfig["user"] = "tg2emall"
	}
	if dbConfig["password"] == "" {
		dbConfig["password"] = "tg2emall"
	}
	if dbConfig["database"] == "" {
		dbConfig["database"] = "tg2em"
	}
	
	// 连接数据库
	dsn := fmt.Sprintf("%s:%s@tcp(%s:%s)/%s?charset=utf8mb4&parseTime=True&loc=Local",
		dbConfig["user"], dbConfig["password"], dbConfig["host"], dbConfig["port"], dbConfig["database"])
	
	db, err := sql.Open("mysql", dsn)
	if err != nil {
		fmt.Printf("⚠️ 数据库连接失败，使用环境变量配置: %v\n", err)
		return
	}
	defer db.Close()
	
	// 查询tgState相关配置
	rows, err := db.Query(`
		SELECT config_key, config_value 
		FROM system_config 
		WHERE config_key IN ('tgstate_token', 'tgstate_target', 'tgstate_pass', 'tgstate_mode', 'tgstate_url', 'tgstate_port', 'public_url')
	`)
	if err != nil {
		fmt.Printf("⚠️ 查询配置失败，使用环境变量配置: %v\n", err)
		return
	}
	defer rows.Close()
	
	// 读取配置
	for rows.Next() {
		var key, value string
		if err := rows.Scan(&key, &value); err != nil {
			continue
		}
		
		switch key {
		case "tgstate_token":
			api.config.Token = value
		case "tgstate_target":
			api.config.Target = value
		case "tgstate_pass":
			api.config.Pass = value
		case "tgstate_mode":
			api.config.Mode = value
		case "tgstate_url":
			api.config.URL = value
		case "tgstate_port":
			api.config.Port = value
		case "public_url":
			// 存储公网地址，用于图片URL生成
			api.publicURL = value
		}
	}
	
	fmt.Printf("✅ 从数据库加载tgState配置: Token=%s***, Target=%s, URL=%s\n", 
		api.config.Token[:4], api.config.Target, api.config.URL)
}

// StartManagementAPI 启动管理API
func (api *ManagementAPI) StartManagementAPI() {
	mux := http.NewServeMux()

	// 管理接口路由（需要密码验证）
	mux.HandleFunc("/api/management/status", api.handleStatus)
	mux.HandleFunc("/api/management/start", api.handleStart)
	mux.HandleFunc("/api/management/stop", api.handleStop)
	mux.HandleFunc("/api/management/restart", api.handleRestart)
	mux.HandleFunc("/api/management/config", api.handleConfig)
	mux.HandleFunc("/api/management/info", api.handleInfo)
	mux.HandleFunc("/api/test/upload", api.handleTestUpload)

	// 提供实际的图片上传API
	mux.HandleFunc("/api", api.handleImageUpload)

	// 密码验证页面
	mux.HandleFunc("/pwd", api.handlePasswordCheck)

	// 图片上传测试页面（公开访问，需要密码）
	mux.HandleFunc("/upload", api.handleUploadPage)

	// 管理页面（需要密码验证）
	mux.HandleFunc("/admin", api.handleAdminPage)

	// 根路径 - 根据是否有密码决定显示内容
	mux.HandleFunc("/", api.handleRoot)

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

// handleInfo 处理服务信息查询
func (api *ManagementAPI) handleInfo(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	info := map[string]interface{}{
		"mode":             api.config.Mode,
		"target":           api.config.Target,
		"token_configured": len(api.config.Token) > 0,
		"pass":             api.config.Pass,
		"url":              api.config.URL,
		"port":             8088,
		"pid":              api.pid,
		"status":           api.status,
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"data":    info,
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
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .container {
            max-width: 800px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 15px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.1); 
            padding: 30px;
        }
        
        h1 {
            color: #333; 
            text-align: center; 
            margin-bottom: 30px; 
            font-size: 2.5rem; 
            background: linear-gradient(45deg, #667eea, #764ba2); 
            -webkit-background-clip: text; 
            -webkit-text-fill-color: transparent; 
            background-clip: text;
        }
        
        .status { 
            padding: 15px; 
            margin: 15px 0; 
            border-radius: 10px;
            font-weight: 500; 
            text-align: center;
            font-size: 1.1rem;
            border: 2px solid;
        }
        
        .running { 
            background: linear-gradient(135deg, #d4edda, #c3e6cb); 
            color: #155724; 
            border-color: #155724;
        }
        
        .stopped { 
            background: linear-gradient(135deg, #f8d7da, #f1b0b7); 
            color: #721c24; 
            border-color: #721c24;
        }
        
        .controls {
            text-align: center;
            margin: 30px 0;
        }
        
        button { 
            padding: 12px 25px; 
            margin: 8px; 
            cursor: pointer; 
            border: none; 
            border-radius: 25px; 
            font-weight: 600; 
            font-size: 14px; 
            transition: all 0.3s ease;
            min-width: 120px;
        }
        
        button:hover { 
            transform: translateY(-2px); 
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        
        .start-btn { background: linear-gradient(135deg, #28a745, #20c997); color: white; }
        .stop-btn { background: linear-gradient(135deg, #dc3545, #c82333); color: white; }
        .restart-btn { background: linear-gradient(135deg, #ffc107, #e0a800); color: #212529; }
        .refresh-btn { background: linear-gradient(135deg, #17a2b8, #138496); color: white; }
        
        .upload-section { 
            margin-top: 40px; 
            padding: 25px; 
            border: 2px dashed #dee2e6; 
            border-radius: 15px; 
            text-align: center;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
        }
        
        .upload-section h3 {
            color: #495057; 
            margin-bottom: 20px; 
            font-size: 1.4rem;
        }
        
        input[type="file"] { 
            margin: 15px 0; 
            padding: 10px; 
            border-radius: 8px; 
            border: 2px solid #dee2e6; 
            background: white;
            font-size: 14px;
        }
        
        .upload-btn { background: linear-gradient(135deg, #007bff, #0056b3); color: white; }
        
        .result { 
            margin-top: 15px; 
            padding: 15px; 
            border-radius: 10px; 
            font-family: 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.4;
            white-space: pre-wrap;
            border-left: 4px solid;
        }
        
        .success { 
            background: linear-gradient(135deg, #d4edda, #c3e6cb); 
            color: #155724; 
            border-left-color: #28a745;
        }
        
        .error { 
            background: linear-gradient(135deg, #f8d7da, #f1b0b7); 
            color: #721c24; 
            border-left-color: #dc3545;
        }
        
        .info { 
            background: linear-gradient(135deg, #d1ecf1, #bee5eb); 
            color: #0c5460; 
            border-left-color: #17a2b8;
        }
        
        .loading {
            animation: pulse 1.5s infinite;
        }
        
        .config-section {
            margin: 20px 0;
            padding: 20px;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 10px;
            border: 1px solid #dee2e6;
        }
        
        .config-section h4 {
            margin-bottom: 15px;
            color: #495057;
            font-size: 1.2rem;
        }
        
        .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 10px;
        }
        
        .config-item {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            background: white;
            border-radius: 6px;
            border-left: 3px solid #007bff;
        }
        
        .config-label {
            font-weight: 600;
            color: #495057;
            margin-right: 10px;
            min-width: 80px;
        }
        
        .config-value {
            color: #6c757d;
            font-family: 'Courier New', monospace;
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            border: 1px solid #e9ecef;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        @keyframes slideIn {
            from { transform: translateX(100%); }
            to { transform: translateX(0); }
        }
    </style>
</head>
<body>
        <div class="container">
        <h1>🖼️ tgState 图片上传服务</h1>
        
        <div id="status" class="status">加载中...</div>
        
        <!-- 服务配置信息 -->
        <div id="config-info" class="config-section" style="display:none;">
            <h4>🔧 服务配置</h4>
            <div class="config-grid">
                <div class="config-item">
                    <span class="config-label">运行模式:</span>
                    <span id="config-mode" class="config-value">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">频道目标:</span>
                    <span id="config-target" class="config-value">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">Token配置:</span>
                    <span id="config-token" class="config-value">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">访问密码:</span>
                    <span id="config-pass" class="config-value">-</span>
                </div>
                <div class="config-item">
                    <span class="config-label">基础URL:</span>
                    <span id="config-url" class="config-value">-</span>
                </div>
            </div>
        </div>
        
        <div class="controls">
            <button class="start-btn" onclick="startService()">启动服务</button>
            <button class="stop-btn" onclick="stopService()">停止服务</button>
            <button class="restart-btn" onclick="restartService()">重启服务</button>
            <button class="refresh-btn" onclick="getStatus()">刷新状态</button>
        </div>
        
        <div class="upload-section">
            <h3>📸 图片上传测试</h3>
            <form id="testUploadForm">
                <input type="file" id="testImage" name="image" accept="image/*" required>
                <br>
                <button class="upload-btn" type="button" onclick="testUpload()">测试上传</button>
            </form>
            <div id="uploadResult" class="result" style="display:none;"></div>
        </div>
    </div>
    
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
        
        function getConfigInfo() {
            fetch('/api/management/info')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateConfigDisplay(data.data);
                    }
                });
        }
        
        function updateConfigDisplay(config) {
            // 显示/隐藏配置区域
            const configSection = document.getElementById('config-info');
            configSection.style.display = 'block';
            
            // 更新运行模式
            const modeText = config.mode === 'p' ? '图片模式 (支持API上传)' : 
                            config.mode === 'm' ? '管理模式 (关闭网页上传)' : 
                            '未知模式';
            document.getElementById('config-mode').textContent = modeText;
            
            // 更新频道目标
            document.getElementById('config-target').textContent = 
                config.target ? config.target : '未配置';
            
            // 更新Token配置（只显示是否配置，不显示内容）
            document.getElementById('config-token').textContent = 
                config.token_configured ? '已配置' : '未配置';
            
            // 更新访问密码
            document.getElementById('config-pass').textContent = 
                config.pass && config.pass !== 'none' ? '已设置' : '未设置';
            
            // 更新基础URL
            document.getElementById('config-url').textContent = 
                config.url ? config.url : '未配置';
        }
        
        function startService() {
            fetch('/api/management/start', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    showNotification(data.message, 'success');
                    getStatus();
                });
        }
        
        function stopService() {
            fetch('/api/management/stop', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    showNotification(data.message, 'success');
                    getStatus();
                });
        }
        
        function restartService() {
            fetch('/api/management/restart', {method: 'POST'})
                .then(response => response.json())
                .then(data => {
                    showNotification(data.message, 'success');
                    getStatus();
                });
        }
        
        function testUpload() {
            const fileInput = document.getElementById('testImage');
            const resultDiv = document.getElementById('uploadResult');
            
            if (!fileInput.files[0]) {
                showUploadResult('请选择一个图片文件', 'error');
                return;
            }
            
            const formData = new FormData();
            formData.append('image', fileInput.files[0]);
            
            resultDiv.style.display = 'block';
            showUploadResult('上传中...', 'info');
            
            fetch('/api/test/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    let message = '✅ ' + data.message;
                    if (data.imgUrl) {
                        message += '\\n图片地址: ' + data.imgUrl;
                        message += '\\n路径: ' + (data.imgPath || '');
                    }
                    showUploadResult(message, 'success');
                } else {
                    showUploadResult('❌ 上传失败: ' + (data.error || '未知错误'), 'error');
                }
            })
            .catch(error => {
                showUploadResult('❌ 上传错误: ' + error.message, 'error');
            });
        }
        
        function showUploadResult(message, type) {
            const resultDiv = document.getElementById('uploadResult');
            resultDiv.textContent = message.replace(/\\n/g, '\n');
            resultDiv.className = 'result ' + type;
            resultDiv.style.display = 'block';
        }
        
        // 美观的通知函数
        function showNotification(message, type = 'info') {
            // 创建通知容器（如果不存在）
            if (!document.getElementById('notification-container')) {
                const notificationContainer = document.createElement('div');
                notificationContainer.id = 'notification-container';
                notificationContainer.style.cssText = 
                    'position: fixed; ' +
                    'top: 20px; ' +
                    'right: 20px; ' +
                    'z-index: 10000; ' +
                    'max-width: 400px;';
                document.body.appendChild(notificationContainer);
            }
            
            const notification = document.createElement('div');
            let bgColor = '';
            if (type === 'success') {
                bgColor = 'linear-gradient(135deg, #28a745, #20c997)';
            } else if (type === 'error') {
                bgColor = 'linear-gradient(135deg, #dc3545, #c82333)';
            } else {
                bgColor = 'linear-gradient(135deg, #17a2b8, #138496)';
            }
            
            notification.style.cssText = 
                'background: ' + bgColor + '; ' +
                'color: white; ' +
                'padding: 15px 20px; ' +
                'margin-bottom: 10px; ' +
                'border-radius: 10px; ' +
                'box-shadow: 0 5px 15px rgba(0,0,0,0.2); ' +
                'font-weight: 500; ' +
                'cursor: pointer; ' +
                'transform: translateX(100%); ' +
                'transition: transform 0.3s ease; ' +
                'animation: slideIn 0.3s ease forwards;';
            
            let icon = type === 'success' ? '✅' : type === 'error' ? '❌' : 'ℹ️';
            notification.innerHTML = 
                '<div style="display: flex; align-items: center; justify-content: space-between;">' +
                    '<span>' + icon + '</span>' +
                    '<span style="flex: 1; margin: 0 10px;">' + message + '</span>' +
                    '<span onclick="this.parentElement.parentElement.remove()" style="cursor: pointer; font-weight: bold;">×</span>' +
                '</div>';
            
            document.getElementById('notification-container').appendChild(notification);
            
            // 3秒后自动消失
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.style.transform = 'translateX(100%)';
                    setTimeout(() => notification.remove(), 300);
                }
            }, 3000);
        }
        
        // 页面加载时获取状态和配置信息
        getStatus();
        getConfigInfo();
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

// handleTestUpload 处理图片上传测试
func (api *ManagementAPI) handleTestUpload(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

	if r.Method != "POST" {
		w.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   "只支持POST方法",
		})
		return
	}

	// 解析multipart form
	err := r.ParseMultipartForm(10 << 20) // 10MB
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("解析表单失败: %v", err),
		})
		return
	}

	// 获取上传的文件
	file, header, err := r.FormFile("image")
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("获取文件失败: %v", err),
		})
		return
	}
	defer file.Close()

	// 创建临时文件
	tempDir := "/tmp"
	os.MkdirAll(tempDir, 0755)
	tempFile := filepath.Join(tempDir, "test_upload_"+header.Filename)

	destFile, err := os.Create(tempFile)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("创建临时文件失败: %v", err),
		})
		return
	}
	defer destFile.Close()
	defer os.Remove(tempFile) // 清理临时文件

	// 复制文件
	_, err = io.Copy(destFile, file)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("保存文件失败: %v", err),
		})
		return
	}

	// 直接调用tgState的上传API
	success, imgPath, imgUrl := api.uploadImageToTGState(tempFile, header.Filename)
	if success {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": true,
			"message": "图片上传成功",
			"imgUrl":  imgUrl,
			"imgPath": imgPath,
		})
	} else {
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error":   imgPath, // 错误时imgPath存储错误信息
		})
	}
}

// uploadImageToTGState 直接上传图片到tgState
func (api *ManagementAPI) uploadImageToTGState(tempFile, filename string) (success bool, imgPath, imgUrl string) {
	// 检查tgState配置
	if conf.BotToken == "" || conf.ChannelName == "" {
		return false, "tgState未配置Bot Token或频道名称", ""
	}

	// 读取文件
	file, err := os.Open(tempFile)
	if err != nil {
		return false, fmt.Sprintf("打开文件失败: %v", err), ""
	}
	defer file.Close()

	// 上传到Telegram
	finalPath := utils.UpDocument(utils.TgFileData(filename, file))
	if finalPath == "" {
		return false, "上传到Telegram失败", ""
	}

	imgPath = conf.FileRoute + finalPath
	
	// 优先使用数据库中的公网地址
	baseUrl := strings.TrimSuffix(api.publicURL, "/")
	if baseUrl == "" {
		// 其次使用配置中的URL
		baseUrl = strings.TrimSuffix(conf.BaseUrl, "/")
		if baseUrl == "" {
			// 最后使用环境变量
			baseUrl = os.Getenv("PUBLIC_URL")
			if baseUrl == "" {
				baseUrl = "http://your-domain.com:8088"
			}
		}
	}
	imgUrl = baseUrl + imgPath

	return true, imgPath, imgUrl
}

// testUploadToTGState 测试上传到tgState服务
func (api *ManagementAPI) testUploadToTGState(tempFile, filename string) (map[string]interface{}, error) {
	// 检查tgState服务状态
	statusClient := &http.Client{Timeout: 5 * time.Second}
	statusResp, err := statusClient.Get("http://localhost:8088/api/management/status")
	if err != nil || statusResp.StatusCode != http.StatusOK {
		return map[string]interface{}{
			"success": false,
			"error":   "tgState管理接口不可访问，请确保服务已启动",
		}, nil
	}
	statusResp.Body.Close()

	// 准备上传到tgState服务
	client := &http.Client{Timeout: 30 * time.Second}

	// 打开文件
	file, err := os.Open(tempFile)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("打开文件失败: %v", err),
		}, nil
	}
	defer file.Close()

	// 创建multipart form
	body := &bytes.Buffer{}
	writer := multipart.NewWriter(body)
	part, err := writer.CreateFormFile("image", filename)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("创建表单字段失败: %v", err),
		}, nil
	}

	_, err = io.Copy(part, file)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("写入文件内容失败: %v", err),
		}, nil
	}

	err = writer.Close()
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("关闭multipart writer失败: %v", err),
		}, nil
	}

	// 准备请求
	url := "http://localhost:8088/api"
	req, err := http.NewRequest("POST", url, body)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("创建请求失败: %v", err),
		}, nil
	}

	req.Header.Set("Content-Type", writer.FormDataContentType())

	// 如果有密码，设置cookie
	if api.config.Pass != "" && api.config.Pass != "none" {
		req.AddCookie(&http.Cookie{
			Name:  "p",
			Value: api.config.Pass,
		})
	}

	// 发送请求
	resp, err := client.Do(req)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("发送请求失败: %v", err),
		}, nil
	}
	defer resp.Body.Close()

	// 读取响应
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("读取响应失败: %v", err),
		}, nil
	}

	// 检查响应状态码
	if resp.StatusCode != http.StatusOK {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("HTTP错误 %d: %s", resp.StatusCode, string(respBody)),
		}, nil
	}

	// 检查响应内容类型
	contentType := resp.Header.Get("Content-Type")
	if !strings.Contains(contentType, "application/json") {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("期望JSON响应，实际收到: %s, 内容: %s", contentType, string(respBody)),
		}, nil
	}

	// 解析响应
	var result map[string]interface{}
	err = json.Unmarshal(respBody, &result)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error":   fmt.Sprintf("解析响应失败: %v, 响应内容: %s", err, string(respBody)),
		}, nil
	}

	success := false
	if code, ok := result["code"]; ok {
		if codeInt, ok := code.(float64); ok && codeInt == 1 {
			success = true
		}
	}

	if !success {
		return map[string]interface{}{
			"success":          false,
			"error":            "上传失败，tgState返回错误",
			"tgstate_response": result,
		}, nil
	}

	return map[string]interface{}{
		"success":          true,
		"message":          "图片上传成功",
		"tgstate_response": result,
	}, nil
}

// handleImageUpload 处理实际的图片上传请求
func (api *ManagementAPI) handleImageUpload(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Access-Control-Allow-Origin", "*")

	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// 检查是否有Token配置
	if api.config.Token == "" || api.config.Target == "" {
		response := map[string]interface{}{
			"code":    0,
			"message": "tgstate_not_configured",
			"imgUrl":  "",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}

	// 获取上传的文件
	file, header, err := r.FormFile("image")
	if err != nil {
		response := map[string]interface{}{
			"code":    0,
			"message": "Unable to get file",
			"imgUrl":  "",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}
	defer file.Close()

	// 检查文件大小
	if r.ContentLength > 20*1024*1024 {
		response := map[string]interface{}{
			"code":    0,
			"message": "File size exceeds 20MB limit",
			"imgUrl":  "",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}

	// 检查文件类型
	allowedExts := []string{".jpg", ".jpeg", ".png"}
	filename := header.Filename
	ext := strings.ToLower(filename)
	valid := false
	for _, allowedExt := range allowedExts {
		if strings.HasSuffix(ext, allowedExt) {
			valid = true
			break
		}
	}

	if !valid {
		response := map[string]interface{}{
			"code":    0,
			"message": "Invalid file type. Only .jpg, .jpeg, and .png are allowed.",
			"imgUrl":  "",
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
		return
	}

	// 直接上传到Telegram频道（按tgState方式）
	img := conf.FileRoute + utils.UpDocument(utils.TgFileData(header.Filename, file))
	if img != conf.FileRoute && img != "" {
		// 上传成功，生成访问URL
		// 优先使用数据库中的公网地址
		baseUrl := strings.TrimSuffix(api.publicURL, "/")
		if baseUrl == "" {
			// 其次使用配置中的URL
			baseUrl = strings.TrimSuffix(conf.BaseUrl, "/")
			if baseUrl == "" {
				// 最后使用环境变量
				baseUrl = os.Getenv("PUBLIC_URL")
				if baseUrl == "" {
					baseUrl = "http://your-domain.com:8088"
				}
			}
		}
		imgUrl := baseUrl + img

		response := map[string]interface{}{
			"code":    1,
			"message": img,
			"imgUrl":  imgUrl,
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	} else {
		// 上传失败
		response := map[string]interface{}{
			"code":    0,
			"message": "Telegram上传失败，请检查Bot Token和频道配置",
			"imgUrl":  "",
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(response)
	}
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

// handleRoot 处理根路径
func (api *ManagementAPI) handleRoot(w http.ResponseWriter, r *http.Request) {
	// 检查是否设置了密码
	if api.config.Pass == "" || api.config.Pass == "none" {
		// 没有密码，直接显示图片上传测试页面
		api.handleUploadPage(w, r)
		return
	}

	// 有密码，检查是否已经验证
	cookie, err := r.Cookie("tgstate_auth")
	if err != nil || cookie.Value != api.config.Pass {
		// 未验证，显示密码输入页面
		api.handlePasswordCheck(w, r)
		return
	}

	// 已验证，显示图片上传测试页面
	api.handleUploadPage(w, r)
}

// handlePasswordCheck 处理密码验证
func (api *ManagementAPI) handlePasswordCheck(w http.ResponseWriter, r *http.Request) {
	if r.Method == "POST" {
		// 处理密码验证
		password := r.FormValue("password")
		if password == api.config.Pass {
			// 设置认证cookie
			cookie := &http.Cookie{
				Name:     "tgstate_auth",
				Value:    api.config.Pass,
				Path:     "/",
				MaxAge:   3600 * 24, // 24小时
				HttpOnly: true,
			}
			http.SetCookie(w, cookie)

			// 重定向到上传页面
			http.Redirect(w, r, "/upload", http.StatusSeeOther)
			return
		}

		// 密码错误，显示错误页面
		html := `<!DOCTYPE html>
<html>
<head>
    <title>tgState 图片上传服务 - 密码验证</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .error { color: #dc3545; margin-bottom: 20px; padding: 10px; background: #f8d7da; border-radius: 5px; }
        input[type="password"] { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        h1 { text-align: center; color: #333; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 密码验证</h1>
        <div class="error">密码错误，请重新输入</div>
        <form method="POST">
            <input type="password" name="password" placeholder="请输入访问密码" required>
            <button type="submit">验证</button>
        </form>
    </div>
</body>
</html>`
		w.Header().Set("Content-Type", "text/html; charset=utf-8")
		w.Write([]byte(html))
		return
	}

	// 显示密码输入页面
	html := `<!DOCTYPE html>
<html>
<head>
    <title>tgState 图片上传服务 - 密码验证</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        input[type="password"] { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 5px; }
        button { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #0056b3; }
        h1 { text-align: center; color: #333; }
        .info { text-align: center; color: #666; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔐 密码验证</h1>
        <div class="info">请输入访问密码以使用图片上传服务</div>
        <form method="POST">
            <input type="password" name="password" placeholder="请输入访问密码" required>
            <button type="submit">验证</button>
        </form>
    </div>
</body>
</html>`
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write([]byte(html))
}

// handleUploadPage 处理图片上传测试页面
func (api *ManagementAPI) handleUploadPage(w http.ResponseWriter, r *http.Request) {
	// 检查密码验证（如果有设置密码）
	if api.config.Pass != "" && api.config.Pass != "none" {
		cookie, err := r.Cookie("tgstate_auth")
		if err != nil || cookie.Value != api.config.Pass {
			http.Redirect(w, r, "/pwd", http.StatusSeeOther)
			return
		}
	}

	html := `<!DOCTYPE html>
<html>
<head>
    <title>tgState 图片上传服务</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; margin-bottom: 30px; }
        .upload-area { border: 2px dashed #ddd; padding: 40px; text-align: center; border-radius: 10px; margin: 20px 0; }
        .upload-area:hover { border-color: #007bff; background: #f8f9fa; }
        input[type="file"] { margin: 20px 0; }
        button { padding: 12px 24px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer; margin: 10px; }
        button:hover { background: #0056b3; }
        button:disabled { background: #6c757d; cursor: not-allowed; }
        .result { margin: 20px 0; padding: 15px; border-radius: 5px; }
        .success { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .loading { text-align: center; color: #666; }
        .admin-link { text-align: center; margin-top: 20px; }
        .admin-link a { color: #007bff; text-decoration: none; }
        .admin-link a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🖼️ 图片上传测试</h1>
        
        <div class="upload-area">
            <h3>选择图片文件</h3>
            <input type="file" id="imageFile" accept="image/*" multiple>
            <br>
            <button onclick="uploadImages()" id="uploadBtn">上传图片</button>
        </div>
        
        <div id="result" class="result" style="display:none;"></div>
        
        <div class="admin-link">
            <a href="/admin">🔧 服务管理</a>
        </div>
    </div>
    
    <script>
        function uploadImages() {
            const fileInput = document.getElementById('imageFile');
            const files = fileInput.files;
            const resultDiv = document.getElementById('result');
            const uploadBtn = document.getElementById('uploadBtn');
            
            if (files.length === 0) {
                showResult('请选择要上传的图片文件', 'error');
                return;
            }
            
            uploadBtn.disabled = true;
            uploadBtn.textContent = '上传中...';
            resultDiv.style.display = 'none';
            
            let uploadPromises = [];
            
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const formData = new FormData();
                formData.append('image', file);
                
                uploadPromises.push(
                    fetch('/api', {
                        method: 'POST',
                        body: formData
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.code === 1) {
                            return { success: true, file: file.name, url: data.imgUrl };
                        } else {
                            return { success: false, file: file.name, error: data.message };
                        }
                    })
                    .catch(error => {
                        return { success: false, file: file.name, error: error.message };
                    })
                );
            }
            
            Promise.all(uploadPromises).then(results => {
                uploadBtn.disabled = false;
                uploadBtn.textContent = '上传图片';
                
                let successCount = 0;
                let errorCount = 0;
                let resultHtml = '';
                
                results.forEach(result => {
                    if (result.success) {
                        successCount++;
                        resultHtml += '<div style="margin: 10px 0;">' +
                            '<strong>' + result.file + ':</strong> ' +
                            '<a href="' + result.url + '" target="_blank">' + result.url + '</a>' +
                        '</div>';
                    } else {
                        errorCount++;
                        resultHtml += '<div style="margin: 10px 0; color: #dc3545;">' +
                            '<strong>' + result.file + ':</strong> ' + result.error +
                        '</div>';
                    }
                });
                
                if (successCount > 0) {
                    showResult('成功上传 ' + successCount + ' 个文件' + (errorCount > 0 ? '，失败 ' + errorCount + ' 个' : '') + '<br>' + resultHtml, 'success');
                } else {
                    showResult('所有文件上传失败<br>' + resultHtml, 'error');
                }
            });
        }
        
        function showResult(message, type) {
            const resultDiv = document.getElementById('result');
            resultDiv.innerHTML = message;
            resultDiv.className = 'result ' + type;
            resultDiv.style.display = 'block';
        }
    </script>
</body>
</html>`
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write([]byte(html))
}

// handleAdminPage 处理管理页面
func (api *ManagementAPI) handleAdminPage(w http.ResponseWriter, r *http.Request) {
	// 检查密码验证（如果有设置密码）
	if api.config.Pass != "" && api.config.Pass != "none" {
		cookie, err := r.Cookie("tgstate_auth")
		if err != nil || cookie.Value != api.config.Pass {
			http.Redirect(w, r, "/pwd", http.StatusSeeOther)
			return
		}
	}

	// 显示原来的管理页面
	api.handleStatic(w, r)
}
