#!/usr/bin/env python3
"""Health Report 共用工具函数 - V5.8.1"""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

# ==================== 配置加载 ====================

def load_config() -> dict:
    """从 config.json 加载配置
    
    搜索路径（按优先级）：
    1. 脚本所在目录的父目录/config.json
    2. ~/.openclaw/workspace-health/config.json
    """
    config_paths = [
        Path(__file__).parent.parent / "config.json",
        Path.home() / '.openclaw' / 'workspace-health' / 'config.json',
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    return {}


# ==================== 成员名称处理 ====================

def safe_member_name(name: str) -> str:
    """将成员名称转换为安全的文件名格式
    
    替换规则：
    - 空格 -> 下划线
    - / -> 下划线
    - \\ -> 下划线
    """
    if not name:
        return "member"
    return (name or "member").strip().replace(' ', '_').replace('/', '_').replace('\\', '_')


# ==================== AI 分析匹配 ====================

def is_single_analysis_dict(obj: Any) -> bool:
    """检查对象是否为单个成员的分析数据结构"""
    if not isinstance(obj, dict):
        return False
    signal_keys = {
        'hrv', 'resting_hr', 'steps', 'distance', 'active_energy',
        'sleep', 'workout', 'priority', 'recommendations',
        'trend_analysis', 'hrv_analysis', 'weekly_analysis', 'monthly_analysis'
    }
    return bool(signal_keys.intersection(obj.keys()))


def pick_member_ai_analysis(
    raw_ai_analyses: Union[Dict, List], 
    member_name: str, 
    idx: int,
    strict: bool = True
) -> Dict[str, Any]:
    """从原始 AI 分析数据中提取指定成员的分析
    
    参数:
        raw_ai_analyses: 原始 AI 分析数据（可能包含多成员）
        member_name: 成员名称
        idx: 成员索引
        strict: 严格模式（True=找不到时返回空，False=兜底到第一个）
    
    返回:
        该成员的 AI 分析字典，找不到时返回空字典
    
    匹配优先级：
    1. 成员名完全匹配
    2. safe_member_name 匹配
    3. 索引匹配 (member_0, member_1)
    4. strict=False 时兜底到第一个有效字典
    """
    data = raw_ai_analyses
    
    # 解包 {"members": [...]} 格式
    if isinstance(data, dict) and 'members' in data:
        data = data['members']
    
    # 情况 1：单成员单对象
    if is_single_analysis_dict(data):
        # 如果只有一个成员，直接返回（但记录警告）
        if idx == 0:
            return data
        elif strict:
            print(f"❌ 严格模式：期望成员 {idx} ({member_name})，但只有单份数据")
            return {}
        else:
            print(f"⚠️  警告：成员 {idx} ({member_name}) 使用兜底数据")
            return data
    
    # 情况 2：按成员名映射的字典
    if isinstance(data, dict):
        # 候选匹配键（按优先级排序）
        candidates = [
            member_name,                                    # 原始名称
            safe_member_name(member_name),                  # 安全名称
            str(idx),                                       # 数字索引
            f'member_{idx}',                                # member_0 格式
            f'member_{idx+1}',                              # member_1 格式（1-based）
        ]
        
        for key in candidates:
            if key in data and isinstance(data[key], dict):
                print(f"✅ 成员 {member_name} 匹配到键: {key}")
                return data[key]
        
        # 严格模式：找不到直接返回空
        if strict:
            available_keys = list(data.keys())
            print(f"❌ 严格模式：找不到成员 {member_name} (索引{idx}) 的分析数据")
            print(f"   可用键: {available_keys}")
            return {}
        
        # 非严格模式：兜底到第一个有效字典（保留原逻辑但加警告）
        print(f"⚠️  警告：成员 {member_name} 未匹配，兜底到第一个可用数据")
        for v in data.values():
            if isinstance(v, dict):
                return v
        return {}
    
    # 情况 3：列表格式
    if isinstance(data, list):
        if 0 <= idx < len(data) and isinstance(data[idx], dict):
            print(f"✅ 成员 {member_name} 匹配到列表索引: {idx}")
            return data[idx]
        
        if strict:
            print(f"❌ 严格模式：索引 {idx} 超出列表范围（长度 {len(data)}）")
            return {}
        
        # 兜底到第一个
        for v in data:
            if isinstance(v, dict):
                print(f"⚠️  警告：成员 {member_name} 使用兜底数据")
                return v
    
    return {}


# ==================== 语言检测 ====================

def detect_language_mismatch(ai_analysis: Dict, expected_language: str, 
                              whitelist: Optional[List[str]] = None) -> Optional[str]:
    """检测 AI 分析语言是否与配置匹配
    
    参数:
        ai_analysis: AI 分析数据
        expected_language: 期望的语言 ("CN" 或 "EN")
        whitelist: 允许的中文字符白名单（如指标名）
    
    返回:
        错误信息（不匹配时），匹配时返回 None
    """
    if expected_language not in ("CN", "EN"):
        return None
    
    full_text = json.dumps(ai_analysis, ensure_ascii=False)
    
    # 移除白名单中的词汇
    if whitelist:
        for word in whitelist:
            full_text = full_text.replace(word, "")
    
    # 统计中文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', full_text))
    
    if expected_language == "EN" and chinese_chars > 20:
        return f"语言配置不匹配: 设置为 EN(英文), 但检测到 {chinese_chars} 个中文字符"
    elif expected_language == "CN" and chinese_chars < 20:
        return f"语言配置不匹配: 设置为 CN(中文), 但未检测到足够中文字符"
    
    return None