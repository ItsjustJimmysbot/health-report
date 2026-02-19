#!/bin/bash
#
# Health Auto Export API Server 启动脚本
# 用于接收 iPhone Health Auto Export App 的数据推送
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PIDFILE="/tmp/health-api-server.pid"
PORT=8080

check_server() {
    if [[ -f "$PIDFILE" ]]; then
        local pid=$(cat "$PIDFILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            echo "✅ Server is already running (PID: $pid)"
            echo "   Endpoint: http://localhost:$PORT"
            return 0
        else
            rm -f "$PIDFILE"
        fi
    fi
    return 1
}

start_server() {
    if check_server; then
        return 0
    fi
    
    echo "🚀 Starting Health Auto Export API Server..."
    echo "   Port: $PORT"
    echo "   Log: ~/.openclaw/workspace-health/logs/health-api.log"
    
    # 后台启动 Python 服务器
    nohup python3 "$SCRIPT_DIR/server.py" "$PORT" > /dev/null 2>&1 &
echo $! > "$PIDFILE"
    
    sleep 1
    
    if check_server; then
        echo "✅ Server started successfully"
        echo ""
        echo "📱 iPhone Health Auto Export 配置:"
        echo "   API Endpoint: http://$(ipconfig getifaddr en0):$PORT/api/health"
        echo "   或: http://$(hostname -I | awk '{print $1}'):$PORT/api/health"
        return 0
    else
        echo "❌ Failed to start server"
        return 1
    fi
}

stop_server() {
    if [[ -f "$PIDFILE" ]]; then
        local pid=$(cat "$PIDFILE" 2>/dev/null || echo "")
        if [[ -n "$pid" ]]; then
            kill "$pid" 2>/dev/null && echo "🛑 Server stopped (PID: $pid)" || echo "⚠️ Server not running"
        fi
        rm -f "$PIDFILE"
    else
        echo "⚠️ No PID file found, server may not be running"
    fi
}

restart_server() {
    stop_server
    sleep 1
    start_server
}

status_server() {
    if check_server; then
        # 测试健康检查端点
        local response=$(curl -s http://localhost:$PORT/health 2>/dev/null || echo "")
        if [[ -n "$response" ]]; then
            echo "📊 Health check response:"
            echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        fi
    else
        echo "❌ Server is not running"
    fi
}

test_connection() {
    echo "🧪 Testing server connection..."
    
    # 本地测试
    local local_response=$(curl -s http://localhost:$PORT/health 2>/dev/null || echo "")
    if [[ -n "$local_response" ]]; then
        echo "✅ Local connection OK: http://localhost:$PORT"
        echo "$local_response" | python3 -m json.tool 2>/dev/null || true
    else
        echo "❌ Local connection failed"
        return 1
    fi
    
    echo ""
    echo "📱 iPhone 配置信息:"
    echo "   请确保 iPhone 和 Mac 在同一 WiFi 网络"
    echo ""
    
    # 获取 IP 地址
    local ip=$(ipconfig getifaddr en0 2>/dev/null || hostname -I | awk '{print $1}')
    if [[ -n "$ip" ]]; then
        echo "   API Endpoint: http://$ip:$PORT/api/health"
    fi
}

case "${1:-start}" in
    start)
        start_server
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server
        ;;
    status)
        status_server
        ;;
    test)
        test_connection
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|test}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the server"
        echo "  stop    - Stop the server"
        echo "  restart - Restart the server"
        echo "  status  - Check server status"
        echo "  test    - Test server connection"
        exit 1
        ;;
esac
