package main

import (
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"

	"csz.net/tgstate/conf"
	"csz.net/tgstate/control"
	"csz.net/tgstate/utils"
)

var webPort string
var OptApi = true

func main() {
	// 检查是否启动管理接口模式
	if len(os.Args) > 1 && os.Args[1] == "management" {
		fmt.Println("🔧 启动管理接口模式")
		api := NewManagementAPI()
		api.StartManagementAPI()
		return
	}

	//判断是否设置参数
	if conf.BotToken == "" || conf.ChannelName == "" {
		fmt.Println("Bot Token 或 Channel Name 为空")
		fmt.Println("运行在简单文件服务模式（仅提供静态页面）")
	} else {
		go utils.BotDo()
	}
	web()
}

func web() {
	http.HandleFunc(conf.FileRoute, control.D)
	if OptApi {
		if conf.Pass != "" && conf.Pass != "none" {
			http.HandleFunc("/pwd", control.Pwd)
		}
		http.HandleFunc("/api", control.Middleware(control.UploadImageAPI))
		http.HandleFunc("/", control.Middleware(control.Index))
	}

	if listener, err := net.Listen("tcp", ":"+webPort); err != nil {
		fmt.Printf("端口 %s 已被占用\n", webPort)
	} else {
		defer listener.Close()
		fmt.Printf("启动Web服务器，监听端口 %s\n", webPort)
		if err := http.Serve(listener, nil); err != nil {
			fmt.Println(err)
		}
	}
}

func init() {
	flag.StringVar(&webPort, "port", "8088", "Web Port")
	flag.StringVar(&conf.BotToken, "token", os.Getenv("TOKEN"), "Bot Token")
	flag.StringVar(&conf.ChannelName, "target", os.Getenv("TARGET"), "Channel Name or ID")
	flag.StringVar(&conf.Pass, "pass", os.Getenv("PASS"), "Visit Password")
	flag.StringVar(&conf.Mode, "mode", os.Getenv("MODE"), "Run mode")
	flag.StringVar(&conf.BaseUrl, "url", os.Getenv("URL"), "Base Url")
	flag.Parse()
	if conf.Mode == "m" {
		OptApi = false
	}
	if conf.Mode != "p" && conf.Mode != "m" {
		conf.Mode = "p"
	}
}
