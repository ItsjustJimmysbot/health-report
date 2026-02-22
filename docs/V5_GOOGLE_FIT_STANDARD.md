### 1.5 Google Fit备用数据源（V5.0新增）

**场景**: 当Apple Health数据缺失时，自动尝试读取Google Fit作为备用

**优先级**:
1. Apple Health (primary)
2. Google Fit (backup for sleep/activity if Apple Health missing)

**数据路径**:
```
~/我的云端硬盘/Google Fit Export/google_fit_YYYY-MM-DD.json
```

**V5.0强制逻辑**:
```python
def parse_google_fit_data(date_str: str, google_fit_dir: Path) -> dict:
    """V5.0: 解析Google Fit数据作为备用数据源"""
    google_fit_path = Path(google_fit_dir) / f'google_fit_{date_str}.json'
    
    if not google_fit_path.exists():
        return None
    
    try:
        with open(google_fit_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        result = {}
        
        # 解析睡眠数据
        sleep_sessions = data.get('sleep', [])
        if sleep_sessions:
            total_sleep = sum(s.get('duration_hours', 0) for s in sleep_sessions)
            result['sleep'] = {
                'total_hours': round(total_sleep, 2),
                'deep_hours': 0,  # Google Fit可能不提供详细阶段
                'core_hours': 0,
                'rem_hours': 0,
                'awake_hours': 0,
                'records': len(sleep_sessions),
                'source': 'Google Fit'
            }
        
        # 解析步数
        steps_data = data.get('steps', [])
        if steps_data:
            total_steps = sum(s.get('count', 0) for s in steps_data)
            result['steps'] = {
                'value': total_steps,
                'source': 'Google Fit'
            }
        
        return result if result else None
        
    except Exception as e:
        print(f"⚠️ Google Fit数据解析错误: {e}")
        return None
```

**数据合并规则**:
- 如果Apple Health和Google Fit都有数据，优先使用Apple Health
- 如果Apple Health缺失，自动使用Google Fit作为备用
- 在报告中注明数据来源 (`data_source`字段)
- 如果两者数据源不同，需要在AI分析中说明可能存在的数据差异

**Google Fit数据格式示例**:
```json
{
  "date": "2026-02-18",
  "sleep": [
    {
      "start_time": "2026-02-18 23:30:00",
      "end_time": "2026-02-19 06:30:00",
      "duration_hours": 7.0
    }
  ],
  "steps": [
    {"time": "2026-02-18 08:00:00", "count": 5000},
    {"time": "2026-02-18 18:00:00", "count": 3000}
  ]
}
```

**如何导出Google Fit数据**:
1. 使用Google Fit API (需要配置OAuth2)
2. 使用第三方导出工具
3. 使用脚本 `scripts/google_fit_export.py` 创建示例数据

**注意事项**:
- Google Fit数据可能缺少详细的睡眠阶段（深睡/核心/REM）
- Google Fit步数可能与Apple Health有差异，AI分析时应说明数据来源
- 如果两者都有数据，以Apple Health为准，不合并

