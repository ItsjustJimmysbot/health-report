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

**旧版错误**: 使用`startDate`字段，未按时间窗口筛选

**V5.0强制逻辑**:
```python
def parse_sleep_data_v5(date_str: str) -> dict:
    """V5.0: 使用sleepStart字段，严格时间窗口筛选"""
    date = datetime.strptime(date_str, '%Y-%m-%d')
    next_date = (date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    filepath = HEALTH_DIR / f'HealthAutoExport-{next_date}.json'
    if not filepath.exists():
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metrics = {m['name']: m for m in data.get('data', {}).get('metrics', [])}
    sleep_metric = metrics.get('sleep_analysis', {})
    
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
                sleep_records.append({
                    'total': sleep.get('asleep', 0) or sleep.get('totalSleep', 0),
                    'deep': sleep.get('deep', 0),
                    'core': sleep.get('core', 0),
                    'rem': sleep.get('rem', 0),
                    'awake': sleep.get('awake', 0),
                })
        except:
            continue
    
    return sleep_records
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

**V5.0强制要求**:
```python
# 每项分析后必须验证
def verify_ai_analysis(text: str, min_len: int, max_len: int) -> bool:
    """验证AI分析字数"""
    if len(text) < min_len:
        print(f"⚠️ 字数不足: {len(text)}字 < {min_len}字")
        return False
    if len(text) > max_len:
        print(f"⚠️ 字数超限: {len(text)}字 > {max_len}字")
        return False
    
    # 检查具体数据引用
    if 'ms' not in text and 'bpm' not in text:
        print("⚠️ 缺少具体数值引用")
        return False
    
    # 检查禁止词汇
    forbidden_words = ['良好', '注意', '适当', '一般']
    for word in forbidden_words:
        if word in text:
            print(f"⚠️ 发现模糊词汇: {word}")
            return False
    
    return True
```

### 2.3 饮食建议格式（预防可读性差）

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
- [ ] 血氧单位判断正确（>1则不乘100）
- [ ] 睡眠数据使用`sleepStart`字段
- [ ] AI分析字数达标（150-200/250-300字）
- [ ] 无模糊词汇（"良好""注意"等）
- [ ] 有具体数据引用（"HRV 52.8ms"）
- [ ] 饮食建议使用HTML格式
- [ ] 图表使用`responsive: false`
- [ ] 所有模板变量已替换
- [ ] 质量验证通过

---

**版本**: V5.0-REVISED  
**修订日期**: 2026-02-22  
**修订内容**: 全面预防V4.3所有已知问题
