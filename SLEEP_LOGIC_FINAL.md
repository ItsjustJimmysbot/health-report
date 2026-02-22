### 3. Apple Health 睡眠数据逻辑 ⭐⭐⭐ **关键规则** **【2026-02-22 最终确定版】**

**⚠️ 睡眠数据归属规则（最终确定）**

```
对于日期 YYYY-MM-DD 的睡眠数据：

✅ 只读取次日文件（YYYY-MM-DD+1）中的睡眠数据
❌ 不读取当日文件中的凌晨睡眠（那属于前一晚）

原因：
- 当日文件的凌晨睡眠（如2月18日03:40-09:12）→ 属于前一晚（2月17日）的夜间睡眠
- 次日文件的早晨睡眠（如2月19日06:28-09:17）→ 才是当日（2月18日）入睡的睡眠

示例（2026-02-18）：
- 读取文件：HealthAutoExport-2026-02-19.json
- 提取该文件中 sleepStart 在 02-19 00:00-12:00 之间的睡眠
- 得到：06:28入睡 → 09:17醒来，时长2.82小时
```

**关键字段说明**：
- `sleepStart` / `sleepEnd`: 实际入睡和醒来时间（必须以此为准）
- `totalSleep` / `asleep`: 总睡眠时长（小时）
- `deep` / `core` / `rem` / `awake`: 各睡眠阶段时长（小时）
- **注意**: 某些时段可能缺少阶段数据（显示为0），这是正常的

**正确的数据提取代码（最终版）**：
```python
def extract_sleep_data_correct(date_str):
    """
    提取指定日期的睡眠数据
    规则：只读取次日文件，提取00:00-12:00之间的睡眠
    """
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    next_date = target_date + timedelta(days=1)
    next_date_str = next_date.strftime("%Y-%m-%d")
    
    # 只读取次日文件
    filepath = f"{DATA_DIR}/HealthAutoExport-{next_date_str}.json"
    
    if not os.path.exists(filepath):
        return None
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    sleep_sessions = []
    
    for metric in data.get('data', {}).get('metrics', []):
        if metric.get('name') == 'sleep_analysis':
            for sleep in metric.get('data', []):
                sleep_start_str = sleep.get('sleepStart')
                sleep_end_str = sleep.get('sleepEnd')
                
                if not sleep_start_str or not sleep_end_str:
                    continue
                
                try:
                    sleep_start = datetime.strptime(sleep_start_str[:19], "%Y-%m-%d %H:%M:%S")
                    sleep_end = datetime.strptime(sleep_end_str[:19], "%Y-%m-%d %H:%M:%S")
                except:
                    continue
                
                # 只提取次日00:00-12:00之间的睡眠
                if sleep_start.hour < 12 and sleep_start.date() == next_date.date():
                    sleep_sessions.append({
                        'start': sleep_start,
                        'end': sleep_end,
                        'total_hours': sleep.get('totalSleep') or sleep.get('asleep') or 0,
                        'deep_hours': sleep.get('deep', 0),
                        'core_hours': sleep.get('core', 0),
                        'rem_hours': sleep.get('rem', 0),
                        'awake_hours': sleep.get('awake', 0),
                    })
    
    if not sleep_sessions:
        return None
    
    # 合并（如果有多段）
    return {
        'total_hours': sum(s['total_hours'] for s in sleep_sessions),
        'deep_hours': sum(s['deep_hours'] for s in sleep_sessions),
        'core_hours': sum(s['core_hours'] for s in sleep_sessions),
        'rem_hours': sum(s['rem_hours'] for s in sleep_sessions),
        'awake_hours': sum(s['awake_hours'] for s in sleep_sessions),
        'bed_time': min(s['start'] for s in sleep_sessions),
        'wake_time': max(s['end'] for s in sleep_sessions),
        'num_sessions': len(sleep_sessions)
    }
```

**关于睡眠阶段数据缺失的说明**：

某些睡眠记录可能 `deep=0, core=0, rem=0, awake=0`，这是正常现象，可能原因：
1. 睡眠时长太短（<3小时），被识别为「小憩」而非「完整睡眠」
2. Apple Watch 睡眠阶段追踪设置未开启
3. 睡眠被手动添加，缺少传感器数据
4. watchOS 版本不支持自动睡眠阶段追踪

**报告展示原则**：
- 如有阶段数据：显示具体 deep/core/rem/awake 数值和百分比
- 如阶段数据为0：显示「睡眠结构未分类」或「小憩模式」，不编造数据
- 总睡眠时长始终显示实际值

---

**更新日期**: 2026-02-22  
**更新内容**: 明确睡眠数据只读取次日文件，不读取当日文件的凌晨睡眠
