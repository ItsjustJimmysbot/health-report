# 周报月报生成标准化流程 V5.0

**生效日期**: 2026-02-22  
**版本**: V5.0  
**核心模式**: AI对话分析 + 模板填充生成

---

## 📋 概述

周报和月报与日报的生成方式有本质区别：
- **日报**: 基于单日数据，逐项指标AI分析
- **周报/月报**: 基于多日数据聚合，进行**趋势分析**和**模式识别**

---

## 🔄 生成流程

### 第一步：数据聚合（脚本完成）

#### 1.1 读取每日缓存文件（V5.0新增）

**必须读取缓存文件获取历史数据**，用于本周对比分析：

```python
def load_daily_cache(date_str: str) -> dict:
    """读取每日数据缓存"""
    cache_file = CACHE_DIR / f'{date_str}.json'
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# 周报：读取本周7天缓存
week_dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', 
              '2026-02-22', '2026-02-23', '2026-02-24']
daily_caches = [load_daily_cache(d) for d in week_dates if load_daily_cache(d)]

# 生成本周对比表数据
weekly_comparison_rows = generate_weekly_comparison(daily_caches)
```

**缓存文件路径**: `cache/daily/YYYY-MM-DD.json`

**缓存数据结构**:
```json
{
  "date": "2026-02-18",
  "hrv": {"value": 52.8, "points": 51},
  "resting_hr": {"value": 57},
  "steps": 6852,
  "sleep": {"total": 2.82, ...},
  "workouts": [...]
}
```

#### 1.2 聚合统计数据

**周报**（7天数据）:
```python
weekly_data = {
    "start_date": "2026-02-18",
    "end_date": "2026-02-24",
    "avg_hrv": 49.6,           # 7天平均
    "hrv_trend": "稳定",        # 脚本计算趋势
    "total_steps": 17765,      # 7天总和
    "daily_data": [...],       # 7天明细
    "statistics": {            # 脚本计算统计值
        "hrv_max": 53.4,
        "hrv_min": 45.7,
        "hrv_std": 3.8
    },
    "weekly_comparison": weekly_comparison_rows  # 本周对比数据
}
```

**月报**（30天数据）:
```python
monthly_data = {
    "year": 2026,
    "month": 2,
    "avg_hrv": 49.6,           # 30天平均
    "avg_steps": 4441,         # 日均
    "workout_days": 4,         # 运动天数
    "workout_frequency": "4/30 天"
}
```

**脚本生成内容（非AI）**:
- 平均值、总和、最大最小值
- 趋势判断（上升/下降/稳定）
- 数据覆盖率统计
- 每日明细列表

---

### 第二步：AI分析（当前对话生成）

**必须由AI生成的内容**:

| 内容 | 类型 | 说明 |
|------|------|------|
| **趋势总结** | AI生成 | 基于多日数据的整体趋势分析 |
| **HRV趋势分析** | AI生成 | HRV变化模式、与睡眠/运动的关联 |
| **睡眠趋势分析** | AI生成 | 睡眠时长/质量的变化趋势 |
| **活动趋势分析** | AI生成 | 步数/运动频率的模式识别 |
| **周/月建议** | AI生成 | 基于趋势的建议（高/中/长期） |

**AI分析示例**:
```
趋势总结: "本周健康状态呈现「睡眠质量显著改善但活动量波动大」的特点。
HRV在45.7-53.4ms区间波动..."

HRV分析: "本周平均HRV 49.6ms（理想区间50-65ms），略低于理想水平。
HRV波动范围较大（45.7-53.4ms，标准差3.8），表明身体恢复状态不够稳定..."
```

---

### 第三步：报告生成（模板填充）

**模板变量分类**:

| 变量 | 来源 | 类型 |
|------|------|------|
| `{{START_DATE}}`, `{{END_DATE}}` | 数据文件 | 脚本填充 |
| `{{AVG_HRV}}`, `{{TOTAL_STEPS}}` | 脚本计算 | 脚本填充 |
| `{{HRV_TREND}}` | 脚本判断 | 脚本填充 |
| `{{TREND_SUMMARY}}` | AI分析 | AI生成 |
| `{{HRV_ANALYSIS}}` | AI分析 | AI生成 |
| `{{AI1_CONTENT}}` | AI建议 | AI生成 |

---

## ✅ 内容来源对照表

### 周报内容来源

| 部分 | AI生成 | 脚本/模板 | 说明 |
|------|--------|-----------|------|
| **页眉页脚** | ❌ | ✅ 模板 | 日期、数据状态 |
| **统计概览卡片** | ❌ | ✅ 脚本 | 平均值、趋势标签 |
| **统计对比表** | ❌ | ✅ 脚本 | 最大/最小/标准差 |
| **每日明细列表** | ❌ | ✅ 脚本 | 7天数据列表 |
| **趋势总结** | ✅ AI | ❌ | 整体趋势分析 |
| **HRV分析** | ✅ AI | ❌ | HRV变化模式 |
| **睡眠分析** | ✅ AI | ❌ | 睡眠趋势分析 |
| **活动分析** | ✅ AI | ❌ | 活动模式识别 |
| **AI建议1-3** | ✅ AI | ❌ | 高/中/长期建议 |

### 月报内容来源

| 部分 | AI生成 | 脚本/模板 | 说明 |
|------|--------|-----------|------|
| **页眉页脚** | ❌ | ✅ 模板 | 年月、数据状态 |
| **统计概览** | ❌ | ✅ 脚本 | 日均值、运动频率 |
| **月度总结** | ✅ AI | ❌ | 整体评估 |
| **成就总结** | ✅ AI | ❌ | 本月亮点 |
| **挑战分析** | ✅ AI | ❌ | 存在问题 |
| **AI建议** | ✅ AI | ❌ | 立即/短期/长期 |

---

## 🚫 禁止事项

1. **禁止凭记忆对比**: 必须读取缓存文件才能对比历史周期
2. **禁止编造趋势**: 必须基于真实数据点识别模式
3. **禁止模板化建议**: AI建议必须基于本周/本月具体数据

---

## 📊 数据文件规范

### 周报数据文件
```json
{
  "report_type": "weekly",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "data_days": 7,
  
  // 脚本计算
  "avg_hrv": 49.6,
  "hrv_trend": "稳定",
  "total_steps": 17765,
  "daily_data": [...],
  "statistics": {...},
  
  // AI生成
  "ai_analysis": {
    "trend_summary": "...",
    "hrv_analysis": "...",
    "sleep_analysis": "...",
    "activity_analysis": "...",
    "recommendations": {...}
  }
}
```

### 月报数据文件
```json
{
  "report_type": "monthly",
  "year": 2026,
  "month": 2,
  "data_days": 30,
  
  // 脚本计算
  "avg_hrv": 49.6,
  "avg_steps": 4441,
  "workout_days": 4,
  
  // AI生成
  "ai_analysis": {
    "summary": "...",
    "achievements": "...",
    "challenges": "...",
    "monthly_recommendations": {...}
  }
}
```

---

## 🔧 生成脚本

**周报月报共用脚本**: `scripts/generate_weekly_monthly_report.py`

```bash
# 周报
python3 scripts/generate_weekly_monthly_report.py weekly data_weekly.json report.html

# 月报
python3 scripts/generate_weekly_monthly_report.py monthly data_monthly.json report.html
```

---

## ✅ 质量检查清单

- [ ] 数据聚合正确（平均/总和/最大最小）
- [ ] 趋势判断合理（基于实际数据变化）
- [ ] AI分析基于真实聚合数据
- [ ] 无凭记忆对比历史周期
- [ ] AI建议针对本周/本月具体情况
- [ ] 数据覆盖率标注清晰

---

**版本**: V5.0  
**配套文档**: REPORT_STANDARD_V5_REVISED.md（日报标准）
