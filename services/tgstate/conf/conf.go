package conf

import "os"

var BotToken string
var ChannelName string
var Pass string
var Mode string
var BaseUrl string

func init() {
	// 从环境变量读取配置
	BotToken = getEnvOrDefault("TOKEN", "")
	ChannelName = getEnvOrDefault("TARGET", "")
	Pass = getEnvOrDefault("PASS", "none")
	Mode = getEnvOrDefault("MODE", "p")
	BaseUrl = getEnvOrDefault("URL", "http://localhost:8088")
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

type UploadResponse struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
	ImgUrl  string `json:"url"`
}

const FileRoute = "/d/"
