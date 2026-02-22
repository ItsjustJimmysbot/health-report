# 健康报告生成标准化流程 V5.0 (修订版)

**生效日期**: 2026-02-22  
**版本**: V5.0-REVISED  
**核心模式**: AI对话分析 + 模板填充生成  
**状态**: ✅ 已修订，防止旧版所有已知问题

---

## 📋 修订说明

本版本基于V4.3历史问题全面修订，**所有旧版问题已在V5.0中系统性预防**。

---

## 🚫 绝对禁止规则（V5.0强制执行）

### 1. 禁止使用Subagent生成报告

**旧版问题**: 使用`sessions_spawn`导致错误无法实时发现，多次返工浪费token

**V5.0解决方案**: 
```python
# ❌ 绝对禁止
sessions_spawn(task="生成健康报告...")

# ✅ V5.0强制做法
# 1. 在当前AI对话中直接分析数据（本session已接入Kimi）
# 2. 实时验证AI分析内容（字数、个性化、数据准确性）
# 3. 将AI生成的分析内容填充到模板
# 4. 生成PDF前检查所有变量替换
# 5. 发送前最终验证
```

**违规后果**: 立即标记为"违规生成"，必须在当前会话重新生成

---

### 2. 禁止编造或估算数据（V5.0新增）

**红线规定**: **没有真实数据的地方必须显示"--"，严禁任何形式的编造**

**禁止行为**:
```python
# ❌ 严禁 - 按比例估算睡眠阶段
if sleep_hours > 0 and sleep_deep == 0:
    sleep_deep = sleep_hours * 0.20  # 严禁编造！

# ❌ 严禁 - 使用固定比例填充
'deep_pct': 20,  # 严禁固定比例！
'core_pct': 50,

# ❌ 严禁 - 编造历史对比数据
"较上周平均上升3.2ms"  # 除非真的有历史数据文件

# ❌ 严禁 - 估算睡眠阶段分布
"深睡占20%，核心睡眠占50%"  # 没有真实数据时严禁！
```

**正确做法**:
```python
# ✅ 正确 - 没有数据就显示"--"
if sleep_deep > 0:
    display = f"{sleep_deep:.1f}h ({sleep_deep/sleep_hours*100:.0f}%)"
else:
    display = "--"  # 没有真实数据

# ✅ 正确 - 在AI分析中说明数据缺失
"睡眠阶段数据（深睡/核心/REM）缺失，无法评估睡眠质量结构。"
```

**违规后果**: 数据信任度归零，必须重新生成报告

---

## 📊 V4.3 → V5.0 问题修正对照表

| 旧版问题 | 原因 | V5.0预防措施 | 验证方式 |
|---------|------|-------------|---------|
| **使用Subagent生成报告** | 无法实时验证 | **必须在当前AI对话中分析** | 对话中实时看到分析内容 |
| **指标与数值不对应** | 数据映射错误 | 建立指标-变量名映射表，逐项核对 | 打印每项指标验证 |
| **评级颜色无区分** | CSS类名未动态设置 | 强制根据评分动态设置CSS类 | 生成后检查CSS类名 |
| **AI分析字数不足** | 未使用标准提示词 | 使用标准化提示词模板，强制字数检查 | 生成后统计字数 |
| **图表未生成** | 遗漏Chart.js代码 | 强制包含完整Chart.js代码 | PDF中查看图表 |
| **睡眠数据逻辑错误** | 使用错误字段 | **强制使用`sleepStart`字段** | 验证时间窗口 |
| **HRV显示为0** | 指标名错误`heart_rate_variability_sdnn` | 使用正确名称`heart_rate_variability` | 检查指标名 |
| **血氧显示为9600%** | 未判断原始值单位 | **强制判断：值>1则不乘100** | 验证数值范围 |
| **睡眠结构消失** | 模板填充逻辑错误 | **无阶段数据时显示"--"** | 检查模板变量 |
| **锻炼心率数值0但图表正常** | `heartRate.avg`为null | **从`heartRateData`数组计算** | 对比数值 |
| **AI建议过于笼统** | 使用简化版建议 | **AI对话生成个性化分析** | 检查具体数据引用 |
| **饮食建议太简略** | 缺少具体食谱 | **强制输出一日三餐+两餐方案** | 检查具体内容 |
| **一大段文字可读性差** | 无格式优化 | **使用HTML格式增强可读性** | 查看PDF格式 |

---

## 第一步：数据提取（预防数据错误）

### 1.1 强制数据验证清单

**每项数据提取后必须验证**：

```python
# 验证函数
def validate_extracted_data(data: dict) -> bool:
    """验证提取的数据是否合理"""
    checks = {
        'HRV范围': 20 <= data['hrv']['value'] <= 100,
        'HRV数据点': data['hrv']['points'] > 0,
        '步数非负': data['steps'] >= 0,
        '能量合理': 0 <= data['active_energy'] < 5000,  # kcal
        '血氧范围': 90 <= data['spo2'] <= 100,
        '睡眠非负': data['sleep']['total'] >= 0 if data['sleep'] else True,
    }
    
    for name, result in checks.items():
        if not result:
            print(f"⚠️ 数据验证失败: {name}")
            return False
    return True
```

### 1.2 血氧单位判断（预防9600%错误）

**旧版错误**: 无论原始值多少都乘以100

**V5.0强制逻辑**:
```python
def extract_spo2(metrics):
    """提取血氧，智能判断单位"""
    spo2_raw, points = extract_metric_avg(metrics, 'blood_oxygen_saturation')
    
    # V5.0: 判断原始值是否已经为百分比
    if spo2_raw and spo2_raw > 1:
        # 原始值已经是百分比（如97），不需要再乘100
        spo2 = spo2_raw
    elif spo2_raw:
        # 原始值是0-1范围（如0.97），需要乘100
        spo2 = spo2_raw * 100
    else:
        spo2 = None
    
    # 验证范围
    if spo2 and not (90 <= spo2 <= 100):
        print(f"⚠️ 血氧值异常: {spo2}%")
    
    return {'value': round(spo2, 1) if spo2 else None, 'points': points}
```

### 1.3 睡眠数据读取（预防逻辑错误）

**旧版错误**: 使用`startDate`字段，未按时间窗口筛选；**数据单位理解错误（重要！）**

**⚠️ 关键注意点**: `sleep_analysis`指标的`units`是`hr`（小时），`asleep`值**已经是小时**，不需要除以3600！

**验证方法**:
```python
# 读取指标元数据
sleep_metric = metrics.get('sleep_analysis', {})
print(f"单位: {sleep_metric.get('units')}")  # 应该输出 'hr'

# 原始数据示例
# asleep: 2.8169228286213346  # 这已经是小时！
```

**V5.0强制逻辑**:
```python
def parse_sleep_data_v5(date_str: str) -> dict:
    """V5.0: 使用sleepStart字段，严格时间窗口筛选，正确处理小时单位"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    filepath = HEALTH_DIR / f'HealthAutoExport-{next_date}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    sleep_metric = metrics.get('sleep_analysis', {})
    
    # ⚠️ V5.0: 验证单位是小时(hr)，不是秒！
    units = sleep_metric.get('units', '')
    if units != 'hr':
        print(f"⚠️ 警告: 睡眠数据单位是 {units}，不是预期的 hr")
    
    # 时间窗口：当日20:00至次日12:00
    window_start = date.replace(hour=20, minute=0)
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)
    
    sleep_records = []
    for sleep in sleep_metric.get('data', []):
        # V5.0: 使用sleepStart字段（不是startDate）
        sleep_start_str = sleep.get('sleepStart', '')
        if not sleep_start_str:
            continue
        
        try:
            sleep_start = datetime.strptime(sleep_start_str[:19], '%Y-%m-%d %H:%M:%S')
            
            # V5.0: 严格检查是否在时间窗口内
            if window_start <= sleep_start <= window_end:
                # ⚠️ V5.0: asleep值已经是小时(hr)，不需要 /3600！
                sleep_records.append({
                    'total': sleep.get('asleep', 0) or sleep.get('totalSleep', 0),  # 单位: 小时
                    'deep': sleep.get('deep', 0),      # 单位: 小时
                    'core': sleep.get('core', 0),      # 单位: 小时
                    'rem': sleep.get('rem', 0),        # 单位: 小时
                    'awake': sleep.get('awake', 0),    # 单位: 小时
                })
        except:
            continue
    
    return sleep_records
```

**常见错误警示**:
```python
# ❌ 错误：误以为单位是秒，除以3600
'total': sleep.get('asleep', 0) / 3600  # 结果会变成 0.00078 小时！

# ✅ 正确：直接使用，单位已经是小时
'total': sleep.get('asleep', 0)  # 2.82 小时
```

### 1.4 心率数据计算（预防数值0错误）

**旧版错误**: 直接使用`heartRate.avg`，当为null时显示0

**V5.0强制逻辑**:
```python
def extract_workout_hr(workout: dict) -> dict:
    """V5.0: 优先使用heartRate字段，null时从heartRateData计算"""
    
    hr_field = workout.get('heartRate', {})
    
    # 尝试获取预计算值
    avg_hr = hr_field.get('avg', {}).get('qty') if isinstance(hr_field, dict) else None
    max_hr = hr_field.get('max', {}).get('qty') if isinstance(hr_field, dict) else None
    
    # V5.0: 如果为null，从heartRateData计算
    if avg_hr is None or max_hr is None:
        hr_data = workout.get('heartRateData', [])
        if hr_data:
            avg_values = [hr.get('Avg', 0) for hr in hr_data if 'Avg' in hr]
            max_values = [hr.get('Max', 0) for hr in hr_data if 'Max' in hr]
            
            if avg_values and avg_hr is None:
                avg_hr = sum(avg_values) / len(avg_values)
            if max_values and max_hr is None:
                max_hr = max(max_values)
    
    return {
        'avg_hr': round(avg_hr) if avg_hr else None,
        'max_hr': round(max_hr) if max_hr else None,
    }
```

### 1.5 完整数据提取指标清单（V5.0新增）

**必须提取的11项指标**:

| 指标名称 | 指标Key | 单位 | 提取方法 | 备注 |
|---------|--------|------|---------|------|
| **HRV** | `heart_rate_variability` | ms | 平均值 | 优先指标 |
| **静息心率** | `resting_heart_rate` | bpm | 平均值 | |
| **步数** | `step_count` | 步 | 累加 | |
| **行走距离** | `walking_running_distance` | km | 累加 | V5.0新增 |
| **活动能量** | `active_energy_burned` + Workout能量 | kcal | 累加并合并 | 注意双数据源 |
| **爬楼层数** | `flights_climbed` | 层 | 累加 | V5.0新增 |
| **站立时间** | `apple_stand_time` | min | 累加 | V5.0新增 |
| **血氧饱和度** | `blood_oxygen_saturation` | % | 平均值 | 智能单位判断 |
| **静息能量** | `basal_energy_burned` | kcal | 累加 | kJ转kcal |
| **呼吸率** | `respiratory_rate` | 次/分 | 平均值 | V5.0新增 |
| **睡眠分析** | `sleep_analysis` | hr | 时间窗口筛选 | 单位是小时！|

**数据来源优先级**:
1. **Health Data文件** (`HealthAutoExport-YYYY-MM-DD.json`): 日常活动数据
2. **Workout Data文件** (`HealthAutoExport-YYYY-MM-DD.json`): 运动详细数据
3. **Google Fit** (备用): 当Apple Health缺失时使用

**活动能量合并规则**:
```python
# V5.0: 活动能量 = 日常活动 + 运动消耗
health_energy = extract_metric_sum(metrics, 'active_energy_burned')  # 日常活动
workout_energy = sum(w.get('activeEnergyBurned', 0) for w in workouts)  # 运动

total_kJ = (health_energy or 0) + workout_energy
total_kcal = total_kJ / 4.184
```

**数据缺失处理**:
```python
# ✅ 正确: 没有数据就显示None或0，不编造
if not data:
    return {'value': None, 'points': 0}  # 或 {'value': 0, 'points': 0}

# ❌ 错误: 使用固定值或估算值填充
if not data:
    return {'value': 100, 'points': 1}  # 严禁编造！
```

### 1.6 数据来源追踪（V5.0新增）

**必须在输出中注明数据来源**:

```python
result = {
    'date': date_str,
    'data_source': 'Apple Health',  # 或 'Google Fit' 或 'Mixed'
    'hrv': {...},
    'sleep': {
        'total_hours': 2.82,
        'data_source': 'Apple Health',  # 每项可单独标注
        # 如果没有阶段数据，不编造，显示0或None
        'deep_hours': 0,  # 真实数据为0，不是编造
        'core_hours': 0,
        'rem_hours': 0,
    }
}
```

**AI分析时说明数据局限性**:

```
✅ 正确示例:
"睡眠时长2.82小时（Apple Health记录）。睡眠阶段数据（深睡/核心/REM）
缺失，无法评估睡眠质量结构。建议检查Apple Watch睡眠追踪设置。"

❌ 错误示例:
"睡眠2.82小时，其中深睡占20%，核心睡眠占50%，REM占20%..."  # 编造！
```

**报告页脚标注**:
```
数据来源: Apple Health | 生成: 2026-02-22 20:30
```

### 1.7 数据字段完整性检查（V5.0新增）

**问题**: 在复制/转换数据文件时，容易遗漏关键字段（如`hr_data`），导致图表缺失

**根本原因**:
```python
# ❌ 错误：创建新数据文件时只复制部分字段
new_data = {
    'date': old_data['date'],
    'hrv': old_data['hrv'],
    'workouts': [{
        'name': w['name'],
        'duration': w['duration'],
        # 遗漏了 hr_data！
    }]
}
```

**解决方案**:

**方案1: 使用数据验证函数**
```python
REQUIRED_WORKOUT_FIELDS = ['name', 'duration_min', 'avg_hr', 'max_hr', 'energy_kcal', 'hr_data']
REQUIRED_METRIC_FIELDS = ['value', 'points', 'analysis']

def validate_data_integrity(data: dict) -> bool:
    """验证数据字段完整性"""
    errors = []
    
    # 检查workouts
    for i, w in enumerate(data.get('workouts', [])):
        for field in REQUIRED_WORKOUT_FIELDS:
            if field not in w:
                errors.append(f"Workout {i} 缺失字段: {field}")
    
    # 检查metrics
    for metric_name in ['hrv', 'resting_hr', 'steps']:
        metric = data.get(metric_name, {})
        if not metric.get('analysis'):
            errors.append(f"{metric_name} 缺失 analysis")
    
    if errors:
        print("❌ 数据完整性检查失败:")
        for e in errors:
            print(f"  - {e}")
        return False
    
    return True

# 生成报告前必须调用
if not validate_data_integrity(data):
    raise ValueError("数据不完整，请检查")
```

**方案2: 使用数据迁移而非复制**
```python
# ✅ 正确：在原数据基础上添加新字段，不删除旧字段
def add_ai_analysis_to_data(raw_data: dict, ai_analyses: dict) -> dict:
    """在原始数据基础上添加AI分析，保留所有原始字段"""
    data = raw_data.copy()  # 复制原始数据，保留所有字段
    
    # 添加AI分析到各指标
    for metric_name, analysis in ai_analyses.items():
        if metric_name in data and isinstance(data[metric_name], dict):
            data[metric_name]['analysis'] = analysis
    
    # 添加AI建议
    data['ai_recommendations'] = ai_analyses.get('recommendations', {})
    
    return data  # 原始字段（包括hr_data）都被保留
```

**方案3: 生成前验证关键图表数据**
```python
def verify_charts_will_render(data: dict) -> bool:
    """验证图表是否能正常渲染"""
    
    # 检查心率图
    for i, w in enumerate(data.get('workouts', [])):
        hr_data = w.get('hr_data', [])
        if not hr_data:
            print(f"⚠️ Workout {i} 缺少 hr_data，心率图将无法显示")
            return False
        if len(hr_data) < 3:
            print(f"⚠️ Workout {i} hr_data点数不足({len(hr_data)})，图表可能异常")
            return False
    
    return True
```

**新增检查清单项**:
- [ ] **数据字段完整性** - 验证所有必需字段（特别是`hr_data`）存在
- [ ] **图表数据验证** - 生成前确认图表有足够数据点

---

## 第二步：AI分析（核心改进）

### 2.1 分析方式（根本性改变）

**旧版**: 使用本地脚本模板填充（非真正AI分析）

**V5.0**: **在当前AI对话中进行分析**（真正的大模型分析）

**优势**:
- ✅ 真正理解数据关联（睡眠↔HRV↔运动）
- ✅ 个性化洞察（基于具体数据点）
- ✅ 实时验证和调整
- ✅ 避免模板化表达

### 2.2 标准化提示词（预防字数不足/笼统）

**V5.0强制要求 - AI分析必须基于真实数据**：

```python
# 每项分析后必须验证
def verify_ai_analysis(text: str, min_len: int, max_len: int, data: dict) -> bool:
    """验证AI分析字数和数据真实性"""
    if len(text) < min_len:
        print(f"⚠️ 字数不足: {len(text)}字 < {min_len}字")
        return False
    if len(text) > max_len:
        print(f"⚠️ 字数超限: {len(text)}字 > {max_len}字")
        return False
    
    # 检查具体数据引用 - 必须引用真实数据
    has_real_data = False
    if data.get('hrv', {}).get('value') and str(data['hrv']['value']) in text:
        has_real_data = True
    if data.get('steps', {}).get('value') and str(data['steps']['value']) in text:
        has_real_data = True
    if not has_real_data:
        print("⚠️ AI分析未引用具体数据点")
        return False
    
    # 检查编造数据 - 严禁！
    # 如果没有睡眠阶段数据，分析中不能出现具体比例
    if not data.get('sleep', {}).get('deep_hours'):
        if '深睡' in text and '%' in text:
            print("❌ AI分析编造了睡眠阶段比例！")
            return False
    
    # 检查禁止词汇
    forbidden_words = ['良好', '注意', '适当', '一般']
    for word in forbidden_words:
        if word in text:
            print(f"⚠️ 发现模糊词汇: {word}")
            return False
    
    return True
```

**AI分析约束规则**：

| 数据情况 | 正确做法 | 错误做法 |
|---------|---------|---------|
| 有完整睡眠数据 | "深睡2.1小时(30%)..." | 无需特别说明 |
| 无睡眠阶段数据 | "睡眠阶段数据缺失，无法评估..." | "深睡占20%，核心占50%..." |
| 无历史数据 | "今日HRV 52.8ms..." | "较上周上升3.2ms..." |
| 数据来源不同 | "(数据来源: Google Fit)" | 混合数据不注明来源 |

**AI分析模板（基于真实数据）**：

```
【HRV分析】（有真实数据）
心率变异性今日为{hrv_value}ms（基于{hrv_points}个数据点测量）...

【睡眠分析】（无阶段数据时）
今日睡眠{sleep_hours}小时（{data_source}记录）。
⚠️ 睡眠阶段数据（深睡/核心/REM）缺失，无法评估睡眠质量结构。
可能原因：Apple Watch未正确佩戴或睡眠模式未开启...

【运动分析】（有真实数据）
今日完成{workout_name}，时长{duration}分钟，平均心率{avg_hr}bpm...
```

### 2.3 禁止凭记忆进行对比分析（V5.0新增）

**红线规定**: **严禁凭记忆引用历史数据，所有对比必须基于读取的缓存文件**

**禁止行为**:
```python
# ❌ 严禁 - 凭记忆引用昨日数据
"较昨日52.8ms下降6.4ms"  # 凭记忆，违规！
"较前日2.82小时显著改善"  # 凭记忆，违规！
"较昨日6,853步下降71%"  # 凭记忆，违规！

# ❌ 严禁 - 编造趋势描述
"近期HRV呈下降趋势"  # 无真实历史数据支撑
"本周睡眠质量持续改善"  # 无真实历史数据支撑
```

**正确做法**:

**方案1: 不对比，只分析当日数据（推荐）**
```python
# ✅ 正确 - 只分析当日真实数据
"心率变异性今日为46.4ms，略低于理想区间（50-65ms）。"

# ✅ 正确 - 说明数据局限性
"如需分析趋势，请提供历史数据文件。"
```

**方案2: 读取缓存文件后进行对比**
```python
# ✅ 正确 - 读取缓存文件后再对比
def load_daily_cache(date_str: str) -> dict:
    """加载每日数据缓存"""
    cache_file = CACHE_DIR / f'{date_str}.json'
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

# 读取昨日缓存
yesterday_cache = load_daily_cache('2026-02-18')
if yesterday_cache:
    hrv_diff = today_hrv - yesterday_cache['hrv']['value']
    analysis = f"较昨日{hrv_diff:+.1f}ms"
else:
    analysis = "昨日数据缺失，无法对比"
```

**缓存文件路径**:
```
cache/daily/YYYY-MM-DD.json
```

**缓存文件结构**:
```json
{
  "date": "2026-02-18",
  "hrv": {"value": 52.8, "points": 51},
  "resting_hr": {"value": 57},
  "steps": 6852,
  "sleep": {"total": 2.82, "deep": 0, "core": 0, "rem": 0},
  "workouts": [...]
}
```

**AI分析约束**:

| 场景 | 正确做法 | 错误做法 |
|-----|---------|---------|
| 有缓存文件 | "较昨日下降6.4ms（52.8→46.4）" | - |
| 无缓存文件 | "今日HRV 46.4ms"（不做对比） | "较昨日下降6.4ms"（凭记忆） |
| 多日趋势 | 读取多份缓存后生成趋势分析 | "近期呈下降趋势"（无数据） |

**违规后果**: 数据可信度严重受损，必须重新生成当日报告

---

### 2.4 饮食建议格式（预防可读性差）

**V5.0强制HTML格式**:
```html
<div style="line-height:1.8;">
<strong style="color:#667eea;">【一日三餐方案】</strong><br><br>

<strong>🌅 早餐（7:00-8:00，约400-500千卡）</strong><br>
• 主食：燕麦粥1碗（50g干燕麦）<br>
• 蛋白质：水煮蛋2个 或 牛奶250ml<br>
...
</div>
```

**格式要求**:
- ✅ 行高1.8
- ✅ 彩色标题
- ✅ 表情符号
- ✅ 列表符号
- ✅ 段落间距

---

## 第三步：报告生成（预防模板错误）

### 3.1 强制变量检查（预防未替换变量）

```python
def generate_report(data: dict, ai_analyses: dict, template: str) -> str:
    """V5.0: 生成报告并验证"""
    html = template
    
    # 替换所有变量
    html = html.replace('{{DATE}}', data['date'])
    html = html.replace('{{HRV_VALUE}}', str(data['hrv']['value']))
    html = html.replace('{{AI_HRV_ANALYSIS}}', ai_analyses['hrv'])
    # ... 其他变量
    
    # V5.0: 强制检查未替换变量
    import re
    unreplaced = re.findall(r'\{\{[^}]+\}\}', html)
    if unreplaced:
        print(f"❌ 发现未替换变量: {unreplaced}")
        raise ValueError(f"模板变量未完全替换: {unreplaced}")
    
    return html
```

### 3.2 评分计算标准化（预防评级混乱）

```python
def calc_recovery_score(hrv, resting_hr, sleep_hours) -> int:
    """V5.0: 标准化恢复度评分"""
    score = 70  # 基础分
    if hrv and hrv > 50: score += 10
    if resting_hr and resting_hr < 65: score += 10
    if sleep_hours and sleep_hours > 7: score += 10
    return min(100, score)

def get_rating_class(score: int) -> str:
    """V5.0: 根据评分动态设置CSS类"""
    if score >= 80:
        return 'rating-excellent', 'badge-excellent', '优秀'
    elif score >= 60:
        return 'rating-good', 'badge-good', '良好'
    elif score >= 40:
        return 'rating-average', 'badge-average', '一般'
    else:
        return 'rating-poor', 'badge-poor', '需改善'
```

### 3.3 心率图表生成（预防图表缺失）

```python
def generate_hr_chart(hr_timeline: list) -> str:
    """V5.0: 强制生成Chart.js图表"""
    times = [h['time'] for h in hr_timeline]
    avg_hrs = [h['avg'] for h in hr_timeline]
    max_hrs = [h['max'] for h in hr_timeline]
    
    return f'''<div style="height:200px;width:100%;">
  <canvas id="hrChart"></canvas>
</div>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
  new Chart(document.getElementById('hrChart'), {{
    type: 'line',
    data: {{
      labels: {times},
      datasets: [
        {{label: '平均心率', data: {avg_hrs}, borderColor: '#667eea', ...}},
        {{label: '最高心率', data: {max_hrs}, borderColor: '#dc2626', ...}}
      ]
    }},
    options: {{
      responsive: false,  // V5.0: 必须设置
      maintainAspectRatio: false,
      scales: {{y: {{min: {min(avg_hrs)-10}, max: {max(max_hrs)+10}}}}}
    }}
  }});
</script>'''
```

---

## 第四步：质量验证（强制检查）

### 4.1 V5.0强制验证清单

```python
def verify_report_v5(pdf_path: str) -> bool:
    """V5.0: 完整的报告质量验证"""
    import fitz
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    
    # 1. 检查页数
    assert len(doc) >= 3, "页数不足3页"
    
    # 2. 检查中文显示
    chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
    assert len(chinese_chars) > 100, "中文显示异常"
    
    # 3. 检查关键内容
    required_keywords = ['HRV', '睡眠', '运动', '分析', '建议']
    for keyword in required_keywords:
        assert keyword in text, f"缺少关键内容: {keyword}"
    
    # 4. 检查无模糊词汇
    forbidden = ['良好', '注意', '适当']
    for word in forbidden:
        assert word not in text, f"发现模糊词汇: {word}"
    
    # 5. 检查有具体数值
    import re
    numbers = re.findall(r'\d+\.?\d*\s*(ms|bpm|步|小时|千卡)', text)
    assert len(numbers) > 10, "缺少具体数值引用"
    
    # V5.0 ADD: 6. 检查无编造数据
    # 如果没有睡眠阶段数据，报告中不能出现具体百分比
    if '深睡' in text and ('20%' in text or '50%' in text):
        # 需要结合数据文件检查，这里只是简单示例
        pass
    
    # V5.0 ADD: 7. 检查数据来源标注
    assert '数据来源' in text or 'Apple Health' in text, "缺少数据来源标注"
    
    return True
```

---

## 第五步：交付

### 5.1 命名规范

```
{YYYY-MM-DD}-daily-report-V5-AI.pdf
```

### 5.2 发送前最终检查

```python
def before_send_check(pdf_path: str) -> bool:
    """发送前的最终检查"""
    # 1. 文件存在且大小合理
    assert pdf_path.exists(), "文件不存在"
    assert pdf_path.stat().st_size > 100000, "文件过小（<100KB）"
    
    # 2. 验证PDF内容
    assert verify_report_v5(pdf_path), "质量验证失败"
    
    # 3. 确认AI分析已保存
    cache_path = pdf_path.parent / f"{pdf_path.stem}_ai_analysis.json"
    assert cache_path.exists(), "AI分析缓存未保存"
    
    print("✅ 所有检查通过，可以发送")
    return True
```

---

## 📊 V5.0 vs V4.3 改进总结

| 维度 | V4.3 | V5.0 (修订版) |
|------|------|---------------|
| **分析方式** | 脚本模板填充 | **AI对话分析** |
| **个性化程度** | 低（模板化） | **高（真正理解数据）** |
| **数据验证** | 无 | **强制验证每项数据** |
| **字数控制** | 无 | **强制150-200字/250-300字** |
| **格式优化** | 纯文本 | **HTML格式增强可读性** |
| **图表生成** | 易遗漏 | **强制包含Chart.js** |
| **错误预防** | 事后修复 | **事前预防** |
| **质量验证** | 人工检查 | **自动化验证** |

---

## ✅ V5.0实施检查清单

**每次生成报告前确认**:
- [ ] 在当前AI对话中进行分析（非Subagent）
- [ ] 使用正确的指标名称（`heart_rate_variability`）
- [ ] **验证数据单位**（睡眠是hr不是秒，距离是km不是m）
- [ ] **不编造数据** - 没有真实数据的地方显示"--"
- [ ] **不估算比例** - 睡眠阶段没有数据时不编造百分比
- [ ] **不凭记忆对比** - 历史对比必须读取缓存文件
- [ ] 血氧单位判断正确（>1则不乘100）
- [ ] 睡眠数据使用`sleepStart`字段，**不除以3600**
- [ ] **标注数据来源** - Apple Health / Google Fit
- [ ] AI分析字数达标（150-200/250-300字）
- [ ] AI分析**基于真实数据** - 不编造历史对比
- [ ] 无模糊词汇（"良好""注意"等）
- [ ] 有具体数据引用（"HRV 52.8ms"）
- [ ] 饮食建议使用HTML格式
- [ ] 图表使用`responsive: false`
- [ ] 所有模板变量已替换
- [ ] **无编造数据** - 检查睡眠阶段等数据是否真实
- [ ] **无凭记忆对比** - 检查是否读取了缓存文件
- [ ] 质量验证通过

---

**版本**: V5.0-REVISED-FINAL  
**修订日期**: 2026-02-22  
**修订内容**: 
- 新增：禁止编造数据规则
- 新增：完整11项指标提取清单
- 新增：数据来源追踪要求
- 新增：AI分析真实数据约束
- **新增：禁止凭记忆对比规则（必须读缓存文件）**
