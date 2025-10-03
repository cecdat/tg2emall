package main

import (
	"bytes"
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
	mux.HandleFunc("/api/test/upload", api.handleTestUpload)
	
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
        .upload-section { margin-top: 20px; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
        input[type="file"] { margin: 10px 0; }
        .result { margin-top: 10px; padding: 10px; border-radius: 5px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        .info { background-color: #d1ecf1; color: #0c5460; }
    </style>
</head>
<body>
    <h1>🖼️ tgState 图片上传服务</h1>
    <div id="status" class="status">加载中...</div>
    <button onclick="startService()">启动服务</button>
    <button onclick="stopService()">停止服务</button>
    <button onclick="restartService()">重启服务</button>
    <button onclick="getStatus()">刷新状态</button>
    
    <div class="upload-section">
        <h3>📸 图片上传测试</h3>
        <form id="testUploadForm">
            <input type="file" id="testImage" name="image" accept="image/*" required>
            <button type="button" onclick="testUpload()">测试上传</button>
        </form>
        <div id="uploadResult" class="result" style="display:none;"></div>
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
                    showUploadResult('✅ ' + data.message, 'success');
                    if (data.result && data.result.tgstate_response) {
                        const resp = data.result.tgstate_response;
                        if (resp.url) {
                            showUploadResult(
                                '✅ ' + data.message + '\\n图片链接: ' + resp.url + 
                                '\\n文件大小: ' + (resp.size || '未知'),
                                'success'
                            );
                        }
                    }
                } else {
                    showUploadResult('❌ 上传失败: ' + data.error, 'error');
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
			"error": "只支持POST方法",
		})
		return
	}

	// 解析multipart form
	err := r.ParseMultipartForm(10 << 20) // 10MB
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("解析表单失败: %v", err),
		})
		return
	}

	// 获取上传的文件
	file, header, err := r.FormFile("image")
	if err != nil {
		w.WriteHeader(http.StatusBadRequest)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("获取文件失败: %v", err),
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
			"error": fmt.Sprintf("创建临时文件失败: %v", err),
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
			"error": fmt.Sprintf("保存文件失败: %v", err),
		})
		return
	}

	// 测试上传到tgState服务
	result, err := api.testUploadToTGState(tempFile, header.Filename)
	if err != nil {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("上传失败: %v", err),
		})
		return
	} else if !result["success"].(bool) {
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"success": false,
			"error": result["error"].(string),
		})
		return
	}

	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"message": "图片上传测试成功",
		"result": result,
	})
}

// testUploadToTGState 测试上传到tgState服务
func (api *ManagementAPI) testUploadToTGState(tempFile, filename string) (map[string]interface{}, error) {
	// 检查tgState服务状态
	client := &http.Client{Timeout: 5 * time.Second}
	statusResp, err := client.Get("http://localhost:8088/api/management/status")
	if err != nil || statusResp.StatusCode != http.StatusOK {
		return map[string]interface{}{
			"success": false,
			"error": "tgState管理接口不可访问，请确保服务已启动",
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
			"error": fmt.Sprintf("打开文件失败: %v", err),
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
			"error": fmt.Sprintf("创建表单字段失败: %v", err),
		}, nil
	}

	_, err = io.Copy(part, file)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("写入文件内容失败: %v", err),
		}, nil
	}

	err = writer.Close()
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("关闭multipart writer失败: %v", err),
		}, nil
	}

	// 准备请求
	url := "http://localhost:8088/api"
	req, err := http.NewRequest("POST", url, body)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("创建请求失败: %v", err),
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
			"error": fmt.Sprintf("发送请求失败: %v", err),
		}, nil
	}
	defer resp.Body.Close()

	// 读取响应
	respBody, err := io.ReadAll(resp.Body)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("读取响应失败: %v", err),
		}, nil
	}

	// 检查响应状态码
	if resp.StatusCode != http.StatusOK {
		return map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("HTTP错误 %d: %s", resp.StatusCode, string(respBody)),
		}, nil
	}

	// 检查响应内容类型
	contentType := resp.Header.Get("Content-Type")
	if !strings.Contains(contentType, "application/json") {
		return map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("期望JSON响应，实际收到: %s, 内容: %s", contentType, string(respBody)),
		}, nil
	}

	// 解析响应
	var result map[string]interface{}
	err = json.Unmarshal(respBody, &result)
	if err != nil {
		return map[string]interface{}{
			"success": false,
			"error": fmt.Sprintf("解析响应失败: %v, 响应内容: %s", err, string(respBody)),
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
			"success": false,
			"error": "上传失败，tgState返回错误",
			"tgstate_response": result,
		}, nil
	}

	return map[string]interface{}{
		"success": true,
		"message": "图片上传成功",
		"tgstate_response": result,
	}, nil
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
