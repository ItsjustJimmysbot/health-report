# 健康报告生成 - 新Session执行手册（V2 - 强制版）

> ⚠️ **强制执行手册**：当 session reset 或新建时，**必须**按此手册执行，无任何例外。

---

## 【强制步骤】新Session启动流程

### 步骤1：自动读取标准化文档（**必须执行，禁止跳过**）

每个新Session在接收健康报告生成任务时，**必须**按顺序读取以下文件：

```python
# 强制读取清单 - 无论任务多紧急都必须执行
required_docs = [
    '~/.openclaw/workspace-health/docs/REPORT_STANDARD.md',  # 标准化流程
    '~/.openclaw/workspace-health/AGENT_ROLES.md',           # Agent职责约束
    '~/.openclaw/workspace-health/QUICK_START.md',           # 本手册
]

for doc in required_docs:
    with open(doc, 'r') as f:
        content = f.read()
        print(f"✅ 已读取: {doc}")
```

**🚫 禁止行为**：
- 禁止说"我知道流程了"就跳过读取
- 禁止凭记忆执行而不读取最新文档
- 禁止直接开始生成而不确认模板存在

---

## 【强制步骤】PDF生成方式（**唯一指定方式**）

### 中文字体保障方案（**强制执行**）

**问题**：Playwright/Chromium默认可能缺少中文字体，导致PDF乱码

**解决方案**（按优先级）：

#### 方案1：使用系统已安装中文字体（**主要方案**）

在HTML的`<style>`中**必须**包含以下字体声明：

```css
body {
  font-family: 
    'PingFang SC',           /* macOS/iOS首选 */
    'Microsoft YaHei',       /* Windows首选 */
    'Noto Sans SC',          /* Linux/通用 */
    'Source Han Sans SC',    /* Adobe开源字体 */
    'WenQuanYi Micro Hei',   /* Linux备选 */
    -apple-system,           /* macOS系统字体 */
    BlinkMacSystemFont,      /* macOS Chrome */
    'Segoe UI',              /* Windows系统 */
    sans-serif;              /* 最终回退 */
}
```

**必须验证**：生成PDF后，用PDF阅读器打开检查中文是否正常显示。

#### 方案2：字体回退机制

如果PDF中文仍乱码，**必须**尝试：

```python
# 备用方案：使用wkhtmltopdf（如果已安装）
import subprocess

# 先生成HTML文件
html_path = '/path/to/report.html'
pdf_path = '/path/to/report.pdf'

subprocess.run([
    'wkhtmltopdf',
    '--enable-local-file-access',
    '--encoding', 'utf-8',
    '--page-size', 'A4',
    '--margin-top', '8mm',
    '--margin-bottom', '8mm',
    '--margin-left', '8mm',
    '--margin-right', '8mm',
    html_path, pdf_path
])
```

#### 方案3：Docker环境（终极方案）

如果以上都失败，使用预配置Docker镜像：

```bash
# 使用包含中文字体的Playwright镜像
docker run --rm \
  -v $(pwd):/workspace \
  mcr.microsoft.com/playwright:v1.40.0-jammy \
  python3 /workspace/generate_pdf.py
```

---

## 【强制步骤】模板使用（**绝对禁止自行编写HTML/CSS**）

### 模板读取（**唯一正确方式**）

```python
# ✅ 正确：使用V2模板
template_path = '~/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html'

with open(template_path, 'r', encoding='utf-8') as f:
    template = f.read()

# 检查模板关键特征（确保是V2模板）
assert '667eea' in template, "模板错误：必须是紫色主题V2模板"
assert '{{DATE}}' in template, "模板错误：必须包含{{VARIABLE}}占位符"
assert 'PingFang SC' in template or 'Microsoft YaHei' in template, "模板错误：必须包含中文字体"

print("✅ V2模板验证通过")
```

### 🚫 **绝对禁止的行为（红线）**

```python
# ❌❌❌ 绝对禁止 - 自行编写HTML/CSS
html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  /* 禁止！禁止！禁止！ */
  .header {{ background: linear-gradient(...); }}  /* 禁止自定义颜色！ */
  body {{ font-family: 'Custom Font'; }}           /* 禁止使用非标准字体！ */
</style>
</head>
<body>
  <div class="my-custom-class">...</div>  /* 禁止自定义class！ */
</body>
</html>
"""

# ❌❌❌ 绝对禁止 - 修改模板CSS
template = template.replace('#667eea', '#ff0000')  /* 禁止修改主题色！ */
template = template.replace('PingFang SC', 'Arial')  /* 禁止修改字体！ */
```

### ✅ **唯一允许的操作**

```python
# 仅替换{{VARIABLE}}内容变量，不改变任何样式
html = template.replace('{{DATE}}', '2026-02-18')
html = html.replace('{{HRV_VALUE}}', '52.8 ms')
html = html.replace('{{HRV_ANALYSIS}}', '心率变异性52.8ms...')
# ... 其他变量替换
```

---

## 【强制步骤】睡眠数据时间窗口（**新定义**）

### 睡眠数据时间范围（**精确定义**）

**对于日期 YYYY-MM-DD 的睡眠数据**：

```
时间窗口：YYYY-MM-DD 20:00 至 YYYY-MM-DD+1 12:00 (UTC+8)

示例（2026-02-18）：
- 开始：2026-02-18 20:00
- 结束：2026-02-19 12:00
- 含义：2月18日晚上8点后入睡，到2月19日中午12点前醒来的所有睡眠
```

### 数据提取逻辑（**必须执行**）

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
    
    # 需要检查的文件：当日文件 + 次日文件
    files_to_check = [
        f"HealthAutoExport-{date_str}.json",  # 当日文件（午睡等）
        f"HealthAutoExport-{(date + timedelta(days=1)).strftime('%Y-%m-%d')}.json"  # 次日文件（夜间睡眠）
    ]
    
    sleep_sessions = []
    
    for file in files_to_check:
        if os.path.exists(file):
            with open(file, 'r') as f:
                data = json.load(f)
            
            for metric in data.get('data', {}).get('metrics', []):
                if metric.get('name') == 'sleep_analysis':
                    for sleep in metric.get('data', []):
                        sleep_start = parse_sleep_time(sleep.get('startDate'))
                        sleep_end = parse_sleep_time(sleep.get('endDate'))
                        
                        # 检查是否与时间窗口重叠
                        if sleep_start < window_end and sleep_end > window_start:
                            sleep_sessions.append({
                                'start': sleep_start,
                                'end': sleep_end,
                                'duration': sleep.get('qty', 0),
                                'source_file': file
                            })
    
    # 合并睡眠时段（去重、排序）
    total_sleep = sum(s['duration'] for s in sleep_sessions)
    
    return {
        'total_hours': total_sleep,
        'sessions': sleep_sessions,
        'source_files': list(set(s['source_file'] for s in sleep_sessions))
    }
```

### 示例说明

| 入睡时间 | 醒来时间 | 归属日期 | 数据来源文件 |
|----------|----------|----------|--------------|
| 2/18 13:00 | 2/18 13:30 | 2/18 | 2/18文件（午睡） |
| 2/18 23:30 | 2/19 07:30 | 2/18 | 2/19文件（夜间睡眠） |
| 2/19 03:47 | 2/19 11:26 | 2/18 | 2/19文件（夜间睡眠） |

**注意**：午睡（13:00-13:30）归2/18，夜间睡眠（23:30-07:30）也归2/18，只要入睡时间在20:00后。

---

## 【强制步骤】报告生成完整代码（**复制即用**）

```python
#!/usr/bin/env python3
"""
健康日报生成脚本 - V2模板强制版
使用方式：python3 generate_daily_report.py 2026-02-18
"""

import json
import os
import sys
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright

def generate_daily_report(date_str):
    # ========== 步骤1：验证模板存在 ==========
    template_path = os.path.expanduser(
        '~/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html'
    )
    
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"V2模板不存在: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 验证模板关键特征
    assert '667eea' in template, "模板错误：不是V2紫色主题模板"
    assert '{{DATE}}' in template, "模板错误：缺少{{VARIABLE}}占位符"
    
    print("✅ V2模板验证通过")
    
    # ========== 步骤2：读取数据（带时间窗口的睡眠数据） ==========
    data_dir = os.path.expanduser('~/我的云端硬盘/Health Auto Export/Health Data')
    
    # 主数据文件
    main_file = f"{data_dir}/HealthAutoExport-{date_str}.json"
    
    # 次日文件（用于睡眠数据）
    next_date = (datetime.strptime(date_str, "%Y-%m-%d") + timedelta(days=1)).strftime('%Y-%m-%d')
    next_file = f"{data_dir}/HealthAutoExport-{next_date}.json"
    
    # 读取主数据
    with open(main_file, 'r') as f:
        health_data = json.load(f)
    
    metrics = health_data.get('data', {}).get('metrics', [])
    
    # 提取各项指标（带数据点计数）
    extracted = extract_all_metrics(metrics)
    
    # 读取睡眠数据（从次日文件）
    sleep_data = extract_sleep_with_window(date_str, main_file, next_file)
    
    print(f"✅ 数据读取完成: {date_str}")
    
    # ========== 步骤3：填充模板 ==========
    html = template
    
    # 基础信息
    html = html.replace('{{DATE}}', date_str)
    html = html.replace('{{HEADER_SUBTITLE}}', f'{date_str} · Apple Health | UTC+8')
    
    # 评分卡
    html = html.replace('{{SCORE_RECOVERY}}', str(calculate_recovery_score(extracted)))
    html = html.replace('{{SCORE_SLEEP}}', str(calculate_sleep_score(sleep_data)))
    html = html.replace('{{SCORE_EXERCISE}}', str(calculate_exercise_score(extracted)))
    
    # 指标数据（示例：HRV）
    html = html.replace('{{METRIC1_VALUE}}', f"{extracted['hrv']:.1f} ms<br><small>{extracted['hrv_count']}个数据点</small>")
    html = html.replace('{{METRIC1_ANALYSIS}}', generate_hrv_analysis(extracted['hrv'], extracted['hrv_count']))
    
    # ... 其他指标
    
    # ========== 步骤4：生成PDF（带中文字体保障） ==========
    output_path = os.path.expanduser(
        f'~/.openclaw/workspace/shared/health-reports/upload/{date_str}-report-zh-V2.pdf'
    )
    
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html)
        
        # 等待字体加载
        page.wait_for_timeout(3000)
        
        # 生成PDF
        page.pdf(
            path=output_path,
            format='A4',
            print_background=True,
            margin={'top': '8mm', 'bottom': '8mm', 'left': '8mm', 'right': '8mm'}
        )
        
        browser.close()
    
    print(f"✅ PDF生成成功: {output_path}")
    
    # ========== 步骤5：保存缓存 ==========
    save_daily_cache(date_str, extracted, sleep_data)
    
    return output_path

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python3 generate_daily_report.py YYYY-MM-DD")
        sys.exit(1)
    
    date_str = sys.argv[1]
    generate_daily_report(date_str)
```

---

## 【强制检查清单】生成前必须确认

```python
def pre_generation_checklist(template, html):
    """生成PDF前的强制检查"""
    checks = {
        '使用V2模板': '667eea' in template and '{{DATE}}' in template,
        '中文字体声明': 'PingFang SC' in html or 'Microsoft YaHei' in html,
        '无未替换变量': '{{' not in html or '}}' not in html.replace('{{', '').replace('}}', ''),
        '紫色主题': 'linear-gradient(135deg, #667eea' in html,
        '亮色背景': '#f8fafc' in html or 'white' in html,
    }
    
    for check_name, result in checks.items():
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")
    
    if not all(checks.values()):
        raise ValueError("检查清单未通过，禁止生成PDF")
    
    return True
```

---

## 快速命令参考

```bash
# 生成单日报告
python3 generate_daily_report.py 2026-02-18

# 检查模板
ls ~/.openclaw/workspace-health/templates/DAILY_TEMPLATE_V2.html

# 验证PDF中文
textextract ~/.openclaw/workspace/shared/health-reports/upload/2026-02-18-report-zh-V2.pdf | head -20
```

---

**版本**: V2.0 - 强制版  
**更新日期**: 2026-02-22  
**更新内容**: 
- 添加强制步骤检查
- 明确中文字体保障方案
- 精确定义睡眠数据时间窗口（20:00-次日12:00）
- 禁止自行编写HTML/CSS的明确声明
