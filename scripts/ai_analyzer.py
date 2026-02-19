#!/usr/bin/env python3
"""
AI 分析模块 - 使用 LLM 生成个性化健康建议
支持 OpenAI、Anthropic 等 API
"""
import json
import os
import sys
from typing import Dict, List, Optional
import subprocess

class HealthAIAnalyzer:
    """健康数据 AI 分析器"""
    
    def __init__(self, provider: str = None, api_key: str = None):
        """
        初始化 AI 分析器
        
        Args:
            provider: AI 提供商 (openai, anthropic, local)
            api_key: API 密钥
        """
        self.provider = provider or os.getenv('HEALTH_AI_PROVIDER', 'template')
        self.api_key = api_key or os.getenv('HEALTH_AI_API_KEY', '')
        self.model = os.getenv('HEALTH_AI_MODEL', '')
        
    def is_configured(self) -> bool:
        """检查是否已配置 AI"""
        return self.provider != 'template' and bool(self.api_key)
    
    def analyze(self, health_data: Dict, lang: str = 'zh') -> Dict:
        """
        分析健康数据并生成建议
        
        Returns:
            Dict with keys: conclusions, recommendations, diet_suggestions, warnings
        """
        if not self.is_configured():
            return None
        
        # 构建提示词
        prompt = self._build_prompt(health_data, lang)
        
        # 调用 AI API
        if self.provider == 'openai':
            return self._call_openai(prompt, lang)
        elif self.provider == 'anthropic':
            return self._call_anthropic(prompt, lang)
        elif self.provider == 'gemini':
            return self._call_gemini(prompt, lang)
        else:
            return None
    
    def _build_prompt(self, data: Dict, lang: str) -> str:
        """构建 AI 提示词"""
        
        # 提取关键指标
        metrics = {
            'date': data.get('date', ''),
            'steps': data.get('steps', 0),
            'sleep_hours': data.get('sleep_hours', 0),
            'has_sleep': data.get('has_sleep_data', False),
            'hrv': data.get('hrv', 0),
            'resting_hr': data.get('resting_hr', 0),
            'exercise_min': data.get('exercise_min', 0),
            'active_calories': data.get('active_calories', 0),
            'workouts': len(data.get('workouts', [])),
            'recovery_score': data.get('recovery_score', 0),
            'sleep_score': data.get('sleep_score', 0),
            'exercise_score': data.get('exercise_score', 0),
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

注意：
1. 建议要具体、可操作，不要泛泛而谈
2. 根据数据给出个性化建议，如睡眠不足时建议具体补觉时间
3. 如果某方面数据不好，给出改善的详细步骤
4. 语气要专业但友好，像一位关心用户的私人教练
"""
        else:
            prompt = f"""You are a professional health coach and nutritionist. Please analyze the following user's health data and generate personalized health analysis and recommendations.

## User's Health Data ({metrics['date']})

### Basic Metrics
- Steps: {metrics['steps']:,}
- Sleep: {metrics['sleep_hours']:.1f} hours {'(no data)' if not metrics['has_sleep'] else ''}
- HRV: {metrics['hrv']} ms
- Resting HR: {metrics['resting_hr']} bpm
- Exercise: {metrics['exercise_min']} minutes
- Active Calories: {metrics['active_calories']} kcal
- Workouts: {metrics['workouts']}

### Overall Scores
- Recovery: {metrics['recovery_score']}/100
- Sleep Quality: {metrics['sleep_score']}/100
- Exercise: {metrics['exercise_score']}/100

## Please generate the following (JSON format):

{{
  "conclusions": [
    "Conclusion 1: Brief data-based analysis (under 30 words)",
    "Conclusion 2: ...",
    "Conclusion 3: ..."
  ],
  "recommendations": [
    {{
      "priority": "high/medium/low",
      "text": "Specific recommendation with actionable guidance"
    }}
  ],
  "diet_suggestions": {{
    "summary": "Data-based diet advice summary",
    "three_meals": {{
      "breakfast": "Specific breakfast suggestion",
      "lunch": "Specific lunch suggestion",
      "dinner": "Specific dinner suggestion"
    }},
    "two_meals": {{
      "first": "First meal suggestion (11:00-12:00)",
      "second": "Second meal suggestion (17:00-19:00)"
    }}
  }},
  "warnings": ["Items needing attention"],
  "encouragement": "One encouraging sentence"
}}

Note:
1. Be specific and actionable, not generic
2. Give personalized advice based on data
3. Provide detailed steps for improvement
4. Tone: professional but friendly, like a caring personal coach
"""
        
        return prompt
    
    def _call_openai(self, prompt: str, lang: str) -> Optional[Dict]:
        """调用 OpenAI API"""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            model = self.model or 'gpt-4o-mini'
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a health coach. Respond in JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"⚠️  OpenAI API error: {e}", file=sys.stderr)
            return None
    
    def _call_anthropic(self, prompt: str, lang: str) -> Optional[Dict]:
        """调用 Anthropic Claude API"""
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=self.api_key)
            
            model = self.model or 'claude-3-5-haiku-20241022'
            
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                temperature=0.7,
                system="You are a health coach. Respond in JSON format only.",
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            # Extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
            
        except Exception as e:
            print(f"⚠️  Anthropic API error: {e}", file=sys.stderr)
            return None
    
    def _call_gemini(self, prompt: str, lang: str) -> Optional[Dict]:
        """调用 Google Gemini API"""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            model = genai.GenerativeModel(self.model or 'gemini-pro')
            
            response = model.generate_content(
                prompt,
                generation_config={'temperature': 0.7}
            )
            
            content = response.text
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return None
            
        except Exception as e:
            print(f"⚠️  Gemini API error: {e}", file=sys.stderr)
            return None


def get_ai_analysis(health_data: Dict, lang: str = 'zh') -> Optional[Dict]:
    """
    获取 AI 分析的便捷函数
    
    Returns:
        AI 分析结果，如果未配置 AI 则返回 None
    """
    analyzer = HealthAIAnalyzer()
    
    if not analyzer.is_configured():
        return None
    
    return analyzer.analyze(health_data, lang)


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
    
    result = get_ai_analysis(test_data, 'zh')
    if result:
        print("✅ AI 分析结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("ℹ️  未配置 AI API，使用模板化分析")
