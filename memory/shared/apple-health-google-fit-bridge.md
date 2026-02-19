# Apple Health → Google Fit 桥接方案

> 解决 Apple Watch HRV、呼吸频率、血氧数据同步到 Google Fit 的技术方案
> 创建日期: 2026-02-19

---

## 🎯 问题背景

Apple Watch 采集的完整健康数据：
- ✅ 心率（已同步）
- ❌ HRV (心率变异性) — Apple Health 有，Google Fit 无
- ❌ 呼吸频率 — Apple Health 有，Google Fit 无  
- ❌ 血氧 (SpO2) — Apple Health 有，Google Fit 无
- ❌ 体温 — Apple Health 有，Google Fit 无
- ❌ 静息心率 — Apple Health 有，Google Fit 不完全

**核心问题**: Apple Health 和 Google Fit 是竞争对手的生态，不会原生互通。

---

## 📱 方案一：第三方同步 App（推荐）

### 1. Health Sync (Android)
**平台**: Android (Google Play)  
**价格**: 免费 / 付费版 ~$3  
**功能**:
- ✅ Apple Health → Google Fit 单向同步
- ✅ 支持心率、步数、活动、睡眠
- ⚠️ HRV 支持不确定（需验证）

**限制**: 
- 需要在 Android 设备上运行
- iPhone 用户需要备用 Android 设备或模拟器

---

### 2. Sync Solver (iOS)
**平台**: iOS App Store  
**价格**: $2-5  
**功能**:
- ✅ Apple Health → Google Fit 导出
- ✅ 批量历史数据导出
- ⚠️ 非实时同步，需手动触发

**限制**:
- 不是实时同步，需要定期手动导出
- HRV 支持待验证

---

### 3. RunKeeper / Strava 中转
**思路**: Apple Health → RunKeeper → Google Fit

**步骤**:
1. iPhone 安装 RunKeeper
2. 授权 RunKeeper 读取 Apple Health
3. RunKeeper 会自动同步到 Google Fit

**支持数据**:
- ✅ 运动记录、心率、GPS 轨迹
- ❌ HRV、呼吸频率、血氧（不通过）

---

## 🔧 方案二：自建桥接（技术方案）

### 架构设计
```
Apple Watch → Apple Health → iOS Shortcuts → 
    ↓
Custom API (自建) → 存储 → Google Fit API 写入
```

### 实现路径

#### Step 1: iOS Shortcuts 自动化
创建 iOS Shortcuts 脚本：
1. 每天定时读取 Apple Health 数据
2. 提取 HRV、呼吸频率、血氧
3. POST 到自建 API

**Shortcuts 能力**:
- 可以读取 Apple Health 几乎所有数据
- 可以定时触发（如每天早上 8 点）
- 可以 HTTP POST 到外部 API

#### Step 2: 自建 API 服务
简单 Flask/FastAPI 服务：
- 接收 Shortcuts 推送的数据
- 存储到本地数据库
- 提供查询接口给健康分析脚本

#### Step 3: 健康分析脚本读取
修改 `daily-health-report.sh`:
- 同时查询 Google Fit + 自建 API
- 合并数据生成完整报告

---

## 🛠️ 方案三：快捷实现（Shortcuts + 文件同步）

### 最简单的 MVP 方案

#### iPhone 端（Shortcuts）
```
1. 每天早上 8:00 自动运行
2. 读取 Apple Health:
   - HRV (昨天平均值)
   - 呼吸频率
   - 血氧平均值
   - 静息心率
3. 生成 JSON:
   {
     "date": "2026-02-19",
     "hrv_avg": 45.2,
     "respiratory_rate": 14.5,
     "spo2_avg": 98.5,
     "resting_hr": 62
   }
4. 发送到: Telegram / iCloud / 邮件
```

#### 服务端（你的 Mac）
```
1. 每天 12:00 健康分析前
2. 读取 iPhone 发来的数据文件
3. 与 Google Fit 数据合并
4. 生成完整报告
```

---

## 📊 各方案对比

| 方案 | 复杂度 | 成本 | HRV | 呼吸 | 血氧 | 实时性 | 推荐度 |
|------|--------|------|-----|------|------|--------|--------|
| Health Sync | 低 | $3 | ? | ? | ? | 实时 | ⭐⭐⭐ |
| Sync Solver | 低 | $5 | ? | ? | ? | 手动 | ⭐⭐ |
| RunKeeper | 低 | 免费 | ❌ | ❌ | ❌ | 准实时 | ⭐ |
| Shortcuts+API | 中 | 免费 | ✅ | ✅ | ✅ | 准实时 | ⭐⭐⭐⭐ |
| Shortcuts+文件 | 低 | 免费 | ✅ | ✅ | ✅ | 延迟 | ⭐⭐⭐⭐⭐ |

---

## 🎯 推荐实施方案

### Phase 1: 立即实施（Shortcuts + 文件）
**时间**: 今天就可以开始  
**成本**: 免费

**iPhone Shortcuts 设置**:
1. 打开 "快捷指令" App
2. 创建自动化：每天 8:00
3. 添加动作：
   - 获取健康样本 (HRV、呼吸、血氧、静息心率)
   - 日期范围：昨天
   - 生成文本/JSON
   - 发送消息到 Telegram (发给我)

**你的 Mac 端**:
- 我修改脚本，每天 12:00 分析前
- 检查是否有 iPhone 发来的数据
- 合并到健康报告中

### Phase 2: 优化（自建 API）
**时间**: 1-2 周开发  
**成本**: 免费（本地运行）

把 Telegram 消息改为直接 HTTP POST 到本地 API，更自动化。

### Phase 3: 长期（评估 Whoop）
使用 1-2 个月后，评估是否有必要入手 Whoop 获取更专业的 Recovery 分析。

---

## ✅ 下一步行动

1. **你现在可以尝试**: 
   - 在 iPhone 上创建一个 Shortcuts 自动化
   - 先简单读取昨天的 HRV 数据发给我
   - 验证数据能正常获取

2. **我来准备**:
   - 修改健康分析脚本，预留 HRV/呼吸/血氧的数据接口
   - 更新报告模板，展示这些新指标

3. **数据验证后**:
   - 完善 Shortcuts 自动化
   - 设置定时同步

---

**你想先尝试哪种方案？我可以指导你设置 iPhone Shortcuts。**
