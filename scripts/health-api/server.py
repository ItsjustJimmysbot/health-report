#!/usr/bin/env python3
"""
Health Auto Export API Server
接收 iPhone Health Auto Export App 的 REST API 推送
保存 Apple Health 数据（HRV、呼吸、血氧等）
"""

import http.server
import socketserver
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 配置
PORT = 8080
DATA_DIR = Path.home() / ".openclaw" / "workspace-health" / "data" / "apple-health"
LOG_FILE = Path.home() / ".openclaw" / "workspace-health" / "logs" / "health-api.log"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

class HealthHandler(http.server.BaseHTTPRequestHandler):
    """处理 Health Auto Export 的 HTTP 请求"""
    
    def log_message(self, format, *args):
        """自定义日志，同时输出到文件和终端"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"[{timestamp}] {self.address_string()} - {format % args}"
        print(message)
        
        # 写入日志文件
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except Exception as e:
            print(f"[ERROR] Failed to write log: {e}")
    
    def do_GET(self):
        """处理 GET 请求 - 健康检查"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "status": "ok",
                "service": "health-auto-export-api",
                "timestamp": datetime.now().isoformat(),
                "data_dir": str(DATA_DIR)
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')
    
    def do_POST(self):
        """处理 POST 请求 - 接收健康数据"""
        if self.path == '/api/health' or self.path == '/api/health-data':
            try:
                # 读取请求体
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self._send_error(400, "Empty request body")
                    return
                
                post_data = self.rfile.read(content_length)
                
                # 验证 JSON 格式
                try:
                    data = json.loads(post_data.decode('utf-8'))
                except json.JSONDecodeError as e:
                    self._send_error(400, f"Invalid JSON: {e}")
                    return
                
                # 从数据中提取日期，或使用今天日期
                export_date = self._extract_date(data)
                filename = f"health-{export_date}.json"
                filepath = DATA_DIR / filename
                
                # 保存数据（如果文件存在则覆盖，保留备份）
                if filepath.exists():
                    backup_name = f"health-{export_date}-backup-{datetime.now().strftime('%H%M%S')}.json"
                    backup_path = DATA_DIR / backup_name
                    filepath.rename(backup_path)
                    print(f"[INFO] Backed up existing file to {backup_name}")
                
                # 保存新数据
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # 同时保存一份 "latest.json" 方便脚本读取
                latest_path = DATA_DIR / "latest.json"
                with open(latest_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                # 记录接收摘要
                summary = self._extract_summary(data)
                print(f"[INFO] Saved health data: {filename}")
                print(f"[INFO] Summary: {summary}")
                
                # 发送成功响应
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    "status": "ok",
                    "message": "Data received and saved",
                    "filename": filename,
                    "summary": summary
                }
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                self._send_error(500, f"Server error: {e}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')
    
    def _send_error(self, code, message):
        """发送错误响应"""
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())
    
    def _extract_date(self, data):
        """从数据中提取日期"""
        # 尝试从 metadata 中提取
        if 'metadata' in data and 'exportDate' in data['metadata']:
            date_str = data['metadata']['exportDate'][:10]  # YYYY-MM-DD
            return date_str
        
        # 尝试从 metrics 中提取
        if 'metrics' in data:
            metrics = data['metrics']
            for key in metrics:
                if isinstance(metrics[key], dict) and 'date' in metrics[key]:
                    return metrics[key]['date'][:10]
        
        # 默认返回今天
        return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_summary(self, data):
        """提取数据摘要用于日志"""
        summary = []
        
        if 'metrics' in data:
            metrics = data['metrics']
            if 'heartRateVariability' in metrics:
                hrv = metrics['heartRateVariability']
                summary.append(f"HRV: {hrv.get('avg', 'N/A')}ms")
            if 'restingHeartRate' in metrics:
                rhr = metrics['restingHeartRate']
                summary.append(f"RHR: {rhr.get('value', 'N/A')}bpm")
            if 'respiratoryRate' in metrics:
                rr = metrics['respiratoryRate']
                summary.append(f"RR: {rr.get('avg', 'N/A')}/min")
            if 'oxygenSaturation' in metrics:
                spo2 = metrics['oxygenSaturation']
                summary.append(f"SpO2: {spo2.get('avg', 'N/A')}%")
            if 'sleep' in metrics:
                sleep = metrics['sleep']
                summary.append(f"Sleep: {sleep.get('totalMinutes', 'N/A')}min")
        
        return ", ".join(summary) if summary else "No metrics extracted"


def run_server(port=PORT):
    """启动 HTTP 服务器"""
    with socketserver.TCPServer(("", port), HealthHandler) as httpd:
        print(f"=" * 60)
        print(f"Health Auto Export API Server")
        print(f"=" * 60)
        print(f"Server running at: http://0.0.0.0:{port}")
        print(f"Data directory: {DATA_DIR}")
        print(f"Log file: {LOG_FILE}")
        print(f"")
        print(f"Endpoints:")
        print(f"  GET  /health          - Health check")
        print(f"  POST /api/health      - Receive health data")
        print(f"  POST /api/health-data - Receive health data (alt)")
        print(f"")
        print(f"Press Ctrl+C to stop")
        print(f"=" * 60)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Server stopped by user")
            sys.exit(0)


if __name__ == "__main__":
    # 允许通过命令行参数指定端口
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port)
