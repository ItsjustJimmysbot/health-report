#!/usr/bin/env python3
"""
从 Google Fit API 获取睡眠数据（处理跨天情况）
"""

import json
import os
import sys
from datetime import datetime, timedelta
import subprocess

def get_google_fit_sleep_for_date_range(start_date, end_date):
    """
    从 Google Fit 获取日期范围内的所有睡眠数据
    
    Args:
        start_date: 格式为 'YYYY-MM-DD' 的开始日期
        end_date: 格式为 'YYYY-MM-DD' 的结束日期
    
    Returns:
        list: 睡眠会话列表
    """
    
    # 凭证文件路径
    token_file = os.path.expanduser("~/.openclaw/credentials/google-fit-token.json")
    cred_file = os.path.expanduser("~/.openclaw/credentials/google-fit-credentials.json")
    
    if not os.path.exists(token_file) or not os.path.exists(cred_file):
        print("❌ Google Fit credentials not found", file=sys.stderr)
        return []
    
    # 读取凭证
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    with open(cred_file, 'r') as f:
        cred_data = json.load(f)
    
    refresh_token = token_data.get('refresh_token')
    client_id = cred_data.get('installed', {}).get('client_id')
    client_secret = cred_data.get('installed', {}).get('client_secret')
    
    if not refresh_token or not client_id or not client_secret:
        print("❌ Missing credentials", file=sys.stderr)
        return []
    
    # 获取 access token
    token_response = subprocess.run([
        'curl', '-s', '-X', 'POST', 'https://oauth2.googleapis.com/token',
        '-d', f'refresh_token={refresh_token}',
        '-d', f'client_id={client_id}',
        '-d', f'client_secret={client_secret}',
        '-d', 'grant_type=refresh_token'
    ], capture_output=True, text=True)
    
    token_result = json.loads(token_response.stdout)
    access_token = token_result.get('access_token')
    
    if not access_token:
        print(f"❌ Failed to get access token", file=sys.stderr)
        return []
    
    # 计算时间范围（查询范围扩展前后一天，处理跨天睡眠）
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=1)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    
    start_time = start_dt.strftime("%Y-%m-%dT00:00:00.000Z")
    end_time = end_dt.strftime("%Y-%m-%dT00:00:00.000Z")
    
    # 获取睡眠会话
    sessions_response = subprocess.run([
        'curl', '-s', '-X', 'GET',
        f'https://www.googleapis.com/fitness/v1/users/me/sessions?startTime={start_time}&endTime={end_time}&activityType=72',
        '-H', f'Authorization: Bearer {access_token}'
    ], capture_output=True, text=True)
    
    sessions_data = json.loads(sessions_response.stdout)
    
    sessions = []
    if 'session' in sessions_data:
        for session in sessions_data['session']:
            start_ms = int(session.get('startTimeMillis', 0))
            end_ms = int(session.get('endTimeMillis', 0))
            
            sessions.append({
                'start_time': datetime.fromtimestamp(start_ms / 1000),
                'end_time': datetime.fromtimestamp(end_ms / 1000),
                'start_ms': start_ms,
                'end_ms': end_ms,
                'duration_min': (end_ms - start_ms) / 60000
            })
    
    return sessions

def get_sleep_for_target_date(target_date, sessions):
    """
    从会话列表中提取目标日期的睡眠数据
    
    策略：
    1. 如果睡眠开始于目标日期 12:00 之后，计入目标日期
    2. 如果睡眠结束于目标日期 12:00 之前，计入目标日期
    3. 否则计入相邻日期
    """
    
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    target_noon = target_dt.replace(hour=12, minute=0, second=0)
    
    total_minutes = 0
    matched_sessions = []
    
    for session in sessions:
        start_time = session['start_time']
        end_time = session['end_time']
        
        # 判断这个睡眠会话是否主要属于目标日期
        # 策略：如果睡眠的主要部分（超过50%）在目标日期，或者睡眠结束于目标日期
        
        # 计算睡眠在目标日期的部分
        target_start = target_dt.replace(hour=0, minute=0, second=0)
        target_end = target_dt.replace(hour=23, minute=59, second=59)
        
        # 计算重叠时间
        overlap_start = max(start_time, target_start)
        overlap_end = min(end_time, target_end)
        
        if overlap_end > overlap_start:
            overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
            
            # 如果重叠超过1小时，计入目标日期
            if overlap_minutes >= 60:
                total_minutes += overlap_minutes
                matched_sessions.append({
                    'start': start_time.strftime("%H:%M"),
                    'end': end_time.strftime("%H:%M"),
                    'duration_min': session['duration_min'],
                    'overlap_min': overlap_minutes
                })
    
    if total_minutes == 0:
        return None
    
    total_hours = total_minutes / 60
    
    return {
        'date': target_date,
        'total_hours': round(total_hours, 1),
        'total_minutes': round(total_minutes),
        'sessions': matched_sessions,
        # 估算睡眠阶段
        'deep_hours': round(total_hours * 0.20, 1),
        'rem_hours': round(total_hours * 0.25, 1),
        'core_hours': round(total_hours * 0.50, 1),
        'awake_hours': round(total_hours * 0.05, 1),
        'deep_pct': 20,
        'rem_pct': 25,
        'core_pct': 50,
        'awake_pct': 5,
        'efficiency': 0.95,
        'source': 'Google Fit'
    }

def get_google_fit_sleep(target_date):
    """
    获取指定日期的睡眠数据（处理跨天情况）
    """
    # 获取前后一天的睡眠数据
    sessions = get_google_fit_sleep_for_date_range(target_date, target_date)
    
    if not sessions:
        print(f"⚠️ No sleep sessions found for {target_date}", file=sys.stderr)
        return None
    
    return get_sleep_for_target_date(target_date, sessions)

def merge_sleep_data(apple_health_data, google_fit_sleep):
    """
    智能合并 Apple Health 和 Google Fit 的睡眠数据
    
    策略：
    1. 优先使用 Google Fit 的睡眠时长（更准确处理跨天）
    2. 但保留 Apple Health 的详细睡眠结构（深睡/REM/浅睡）
    3. 如果 Google Fit 没有数据，完全使用 Apple Health
    """
    
    # 保存 Apple Health 的原始睡眠数据
    apple_sleep = {
        'hours': apple_health_data.get('sleep_hours', 0),
        'deep': apple_health_data.get('sleep_deep', 0),
        'rem': apple_health_data.get('sleep_rem', 0),
        'core': apple_health_data.get('sleep_core', 0),
        'awake': apple_health_data.get('sleep_awake', 0),
        'deep_pct': apple_health_data.get('sleep_deep_pct', 0),
        'rem_pct': apple_health_data.get('sleep_rem_pct', 0),
        'core_pct': apple_health_data.get('sleep_core_pct', 0),
        'awake_pct': apple_health_data.get('sleep_awake_pct', 0),
        'efficiency': apple_health_data.get('sleep_efficiency', 0),
        'start': apple_health_data.get('sleep_start', '--:--'),
        'end': apple_health_data.get('sleep_end', '--:--'),
    }
    
    if google_fit_sleep and google_fit_sleep['total_hours'] > 0:
        # 使用 Google Fit 的睡眠时长
        apple_health_data['sleep_hours'] = google_fit_sleep['total_hours']
        apple_health_data['time_in_bed'] = google_fit_sleep['total_hours']
        apple_health_data['sleep_source'] = 'Google Fit'
        
        # 使用 Google Fit 的时间
        if google_fit_sleep['sessions']:
            apple_health_data['sleep_start'] = google_fit_sleep['sessions'][0]['start']
            apple_health_data['sleep_end'] = google_fit_sleep['sessions'][-1]['end']
        
        # 如果有 Apple Health 的详细结构，按比例调整
        if apple_sleep['hours'] > 0:
            ratio = google_fit_sleep['total_hours'] / apple_sleep['hours']
            apple_health_data['sleep_deep'] = round(apple_sleep['deep'] * ratio, 1)
            apple_health_data['sleep_rem'] = round(apple_sleep['rem'] * ratio, 1)
            apple_health_data['sleep_core'] = round(apple_sleep['core'] * ratio, 1)
            apple_health_data['sleep_awake'] = round(apple_sleep['awake'] * ratio, 1)
            # 保留百分比
            apple_health_data['sleep_deep_pct'] = apple_sleep['deep_pct']
            apple_health_data['sleep_rem_pct'] = apple_sleep['rem_pct']
            apple_health_data['sleep_core_pct'] = apple_sleep['core_pct']
            apple_health_data['sleep_awake_pct'] = apple_sleep['awake_pct']
            apple_health_data['sleep_efficiency'] = apple_sleep['efficiency']
        else:
            # 没有 Apple Health 数据，使用 Google Fit 的估算值
            apple_health_data['sleep_deep'] = google_fit_sleep['deep_hours']
            apple_health_data['sleep_rem'] = google_fit_sleep['rem_hours']
            apple_health_data['sleep_core'] = google_fit_sleep['core_hours']
            apple_health_data['sleep_awake'] = google_fit_sleep['awake_hours']
            apple_health_data['sleep_deep_pct'] = google_fit_sleep['deep_pct']
            apple_health_data['sleep_rem_pct'] = google_fit_sleep['rem_pct']
            apple_health_data['sleep_core_pct'] = google_fit_sleep['core_pct']
            apple_health_data['sleep_awake_pct'] = google_fit_sleep['awake_pct']
            apple_health_data['sleep_efficiency'] = google_fit_sleep['efficiency']
    else:
        # 没有 Google Fit 数据，使用 Apple Health
        apple_health_data['sleep_source'] = 'Apple Health'
    
    return apple_health_data

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='获取 Google Fit 睡眠数据（处理跨天）')
    parser.add_argument('date', help='目标日期 (YYYY-MM-DD)')
    parser.add_argument('--output', '-o', help='输出 JSON 文件路径')
    
    args = parser.parse_args()
    
    sleep_data = get_google_fit_sleep(args.date)
    
    if sleep_data:
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(sleep_data, f, ensure_ascii=False, indent=2)
            print(f"✅ 睡眠数据已保存: {args.output}")
        else:
            print(json.dumps(sleep_data, ensure_ascii=False, indent=2))
    else:
        print("❌ 未获取到睡眠数据")
        sys.exit(1)
