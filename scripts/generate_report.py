#!/usr/bin/env python3
"""
Health Agent - Daily Report Generator
Generates bilingual health reports from Apple Health data
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Configuration (loaded from environment)
HEALTH_DATA_PATH = os.getenv("HEALTH_DATA_PATH", "~/Google Drive/Health Auto Export/Health Data/")
OUTPUT_PATH = os.getenv("OUTPUT_PATH", "~/Documents/Health Reports/")
AI_MODEL = os.getenv("AI_MODEL", "kimi-coding/k2p5")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Shanghai")

def parse_health_data(file_path, date_str):
    """Parse Apple Health Auto Export JSON"""
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return None
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    metrics = data.get('data', {}).get('metrics', [])
    results = {'date': date_str}
    
    for metric in metrics:
        name = metric.get('name', '')
        metric_data = metric.get('data', [])
        
        if not metric_data:
            continue
        
        values = [d.get('qty', 0) for d in metric_data if 'qty' in d]
        if not values:
            continue
        
        if name == 'heart_rate_variability':
            results['hrv'] = round(sum(values) / len(values), 1)
        elif name == 'resting_heart_rate':
            results['resting_hr'] = round(sum(values) / len(values), 1)
        elif name == 'step_count':
            results['steps'] = int(sum(values))
        elif name == 'active_energy':
            kj = sum(values)
            results['active_energy_kj'] = round(kj, 1)
            results['active_energy'] = round(kj / 4.184, 1)  # Convert kJ to kcal
        elif name == 'apple_exercise_time':
            results['exercise_min'] = round(sum(values), 1)
    
    return results

def generate_report(data, lang='zh'):
    """Generate HTML report"""
    # This is a simplified template
    # Full template should be loaded from ~/.config/health-agent/templates/
    
    date = data.get('date', 'Unknown')
    
    html = f"""
<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <title>Health Report - {date}</title>
    <style>
        body {{ font-family: 'PingFang SC', -apple-system, sans-serif; }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 20px; }}
        .content {{ padding: 20px; }}
        .metric {{ margin: 10px 0; padding: 10px; background: #f5f5f5; border-radius: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🏥 Daily Health Report</h1>
        <p>{date}</p>
    </div>
    <div class="content">
        <div class="metric">
            <strong>HRV:</strong> {data.get('hrv', 'N/A')} ms
        </div>
        <div class="metric">
            <strong>Resting HR:</strong> {data.get('resting_hr', 'N/A')} bpm
        </div>
        <div class="metric">
            <strong>Steps:</strong> {data.get('steps', 'N/A'):,}
        </div>
        <div class="metric">
            <strong>Active Energy:</strong> {data.get('active_energy', 'N/A')} kcal
        </div>
    </div>
</body>
</html>
"""
    return html

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_report.py <date>")
        print("Example: generate_report.py 2024-02-20")
        sys.exit(1)
    
    target_date = sys.argv[1]
    
    # Expand paths
    health_path = os.path.expanduser(HEALTH_DATA_PATH)
    output_path = os.path.expanduser(OUTPUT_PATH)
    
    # Ensure output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # Read data
    file_path = os.path.join(health_path, f"HealthAutoExport-{target_date}.json")
    data = parse_health_data(file_path, target_date)
    
    if not data:
        print(f"❌ Failed to read data for {target_date}")
        sys.exit(1)
    
    # Generate reports
    html_zh = generate_report(data, 'zh')
    html_en = generate_report(data, 'en')
    
    # Save HTML (in real implementation, convert to PDF using Playwright)
    output_zh = os.path.join(output_path, f"{target_date}-report-zh.html")
    output_en = os.path.join(output_path, f"{target_date}-report-en.html")
    
    with open(output_zh, 'w') as f:
        f.write(html_zh)
    
    with open(output_en, 'w') as f:
        f.write(html_en)
    
    print(f"✅ Reports generated:")
    print(f"   - {output_zh}")
    print(f"   - {output_en}")

if __name__ == '__main__':
    main()
