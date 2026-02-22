# 健康报告标准化流程 v4.3

## 🚫 【2026-02-22 新增】绝对禁止规则

### 禁止使用Subagent生成报告

**⚠️ 绝对禁止：使用 `sessions_spawn` 或 `subagent` 生成健康报告**

**原因：**
1. Subagent执行过程无法实时验证，导致错误无法及时发现
2. 数据映射错误、评级颜色缺失、图表未生成等问题无法即时修正
3. 字数要求无法保证达标
4. 多次返工浪费时间和token

**正确做法（强制）：**
```python
# ❌ 绝对禁止
sessions_spawn(task="生成健康报告...")  # 禁止！

# ✅ 必须这样做：在当前会话直接生成
# 1. 读取数据文件并打印验证
# 2. 逐项核对指标映射
# 3. 生成HTML并检查未替换变量
# 4. 转换为PDF并验证页数/内容
# 5. 发送前最终检查
```

**违规后果：** 如果用户使用subagent生成报告，必须：
1. 立即停止并标记为"违规生成"
2. 在当前会话重新生成
3. 报告最终质量责任由当前会话承担

---

## 【2026-02-22 关键修正汇总】⭐⭐⭐⭐⭐

### 本次修正的问题清单

| 问题 | 原因 | 修正方案 |
|------|------|----------|
| **使用Subagent生成报告** | 无法实时验证，导致错误无法及时发现 | **绝对禁止** - 必须在当前会话直接生成 |
| **指标与数值不对应** | 数据映射错误，模板变量填充混乱 | 建立指标-变量名映射表，逐项核对 |
| **评级颜色无区分/缺失** | CSS类名未动态设置或未被应用 | 强制使用rating-excellent/good/average/poor类，生成后验证 |
| **AI分析字数不足** | 未使用标准提示词模板，字数未检查 | 使用流程中的AI提示词，生成后统计字数验证 |
| **图表未生成** | 遗漏Chart.js代码或配置错误 | 强制包含图表代码，设置responsive=false，高度140-200px |
| **睡眠数据逻辑错误** | 未严格按时间窗口筛选，使用错误字段 | 使用sleepStart字段，严格按20:00-次日12:00筛选 |
| HRV显示为0 | 指标名错误：用了`heart_rate_variability_sdnn`，实际是`heart_rate_variability` | 使用正确的指标名称 |
| 血氧显示为0 | 指标名错误：未正确读取`blood_oxygen_saturation` | 使用正确的指标名称 |
| 距离显示为0 | 指标名错误：未正确读取`walking_running_distance` | 使用正确的指标名称 |
| 活动能量显示为0 | 指标名错误：未正确读取`active_energy` | 使用正确的指标名称 |
| 静息能量显示为7kcal | 单位未换算：kJ未转kcal，1702kJ≈7kcal是错的，实际应为1702kcal | kJ ÷ 4.184 = kcal |
| 睡眠结构消失 | 模板填充逻辑错误 | 确保所有睡眠结构占位符被正确替换 |
| 无运动心率图 | 未提取`heartRateData`时序数据 | 添加Chart.js心率曲线图 |
| **锻炼心率数值0但图表正常** | `heartRate.avg/max`为null，未从`heartRateData`计算 | 从`heartRateData`数组计算平均/最大心率 |
| **评级颜色无区分** | CSS类名未动态设置，所有评级使用相同类 | 根据评级值动态设置CSS类（rating-excellent/good/average/poor） |
| AI建议过于笼统 | 使用了简化版建议 | 提供详细的4部分建议（最高/中等/日常/洞察） |
| 数据路径混乱 | 未记录实际数据路径 | 统一记录到TOOLS.md并标准化 |
| Google Fit未读取 | 仅读取Apple Health | 添加Google Fit作为备选数据源 |

---

## 【2026-02-22 新增】数据路径标准化 ⭐⭐⭐⭐⭐

### 强制读取的数据源（优先级顺序）

**每个健康报告生成任务必须按顺序读取以下数据源：**

```python
# 强制数据源读取清单
data_sources = [
    # 1. Apple Health Data (主要数据源)
    '~/我的云端硬盘/Health Auto Export/Health Data/HealthAutoExport-YYYY-MM-DD.json',
    
    # 2. Apple Health Workout Data (运动详细数据)
    '~/我的云端硬盘/Health Auto Export/Workout Data/HealthAutoExport-YYYY-MM-DD.json',
    
    # 3. Google Fit API (备选数据源)
    'Google Fit API: fitness.activity.read, fitness.sleep.read, fitness.heart_rate.read',
]

for source in data_sources:
    read_source(source)  # 必须尝试读取，不存在的记录为null
```

### 1. Apple Health Data 路径

**文件位置**：`~/我的云端硬盘/Health Auto Export/Health Data/`

**文件命名**：`HealthAutoExport-YYYY-MM-DD.json`

**文件大小**：约400-600KB/天

**包含指标**：
- HRV (`heart_rate_variability`)
- 静息心率 (`resting_heart_rate`)
- 步数 (`step_count`)
- 行走距离 (`walking_running_distance`)
- 活动能量 (`active_energy`)
- 静息能量 (`basal_energy_burned`)
- 爬楼层数 (`flights_climbed`)
- 站立时间 (`apple_stand_time`)
- 锻炼时间 (`apple_exercise_time`)
- 血氧 (`blood_oxygen_saturation`)
- 呼吸率 (`respiratory_rate`)
- 睡眠分析 (`sleep_analysis`) ⚠️ 注意：睡眠数据在次日文件

**代码示例**：
```python
import json
from pathlib import Path

def read_apple_health(date_str: str) -> dict:
    """读取Apple Health数据（强制标准化路径）"""
    home = Path.home()
    filepath = home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data' / f'HealthAutoExport-{date_str}.json'
    
    if not filepath.exists():
        raise FileNotFoundError(f"Apple Health数据不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 转换为metrics字典便于访问
    metrics = {m['name']: m for m in data['data']['metrics']}
    
    return {
        'hrv': extract_avg(metrics, 'heart_rate_variability'),
        'resting_hr': extract_avg(metrics, 'resting_heart_rate'),
        'steps': extract_sum(metrics, 'step_count'),
        'distance_km': extract_sum(metrics, 'walking_running_distance'),
        'active_energy_kj': extract_sum(metrics, 'active_energy'),
        'basal_energy_kj': extract_sum(metrics, 'basal_energy_burned'),
        'flights_climbed': extract_sum(metrics, 'flights_climbed'),
        'stand_min': extract_sum(metrics, 'apple_stand_time'),
        'exercise_min': extract_sum(metrics, 'apple_exercise_time'),
        'blood_oxygen': extract_avg_pct(metrics, 'blood_oxygen_saturation'),  # ×100
        'respiratory_rate': extract_avg(metrics, 'respiratory_rate'),
    }

def extract_avg(metrics: dict, name: str) -> float:
    """提取平均值"""
    metric = metrics.get(name, {})
    values = [d['qty'] for d in metric.get('data', []) if 'qty' in d]
    return sum(values) / len(values) if values else 0

def extract_sum(metrics: dict, name: str) -> float:
    """提取总和"""
    metric = metrics.get(name, {})
    return sum(d['qty'] for d in metric.get('data', []) if 'qty' in d)

def extract_avg_pct(metrics: dict, name: str) -> float:
    """提取百分比（值是0-1范围，需要×100）"""
    val = extract_avg(metrics, name)
    return val * 100 if val else 0
```

### 2. Apple Health Workout Data 路径

**文件位置**：`~/我的云端硬盘/Health Auto Export/Workout Data/`

**文件命名**：`HealthAutoExport-YYYY-MM-DD.json`

**注意**：该文件只在有运动的日子存在！

**包含数据**：
- 运动类型 (`name`)
- 开始/结束时间 (`start`, `end`)
- 持续时间 (`duration`)
- 消耗能量 (`activeEnergy`)
- 心率统计 (`heartRate`)
- **心率时序数据** (`heartRateData`) ⭐ 用于生成图表
- 步数 (`stepCount`)
- 心率恢复数据 (`heartRateRecovery`)

**代码示例**：
```python
def read_workout_data(date_str: str) -> list:
    """读取Workout数据（可能不存在）"""
    home = Path.home()
    filepath = home / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data' / f'HealthAutoExport-{date_str}.json'
    
    if not filepath.exists():
        return []  # 当日无运动
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    workouts = data.get('data', {}).get('workouts', [])
    
    result = []
    for w in workouts:
        # 提取能量（kJ转kcal）
        energy_list = w.get('activeEnergy', [])
        total_kj = sum(e.get('qty', 0) for e in energy_list) if isinstance(energy_list, list) else 0
        
        # 提取心率时序数据
        hr_data = w.get('heartRateData', [])
        hr_times = []
        hr_avg = []
        hr_max = []
        
        for hr in hr_data:
            time_str = hr['date'].split(' ')[1][:5]  # HH:MM
            hr_times.append(time_str)
            hr_avg.append(round(hr.get('Avg', 0)))
            hr_max.append(hr.get('Max', 0))
        
        result.append({
            'name': w.get('name', '未知运动'),
            'start': w.get('start', '')[:19],
            'end': w.get('end', '')[:19],
            'duration_min': w.get('duration', 0) / 60,
            'energy_kcal': total_kj / 4.184,
            'avg_hr': w.get('heartRate', {}).get('avg', {}).get('qty'),
            'max_hr': w.get('heartRate', {}).get('max', {}).get('qty'),
            'min_hr': w.get('heartRate', {}).get('min', {}).get('qty'),
            'hr_times': hr_times,
            'hr_avg': hr_avg,
            'hr_max': hr_max,
            'hr_data_points': len(hr_data),
        })
    
    return result
```

### 3. Google Fit API 路径

**API端点**：`https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate`

**数据源ID**：
- 步数：`derived:com.google.step_count.delta`
- 距离：`derived:com.google.distance.delta`
- 卡路里：`derived:com.google.calories.expended`
- 心率：`derived:com.google.heart_rate.bpm`
- 睡眠：`derived:com.google.sleep.segment`

**代码示例**：
```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

def read_google_fit(date_str: str) -> dict:
    """读取Google Fit数据（作为Apple Health的备选）"""
    # 时间范围：当日15:00至次日12:00
    date = datetime.strptime(date_str, "%Y-%m-%d")
    start_time = date.replace(hour=15, minute=0).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    end_time = (date + timedelta(days=1)).replace(hour=12, minute=0).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    # 使用OAuth2认证
    creds = Credentials.from_authorized_user_file('~/.openclaw/credentials/google-fit-token.json')
    service = build('fitness', 'v1', credentials=creds)
    
    # 读取步数
    steps_data = service.users().dataset().aggregate(
        userId='me',
        body={
            'aggregateBy': [{'dataTypeName': 'com.google.step_count.delta'}],
            'bucketByTime': {'durationMillis': 86400000},
            'startTimeMillis': int(datetime.fromisoformat(start_time.replace('Z', '+00:00')).timestamp() * 1000),
            'endTimeMillis': int(datetime.fromisoformat(end_time.replace('Z', '+00:00')).timestamp() * 1000),
        }
    ).execute()
    
    # 提取步数
    steps = 0
    for bucket in steps_data.get('bucket', []):
        for dataset in bucket.get('dataset', []):
            for point in dataset.get('point', []):
                steps = point.get('value', [{}])[0].get('intVal', 0)
    
    return {
        'steps': steps,
        # ... 其他指标
    }
```

### 4. 睡眠数据特殊处理

**重要**：Apple Health的睡眠数据记录在**次日文件**中！

```python
def read_sleep_data(date_str: str) -> dict:
    """读取睡眠数据（从次日文件）"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    home = Path.home()
    filepath = home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data' / f'HealthAutoExport-{next_date}.json'
    
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data['data']['metrics']}
    sleep = metrics.get('sleep_analysis', {})
    
    if not sleep or not sleep.get('data'):
        return None
    
    s = sleep['data'][0]
    
    # 检查睡眠是否属于目标日期（入睡时间在当日20:00至次日12:00之间）
    sleep_start = datetime.fromisoformat(s.get('sleepStart', '').replace(' +0800', '+08:00'))
    window_start = date.replace(hour=20, minute=0)
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)
    
    if window_start <= sleep_start <= window_end:
        return {
            'total': s.get('asleep', 0),
            'deep': s.get('deep', 0),
            'core': s.get('core', 0),
            'rem': s.get('rem', 0),
            'awake': s.get('awake', 0),
            'sleep_start': s.get('sleepStart', ''),
            'sleep_end': s.get('sleepEnd', ''),
            'source_file': str(filepath),
        }
    
    return None
```

### 5. 数据路径检查清单

生成报告前必须确认：

```python
def validate_data_paths(date_str: str) -> dict:
    """验证所有数据路径"""
    home = Path.home()
    
    paths = {
        'health_data': home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data' / f'HealthAutoExport-{date_str}.json',
        'workout_data': home / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data' / f'HealthAutoExport-{date_str}.json',
        'sleep_data': home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data' / f'HealthAutoExport-{datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1):%Y-%m-%d}.json',
    }
    
    results = {}
    for name, path in paths.items():
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        results[name] = {
            'path': str(path),
            'exists': exists,
            'size_kb': size / 1024,
        }
        print(f"{'✅' if exists else '❌'} {name}: {path} ({size/1024:.1f} KB)")
    
    return results
```

### 6. 工具文件记录

**必须在 `TOOLS.md` 中记录实际路径**：

```markdown
## Health Data Paths

### Apple Health Export
- **Health Data**: `~/我的云端硬盘/Health Auto Export/Health Data/`
  - Format: `HealthAutoExport-YYYY-MM-DD.json`
  - Size: ~400-600KB per day
  
- **Workout Data**: `~/我的云端硬盘/Health Auto Export/Workout Data/`
  - Format: `HealthAutoExport-YYYY-MM-DD.json`
  - Only exists on days with workouts

### Google Fit API
- Credentials: `~/.openclaw/credentials/google-fit-token.json`
- Endpoints: `fitness.activity.read`, `fitness.sleep.read`, `fitness.heart_rate.read`

### Available Dates
- 2026-02-18: Health (657KB) + Workout (29KB) ✓
- 2026-02-19: Health (443KB)
- 2026-02-20: Health (459KB)
- 2026-02-21: Health (242KB)

### Data Sources Priority
1. Apple Health (primary)
2. Google Fit (backup for sleep if Apple Health missing)
```

### 正确的指标名称映射表（Apple Health）

| 指标 | 正确的指标名称 | 单位 | 换算 |
|------|---------------|------|------|
| HRV | `heart_rate_variability` | ms | 无 |
| 静息心率 | `resting_heart_rate` | count/min | 无 |
| 步数 | `step_count` | count | 无 |
| 行走距离 | `walking_running_distance` | km | 无 |
| 活动能量 | `active_energy` | kJ | ÷ 4.184 → kcal |
| 爬楼层数 | `flights_climbed` | count | 无 |
| 站立时间 | `apple_stand_time` | min | ÷ 60 → hour |
| 血氧饱和度 | `blood_oxygen_saturation` | % | 值是0-1，×100显示为% |
| 呼吸率 | `respiratory_rate` | count/min | 无 |
| 静息能量 | `basal_energy_burned` | kJ | ÷ 4.184 → kcal |
| 睡眠分析 | `sleep_analysis` | hr | 无 |

### 关键数据提取代码（修正版）

```python
def extract_health_metrics_correct(date_str):
    """正确提取Apple Health指标（2026-02-22修正版）"""
    filepath = f"HealthAutoExport-{date_str}.json"
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data['data']['metrics']}
    
    # 1. HRV - 正确的指标名
    hrv_metric = metrics.get('heart_rate_variability')
    hrv_values = [d['qty'] for d in hrv_metric['data'] if d.get('qty')]
    hrv_avg = sum(hrv_values) / len(hrv_values) if hrv_values else 0
    
    # 2. 血氧 - 值是0-1范围，需要×100显示
    spo2_metric = metrics.get('blood_oxygen_saturation')
    spo2_values = [d['qty'] for d in spo2_metric['data'] if d.get('qty')]
    spo2_avg = (sum(spo2_values) / len(spo2_values) * 100) if spo2_values else 0
    
    # 3. 活动能量 - kJ转kcal
    energy_metric = metrics.get('active_energy')
    energy_kj = sum(d['qty'] for d in energy_metric['data'] if d.get('qty'))
    energy_kcal = energy_kj / 4.184
    
    # 4. 静息能量 - kJ转kcal（修正：之前显示7是因为忘了换算！）
    resting_metric = metrics.get('basal_energy_burned')
    resting_kj = sum(d['qty'] for d in resting_metric['data'] if d.get('qty'))
    resting_kcal = resting_kj / 4.184  # 正确：1702kcal，不是7kcal
    
    # 5. 行走距离 - 直接使用，已经是km
    distance_metric = metrics.get('walking_running_distance')
    distance_km = sum(d['qty'] for d in distance_metric['data'] if d.get('qty'))
    
    return {
        'hrv': hrv_avg,
        'spo2': spo2_avg,
        'energy_kcal': energy_kcal,
        'resting_energy_kcal': resting_kcal,
        'distance_km': distance_km,
        # ... 其他指标
    }
```

### Workout Data 正确提取（2026-02-22修正版）

```python
def extract_workout_data_correct(date_str):
    """正确提取锻炼数据（2026-02-22修正版）"""
    filepath = f"Workout Data/HealthAutoExport-{date_str}.json"
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # 注意：data.workouts 是数组，不是 data 直接是数组
    workouts = data.get('data', {}).get('workouts', [])
    
    result = []
    for w in workouts:
        # 能量：activeEnergy 是数组，需要求和并转千卡
        energy_list = w.get('activeEnergy', [])
        total_kj = sum(e.get('qty', 0) for e in energy_list) if isinstance(energy_list, list) else 0
        total_kcal = total_kj / 4.184
        
        # 心率：heartRate 是字典，包含 avg/min/max
        hr = w.get('heartRate', {})
        avg_hr = hr.get('avg', {}).get('qty') if isinstance(hr, dict) else None
        max_hr = hr.get('max', {}).get('qty') if isinstance(hr, dict) else None
        
        # 心率时序数据
        hr_timeline = w.get('heartRateData', [])
        
        result.append({
            'name': w.get('name', '未知运动'),
            'duration_min': round(w.get('duration', 0) / 60, 1),
            'energy_kcal': total_kcal if total_kcal > 0 else None,
            'avg_hr': avg_hr,
            'max_hr': max_hr,
            'hr_timeline': hr_timeline  # 用于绘制心率图
        })
    
    return result
```

### 运动心率图表生成代码

```python
def generate_hr_chart_html(hr_timeline):
    """生成心率图表HTML（使用Chart.js）"""
    if not hr_timeline:
        return "<p>无心率时序数据</p>"
    
    # 提取数据
    times = [hr['date'].split(' ')[1][:5] for hr in hr_timeline]
    avg_hrs = [round(hr['Avg']) for hr in hr_timeline]
    max_hrs = [hr['Max'] for hr in hr_timeline]
    min_hrs = [hr['Min'] for hr in hr_timeline]
    
    html = f"""
    <div style="margin: 15px 0;">
        <canvas id="hrChart" width="700" height="180"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        new Chart(document.getElementById('hrChart'), {{
            type: 'line',
            data: {{
                labels: {times},
                datasets: [
                    {{
                        label: '平均心率',
                        data: {avg_hrs},
                        borderColor: '#667eea',
                        backgroundColor: 'rgba(102, 126, 234, 0.1)',
                        fill: true,
                        tension: 0.4
                    }},
                    {{
                        label: '最高心率',
                        data: {max_hrs},
                        borderColor: '#dc2626',
                        borderDash: [5, 5],
                        pointRadius: 2
                    }}
                ]
            }},
            options: {{
                responsive: false,
                scales: {{
                    y: {{ beginAtZero: false, min: 100, title: {{ display: true, text: '心率 (bpm)' }} }},
                    x: {{ ticks: {{ maxTicksLimit: 8 }} }}
                }}
            }}
        }});
    </script>
    """
    return html
```

### 详细AI建议模板（4部分，每部分200-300字）

```python
# 最高优先级（睡眠问题示例）
ai_high_priority = f"""
<strong>问题识别：</strong>昨晚睡眠仅{sleep_hours:.1f}小时，远低于推荐值7-9小时。
睡眠不足会严重影响身体恢复、认知功能和免疫系统。

<strong>行动计划：</strong>
1. 今晚提前90分钟入睡（如平时23:30睡，今晚22:00前上床）
2. 睡前准备（21:00开始）：调暗灯光，停止工作，避免蓝光
3. 助眠措施：尝试478呼吸法（吸气4秒、屏息7秒、呼气8秒）
4. 明日安排：如条件允许，午休20-30分钟
5. 恢复训练：明日降低运动强度，改为轻度活动

<strong>预期效果：</strong>通过今晚的充足睡眠，明日HRV应有所提升，
连续3天保证7小时以上睡眠后，身体恢复度评分应从50分提升至70分以上。
"""

# 中等优先级（运动恢复示例）
ai_medium_priority = f"""
<strong>问题分析：</strong>今日进行了{duration}分钟高强度锻炼，
消耗{energy}千卡，平均心率{avg_hr}bpm。高强度运动后身体需要充分恢复。

<strong>具体建议：</strong>
1. 水分补充：确保全天饮水2.5-3升，观察尿液颜色保持淡黄色
2. 营养摄入：晚餐包含优质蛋白质150-200g和复合碳水
3. 拉伸放松：睡前进行10-15分钟下肢拉伸，每个动作30秒
4. 明日活动：改为低强度活动，心率控制在120bpm以下
5. 疲劳监测：明日晨起测量静息心率，如比平常高5bpm以上应继续休息

<strong>恢复周期：</strong>通过充分的水分和营养补充，配合优质睡眠，
24-48小时内应感到肌肉酸痛明显减轻。
"""
```

---

## 🎨 UI模板规范（2026-02-22 更新）⭐⭐⭐⭐⭐

### 【2026-02-22 新增】中文字体强制保障

**必须在HTML中包含以下字体声明**：
```css
body {
  font-family:
    'PingFang SC',           /* macOS首选 */
    'Microsoft YaHei',       /* Windows首选 */
    'Noto Sans SC',          /* Linux/通用 */
    'Source Han Sans SC',    /* Adobe开源 */
    -apple-system,
    BlinkMacSystemFont,
    sans-serif;
}
```

**生成PDF后必须验证中文显示**：
```python
def verify_chinese_in_pdf(pdf_path):
    """验证PDF中中文是否正常显示"""
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    page = doc[0]
    text = page.get_text()
    
    # 检查是否包含中文字符
    chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
    if len(chinese_chars) < 10:
        raise ValueError("PDF中文显示异常，可能字体缺失")
    
    print(f"✅ PDF中文验证通过: 检测到{len(chinese_chars)}个中文字符")
    return True
```

### 【绝对强制】必须使用V2统一模板

**🚫 禁止行为（红线）：**
- 禁止每次生成报告时重新编写HTML/CSS
- 禁止修改模板的颜色、字体、布局
- 禁止使用不同的样式文件
- 禁止sub-agent自行决定UI样式
- **禁止不使用V2模板**（旧模板已废弃）

**✅ 必须使用V2模板：**
```python
# 读取V2统一模板（强制执行）
template_path = '~/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html'
with open(template_path, 'r', encoding='utf-8') as f:
    template = f.read()

# 验证模板关键特征
assert '667eea' in template, "模板错误：必须是紫色V2模板"
assert 'PingFang SC' in template or 'Microsoft YaHei' in template, "模板错误：缺少中文字体"
assert '{{DATE}}' in template, "模板错误：缺少占位符"

# 填充数据（仅修改内容，不改变结构）
html = template.replace('{{DATE}}', date_str)
html = html.replace('{{HRV_VALUE}}', str(hrv_value))
# ... 其他变量替换

# 生成PDF
generate_pdf(html, output_path)
```

### 模板文件路径（必须使用V2版本）

| 报告类型 | 模板文件 | 颜色主题 |
|---------|---------|---------|
| **日报告** | `templates/DAILY_TEMPLATE_V2.html` | 紫色渐变 `#667eea → #764ba2` |
| **周报告** | `templates/WEEKLY_TEMPLATE_V2.html` | 蓝色渐变 `#3b82f6 → #1d4ed8` |
| **月报告** | `templates/MONTHLY_TEMPLATE_V2.html` | 紫红色 `#7c3aed → #db2777` |

### 模板关键规范

**1. 日报告模板（DAILY_TEMPLATE.html）**
- 头部：紫色渐变背景
- 评分卡：3列网格，带颜色标签（优秀/良好/一般/不足）
- 指标表：4列（指标/数值/评级/AI分析）
- 睡眠分析：第二页开始（`page-break`）
- AI建议：第三页
- 页脚：数据来源标注

**2. 周报告模板（WEEKLY_TEMPLATE.html）**
- 头部：蓝色渐变背景
- 数据进度警告：黄色框（数据不足）/绿色框（数据完整）
- 统计卡片：3列网格
- 数据表：每日明细
- AI分析：周总结+优势风险+下周建议

**3. 月报告模板（MONTHLY_TEMPLATE.html）**
- 头部：紫红色渐变背景
- 数据进度警告：红色框（数据不足）/绿色框（数据完整）
- 统计卡片：4列网格
- 月度推算框：绿色背景
- AI分析：月度总结+长期趋势+月度目标

### 检查清单（生成报告时必须确认）

- [ ] 使用了正确的模板文件（日/周/月）
- [ ] 没有修改模板的CSS样式
- [ ] 仅替换了`{{VARIABLE}}`内容变量
- [ ] 页面布局与模板一致
- [ ] 颜色主题与模板定义一致

---

## 📋 报告类型

### 1. 单日完整报告（标准版）
- 针对单日的详细健康分析
- 包含所有指标、建议、饮食、备注
- 输出格式：PDF (A4)

### 2. 单日详细分析报告（推荐版）⭐
- **包含所有指标的AI评级和深度分析**
- **Workout Data 运动数据完整展示**
- **心率曲线图**
- **睡眠结构详细分解**
- 分优先级的详细AI建议
- 整体健康评估洞察
- 输出格式：PDF (A4)

### 3. 对比报告
- 两日数据对比分析
- 保持指标一致性
- 显示当前日期的建议
- 输出格式：PDF (A4)

### 4. 周报告/月报告（新增）⭐⭐⭐

**核心规则：周/月报告必须从缓存读取数据，禁止重新解析原始JSON文件**

**原因**：
- 原始JSON文件450KB/天，缓存仅0.5KB/天（节省99.9%存储和token）
- 避免重复解析大文件，周报告7天仅需3.5KB而非3.15MB
- 保证数据一致性（日报和周/月报告使用相同数据源）

**数据来源**：每日缓存文件 `cache/daily/YYYY-MM-DD.json`

**正确做法**：
```python
# ✅ 正确：从缓存读取
def generate_weekly_report(week_dates):
    weekly_data = []
    for date_str in week_dates:
        cache = load_cache(f'cache/daily/{date_str}.json')
        weekly_data.append(cache)
    # 计算统计并生成报告
    
# ❌ 禁止：重新解析原始JSON
def generate_weekly_report_wrong(week_dates):
    for date_str in week_dates:
        raw_data = json.load(open(f'HealthAutoExport-{date_str}.json'))  # 禁止！
```

**报告内容**：
- 周报：7日趋势分析、平均值计算、运动频率统计
- 月报：月度健康评分、长期趋势、改善建议
- 输出格式：PDF (A4)

---

## 🗄️ 每日数据缓存方案（2026-02-21 新增）⭐⭐⭐

**目的**：
1. 避免重复读取大JSON文件（节省99.9%存储和token）
2. 方便快速生成周报告、月报告
3. 支持长期趋势分析

**方案设计**：

### 1. 缓存文件结构
```
~/.openclaw/workspace-health/cache/daily/
├── 2026-02-18.json   # 每日缓存（~0.5KB）
├── 2026-02-19.json
├── 2026-02-20.json
└── ...
```

### 2. 缓存数据格式（非常简洁）
```json
{
  "date": "2026-02-20",
  "hrv": {"value": 53.4, "points": 35},
  "resting_hr": {"value": 63.0, "points": 1},
  "steps": {"value": 6230, "points": 136},
  "distance": {"value": 4.34, "points": 136},
  "active_energy": {"value": 213.6, "points": 451},
  "sleep": {
    "total": 7.59,
    "deep": 1.85,
    "core": 3.63,
    "rem": 2.11,
    "awake": 0.05
  },
  "sleep_source": "2026-02-21",
  "has_workout": false,
  "workout_count": 0,
  "workouts": [],
  "cached_at": "2026-02-21T22:30:00"
}
```

### 3. 文件大小对比
| 文件类型 | 大小 | 说明 |
|---------|------|------|
| 原始 Apple Health JSON | ~450 KB | 包含所有原始数据点 |
| **每日缓存 JSON** | **~0.5 KB** | **仅包含关键指标（节省99.9%）** |

### 4. 缓存生成流程（每日报告生成时自动执行）

**强制规则：每次生成日报后，必须保存缓存文件**

```python
def generate_daily_report(date_str):
    """生成日报的标准流程"""
    
    # 1. 读取原始数据（Apple Health + Workout + Google Fit）
    raw_data = extract_all_data(date_str)
    
    # 2. 【强制】提取关键指标并保存缓存
    cache_data = {
        'date': date_str,
        'generatedAt': datetime.now().isoformat(),
        'metrics': {
            'hrv': {
                'value': round(raw_data['hrv'], 2),
                'unit': 'ms',
                'dataPoints': raw_data['hrv_n'],
                'min': raw_data['hrv_min'],
                'max': raw_data['hrv_max']
            },
            'restingHeartRate': {
                'value': raw_data['resting_hr'],
                'unit': 'bpm',
                'dataPoints': raw_data['resting_hr_n']
            },
            'steps': {
                'value': raw_data['steps'],
                'unit': '步',
                'dataPoints': raw_data['steps_n']
            },
            'activeEnergy': {
                'value': round(raw_data['active_kcal']),
                'unit': 'kcal',
                'originalUnit': 'kJ',
                'originalValue': raw_data['active_kj'],
                'dataPoints': raw_data['active_n']
            },
            'bloodOxygen': {
                'value': round(raw_data['blood_oxygen'], 1),
                'unit': '%',
                'dataPoints': raw_data['bo_n'],
                'min': raw_data['bo_min'],
                'max': raw_data['bo_max']
            },
            'respiratoryRate': {
                'value': round(raw_data['respiratory'], 1),
                'unit': '次/分钟',
                'dataPoints': raw_data['resp_n'],
                'min': raw_data['resp_min'],
                'max': raw_data['resp_max']
            },
            'floorsClimbed': {
                'value': raw_data['flights'],
                'unit': '层',
                'dataPoints': raw_data['flights_n']
            },
            'distance': {
                'value': round(raw_data['distance'], 2),
                'unit': 'km',
                'dataPoints': raw_data['distance_n']
            },
            'sleep': {
                'totalSleep': raw_data['sleep_total'],
                'deep': raw_data['sleep_deep'],
                'core': raw_data['sleep_core'],
                'rem': raw_data['sleep_rem'],
                'awake': raw_data['sleep_awake'],
                'count': 1 if raw_data['sleep_total'] > 0 else 0
            }
        },
        'workout': {
            'hasWorkout': raw_data['has_workout'],
            'type': raw_data.get('workout_type', ''),
            'duration': raw_data.get('workout_duration', 0),
            'caloriesKJ': raw_data.get('workout_kj', 0),
            'caloriesKcal': raw_data.get('workout_kcal', 0),
            'avgHR': raw_data.get('workout_avg_hr', 0),
            'maxHR': raw_data.get('workout_max_hr', 0),
            'minHR': raw_data.get('workout_min_hr', 0),
            'hrDataPoints': raw_data.get('workout_hr_points', 0)
        }
    }
    
    # 【强制】保存缓存
    cache_path = f'cache/daily/{date_str}.json'
    save_json(cache_data, cache_path)
    print(f"✓ 缓存已保存: {cache_path} ({len(json.dumps(cache_data))} bytes)")
    
    # 3. 生成日报PDF
    generate_pdf(raw_data)
    
    return cache_data
```

### 5. 周报告生成流程（必须从缓存读取）

**⚠️ 强制规则：周报告必须使用缓存，禁止读取原始JSON**

```python
def generate_weekly_report(week_dates):
    """
    生成周报告 - 必须从缓存读取数据
    
    Args:
        week_dates: 日期列表，如 ['2026-02-18', '2026-02-19', ...]
    
    Returns:
        PDF文件路径
    """
    weekly_data = []
    missing_cache = []
    
    for date_str in week_dates:
        cache_path = f'cache/daily/{date_str}.json'
        
        # ✅ 直接读取缓存（0.5KB）
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            weekly_data.append(cache)
            print(f"✓ 从缓存读取: {date_str}")
        else:
            # 如果缓存不存在，先生成缓存（但这种情况应该避免）
            missing_cache.append(date_str)
            print(f"⚠️ 缓存不存在: {date_str}")
    
    if missing_cache:
        raise FileNotFoundError(
            f"以下日期缺少缓存: {missing_cache}\n"
            f"请先生成这些日期的日报，或手动生成缓存。"
        )
    
    # 计算周统计
    week_stats = {
        'avg_hrv': sum(d['metrics']['hrv']['value'] for d in weekly_data) / len(weekly_data),
        'total_steps': sum(d['metrics']['steps']['value'] for d in weekly_data),
        'avg_steps': sum(d['metrics']['steps']['value'] for d in weekly_data) / len(weekly_data),
        'avg_sleep': sum(d['metrics']['sleep']['totalSleep'] for d in weekly_data 
                        if d['metrics']['sleep']['totalSleep'] > 0) / 
                     len([d for d in weekly_data if d['metrics']['sleep']['totalSleep'] > 0]),
        'workout_days': sum(1 for d in weekly_data if d['workout']['hasWorkout']),
        'rest_days': len(weekly_data) - sum(1 for d in weekly_data if d['workout']['hasWorkout']),
        'total_energy': sum(d['metrics']['activeEnergy']['value'] for d in weekly_data),
        'avg_energy': sum(d['metrics']['activeEnergy']['value'] for d in weekly_data) / len(weekly_data),
    }
    
    # 生成周报告PDF
    pdf_path = generate_weekly_pdf(week_stats, weekly_data)
    
    print(f"✓ 周报告生成完成: {pdf_path}")
    print(f"  - 数据天数: {len(weekly_data)}")
    print(f"  - 总步数: {week_stats['total_steps']:,}")
    print(f"  - 运动天数: {week_stats['workout_days']}")
    
    return pdf_path

# 使用示例
try:
    report = generate_weekly_report(['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21'])
except FileNotFoundError as e:
    print(f"错误: {e}")
```

### 6. 月报告生成流程（必须从缓存读取）

**⚠️ 强制规则：月报告必须使用缓存，禁止读取原始JSON**

```python
def generate_monthly_report(year, month, available_dates=None):
    """
    生成月报告 - 必须从缓存读取数据
    
    流程：
    1. 检查当月所有日期的缓存
    2. 计算数据覆盖率
    3. 根据覆盖率决定报告类型（完整版/预览版）
    4. 从缓存读取数据并生成报告
    
    Args:
        year: 年份
        month: 月份
        available_dates: 可用日期列表（可选，默认扫描缓存目录）
    
    Returns:
        (report_type, pdf_path): 报告类型和文件路径
    """
    import os
    from calendar import monthrange
    
    # 1. 获取当月所有日期
    _, last_day = monthrange(year, month)
    all_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
    
    # 2. 检查哪些日期有缓存
    if available_dates is None:
        available_dates = []
        for date_str in all_dates:
            cache_path = f'cache/daily/{date_str}.json'
            if os.path.exists(cache_path):
                available_dates.append(date_str)
    
    # 3. 计算覆盖率
    total_days = len(all_dates)
    available_count = len(available_dates)
    coverage = available_count / total_days
    
    print(f"数据覆盖率: {available_count}/{total_days}天 ({coverage*100:.1f}%)")
    
    # 4. 根据覆盖率决定报告类型
    if coverage < 0.25:  # <7天
        raise ValueError(
            f"数据覆盖率仅{coverage*100:.1f}%，不足以生成有意义的月报告。"
            f"请先生成更多日期的日报。"
        )
    elif coverage < 0.50:  # 7-14天
        report_type = 'partial'
        alert_class = 'warning'
        alert_text = f'⚠️ 部分数据报告：{available_count}/{total_days}天（{coverage*100:.0f}%）'
    elif coverage < 0.90:  # 15-24天
        report_type = 'preview'
        alert_class = 'warning'
        alert_text = f'⚠️ 数据预览版：{available_count}/{total_days}天（{coverage*100:.0f}%）'
    else:  # ≥25天
        report_type = 'full'
        alert_class = 'complete'
        alert_text = f'✅ 数据完整：{available_count}/{total_days}天'
    
    # 5. 从缓存读取数据（禁止读取原始JSON！）
    monthly_data = []
    for date_str in available_dates:
        cache_path = f'cache/daily/{date_str}.json'
        with open(cache_path, 'r') as f:
            cache = json.load(f)
        monthly_data.append(cache)
    
    # 6. 计算月统计
    valid_sleep_days = [d for d in monthly_data if d['metrics']['sleep']['totalSleep'] > 0]
    
    month_stats = {
        'avg_hrv': sum(d['metrics']['hrv']['value'] for d in monthly_data) / len(monthly_data),
        'total_steps': sum(d['metrics']['steps']['value'] for d in monthly_data),
        'avg_steps': sum(d['metrics']['steps']['value'] for d in monthly_data) / len(monthly_data),
        'avg_sleep': sum(d['metrics']['sleep']['totalSleep'] for d in valid_sleep_days) / len(valid_sleep_days) if valid_sleep_days else 0,
        'workout_days': sum(1 for d in monthly_data if d['workout']['hasWorkout']),
        'total_energy': sum(d['metrics']['activeEnergy']['value'] for d in monthly_data),
        'avg_energy': sum(d['metrics']['activeEnergy']['value'] for d in monthly_data) / len(monthly_data),
        'data_coverage': coverage,
        'available_days': available_count,
        'total_days': total_days,
        'missing_dates': [d for d in all_dates if d not in available_dates]
    }
    
    # 7. 生成月报告PDF
    pdf_path = generate_monthly_pdf(
        month_stats, 
        monthly_data,
        report_type=report_type,
        alert_class=alert_class,
        alert_text=alert_text
    )
    
    print(f"✓ 月报告生成完成: {pdf_path}")
    print(f"  - 报告类型: {report_type}")
    print(f"  - 数据天数: {available_count}/{total_days}")
    print(f"  - 日均步数: {month_stats['avg_steps']:,.0f}")
    
    return report_type, pdf_path

# 使用示例
try:
    report_type, path = generate_monthly_report(2026, 2)
    print(f"✅ 已生成{report_type}报告: {path}")
except ValueError as e:
    print(f"❌ {e}")
```

### 7. 优势总结

| 对比项 | 传统方式（读原始JSON） | 缓存方式 | 节省 |
|--------|---------------------|---------|------|
| 日报存储 | 450 KB/天 | 0.5 KB/天 | 99.9% |
| 周报告读取 | 3.15 MB (7天) | 3.5 KB (7天) | 99.9% |
| 月报告读取 | 13.5 MB (30天) | 15 KB (30天) | 99.9% |
| Token消耗 | 高（解析大JSON） | 极低（读小缓存） | ~95% |
| 生成速度 | 慢 | 快 | 10倍+ |
| 数据一致性 | 可能不一致 | 完全一致 | ✅ |

**关键原则**：
1. ✅ 日报生成时必须保存缓存
2. ✅ 周/月报告必须从缓存读取
3. ❌ 禁止周/月报告直接读取原始JSON
4. ❌ 禁止重复解析大文件

---

## 🕐 时区规则

**统一使用 UTC+8 (北京时间)**

- 所有时间显示必须带时区标注
- 格式：`HH:MM (UTC+8)` 或 `YYYY-MM-DD HH:MM UTC+8`
- 睡眠数据转换：
  ```python
  from datetime import datetime, timezone, timedelta
  utc8 = timezone(timedelta(hours=8))
  local_time = utc_time.astimezone(utc8)
  ```

---

## 📊 数据来源

### 数据源优先级规则

**当多个数据源有同一指标时，按以下优先级选择**：

| 指标类别 | 第一优先级 | 第二优先级 | 说明 |
|----------|------------|------------|------|
| **睡眠数据** | **Apple Health**（次日文件，方案D） | **Google Fit** | Apple Health 提供详细睡眠结构，但需从次日文件提取 |
| **HRV/静息心率** | Apple Health | - | Apple Watch 测量最准确 |
| **步数/距离** | Apple Health | **Google Fit** | Apple Health 更实时，Google Fit 作为备选验证 |
| **活动能量** | Apple Health | **Google Fit** | Apple Health 包含更多细节，Google Fit 作为备选 |
| **运动数据** | Workout Data | Apple Health | Workout Data 有心率时序 |
| **血氧/呼吸率** | Apple Health | - | Apple Watch 专用传感器 |

**【2026-02-21 关键修正】数据源读取规则**：

### 1. 行走距离单位（已修正）
```python
# ❌ 错误：Apple Health 的 walking_running_distance 已经是 km，不需要再除以 1000
'distance': round(distance / 1000, 2)  # 错误！会导致 4.34km 显示为 0.00km

# ✅ 正确：直接使用原始值
'distance': round(distance, 2)  # 正确：4.34km 保持为 4.34km
```

### 2. 永远读取 Google Fit 作为备选
```python
# 必须执行的步骤：
1. 读取 Apple Health 主数据
2. 读取 Google Fit 数据作为备选
3. 如果 Apple Health 缺失某项数据，使用 Google Fit 补充
4. 在报告中标注数据来源（Apple Health / Google Fit）
```

### 3. 删除所有估算值（禁止行为）
```python
# ❌ 禁止：使用估算值
sleep_total = 6.0 + (hrv - 45) * 0.05  # 禁止！禁止基于其他指标估算

# ✅ 正确：只使用实际数据
sleep_total = sleep_data.get('totalSleep', 0)  # 从文件读取实际值
if sleep_total == 0:
    sleep_display = "数据缺失"  # 明确标注缺失，不使用估算
```

**冲突解决规则**:
```python
# 睡眠数据：Apple Health 优先（次日文件），Google Fit 备选
sleep_data = extract_apple_health_sleep(date_str)  # 从次日文件提取
if not sleep_data:
    sleep_data = fetch_google_fit_sleep(date_str)  # 使用 Google Fit
if not sleep_data:
    sleep_data = None  # 标记为未记录，禁止估算

# 步数/距离：Apple Health 优先，Google Fit 验证
steps = apple_health_steps  # 主数据源
if google_fit_steps and abs(google_fit_steps - apple_health_steps) > 1000:
    print(f"⚠️  数据差异警告: Apple={apple_health_steps}, Google Fit={google_fit_steps}")
```

### 1. Health Data（健康数据）
**路径**: `~/Health Auto Export/Health Data/HealthAutoExport-YYYY-MM-DD.json`

| 指标 | name | 单位 | 重要性 |
|------|------|------|--------|
| HRV | `heart_rate_variability` | ms | ⭐⭐⭐ 高 |
| 静息心率 | `resting_heart_rate` | bpm | ⭐⭐⭐ 高 |
| 全天心率 | `heart_rate` | bpm (Min/Max/Avg) | ⭐⭐⭐ 高 |
| 步数 | `step_count` | count | ⭐⭐⭐ 高 |
| 活动能量 | `active_energy` | kJ → kcal | ⭐⭐⭐ 高 |
| **血氧** | `blood_oxygen_saturation` | % | ⭐⭐⭐ **新增** |
| **呼吸率** | `respiratory_rate` | count/min | ⭐⭐⭐ **新增** |
| **爬楼层** | `flights_climbed` | count | ⭐⭐ **新增** |
| **站立时间** | `apple_stand_time` | min | ⭐⭐ **新增** |
| **站立小时** | `apple_stand_hour` | count | ⭐⭐ **新增** |
| **步行速度** | `walking_speed` | km/hr | ⭐⭐ **新增** |
| **步长** | `walking_step_length` | cm | ⭐ **新增** |
| **距离** | `walking_running_distance` | km | ⭐⭐ **新增** |
| 睡眠分析 | `sleep_analysis` | hr (结构数据) | ⭐⭐⭐ 高 |
| 基础代谢 | `basal_energy_burned` | kJ → kcal | ⭐⭐ 中 |
| 锻炼时间 | `apple_exercise_time` | min | ⭐⭐⭐ 高 |
| 呼吸紊乱 | `breathing_disturbances` | count | ⭐ 低 |

**【2026-02-21 更新】呼吸率数据源确认**：

| 指标 | 数据源 | 数据点数示例 | 说明 |
|------|--------|-------------|------|
| **呼吸率** | **Apple Health** | 42点（2.20数据） | 由Apple Watch在睡眠期间监测，夜间数据 |
| **呼吸率** | Google Fit | 无数据 | Google Fit 未同步呼吸率数据 |

**结论**：呼吸率仅从 **Apple Health** 获取，不尝试 Google Fit。

**数据提取代码**：
```python
import json

file_path = "~/Health Auto Export/Health Data/HealthAutoExport-2026-02-20.json"
with open(file_path, 'r') as f:
    data = json.load(f)

metrics = data.get('data', {}).get('metrics', [])
for m in metrics:
    if m.get('name') == 'respiratory_rate':
        data_points = m.get('data', [])
        rates = [d.get('qty', 0) for d in data_points]
        avg_rate = sum(rates) / len(rates)
        print(f"呼吸率: {avg_rate:.1f} 次/分钟 (基于{len(rates)}个数据点)")
        # 结果示例：14.6 次/分钟 (范围12.0-17.5)
```

**数据特征**：
- 仅夜间睡眠期间有数据（Apple Watch在睡眠时监测）
- 正常范围：12-20 次/分钟（成人）
- 睡眠期间略低于清醒时（正常生理现象）
- 数据质量：⭐⭐⭐ 高（Apple Watch专用传感器）

### 2. Workout Data（运动数据）⭐ **重要** **【2026-02-22 更新：正确提取逻辑】**
**路径**: `~/Health Auto Export/Workout Data/HealthAutoExport-YYYY-MM-DD.json`

**注意**: Workout Data 不是每天都有，只有当天有运动时才会生成文件。

**正确的锻炼数据提取代码**：
```python
def extract_workout_data(date_str, workout_dir):
    """
    提取指定日期的锻炼数据
    
    数据结构：
    {
      "data": [{
        "name": "楼梯",              // 运动类型
        "start": "2026-02-18 20:25:19 +0800",  // 开始时间
        "end": "2026-02-18 20:58:40 +0800",    // 结束时间
        "duration": 2001.52,         // 持续时间（秒）
        "activeEnergy": null,        // 消耗能量（可能为null）
        "heart_rate_avg": null,      // 平均心率（可能为null）
        "heart_rate_max": null,      // 最高心率（可能为null）
        "distance": null             // 距离（可能为null）
      }]
    }
    """
    filepath = f"{workout_dir}/HealthAutoExport-{date_str}.json"
    
    if not os.path.exists(filepath):
        return []  # 当天无运动
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    workouts = data.get('data', [])  # 注意：直接是数组，不是 .get('workouts', [])
    
    result = []
    for w in workouts:
        workout = {
            'name': w.get('name', '未知运动'),
            'start': w.get('start', ''),
            'duration_min': round((w.get('duration') or 0) / 60, 1),
            'energy_kcal': w.get('activeEnergy'),  # 可能为null
            'avg_hr': w.get('heart_rate_avg'),     # 可能为null
            'max_hr': w.get('heart_rate_max'),     # 可能为null
            'distance_m': w.get('distance')        # 可能为null
        }
        result.append(workout)
    
    return result
```

**关键注意点**：
1. Workout Data 文件路径正确：`.../Workout Data/HealthAutoExport-YYYY-MM-DD.json`
2. 数据结构：`data` 字段直接是数组，不是嵌套的 `workouts`
3. `duration` 单位是秒，需要转换为分钟
4. `activeEnergy`、`heart_rate_avg` 等可能为 `null`，必须处理
5. 能量和心率缺失时，显示"未记录"而非跳过

**数据字段说明**：
| 字段 | 类型 | 说明 | 可能为null |
|------|------|------|-----------|
| `name` | string | 运动类型 | 否 |
| `start` | string | 开始时间 | 否 |
| `end` | string | 结束时间 | 否 |
| `duration` | float | 持续时间（秒） | 否 |
| `activeEnergy` | float/null | 消耗能量 | **是** |
| `heart_rate_avg` | float/null | 平均心率 | **是** |
| `heart_rate_max` | float/null | 最高心率 | **是** |
| `distance` | float/null | 距离（米） | **是** |

| 数据项 | 字段 | 说明 |
|--------|------|------|
| 运动类型 | `name` | 如：楼梯、跑步、骑行 |
| 开始时间 | `start` | UTC+8 时间戳 |
| 结束时间 | `end` | UTC+8 时间戳 |
| 持续时间 | `duration` | 秒 → 转换为分钟 |
| 消耗能量 | `activeEnergy` | kcal (注意：可能是数组) |
| 距离 | `distance` | km (可能为数组) |
| **心率时序** | `heartRateData` | ⭐ **每分钟心率数据** |
| 强度 | `intensity` | kcal/hr·kg |
| 温度 | `temperature` | °C |
| 湿度 | `humidity` | % |

**心率时序数据结构**:
```json
{
  "date": "2026-02-18 20:33:19 +0800",
  "Avg": 147.3,
  "Max": 155,
  "Min": 140,
  "units": "bpm"
}
```

**【2026-02-21 新增】必须尝试读取 Workout Data**：

```python
# 必须尝试读取，无法预先知道用户当天有没有锻炼
def extract_workout_data(date_str):
    file_path = f"~/Health Auto Export/Workout Data/HealthAutoExport-{date_str}.json"
    
    if not os.path.exists(file_path):
        print(f"  ℹ️  当日无 Workout Data 文件（用户可能未锻炼）")
        return None  # 正常情况，不是错误
    
    try:
        with open(file_path) as f:
            data = json.load(f)
        
        workouts = []
        for w in data.get('data', []):
            workout = {
                'name': w.get('name', '未知运动'),
                'start': w.get('start', ''),
                'end': w.get('end', ''),
                'duration': round(w.get('duration', 0) / 60, 1),  # 秒→分钟
                'activeEnergy': w.get('activeEnergy', 0),
                'distance': w.get('distance', 0),
                'heartRateData': w.get('heartRateData', []),
            }
            workouts.append(workout)
        
        return workouts
    except Exception as e:
        print(f"  ⚠️  读取 Workout Data 出错: {e}")
        return None

# 报告中显示逻辑
if workout_data:
    print(f"  ✅ 当日有 {len(workout_data)} 条运动记录")
    for w in workout_data:
        print(f"     - {w['name']}: {w['duration']}分钟, {w['activeEnergy']}kcal")
else:
    print(f"  ℹ️  当日无锻炼记录")
```

**报告展示逻辑**：
- **有 Workout Data**：显示运动类型、时长、消耗、心率曲线
- **无 Workout Data**：显示"今日无锻炼记录"（不是错误）

**重要**：不能因为无 Workout Data 而报错或跳过报告生成，这是正常情况。

### ⚠️ 数据真实性红线（2026-02-21 新增）

**🚫 绝对禁止行为**：

1. **禁止估算值**：绝不允许基于其他指标估算任何数据
   ```python
   # ❌ 禁止
   sleep_total = 6.0 + (hrv - 45) * 0.05  # 禁止估算睡眠！
   sleep_total = max(5.0, min(8.5, sleep_total))  # 禁止人工调整范围！
   
   # ✅ 正确
   sleep_total = actual_data.get('totalSleep', 0)  # 只使用实际数据
   if sleep_total == 0:
       display = "数据缺失"  # 明确标注缺失
   ```

2. **禁止单位换算错误**：
   ```python
   # ❌ 错误：Apple Health 的 walking_running_distance 已经是 km
   'distance': round(distance / 1000, 2)  # 错误！会导致 4.34km → 0.00km
   
   # ✅ 正确
   'distance': round(distance, 2)  # 直接使用，不换算
   ```

3. **禁止睡眠数据造假**：
   ```python
   # ❌ 错误：使用硬编码的估算值
   'deep': 1.1, 'core': 3.8, 'rem': 1.1  # 禁止！必须使用文件中的实际值
   
   # ✅ 正确：从文件读取实际值
   'deep': round(sleep_data.get('deep', 0), 2),  # 实际值：1.847h
   'core': round(sleep_data.get('core', 0), 2),  # 实际值：3.628h
   'rem': round(sleep_data.get('rem', 0), 2),    # 实际值：2.115h
   ```

4. **必须验证数据一致性**：
   ```python
   # 睡眠各阶段之和应约等于总睡眠时长
   total = deep + core + rem + awake
   if abs(total - total_sleep) > 0.5:
       print(f"⚠️  数据不一致警告: 各阶段之和 {total:.2f} ≠ 总时长 {total_sleep:.2f}")
   ```

5. **必须标注数据来源**：
   ```python
   # 报告中必须明确标注数据来源
   '数据来源: Apple Health (HRV:53.4ms/35点, 步数:6230/136点, 睡眠:7.59h/来源2026-02-21文件)'
   ```

**违规后果**：
- 估算值会导致用户获得错误的健康评估
- 单位错误会导致数据完全不可信（如 4.34km 显示为 0.00km）
- 睡眠结构错误会导致恢复建议完全错误

### 3. Apple Health 睡眠数据逻辑 ⭐⭐⭐ **关键规则** **【2026-02-22 精确定义 - 已修正】**

**⚠️ 重要：睡眠数据结构和时间窗口（精确定义）**

#### Apple Health 睡眠数据结构（实际格式）
```json
{
  "name": "sleep_analysis",
  "units": "hr",
  "data": [{
    "date": "2026-02-19 00:00:00 +0800",
    "asleep": 2.8169228286213346,      // 总睡眠时长（小时）
    "totalSleep": 2.8169228286213346,  // 同上
    "deep": 0,     // 深睡时长（小时）
    "core": 0,     // 核心睡眠时长（小时）
    "rem": 0,      // REM睡眠时长（小时）
    "awake": 0,    // 清醒时长（小时）
    "sleepStart": "2026-02-19 06:28:03 +0800",  // 入睡时间
    "sleepEnd": "2026-02-19 09:17:04 +0800",    // 醒来时间
    "inBedStart": "2026-02-19 06:28:03 +0800",
    "inBedEnd": "2026-02-19 09:17:04 +0800",
    "inBed": 0,
    "source": "Siegfried's Apple Watch"
  }]
}
```

**关键字段说明**：
- `sleepStart` / `sleepEnd`: 实际入睡和醒来时间（必须以此为准）
- `totalSleep` / `asleep`: 总睡眠时长（小时）
- `deep` / `core` / `rem` / `awake`: 各睡眠阶段时长（小时）
- **注意**: 使用 `sleepStart` 而非 `startDate` 来判断归属日期

#### 睡眠数据字段优先级（关键！）

**Apple Health 数据格式不一致问题**：
- 有些记录只填充 `asleep` 字段，阶段字段为0
- 有些记录只填充阶段字段（deep/core/rem/awake），`asleep` 为0
- 极少数记录两者都有值

**正确提取逻辑（优先级）**：
```python
def extract_sleep_duration(sleep_record):
    """
    提取睡眠时长 - 处理Apple Health数据格式不一致问题
    
    优先级：
    1. 如果 asleep > 0，使用 asleep（总睡眠时长）
    2. 如果 asleep == 0 但阶段之和 > 0，使用阶段之和
    3. 如果都为0，返回0
    """
    asleep = sleep_record.get('asleep', 0) or sleep_record.get('totalSleep', 0)
    deep = sleep_record.get('deep', 0)
    core = sleep_record.get('core', 0)
    rem = sleep_record.get('rem', 0)
    awake = sleep_record.get('awake', 0)
    
    # 优先使用asleep字段
    if asleep > 0:
        return {
            'total': asleep,
            'deep': deep,
            'core': core,
            'rem': rem,
            'awake': awake,
            'source': 'asleep_field'
        }
    
    # 如果asleep为0，使用各阶段之和
    stage_sum = deep + core + rem + awake
    if stage_sum > 0:
        return {
            'total': stage_sum,
            'deep': deep,
            'core': core,
            'rem': rem,
            'awake': awake,
            'source': 'stage_sum'
        }
    
    # 都无值
    return {
        'total': 0,
        'deep': 0,
        'core': 0,
        'rem': 0,
        'awake': 0,
        'source': 'none'
    }
```

**常见数据模式**：
| 日期 | asleep | deep+core+rem+awake | 应使用 | 说明 |
|------|--------|---------------------|--------|------|
| 02-18 | 2.82h | 0h | **asleep** | 只有总时长 |
| 02-19 | 0h | 6.54h | **阶段之和** | 只有阶段数据 |
| 02-20 | 0h | 7.64h | **阶段之和** | 只有阶段数据 |
| 02-21 | 0h | 7.94h | **阶段之和** | 只有阶段数据 |

#### 时间窗口定义
```
对于日期 YYYY-MM-DD 的睡眠数据：

时间窗口：YYYY-MM-DD 20:00 至 YYYY-MM-DD+1 12:00 (UTC+8)

示例（2026-02-18）：
- 2月18日 13:00-13:30 午睡 → 归属于2月18日（午睡，当日文件）
- 2月19日 06:28入睡 → 09:17醒来 → 归属于2月18日（夜间睡眠，次日文件）
- 2月19日 13:00-14:00 午睡 → 归属于2月19日

关键规则：
- 入睡时间在当日20:00至次日12:00之间 → 归属于当日
- 主要睡眠数据通常在次日文件中（夜间睡眠）
- 必须检查当日文件（午睡）+ 次日文件（夜间睡眠）
```

**数据来源规则**：

| 睡眠类型 | 可能来源文件 | 归属日期 |
|----------|--------------|----------|
| 午睡（12:00-20:00） | 当日文件（2月18日） | 2月18日 |
| 夜间睡眠（20:00-次日12:00） | 次日文件（2月19日） | 2月18日 |

**实现代码**：
```python
from datetime import datetime, timedelta

def extract_sleep_data(date_str):
    """
    提取指定日期的睡眠数据
    时间窗口：当日20:00 至 次日12:00
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # 时间窗口边界
    window_start = date.replace(hour=20, minute=0)  # 当日20:00
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)  # 次日12:00
    
    # 需要检查的文件
    files_to_check = [
        f"HealthAutoExport-{date_str}.json",  # 当日文件（午睡等）
        f"HealthAutoExport-{(date + timedelta(days=1)).strftime('%Y-%m-%d')}.json"  # 次日文件
    ]
    
    sleep_sessions = []
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for metric in data.get('data', {}).get('metrics', []):
                if metric.get('name') == 'sleep_analysis':
                    for sleep in metric.get('data', []):
                        sleep_start = parse(sleep.get('startDate'))
                        sleep_end = parse(sleep.get('endDate'))
                        
                        # 检查是否与时间窗口重叠
                        if sleep_start < window_end and sleep_end > window_start:
                            sleep_sessions.append({
                                'start': sleep_start,
                                'end': sleep_end,
                                'duration': sleep.get('qty', 0),
                                'source_file': file_path
                            })
    
    # 合并计算总睡眠时长
    total_sleep = sum(s['duration'] for s in sleep_sessions)
    
    return {
        'total_hours': total_sleep,
        'sessions': sleep_sessions,
        'source_files': list(set(s['source_file'] for s in sleep_sessions))
    }
```

**Apple Health 数据文件时间错位说明**：
Apple Health 的每日导出文件将睡眠记录在**醒来当天**的文件中：
- 2月19日 06:28入睡 → 09:17醒来 → 记录在 `HealthAutoExport-2026-02-19.json`
- 这实际上是 **2月18日晚上的睡眠**（因为入睡时间是2月18日23:30），应归属于 **2月18日报告**

**正确的数据提取规则（精确定义）**：
```
对于日期 YYYY-MM-DD 的报告：
  睡眠数据应从以下文件中提取：
  1. HealthAutoExport-YYYY-MM-DD.json（检查是否有午睡，12:00-20:00）
  2. HealthAutoExport-YYYY-MM-DD+1.json（主要来源，夜间睡眠20:00-次日12:00）
  
  然后筛选时间窗口：入睡时间在 YYYY-MM-DD 20:00 至 YYYY-MM-DD+1 12:00 之间
  
  例如：
  - 2月18日报告 → 检查 2月18日文件（午睡） + 2月19日文件（夜间睡眠）
  - 2月19日报告 → 检查 2月19日文件（午睡） + 2月20日文件（夜间睡眠）
  - 2月20日报告 → 检查 2月20日文件（午睡） + 2月21日文件（夜间睡眠）
```

**验证方法**：
检查 sleepStart 和 sleepEnd 时间：
- sleepStart: 2026-02-21 03:47:39 → 入睡在2月20日晚上 → 归属于 **2月20日**
- sleepEnd: 2026-02-21 11:26:02 → 醒来在2月21日中午前 → 正确归属

**🚫 禁止行为**：
- 绝不在找不到数据时编造睡眠数据
- 绝不用当日文件中的睡眠数据直接作为当日睡眠（必须检查时间）
- 如发现数据缺失，明确标注"数据待补充"而非估算

---

### 4. Google Fit API（睡眠数据）⭐⭐⭐ **备选方案**

**当 Apple Health 数据不可用时的备选方案**

**睡眠数据获取逻辑**：
睡眠数据用于评估当天的恢复效果，因此需要获取**当天结束后**的完整睡眠数据。

**时间窗口规则**：
```
对于日期 YYYY-MM-DD：
- 开始时间：YYYY-MM-DD 15:00 (UTC+8)
- 结束时间：YYYY+1-MM-DD 12:00 (UTC+8)

例如 2026-02-18：
- 开始：2026-02-18 15:00
- 结束：2026-02-19 12:00
```

**API调用示例**：
```python
def get_sleep_for_date(date_str):
    """获取指定日期的睡眠数据"""
    from datetime import datetime, timedelta
    
    # 解析日期
    date = datetime.strptime(date_str, "%Y-%m-%d")
    
    # 计算时间窗口
    start_time = date.replace(hour=15, minute=0, second=0)  # 当天15:00
    end_time = (date + timedelta(days=1)).replace(hour=12, minute=0, second=0)  # 次日12:00
    
    # 调用 Google Fit Sessions API
    # 过滤 activityType = 72 (睡眠)
    # 包含条件：session.start 在 [start_time, end_time] 内
    #        或 session.end 在 [start_time, end_time] 内
```

---

## 🔧 数据解析规范

### 1. 单位转换

**活动能量**: kJ → kcal
```python
kcal = kJ / 4.184
```

**时间**: 秒 → 分钟
```python
minutes = seconds / 60
```

### 2. Workout Data 解析示例

```python
def parse_workout_data(file_path):
    """解析运动数据"""
    if not os.path.exists(file_path):
        return []  # 当天无运动
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    workouts = data.get('data', {}).get('workouts', [])
    parsed = []
    
    for w in workouts:
        workout = {
            'type': w.get('name', '未知运动'),
            'start': w.get('start', '')[:16],
            'duration_min': round(w.get('duration', 0) / 60, 1),
        }
        
        # 消耗能量（处理数组或对象）
        ae = w.get('activeEnergy', [])
        if isinstance(ae, list) and ae:
            workout['calories'] = sum([e.get('qty', 0) for e in ae])
        elif isinstance(ae, dict):
            workout['calories'] = ae.get('qty', 0)
        
        # 心率时序数据
        hr_data = w.get('heartRateData', [])
        if hr_data:
            hr_timeline = []
            for hr in hr_data:
                if 'Avg' in hr:
                    hr_timeline.append({
                        'time': hr['date'].split(' ')[1][:5],
                        'hr': hr['Avg'],
                        'max': hr.get('Max', 0),
                        'min': hr.get('Min', 0)
                    })
            workout['hr_timeline'] = hr_timeline
            
            # 计算统计值
            avg_hrs = [h['Avg'] for h in hr_data if 'Avg' in h]
            workout['hr_avg'] = round(sum(avg_hrs) / len(avg_hrs), 1)
            workout['hr_max'] = max([h.get('Max', 0) for h in hr_data])
            workout['hr_min'] = min([h.get('Min', 999) for h in hr_data])
        
        parsed.append(workout)
    
    return parsed
```

### 3. 睡眠结构解析

```python
def parse_sleep_structure(metric_data):
    """解析睡眠结构"""
    if not metric_data:
        return None
    
    sleep = metric_data[0]  # 睡眠数据通常只有一条
    total = sleep.get('asleep', 0)
    
    return {
        'total': total,
        'deep': sleep.get('deep', 0),
        'core': sleep.get('core', 0),
        'rem': sleep.get('rem', 0),
        'awake': sleep.get('awake', 0),
        'in_bed': sleep.get('inBed', 0),
        'deep_pct': round(sleep.get('deep', 0) / total * 100, 1) if total else 0,
        'core_pct': round(sleep.get('core', 0) / total * 100, 1) if total else 0,
        'rem_pct': round(sleep.get('rem', 0) / total * 100, 1) if total else 0,
        'awake_pct': round(sleep.get('awake', 0) / total * 100, 1) if total else 0,
    }
```

---

## 📏 报告结构标准（详细分析版）

### 页面布局

**页眉**
- 标题：健康日报
- 日期 + 星期 + 天数
- 数据来源说明
- 时区标注

**1. Recovery Score 概览（3卡片）**
```
┌─────────────┬─────────────┬─────────────┐
│  恢复度评分  │  睡眠质量   │  运动完成   │
│     66      │     30      │    100      │
│    一般     │   需改善    │    优秀     │
└─────────────┴─────────────┴─────────────┘
```

**2. 详细指标分析表（10+项）**
| 指标 | 数值 | 评级 | AI分析 |
|------|------|------|--------|
| HRV | 52.8 ms | 🟢 良好 | [详细分析文本] |
| 静息心率 | 57 bpm | 🟢 优秀 | [详细分析文本] |
| ... | ... | ... | ... |

**评级标准**:
- 🟢 优秀 (90-100分): 超越大多数人，保持即可
- 🟢 良好 (70-89分): 正常范围，可优化
- 🟡 一般 (50-69分): 接近目标，需关注
- 🔴 需改善 (<50分): 低于标准，需改进

**3. 睡眠分析（详细版）**
- 关键问题警告（红色高亮）
- 睡眠结构横向条形图
```
深睡 0.5h (18%) ████ | 核心 1.5h (53%) ████████████ | REM 0.5h (18%) ████ | 清醒 0.3h (11%) ██
```
- 4阶段详细数据卡片
- AI深度分析文本

**4. 运动记录（带心率曲线+详细分析）**
- 运动类型 + 时间
- 4项统计数据（时长/消耗/平均心率/最高心率）
- **Chart.js 心率曲线图**
- **AI运动详细分析（必须包含4点）**：
  1. **运动强度评估**：消耗卡路里、平均心率、最高心率，判断强度等级
  2. **心率曲线分析**：心率波动特点、恢复能力、有无危险心率区间
  3. **训练效果评估**：对心肺功能、肌肉力量的锻炼效果
  4. **注意事项**：睡眠状态影响、受伤风险、改进建议

**5. AI详细建议（分4个部分，每个部分必须详细）**

**🔴 最高优先级**
- **问题识别**：具体指出问题，分析对健康的影响
- **行动计划（分步骤）**：
  - 立即行动（今晚/今天执行）
  - 睡前准备
  - 助眠措施
  - 明日安排
  - 恢复训练计划
- **预期效果**：改善后会有什么变化，什么时间能看到效果

**🟡 中等优先级**
- **问题分析**：为什么会出现这个问题，与什么因素相关
- **具体建议（分点列出）**：
  - 水分补充：具体量和方式
  - 营养摄入：具体食物和克数
  - 拉伸放松：时间和部位
  - 明日活动：具体运动类型和强度
  - 疲劳监测：观察哪些信号
- **恢复周期**：预计需要多长时间恢复

**🟢 日常优化**
- **饮食建议（三餐具体搭配）**：
  - 早餐：时间+具体食物+分量
  - 午餐：时间+具体食物+分量
  - 晚餐：时间+具体食物+分量
  - 营养素补充：具体营养素+食物来源
- **作息建议**：
  - 固定作息：误差范围
  - 午休：时长限制
  - 环境优化：温度/光线/噪音

**📊 数据洞察**
- **优势总结**：逐条列出健康优势，结合具体数据
- **风险提醒**：逐条列出健康风险，说明潜在后果
- **整体评估结论**：总结性建议，强调最重要的改进点，引用关键数据支撑

---

## 🤖 AI 提示词标准（Prompt Templates）

为了确保每份报告的AI分析详细度一致，必须使用以下标准化提示词模板：

### 提示词结构原则

**1. 详细度标准**
- 每个分析段落不少于 **100-150字**
- 必须包含：**具体数据引用** + **健康影响分析** + **行动建议**
- 使用分点编号（1. 2. 3.）组织内容

**2. 语气标准**
- 专业但易懂，避免过于学术化
- 积极鼓励，避免恐吓式表述
- 使用"建议"、"推荐"而非"必须"

**3. 数据引用标准**
- 每个分析必须引用至少 **1-2个具体数据点**
- 格式：`指标（数值）` 或 `相比昨日（变化）`

---

### 标准提示词模板

#### 模板1：指标分析提示词

```
你是健康数据分析专家。请为以下健康指标生成详细分析：

指标：{metric_name}
数值：{value} {unit}
评级：{rating}
历史对比：{comparison_with_previous}

要求：
1. 分析当前数值的健康意义（50-80字）
2. 与正常范围对比，说明位置（30-50字）
3. 结合历史数据的变化趋势（30-50字）
4. 给出具体改善建议（40-60字）

输出格式：
[综合分析段落，150-200字，包含上述4点]
```

#### 模板2：运动分析提示词

```
你是运动科学专家。请分析以下运动数据：

运动类型：{workout_type}
时长：{duration} 分钟
消耗：{calories} 千卡
平均心率：{avg_hr} bpm
最高心率：{max_hr} bpm
睡眠状态：前日睡眠 {sleep_hours} 小时

必须包含以下4点分析，每点不少于80字：

1. **运动强度评估**：
   - 根据心率和消耗判断强度等级（低/中/高）
   - 与睡眠状态结合分析是否适宜
   - 引用具体数据支撑判断

2. **心率曲线分析**：
   - 描述心率变化特点
   - 评估心率恢复能力
   - 指出是否有危险区间

3. **训练效果评估**：
   - 对心肺功能的影响
   - 肌肉力量和耐力训练效果
   - 与长期训练目标的关系

4. **注意事项与建议**：
   - 基于当前身体状况的风险提醒
   - 具体的改进建议
   - 下次运动的调整方向

输出格式：
1. **运动强度评估**：...（80-100字）
2. **心率曲线分析**：...（80-100字）
3. **训练效果评估**：...（80-100字）
4. **注意事项与建议**：...（80-100字）
```

#### 模板3：AI建议提示词（4部分）

```
你是健康管理和运动医学专家。基于以下健康数据，生成4部分详细建议：

【健康数据摘要】
- 睡眠：{sleep_hours}小时（深睡{deep}h/核心{core}h/REM{rem}h）
- 步数：{steps} 步
- 活动能量：{active_energy} 千卡
- 运动：{workout_summary}
- HRV：{hrv} ms
- 静息心率：{resting_hr} bpm

【昨日对比】
- 睡眠变化：{sleep_change}
- 活动量变化：{activity_change}

请生成以下4部分建议，每部分必须达到指定字数：

---

**🔴 最高优先级**（200-250字）

**问题识别**（80-100字）：
- 具体指出最严重的问题
- 分析对健康的直接影响
- 如果不改善会有什么后果

**行动计划**（5个步骤，共100-150字）：
1. 立即行动（今晚/今天做什么）
2. 睡前准备（具体时间、行为）
3. 助眠措施（方法、工具）
4. 明日安排（时间、内容）
5. 恢复计划（几天、什么标准）

**预期效果**（50-80字）：
- 改善后会有什么变化
- 多久能看到效果
- 长期收益

---

**🟡 中等优先级**（200-250字）

**问题分析**（80-100字）：
- 为什么会出现这个问题
- 与哪些因素相关
- 当前的身体状态评估

**具体建议**（5点，共100-150字）：
1. 水分补充：具体量（几升）、方式（几次）
2. 营养摄入：具体食物、克数、蛋白质计算
3. 拉伸放松：时间（分钟）、具体部位、保持时间
4. 明日活动：具体类型、强度控制（心率范围）
5. 疲劳监测：观察信号、判断标准、应对措施

**恢复周期**（50-80字）：
- 预计恢复时间
- 分阶段恢复计划
- 恢复标志

---

**🟢 日常优化**（250-300字）

**饮食建议**（150-180字）：
- 早餐（7:30-8:30）：具体食物+分量
- 午餐（12:00-13:00）：具体食物+分量
- 晚餐（18:00-19:00）：具体食物+分量
- 营养素补充：具体营养素、食物来源、摄入量

**作息建议**（100-120字）：
- 固定作息：具体时间、误差范围
- 午休：时长、最佳时间、注意事项
- 环境优化：温度、光线、噪音控制

---

**📊 数据洞察**（250-300字）

**优势总结**（4点，共100-120字）：
1. [优势1]：结合具体数据
2. [优势2]：结合具体数据
3. [优势3]：结合具体数据
4. [优势4]：结合具体数据

**风险提醒**（2-3点，共80-100字）：
- 逐条列出风险
- 说明潜在后果
- 引用关键数据

**整体评估结论**（80-100字）：
- 总结性建议
- 最重要的改进点
- 1-2周行动计划
- 核心原则强调

---

输出要求：
- 每个部分必须达到最低字数要求
- 使用具体数据支撑每个观点
- 建议必须具体可执行（有数字、时间、食物名称）
- 使用专业但易懂的语气
```

---

## 🎨 设计规范

### 颜色系统

**评级颜色**:
- 优秀: `#166534` (深绿) + `#dcfce7` (浅绿背景)
- 良好: `#1e40af` (深蓝) + `#dbeafe` (浅蓝背景)
- 一般: `#92400e` (橙色) + `#fef3c7` (浅黄背景)
- 需改善: `#991b1b` (红色) + `#fee2e2` (浅红背景)

**睡眠结构颜色**:
- 深睡: `#1e40af` (深蓝)
- 核心: `#3b82f6` (蓝色)
- REM: `#60a5fa` (浅蓝)
- 清醒: `#f59e0b` (橙色)

**主色调**:
- 主色: `#667eea` (紫蓝)
- 辅助: `#764ba2` (紫色)
- 背景: `#f8fafc` (浅灰)

### 字体

- 主字体: `'PingFang SC', 'Microsoft YaHei', -apple-system, sans-serif`
- 正文: 9pt
- 标题: 11-12pt
- 大数字: 22-24pt

### 图表

**心率曲线图**:
- 类型: Line Chart
- 高度: 140px
- 线条: `#667eea`
- 填充: `rgba(102, 126, 234, 0.1)`
- 点: 半径3px

**睡眠结构图**:
- 类型: 横向堆叠条形图
- 高度: 28px
- 显示数值和百分比

---

## 🤖 AI 分析标准

### 1. 指标分析模板

每项指标必须包含:
1. **数值**: 实际测量值
2. **评级**: 优秀/良好/一般/需改善
3. **分析文本**: 50-100字，包含:
   - 当前状态解读
   - 与健康标准对比
   - 潜在风险提示

### 2. 建议分级标准

**最高优先级 (🔴)**
- 严重健康风险
- 需要立即行动
- 有明确截止时间

**中等优先级 (🟡)**
- 需要关注改善
- 有具体执行方案
- 1-3天内执行

**日常优化 (🟢)**
- 长期健康习惯
- 预防性建议
- 持续执行

### 3. AI建议内容要求

每条建议必须包含:
1. **问题识别**: 具体指出问题
2. **原因分析**: 为什么会出现
3. **行动方案**: 具体步骤（可执行）
4. **预期效果**: 改善后会有什么变化

---

## ✅ 质量检查清单

生成报告前检查:
- [ ] Health Data 所有指标已读取（12+项）
- [ ] Workout Data 已尝试读取（可能为空）
- [ ] 所有数值单位已转换（kJ→kcal）
- [ ] 时区已转换（UTC→UTC+8）
- [ ] 每项指标有AI评级
- [ ] **每项指标有AI分析文本（100-150字）** ⭐
- [ ] 睡眠结构百分比计算正确
- [ ] 睡眠分析包含4阶段数据卡片+AI深度分析
- [ ] 心率时序数据已提取
- [ ] 图表数据格式正确
- [ ] **运动AI分析包含4个部分（每部分80-100字）** ⭐
- [ ] AI建议分4个部分（最高/中等/日常/洞察）
- [ ] **最高优先级200-250字**（问题识别+行动计划+预期效果）⭐
- [ ] **中等优先级200-250字**（问题分析+具体建议+恢复周期）⭐
- [ ] **日常优化250-300字**（三餐具体搭配+作息建议）⭐
- [ ] **数据洞察250-300字**（优势+风险+整体评估）⭐
- [ ] 建议内容具体可执行（有具体数字、时间、食物）
- [ ] 页眉页脚信息完整
- [ ] 数据验证通过（无异常值）
- [ ] 错误处理已考虑（缺失数据显示"未记录"）
- [ ] **使用标准AI提示词模板生成** ⭐

---

## 【2026-02-22 新增】强制验证步骤（发送前必须执行）

### 验证1：指标与数值对应检查
```python
def verify_metric_mapping(html_content, expected_data):
    """验证指标名称与数值正确对应"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 检查关键指标是否存在
    required_metrics = ['HRV', '静息心率', '步数', '行走距离', '活动能量', '血氧']
    for metric in required_metrics:
        if metric not in soup.get_text():
            raise ValueError(f"指标缺失: {metric}")
    
    # 检查数值是否合理（不为0或空）
    metric_values = {
        'HRV': expected_data.get('hrv', 0),
        '步数': expected_data.get('steps', 0),
        '活动能量': expected_data.get('active_energy', 0),
    }
    
    for name, value in metric_values.items():
        if value == 0 or value is None:
            raise ValueError(f"指标数值异常: {name} = {value}")
    
    print("✅ 指标映射验证通过")
    return True
```

### 验证2：评级颜色检查
```python
def verify_rating_colors(html_content):
    """验证评级颜色CSS类正确应用"""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找所有评级元素
    ratings = soup.find_all('span', class_=lambda x: x and 'rating-' in x)
    
    if not ratings:
        raise ValueError("未找到任何评级元素")
    
    expected_classes = {'rating-excellent', 'rating-good', 'rating-average', 'rating-poor'}
    found_classes = set()
    
    for r in ratings:
        classes = r.get('class', [])
        for c in classes:
            if c.startswith('rating-'):
                found_classes.add(c)
    
    # 检查是否至少使用了2种不同颜色
    if len(found_classes) < 2:
        raise ValueError(f"评级颜色无区分：只使用了 {found_classes}，需要至少2种不同颜色")
    
    # 检查是否使用了预期的CSS类
    invalid_classes = found_classes - expected_classes
    if invalid_classes:
        raise ValueError(f"使用了无效的评级类: {invalid_classes}")
    
    print(f"✅ 评级颜色验证通过：使用了 {len(found_classes)} 种颜色类")
    return True
```

### 验证3：AI分析字数检查
```python
def verify_ai_text_length(html_content):
    """验证AI分析文本字数达标"""
    from bs4 import BeautifulSoup
    import re
    
    soup = BeautifulSoup(html_content, 'html.parser')
    ai_texts = soup.find_all('td', class_='ai-text')
    
    issues = []
    for i, text_elem in enumerate(ai_texts):
        text = text_elem.get_text().strip()
        # 去除HTML标签后计算字符数
        char_count = len(text.replace(' ', '').replace('\n', ''))
        
        if char_count < 100:
            issues.append(f"指标分析{i+1}字数不足: {char_count}字 (要求≥100字)")
        elif char_count > 150:
            issues.append(f"指标分析{i+1}字数超限: {char_count}字 (要求≤150字)")
    
    if issues:
        raise ValueError("AI分析字数检查失败:\n" + "\n".join(issues))
    
    print(f"✅ AI分析字数验证通过：{len(ai_texts)}项指标均达标")
    return True
```

### 验证4：图表存在性检查
```python
def verify_chart_exists(html_content):
    """验证心率图表已包含"""
    if 'Chart.js' not in html_content:
        raise ValueError("缺少Chart.js引用")
    
    if 'hrChart' not in html_content:
        raise ValueError("缺少心率图表canvas元素")
    
    if 'responsive: false' not in html_content:
        raise ValueError("图表未设置responsive: false")
    
    if 'height: 200px' not in html_content and 'height="200"' not in html_content:
        raise ValueError("图表高度未限制在200px")
    
    print("✅ 心率图表验证通过")
    return True
```

### 验证5：模板变量替换检查
```python
def verify_no_unreplaced_variables(html_content):
    """验证所有{{VARIABLE}}已替换"""
    import re
    
    unreplaced = re.findall(r'\{\{\w+\}\}', html_content)
    if unreplaced:
        raise ValueError(f"发现未替换的模板变量: {unreplaced}")
    
    print("✅ 模板变量验证通过：所有变量已替换")
    return True
```

### 验证6：PDF生成后验证
```python
def verify_pdf_final(pdf_path, expected_pages=3):
    """PDF生成后的最终验证"""
    import fitz
    
    doc = fitz.open(pdf_path)
    actual_pages = len(doc)
    
    # 检查页数
    if actual_pages != expected_pages:
        raise ValueError(f"页数异常：期望{expected_pages}页，实际{actual_pages}页")
    
    # 检查中文显示
    page = doc[0]
    text = page.get_text()
    chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
    if len(chinese_chars) < 50:
        raise ValueError(f"中文显示异常：仅检测到{len(chinese_chars)}个中文字符")
    
    # 检查关键内容存在
    required_content = ['HRV', '静息心率', '步数', '睡眠', '运动']
    for content in required_content:
        if content not in text:
            raise ValueError(f"PDF缺少关键内容: {content}")
    
    doc.close()
    print(f"✅ PDF最终验证通过：{actual_pages}页，{len(chinese_chars)}个中文字符")
    return True
```

### 完整验证流程（发送前必须执行）
```python
def complete_verification_before_send(html_content, pdf_path, expected_data):
    """发送报告前的完整验证流程"""
    print("=== 执行发送前强制验证 ===")
    
    try:
        verify_metric_mapping(html_content, expected_data)
        verify_rating_colors(html_content)
        verify_ai_text_length(html_content)
        verify_chart_exists(html_content)
        verify_no_unreplaced_variables(html_content)
        verify_pdf_final(pdf_path)
        
        print("\n✅ 所有验证通过，报告可以发送")
        return True
        
    except ValueError as e:
        print(f"\n❌ 验证失败: {e}")
        print("报告未通过验证，禁止发送！")
        print("请在当前会话修正问题后重新生成。")
        return False
```

---

## ⚠️ 错误处理与数据验证

### 1. 文件缺失处理

**Health Data 文件缺失**:
```python
if not os.path.exists(health_file):
    raise FileNotFoundError(f"Health Data 文件不存在: {health_file}")
    # 发送错误通知，终止报告生成
```

**Workout Data 文件缺失**:
```python
if not os.path.exists(workout_file):
    # 正常情况，标记为"无运动记录"
    workout_data = None
    workout_section = "今日无运动记录"
```

### 2. 数据验证规则

**数值合理性检查**:
| 指标 | 正常范围 | 异常值处理 |
|------|----------|------------|
| 心率 | 40-200 bpm | >200 或 <30 标记为"数据异常" |
| 血氧 | 90-100% | <90% 标记为"需关注" |
| 睡眠 | 0-12小时 | >12小时检查是否为数据错误 |
| 步数 | 0-50000 | >50000 标记为"数据异常" |
| HRV | 20-150 ms | <20 或 >150 标记为"数据异常" |
| 能量 | 0-5000 kcal | >5000 检查单位是否为kJ |

**数据验证代码示例**:
```python
def validate_metric(name, value, min_val, max_val):
    """验证指标值是否在合理范围内"""
    if value is None:
        return None, "未记录"
    if value < min_val or value > max_val:
        return value, f"异常值（正常范围：{min_val}-{max_val}）"
    return value, "正常"

# 使用示例
hr, status = validate_metric("心率", health_data.get('avg_hr'), 40, 200)
```

### 3. 数据正确性验证（防错机制）

**数据来源追溯**：
```python
def extract_metric_with_trace(metrics, name, units=None):
    """
    提取指标值并记录数据来源，用于调试和验证
    
    Returns:
        {
            'value': 数值,
            'unit': 单位,
            'count': 数据点数量,
            'source': 'heart_rate_variability',
            'raw_samples': [前3个原始数据点]  # 用于验证
        }
    """
    for metric in metrics:
        if metric.get('name') == name:
            metric_data = metric.get('data', [])
            values = [d.get('qty', 0) for d in metric_data if 'qty' in d]
            
            if not values:
                return None
            
            avg = sum(values) / len(values)
            
            return {
                'value': round(avg, 1),
                'unit': metric.get('units', 'unknown'),
                'count': len(values),
                'source': name,
                'raw_samples': values[:3],  # 保存前3个样本用于验证
                'range': f"{min(values):.1f}-{max(values):.1f}"
            }
    return None

# 使用示例
hrv_data = extract_metric_with_trace(metrics, 'heart_rate_variability')
print(f"HRV: {hrv_data['value']} {hrv_data['unit']} (基于{hrv_data['count']}个数据点)")
print(f"样本范围: {hrv_data['range']}, 前3个样本: {hrv_data['raw_samples']}")
```

**数据验证清单（生成报告前必须执行）**：
```python
def pre_report_data_validation(health_data, date_str):
    """
    生成报告前的数据验证
    返回验证结果和潜在问题列表
    """
    issues = []
    
    # 1. 检查关键指标是否存在
    critical_metrics = ['hrv', 'resting_hr', 'steps', 'active_energy']
    for metric in critical_metrics:
        if metric not in health_data or health_data[metric] is None:
            issues.append(f"⚠️ 关键指标缺失: {metric}")
    
    # 2. 检查数值合理性
    if health_data.get('hrv', 0) > 100:
        issues.append(f"⚠️ HRV异常: {health_data['hrv']}ms (正常<100ms)")
    
    if health_data.get('hrv', 0) < 20:
        issues.append(f"⚠️ HRV异常偏低: {health_data['hrv']}ms (正常>20ms)")
    
    # 3. 与昨日数据对比（如有）
    # ...
    
    return len(issues) == 0, issues
```

**人工复核触发条件**：
- 任何指标超出正常范围
- 与昨日数据变化超过50%
- 数据点数量异常（如HRV只有1-2个数据点）
- 单位异常

### 4. 缺失数据显示规范

**当指标缺失时**:
- 数值栏显示："—" 或 "未记录"
- 评级栏显示："—"
- AI分析栏显示："当日未记录该数据"

### 4. 多段睡眠处理

**情况**: 一天内有多段睡眠（如午睡+夜间睡眠）

**处理规则**:
- 合并计算总睡眠时长
- 分别计算各阶段总时长
- 显示主睡眠（最长的一段）的入睡/醒来时间

### 5. 多次运动处理

**情况**: 一天内有多次运动

**处理规则**:
- 分别显示每次运动的详细分析
- 添加"总运动统计"卡片

### 6. 报告生成失败处理

**PDF生成失败**: 保存HTML作为备用，发送错误通知
**数据解析失败**: 尝试修复JSON或使用前一天数据生成异常报告

---

## 📊 对比报告格式标准

### 1. 对比报告结构

**标题格式**：`健康对比报告 - YYYY-MM-DD vs YYYY-MM-DD`

**必须包含的章节**：
1. **两日概览对比卡片**（3列布局）
   - 左：日期A + 恢复度评分 + 当日定位标签
   - 中：最大变化亮点 + 关键趋势
   - 右：日期B + 恢复度评分 + 当日定位标签

2. **关键指标对比表**（⚠️ **必须一行一个指标，不要多列合并**）

3. **睡眠结构对比**（左右并排展示）

4. **变化趋势分析**
   - 📈 积极改善（绿色边框）
   - 📉 正常下降/需关注（红色边框）
   - 📊 持平/无变化（灰色边框）

5. **AI深度分析**
   - 训练-恢复周期解读
   - 关键指标对比解读
   - 未来行动建议

### 2. 关键指标对比表格式（标准模板）

**布局要求**：
- 每行一个指标
- 5列：指标名 | 日期A数值 | 日期B数值 | 变化 | 趋势评级
- 背景色区分：改善(浅绿) | 下降(浅红) | 持平(白色)

**代码模板**：
```html
<table class="compare-table">
  <thead>
    <tr>
      <th>指标</th>
      <th>日期A</th>
      <th>日期B</th>
      <th>变化</th>
      <th>趋势</th>
    </tr>
  </thead>
  <tbody>
    <!-- 改善指标 - 浅绿背景 -->
    <tr style="background: #f0fdf4;">
      <td><b>睡眠时长</b></td>
      <td class="metric-value">2.82h</td>
      <td class="metric-value">6.15h</td>
      <td class="change-up">+3.33h (+118%)</td>
      <td><span class="rating rating-excellent">显著改善</span></td>
    </tr>
    <!-- 下降指标 - 浅红背景 -->
    <tr style="background: #fef2f2;">
      <td><b>步数</b></td>
      <td>6,852</td>
      <td>1,994</td>
      <td class="change-down">-4,858 (-71%)</td>
      <td><span class="rating rating-poor">恢复模式</span></td>
    </tr>
    <!-- 持平指标 - 白色背景 -->
    <tr>
      <td>血氧</td>
      <td>96.1%</td>
      <td>97.6%</td>
      <td class="change-up">+1.5%</td>
      <td><span class="rating rating-excellent">优秀</span></td>
    </tr>
  </tbody>
</table>
```

**CSS样式**：
```css
.compare-table { width: 100%; border-collapse: collapse; font-size: 8pt; }
.compare-table th, .compare-table td { 
  padding: 8px; 
  text-align: center; 
  border-bottom: 1px solid #e2e8f0; 
}
.compare-table th { background: #f1f5f9; font-weight: 600; }
.change-up { color: #16a34a; font-weight: bold; }
.change-down { color: #dc2626; font-weight: bold; }
.change-neutral { color: #6b7280; }
```

### 3. 必须包含的对比指标（至少8-10项）

**核心指标**（必选）：
1. 睡眠时长
2. 入睡时间
3. HRV
4. 静息心率
5. 步数
6. 活动能量
7. 爬楼层数（或运动时长）
8. 站立时间

**可选指标**：
- 血氧
- 呼吸率
- 行走距离
- 静息能量

### 4. 变化趋势分类标准

**📈 积极改善**（绿色边框）：
- 睡眠时长增加
- HRV提升
- 血氧改善
- 步数/运动量增加（如目标是增加）

**📉 正常下降/需关注**（红色边框）：
- 活动量下降（恢复日正常）
- 静息心率升高（运动后正常反应）
- 步数减少

**📊 持平/稳定**（灰色边框）：
- 变化幅度 < 5%
- 指标维持在目标范围内

---

## 📊 报告一致性检查

### 1. 详细度验证脚本

生成报告后，运行以下检查确保详细度一致：

```python
def check_report_detail_level(html_content):
    """检查报告详细度是否符合标准"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    issues = []
    
    # 检查指标分析字数
    ai_texts = soup.find_all(class_='ai-text')
    for i, text in enumerate(ai_texts):
        char_count = len(text.get_text())
        if char_count < 100:
            issues.append(f"指标分析{i+1}字数不足: {char_count}字 (要求100-150字)")
    
    # 检查AI建议各部分字数
    ai_rec_contents = soup.find_all(class_='ai-rec-content')
    for i, content in enumerate(ai_rec_contents):
        char_count = len(content.get_text())
        if char_count < 200:
            issues.append(f"AI建议部分{i+1}字数不足: {char_count}字 (要求200-300字)")
    
    return issues
```

### 2. 对比检查清单

生成新报告后，与标准2.18报告对比：

| 检查项 | 2.18报告参考 | 新报告要求 |
|--------|-------------|-----------|
| 指标分析字数 | 100-150字/项 | 必须达到 |
| 运动分析点数 | 4点详细分析 | 必须4点 |
| 最高优先级字数 | 200-250字 | 必须达到 |
| 中等优先级字数 | 200-250字 | 必须达到 |
| 日常优化字数 | 250-300字 | 必须达到 |
| 数据洞察字数 | 250-300字 | 必须达到 |
| 具体数据引用 | 每个分析都有 | 必须包含 |
| 可执行建议 | 有数字/时间/食物 | 必须包含 |

### 3. 自动化详细度检查

在报告生成流程中添加自动检查：

```python
# 在生成HTML后、转PDF前执行
def validate_report_detail(report_html):
    """验证报告详细度"""
    issues = check_report_detail_level(report_html)
    
    if issues:
        # 重新生成AI分析部分
        for issue in issues:
            print(f"⚠️ {issue}")
        
        # 使用更详细的提示词重新生成不足部分
        regenerate_with_longer_prompt(issues)
        
        return False, issues
    
    return True, []
```

### 4. 提示词自动增强

如果检测到详细度不足，自动增强提示词：

```python
def enhance_prompt_for_detail(base_prompt, target_section):
    """为特定部分增强提示词以提高详细度"""
    
    enhancements = {
        'ai_advice_high': """
        要求：
        - 问题识别部分必须达到80-100字
        - 行动计划必须包含5个具体步骤，每步骤20-30字
        - 预期效果必须达到50-80字
        - 使用具体数据支撑每个观点
        - 包含具体的数字、时间和行动指令
        """,
        'ai_advice_medium': """
        要求：
        - 问题分析部分必须达到80-100字
        - 具体建议必须包含5点，每点20-30字
        - 恢复周期必须达到50-80字
        - 所有建议必须有具体的量（克、毫升、分钟）
        """,
        'ai_advice_low': """
        要求：
        - 饮食建议必须包含三餐，每餐30-40字
        - 作息建议必须包含3点，每点30-40字
        - 所有食物必须有具体分量
        - 所有时间必须有具体范围
        """,
        'data_insight': """
        要求：
        - 优势总结必须包含4点，每点25-30字
        - 风险提醒必须包含2-3点，共80-100字
        - 整体评估结论必须达到80-100字
        - 必须引用具体数据支撑每个观点
        """
    }
    
    return base_prompt + enhancements.get(target_section, "")
```

---

## 🚀 自动化流程

### 每日报告生成流程

```
1. 计算日期 (昨天/前天)
   ↓
2. 读取 Health Data
   - 解析所有指标
   - 单位转换
   ↓
3. 尝试读取 Workout Data
   - 如果存在：解析运动详情和心率时序
   - 如果不存在：标记为"无运动记录"
   ↓
4. 计算评分和评级
   ↓
5. 调用 AI 生成分析文本
   - 每项指标分析
   - 分级建议
   ↓
6. 生成 HTML (含 Chart.js)
   ↓
7. 转换为 PDF
   ↓
8. 发送邮件
   ↓
9. Discord 通知
```

---

## 📁 文件命名规范

### 中文报告
- 单日标准: `YYYY-MM-DD-report-zh.pdf`
- 单日详细: `YYYY-MM-DD-detailed-zh.pdf` ⭐
- 对比: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-zh.pdf`

### 英文报告
- 单日标准: `YYYY-MM-DD-report-en.pdf`
- 单日详细: `YYYY-MM-DD-detailed-en.pdf` ⭐
- 对比: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-en.pdf`

---

## 📚 相关文档

- `PATH_REFERENCE.md`: 所有路径速查
- `EMAIL_CREDENTIALS.md`: 邮箱配置
- `MAIL_APP_STANDARD.md`: 邮件发送规范
- `REPORT_AUTOMATION.md`: 自动化流程

---

**版本**: 3.5  
**更新日期**: 2026-02-21  
**更新内容**: 
- 新增 Workout Data 支持、详细分析版标准
- 能量单位转换规则 (kJ→kcal)
- AI分析评级标准
- **运动分析4点要求**（强度/曲线/效果/注意）
- **AI建议4部分详细规范**（最高/中等/日常/洞察）
- **睡眠数据时间窗口规范**（当日15:00至次日12:00）
- **错误处理与数据验证规范**
- **多段睡眠/多次运动处理规则**
- **AI提示词标准模板**（确保详细度一致）
- **报告一致性检查清单**
- **数据正确性验证机制**（防错机制、数据来源追溯）
- **对比报告格式标准**（一行一个指标、标准模板）
- **每日自动化报告流程**（12:30定时、双语、邮件发送）

---

## 🕐 每日自动化报告流程

### 1. 执行时间
**每天 12:30 (UTC+8)**

### 2. 报告内容

**必须生成4份报告：**
1. **昨日详细报告（中文）**: `YYYY-MM-DD-report-zh.pdf`
2. **昨日详细报告（英文）**: `YYYY-MM-DD-report-en.pdf`
3. **对比报告（中文）**: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-zh.pdf`
4. **对比报告（英文）**: `YYYY-MM-DD-vs-YYYY-MM-DD-comparison-en.pdf`

**示例（假设今天是2月20日）:**
- 昨日：2026-02-19
- 前日：2026-02-18
- 生成：2.19单日报告（中英）+ 2.19vs2.18对比报告（中英）

### 3. 数据获取时间窗口

**昨日日期计算**：
```python
from datetime import datetime, timedelta

# 今天 12:30
today = datetime.now()

# 昨天
yesterday = today - timedelta(days=1)
yesterday_str = yesterday.strftime("%Y-%m-%d")  # 2026-02-19

# 前天
day_before = today - timedelta(days=2)
day_before_str = day_before.strftime("%Y-%m-%d")  # 2026-02-18
```

### 4. 自动化执行流程

```
12:30 定时触发
    ↓
1. 计算日期
   - 昨天: 2026-02-19
   - 前天: 2026-02-18
    ↓
2. 读取昨日数据 (2026-02-19)
   - Health Data
   - Workout Data (可能为空)
   - 数据验证 (数据点数量、范围检查)
    ↓
3. 读取前日数据 (2026-02-18)
   - 用于对比报告
    ↓
4. 生成昨日详细报告 - 中文版
   - 应用所有标准化模板
   - 详细度检查 (100-150字/项)
    ↓
5. 生成昨日详细报告 - 英文版
   - 内容同中文版，语言为英文
    ↓
6. 生成对比报告 - 中文版
   - 一行一个指标格式
   - 包含所有关键指标对比
    ↓
7. 生成对比报告 - 英文版
   - 内容同中文版，语言为英文
    ↓
8. 合并PDF (可选)
   - 4份报告合并为1个PDF
   - 或分开发送
    ↓
9. 发送邮件
   - 收件人: revolutionljk@gmail.com
   - 主题: 健康日报 2026-02-19 + 对比分析
   - 附件: 4份PDF报告
    ↓
10. Discord 通知
    - 发送完成通知
    - 附简要数据摘要
```

### 5. 双语报告要求

**中文版**：
- 语言：简体中文
- 时间格式：24小时制，UTC+8
- 单位：中文标注（千卡、小时、次/分）

**英文版**：
- 语言：English
- 时间格式：24-hour format, UTC+8
- 单位：英文标注 (kcal, hr, bpm)

**内容一致性**：
- 中英文报告数据完全一致
- AI分析内容相同，仅语言不同
- 同时生成，同时发送

### 6. 邮件发送规范

**收件人**: `revolutionljk@gmail.com`

**邮件主题**: 
```
健康日报 2026-02-19 + 对比分析 | Health Report 2026-02-19 + Comparison
```

**邮件正文模板**:
```
您好，

今日健康报告已生成（2026-02-19）。

【昨日关键数据】
- 睡眠: 6.15小时 (+118% vs 前日)
- HRV: 46.4 ms (-12.1% vs 前日)
- 步数: 1,993 (-71% vs 前日)
- 活动能量: 127 kcal (-77% vs 前日)

【报告附件】
1. 2026-02-19-report-zh.pdf (中文详细报告)
2. 2026-02-19-report-en.pdf (English Detailed Report)
3. 2026-02-18-vs-02-19-comparison-zh.pdf (中文对比报告)
4. 2026-02-18-vs-02-19-comparison-en.pdf (English Comparison Report)

【核心建议】
基于HRV 46.4ms（下降12.1%），建议延后高强度训练至第4-5天。

---
Best regards,
Health Report System
```

### 7. 标准化执行检查清单

**每次自动化执行前检查**:
- [ ] 日期计算正确（昨天/前天）
- [ ] Health Data 文件存在且可读
- [ ] 数据验证通过（数据点数量、数值范围）
- [ ] 所有指标单位正确转换（kJ→kcal）
- [ ] 时区设置正确（UTC+8）

**每次自动化执行后检查**:
- [ ] 生成4份PDF报告（中英各2份）
- [ ] 每份报告通过详细度验证（字数检查）
- [ ] PDF文件大小正常（不损坏）
- [ ] 邮件发送成功
- [ ] Discord 通知发送成功
- [ ] 日志记录完整（时间、状态、错误信息）

### 8. 错误处理

**数据文件缺失**:
```python
if not os.path.exists(health_file):
    # 发送错误通知邮件
    send_error_email("Health Data 文件缺失", f"找不到: {health_file}")
    # 记录日志
    log_error(f"Health Data missing for {date}")
    # 跳过今日报告，明日重试
    return
```

**报告生成失败**:
```python
try:
    generate_report()
except Exception as e:
    # 发送错误通知
    send_error_email("报告生成失败", str(e))
    # 保存错误日志
    log_error(f"Report generation failed: {e}")
    # 重试机制（最多3次）
    retry_count += 1
    if retry_count < 3:
        time.sleep(60)
        retry_generate()
```

**邮件发送失败**:
```python
try:
    send_email()
except Exception as e:
    # 记录错误
    log_error(f"Email send failed: {e}")
    # 重试
    retry_send_email()
    # 如仍失败，发送Discord紧急通知
    send_discord_alert(f"邮件发送失败: {e}")
```

### 9. 监控与日志

**必须记录的日志信息**:
```
[2026-02-20 12:30:00] 开始执行每日报告生成
[2026-02-20 12:30:02] 计算日期: 昨天=2026-02-19, 前天=2026-02-18
[2026-02-20 12:30:05] 读取2.19数据: HRV=46.4ms(26点), 睡眠=6.15h
[2026-02-20 12:30:08] 读取2.18数据: HRV=52.8ms(51点), 睡眠=2.82h
[2026-02-20 12:30:30] 生成2.19中文报告: 通过详细度检查
[2026-02-20 12:30:55] 生成2.19英文报告: 通过详细度检查
[2026-02-20 12:31:20] 生成对比报告(中): 通过格式检查
[2026-02-20 12:31:45] 生成对比报告(英): 通过格式检查
[2026-02-20 12:32:00] 发送邮件: 成功
[2026-02-20 12:32:05] Discord通知: 成功
[2026-02-20 12:32:05] 执行完成
```

### 10. 无例外原则

**严格执行，无任何例外**：
- ✅ 每天12:30准时执行（无节假日例外）
- ✅ 必须生成4份报告（中英双语）
- ✅ 必须使用标准化模板（一行一个指标）
- ✅ 必须通过详细度检查（100-150字/项）
- ✅ 必须包含数据点数量（追溯信息）
- ✅ 必须通过数据验证（数值范围检查）
- ✅ 必须发送至指定邮箱（revolutionljk@gmail.com）
- ✅ 必须发送Discord通知
- ✅ **必须记录数据路径（Apple Health + Workout + Google Fit）**
- ✅ **必须生成运动心率图表（当有Workout Data时）**
- ✅ **必须使用V2模板内置样式（禁止自定义CSS）**

**违规处理**:
- 如任一项检查失败，标记为"失败"并记录
- 立即重试（最多3次）
- 如仍失败，发送紧急通知并要求人工介入

---

## 【2026-02-22 新增】附录：完整数据提取代码模板

### 完整数据提取脚本

```python
#!/usr/bin/env python3
"""
完整健康数据提取脚本 - 2026-02-22标准化版
包含：Apple Health + Workout Data + Google Fit + 心率图表生成
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from playwright.sync_api import sync_playwright

# ========== 配置：数据路径 ==========
DATA_PATHS = {
    'apple_health': '~/我的云端硬盘/Health Auto Export/Health Data',
    'workout_data': '~/我的云端硬盘/Health Auto Export/Workout Data',
    'google_fit_token': '~/.openclaw/credentials/google-fit-token.json',
}

# ========== 1. 读取Apple Health数据 ==========
def read_apple_health(date_str: str) -> Dict:
    """读取Apple Health数据"""
    home = Path.home()
    filepath = home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data' / f'HealthAutoExport-{date_str}.json'
    
    if not filepath.exists():
        raise FileNotFoundError(f"Apple Health数据不存在: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data['data']['metrics']}
    
    def avg(name): 
        vals = [d['qty'] for d in metrics.get(name, {}).get('data', []) if 'qty' in d]
        return sum(vals) / len(vals) if vals else 0
    
    def sum_val(name):
        return sum(d['qty'] for d in metrics.get(name, {}).get('data', []) if 'qty' in d)
    
    def points(name):
        return len([d for d in metrics.get(name, {}).get('data', []) if 'qty' in d])
    
    return {
        'hrv': {'value': avg('heart_rate_variability'), 'points': points('heart_rate_variability')},
        'resting_hr': {'value': avg('resting_heart_rate'), 'points': points('resting_heart_rate')},
        'steps': {'value': sum_val('step_count'), 'points': points('step_count')},
        'distance': {'value': sum_val('walking_running_distance'), 'points': points('walking_running_distance')},
        'active_energy': {'value': sum_val('active_energy') / 4.184, 'kj': sum_val('active_energy'), 'points': points('active_energy')},
        'basal_energy': {'value': sum_val('basal_energy_burned') / 4.184, 'kj': sum_val('basal_energy_burned')},
        'flights_climbed': sum_val('flights_climbed'),
        'stand_min': sum_val('apple_stand_time'),
        'exercise_min': sum_val('apple_exercise_time'),
        'blood_oxygen': {'value': avg('blood_oxygen_saturation') * 100, 'points': points('blood_oxygen_saturation')},
        'respiratory_rate': {'value': avg('respiratory_rate'), 'points': points('respiratory_rate')},
    }

# ========== 2. 读取Workout数据 ==========
def read_workout_data(date_str: str) -> List[Dict]:
    """读取Workout数据（可能不存在）"""
    home = Path.home()
    filepath = home / '我的云端硬盘' / 'Health Auto Export' / 'Workout Data' / f'HealthAutoExport-{date_str}.json'
    
    if not filepath.exists():
        return []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    workouts = data.get('data', {}).get('workouts', [])
    result = []
    
    for w in workouts:
        # 能量
        energy_list = w.get('activeEnergy', [])
        total_kj = sum(e.get('qty', 0) for e in energy_list) if isinstance(energy_list, list) else 0
        
        # 心率时序
        hr_data = w.get('heartRateData', [])
        hr_times, hr_avg, hr_max = [], [], []
        for hr in hr_data:
            hr_times.append(hr['date'].split(' ')[1][:5])
            hr_avg.append(round(hr.get('Avg', 0)))
            hr_max.append(hr.get('Max', 0))
        
        result.append({
            'name': w.get('name', '未知运动'),
            'start': w.get('start', '')[:19],
            'end': w.get('end', '')[:19],
            'duration_min': w.get('duration', 0) / 60,
            'energy_kcal': total_kj / 4.184,
            'avg_hr': w.get('heartRate', {}).get('avg', {}).get('qty'),
            'max_hr': w.get('heartRate', {}).get('max', {}).get('qty'),
            'hr_times': hr_times,
            'hr_avg': hr_avg,
            'hr_max': hr_max,
            'hr_points': len(hr_data),
        })
    
    return result

# ========== 3. 读取睡眠数据 ==========
def read_sleep_data(date_str: str) -> Optional[Dict]:
    """读取睡眠数据（从次日文件）"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    home = Path.home()
    filepath = home / '我的云端硬盘' / 'Health Auto Export' / 'Health Data' / f'HealthAutoExport-{next_date}.json'
    
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data['data']['metrics']}
    sleep = metrics.get('sleep_analysis', {})
    
    if not sleep or not sleep.get('data'):
        return None
    
    s = sleep['data'][0]
    
    # 检查时间窗口
    sleep_start = datetime.fromisoformat(s.get('sleepStart', '').replace(' +0800', '+08:00'))
    window_start = date.replace(hour=20, minute=0)
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)
    
    if window_start <= sleep_start <= window_end:
        return {
            'total': s.get('asleep', 0),
            'deep': s.get('deep', 0),
            'core': s.get('core', 0),
            'rem': s.get('rem', 0),
            'awake': s.get('awake', 0),
            'sleep_start': s.get('sleepStart', ''),
            'sleep_end': s.get('sleepEnd', ''),
        }
    
    return None

# ========== 4. 生成心率图表 ==========
def generate_hr_chart_html(hr_times: List[str], hr_avg: List[int], hr_max: List[int]) -> str:
    """生成Chart.js心率曲线图"""
    if not hr_times:
        return "<p>无心率数据</p>"
    
    y_min = max(0, min(hr_avg) - 10)
    y_max = max(hr_max) + 10
    
    return f"""
    <canvas id="hrChart" width="700" height="200"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
      new Chart(document.getElementById('hrChart'), {{
        type: 'line',
        data: {{
          labels: {hr_times},
          datasets: [
            {{
              label: '平均心率',
              data: {hr_avg},
              borderColor: '#667eea',
              backgroundColor: 'rgba(102, 126, 234, 0.1)',
              fill: true,
              tension: 0.3,
              pointRadius: 3,
              borderWidth: 2
            }},
            {{
              label: '最高心率',
              data: {hr_max},
              borderColor: '#dc2626',
              borderDash: [5, 5],
              fill: false,
              tension: 0.3,
              pointRadius: 2,
              borderWidth: 1.5
            }}
          ]
        }},
        options: {{
          responsive: false,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'top', labels: {{ font: {{ size: 10 }}, usePointStyle: true }} }},
            title: {{ display: true, text: '运动时心率变化 (bpm)', font: {{ size: 11 }} }}
          }},
          scales: {{
            y: {{ beginAtZero: false, min: {y_min}, max: {y_max}, title: {{ display: true, text: '心率 (bpm)', font: {{ size: 10 }} }}, ticks: {{ font: {{ size: 9 }} }}, grid: {{ color: 'rgba(0,0,0,0.05)' }} }},
            x: {{ ticks: {{ font: {{ size: 9 }}, maxTicksLimit: 8 }}, grid: {{ color: 'rgba(0,0,0,0.05)' }} }}
          }}
        }}
      }});
    </script>
    """

# ========== 5. 主函数 ==========
def generate_report(date_str: str):
    """生成完整报告"""
    print(f"=== 生成 {date_str} 健康报告 ===")
    
    # 读取数据
    health = read_apple_health(date_str)
    workouts = read_workout_data(date_str)
    sleep = read_sleep_data(date_str)
    
    print(f"✅ Health: HRV={health['hrv']['value']:.1f}ms ({health['hrv']['points']}点)")
    print(f"✅ Workout: {len(workouts)}条记录" + (f", 心率点={workouts[0]['hr_points']}" if workouts else ""))
    print(f"✅ Sleep: {sleep['total']:.2f}h" if sleep else "❌ Sleep: 无数据")
    
    # 读取模板
    with open('templates/DAILY_TEMPLATE_V2.html', 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 填充数据（省略详细填充代码）...
    html = template
    
    # 生成心率图表
    if workouts:
        w = workouts[0]
        hr_chart = generate_hr_chart_html(w['hr_times'], w['hr_avg'], w['hr_max'])
        html = html.replace('{{WORKOUT_HR_CHART}}', hr_chart)
    else:
        html = html.replace('{{WORKOUT_HR_CHART}}', '<p>当日无运动记录</p>')
    
    # 生成PDF
    output_path = f'{date_str}-report-zh-V2.pdf'
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        page.wait_for_timeout(5000)
        page.pdf(path=output_path, format='A4', print_background=True, margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'})
        browser.close()
    
    print(f"✅ 报告已生成: {output_path}")
    return output_path

if __name__ == '__main__':
    generate_report('2026-02-18')
```

---

## 【2026-02-22 新增】常见问题与避免方案 ⭐⭐⭐⭐⭐

### 问题清单与根本原因分析

| # | 问题现象 | 根本原因 | 避免方案 |
|---|---------|---------|---------|
| 1 | **指标数值错乱/映射错误** | 模板变量替换时顺序混乱，或变量名相似导致错配（如`{{METRIC1_VALUE}}`填成了步数而不是HRV） | 建立指标-变量名映射表，逐项核对；使用字典映射而非顺序替换 |
| 2 | **单位显示错误（kJ vs kcal）** | 混淆原始单位（kJ）和显示单位（kcal），忘记÷4.184换算 | 提取数据时同时保存原始值和换算值；模板中只使用换算后的值 |
| 3 | **心率图表生成10+页** | Chart.js图表高度未限制，或`responsive: true`导致自适应过大 | 强制设置`height: 200px`和`responsive: false`；使用固定尺寸容器 |
| 4 | **睡眠数据时间窗口错误** | 未按20:00-次日12:00筛选，直接从当日文件取数据 | 必须检查当日+次日文件；严格按`sleepStart`时间筛选 |
| 5 | **饮食建议过于笼统** | 提示词未要求具体食物和分量，AI生成泛泛建议 | 在提示词中明确要求"早餐/午餐/晚餐+具体食物+分量"格式 |
| 6 | **PDF生成失败或文件损坏** | HTML中Chart.js CDN加载失败，或内存不足 | 添加本地回退；限制图表复杂度；分段生成 |
| 7 | **中文显示乱码** | 未声明中文字体或PDF生成工具缺少字体支持 | 必须声明`'PingFang SC', 'Microsoft YaHei'`字体栈；生成后验证 |

### 强制性检查清单（生成前必须执行）

```python
def pre_generation_checklist(template, filled_html, data_dict):
    """
    生成PDF前的强制性检查
    任何一项失败都必须停止生成并修复
    """
    checks = {
        # 1. 指标映射检查
        '指标映射正确': all(
            data_dict.get(key) is not None 
            for key in ['hrv', 'resting_hr', 'steps', 'distance', 'active_energy']
        ),
        
        # 2. 单位检查
        '活动能量单位是kcal': data_dict.get('active_energy', 0) < 5000,  # kcal值通常<5000，kJ会>20000
        '距离单位是km': data_dict.get('distance', 0) < 100,  # km值通常<50，米会>50000
        
        # 3. 模板检查
        '使用V2模板': '667eea' in template and '{{DATE}}' in template,
        '无未替换变量': '{{' not in filled_html.replace('{{', '').replace('}}', ''),
        '中文字体声明': 'PingFang SC' in filled_html or 'Microsoft YaHei' in filled_html,
        
        # 4. 心率图表检查
        '图表高度限制': 'height: 200' in filled_html or 'height="200"' in filled_html,
        'Chart.js配置正确': 'responsive: false' in filled_html,
        
        # 5. 睡眠数据检查
        '睡眠数据在正确窗口': data_dict.get('sleep', {}).get('source_file', '').endswith(
            (datetime.strptime(data_dict['date'], "%Y-%m-%d") + timedelta(days=1)).strftime('%Y-%m-%d') + '.json'
        ) if data_dict.get('sleep') else True,
    }
    
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    if not all(checks.values()):
        failed = [k for k, v in checks.items() if not v]
        raise ValueError(f"检查清单未通过: {', '.join(failed)}")
    
    return True
```

### 指标-变量名映射表（必须严格遵循）

```python
# 禁止随意更改变量名！必须与模板中的{{VARIABLE}}完全匹配
METRIC_MAPPING = {
    # 基础信息
    'DATE': 'date_str',
    'HEADER_SUBTITLE': 'f"{date_str} · Apple Health | UTC+8"',
    
    # 评分卡
    'SCORE_RECOVERY': 'recovery_score',  # 计算值 0-100
    'SCORE_SLEEP': 'sleep_score',        # 计算值 0-100
    'SCORE_EXERCISE': 'exercise_score',  # 计算值 0-100
    
    # 指标（必须对应正确）
    'METRIC1_VALUE': 'f"{hrv:.1f} ms<br><small>{hrv_points}个数据点</small>"',
    'METRIC1_RATING': 'hrv_rating',      # 优秀/良好/一般/需改善
    'METRIC1_RATING_CLASS': 'hrv_rating_class',  # rating-excellent等
    'METRIC1_ANALYSIS': 'hrv_analysis',  # AI分析文本
    
    'METRIC2_VALUE': 'f"{resting_hr:.0f} bpm"',
    'METRIC2_RATING': 'resting_hr_rating',
    'METRIC2_RATING_CLASS': 'resting_hr_rating_class',
    'METRIC2_ANALYSIS': 'resting_hr_analysis',
    
    'METRIC3_VALUE': 'f"{steps:,.0f} 步<br><small>{steps_points}个数据点</small>"',
    # ... 以此类推
    
    # 睡眠
    'SLEEP_TOTAL': 'f"{sleep_total:.1f}"',  # 小时数
    'SLEEP_DEEP': 'f"{sleep_deep:.1f}"',
    'SLEEP_DEEP_PCT': 'f"{sleep_deep_pct:.0f}"',  # 百分比，无%符号
    # ... 其他睡眠阶段
    
    # Workout
    'WORKOUT_NAME': 'workout_name',
    'WORKOUT_DURATION': 'f"{workout_duration:.0f}"',
    'WORKOUT_ENERGY': 'f"{workout_energy:.0f}"',  # kcal！
    'WORKOUT_AVG_HR': 'f"{workout_avg_hr:.0f}"',
    'WORKOUT_MAX_HR': 'f"{workout_max_hr:.0f}"',
    'WORKOUT_HR_CHART': 'hr_chart_html',  # Chart.js代码
    
    # AI建议
    'AI3_DIET': 'diet_advice',  # 必须包含具体食物和分量
    'AI3_ROUTINE': 'routine_advice',
}
```

### 单位换算强制规范

```python
# 单位换算必须在数据提取阶段完成，不要在模板中换算

# ✅ 正确做法
'active_energy': {'value': sum_kj / 4.184, 'kj': sum_kj, 'unit': 'kcal'}
# 模板中使用：{{ACTIVE_ENERGY}} kcal → 显示：289 kcal

# ❌ 错误做法
'active_energy_kj': sum_kj
# 模板中换算：{{ACTIVE_ENERGY_KJ}} / 4.184 kcal → 容易出错且混淆

# 所有需要换算的指标
UNIT_CONVERSIONS = {
    'active_energy': {'from': 'kJ', 'to': 'kcal', 'factor': 4.184},
    'basal_energy': {'from': 'kJ', 'to': 'kcal', 'factor': 4.184},
    'blood_oxygen': {'from': 'ratio', 'to': '%', 'factor': 100},  # 0.96 → 96%
    'stand_time': {'from': 'min', 'to': 'hr', 'factor': 60},      # 可选
}
```

### 心率图表生成规范（防10页问题）

```python
def generate_hr_chart_safe(hr_times, hr_avg, hr_max):
    """
    安全生成心率图表 - 防止过大导致多页
    """
    if not hr_times:
        return "<p>当日无运动记录</p>"
    
    # 限制数据点数量（最多30个，避免X轴过密）
    if len(hr_times) > 30:
        step = len(hr_times) // 30 + 1
        hr_times = hr_times[::step]
        hr_avg = hr_avg[::step]
        hr_max = hr_max[::step]
    
    html = f'''
    <div style="height: 200px; width: 100%;">
      <canvas id="hrChart"></canvas>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
      new Chart(document.getElementById('hrChart'), {{
        type: 'line',
        data: {{
          labels: {hr_times},
          datasets: [
            {{
              label: '平均心率',
              data: {hr_avg},
              borderColor: '#667eea',
              backgroundColor: 'rgba(102, 126, 234, 0.1)',
              fill: true,
              tension: 0.3,
              pointRadius: 3
            }},
            {{
              label: '最高心率',
              data: {hr_max},
              borderColor: '#dc2626',
              borderDash: [5, 5],
              fill: false,
              pointRadius: 2
            }}
          ]
        }},
        options: {{
          responsive: false,  # ❗关键：禁用响应式
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'top' }},
            title: {{ display: true, text: '心率变化 (bpm)' }}
          }},
          scales: {{
            y: {{ 
              beginAtZero: false,
              min: {max(0, min(hr_avg) - 10)},
              max: {max(hr_max) + 10}
            }}
          }}
        }}
      }});
    </script>
    '''
    return html
```

### 饮食建议生成规范（防笼统问题）

```python
# 在AI提示词中强制要求具体食物和分量

DIET_PROMPT = """
请为以下健康数据生成具体的饮食建议：

用户数据：
- 运动消耗：{active_energy} kcal
- 步数：{steps} 步
- HRV：{hrv} ms
- 睡眠：{sleep_hours} 小时

要求（必须严格遵守）：
1. 早餐（7:30-8:30）：列出具体食物+分量，如"燕麦粥1碗(50g)+鸡蛋1个+牛奶250ml+苹果1个"
2. 午餐（12:00-13:00）：列出具体食物+分量，如"糙米饭150g+清蒸鱼100g+西兰花200g+番茄蛋汤1碗"
3. 晚餐（18:00-19:00）：列出具体食物+分量，如"杂粮粥1碗+豆腐100g+凉拌黄瓜150g+酸奶100g"
4. 营养素补充：具体营养素+食物来源，如"补充蛋白质：鸡胸肉/鱼类/豆腐；补充碳水：燕麦/糙米"

禁止：
- 禁止使用"适量"、"一些"等模糊词汇
- 禁止只列出食物类别而不给具体选项
- 禁止缺少分量说明

输出格式：
早餐（7:30-8:30）：...
午餐（12:00-13:00）：...
晚餐（18:00-19:00）：...
营养素补充：...
"""
```

### 睡眠数据时间窗口验证代码

```python
def extract_sleep_with_validation(date_str, health_data_dir):
    """
    提取睡眠数据并验证时间窗口正确性
    """
    date = datetime.strptime(date_str, "%Y-%m-%d")
    window_start = date.replace(hour=20, minute=0)      # 当日20:00
    window_end = (date + timedelta(days=1)).replace(hour=12, minute=0)  # 次日12:00
    
    # 需要检查的文件
    current_file = f"{health_data_dir}/HealthAutoExport-{date_str}.json"
    next_file = f"{health_data_dir}/HealthAutoExport-{(date + timedelta(days=1)).strftime('%Y-%m-%d')}.json"
    
    sleep_records = []
    
    for file_path in [current_file, next_file]:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            for metric in data.get('data', {}).get('metrics', []):
                if metric.get('name') == 'sleep_analysis':
                    for sleep in metric.get('data', []):
                        sleep_start = parse_sleep_time(sleep.get('sleepStart'))
                        
                        # 严格验证时间窗口
                        if window_start <= sleep_start <= window_end:
                            sleep_records.append({
                                'total': sleep.get('asleep', 0),
                                'deep': sleep.get('deep', 0),
                                'core': sleep.get('core', 0),
                                'rem': sleep.get('rem', 0),
                                'awake': sleep.get('awake', 0),
                                'sleep_start': sleep.get('sleepStart'),
                                'source_file': file_path,
                                'validated': True  # 标记已通过验证
                            })
    
    if not sleep_records:
        return {'error': '在指定时间窗口内未找到睡眠数据', 'window': f'{window_start} 至 {window_end}'}
    
    # 合并睡眠数据
    return {
        'total': sum(r['total'] for r in sleep_records),
        'deep': sum(r['deep'] for r in sleep_records),
        'core': sum(r['core'] for r in sleep_records),
        'rem': sum(r['rem'] for r in sleep_records),
        'awake': sum(r['awake'] for r in sleep_records),
        'records': sleep_records,
        'window': f'{window_start} 至 {window_end}'
    }
```

### PDF生成后验证

```python
def verify_generated_pdf(pdf_path, expected_pages=3):
    """
    生成PDF后进行验证
    """
    import fitz  # PyMuPDF
    
    doc = fitz.open(pdf_path)
    actual_pages = len(doc)
    
    # 1. 验证页数
    if actual_pages != expected_pages:
        raise ValueError(f"页数异常：期望{expected_pages}页，实际{actual_pages}页")
    
    # 2. 验证中文显示
    page = doc[0]
    text = page.get_text()
    chinese_chars = [c for c in text if '\u4e00' <= c <= '\u9fff']
    if len(chinese_chars) < 20:
        raise ValueError(f"中文显示异常：仅检测到{len(chinese_chars)}个中文字符")
    
    # 3. 验证文件大小（过小可能损坏，过大可能图表异常）
    size_kb = os.path.getsize(pdf_path) / 1024
    if size_kb < 100:
        raise ValueError(f"文件可能损坏：仅{size_kb:.0f}KB")
    if size_kb > 3000:  # 超过3MB可能图表过大
        raise ValueError(f"文件过大：{size_kb:.0f}KB，可能包含异常大的图表")
    
    doc.close()
    print(f"✅ PDF验证通过：{actual_pages}页，{len(chinese_chars)}个中文字符，{size_kb:.0f}KB")
    return True
```

### 错误处理与重试机制

```python
def generate_report_with_retry(date_str, max_retries=3):
    """
    带重试机制的报告生成
    """
    for attempt in range(max_retries):
        try:
            # 1. 数据提取
            data = extract_all_data(date_str)
            
            # 2. 预生成检查
            template = load_template()
            html = fill_template(template, data)
            pre_generation_checklist(template, html, data)
            
            # 3. 生成PDF
            pdf_path = generate_pdf(html, date_str)
            
            # 4. 后验证
            verify_generated_pdf(pdf_path)
            
            return pdf_path
            
        except Exception as e:
            print(f"❌ 第{attempt + 1}次尝试失败: {e}")
            if attempt == max_retries - 1:
                # 最后一次尝试，记录详细错误并发送通知
                log_error(f"报告生成失败({date_str}): {e}")
                send_alert(f"健康报告生成失败: {date_str}")
                raise
            else:
                # 等待后重试
                time.sleep(2 ** attempt)  # 指数退避
    
    return None
```

---

## 【2026-02-22 新增】快速问题排查指南

### 症状→原因→解决方案速查表

| 症状 | 可能原因 | 解决方案 |
|-----|---------|---------|
| 指标显示0 | 指标名错误 | 对照指标名映射表检查 |
| 能量数值异常大（>10000） | 单位未换算（kJ未转kcal） | ÷4.184 |
| 能量数值异常小（<10） | 单位错误换算（÷4.184两次） | 检查换算逻辑 |
| 睡眠数据缺失 | 未检查次日文件 | 同时检查当日+次日文件 |
| 睡眠时长>12小时 | 未按时间窗口筛选 | 严格按20:00-次日12:00筛选 |
| 心率图表跨多页 | 图表高度未限制 | 设置height=200px，responsive=false |
| **锻炼心率数值为0但图表正常** | `heartRate.avg/max`为null，未从`heartRateData`计算 | 从`heartRateData`数组手动计算平均/最大心率 |
| **评级颜色无区分** | CSS类名未动态设置，所有评级使用相同类 | 根据评级值设置对应CSS类（rating-excellent/good/average/poor）|
| PDF无中文 | 字体声明缺失 | 添加PingFang SC/Microsoft YaHei |
| AI建议太笼统 | 提示词不够具体 | 使用强制格式要求的提示词 |
| PDF文件损坏 | Chart.js加载失败 | 添加超时检测和本地回退 |

---

## 【2026-02-22 新增】问题8-9详细解决方案

### 问题8：锻炼心率数值为0但图表正常

**根本原因分析：**
Apple Health Workout Data 的结构中，`heartRate` 字段（包含avg/max/min）可能为null，但 `heartRateData` 数组（时序数据）是正常的。

```json
{
  "heartRate": null,  // 可能为null！
  "heartRateData": [  // 但时序数据正常
    {"Avg": 147, "Max": 155, "Min": 140, ...},
    {"Avg": 133, "Max": 136, "Min": 129, ...},
    ...
  ]
}
```

**错误代码示例（导致显示0）：**
```python
# ❌ 错误：直接使用可能为null的heartRate字段
avg_hr = w.get('heartRate', {}).get('avg', {}).get('qty')  # 可能返回None
max_hr = w.get('heartRate', {}).get('max', {}).get('qty')  # 可能返回None
```

**正确代码示例（从heartRateData计算）：**
```python
# ✅ 正确：从heartRateData数组计算
hr_data = w.get('heartRateData', [])
if hr_data:
    avg_hrs = [hr.get('Avg', 0) for hr in hr_data if hr.get('Avg')]
    max_hrs = [hr.get('Max', 0) for hr in hr_data if hr.get('Max')]
    
    avg_hr = round(sum(avg_hrs) / len(avg_hrs)) if avg_hrs else 0
    max_hr = max(max_hrs) if max_hrs else 0
else:
    avg_hr = 0
    max_hr = 0
```

**验证检查：**
```python
def validate_workout_hr(workout_data):
    """验证锻炼心率数据一致性"""
    for w in workout_data:
        hr_from_field = w.get('heartRate', {}).get('avg', {}).get('qty')
        hr_calculated = w.get('avg_hr_calculated')
        
        if hr_from_field is None and hr_calculated > 0:
            print(f"⚠️ heartRate.avg为null，但heartRateData计算值为{hr_calculated}")
            print(f"   解决方案：使用计算值填充{{WORKOUT_AVG_HR}}")
        
        if hr_from_field != hr_calculated:
            print(f"⚠️ 心率值不一致：字段值={hr_from_field}, 计算值={hr_calculated}")
```

---

### 问题9：评级颜色无区分

**根本原因分析：**
模板中的评级CSS类名未根据实际评级值动态设置，导致所有评级使用相同的颜色样式。

**模板中的评级类定义：**
```css
/* V2模板中的评级颜色 */
.rating-excellent { background: #dcfce7; color: #166534; }  /* 绿色 */
.rating-good { background: #dbeafe; color: #1e40af; }       /* 蓝色 */
.rating-average { background: #fef3c7; color: #92400e; }     /* 黄色 */
.rating-poor { background: #fee2e2; color: #991b1b; }        /* 红色 */
```

**错误代码示例（导致颜色无区分）：**
```python
# ❌ 错误：所有评级使用相同类名
html = template.replace('{{METRIC1_RATING_CLASS}}', 'rating-good')
html = html.replace('{{METRIC2_RATING_CLASS}}', 'rating-good')  # 应该根据实际评级设置
```

**正确代码示例（动态设置CSS类）：**
```python
# ✅ 正确：根据评级值动态设置CSS类
def get_rating_class(rating_value):
    """根据评级值返回对应的CSS类名"""
    if rating_value >= 90:
        return 'rating-excellent'
    elif rating_value >= 70:
        return 'rating-good'
    elif rating_value >= 50:
        return 'rating-average'
    else:
        return 'rating-poor'

def get_rating_text(value, metric_type):
    """根据数值和指标类型返回评级文字"""
    thresholds = {
        'hrv': [(60, '优秀'), (45, '良好'), (30, '一般')],
        'resting_hr': [(60, '优秀'), (70, '良好'), (80, '一般')],
        'steps': [(10000, '优秀'), (8000, '良好'), (5000, '一般')],
        # ... 其他指标阈值
    }
    
    for threshold, rating in thresholds.get(metric_type, []):
        if value >= threshold:
            return rating
    return '需关注'

# 填充模板时使用
hrv_rating = get_rating_text(hrv_value, 'hrv')
hrv_rating_class = get_rating_class(calculate_score(hrv_value, 'hrv'))

html = template.replace('{{METRIC1_RATING}}', hrv_rating)
html = html.replace('{{METRIC1_RATING_CLASS}}', hrv_rating_class)
```

**验证检查：**
```python
def validate_rating_colors(html_content):
    """验证评级颜色是否正确应用"""
    from bs4 import BeautifulSoup
    
    soup = BeautifulSoup(html_content, 'html.parser')
    ratings = soup.find_all('span', class_=lambda x: x and 'rating-' in x)
    
    rating_classes = [r.get('class')[0] for r in ratings]
    unique_classes = set(rating_classes)
    
    if len(unique_classes) == 1:
        raise ValueError(f"评级颜色无区分：所有评级使用相同的类 '{list(unique_classes)[0]}'")
    
    print(f"✅ 评级颜色验证通过：使用了 {len(unique_classes)} 种颜色类")
    return True
```

---

## 【2026-02-22 新增】月报告数据完整性规则

### 原则：即使数据不完整也要生成报告

**强制规则：当月报告数据不完整时，必须生成"预览版"报告，而不是等待完整数据。**

**背景：**
- 用户需要及时了解自己的健康趋势
- 等待完整数据会导致报告延迟，失去时效性
- 部分数据比无数据更有价值

### 数据完整性分级

| 数据覆盖 | 报告类型 | 处理方式 |
|---------|---------|---------|
| ≥25天 (≥90%) | 完整月报告 | 标准流程生成 |
| 15-24天 (50-90%) | 月报告预览版 | 生成并标注数据不完整 |
| 7-14天 (25-50%) | 月度预览报告 | 生成，明确标注为"部分数据" |
| <7天 (<25%) | 不建议生成 | 建议等待更多数据或生成周报告 |

### 预览版报告要求

**1. 头部必须显示数据完整性警告：**
```html
<div class="alert">
  <strong>⚠️ 数据不完整提示</strong><br>
  本报告基于 {available_days}/28 天数据（{coverage_percentage}%），
  缺少 {missing_days} 天数据（{missing_dates}）。
  分析结果可能存在偏差，仅供参考。
</div>
```

**2. 统计计算必须注明样本量：**
```html
<div class="metric-note">
  平均HRV: 49.6 ms <span class="sample-size">（基于4天数据）</span>
</div>
```

**3. 趋势分析必须保守：**
- 不做过强趋势推断
- 使用"初步观察"、"有限样本显示"等措辞
- 避免预测未来趋势

**4. AI建议必须考虑数据局限：**
```
【AI建议示例】
基于当前可用的4天数据，观察到以下初步模式...
（注意：由于数据不完整，建议待完整数据可用后进行确认）
```

### 代码实现

```python
def generate_monthly_report_with_data_check(year, month, available_dates):
    """
    生成月报告，自动处理数据不完整情况
    
    Args:
        year: 年份
        month: 月份
        available_dates: 已获取数据的日期列表
    
    Returns:
        report_type: 'full' | 'preview'
        report_path: PDF文件路径
    """
    total_days = 28 if month == 2 else (30 if month in [4,6,9,11] else 31)
    available_count = len(available_dates)
    coverage = available_count / total_days
    
    # 检查数据完整性
    if coverage < 0.25:
        raise ValueError(
            f"数据覆盖率仅{coverage*100:.1f}%（{available_count}/{total_days}天），"
            f"不足以生成有意义的月报告。建议等待更多数据。"
        )
    
    # 确定报告类型
    if coverage >= 0.90:
        report_type = 'full'
        alert_class = 'complete'
        alert_text = f'✅ 数据完整：{available_count}/{total_days}天'
    elif coverage >= 0.50:
        report_type = 'preview'
        alert_class = 'warning'
        alert_text = f'⚠️ 数据预览版：{available_count}/{total_days}天（{coverage*100:.0f}%）'
    else:
        report_type = 'partial'
        alert_class = 'warning'
        alert_text = f'⚠️ 部分数据报告：{available_count}/{total_days}天（{coverage*100:.0f}%）'
    
    # 生成报告（传入report_type以调整模板）
    report_path = generate_monthly_report(
        year=year,
        month=month,
        available_dates=available_dates,
        report_type=report_type,
        alert_class=alert_class,
        alert_text=alert_text
    )
    
    return report_type, report_path

# 使用示例
try:
    available_dates = ['2026-02-18', '2026-02-19', '2026-02-20', '2026-02-21', '2026-02-22']
    report_type, path = generate_monthly_report_with_data_check(2026, 2, available_dates)
    print(f"✅ 已生成{report_type}报告: {path}")
except ValueError as e:
    print(f"❌ {e}")
```

### 模板变量

预览版报告使用以下额外变量：

| 变量 | 说明 | 示例值 |
|-----|------|-------|
| `{{DATA_STATUS}}` | 数据状态 | "预览版 (5/28天)" |
| `{{ALERT_CLASS}}` | 警告框CSS类 | "warning" / "complete" |
| `{{ALERT_TEXT}}` | 警告文本 | "⚠️ 数据不完整..." |
| `{{AVAILABLE_DAYS}}` | 可用天数 | 5 |
| `{{TOTAL_DAYS}}` | 总天数 | 28 |
| `{{COVERAGE_PERCENT}}` | 覆盖率 | 18% |
| `{{MISSING_DATES}}` | 缺失日期 | "02-01 至 02-17" |

---

---

**版本**: 4.3  
**更新日期**: 2026-02-22  
**更新内容**:
- **【修复】睡眠数据提取逻辑 - 处理Apple Health格式不一致问题**
- **【新增】asleep字段 vs 阶段字段优先级规则**
- **【更新】常见数据模式示例（02-18至02-21实际数据）**
- **【修复】2月18日缓存睡眠数据（从0修正为2.82小时）**
- **【版本升级】4.2 → 4.3**
- 如任一项检查失败，标记为"失败"并记录
- 立即重试（最多3次）
- 如仍失败，发送紧急通知并要求人工介入
