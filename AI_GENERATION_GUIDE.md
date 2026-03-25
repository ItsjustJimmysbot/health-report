# Health Report AI 分析生成指南

## 日报 AI 分析格式

日报需要以下 AI 分析字段（每个字段 150-200 字）：

```json
{
  "hrv": "HRV 分析内容 (150-200字)",
  "resting_hr": "静息心率分析内容 (150-200字)",
  "steps": "步数分析内容 (150-200字)",
  "distance": "距离分析内容 (150-200字)",
  "active_energy": "活动能量分析内容 (150-200字)",
  "spo2": "血氧分析内容 (150-200字)",
  "flights": "爬楼分析内容 (150-200字) - 注意：不是 flights_climbed",
  "stand": "站立时间分析内容 (150-200字) - 注意：不是 apple_stand_time",
  "basal": "基础代谢分析内容 (150-200字) - 注意：不是 basal_energy_burned",
  "respiratory": "呼吸率分析内容 (150-200字) - 注意：不是 respiratory_rate",
  "sleep": "睡眠分析内容 (150-200字)",
  "workout": "运动分析内容 (150-200字)",
  "priority": {
    "title": "最高优先级建议标题 (≥10字)",
    "problem": "问题识别 (≥80字)",
    "action": "行动计划 (250-300字)",
    "expectation": "预期效果 (≥70字)"
  },
  "ai2_title": "第二优先级标题 (≥10字)",
  "ai2_problem": "第二优先级问题 (≥80字)",
  "ai2_action": "第二优先级行动 (≥100字)",
  "ai2_expectation": "第二优先级预期 (≥70字)",
  "ai3_title": "第三优先级标题 (≥10字)",
  "ai3_problem": "第三优先级问题 (≥80字)",
  "ai3_action": "第三优先级行动 (≥100字)",
  "ai3_expectation": "第三优先级预期 (≥70字)",
  "breakfast": "早餐建议 (≥30字)",
  "lunch": "午餐建议 (≥30字)",
  "dinner": "晚餐建议 (≥30字)",
  "snack": "加餐建议 (≥30字)"
}
```

**重要字段名映射**（指标名 → AI 字段名）：
| 指标名 | AI 字段名 | 说明 |
|--------|-----------|------|
| flights_climbed | flights | 爬楼层数 |
| apple_stand_time | stand | 站立时间 |
| basal_energy_burned | basal | 基础代谢 |
| respiratory_rate | respiratory | 呼吸率 |
| 其他指标 | 同名 | hrv, resting_hr, steps, distance, active_energy, spo2, sleep, workout |

如果 `report_metrics.selected` 包含额外指标（如 vo2_max, apple_exercise_time），也需要提供对应的 AI 字段。

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

## 完整32项指标AI字段映射表

当 `report_metrics.selected` 包含以下指标时，需要提供对应的AI分析字段：

### 核心健康 (10项)
| 指标名 | AI字段名 | 单位 | 说明 |
|--------|----------|------|------|
| hrv | hrv | ms | 心率变异性 |
| resting_hr | resting_hr | bpm | 静息心率 |
| heart_rate_avg | heart_rate_avg | bpm | 平均心率 |
| steps | steps | 步 | 步数 |
| distance | distance | km | 行走距离 |
| active_energy | active_energy | kcal | 活动能量 |
| spo2 | spo2 | % | 血氧饱和度 |
| respiratory_rate | respiratory | 次/分 | 呼吸率 |
| apple_stand_time | stand | 分钟 | 站立时间 |
| basal_energy_burned | basal | kcal | 基础代谢 |

### 心肺能力 (2项)
| 指标名 | AI字段名 | 单位 | 说明 |
|--------|----------|------|------|
| vo2_max | vo2_max | ml/(kg·min) | 最大摄氧量 |
| physical_effort | physical_effort | kcal/hr·kg | 体力消耗率 |

### 睡眠恢复 (4项)
| 指标名 | AI字段名 | 单位 | 说明 |
|--------|----------|------|------|
| sleep_total_hours | sleep | 小时 | 总睡眠时长 |
| sleep_deep_hours | sleep_deep_hours | 小时 | 深睡时长 |
| sleep_rem_hours | sleep_rem_hours | 小时 | REM睡眠时长 |
| breathing_disturbances | breathing_disturbances | index | 呼吸紊乱指数 |

### 活动与机能 (4项)
| 指标名 | AI字段名 | 单位 | 说明 |
|--------|----------|------|------|
| apple_exercise_time | apple_exercise_time | 分钟 | 锻炼时间 |
| flights_climbed | flights | 层 | 爬楼层数 |
| apple_stand_hour | apple_stand_hour | 小时 | 站立小时数 |
| stair_speed_up | stair_speed_up | m/s | 上楼速度 |

### 高级跑步 (5项)
| 指标名 | AI字段名 | 单位 | 说明 |
|--------|----------|------|------|
| running_speed | running_speed | km/hr | 跑步速度 |
| running_power | running_power | W | 跑步功率 |
| running_stride_length | running_stride_length | m | 跑步步幅 |
| running_ground_contact_time | running_ground_contact_time | ms | 触地时间 |
| running_vertical_oscillation | running_vertical_oscillation | cm | 垂直振幅 |

### 步行步态 (5项)
| 指标名 | AI字段名 | 单位 | 说明 |
|--------|----------|------|------|
| walking_speed | walking_speed | km/hr | 步行速度 |
| walking_step_length | walking_step_length | cm | 步行步长 |
| walking_heart_rate_average | walking_heart_rate_average | bpm | 步行平均心率 |
| walking_asymmetry_percentage | walking_asymmetry_percentage | % | 步行不对称性 |
| walking_double_support_percentage | walking_double_support_percentage | % | 双支撑时间占比 |

### 环境暴露 (2项)
| 指标名 | AI字段名 | 单位 | 说明 |
|--------|----------|------|------|
| headphone_audio_exposure | headphone_audio_exposure | dBASPL | 耳机音频暴露 |
| environmental_audio_exposure | environmental_audio_exposure | dBASPL | 环境音频暴露 |
