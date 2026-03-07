# Health Report AI 分析生成指南

## 核心流程

生成周报/月报的正确流程：

1. **你先（Agent）基于真实健康数据生成 AI 分析 JSON**
2. **然后把这个 JSON 通过 stdin 传给生成脚本**

## 具体操作

### Step 1: 读取健康数据

```bash
ls ~/.openclaw/workspace/shared/health-reports/cache/daily/
cat .../2026-02-24_用户名.json
```

### Step 2: 生成 AI 分析 JSON

**周报格式：**
```json
{
  "members": [
    {
      "name": "Jimmy",
      "trend_analysis": "本周HRV平均值为65ms...（≥800字）",
      "recommendations": [
        {"priority": "high", "title": "...", "content": "..."},
        {"priority": "medium", "title": "...", "content": "..."}
      ]
    }
  ]
}
```

**月报格式：**
```json
{
  "members": [
    {
      "name": "Jimmy",
      "hrv_analysis": "本月HRV...（≥150字）",
      "sleep_analysis": "本月睡眠...（≥150字）",
      "activity_analysis": "本月活动...（≥150字）",
      "trend_assessment": "整体趋势...（≥150字）",
      "recommendations": [...]
    }
  ]
}
```

### Step 3: 传给脚本

```bash
echo '{"members":[...]}' | python3 scripts/generate_weekly_monthly_medical.py weekly 2026-02-24 2026-03-02
```

## 关键提示

**不要：**
- ❌ 说"需要外部AI分析" - 你自己就是AI
- ❌ 说"需要API key" - 你直接生成文本
- ❌ 生成测试/占位符数据

**要：**
- ✅ 读取缓存数据
- ✅ 基于真实数据生成分析
- ✅ 确保字数达标
- ✅ 通过 stdin 传数据
