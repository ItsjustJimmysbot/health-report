# Health Auto Export 配置指南

> iPhone Health Auto Export App → Mac 本地 HTTP 服务器
> 自动同步 Apple Health 数据（HRV、呼吸、血氧等）

---

## ✅ 服务器状态

**Mac 端服务器已启动！**

```
状态: ✅ 运行中
端口: 8080
本地地址: http://localhost:8080
局域网地址: http://198.18.0.1:8080

API 端点:
  GET  http://198.18.0.1:8080/health          - 健康检查
  POST http://198.18.0.1:8080/api/health      - 接收数据
  POST http://198.18.0.1:8080/api/health-data - 接收数据（备用）

数据保存位置: ~/.openclaw/workspace-health/data/apple-health/
日志文件: ~/.openclaw/workspace-health/logs/health-api.log
```

---

## 📱 iPhone 配置步骤

### Step 1: 确认网络连接
1. 确保 iPhone 和 Mac 连接到 **同一个 WiFi 网络**
2. iPhone 关闭 VPN（避免局域网连接问题）

### Step 2: Health Auto Export 设置

打开 **Health Auto Export** App：

#### 1. 进入 Settings → API v2

```
☑️ Enable REST API v2
   └─ 开启

☑️ Automatic Export
   └─ 开启

Export Format
   └─ 选择: JSON v2

Export Frequency
   └─ 选择: Daily

Export Time
   └─ 设置: 08:00 (建议，在12:00分析前)
```

#### 2. 配置 API Endpoint

```
API Endpoint URL:
http://198.18.0.1:8080/api/health

HTTP Method:
POST

Content-Type:
application/json
```

#### 3. 选择要导出的数据类型

```
☑ Heart Rate (心率)
☑ Heart Rate Variability (心率变异性/HRV)
☑ Resting Heart Rate (静息心率)
☑ Respiratory Rate (呼吸频率)
☑ Oxygen Saturation (血氧饱和度)
☑ Sleep Analysis (睡眠分析)
☑ Active Energy (活动能量)
☑ Steps (步数)
☑ Workouts (运动记录)
```

#### 4. 配置导出时间范围

```
Time Range:
└─ 选择: Last 24 hours

Data Aggregation:
└─ 选择: Include summary statistics (包含统计摘要)
```

### Step 3: 测试连接

1. 在 Health Auto Export 中点击 **"Test Connection"** 或 **"Send Test"**
2. 等待测试完成
3. 查看 Mac 端日志确认收到数据：

```bash
# 在 Mac 终端运行
tail -f ~/.openclaw/workspace-health/logs/health-api.log
```

### Step 4: 保存配置

点击 **Save** 保存配置。

---

## 🧪 手动测试方法

如果你想先测试数据是否能正常接收，可以在 iPhone 上手动触发一次导出：

1. Health Auto Export → 点击 **"Export Now"** 或 **"Manual Export"**
2. 选择 **JSON v2** 格式
3. 选择 **REST API** 目标
4. 检查 Mac 是否收到数据

---

## 📊 数据格式示例

Health Auto Export JSON v2 格式：

```json
{
  "metadata": {
    "exportDate": "2026-02-19T08:00:00Z",
    "device": "Apple Watch",
    "source": "Health Auto Export",
    "version": "2.0"
  },
  "metrics": {
    "heartRateVariability": {
      "avg": 45.2,
      "min": 32.1,
      "max": 68.5,
      "samples": 24,
      "unit": "ms"
    },
    "restingHeartRate": {
      "value": 62,
      "unit": "bpm"
    },
    "respiratoryRate": {
      "avg": 14.5,
      "min": 12.0,
      "max": 16.5,
      "unit": "breaths/min"
    },
    "oxygenSaturation": {
      "avg": 98.5,
      "min": 95.0,
      "max": 100.0,
      "unit": "%"
    },
    "sleep": {
      "totalMinutes": 420,
      "deepMinutes": 85,
      "remMinutes": 95,
      "lightMinutes": 240,
      "efficiency": 85,
      "wakeCount": 3
    }
  }
}
```

---

## 🛠️ Mac 端管理命令

```bash
# 启动服务器
cd ~/.openclaw/workspace-health
bash scripts/health-api/control.sh start

# 停止服务器
bash scripts/health-api/control.sh stop

# 重启服务器
bash scripts/health-api/control.sh restart

# 查看状态
bash scripts/health-api/control.sh status

# 测试连接
bash scripts/health-api/control.sh test
```

---

## 📝 故障排查

### 问题 1: iPhone 无法连接到 Mac

**症状**: 导出失败，显示连接错误

**检查**:
1. iPhone 和 Mac 是否在同一 WiFi？
2. Mac 防火墙是否允许 8080 端口？
3. iPhone 是否开启了 VPN？

**解决**:
```bash
# 检查 Mac 防火墙
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

# 如果开启，添加允许规则
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add $(which python3)
```

### 问题 2: 数据格式不正确

**症状**: 服务器返回 400 错误

**检查**:
1. Health Auto Export 是否选择了 **JSON v2** 格式？
2. Content-Type 是否设置为 **application/json**？

### 问题 3: 数据没有保存

**症状**: 服务器返回 200 但找不到文件

**检查**:
```bash
# 检查数据目录
ls -la ~/.openclaw/workspace-health/data/apple-health/

# 检查日志
cat ~/.openclaw/workspace-health/logs/health-api.log
```

---

## ✅ 配置检查清单

- [ ] iPhone 和 Mac 在同一 WiFi
- [ ] Health Auto Export API v2 已开启
- [ ] 导出格式选择 JSON v2
- [ ] API Endpoint 设置为 http://198.18.0.1:8080/api/health
- [ ] 选择了 HRV、呼吸频率、血氧等关键指标
- [ ] 手动测试成功
- [ ] Mac 端能看到接收到的数据文件

---

**配置完成后，每天 8:00 数据会自动推送到 Mac，12:00 健康分析报告会包含这些指标！**
