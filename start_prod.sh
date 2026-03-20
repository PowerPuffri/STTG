#!/bin/bash

# 配置区域
export TG_BOT_TOKEN="8528099425:AAFHxGGIHMSJkAHDBDXKJ9eim68wziF_rQQ"
export ST_ADMIN_PASS="123456"  # 之前设置的密码

# 代理配置（从系统设置读取）
export HTTP_PROXY="http://127.0.0.1:7897"
export HTTPS_PROXY="http://127.0.0.1:7897"

# 检查是否安装了 PM2
if ! command -v pm2 &> /dev/null; then
    echo "PM2 未安装，正在安装..."
    npm install pm2 -g
fi

# 创建日志目录
mkdir -p logs

# 安装 Python 依赖
echo "安装 Python 依赖..."
pip3 install requests websockets aiohttp

# 启动服务
echo "启动服务..."
pm2 start ecosystem.config.js

# 保存当前进程列表，以便开机自启（可选）
# pm2 save

echo "=================================================="
echo "所有服务已启动！"
echo "使用 'pm2 list' 查看状态"
echo "使用 'pm2 logs' 查看日志"
echo "使用 'pm2 stop all' 停止服务"
echo "=================================================="
