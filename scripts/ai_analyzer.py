#!/usr/bin/env python3
"""
AI 分析模块 - 使用 OpenClaw sessions_spawn 调用 LLM 生成个性化健康建议
这是 OpenClaw Skill 版本，使用 OpenClaw 的 agent 机制而非直接 API 调用
"""
import json
import os
import sys
from typing import Dict, List, Optional

def get_ai_analysis(health_data: Dict, lang: str = 'zh') -> Optional[Dict]:
    """
    通过 OpenClaw sessions_spawn 获取 AI 分析
    
    注意：此函数在 OpenClaw 环境中运行时，会调用 sessions_spawn 触发 AI 分析
    在独立运行时返回 None，使用模板化分析
    
    Returns:
        AI 分析结果字典，包含 conclusions, recommendations, diet_suggestions, warnings
    """
    # 检查是否在 OpenClaw 环境中
    if 'OPENCLAW_SESSION' not in os.environ:
        return None
    
    # 构建提示词
    metrics = {
        'date': health_data.get('date', ''),
        'steps': health_data.get('steps', 0),
        'sleep_hours': health_data.get('sleep_hours', 0),
        'has_sleep': health_data.get('has_sleep_data', False),
        'hrv': health_data.get('hrv', 0),
        'resting_hr': health_data.get('resting_hr', 0),
        'exercise_min': health_data.get('exercise_min', 0),
        'active_calories': health_data.get('active_calories', 0),
        'workouts': len(health_data.get('workouts', [])),
        'recovery_score': health_data.get('recovery_score', 0),
        'sleep_score': health_data.get('sleep_score', 0),
        'exercise_score': health_data.get('exercise_score', 0),
    }
    
    if lang == 'zh':
        prompt = f"""你是一位专业的健康教练和营养师。请根据以下用户的健康数据，生成个性化的健康分析和建议。

## 用户今日健康数据（{metrics['date']}）

### 基础指标
- 步数: {metrics['steps']:,} 步
- 睡眠: {metrics['sleep_hours']:.1f} 小时 {'(无数据)' if not metrics['has_sleep'] else ''}
- HRV: {metrics['hrv']} ms
- 静息心率: {metrics['resting_hr']} bpm
- 锻炼时长: {metrics['exercise_min']} 分钟
- 活跃消耗: {metrics['active_calories']} kcal
- 运动次数: {metrics['workouts']} 次

### 综合评分
- 恢复度: {metrics['recovery_score']}/100
- 睡眠质量: {metrics['sleep_score']}/100
- 运动完成: {metrics['exercise_score']}/100

## 请生成以下内容（JSON格式）

{{
  "conclusions": [
    "结论1：基于数据的简短分析（20字以内）",
    "结论2：...",
    "结论3：..."
  ],
  "recommendations": [
    {{
      "priority": "high/medium/low",
      "text": "具体建议内容（包含行动指导）"
    }}
  ],
  "diet_suggestions": {{
    "summary": "基于数据的饮食建议概述",
    "three_meals": {{
      "breakfast": "具体早餐建议",
      "lunch": "具体午餐建议",
      "dinner": "具体晚餐建议"
    }},
    "two_meals": {{
      "first": "第一餐建议（11:00-12:00）",
      "second": "第二餐建议（17:00-19:00）"
    }}
  }},
  "warnings": ["需要关注的事项"],
  "encouragement": "鼓励性的一句话"
}}

注意：建议要具体、可操作，根据数据给出个性化建议，语气像一位关心用户的私人教练。"""
    else:
        prompt = f"""You are a professional health coach and nutritionist. Please analyze the following user's health data.

## User's Health Data ({metrics['date']})

### Basic Metrics
- Steps: {metrics['steps']:,}
- Sleep: {metrics['sleep_hours']:.1f} hours
- HRV: {metrics['hrv']} ms
- Resting HR: {metrics['resting_hr']} bpm
- Exercise: {metrics['exercise_min']} minutes
- Active Calories: {metrics['active_calories']} kcal
- Workouts: {metrics['workouts']}

### Overall Scores
- Recovery: {metrics['recovery_score']}/100
- Sleep Quality: {metrics['sleep_score']}/100
- Exercise: {metrics['exercise_score']}/100

## Please generate JSON with: conclusions, recommendations, diet_suggestions, warnings, encouragement

Note: Be specific and actionable, give personalized advice based on data."""
    
    # 在 OpenClaw 环境中，实际调用由外层 agent 处理
    # 这里返回 None 表示使用模板化分析
    return None


# 模板化分析（当 AI 不可用时使用）
def get_template_analysis(health_data: Dict, lang: str = 'zh') -> Dict:
    """获取模板化分析（无需 AI）"""
    
    if lang == 'zh':
        conclusions = []
        recommendations = []
        
        # 基于数据的模板化结论
        steps = health_data.get('steps', 0)
        sleep = health_data.get('sleep_hours', 0)
        hrv = health_data.get('hrv', 0)
        
        if steps >= 10000:
            conclusions.append("✓ 今日步数达标，运动量充足")
        elif steps >= 6000:
            conclusions.append("△ 步数接近目标，可适当增加活动")
        else:
            conclusions.append("⚠ 步数偏低，建议增加日常活动")
        
        if sleep >= 7:
            conclusions.append("✓ 睡眠充足，恢复良好")
        elif sleep >= 6:
            conclusions.append("△ 睡眠略少，注意今晚早点休息")
        else:
            conclusions.append("⚠ 睡眠不足，请优先补觉")
        
        if hrv >= 50:
            conclusions.append("✓ HRV良好，身体状态稳定")
        else:
            conclusions.append("△ HRV偏低，注意压力管理")
        
        # 推荐
        if sleep < 7:
            recommendations.append({
                "priority": "high",
                "text": "今晚争取23:00前入睡，保证7-8小时睡眠"
            })
        
        if steps < 6000:
            recommendations.append({
                "priority": "medium",
                "text": "每小时起身活动5分钟，目标8000步"
            })
        
        return {
            "conclusions": conclusions,
            "recommendations": recommendations,
            "diet_suggestions": {
                "summary": "保持均衡饮食，多吃蔬菜水果",
                "three_meals": {
                    "breakfast": "蛋白质+碳水，如鸡蛋+全麦面包",
                    "lunch": "瘦肉+蔬菜+适量主食",
                    "dinner": "清淡为主，7分饱"
                }
            },
            "warnings": [],
            "encouragement": "坚持就是胜利，每一天都是新的开始！"
        }
    else:
        # English templates
        return {
            "conclusions": [
                "Daily activity analysis based on your data",
                "Sleep quality assessment",
                "Recovery status overview"
            ],
            "recommendations": [
                {
                    "priority": "high",
                    "text": "Prioritize sleep tonight, aim for 7-8 hours"
                }
            ],
            "diet_suggestions": {
                "summary": "Maintain balanced diet with more vegetables",
                "three_meals": {
                    "breakfast": "Protein + carbs",
                    "lunch": "Lean meat + vegetables",
                    "dinner": "Light meal, 70% full"
                }
            },
            "warnings": [],
            "encouragement": "Every day is a new beginning!"
        }


if __name__ == '__main__':
    # 测试
    test_data = {
        'date': '2026-02-20',
        'steps': 6852,
        'sleep_hours': 6.5,
        'has_sleep_data': True,
        'hrv': 52,
        'resting_hr': 58,
        'exercise_min': 45,
        'active_calories': 420,
        'workouts': [{'type': '跑步', 'duration': 1800}],
        'recovery_score': 75,
        'sleep_score': 68,
        'exercise_score': 82,
    }
    
    result = get_template_analysis(test_data, 'zh')
    print("✅ 模板化分析结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
